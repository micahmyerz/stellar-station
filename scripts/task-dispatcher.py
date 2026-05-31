#!/usr/bin/env python3
"""
Stellar Station Task Dispatcher Daemon
Polls the SQLite queue every 2 seconds and fires agents on-demand via Hermes.

COST CONTROLS (added):
  - Per-agent model selection: reads model/provider from each agent's IDENTITY.md
    and passes `-m MODEL --provider PROVIDER` to hermes (cheap models per agent).
  - Per-agent cooldowns: honors *_cooldown_seconds from limits.json.
  - Real circuit breaker: pauses spawning when TODAY's spend (from the tasks table)
    reaches daily_total_spend_cap. Spend = cost_actual when reported, else cost_estimate.
"""

import subprocess
import sqlite3
import time
import json
import os
import re
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

# Config
DB_PATH = '/root/stellar-station/tasks/queue.db'
LIMITS_PATH = '/root/stellar-station/tasks/limits.json'
LOG_FILE = '/root/stellar-station/logs/dispatcher.log'
POLL_INTERVAL = 2  # seconds
MAX_TASK_TIMEOUT = 600  # seconds
AGENTS = ['atlas', 'vega', 'nova', 'pulsar', 'lyra']
AGENT_DIR = '/root/stellar-station/agents'

# Ensure log directory exists
Path(LOG_FILE).parent.mkdir(exist_ok=True)

# Load limits once at startup (re-read each cycle so edits take effect without restart)
def load_limits():
    try:
        with open(LIMITS_PATH) as f:
            return json.load(f)
    except Exception as e:
        # Fail safe: if limits can't be read, use conservative defaults
        return {
            "single_task_cost_max": 5.00,
            "daily_total_spend_cap": 10.00,
            "credits_warn_threshold": 25.00,
        }

def log(msg):
    """Log to both stdout and file."""
    timestamp = f"[{datetime.now().isoformat()}]"
    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(full_msg + '\n')

# Track whether we've already warned today so we don't spam the log
_warned_today = None

