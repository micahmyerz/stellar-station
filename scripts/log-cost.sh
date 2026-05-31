#!/bin/bash
# Usage: log-cost.sh <provider> <amount> <agent> <task_id> <notes>

PROVIDER=$1
AMOUNT=$2
AGENT=$3
TASK_ID=$4
NOTES=$5

LEDGER="/root/stellar-station/treasury/${PROVIDER}-ledger.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "{\"ts\":\"$TIMESTAMP\",\"provider\":\"$PROVIDER\",\"amount\":$AMOUNT,\"agent\":\"$AGENT\",\"task_id\":$TASK_ID,\"notes\":\"$NOTES\"}" >> "$LEDGER"
