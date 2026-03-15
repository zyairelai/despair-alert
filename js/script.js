let SYMBOL = localStorage.getItem('globalSymbol') || "BTCUSDT";
let started = false;
let sessionStarted = false;
let lastBeepTime = 0; // Prevent duplicate beeps in the same second
let beepMode = 'interval';

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

function calculateEMA(candles, period) {
    const prices = candles.map(c => c.close);
    const k = 2 / (period + 1);
    let ema = prices[0];
    for (let i = 1; i < prices.length; i++) {
        ema = (prices[i] * k) + (ema * (1 - k));
    }
    return ema;
}

function getEMAs(candles) {
    return {
        ema10: calculateEMA(candles, 10),
        ema20: calculateEMA(candles, 20),
        ema50: calculateEMA(candles, 50)
    };
}

async function updateTrend() {
    try {
        const [p1h, p15m, p5m] = await Promise.all([fetchKlines("1h"), fetchKlines("15m"), fetchKlines("5m")]);

        // Emergency 1h Logic: Current high > previous high AND current 1h candle is RED
        const cur1h = p1h[p1h.length - 1];
        const prev1h = p1h[p1h.length - 2];
        const isEmergency = cur1h.high > prev1h.high && cur1h.close < cur1h.open;

        // 15m (HTF): Previous close (-2) vs 20 EMA
        const p15mPrev = p15m.slice(0, -1);
        const e15mPrev = getEMAs(p15mPrev);
        const prevClose15m = p15m[p15m.length - 2].close;

        const htfUp = e15mPrev.ema20 > e15mPrev.ema50 && prevClose15m > e15mPrev.ema50;
        const htfDown = prevClose15m < e15mPrev.ema20;

        // 5m (LTF): Remain 10/20 crossing for down, 10/20/50 for up
        const e5m = getEMAs(p5m);
        const ltfUp = e5m.ema10 > e5m.ema20 && e5m.ema20 > e5m.ema50;
        const ltfDown = e5m.ema10 < e5m.ema20;

        let currentTrend = "NO TRADE ZONE";
        if (isEmergency) currentTrend = "DOWNTREND";
        else if (htfUp && ltfUp) currentTrend = "UPTREND";
        else if (htfDown && ltfDown) currentTrend = "DOWNTREND";


        const htfStatus = document.getElementById("htfStatus");
        const ltfStatus = document.getElementById("ltfStatus");
        const trendDisplay = document.getElementById("trendDisplay");

        htfStatus.innerText = htfUp ? 'UP' : (htfDown ? 'DOWN' : 'NEUTRAL');
        document.getElementById("htfRow").className = `status-row ${htfUp ? 'status-up' : (htfDown ? 'status-down' : 'status-neutral')}`;

        ltfStatus.innerText = ltfUp ? 'UP' : (ltfDown ? 'DOWN' : 'NEUTRAL');
        document.getElementById("ltfRow").className = `status-row ${ltfUp ? 'status-up' : (ltfDown ? 'status-down' : 'status-neutral')}`;

        if (currentTrend === "UPTREND") {
            trendDisplay.innerText = "CURRENTLY UPTREND";
            trendDisplay.className = "overall-trend trend-up";
            updateFavicon("images/favicon_green.png");
        } else if (currentTrend === "DOWNTREND") {
            trendDisplay.innerText = isEmergency ? "EMERGENCY DOWNTREND" : "CURRENTLY DOWNTREND";
            trendDisplay.className = "overall-trend trend-down";
            updateFavicon("images/favicon_red.png");
        } else {
            trendDisplay.innerText = "NO TRADE ZONE";
            trendDisplay.className = "overall-trend trend-neutral";
            updateFavicon("images/favicon_yellow.png");
        }

        checkAndSendAlert(currentTrend, isEmergency);
    } catch (e) {
        console.error("Trend update failed", e);
    }
}

function updateFavicon(path) {
    let link = document.querySelector("link[rel~='icon']");
    if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.getElementsByTagName('head')[0].appendChild(link);
    }
    link.href = path;
}


