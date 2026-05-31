#!/usr/bin/env python3
"""
Atlas Heartbeat - Manager Agent Periodic Check
Runs every 6 hours, reviews system state, creates tasks as needed
"""

import json
import subprocess
from datetime import datetime
import sqlite3

DB_PATH = '/root/stellar-station/tasks/queue.db'
API_URL = 'http://localhost:3001'

def get_pending_tasks():
    """Check if there are pending tasks waiting"""
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    count = cursor.fetchone()[0]
    db.close()
    return count

def get_recent_tasks():
    """Get recent task status"""
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    cursor.execute("""
        SELECT COUNT(*), status 
        FROM tasks 
        WHERE datetime(created_at) > datetime('now', '-6 hours')
        GROUP BY status
    """)
    results = dict(cursor.fetchall())
    db.close()
    return results

def create_atlas_heartbeat_task():
    """Create a task for Atlas to review system state"""
    task_stats = get_recent_tasks()
    pending = get_pending_tasks()
    
    payload = {
        'created_by': 'heartbeat',
        'assignee': 'atlas',
        'type': 'heartbeat',
        'payload': json.dumps({
            'instruction': 'Review system state for last 6 hours. Check war room reports. Create tasks for agents if needed.',
            'recent_tasks': task_stats,
            'pending_tasks': pending
        }),
        'cost_estimate': 0.05,
        'priority': 50
    }
    
    result = subprocess.run([
        'curl', '-X', 'POST', f'{API_URL}/tasks',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(payload)
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"[{datetime.now().isoformat()}] ✅ Atlas heartbeat task created")
    else:
        print(f"[{datetime.now().isoformat()}] ✗ Failed to create task: {result.stderr}")

if __name__ == '__main__':
    print(f"[{datetime.now().isoformat()}] 💓 Atlas Heartbeat Running...")
    create_atlas_heartbeat_task()
    print(f"[{datetime.now().isoformat()}] 💓 Heartbeat Complete\n")
