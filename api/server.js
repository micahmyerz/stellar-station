const express = require('express');
const Database = require('better-sqlite3');
const cors = require('cors');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

const app = express();
app.use((req, res, next) => { res.set("Access-Control-Allow-Origin", "*"); next(); });
const db = new Database('/root/stellar-station/tasks/queue.db');
const limits = require('/root/stellar-station/tasks/limits.json');

// Wire in store stats endpoint
require('./store-stats')(app);

app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get all tasks (with optional filters)
app.get('/tasks', (req, res) => {
  const { assignee, status, limit = 100 } = req.query;
  let query = 'SELECT * FROM tasks WHERE 1=1';
  const params = [];
  
  if (assignee) {
    query += ' AND assignee = ?';
    params.push(assignee);
  }
  if (status) {
    query += ' AND status = ?';
    params.push(status);
  }
  
  query += ' ORDER BY created_at DESC LIMIT ?';
  params.push(parseInt(limit));
  
  const tasks = db.prepare(query).all(...params);
  res.json(tasks);
});

// Get single task
app.get('/tasks/:id', (req, res) => {
  const task = db.prepare('SELECT * FROM tasks WHERE id = ?').get(req.params.id);
  if (!task) return res.status(404).json({ error: 'Task not found' });
  res.json(task);
});

// Create task (with limit checks)
app.post('/tasks', (req, res) => {
  const { created_by, assignee, type, payload, cost_estimate = 0.10, priority = 50, notes } = req.body;
  
  if (!assignee || !type || !payload) {
    return res.status(400).json({ error: 'Missing required fields: assignee, type, payload' });
  }
  
  // Enforce cost floors
  const costFloors = {
    research: 0.10,
    marketing: 0.08,
    copywriting: 0.05,
    analytics: 0.05,
    chat: 0.02
  };
  const finalEstimate = Math.max(cost_estimate, costFloors[type] || 0.05);
  
  // Check daily spend cap
  const todayStart = new Date().toISOString().split('T')[0] + 'T00:00:00Z';
  const todayTotal = db.prepare(
    'SELECT COALESCE(SUM(cost_estimate), 0) AS sum FROM tasks WHERE created_at >= ?'
  ).get(todayStart).sum;
  
  if (todayTotal + finalEstimate > limits.daily_total_spend_cap) {
    return res.status(429).json({
      code: 'LIMIT_HIT',
      reason: 'daily_total_spend_cap',
      current: todayTotal,
      cap: limits.daily_total_spend_cap,
      requested: finalEstimate
    });
  }
  
  // Check single task max
  if (finalEstimate > limits.single_task_cost_max) {
    return res.status(429).json({
      code: 'LIMIT_HIT',
      reason: 'single_task_cost_max',
      estimate: finalEstimate,
      cap: limits.single_task_cost_max
    });
  }
  
  // Create task
  const now = new Date().toISOString();
  const dedupeKey = null; // We can add SHA1 hashing later if needed
  
  const insert = db.prepare(`
    INSERT INTO tasks (created_at, created_by, assignee, type, status, payload, cost_estimate, priority, notes, dedupe_key)
    VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
  `);
  
  const result = insert.run(now, created_by || 'system', assignee, type, JSON.stringify(payload), finalEstimate, priority, notes, dedupeKey);
  
  // Log event
  db.prepare('INSERT INTO events (ts, task_id, event, msg) VALUES (?, ?, ?, ?)').run(
    now, result.lastInsertRowid, 'created', `Task created by ${created_by || 'system'}`
  );
  
  res.status(201).json({ id: result.lastInsertRowid, status: 'pending' });
});

// Complete task
app.post('/tasks/:id/complete', (req, res) => {
  const { result, cost_actual = 0 } = req.body;
  const now = new Date().toISOString();
  
  const update = db.prepare(`
    UPDATE tasks SET status = 'done', result = ?, cost_actual = ?, completed_at = ?
    WHERE id = ?
  `);
  
  update.run(JSON.stringify(result), cost_actual, now, req.params.id);
  
  db.prepare('INSERT INTO events (ts, task_id, event, msg) VALUES (?, ?, ?, ?)').run(
    now, req.params.id, 'status_change', 'Task completed'
  );
  
  res.json({ status: 'done' });
});

// Fail task
app.post('/tasks/:id/fail', (req, res) => {
  const { reason } = req.body;
  const now = new Date().toISOString();
  
  const update = db.prepare(`
    UPDATE tasks SET status = 'failed', notes = ?, completed_at = ?
    WHERE id = ?
  `);
  
  update.run(reason, now, req.params.id);
  
  db.prepare('INSERT INTO events (ts, task_id, event, msg) VALUES (?, ?, ?, ?)').run(
    now, req.params.id, 'status_change', `Task failed: ${reason}`
  );
  
  res.json({ status: 'failed' });
});

// Get daily spend summary
app.get('/treasury/daily', (req, res) => {
  const todayStart = new Date().toISOString().split('T')[0] + 'T00:00:00Z';
  
  const stats = db.prepare(`
    SELECT 
      COALESCE(SUM(cost_estimate), 0) AS estimated,
      COALESCE(SUM(cost_actual), 0) AS actual,
      COUNT(*) AS task_count
    FROM tasks
    WHERE created_at >= ?
  `).get(todayStart);
  
  res.json({
    date: todayStart.split('T')[0],
    estimated: stats.estimated,
    actual: stats.actual,
    tasks: stats.task_count,
    cap: limits.daily_total_spend_cap,
    remaining: limits.daily_total_spend_cap - stats.estimated
  });
});

// Get events
app.get('/events', (req, res) => {
  const { limit = 100 } = req.query;
  const events = db.prepare('SELECT * FROM events ORDER BY ts DESC LIMIT ?').all(parseInt(limit));
  res.json(events);
});

const PORT = process.env.API_PORT || 3001;
app.listen(PORT, () => {
  console.log(`✓ Stellar Station Task Queue API running on port ${PORT}`);
  console.log(`  Health: http://localhost:${PORT}/health`);
  console.log(`  Tasks: http://localhost:${PORT}/tasks`);
  console.log(`  Daily spend: http://localhost:${PORT}/treasury/daily`);
});
