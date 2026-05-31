// Stellar Station Dashboard - Retro Effects

// Auto-refresh every 10 seconds
setTimeout(() => {
    location.reload();
}, 10000);

// Add scanline effect
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎮 Stellar Station Dashboard Loaded');
    console.log('   Theme: Retro Pixel Space');
    console.log('   Status: ONLINE');
});

// Random CRT flicker effect
setInterval(() => {
    const crt = document.querySelector('.crt');
    if (crt && Math.random() < 0.05) {
        crt.style.opacity = '0.95';
        setTimeout(() => {
            crt.style.opacity = '1';
        }, 50);
    }
}, 2000);