def signal_handler(sig, frame):
    log(f"Received signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_db():
    return sqlite3.connect(DB_PATH)

# ── Model selection ───────────────────────────────────────────────────────────
# Cache parsed identities so we don't re-read files every loop.
_agent_model_cache = {}

def get_agent_model(agent):
    """Read model + provider from the agent's IDENTITY.md frontmatter.
    Returns (model, provider) or (None, None) if not declared (falls back to
    Hermes global default)."""
    if agent in _agent_model_cache:
        return _agent_model_cache[agent]

    model, provider = None, None
    identity_path = os.path.join(AGENT_DIR, agent, 'IDENTITY.md')
    try:
        with open(identity_path) as f:
            text = f.read()
        # Grab the first frontmatter block between --- ... ---
        m = re.search(r'^---\s*\n(.*?)\n---', text, re.DOTALL | re.MULTILINE)
        block = m.group(1) if m else text[:500]
        for line in block.splitlines():
            if ':' not in line:
                continue
            key, _, val = line.partition(':')
            key = key.strip().lower()
            val = val.strip()
            if key == 'model' and val:
                model = val
            elif key == 'provider' and val:
                provider = val
    except Exception as e:
        log(f"⚠️  Could not read model for {agent}: {e} — using Hermes default")

    _agent_model_cache[agent] = (model, provider)
    return model, provider

# ── Timestamp helpers ──────────────────────────────────────────────────────────
def parse_ts(s):
    """Parse the ISO timestamps stored in the DB (UTC, may end in Z, may have
    fractional seconds). Returns a naive UTC datetime, or None."""
    if not s:
        return None
    try:
        s = s.strip().replace('Z', '').replace('+00:00', '')
        # Try with fractional seconds, then without
        for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
    except Exception:
        pass
    return None

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ── Cost / circuit breaker ──────────────────────────────────────────────────────
def today_spend():
    """Sum today's spend from the tasks table. Uses cost_actual when an agent
    has reported it (> 0), otherwise the cost_estimate. Mirrors the source the
    API's /treasury/daily uses."""
    today_start = utcnow().strftime('%Y-%m-%d') + 'T00:00:00'
    db = get_db()
    try:
        row = db.execute("""
            SELECT COALESCE(SUM(
                CASE WHEN cost_actual > 0 THEN cost_actual ELSE cost_estimate END
            ), 0)
            FROM tasks
            WHERE created_at >= ?
        """, (today_start,)).fetchone()
        return float(row[0] or 0)
    finally:
        db.close()

def credits_paused(limits):
    """Real circuit breaker: pause spawning when today's spend has hit the daily
    cap. Returns True if we should NOT spawn new work right now."""
    global _warned_today
    cap = float(limits.get('daily_total_spend_cap', 10.0))
    warn = float(limits.get('credits_warn_threshold', cap))
    spend = today_spend()

    # One-time-per-day warning as we approach the cap
    today_key = utcnow().strftime('%Y-%m-%d')
    if warn and spend >= min(warn, cap * 0.8) and _warned_today != today_key:
        log(f"⚠️  Spend warning: today ${spend:.2f} (cap ${cap:.2f})")
        _warned_today = today_key

    if spend >= cap:
        log(f"🛑 Circuit breaker: today's spend ${spend:.2f} >= cap ${cap:.2f}. Pausing new tasks.")
        return True
    return False

def agent_in_cooldown(agent, limits):
    """True if the agent ran a task more recently than its cooldown allows."""
    cooldown = float(limits.get(f'{agent}_cooldown_seconds', 0) or 0)
    if cooldown <= 0:
        return False
    db = get_db()
    try:
        row = db.execute("""
            SELECT MAX(COALESCE(completed_at, started_at, created_at))
            FROM tasks WHERE assignee = ?
        """, (agent,)).fetchone()
    finally:
        db.close()
    last = parse_ts(row[0]) if row else None
    if last is None:
        return False
    elapsed = (utcnow() - last).total_seconds()
    if elapsed < cooldown:
        return True
    return False

def agent_already_running(agent):
    """Check if agent has a task in progress."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE assignee = ? AND status = 'in_progress'
    """, (agent,))
    count = cursor.fetchone()[0]
    db.close()
    return count > 0

def claim_next_pending_task(agent):
    """Atomically claim a pending task for this agent."""
    db = get_db()
    cursor = db.cursor()

    now = utcnow().isoformat() + 'Z'

    cursor.execute("""
        SELECT id FROM tasks
        WHERE assignee = ? AND status = 'pending'
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
    """, (agent,))

    row = cursor.fetchone()
    if not row:
        db.close()
        return None

    task_id = row[0]

    cursor.execute("""
        UPDATE tasks SET status = 'in_progress', started_at = ?
        WHERE id = ? AND status = 'pending'
    """, (now, task_id))

    if cursor.rowcount == 0:
        db.close()
        return None

    cursor.execute("""
        INSERT INTO events (ts, task_id, event, msg)
        VALUES (?, ?, 'status_change', 'Claimed by dispatcher')
    """, (now, task_id))

    db.commit()

    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    db.close()

    return dict(zip(columns, row))

