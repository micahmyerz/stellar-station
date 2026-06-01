const express = require('express');
const Database = require('better-sqlite3');
const path = require('path');
const bcrypt = require('bcryptjs');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

const app = express();
const PORT = process.env.DASHBOARD_PORT || 3000;
const DB_PATH = '/root/stellar-station/tasks/queue.db';

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Database
const db = new Database(DB_PATH, { readonly: true });

// Routes

// Home - Mission Control Dashboard
app.get('/', (req, res) => {
    res.render('stellar-station');
});

// Walkable Phaser station
app.get('/walk', (req, res) => {
    res.sendFile(path.join(__dirname, 'views', 'walk.html'));
});

// API endpoint for live dashboard data
app.get('/api/status', (req, res) => {
    const tasks = db.prepare('SELECT status FROM tasks').all();
    const total = tasks.length;
    const completed = tasks.filter(t => t.status === 'done').length;
    const active = tasks.filter(t => t.status === 'in_progress').length;
    
    // Check which agents have active tasks
    const activeTasks = db.prepare('SELECT assignee FROM tasks WHERE status = ?').all('in_progress');
    const activeAgents = new Set(activeTasks.map(t => t.assignee));
    
    const agents = ['atlas', 'vega', 'nova', 'pulsar', 'lyra'].map(id => ({
        id,
        status: activeAgents.has(id) ? 'ACTIVE' : 'IDLE'
    }));
    
    res.json({
        tasks: { total, completed, active },
        agents
    });
});

// Living Station page - real-time agent activity
app.get('/station', (req, res) => {
    res.sendFile(path.join(__dirname, 'views', 'station-live.html'));
});

// Old Phaser dashboard (archived)
app.get('/dashboard-phaser', (req, res) => {
    try {
        // Get system stats
        const totalTasks = db.prepare('SELECT COUNT(*) as count FROM tasks').get();
        const doneTasks = db.prepare('SELECT COUNT(*) as count FROM tasks WHERE status = ?').get('done');
        const failedTasks = db.prepare('SELECT COUNT(*) as count FROM tasks WHERE status = ?').get('failed');
        const pendingTasks = db.prepare('SELECT COUNT(*) as count FROM tasks WHERE status = ?').get('pending');
        const inProgressTasks = db.prepare('SELECT COUNT(*) as count FROM tasks WHERE status = ?').get('in_progress');
        
        // Get agent activity
        const agentStats = db.prepare(`
            SELECT 
                assignee,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as active
            FROM tasks
            GROUP BY assignee
        `).all();
        
        // Get recent tasks
        const recentTasks = db.prepare(`
            SELECT id, created_at, assignee, type, status, priority
            FROM tasks
            ORDER BY created_at DESC
            LIMIT 10
        `).all();
        
        // Get latest war room reports
        const { readdirSync, statSync } = require('fs');
        const warRoomPath = '/root/stellar-station/war-room';
        let reports = [];
        try {
            reports = readdirSync(warRoomPath)
                .filter(f => f.endsWith('.md'))
                .map(f => ({
                    name: f,
                    path: path.join(warRoomPath, f),
                    time: statSync(path.join(warRoomPath, f)).mtime
                }))
                .sort((a, b) => b.time - a.time)
                .slice(0, 5);
        } catch (e) {
            // War room empty
        }
        
        res.render('dashboard', {
            stats: {
                total: totalTasks.count,
                done: doneTasks.count,
                failed: failedTasks.count,
                pending: pendingTasks.count,
                in_progress: inProgressTasks.count
            },
            agents: agentStats,
            recentTasks,
            reports
        });
    } catch (error) {
        res.status(500).send(`Error: ${error.message}`);
    }
});

// Task Details
app.get('/task/:id', (req, res) => {
    try {
        const task = db.prepare('SELECT * FROM tasks WHERE id = ?').get(req.params.id);
        
        if (!task) {
            return res.status(404).send('Task not found');
        }
        
        res.render('task', { task });
    } catch (error) {
        res.status(500).send(`Error: ${error.message}`);
    }
});

// Agent Profile
app.get('/agent/:name', (req, res) => {
    try {
        const agentName = req.params.name;
        
        // Read agent identity
        const fs = require('fs');
        const identityPath = `/root/stellar-station/agents/${agentName}/IDENTITY.md`;
        let identity = 'No identity file found';
        if (fs.existsSync(identityPath)) {
            identity = fs.readFileSync(identityPath, 'utf8');
        }
        
        // Get agent tasks
        const tasks = db.prepare(`
            SELECT * FROM tasks 
            WHERE assignee = ? 
            ORDER BY created_at DESC 
            LIMIT 20
        `).all(agentName);
        
        res.render('agent', { 
            name: agentName, 
            identity,
            tasks 
        });
    } catch (error) {
        res.status(500).send(`Error: ${error.message}`);
    }
});

// War Room Report Viewer
app.get('/report/:filename', (req, res) => {
    try {
        const fs = require('fs');
        const reportPath = path.join('/root/stellar-station/war-room', req.params.filename);
        
        if (!fs.existsSync(reportPath)) {
            return res.status(404).send('Report not found');
        }
        
        const content = fs.readFileSync(reportPath, 'utf8');
        res.render('report', { filename: req.params.filename, content });
    } catch (error) {
        res.status(500).send(`Error: ${error.message}`);
    }
});

// API: Get all tasks (JSON)
app.get('/api/tasks', (req, res) => {
    try {
        const tasks = db.prepare('SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100').all();
        res.json(tasks);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API: System health
app.get('/api/health', (req, res) => {
    res.json({
        status: 'operational',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🎮 Stellar Station Mission Control`);
    console.log(`   Dashboard: http://localhost:${PORT}`);
    console.log(`   Theme: Retro Pixel Space Station`);
    console.log(`   Status: ONLINE`);
});
