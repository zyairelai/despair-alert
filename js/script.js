let SYMBOL = localStorage.getItem('globalSymbol') || "BTCUSDT";
let started = false;
let sessionStarted = true;
let lastBeepTime = 0; // Prevent duplicate beeps in the same second
let beepMode = 'interval';
let monitoringStartTime = 0;

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
        ema20: calculateEMA(candles, 20)
    };
}

async function updateTrend() {
    try {
        const [p1h, p5m] = await Promise.all([fetchKlines("1h"), fetchKlines("5m")]);

        // Emergency 1h Logic: Current high > previous high AND current 1h candle is RED
        const cur1h = p1h[p1h.length - 1];
        const prev1h = p1h[p1h.length - 2];
        const isEmergency = cur1h.high > prev1h.high && cur1h.close < cur1h.open;

        // 5m (LTF): 10/20 EMA crossing
        const e5m = getEMAs(p5m);
        const ltfUp = e5m.ema10 > e5m.ema20;
        const ltfDown = e5m.ema10 < e5m.ema20;

        let currentTrend = "NO TRADE ZONE";
        if (isEmergency) currentTrend = "DOWNTREND";
        else if (ltfUp) currentTrend = "UPTREND";
        else if (ltfDown) currentTrend = "DOWNTREND";


        const ltfStatus = document.getElementById("ltfStatus");
        const trendDisplay = document.getElementById("trendDisplay");

        ltfStatus.innerText = ltfUp ? 'UP' : (ltfDown ? 'DOWN' : 'NEUTRAL');
        document.getElementById("ltfRow").className = `status-row ${ltfUp ? 'status-up' : (ltfDown ? 'status-down' : 'status-neutral')}`;

        const symbolBtn = document.getElementById("global-symbol");

        if (currentTrend === "UPTREND") {
            trendDisplay.innerText = "CURRENTLY UPTREND";
            trendDisplay.className = "overall-trend trend-up";
            if (symbolBtn) {
                symbolBtn.classList.add("title-green");
                symbolBtn.classList.remove("title-red", "title-doji");
            }
            updateFavicon("images/favicon_green.png");
        } else if (currentTrend === "DOWNTREND") {
            trendDisplay.innerText = isEmergency ? "EMERGENCY DOWNTREND" : "CURRENTLY DOWNTREND";
            trendDisplay.className = "overall-trend trend-down";
            if (symbolBtn) {
                symbolBtn.classList.add("title-red");
                symbolBtn.classList.remove("title-green", "title-doji");
            }
            updateFavicon("images/favicon_red.png");
        } else {
            trendDisplay.innerText = "WAITING FOR CROSS";
            trendDisplay.className = "overall-trend trend-neutral";
            if (symbolBtn) {
                symbolBtn.classList.remove("title-green", "title-red", "title-doji");
            }
            updateFavicon("images/favicon_yellow.png");
        }

        checkAndSendAlert(p5m, isEmergency);
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


function checkAndSendAlert(p5m, isEmergency = false) {
    const lastAlertTrend = localStorage.getItem('lastAlertTrend');
    const lastAlertCandle = localStorage.getItem('lastAlertCandle'); // This will store 5m TS now
    const lastEmergencyHour = localStorage.getItem('lastEmergencyHour');

    const now = new Date();
    const current5mTs = p5m[p5m.length - 1].timestamp;
    const currentHourTs = Math.floor(now.getTime() / (3600 * 1000)) * (3600 * 1000);

    const isNewCandle = !lastAlertCandle || current5mTs > parseInt(lastAlertCandle);
    const isNewEmergencyHour = !lastEmergencyHour || currentHourTs > parseInt(lastEmergencyHour);
    const m = now.getMinutes();

    // Trend of the CLOSED candle (iloc -2)
    const closedCandles = p5m.slice(0, -1);
    const e5mClosed = getEMAs(closedCandles);
    const ltfUpClosed = e5mClosed.ema10 > e5mClosed.ema20;
    const ltfDownClosed = e5mClosed.ema10 < e5mClosed.ema20;

    let closedTrend = "NEUTRAL";
    if (ltfUpClosed) closedTrend = "UPTREND";
    else if (ltfDownClosed) closedTrend = "DOWNTREND";

    if (isEmergency) closedTrend = "DOWNTREND"; // Emergency overrides

    // 0. Skip if monitoring started less than 1 minute ago
    if (Date.now() - monitoringStartTime < 60000) {
        return;
    }

    // 1. Emergency Case: Bypass 5m rule, respect hourly lock, AND skip first 3m of new hour
    if (isEmergency && isNewEmergencyHour && m >= 3) {
        const symbolShort = SYMBOL.replace("USDT", "");
        const msg = `🩸 ${symbolShort} 1H EMERGENCY BREAKDOWN 🩸`;

        sendTelegramAlert(msg);
        speak(`${symbolShort} 1 hour emergency breakdown.`);

        localStorage.setItem('lastEmergencyHour', currentHourTs.toString());
        localStorage.setItem('lastAlertTrend', "DOWNTREND");
        localStorage.setItem('lastAlertCandle', current5mTs.toString());
        sessionStarted = true;
        return;
    }

    // Global Lock: If an emergency alert was sent this hour, standard alerts are muted
    if (!isNewEmergencyHour) {
        return;
    }

    // 2. Standard Case: Alert on NEW 5m candle if closed trend changed
    const isTrendChanged = closedTrend !== lastAlertTrend;

    // Initialization: If we just started, capture trend but don't lock the candle slot
    if (lastAlertTrend === null) {
        localStorage.setItem('lastAlertTrend', closedTrend);
        return;
    }

    if (isTrendChanged && isNewCandle) {
        let emoji = "";
        if (closedTrend === "UPTREND") emoji = "🚀";
        else if (closedTrend === "DOWNTREND") emoji = "💥";

        if (emoji) {
            const symbolShort = SYMBOL.replace("USDT", "");
            const msg = `${emoji} ${symbolShort} Trend: ${closedTrend} ${emoji}`;

            if (sessionStarted) {
                sendTelegramAlert(msg);
                speak(`${symbolShort} trend: ${closedTrend}`);
            }
        }

        localStorage.setItem('lastAlertTrend', closedTrend);
        localStorage.setItem('lastAlertCandle', current5mTs.toString());
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
    monitoringStartTime = Date.now();
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
    document.getElementById("ltfStatus").innerText = "LOADING...";
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
    const btn = document.getElementById('global-symbol');
    if (btn) {
        btn.innerText = SYMBOL;
    }
});