def spawn_worker(agent, task):
    """Spawn Hermes agent to work on task and wait for completion."""
    task_id = task['id']
    payload = json.loads(task['payload'])

    task_msg = f"""You have been assigned task #{task_id}.

Task Type: {task['type']}
Created By: {task['created_by']}
Payload: {json.dumps(payload, indent=2)}

Instructions:
1. Read your IDENTITY.md and PLAYBOOK.md files in this directory
2. Execute the task according to your playbook
3. When done, call: curl -X POST http://localhost:3001/tasks/{task_id}/complete \\
     -H 'Content-Type: application/json' \\
     -d '{{"result": {{"status": "success", "summary": "..."}}, "cost_actual": 0.XX}}'

Cost estimate for this task: ${task['cost_estimate']}
Work within that budget.
"""

    # Build the hermes command, injecting the agent's declared cheap model.
    model, provider = get_agent_model(agent)
    cmd = ['hermes', 'chat', '-q', task_msg]
    if model:
        cmd += ['-m', model]
    if provider:
        cmd += ['--provider', provider]
    cmd += ['--max-turns', '10', '--quiet']

    model_note = f"{provider}/{model}" if model else "hermes-default-model"
    log(f"🚀 Spawning {agent} for task #{task_id} (type: {task['type']}) on {model_note}")

    try:
        result = subprocess.run(
            cmd,
            cwd=f'/root/stellar-station/agents/{agent}',
            capture_output=True,
            text=True,
            timeout=MAX_TASK_TIMEOUT
        )

        log(f"✓ {agent} completed task #{task_id} (exit: {result.returncode})")

        # If hermes errored (e.g. bad model string), surface it instead of hiding it
        if result.returncode != 0:
            err = (result.stderr or result.stdout or '').strip()[:300]
            log(f"⚠️  {agent} task #{task_id} hermes exit {result.returncode}: {err}")

        db = get_db()
        task_check = db.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        db.close()

        if task_check and task_check[0] == 'in_progress':
            log(f"⚠️  Task #{task_id} still in_progress, auto-completing")
            db = get_db()
            now = utcnow().isoformat() + 'Z'
            db.execute(
                "UPDATE tasks SET status = 'done', completed_at = ?, result = ? WHERE id = ?",
                (now, json.dumps({"auto_completed": True, "output": result.stdout[:500]}), task_id)
            )
            db.commit()
            db.close()

    except subprocess.TimeoutExpired:
        log(f"⏱️  Task #{task_id} timed out after {MAX_TASK_TIMEOUT}s")
        db = get_db()
        db.execute("UPDATE tasks SET status = 'failed', notes = ? WHERE id = ?",
                   (f"Timeout after {MAX_TASK_TIMEOUT}s", task_id))
        db.commit()
        db.close()

    except Exception as e:
        log(f"✗ Failed to spawn {agent}: {e}")
        db = get_db()
        db.execute("UPDATE tasks SET status = 'failed', notes = ? WHERE id = ?",
                   (f"Dispatcher error: {str(e)}", task_id))
        db.commit()
        db.close()

def main():
    limits = load_limits()
    log("⭐ Stellar Station Task Dispatcher starting...")
    log(f"Agents: {', '.join(AGENTS)}")
    log(f"Poll interval: {POLL_INTERVAL}s")
    log(f"Database: {DB_PATH}")
    log(f"Daily spend cap: ${limits.get('daily_total_spend_cap')}  |  per-task max: ${limits.get('single_task_cost_max')}")
    for a in AGENTS:
        m, p = get_agent_model(a)
        log(f"  {a}: {p}/{m}" if m else f"  {a}: hermes default model")
    log("")

    while True:
        try:
            # Re-read limits each cycle so changes apply without a restart
            limits = load_limits()

            if credits_paused(limits):
                time.sleep(30)
                continue

            for agent in AGENTS:
                if agent_already_running(agent):
                    continue
                if agent_in_cooldown(agent, limits):
                    continue

                task = claim_next_pending_task(agent)
                if task:
                    # Re-check the breaker right before spending money
                    if credits_paused(limits):
                        # Put the task back to pending; we'll pick it up after reset
                        db = get_db()
                        db.execute("UPDATE tasks SET status = 'pending', started_at = NULL WHERE id = ?",
                                   (task['id'],))
                        db.commit()
                        db.close()
                        log(f"↩️  Returned task #{task['id']} to pending (spend cap hit)")
                        break
                    spawn_worker(agent, task)

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log("🛑 Dispatcher shutting down...")
            break
        except Exception as e:
            log(f"✗ ERROR: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
