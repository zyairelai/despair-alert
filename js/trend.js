let SYMBOL = localStorage.getItem('globalSymbol') || "BTCUSDT";
let started = false;
let lastBeepInterval = 0;
let beepInterval = 5;
let audioCtx = null;



function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
}


function getHA(klines) {
    if (klines.length < 2) return null;
    let haOpen = (klines[0].open + klines[0].close) / 2;
    let haClose = (klines[0].open + klines[0].high + klines[0].low + klines[0].close) / 4;
    let haHigh = klines[0].high;
    let haLow = klines[0].low;

    for (let i = 1; i < klines.length; i++) {
        const k = klines[i];
        haOpen = (haOpen + haClose) / 2;
        haClose = (k.open + k.high + k.low + k.close) / 4;
        haHigh = Math.max(k.high, haOpen, haClose);
        haLow = Math.min(k.low, haOpen, haClose);
    }
    return { open: haOpen, high: haHigh, low: haLow, close: haClose, color: haClose > haOpen ? "GREEN" : "RED" };
}

async function updateTrend() {
    try {
        const [p1h] = await Promise.all([
            fetchKlines(SYMBOL, "1h")
        ]);

        if (p1h.length < 50) return;

        const ha1h = getHA(p1h);
        if (!ha1h) return;

        const isPerfectGreen = ha1h.color === "GREEN" && ha1h.low >= ha1h.open - (ha1h.open * 0.0001);
        const isPerfectRed = ha1h.color === "RED" && ha1h.high <= ha1h.open + (ha1h.open * 0.0001);

        const trendDisplay = document.getElementById("trendDisplay");
        if (trendDisplay) {
            if (isPerfectGreen) {
                trendDisplay.innerText = "UPTREND";
                trendDisplay.className = "overall-trend trend-up";
            } else if (isPerfectRed) {
                trendDisplay.innerText = "DOWNTREND";
                trendDisplay.className = "overall-trend trend-down";
            } else {
                trendDisplay.innerText = "NO TRADE ZONE";
                trendDisplay.className = "overall-trend trend-neutral";
            }
        }
    } catch (e) {
        console.error("Trend update failed", e);
    }
}

function beep() {
    try {
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume();
        const osc = ctx.createOscillator();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1000, ctx.currentTime);
        osc.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.4);
    } catch (e) {
        console.error("Beep failed:", e);
    }
}

function tick() {
    const now = new Date();
    const nowTime = now.getTime();
    const m = now.getMinutes();
    const s = now.getSeconds();

    // Calculate seconds until next interval mark for display
    const next = beepInterval - (m % beepInterval);
    let r = next * 60 - s;
    if (r === (beepInterval * 60)) r = 0;

    const mStr = String(Math.floor(r / 60)).padStart(2, '0');
    const sStr = String(r % 60).padStart(2, '0');
    document.getElementById("countdown").innerText = `${mStr}:${sStr}`;

    // Robust Beep Logic: Check if we've entered a new interval
    const mInterval = beepInterval * 60 * 1000;
    const currentInterval = Math.floor(nowTime / mInterval);
    if (currentInterval > lastBeepInterval) {
        console.log(`Beeping for ${beepInterval}m interval`, currentInterval, "at", now.toLocaleTimeString());
        beep();
        lastBeepInterval = currentInterval;
    }

    if (s % 3 === 0) updateTrend(); // Update trend every 3s
}

function start() {
    if (started) return;
    started = true;
    document.getElementById("startBtn").disabled = true;
    document.getElementById("startBtn").innerText = "MONITORING ACTIVE";

    const nowTs = Date.now();
    // Initialize to current interval to avoid double-beep on start
    lastBeepInterval = Math.floor(nowTs / (beepInterval * 60 * 1000));

    monitorInterval = setInterval(tick, 1000);
    updateTrend(); // Initial Immediate Update
    tick();

    // Initial check does not beep or alert, just verifies audio
    beep();
}

// Beep logic simplified to always trigger on 5m interval
let monitorInterval = null;


function updateGlobalSymbol() {
    const btn = document.getElementById('global-symbol');
    SYMBOL = btn.innerText;
    localStorage.setItem('globalSymbol', SYMBOL);
    console.log("Global symbol updated to:", SYMBOL);

    // STOP EVERYTHING: Reset monitoring state
    if (monitorInterval) {
        clearInterval(monitorInterval);
        monitorInterval = null;
    }

    started = false;
    const startBtn = document.getElementById("startBtn");
    if (startBtn) {
        startBtn.disabled = false;
        startBtn.innerText = "START MONITORING";
    }

    // FULL UI RESET: Revert elements to initial state
    if (window.updateTitleAndFavicon) window.updateTitleAndFavicon();
    const trendDisplay = document.getElementById("trendDisplay");
    trendDisplay.innerText = "INITIALIZING...";
    trendDisplay.className = "overall-trend trend-neutral";

    document.getElementById("countdown").innerText = "00:00";

    // Reset session markers
    localStorage.removeItem('lastAlertTrend');
    localStorage.removeItem('lastTrendAlertCandle');
    localStorage.removeItem('lastAlertCandle');
}

// Ensure the dropdown matches the stored symbol on load
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('global-symbol');
    if (btn) {
        btn.innerText = SYMBOL;
        btn.classList.add('title-yellow');
    }
});
