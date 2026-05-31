#!/bin/bash
# Stellar Station System Status Check

echo "════════════════════════════════════════════════════════════"
echo "  ⭐ STELLAR STATION SYSTEM STATUS"
echo "════════════════════════════════════════════════════════════"
echo ""

# Services
echo "🚀 SERVICES:"
echo ""
for service in stellar-api stellar-dispatcher stellar-dashboard; do
    if systemctl is-active --quiet $service; then
        echo "  ✅ $service: RUNNING"
    else
        echo "  ❌ $service: STOPPED"
    fi
done
echo ""

# Database Stats
echo "📊 TASK QUEUE:"
echo ""
cd /root/stellar-station
sqlite3 tasks/queue.db "SELECT '  Total: ' || COUNT(*) FROM tasks;" .quit
sqlite3 tasks/queue.db "SELECT '  Done: ' || COUNT(*) FROM tasks WHERE status='done';" .quit
sqlite3 tasks/queue.db "SELECT '  Failed: ' || COUNT(*) FROM tasks WHERE status='failed';" .quit
sqlite3 tasks/queue.db "SELECT '  In Progress: ' || COUNT(*) FROM tasks WHERE status='in_progress';" .quit
sqlite3 tasks/queue.db "SELECT '  Pending: ' || COUNT(*) FROM tasks WHERE status='pending';" .quit
echo ""

# Agent Activity
echo "🛸 AGENT ACTIVITY:"
echo ""
for agent in atlas vega nova pulsar lyra; do
    count=$(sqlite3 tasks/queue.db "SELECT COUNT(*) FROM tasks WHERE assignee='$agent';" .quit)
    echo "  $agent: $count tasks"
done
echo ""

# Recent Logs
echo "📝 RECENT DISPATCHER LOG (last 5 lines):"
echo ""
tail -5 /root/stellar-station/logs/dispatcher.log | sed 's/^/  /'
echo ""

# War Room
echo "📡 WAR ROOM REPORTS:"
echo ""
ls -lt /root/stellar-station/war-room/*.md 2>/dev/null | head -3 | awk '{print "  "$9" ("$6" "$7" "$8")"}'
echo ""

# Firewall
echo "🔥 FIREWALL:"
echo ""
ufw status | grep -E "3000|3001" | sed 's/^/  /'
echo ""

echo "════════════════════════════════════════════════════════════"
echo "  Dashboard: http://2.24.126.194:3000"
echo "  API: http://localhost:3001"
echo "════════════════════════════════════════════════════════════"
