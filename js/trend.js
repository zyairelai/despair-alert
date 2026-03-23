let SYMBOL = localStorage.getItem('globalSymbol') || "BTCUSDT";
let started = false;
let sessionStarted = true;
let lastBeepInterval = 0;
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
    if (klines.length < 7) return false;

    const ss = klines[klines.length - 2]; // Target candle (last closed)
    const prior3 = klines.slice(klines.length - 5, klines.length - 2); // -3, -4, -5
    const prior5 = klines.slice(klines.length - 7, klines.length - 2); // -3, -4, -5, -6, -7

    const ssBody = Math.abs(ss.open - ss.close);
    const ssUpperWick = ss.high - Math.max(ss.open, ss.close);
    const ssLowerWick = Math.min(ss.open, ss.close) - ss.low;
    const ssRangeHC = ss.high - ss.close;

    // 1. Upper wick > (body + lower wick)
    const cond1 = ssUpperWick > (ssBody + ssLowerWick);

    // 2. Upper wick > max upper wick of last 3 candles before SS
    const maxUpperWick3 = Math.max(...prior3.map(k => k.high - Math.max(k.open, k.close)));
    const cond2 = ssUpperWick > maxUpperWick3;

    // 3. Range (high-close) > average range (high-close) of last 5 candles before SS
    const avgRangeHC5 = prior5.reduce((sum, k) => sum + (k.high - k.close), 0) / 5;
    const cond3 = ssRangeHC > avgRangeHC5;

    // 4. High > highest high of last 5 candles before SS
    const maxHigh5 = Math.max(...prior5.map(k => k.high));
    const cond4 = ss.high > maxHigh5;

    return cond1 && cond2 && cond3 && cond4;
}

function calculateEMA(data, period) {
    if (data.length < period) return null;
    const k = 2 / (period + 1);
    let ema = data.slice(0, period).reduce((acc, val) => acc + val.close, 0) / period;
    for (let i = period; i < data.length; i++) {
        ema = (data[i].close - ema) * k + ema;
    }
    return ema;
}