function checkAndSendAlert(currentTrend, isEmergency = false) {
    const lastAlertTrend = localStorage.getItem('lastAlertTrend');
    const lastAlertCandle = localStorage.getItem('lastAlertCandle');
    const lastEmergencyHour = localStorage.getItem('lastEmergencyHour');

    const now = new Date();
    const current15mTs = Math.floor(now.getTime() / (15 * 60 * 1000)) * (15 * 60 * 1000);
    const currentHourTs = Math.floor(now.getTime() / (60 * 60 * 1000)) * (60 * 60 * 1000);

    const isNewCandle = !lastAlertCandle || current15mTs > parseInt(lastAlertCandle);
    const isNewEmergencyHour = !lastEmergencyHour || currentHourTs > parseInt(lastEmergencyHour);

    // Global Lock: If an emergency alert was sent this hour, all Telegram alerts are muted until next hour resets it
    if (!isNewEmergencyHour) return;

    // 1. Emergency Case: Bypass 15m rule
    if (isEmergency) {
        const symbolShort = SYMBOL.replace("USDT", "");
        const msg = `🚨 ${symbolShort} 1H EMERGENCY DOWNTREND 🚨`;

        // Always send Telegram for emergencies
        sendTelegramAlert(msg);
        speak(`${symbolShort} 1 hour emergency breakdown. ${symbolShort} 1 hour emergency breakdown.`);

        localStorage.setItem('lastEmergencyHour', currentHourTs.toString());
        localStorage.setItem('lastAlertTrend', "DOWNTREND");
        localStorage.setItem('lastAlertCandle', current15mTs.toString());
        sessionStarted = true;
        return;
    }

    // 2. Standard Case: Once per 15m candle on trend change
    if (isNewCandle && currentTrend !== lastAlertTrend) {
        if (lastAlertTrend !== null) {
            let emoji = "";
            if (currentTrend === "UPTREND") emoji = "🚀";
            else if (currentTrend === "DOWNTREND") emoji = "💥";
            else if (currentTrend === "NO TRADE ZONE") emoji = "⏳";

            const symbolShort = SYMBOL.replace("USDT", "");
            const msg = `${emoji} ${symbolShort} Trend: ${currentTrend} ${emoji}`;

            if (sessionStarted) {
                sendTelegramAlert(msg);
            }
        }

        localStorage.setItem('lastAlertTrend', currentTrend);
        localStorage.setItem('lastAlertCandle', current15mTs.toString());
        sessionStarted = true;
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

function tick() {
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
    document.getElementById("countdown").innerText = `${mStr}:${sStr}`;

    // Triple-check for beep
    // 1. Should be exactly at the 5-minute mark (r === 0)
    // 2. Or if we just passed it (r === 299) and haven't beeped in the last 10 seconds
    if ((r === 0 || r === 299) && (nowTime - lastBeepTime > 10000)) {
        const trendText = document.getElementById("trendDisplay").innerText;
        const isNoTrade = trendText === "NO TRADE ZONE";

        if (beepMode === 'interval' || (beepMode === 'trend' && !isNoTrade)) {
            console.log("Beeping at", now.toLocaleTimeString());
            beep();
            lastBeepTime = nowTime;
        }
    }

    if (s % 3 === 0) updateTrend(); // Update trend every 3s
}

function start() {
    if (started) return;
    started = true;
    document.getElementById("startBtn").disabled = true;
    document.getElementById("startBtn").innerText = "MONITORING ACTIVE";
    monitorInterval = setInterval(tick, 1000);
    tick();
    updateTrend();

    // Initial check does not beep or alert, just verifies audio
    beep();
    lastBeepTime = new Date().getTime();
}

function setBeepMode(mode) {
    beepMode = mode;
    document.getElementById('beepInterval').classList.toggle('active', mode === 'interval');
    document.getElementById('beepTrend').classList.toggle('active', mode === 'trend');
    console.log("Beep mode set to:", mode);
}
let monitorInterval = null;

function updateGlobalSymbol() {
    const selector = document.getElementById('global-symbol');
    SYMBOL = selector.value;
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
    document.getElementById("htfStatus").innerText = "LOADING...";
    document.getElementById("ltfStatus").innerText = "LOADING...";
    document.getElementById("htfRow").className = "status-row status-neutral";
    document.getElementById("ltfRow").className = "status-row status-neutral";

    const trendDisplay = document.getElementById("trendDisplay");
    trendDisplay.innerText = "INITIALIZING...";
    trendDisplay.className = "overall-trend trend-neutral";

    document.getElementById("countdown").innerText = "00:00";

    // Reset session markers
    localStorage.removeItem('lastAlertTrend');
    localStorage.removeItem('lastAlertCandle');
    localStorage.removeItem('lastEmergencyHour');

    // Reset favicon to yellow/neutral
    updateFavicon("images/favicon_yellow.png");
}

// Ensure the dropdown matches the stored symbol on load
document.addEventListener('DOMContentLoaded', () => {
    const selector = document.getElementById('global-symbol');
    if (selector) {
        selector.value = SYMBOL;
    }
});
