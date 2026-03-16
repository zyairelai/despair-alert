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
let beepActive = false;
let beepInterval = null;
let lastBeepTime = 0;

function toggleGlobalBeep() {
    const btn = document.getElementById('beep-start-btn');
    const statusText = document.getElementById('beep-status');
    const indicator = statusText ? statusText.parentElement : null;

    if (beepActive) {
        beepActive = false;
        if (beepInterval) clearInterval(beepInterval);
        beepInterval = null;
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

        // Start the timer
        beepInterval = setInterval(updateBeepTimer, 1000);
        updateBeepTimer();
        beep(); // Immediate feedback on start
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

    // Beep logic
    if ((r === 0 || r === 299) && (nowTime - lastBeepTime > 10000)) {
        console.log("Beeping at", now.toLocaleTimeString());
        beep();
        lastBeepTime = nowTime;
    }
}

function beep() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        if (ctx.state === 'suspended') ctx.resume();
        const osc = ctx.createOscillator();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1000, ctx.currentTime);
        osc.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.3);
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

        window.speechSynthesis.cancel(); // Immediately silence when stopping

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

function testTTS(id) {
    const symbol = document.getElementById('global-symbol').value.replace("USDT", "");
    const isLiquidity = id.startsWith('liquidity');
    const menuId = isLiquidity ? 'liquidity-1-tf-menu' : `${id}-tf-menu`;
    const menuEl = document.getElementById(menuId);
    const tf = menuEl ? menuEl.dataset.value : "5m";
    let text = "";
    let voiceText = "";

    if (id === 'price') {
        text = `🔔 ${symbol} Price Hits Test 🔔`;
        voiceText = `${symbol} price hits test`;
    }
    else if (id === 'ema-cross') {
        const cond = document.getElementById('ema-cross-condition').value;
        const side = cond === 'up' ? 'UP' : 'DOWN';
        const emoji = cond === 'up' ? '🚀' : '💥';
        text = `${emoji} ${symbol} ${tf} EMA CROSS ${side} ${emoji}`;
        voiceText = `${symbol} ${tf} EMA cross test`;
    }
    else if (id === 'heikin') {
        const cond = document.getElementById('heikin-condition').value;
        const color = cond === 'perfect-green' ? 'GREEN' : 'RED';
        const emoji = cond === 'perfect-green' ? '🚀' : '💥';
        text = `${emoji} ${symbol} ${tf} HEIKIN ASHI ${color} ${emoji}`;
        voiceText = `${symbol} ${tf} HEIKIN ASHI turned into ${color.toLowerCase()} color`;
    }
    else if (id === 'standing') {
        const cond = document.getElementById('standing-condition').value;
        const level = document.getElementById('standing-level').value;
        const side = cond === 'above' ? 'ABOVE' : 'BELOW';
        const emoji = cond === 'above' ? '🚀' : '💥';
        text = `${emoji} ${symbol} ${tf} STAND ${side} ${level}EMA ${emoji}`;
        voiceText = `${symbol} EMA STAND alert test`;
    }
    else if (id === 'line-touch') {
        const level = document.getElementById('line-touch-price').value;
        text = `🔔 ${symbol} ${tf} TOUCH ${level}EMA 🔔`;
        voiceText = `${symbol} EMA TOUCH alert test`;
    }
    else if (id === 'liquidity') {
        text = `🩸 ${symbol} ${tf} LIQUIDITY HUNT 🩸`;
        voiceText = `${symbol} ${tf} LIQUIDITY HUNT ACTIVATED`;
    }

    if (!voiceText) voiceText = text;

    // Prefix for both Telegram and Speech
    const finalTlg = `TEST MESSAGE\n${text}`;
    const finalVoice = `TEST MESSAGE. ${voiceText}`;

    speak(finalVoice);

    // Also send Telegram for every test as requested
    const wolvesRiseIds = ['ema-cross', 'standing', 'line-touch', 'heikin'];
    const telegramChatId = wolvesRiseIds.includes(id) ? "@futures_wolves_rise" : null;
    sendTelegramAlert(finalTlg, telegramChatId);
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
updateGlobalSymbol();

// Init all selects for color-coded mode
document.querySelectorAll('select').forEach(sel => {
    if (sel.id !== 'global-symbol') {
        updateSelectColor(sel);
    }
});
