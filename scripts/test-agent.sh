#!/bin/bash
# Quick task creator for testing agent animations

AGENT=${1:-atlas}

echo "Creating demo task for $AGENT..."

curl -X POST http://localhost:3001/tasks \
  -H 'Content-Type: application/json' \
  -d "{
    \"created_by\": \"demo\",
    \"assignee\": \"$AGENT\",
    \"type\": \"demo\",
    \"payload\": \"{}\",
    \"cost_estimate\": 0.01,
    \"priority\": 100
  }" 2>/dev/null

echo ""
echo "✅ Task created! Watch $AGENT walk to the War Room on the dashboard!"
echo "   Dashboard: http://2.24.126.194:3000"
