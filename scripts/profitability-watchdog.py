#!/usr/bin/env python3
"""
Profitability Watchdog - Weekly P&L Check
Runs every Sunday at midnight, checks if net profit is negative for the week.
If negative, triggers emergency meeting among agents.
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

TREASURY_DIR = '/root/stellar-station/treasury'
WAR_ROOM_DIR = '/root/stellar-station/war-room'
API_URL = 'http://localhost:3001'

def get_weekly_costs():
    """Calculate total costs from all ledgers for last 7 days"""
    total = 0.0
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    
    for ledger in Path(TREASURY_DIR).glob('*-ledger.jsonl'):
        try:
            with open(ledger) as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get('timestamp', '') >= cutoff:
                        total += float(entry.get('amount', 0))
        except Exception as e:
            print(f"Error reading {ledger}: {e}")
    
    return total

def get_weekly_revenue():
    """Get revenue from Shopify helper (mock or real)"""
    try:
        result = subprocess.run(
            ['python', '/root/stellar-station/scripts/shopify-helper.py', 'orders', 'list'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('total_revenue', 0)
        else:
            return 0
    except Exception as e:
        print(f"Error getting revenue: {e}")
        return 0

def create_emergency_tasks():
    """Create tasks for all agents to submit profitability assessments"""
    agents = {
        'pulsar': 'Analyze last 7 days. What are the exact revenue and cost figures? Where is the money going?',
        'vega': 'Research competitors and market trends. What opportunities are we missing?',
        'nova': 'Review current marketing approach. What changes could improve ROAS?',
        'lyra': 'Review product copy. Is it converting? What improvements would help sales?'
    }
    
    for agent, question in agents.items():
        payload = {
            'created_by': 'watchdog',
            'assignee': agent,
            'type': 'emergency_assessment',
            'payload': json.dumps({'question': question, 'context': 'Weekly profitability check triggered'}),
            'cost_estimate': 0.05,
            'priority': 200
        }
        
        # Create task via API
        subprocess.run([
            'curl', '-X', 'POST', f'{API_URL}/tasks',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ], capture_output=True)

def send_discord_alert(revenue, costs, net_profit):
    """Send alert to Discord (via Hermes send_message)"""
    # This will be implemented when Discord integration is ready
    pass

def main():
    print(f"[{datetime.now().isoformat()}] 🐕 Profitability Watchdog Running...")
    
    revenue = get_weekly_revenue()
    costs = get_weekly_costs()
    net_profit = revenue - costs
    
    # VPS cost (approximately)
    vps_monthly = 10.00
    vps_weekly = vps_monthly / 4.33
    total_costs = costs + vps_weekly
    true_net = revenue - total_costs
    
    print(f"  Revenue: ${revenue:.2f}")
    print(f"  Agent Costs: ${costs:.2f}")
    print(f"  VPS: ${vps_weekly:.2f}")
    print(f"  Net Profit: ${true_net:.2f}")
    
    # Save report
    report_path = Path(WAR_ROOM_DIR) / f'watchdog-{datetime.now().strftime("%Y%m%d")}.md'
    with open(report_path, 'w') as f:
        f.write(f"""# 🐕 PROFITABILITY WATCHDOG REPORT
Date: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}
Period: Last 7 days

## FINANCIAL SNAPSHOT

- **Revenue**: ${revenue:.2f}
- **Agent Costs**: ${costs:.2f}
- **VPS Costs**: ${vps_weekly:.2f}
- **NET PROFIT**: ${true_net:.2f}

## STATUS

""")
        
        if true_net < 0:
            f.write(f"""⚠️ **ALERT: NEGATIVE PROFITABILITY**

The system is operating at a loss. Emergency strategy meeting triggered.

All agents have been tasked to submit profitability assessments.
Atlas will review and escalate to human operator.

**Action Required**: Review agent assessments and adjust strategy.
""")
            
            # Trigger emergency meeting
            print("  ⚠️  NEGATIVE PROFIT - Triggering emergency meeting")
            create_emergency_tasks()
            
            # Create Atlas task to coordinate
            atlas_payload = {
                'created_by': 'watchdog',
                'assignee': 'atlas',
                'type': 'emergency_coordination',
                'payload': json.dumps({
                    'situation': f'Weekly P&L is negative: ${true_net:.2f}',
                    'revenue': revenue,
                    'costs': total_costs,
                    'action': 'Collect assessments from all agents and present recommendations to human'
                }),
                'cost_estimate': 0.10,
                'priority': 300
            }
            
            subprocess.run([
                'curl', '-X', 'POST', f'{API_URL}/tasks',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(atlas_payload)
            ], capture_output=True)
            
        else:
            f.write(f"""✅ **HEALTHY OPERATION**

The system is profitable. Continue current strategy.

**Profit Margin**: {(true_net / revenue * 100) if revenue > 0 else 0:.1f}%
""")
            print("  ✅ Profitable - No action needed")
    
    print(f"  Report saved: {report_path}")
    print(f"[{datetime.now().isoformat()}] 🐕 Watchdog Complete\n")

if __name__ == '__main__':
    main()
