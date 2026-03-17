const alerts = {
    price: { active: false, interval: null, lastTriggerCandleTime: null },
    'ema-cross': { active: false, interval: null },
    heikin: { active: false, interval: null },
    standing: { active: false, interval: null },
    'line-touch': { active: false, interval: null },
    liquidity: { active: false, interval: null }
};

let lastAlertMessages = {};
let lastAlertTimes = {};

// Global Beep State
// Global Beep State
let beepActive = false;
let beepInterval = null;
let lastBeepTime = 0;
// Audio Singleton
let audioCtx = null;
function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
}

function toggleGlobalBeep() {
    const btn = document.getElementById('beep-start-btn');
    const statusText = document.getElementById('beep-status');
    const indicator = statusText ? statusText.parentElement : null;

    if (beepActive) {
        beepActive = false;
        if (beepInterval) clearInterval(beepInterval);
        beepInterval = null;
        clearSpeechQueue(); // Cancel any pending alert speech
        btn.innerText = "BEEP";
        btn.classList.remove('active');
        if (indicator) {
            indicator.classList.remove('monitoring');
            indicator.classList.add('inactive');
        }
        if (statusText) statusText.innerText = "INACTIVE";
        document.getElementById('beep-countdown').innerText = "00:00";
    } else {
        beepActive = true;
        btn.innerText = "STOP";
        btn.classList.add('active');
        if (indicator) {
            indicator.classList.remove('inactive');
            indicator.classList.add('monitoring');
        }
        if (statusText) statusText.innerText = "MONITORING";

        // Initialize/Resume Audio Context on user gesture
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume();

        // Start the timer
        beepInterval = setInterval(updateBeepTimer, 1000);
        updateBeepTimer();

        // Manual beep and sync timestamp
        beep();
        lastBeepTime = Date.now();
    }
}

function updateBeepTimer() {
    const now = new Date();
    const nowTime = now.getTime();
    const m = now.getMinutes();
    const s = now.getSeconds();

    // Calculate seconds until next 5m mark
    const next = 5 - (m % 5);
    let r = next * 60 - s;
    if (r === 300) r = 0;

    const mStr = String(Math.floor(r / 60)).padStart(2, '0');
    const sStr = String(r % 60).padStart(2, '0');
    const display = document.getElementById("beep-countdown");
    if (display) display.innerText = `${mStr}:${sStr}`;

    // Beep logic: Beep at 00:00 (r=0) or 04:59 (r=299)
    if ((r === 0 || r === 299) && (nowTime - lastBeepTime > 10000)) {
        console.log("Global Beep triggered at", now.toLocaleTimeString());
        beep();
        lastBeepTime = nowTime;
    }
}

function beep() {
    try {
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume().catch(e => console.warn("Context resume failed:", e));

        const osc = ctx.createOscillator();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1000, ctx.currentTime);
        osc.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.3);
        console.log("Global beep triggered (Perfect BEEP logic).");
    } catch (e) {
        console.error("Beep failed:", e);
    }
}

function testBeep() {
    console.log("Testing beep...");
    beep();
}

function toggleAlert(id) {
    const alert = alerts[id];
    const card = document.getElementById(`${id}-card`);
    if (!card) return;
    const btn = card.querySelector('.toggle-btn');
    const statusText = document.getElementById(`${id}-status`);
    const indicator = statusText.parentElement;

    if (alert.active || btn.innerText === "STOP") {
        console.log(`Stopping ${id}`);
        alert.active = false;
        if (alert.interval) clearInterval(alert.interval);
        alert.interval = null;

        clearSpeechQueue(); // Immediately silence when stopping
        if (alert.uiBackupTimeout) clearTimeout(alert.uiBackupTimeout);

        btn.innerText = "START";
        btn.classList.remove('active');

        // Revert title color
        const title = card.querySelector('.card-header h2');
        if (title) title.classList.remove('running-title');

        indicator.classList.remove('monitoring', 'triggered');
        indicator.classList.add('inactive');
        statusText.innerText = "INACTIVE";
    } else {
        console.log(`Starting ${id}`);
        delete lastAlertMessages[id];
        delete lastAlertTimes[id];
        if (id === 'price') alert.lastTriggerCandleTime = null;

        alert.active = true;
        btn.innerText = "STOP";
        btn.classList.add('active');

        // Make title red
        const title = card.querySelector('.card-header h2');
        if (title) title.classList.add('running-title');

        indicator.classList.remove('inactive', 'triggered');
        indicator.classList.add('monitoring');
        statusText.innerText = "MONITORING";

        checkAlert(id);
        alert.interval = setInterval(() => checkAlert(id), 5000);
    }
}


// Global click listener to close TF menus
document.addEventListener('click', (e) => {
    if (!e.target.closest('.tf-selector')) {
        document.querySelectorAll('.tf-dropdown-menu').forEach(menu => {
            menu.classList.remove('show');
        });
        document.querySelectorAll('.alert-card').forEach(card => {
            card.classList.remove('z-active');
        });
    }
});

// Initialize
window.speechSynthesis.onvoiceschanged = () => {
    console.log("Voices loaded");
};

// Start logic
document.addEventListener('DOMContentLoaded', () => {
    const symbolBtn = document.getElementById('global-symbol');
    const storedSymbol = localStorage.getItem('globalSymbol') || 'BTCUSDT';
    if (symbolBtn) symbolBtn.innerText = storedSymbol;
});
updateGlobalSymbol();

// Init all condition elements for color-coded mode
document.querySelectorAll('select, .condition-toggle').forEach(el => {
    if (el.id !== 'global-symbol') {
        updateConditionUI(el);
    }
});
