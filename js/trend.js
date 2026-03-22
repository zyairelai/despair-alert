let SYMBOL = localStorage.getItem('globalSymbol') || "BTCUSDT";
let started = false;
let sessionStarted = true;
let lastBeepInterval = 0;
let beepMode = 'interval';
let monitoringStartTime = 0;
let audioCtx = null;

function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
}

async function fetchKlines(interval) {
    const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${SYMBOL}&interval=${interval}&limit=200`;
    const resp = await fetch(url);
    const data = await resp.json();
    return data.map(d => ({
        timestamp: d[0],
        open: parseFloat(d[1]),
        high: parseFloat(d[2]),
        low: parseFloat(d[3]),
        close: parseFloat(d[4])
    }));
}

function isShootingStar(klines) {
    if (klines.length < 3) return false;
    const c1 = klines[klines.length - 2]; // Previous candle
    const c2 = klines[klines.length - 3]; // Candle before previous

    // Red Candle Condition
    if (c1.close >= c1.open) return false;

    const body1 = Math.abs(c1.open - c1.close);
    const upperWick1 = c1.high - Math.max(c1.open, c1.close);
    const lowerWick1 = Math.min(c1.open, c1.close) - c1.low;

    const body2 = Math.abs(c2.open - c2.close);
    const upperWick2 = c2.high - Math.max(c2.open, c2.close);
    const lowerWick2 = Math.min(c2.open, c2.close) - c2.low;

    const cond1 = upperWick1 > (lowerWick1 + body1);
    // Condition 2: Upper wick of current candle must be larger than each component of the previous candle INDIVIDUALLY
    const cond2 = upperWick1 > upperWick2 && upperWick1 > body2 && upperWick1 > lowerWick2;

    return cond1 && cond2;
}

async function updateTrend() {
    try {
        const [p1h, p15m, p5m] = await Promise.all([
            fetchKlines("1h"),
            fetchKlines("15m"),
            fetchKlines("5m")
        ]);

        // Emergency 1h Logic: Current high > previous high AND current 1h candle is RED
        const cur1h = p1h[p1h.length - 1];
        const prev1h = p1h[p1h.length - 2];
        const isEmergency = cur1h.high > prev1h.high && cur1h.close < cur1h.open;

        const trendDisplay = document.getElementById("trendDisplay");

        if (isEmergency) {
            trendDisplay.innerText = "EMERGENCY DOWNTREND";
            trendDisplay.className = "overall-trend trend-down";
        } else {
            trendDisplay.innerText = "MONITORING...";
            trendDisplay.className = "overall-trend trend-neutral";
        }

        checkAndSendAlert(p1h, p15m, p5m, isEmergency);
    } catch (e) {
        console.error("Trend update failed", e);
    }
}

function updateFavicon(path) {
    let link = document.getElementById('favicon') || document.querySelector("link[rel~='icon']");
    if (!link) {
        link = document.createElement('link');
        link.id = 'favicon';
        link.rel = 'icon';
        document.getElementsByTagName('head')[0].appendChild(link);
    }
    link.href = path;
}


function checkAndSendAlert(p1h, p15m, p5m, isEmergency = false) {
    const lastEmergencyHour = localStorage.getItem('lastEmergencyHour');
    const lastShootingStarHour = localStorage.getItem('lastShootingStarHour');

    const now = new Date();
    const currentHourTs = Math.floor(now.getTime() / (3600 * 1000)) * (3600 * 1000);
    const isNewEmergencyHour = !lastEmergencyHour || currentHourTs > parseInt(lastEmergencyHour);

    // Cooldown reset check: New hour AND at least 30 seconds in
    const isAfter30s = now.getMinutes() > 0 || now.getSeconds() >= 30;
    const isNewShootingStarHour = (!lastShootingStarHour || currentHourTs > parseInt(lastShootingStarHour)) && isAfter30s;

    // 0. Skip if monitoring started less than 1 minute ago
    if (Date.now() - monitoringStartTime < 60000) {
        return;
    }

    // 1. Emergency Case: 1H Breakdown
    if (isEmergency && isNewEmergencyHour) {
        const symbolShort = SYMBOL.replace("USDT", "");
        const msg = `🩸 ${symbolShort} 1H EMERGENCY BREAKDOWN 🩸`;

        sendTelegramAlert(msg);
        speak(`${symbolShort} 1 hour emergency breakdown.`);

        localStorage.setItem('lastEmergencyHour', currentHourTs.toString());
        sessionStarted = true;
        return;
    }

    // 2. Shooting Star Case: 1H or 15m
    if (isNewShootingStarHour) {
        const ss1h = isShootingStar(p1h);
        const ss15m = isShootingStar(p15m);

        if (ss1h || ss15m) {
            const ssTf = ss1h ? "1H" : "15m";
            const symbolShort = SYMBOL.replace("USDT", "");
            const emoji = "🌠";
            const msg = `${emoji} ${symbolShort} ${ssTf} SHOOTING STAR ${emoji}`;

            sendTelegramAlert(msg);
            speak(`${symbolShort} ${ssTf} shooting star detected.`);

            localStorage.setItem('lastShootingStarHour', currentHourTs.toString());
        }
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

    // Calculate seconds until next 5m mark for display
    const next = 5 - (m % 5);
    let r = next * 60 - s;
    if (r === 300) r = 0;

    const mStr = String(Math.floor(r / 60)).padStart(2, '0');
    const sStr = String(r % 60).padStart(2, '0');
    document.getElementById("countdown").innerText = `${mStr}:${sStr}`;

    // Robust Beep Logic: Check if we've entered a new 5-minute interval
    // This is more reliable than checking exact seconds (r === 0) 
    // which can be missed if the browser throttles background tabs.
    const currentInterval = Math.floor(nowTime / (5 * 60 * 1000));
    if (currentInterval > lastBeepInterval) {
        const trendText = document.getElementById("trendDisplay").innerText;
        const isNoTrade = trendText === "NO TRADE ZONE";

        if (beepMode === 'interval' || (beepMode === 'trend' && !isNoTrade)) {
            console.log("Beeping for interval", currentInterval, "at", now.toLocaleTimeString());
            beep();
        }
        lastBeepInterval = currentInterval;
    }

    if (s % 3 === 0) updateTrend(); // Update trend every 3s
}

function start() {
    if (started) return;
    started = true;
    document.getElementById("startBtn").disabled = true;
    document.getElementById("startBtn").innerText = "MONITORING ACTIVE";
    monitoringStartTime = Date.now();

    // Initialize to current interval to avoid double-beep on start
    lastBeepInterval = Math.floor(Date.now() / (5 * 60 * 1000));

    monitorInterval = setInterval(tick, 1000);
    tick();
    updateTrend();

    // Initial check does not beep or alert, just verifies audio
    beep();
}

function setBeepMode(mode) {
    beepMode = mode;
    document.getElementById('beepInterval').classList.toggle('active', mode === 'interval');
    document.getElementById('beepTrend').classList.toggle('active', mode === 'trend');
    console.log("Beep mode set to:", mode);
}
let monitorInterval = null;

function toggleGlobalSymbol() {
    // const btn = document.getElementById('global-symbol');
    // if (!btn) return;

    // const currentSymbol = btn.innerText;
    // const nextSymbol = currentSymbol === 'BTCUSDT' ? 'ETHUSDT' : 'BTCUSDT';

    // btn.innerText = nextSymbol;
    // updateGlobalSymbol();
    console.log("Symbol toggle disabled (static BTC)");
}

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
    const trendDisplay = document.getElementById("trendDisplay");
    trendDisplay.innerText = "INITIALIZING...";
    trendDisplay.className = "overall-trend trend-neutral";

    document.getElementById("countdown").innerText = "00:00";

    // Reset session markers
    localStorage.removeItem('lastAlertTrend');
    localStorage.removeItem('lastAlertCandle');
    localStorage.removeItem('lastEmergencyHour');
}

// Ensure the dropdown matches the stored symbol on load
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('global-symbol');
    if (btn) {
        btn.innerText = SYMBOL;
    }
});
