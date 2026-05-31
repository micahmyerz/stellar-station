# How to Add Room Background Images

## Current Status

The animated mission control is running with **placeholder graphics**:
- 6 colored rooms (Atlas, Vega, Nova, Pulsar, Lyra, War Room)
- Agents shown as colored circles with emoji labels
- Agents walk to the War Room when working on tasks
- Real-time data from task queue

## To Add Custom Room Art

### Option 1: Use DALL-E (You Have ChatGPT Plus)

Generate these 7 images in ChatGPT:

1. **Hero Background**: `Top-down isometric pixel-art space station interior cutaway, 5 distinct rooms visible through transparent hull, rectangular ship layout, pastel purple and cyan nebula starry background, retro Game Boy Color aesthetic, neon pink and blue accents, 16-bit style, wide view --ar 16:9`

2. **Atlas Command Center**: `Top-down pixel-art command center room, holographic tactical display table, glowing cyan screens, captain's chair, strategic maps, soft blue lighting, Game Boy Color palette, retro 16-bit aesthetic --ar 1:1`

3. **Vega Research Lab**: `Top-down pixel-art research laboratory, floating data screens, market trend holographs, glowing green analytics displays, research terminal, Game Boy Color palette, 16-bit aesthetic --ar 1:1`

4. **Nova Marketing Studio**: `Top-down pixel-art marketing studio, neon magenta lighting, ad campaign boards, social media screens, creative workstation, Game Boy Color palette, pink and purple accents, 16-bit aesthetic --ar 1:1`

5. **Pulsar Analytics Bay**: `Top-down pixel-art analytics room, multiple glowing green data visualizations, revenue charts, profit graphs, scrolling numbers, Game Boy Color palette, 16-bit aesthetic --ar 1:1`

6. **Lyra Writing Studio**: `Top-down pixel-art copywriting studio, floating text screens, glowing yellow word processors, creative writing desk, Game Boy Color palette, warm lighting, 16-bit aesthetic --ar 1:1`

7. **War Room**: `Top-down pixel-art war room, circular holographic table in center, tactical screens on walls, team meeting space, cyan and magenta lighting, Game Boy Color palette, 16-bit aesthetic --ar 1:1`

### Upload to VPS

After generating, save and upload to `/root/stellar-station/dashboard/public/rooms/`:

```bash
# From your local computer (Windows PowerShell):
scp hero-bg.png root@2.24.126.194:/root/stellar-station/dashboard/public/rooms/
scp room-atlas.png root@2.24.126.194:/root/stellar-station/dashboard/public/rooms/
scp room-vega.png root@2.24.126.194:/root/stellar-station/dashboard/public/rooms/
scp room-nova.png root@2.24.126.194:/root/stellar-station/dashboard/public/rooms/
scp room-pulsar.png root@2.24.126.194:/root/stellar-station/dashboard/public/rooms/
scp room-lyra.png root@2.24.126.194:/root/stellar-station/dashboard/public/rooms/
scp room-warroom.png root@2.24.126.194:/root/stellar-station/dashboard/public/rooms/
```

Then update `/root/stellar-station/dashboard/public/js/mission-control.js` to load them.

### Option 2: Buy Sprite Pack from itch.io ($3)

For walking agent sprites: https://itch.io/game-assets/tag-character-sprites

Search for "pixel RPG character spritesheet" and buy one with walk cycles.

Upload to `/root/stellar-station/dashboard/public/sprites/`

## Current Behavior

**Without custom art:**
- Colored rectangle rooms with neon borders
- Agents are circles + emoji
- Agents walk between rooms when tasks fire

**With custom art (after upload):**
- Beautiful pixel-art rooms as backgrounds
- Optional: Real sprite characters walking

## Access

**Animated View**: http://2.24.126.194:3000  
**Data View**: http://2.24.126.194:3000/dashboard-simple
