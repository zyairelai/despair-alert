const SYMBOL = "BTCUSDT";
let started = false;
let lastBeepTime = 0; // Prevent duplicate beeps in the same second

async function fetchKlines(interval) {
    const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${SYMBOL}&interval=${interval}&limit=100`;
    const resp = await fetch(url);
    const data = await resp.json();
    return data.map(d => parseFloat(d[4])); // Close prices
}

function calculateEMA(prices, period) {
    const k = 2 / (period + 1);
    let ema = prices[0];
    for (let i = 1; i < prices.length; i++) {
        ema = (prices[i] * k) + (ema * (1 - k));
    }
    return ema;
}

function getEMAs(prices) {
    return {
        ema10: calculateEMA(prices.slice(-60), 10),
        ema20: calculateEMA(prices.slice(-60), 20),
        ema50: calculateEMA(prices.slice(-60), 50)
    };
}

async function updateTrend() {
    try {
        const [p15m, p5m] = await Promise.all([fetchKlines("15m"), fetchKlines("5m")]);
        const e15m = getEMAs(p15m);
        const e5m = getEMAs(p5m);

        const htfUp = e15m.ema10 > e15m.ema20 && e15m.ema20 > e15m.ema50;
        const htfDown = e15m.ema10 < e15m.ema20;

        const ltfUp = e5m.ema10 > e5m.ema20 && e5m.ema20 > e5m.ema50;
        const ltfDown = e5m.ema10 < e5m.ema20;

        const htfStatus = document.getElementById("htfStatus");
        const ltfStatus = document.getElementById("ltfStatus");
        const trendDisplay = document.getElementById("trendDisplay");

        htfStatus.innerText = htfUp ? 'UP' : (htfDown ? 'DOWN' : 'NEUTRAL');
        document.getElementById("htfRow").className = `status-row ${htfUp ? 'status-up' : (htfDown ? 'status-down' : 'status-neutral')}`;

        ltfStatus.innerText = ltfUp ? 'UP' : (ltfDown ? 'DOWN' : 'NEUTRAL');
        document.getElementById("ltfRow").className = `status-row ${ltfUp ? 'status-up' : (ltfDown ? 'status-down' : 'status-neutral')}`;

        if (htfUp && ltfUp) {
            trendDisplay.innerText = "CURRENTLY UPTREND";
            trendDisplay.className = "overall-trend trend-up";
        } else if (htfDown && ltfDown) {
            trendDisplay.innerText = "CURRENTLY DOWNTREND";
            trendDisplay.className = "overall-trend trend-down";
        } else {
            trendDisplay.innerText = "NO TRADE ZONE";
            trendDisplay.className = "overall-trend trend-neutral";
        }
    } catch (e) {
        console.error("Trend update failed", e);
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
        console.log("Beeping at", now.toLocaleTimeString());
        beep();
        lastBeepTime = nowTime;
    }

    if (s % 10 === 0) updateTrend(); // Update trend every 10s
}

function start() {
    if (started) return;
    started = true;
    document.getElementById("startBtn").disabled = true;
    document.getElementById("startBtn").innerText = "MONITORING ACTIVE";
    setInterval(tick, 1000);
    tick();
    updateTrend();

    // Initial beep to verify audio works
    beep();
    lastBeepTime = new Date().getTime();
}
