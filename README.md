# ⭐ Stellar Station - Autonomous Agent System

Multi-agent AI system for managing and optimizing **getniella.com** Shopify store.

## System Overview

**Status**: ✅ Operational  
**Store**: getniella.com (zzahbk-rt.myshopify.com)  
**VPS**: 2.24.126.194 (Hostinger Ubuntu)  
**Theme**: Retro Pixel Space Station (Game Boy Color + CRT effects)

---

## 🛸 Agents

| Agent | Role | Responsibilities |
|-------|------|-----------------|
| **Atlas** 🌍 | Manager | Task routing, crew coordination, strategic decisions |
| **Vega** ⭐ | Research | Competitor analysis, market trends, product research |
| **Nova** 💫 | Marketing | Ad campaigns, promotions, social media |
| **Pulsar** 📊 | Analytics | Revenue tracking, A/B testing, profitability reports |
| **Lyra** ✨ | Copywriting | Product descriptions, landing pages, email campaigns |

---

## 🚀 Services

### Core Services (Systemd)

```bash
# Check status
systemctl status stellar-api
systemctl status stellar-dispatcher
systemctl status stellar-dashboard

# Restart a service
sudo systemctl restart stellar-api
sudo systemctl restart stellar-dispatcher
sudo systemctl restart stellar-dashboard

# View logs
journalctl -u stellar-api -f
journalctl -u stellar-dispatcher -f
journalctl -u stellar-dashboard -f
```

### Quick Status Check

```bash
/root/stellar-station/scripts/status.sh
```

---

## 🖥️ Dashboard

**URL**: http://2.24.126.194:3000

Features:
- Real-time agent status
- Task queue visualization
- War room reports
- System metrics
- Retro pixel CRT theme

---

## 📊 Task Management

### View Tasks

```bash
# All tasks
sqlite3 /root/stellar-station/tasks/queue.db "SELECT * FROM tasks ORDER BY id DESC LIMIT 10;"

# By agent
sqlite3 /root/stellar-station/tasks/queue.db "SELECT * FROM tasks WHERE assignee='atlas';"

# By status
sqlite3 /root/stellar-station/tasks/queue.db "SELECT * FROM tasks WHERE status='done';"
```

### Create a Task (via API)

```bash
curl -X POST http://localhost:3001/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "created_by": "human",
    "assignee": "pulsar",
    "type": "analytics",
    "payload": "{\"request\": \"Pull weekly sales data\"}",
    "cost_estimate": 0.04,
    "priority": 100
  }'
```

---

## 🐕 Automated Systems

### Profitability Watchdog
- **Schedule**: Every Sunday at midnight
- **Function**: Checks weekly P&L, triggers emergency meeting if negative
- **Manual Run**: `python /root/stellar-station/scripts/profitability-watchdog.py`

### Atlas Heartbeat
- **Schedule**: Every 6 hours
- **Function**: Reviews system state, creates tasks as needed
- **Manual Run**: `python /root/stellar-station/scripts/atlas-heartbeat.py`

### View Cron Jobs

```bash
crontab -l
```

---

## 📁 Directory Structure

```
/root/stellar-station/
├── agents/                    # Agent IDENTITY + PLAYBOOK files
│   ├── atlas/
│   ├── vega/
│   ├── nova/
│   ├── pulsar/
│   └── lyra/
├── api/                       # Express API server
│   └── server.js
├── dashboard/                 # Web dashboard
│   ├── server.js
│   ├── views/
│   └── public/
├── scripts/                   # Helper scripts
│   ├── shopify-helper.py      # Shopify API (mock mode)
│   ├── image-gen.py           # Replicate image generation
│   ├── task-dispatcher.py     # Task queue daemon
│   ├── profitability-watchdog.py
│   ├── atlas-heartbeat.py
│   └── status.sh              # System status check
├── tasks/
│   ├── queue.db               # SQLite task database
│   └── limits.json            # Cost caps ($10/day)
├── treasury/                  # Cost ledgers (JSONL)
│   ├── openrouter-ledger.jsonl
│   ├── anthropic-ledger.jsonl
│   ├── replicate-ledger.jsonl
│   └── higgsfield-ledger.jsonl
├── war-room/                  # Agent reports
├── logs/                      # System logs
│   ├── dispatcher.log
│   ├── watchdog.log
│   └── heartbeat.log
└── .env                       # API keys (chmod 600)
```

---

## 🔐 Security

### Firewall Rules

```bash
sudo ufw status
```

Open ports: **22** (SSH), **3000** (Dashboard), **3001** (API)

### API Keys

Stored in `/root/stellar-station/.env` (chmod 600)

**Still Needed:**
- Shopify Admin API token (starts with `shpat_`)
- Replicate API token (optional, for real image generation)

---

## 📈 Next Steps

### Phase 4 Remaining:
- [ ] Add Shopify Admin API token to `.env`
- [ ] Add Replicate API token to `.env` (optional)
- [ ] Test real Shopify integration

### Phase 7: Launch
- [ ] Atlas creates first product optimization task
- [ ] Monitor for 48 hours
- [ ] User training on Discord commands

---

## 🛠️ Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u stellar-dispatcher --since "10 minutes ago"

# Restart all services
sudo systemctl restart stellar-api stellar-dispatcher stellar-dashboard
```

### Tasks Stuck in "Pending"

- Check dispatcher logs: `tail -f /root/stellar-station/logs/dispatcher.log`
- Verify agents aren't blocked: `sqlite3 /root/stellar-station/tasks/queue.db "SELECT assignee, status FROM tasks WHERE status='in_progress';"`
- Restart dispatcher: `sudo systemctl restart stellar-dispatcher`

### Dashboard Not Loading

- Check service: `systemctl status stellar-dashboard`
- Check firewall: `sudo ufw status | grep 3000`
- Test locally: `curl http://localhost:3000`

---

## 💰 Budget

- **Daily Cap**: $10.00 (enforced by API)
- **Task Cap**: $5.00 per task
- **VPS**: ~$10/month (Hostinger)
- **Target**: $5,000+/month revenue

---

## 📞 Support

Created by: Larry (Hermes AI Assistant)  
Date: May 30, 2026  
Build Guide: `/root/tonka-guide/`

**Quick Help:**

```bash
# System status
/root/stellar-station/scripts/status.sh

# Recent tasks
sqlite3 /root/stellar-station/tasks/queue.db "SELECT * FROM tasks ORDER BY id DESC LIMIT 5;"

# Recent logs
tail -20 /root/stellar-station/logs/dispatcher.log

# War room reports
ls -lt /root/stellar-station/war-room/
```

---

## 🎮 Dashboard Access

**Local**: http://localhost:3000  
**Remote**: http://2.24.126.194:3000

Retro pixel theme with CRT effects, neon glow, and Game Boy Color palette.

---

**Status**: All systems operational ✅  
**Build Phase**: 5/7 complete  
**Next**: Shopify API token + Full testing
