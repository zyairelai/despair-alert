let SYMBOL = localStorage.getItem('globalSymbol') || "BTCUSDT";
let started = false;
let lastBeepInterval = 0;
let beepInterval = parseInt(localStorage.getItem('beepInterval')) || 5;
let audioCtx = null;

// Secret Telegram Toggle (Trend Change Alerts Only)
window.telegramEnabled = true;
let teleBuffer = "";

document.addEventListener('keydown', (e) => {
    // Basic buffer logic to detect "te", "tt", "on", "off"
    teleBuffer += e.key.toLowerCase();
    if (teleBuffer.length > 5) teleBuffer = teleBuffer.slice(-5);

    const lastTwo = teleBuffer.slice(-2);
    const lastThree = teleBuffer.slice(-3);

    if (!window.telegramEnabled && (lastTwo === "te" || lastTwo === "tt" || lastTwo === "on")) {
        window.telegramEnabled = true;
        console.log("SECRET: Trend Telegram Alerts Enabled.");

        // Play pickup sound
        const audio = new Audio('images/pickup.mp3');
        audio.play().catch(err => console.error("Sound play failed:", err));

        teleBuffer = ""; // Reset buffer
    } else if (window.telegramEnabled && (lastThree === "off" || lastTwo === "zz" || lastTwo === "oo")) {
        window.telegramEnabled = false;
        console.log("SECRET: Trend Telegram Alerts Disabled.");

        // Play gameover sound
        const audio = new Audio('images/gameover.mp3');
        audio.play().catch(err => console.error("Sound play failed:", err));

        teleBuffer = ""; // Reset buffer
    }
});

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

        const cur1h = p1h[p1h.length - 1];
        const prev1h = p1h[p1h.length - 2];

        // 1. HA & Raw Color Detection (1H Only)
        const ha1h = getHA(p1h);
        const raw1h = cur1h.close > cur1h.open ? "GREEN" : "RED";

        // 1.2. EMA 50 Calculation
        const closes = p1h.map(k => k.close);
        const ema50 = calculateEMA(closes, 50);
        const isAboveEma = ha1h && ema50 && ha1h.close > ema50;

        // 1.5. 1H Price Action Conditions
        const prev1hMinBody = Math.min(prev1h.open, prev1h.close);
        const prev1hMaxBody = Math.max(prev1h.open, prev1h.close);
        const priceLowBroken = cur1h.low < prev1hMinBody;
        const priceHighBroken = cur1h.high > prev1hMaxBody;

        // 2. Trend Logic (1H Only + Price Condition)
        const isRedSingularity = (ha1h && ha1h.color === "RED" && raw1h === "RED" && priceLowBroken);
        const isUptrend = (ha1h && ha1h.color === "GREEN" && raw1h === "GREEN" && priceHighBroken && isAboveEma);

        // 3. Emergency 1h Logic
        const maxPrevHigh = prev1h.high;
        const isEmergency = cur1h.high > maxPrevHigh && cur1h.close < cur1h.open;

        const trendDisplay = document.getElementById("trendDisplay");
        const symbolBtn = document.getElementById("global-symbol");

        // UI Visuals
        if (isEmergency) {
            trendDisplay.innerText = "1H EMERGENCY BREAKDOWN";
            trendDisplay.className = "overall-trend trend-down";
            if (symbolBtn) {
                symbolBtn.classList.add("title-red");
                symbolBtn.classList.remove("title-green", "title-yellow");
            }
            updateFavicon("images/favicon_red.png");
        } else if (isRedSingularity) {
            trendDisplay.innerText = "CURRENTLY DOWNTREND";
            trendDisplay.className = "overall-trend trend-down";
            if (symbolBtn) {
                symbolBtn.classList.add("title-red");
                symbolBtn.classList.remove("title-green", "title-yellow");
            }
            updateFavicon("images/favicon_red.png");
        } else if (isUptrend) {
            trendDisplay.innerText = "CURRENTLY UPTREND";
            trendDisplay.className = "overall-trend trend-up";
            if (symbolBtn) {
                symbolBtn.classList.add("title-green");
                symbolBtn.classList.remove("title-red", "title-yellow");
            }
            updateFavicon("images/favicon_green.png");
        } else {
            trendDisplay.innerText = "NO TRADE ZONE";
            trendDisplay.className = "overall-trend trend-neutral";
            if (symbolBtn) {
                symbolBtn.classList.remove("title-green", "title-red");
                symbolBtn.classList.add("title-yellow");
            }
            updateFavicon("images/favicon_yellow.png");
        }

        checkAndSendAlert(p1h, isEmergency, isRedSingularity);
    } catch (e) {
        console.error("Trend update failed", e);
    }
}