async function updateTrend() {
    try {
        const [p1h, p15m, p5m] = await Promise.all([
            fetchKlines("1h"),
            fetchKlines("15m"),
            fetchKlines("5m")
        ]);

        // 5m (LTF) UI Update - only depends on p5m
        const closed5m = p5m.slice(0, -1);

        if (closed5m.length < 51) return; // Need at least 50 for EMA50 + some buffer

        // Helper to check 10/20/50 condition for a slice
        const getTrendAt = (slice) => {
            const ema10 = calculateEMA(slice, 10);
            const ema20 = calculateEMA(slice, 20);
            const ema50 = calculateEMA(slice, 50);

            if (ema10 === null || ema20 === null || ema50 === null) return "NEUTRAL";

            // Uptrend: 10 > 20 > 50 (Wait 4 candles logic applied outside)
            // Downtrend: 10 < 20 (Immediately)
            if (ema10 < ema20) return "DOWNTREND";
            if (ema10 > ema20 && ema20 > ema50) return "UPTREND_CANDIDATE";
            return "NEUTRAL";
        };

        // Check last 4 closed candles for Uptrend (EMA10 > EMA20 > EMA50)
        let isUptrendConfirmed = true;
        for (let i = 0; i < 4; i++) {
            const slice = closed5m.slice(0, closed5m.length - i);
            if (getTrendAt(slice) !== "UPTREND_CANDIDATE") {
                isUptrendConfirmed = false;
                break;
            }
        }

        // Downtrend: 10/20 EMA crossing downtrend (previous close crossing)
        const closedCandles = p5m.slice(0, -1);
        const ema10_closed = calculateEMA(closedCandles, 10);
        const ema20_closed = calculateEMA(closedCandles, 20);
        const ema10_prev_closed = calculateEMA(closedCandles.slice(0, -1), 10);
        const ema20_prev_closed = calculateEMA(closedCandles.slice(0, -1), 20);

        const isBearishCross = (ema10_prev_closed > ema20_prev_closed) && (ema10_closed < ema20_closed);

        if (p1h.length < 4) return;

        // Emergency 1h Logic: Current high > max(previous 3 highs) AND current 1h candle is RED
        const cur1h = p1h[p1h.length - 1];
        const prev3h = p1h.slice(p1h.length - 4, p1h.length - 1);
        const maxPrevHigh = Math.max(...prev3h.map(k => k.high));
        const isEmergency = cur1h.high > maxPrevHigh && cur1h.close < cur1h.open;

        let currentTrend = "NO TRADE ZONE";
        if (isUptrendConfirmed) currentTrend = "UPTREND";
        else if (isBearishCross) currentTrend = "DOWNTREND";
        // Keep DOWNTREND state if already in DOWNTREND and EMA10 < EMA20
        else if ((localStorage.getItem('lastTrendState') === "DOWNTREND") && (ema10_closed < ema20_closed)) currentTrend = "DOWNTREND";

        const trendDisplay = document.getElementById("trendDisplay");
        const symbolBtn = document.getElementById("global-symbol");

        const lastTrendState = localStorage.getItem('lastTrendState') || "INITIALIZING";

        if (currentTrend === "UPTREND") {
            trendDisplay.innerText = "CURRENTLY UPTREND";
            trendDisplay.className = "overall-trend trend-up";
            if (symbolBtn) {
                symbolBtn.classList.add("title-green");
                symbolBtn.classList.remove("title-red", "title-yellow");
            }
            updateFavicon("images/favicon_green.png");

            // Alert only on change to UPTREND and NOT on first initial load
            if (lastTrendState !== "UPTREND" && lastTrendState !== "INITIALIZING") {
                const symbolShort = SYMBOL.replace("USDT", "");
                speak(`${symbolShort} trend: UPTREND`);
                sendTelegramAlert(`🚀 ${symbolShort} trend: UPTREND 🚀`);
            }
        } else if (currentTrend === "DOWNTREND") {
            trendDisplay.innerText = "CURRENTLY DOWNTREND";
            trendDisplay.className = "overall-trend trend-down";
            if (symbolBtn) {
                symbolBtn.classList.add("title-red");
                symbolBtn.classList.remove("title-green", "title-yellow");
            }
            updateFavicon("images/favicon_red.png");

            // Alert only on change to DOWNTREND and NOT on first initial load
            if (lastTrendState !== "DOWNTREND" && lastTrendState !== "INITIALIZING") {
                const symbolShort = SYMBOL.replace("USDT", "");
                speak(`${symbolShort} trend: DOWNTREND`);
                sendTelegramAlert(`💥 ${symbolShort} trend: DOWNTREND 💥`);
            }
        } else {
            trendDisplay.innerText = "NO TRADE ZONE";
            trendDisplay.className = "overall-trend trend-neutral";
            if (symbolBtn) {
                symbolBtn.classList.remove("title-green", "title-red");
                symbolBtn.classList.add("title-yellow");
            }
            updateFavicon("images/favicon_yellow.png");
        }

        localStorage.setItem('lastTrendState', currentTrend);

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

    const now = new Date();
    const nowTs = now.getTime();
    const currentHourTs = Math.floor(nowTs / (3600 * 1000)) * (3600 * 1000);
    const cooldownEnd = lastEmergencyHour ? (parseInt(lastEmergencyHour) + 3600000 + 30000) : 0;
    const isNewEmergencyHour = nowTs >= cooldownEnd;

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

    // 1.5. Local Variables for Cross Logic (Stable Trend)
    const closed5m = p5m.slice(0, -1);
    const ema10_5m = calculateEMA(closed5m, 10);
    const ema20_5m = calculateEMA(closed5m, 20);
    const ltfUp = ema10_5m > ema20_5m;
    const ltfDown = ema10_5m < ema20_5m;

    // 1.6. Bearish Cross Logic (Only alert UP to DOWN on closed candle)
    const lastAlertTrend = localStorage.getItem('lastAlertTrend'); // Store previous trend state
    const current5mTs = p5m[p5m.length - 1].timestamp;
    const lastAlertCandle = localStorage.getItem('lastAlertCandle');
    const isNewCandle = !lastAlertCandle || current5mTs > parseInt(lastAlertCandle);

    const closedCandles = p5m.slice(0, -1);
    const ema10_closed = calculateEMA(closedCandles, 10);
    const ema20_closed = calculateEMA(closedCandles, 20);
    const ema10_prev_closed = calculateEMA(closedCandles.slice(0, -1), 10);
    const ema20_prev_closed = calculateEMA(closedCandles.slice(0, -1), 20);

    const isBearishCross = (ema10_prev_closed > ema20_prev_closed) && (ema10_closed < ema20_closed);

    if (isBearishCross && isNewCandle) {
        const symbolShort = SYMBOL.replace("USDT", "");
        const msg = `💥 ${symbolShort} 5m EMA BEARISH CROSS 💥`;
        sendTelegramAlert(msg);
        speak(`${symbolShort} 5 minute trend turned into DOWN.`);
        localStorage.setItem('lastAlertCandle', current5mTs.toString());
    }

    const ema10_15m = calculateEMA(p15m, 10);
    const ema20_15m = calculateEMA(p15m, 20);
    const isEmaConditionMet = (ema20_15m > ema10_15m) || (ema20_5m > ema10_5m);

    // 2. Shooting Star Case: 15m, 5m
    const checkSS = (tf, klines, intervalMs, storageKey) => {
        if (!isEmaConditionMet) return false; // Early exit if EMA condition fails

        const lastAlert = localStorage.getItem(storageKey);
        const intervalStart = Math.floor(nowTs / intervalMs) * intervalMs;

        // Cooldown: Mute until the NEXT interval + 30 seconds
        const cooldownEnd = lastAlert ? (parseInt(lastAlert) + intervalMs + 30000) : 0;
        const isCooledDown = nowTs >= cooldownEnd;

        if (isCooledDown && isShootingStar(klines)) {
            const symbolShort = SYMBOL.replace("USDT", "");
            const emoji = "🌠";
            const msg = `${emoji} ${symbolShort} ${tf} SHOOTING STAR ${emoji}`;

            sendTelegramAlert(msg);
            speak(`${symbolShort} ${tf} shooting star detected.`);

            localStorage.setItem(storageKey, intervalStart.toString());
            return true;
        }
        return false;
    };

    // Check each timeframe independently
    checkSS("15m", p15m, 900000, 'lastSS15m');
    checkSS("5m", p5m, 300000, 'lastSS5m');
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
        console.log("Beeping for interval", currentInterval, "at", now.toLocaleTimeString());
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
    monitoringStartTime = Date.now();

    // Initialize to current interval to avoid double-beep on start
    lastBeepInterval = Math.floor(Date.now() / (5 * 60 * 1000));

    monitorInterval = setInterval(tick, 1000);
    updateTrend(); // Initial Immediate Update
    tick();

    // Initial check does not beep or alert, just verifies audio
    beep();
}

// Beep logic simplified to always trigger on 5m interval
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

    const symbolBtn = document.getElementById("global-symbol");
    if (symbolBtn) {
        symbolBtn.classList.remove("title-green", "title-red");
        symbolBtn.classList.add("title-yellow");
    }
    const trendDisplay = document.getElementById("trendDisplay");
    trendDisplay.innerText = "INITIALIZING...";
    trendDisplay.className = "overall-trend trend-neutral";

    document.getElementById("countdown").innerText = "00:00";

    // Reset session markers
    localStorage.removeItem('lastAlertTrend');
    localStorage.removeItem('lastAlertCandle');
    localStorage.removeItem('lastEmergencyHour');
    localStorage.removeItem('lastSS1h');
    localStorage.removeItem('lastSS15m');
    localStorage.removeItem('lastShootingStarHour');
}

// Ensure the dropdown matches the stored symbol on load
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('global-symbol');
    if (btn) {
        btn.innerText = SYMBOL;
        btn.classList.add('title-yellow');
    }
});
