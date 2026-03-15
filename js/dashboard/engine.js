async function checkAlert(id) {
    const alert = alerts[id];
    if (!alert.active) return;

    const symbol = document.getElementById('global-symbol').value;
    const shortSymbol = symbol.replace("USDT", "");

    // Read TF from Menu data-value
    const menuEl = document.getElementById(`${id}-tf-menu`);
    const tf = menuEl ? menuEl.dataset.value : "5m";

    try {
        if (id === 'price') {
            const t1El = document.getElementById('price-target-1');
            const t2El = document.getElementById('price-target-2');
            const t3El = document.getElementById('price-target-3');
            const t1Val = t1El.value.trim();
            const t2Val = t2El.value.trim();
            const t3Val = t3El.value.trim();

            const target1 = t1Val !== "" ? parseFloat(t1Val) : parseFloat(t1El.placeholder);
            const target2 = t2Val !== "" ? parseFloat(t2Val) : parseFloat(t2El.placeholder);
            const target3 = t3Val !== "" ? parseFloat(t3Val) : parseFloat(t3El.placeholder);

            if (isNaN(target1) && isNaN(target2) && isNaN(target3)) return;

            const klines = await fetchKlines(symbol, tf);
            const currentCandle = klines[klines.length - 1];

            let triggered = false;
            let msg = "";

            if (!isNaN(target1)) {
                if (currentCandle.low <= target1 && currentCandle.high >= target1) {
                    triggered = true;
                    msg = `${shortSymbol} price swallowed ${target1}`;
                }
            }

            if (!triggered && !isNaN(target2)) {
                if (currentCandle.low <= target2 && currentCandle.high >= target2) {
                    triggered = true;
                    msg = `${shortSymbol} price swallowed ${target2}`;
                }
            }

            if (!triggered && !isNaN(target3)) {
                if (currentCandle.low <= target3 && currentCandle.high >= target3) {
                    triggered = true;
                    msg = `${shortSymbol} price swallowed ${target3}`;
                }
            }

            if (triggered) {
                alert.lastTriggerCandleTime = currentCandle.time;
                triggerAlert(id, msg);
            }
        }

        if (id === 'ema-cross') {
            const shortPeriod = parseInt(document.getElementById('ema-cross-short').value);
            const longPeriod = parseInt(document.getElementById('ema-cross-long').value);
            const condition = document.getElementById('ema-cross-condition').value;

            const klines = await fetchKlines(symbol, tf);
            const prices = klines.map(k => k.close);

            const emaShortCurrent = calculateEMA(prices, shortPeriod);
            const emaLongCurrent = calculateEMA(prices, longPeriod);

            if (condition === 'uptrend' && emaShortCurrent > emaLongCurrent) {
                triggerAlert(id, `${shortSymbol} ${tf} EMA Cross to Uptrend`);
            } else if (condition === 'downtrend' && emaShortCurrent < emaLongCurrent) {
                triggerAlert(id, `${shortSymbol} ${tf} EMA Cross to Downtrend`);
            }
        }

        if (id === 'heikin') {
            const condition = document.getElementById('heikin-condition').value;
            const klines = await fetchKlines(symbol, tf);

            if (klines.length < 50) return; // Need history for stable HA

            // Stable HA Calculation Loop
            let haOpen = (klines[0].open + klines[0].close) / 2;
            let haClose = (klines[0].open + klines[0].high + klines[0].low + klines[0].close) / 4;

            for (let i = 1; i < klines.length; i++) {
                const k = klines[i];
                const currentHaClose = (k.open + k.high + k.low + k.close) / 4;
                const currentHaOpen = (haOpen + haClose) / 2;
                const currentHaHigh = Math.max(k.high, currentHaOpen, currentHaClose);
                const currentHaLow = Math.min(k.low, currentHaOpen, currentHaClose);

                haOpen = currentHaOpen;
                haClose = currentHaClose;

                // Only evaluate the final (current) candle
                if (i === klines.length - 1) {
                    if (condition === 'perfect-green') {
                        // Perfect Green: Close > Open AND No lower wick (Low == Open)
                        if (haClose > haOpen && Math.abs(currentHaLow - haOpen) < (haOpen * 0.00001)) {
                            triggerAlert(id, `${shortSymbol} ${tf} heikin ashi turned into GREEN color`);
                        }
                    } else if (condition === 'perfect-red') {
                        // Perfect Red: Close < Open AND No upper wick (High == Open)
                        if (haClose < haOpen && Math.abs(currentHaHigh - haOpen) < (haOpen * 0.00001)) {
                            triggerAlert(id, `${shortSymbol} ${tf} heikin ashi turned into RED color`);
                        }
                    }
                }
            }
        }

        if (id === 'standing') {
            const period = parseInt(document.getElementById('standing-level').value) || 20;
            const condition = document.getElementById('standing-condition').value;

            const klines = await fetchKlines(symbol, tf);
            if (klines.length < period + 1) return;

            const prices = klines.map(k => k.close);
            const emaVal = calculateEMA(prices.slice(0, -1), period); // Previous candle EMA
            const prevClose = klines[klines.length - 2].close;

            if (condition === 'above' && prevClose > emaVal) {
                triggerAlert(id, `${shortSymbol} ${tf} standing above ${period} EMA`);
            } else if (condition === 'below' && prevClose < emaVal) {
                triggerAlert(id, `${shortSymbol} ${tf} standing below ${period} EMA`);
            }
        }

        if (id === 'line-touch') {
            const period = parseInt(document.getElementById('line-touch-price').value) || 20;

            const klines = await fetchKlines(symbol, tf);
            if (klines.length < period) return;

            const prices = klines.map(k => k.close);
            const emaVal = calculateEMA(prices, period);
            const currentCandle = klines[klines.length - 1];

            if (currentCandle.low <= emaVal && currentCandle.high >= emaVal) {
                triggerAlert(id, `${shortSymbol} ${tf} touch the ${period} EMA`);
            }
        }
    } catch (e) {
        console.error(`Check failed for ${id}`, e);
    }
}

function triggerAlert(id, message) {
    const alert = alerts[id];
    const statusText = document.getElementById(`${id}-status`);
    const indicator = statusText.parentElement;
    const card = document.getElementById(`${id}-card`);
    const btn = card.querySelector('.toggle-btn');

    // Stop monitoring immediately
    alert.active = false;
    if (alert.interval) clearInterval(alert.interval);
    alert.interval = null;

    indicator.classList.remove('monitoring', 'inactive');
    indicator.classList.add('triggered');
    statusText.innerText = "TRIGGER";

    // Show STOP button immediately for silencing
    if (btn) {
        btn.innerText = "STOP";
        btn.classList.add('active');
    }

    speak(message, () => {
        // Revert to START only if we stopped because of trigger (not manual stop)
        if (!alert.active) {
            btn.innerText = "START";
            btn.classList.remove('active');
            indicator.classList.remove('triggered');
            indicator.classList.add('inactive');
            statusText.innerText = "INACTIVE";

            const title = card.querySelector('.card-header h2');
            if (title) title.classList.remove('running-title');
        }
    });

    lastAlertMessages[id] = message;
    lastAlertTimes[id] = Date.now();
}