function checkAndSendAlert(p1h, isEmergency = false, isRedSingularity = false) {
    const now = new Date();
    const nowTs = now.getTime();
    const currentHourTs = Math.floor(nowTs / (3600 * 1000)) * (3600 * 1000);

    const symbolShort = SYMBOL.replace("USDT", "");

    // 1. Emergency Case: 1H Breakdown
    const lastEmergencyHour = localStorage.getItem('lastEmergencyHour');
    const cooldownEndEmergency = lastEmergencyHour ? (parseInt(lastEmergencyHour) + 3600000 + 30000) : 0;
    if (isEmergency && nowTs >= cooldownEndEmergency) {
        const msg = `🩸 ${symbolShort} 1H EMERGENCY BREAKDOWN 🩸`;
        if (window.telegramEnabled) sendTelegramAlert(msg);
        speak(`${symbolShort} 1 hour emergency breakdown.`);
        localStorage.setItem('lastEmergencyHour', currentHourTs.toString());
    }

    // 2. Red Singularity Alert
    const lastRedSingularityHour = localStorage.getItem('lastRedSingularityHour');
    const cooldownEndRS = lastRedSingularityHour ? (parseInt(lastRedSingularityHour) + 3600000 + 30000) : 0;
    if (isRedSingularity && nowTs >= cooldownEndRS) {
        const msg = `💥 ${symbolShort} 1H RED SINGULARITY 💥`;
        if (window.telegramEnabled) sendTelegramAlert(msg);
        speak(`${symbolShort} 1 hour red singularity.`);
        localStorage.setItem('lastRedSingularityHour', currentHourTs.toString());
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

    // Initialize alert cooldowns to now to avoid immediate trigger on first run
    const nowTs = Date.now();
    const currentHourTs = Math.floor(nowTs / (3600 * 1000)) * (3600 * 1000);
    localStorage.setItem('lastEmergencyHour', currentHourTs.toString());
    localStorage.setItem('lastRedSingularityHour', currentHourTs.toString());

    // Initialize to current interval to avoid double-beep on start
    lastBeepInterval = Math.floor(nowTs / (beepInterval * 60 * 1000));

    monitorInterval = setInterval(tick, 1000);
    updateTrend(); // Initial Immediate Update (silenced by cooldown)
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
    localStorage.removeItem('lastTrendAlertCandle');
    localStorage.removeItem('lastAlertCandle');
    localStorage.removeItem('lastEmergencyHour');
    localStorage.removeItem('lastRedSingularityHour');
}

// Ensure the dropdown matches the stored symbol on load
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('global-symbol');
    if (btn) {
        btn.innerText = SYMBOL;
        btn.classList.add('title-yellow');
    }

    // Initialize Beep Mode UI
    updateBeepUI();
});

function setBeepInterval(m) {
    beepInterval = m;
    localStorage.setItem('beepInterval', m);
    updateBeepUI();
    console.log("Beep interval set to:", m, "minutes");

    // Reset lastBeepInterval to current so it doesn't immediately beep if we just switched
    lastBeepInterval = Math.floor(Date.now() / (m * 60 * 1000));

    // Immediate UI Update
    tick();
}

function updateBeepUI() {
    const b5 = document.getElementById('beep5m');
    const b15 = document.getElementById('beep15m');
    if (b5 && b15) {
        b5.classList.toggle('active', beepInterval === 5);
        b15.classList.toggle('active', beepInterval === 15);
    }
}
