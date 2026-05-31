// Stellar Station Mission Control - Phaser-powered Animated Dashboard
// Agents walk between rooms, rooms glow when active, visual task tracking

const config = {
    type: Phaser.AUTO,
    width: 1920,
    height: 1080,
    parent: 'game-container',
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 0 },
            debug: false
        }
    },
    scene: {
        preload: preload,
        create: create,
        update: update
    },
    backgroundColor: '#0f0f23'
};

const game = new Phaser.Game(config);

// Room layout (aligned to hero-bg.png actual room positions)
const ROOMS = {
    atlas: { x: 210, y: 120, w: 360, h: 270, color: 0x00ffcc, name: 'ATLAS COMMAND' },
    vega: { x: 610, y: 120, w: 360, h: 270, color: 0x0066ff, name: 'VEGA RESEARCH LAB' },
    nova: { x: 1010, y: 120, w: 360, h: 270, color: 0xff00ff, name: 'NOVA MARKETING' },
    pulsar: { x: 210, y: 450, w: 360, h: 280, color: 0x00ff00, name: 'PULSAR ANALYTICS' },
    lyra: { x: 610, y: 450, w: 360, h: 280, color: 0xffff00, name: 'LYRA COPYWRITING' },
    warroom: { x: 1010, y: 450, w: 360, h: 280, color: 0xff3366, name: 'WAR ROOM' }
};

let agents = {};
let roomGraphics = {};
let roomLabels = {};
let currentHoveredRoom = null;

function preload() {
    // Load DALL-E generated room backgrounds
    this.load.image('hero-bg', '/rooms/hero-bg.png');
    this.load.image('room-atlas', '/rooms/room-atlas.png');
    this.load.image('room-vega', '/rooms/room-vega.png');
    this.load.image('room-nova', '/rooms/room-nova.png');
    this.load.image('room-pulsar', '/rooms/room-pulsar.png');
    this.load.image('room-lyra', '/rooms/room-lyra.png');
    this.load.image('room-warroom', '/rooms/room-warroom.png');
    
    // Error handling
    this.load.on('loaderror', function(file) {
        console.error('Error loading file:', file.key, file.src);
    });
    
    this.load.on('complete', function() {
        console.log('All assets loaded successfully');
    });
}

function create() {
    const scene = this;
    
    // Hero background (main station) - make it prominent
    const heroBg = scene.add.image(960, 540, 'hero-bg');
    heroBg.setDisplaySize(1920, 1080);
    heroBg.setDepth(0); // Behind everything
    
    // Add stars on top
    for (let i = 0; i < 200; i++) {
        const x = Phaser.Math.Between(0, 1920);
        const y = Phaser.Math.Between(0, 1080);
        const star = scene.add.circle(x, y, 1, 0xffffff, Phaser.Math.FloatBetween(0.3, 1));
        scene.tweens.add({
            targets: star,
            alpha: 0.2,
            duration: Phaser.Math.Between(1000, 3000),
            yoyo: true,
            repeat: -1
        });
    }
    
    // Draw minimal room markers (just for agent targeting, invisible)
    Object.keys(ROOMS).forEach(roomId => {
        const room = ROOMS[roomId];
        
        // No visible graphics - rooms are shown in hero background
        const graphics = scene.add.graphics();
        roomGraphics[roomId] = graphics;
        
        // Room label
        const label = scene.add.text(
            room.x + room.w / 2,
            room.y + 30,
            room.name,
            {
                fontSize: '16px',
                fontFamily: '"Press Start 2P", monospace',
                color: '#' + room.color.toString(16).padStart(6, '0'),
                align: 'center'
            }
        ).setOrigin(0.5);
        
        roomLabels[roomId] = label;
        
        // Make rooms interactive
        const zone = scene.add.zone(room.x, room.y, room.w, room.h).setOrigin(0).setInteractive();
        zone.on('pointerover', () => showRoomInfo(roomId));
        zone.on('pointerout', () => hideRoomInfo());
    });
    
    // Create agent sprites (simple colored circles for now - replace with spritesheets later)
    const agentData = {
        atlas: { room: 'atlas', color: 0x00ffcc, emoji: '🌍' },
        vega: { room: 'vega', color: 0x0066ff, emoji: '⭐' },
        nova: { room: 'nova', color: 0xff00ff, emoji: '💫' },
        pulsar: { room: 'pulsar', color: 0x00ff00, emoji: '📊' },
        lyra: { room: 'lyra', color: 0xffff00, emoji: '✨' }
    };
    
    Object.keys(agentData).forEach(agentId => {
        const data = agentData[agentId];
        const room = ROOMS[data.room];
        
        // Agent sprite (circle placeholder with glow)
        const sprite = scene.add.circle(
            room.x + room.w / 2,
            room.y + room.h / 2,
            25,
            data.color
        );
        sprite.setDepth(10); // Agents on top of everything
        sprite.setStrokeStyle(3, 0xffffff, 1); // White border for visibility
        
        // Glow effect
        const glow = scene.add.circle(
            room.x + room.w / 2,
            room.y + room.h / 2,
            30,
            data.color,
            0.3
        );
        glow.setDepth(9);
        
        // Agent emoji label (bigger and with shadow)
        const label = scene.add.text(
            sprite.x,
            sprite.y - 50,
            data.emoji,
            { 
                fontSize: '32px',
                stroke: '#000000',
                strokeThickness: 4
            }
        ).setOrigin(0.5);
        label.setDepth(10); // Labels on top too
        
        agents[agentId] = {
            sprite: sprite,
            glow: glow,
            label: label,
            currentRoom: data.room,
            targetRoom: null,
            isMoving: false,
            color: data.color,
            emoji: data.emoji
        };
        
        // Idle animation (subtle bounce)
        scene.tweens.add({
            targets: [sprite, glow, label],
            y: sprite.y - 8,
            duration: 1500,
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut'
        });
        
        // Pulse glow
        scene.tweens.add({
            targets: glow,
            alpha: 0.6,
            duration: 2000,
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut'
        });
    });
    
    // Fetch live data and update
    fetchSystemData(scene);
    
    // Update every 5 seconds
    scene.time.addEvent({
        delay: 5000,
        callback: () => fetchSystemData(scene),
        loop: true
    });
}

