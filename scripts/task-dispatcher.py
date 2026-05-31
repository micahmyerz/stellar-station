#!/usr/bin/env python3
"""
Stellar Station Task Dispatcher Daemon
Polls the SQLite queue every 2 seconds and fires agents on-demand via Hermes.
"""

import subprocess
import sqlite3
import time
import json
import os
import signal
import sys
from datetime import datetime
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

def log(msg):
    """Log to both stdout and file."""
    timestamp = f"[{datetime.now().isoformat()}]"
    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(full_msg + '\n')

# Track running processes
running_pids = {}

def signal_handler(sig, frame):
    log(f"Received signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_db():
    return sqlite3.connect(DB_PATH)

def credits_paused():
    """Check if we're in circuit-breaker mode (low credits)."""
    # TODO: Implement real credit check via Anthropic/OpenRouter API
    # For now, just return False
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
    
    now = datetime.utcnow().isoformat() + 'Z'
    
    # Find oldest pending task for this agent
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
    
    # Claim it (atomic update)
    cursor.execute("""
        UPDATE tasks SET status = 'in_progress', started_at = ?
        WHERE id = ? AND status = 'pending'
    """, (now, task_id))
    
    if cursor.rowcount == 0:
        # Someone else claimed it
        db.close()
        return None
    
    # Log event
    cursor.execute("""
        INSERT INTO events (ts, task_id, event, msg)
        VALUES (?, ?, 'status_change', 'Claimed by dispatcher')
    """, (now, task_id))
    
    db.commit()
    
    # Fetch full task
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    db.close()
    
    return dict(zip(columns, row))

def spawn_worker(agent, task):
    """Spawn Hermes agent to work on task and wait for completion."""
    task_id = task['id']
    payload = json.loads(task['payload'])
    
    # Build task message for the agent
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
    
    log(f"🚀 Spawning {agent} for task #{task_id} (type: {task['type']})")
    
    # Spawn Hermes agent and WAIT for completion
    try:
        result = subprocess.run(
            [
                'hermes', 'chat',
                '-q', task_msg,
                '--max-turns', '10',
                '--quiet'
            ],
            cwd=f'/root/stellar-station/agents/{agent}',
            capture_output=True,
            text=True,
            timeout=MAX_TASK_TIMEOUT
        )
        
        log(f"✓ {agent} completed task #{task_id} (exit: {result.returncode})")
        
        # Check if task was marked complete by the agent
        db = get_db()
        task_check = db.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        db.close()
        
        if task_check and task_check[0] == 'in_progress':
            # Agent finished but didn't call completion API — mark as done anyway
            log(f"⚠️  Task #{task_id} still in_progress, auto-completing")
            db = get_db()
            now = datetime.utcnow().isoformat() + 'Z'
            db.execute(
                "UPDATE tasks SET status = 'done', completed_at = ?, result = ? WHERE id = ?",
                (now, json.dumps({"auto_completed": True, "output": result.stdout[:500]}), task_id)
            )
            db.commit()
            db.close()
        
    except subprocess.TimeoutExpired:
        log(f"⏱️  Task #{task_id} timed out after {MAX_TASK_TIMEOUT}s")
        db = get_db()
        now = datetime.utcnow().isoformat() + 'Z'
        db.execute("UPDATE tasks SET status = 'failed', notes = ? WHERE id = ?", 
                   (f"Timeout after {MAX_TASK_TIMEOUT}s", task_id))
        db.commit()
        db.close()
        
    except Exception as e:
        log(f"✗ Failed to spawn {agent}: {e}")
        # Mark task as failed
        db = get_db()
        now = datetime.utcnow().isoformat() + 'Z'
        db.execute("UPDATE tasks SET status = 'failed', notes = ? WHERE id = ?", 
                   (f"Dispatcher error: {str(e)}", task_id))
        db.commit()
        db.close()

def main():
    log("⭐ Stellar Station Task Dispatcher starting...")
    log(f"Agents: {', '.join(AGENTS)}")
    log(f"Poll interval: {POLL_INTERVAL}s")
    log(f"Database: {DB_PATH}")
    log("")
    
    while True:
        try:
            if credits_paused():
                log("⚠️  Circuit breaker: credits paused")
                time.sleep(30)
                continue
            
            for agent in AGENTS:
                if agent_already_running(agent):
                    continue
                
                task = claim_next_pending_task(agent)
                if task:
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