function update() {
    // Handle agent movement
    Object.keys(agents).forEach(agentId => {
        const agent = agents[agentId];
        
        if (agent.isMoving && agent.targetRoom) {
            const target = ROOMS[agent.targetRoom];
            const targetX = target.x + target.w / 2;
            const targetY = target.y + target.h / 2;
            
            const dx = targetX - agent.sprite.x;
            const dy = targetY - agent.sprite.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance < 5) {
                // Arrived
                agent.isMoving = false;
                agent.currentRoom = agent.targetRoom;
                agent.targetRoom = null;
            } else {
                // Move towards target
                const speed = 2;
                agent.sprite.x += (dx / distance) * speed;
                agent.sprite.y += (dy / distance) * speed;
                agent.glow.x = agent.sprite.x;
                agent.glow.y = agent.sprite.y;
                agent.label.x = agent.sprite.x;
                agent.label.y = agent.sprite.y - 50;
            }
        }
    });
}

function createStarfield(scene) {
    const graphics = scene.make.graphics({ x: 0, y: 0, add: false });
    graphics.fillStyle(0xffffff);
    
    for (let i = 0; i < 100; i++) {
        const x = Phaser.Math.Between(0, 1920);
        const y = Phaser.Math.Between(0, 1080);
        graphics.fillCircle(x, y, 1);
    }
    
    graphics.generateTexture('bg-space', 1920, 1080);
    graphics.destroy();
    return 'bg-space';
}

function moveAgentToRoom(agentId, roomId) {
    const agent = agents[agentId];
    if (agent && roomId && ROOMS[roomId] && agent.currentRoom !== roomId) {
        agent.targetRoom = roomId;
        agent.isMoving = true;
    }
}

function pulseRoom(roomId) {
    const graphics = roomGraphics[roomId];
    const room = ROOMS[roomId];
    
    if (graphics && room) {
        game.scene.scenes[0].tweens.add({
            targets: graphics,
            alpha: 0.5,
            duration: 500,
            yoyo: true,
            repeat: 2
        });
    }
}

function showRoomInfo(roomId) {
    const room = ROOMS[roomId];
    const info = document.getElementById('room-info');
    info.textContent = room.name;
    info.style.display = 'block';
    currentHoveredRoom = roomId;
}

function hideRoomInfo() {
    const info = document.getElementById('room-info');
    info.style.display = 'none';
    currentHoveredRoom = null;
}

async function fetchSystemData(scene) {
    try {
        // Fetch tasks from API
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        
        // Update stats overlay
        document.getElementById('task-total').textContent = tasks.length;
        document.getElementById('task-done').textContent = tasks.filter(t => t.status === 'done').length;
        document.getElementById('task-active').textContent = tasks.filter(t => t.status === 'in_progress').length;
        
        // Update agent statuses
        const agentTasks = {
            atlas: tasks.filter(t => t.assignee === 'atlas' && t.status === 'in_progress'),
            vega: tasks.filter(t => t.assignee === 'vega' && t.status === 'in_progress'),
            nova: tasks.filter(t => t.assignee === 'nova' && t.status === 'in_progress'),
            pulsar: tasks.filter(t => t.assignee === 'pulsar' && t.status === 'in_progress'),
            lyra: tasks.filter(t => t.assignee === 'lyra' && t.status === 'in_progress')
        };
        
        Object.keys(agentTasks).forEach(agentId => {
            const statusEl = document.getElementById(`status-${agentId}`);
            const isActive = agentTasks[agentId].length > 0;
            
            if (isActive) {
                statusEl.innerHTML = statusEl.innerHTML.split(':')[0] + ': <span class="status-active">● ACTIVE</span>';
                // Move agent to war room when working
                moveAgentToRoom(agentId, 'warroom');
                pulseRoom('warroom');
            } else {
                statusEl.innerHTML = statusEl.innerHTML.split(':')[0] + ': <span class="status-idle">○ IDLE</span>';
                // Return agent to home room
                moveAgentToRoom(agentId, agentId);
            }
        });
        
    } catch (error) {
        console.error('Error fetching system data:', error);
    }
}
