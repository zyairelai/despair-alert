async function checkAlert(id) {
    const alert = alerts[id];
    if (!alert.active) return;

    const symbol = document.getElementById('global-symbol').innerText;
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
            let voiceMsg = "";

            if (!isNaN(target1)) {
                if (currentCandle.low <= target1 && currentCandle.high >= target1) {
                    triggered = true;
                    msg = `🔔 ${shortSymbol} Price Hits ${target1} 🔔`;
                    voiceMsg = `${shortSymbol} price hits ${target1}`;
                }
            }

            if (!triggered && !isNaN(target2)) {
                if (currentCandle.low <= target2 && currentCandle.high >= target2) {
                    triggered = true;
                    msg = `🔔 ${shortSymbol} Price Hits ${target2} 🔔`;
                    voiceMsg = `${shortSymbol} price hits ${target2}`;
                }
            }

            if (!triggered && !isNaN(target3)) {
                if (currentCandle.low <= target3 && currentCandle.high >= target3) {
                    triggered = true;
                    msg = `🔔 ${shortSymbol} Price Hits ${target3} 🔔`;
                    voiceMsg = `${shortSymbol} price hits ${target3}`;
                }
            }

            if (triggered) {
                alert.lastTriggerCandleTime = currentCandle.time;
                triggerAlert(id, msg, voiceMsg);
            }
        }

        if (id === 'ema-cross') {
            const shortEl = document.getElementById('ema-cross-short');
            const longEl = document.getElementById('ema-cross-long');
            const shortPeriod = parseInt(shortEl.value) || parseInt(shortEl.placeholder) || 10;
            const longPeriod = parseInt(longEl.value) || parseInt(longEl.placeholder) || 20;
            const el = document.getElementById('ema-cross-condition');
            const condition = el.dataset.state || el.value;

            const klines = await fetchKlines(symbol, tf);
            const prices = klines.map(k => k.close);

            const emaShortCurrent = calculateEMA(prices, shortPeriod);
            const emaLongCurrent = calculateEMA(prices, longPeriod);

            if (condition === 'up' && emaShortCurrent > emaLongCurrent) {
                triggerAlert(id, `🚀 ${shortSymbol} ${tf} EMA CROSS UP 🚀`, `${shortSymbol} ${tf} EMA cross to uptrend`);
            } else if (condition === 'down' && emaShortCurrent < emaLongCurrent) {
                triggerAlert(id, `💥 ${shortSymbol} ${tf} EMA CROSS DOWN 💥`, `${shortSymbol} ${tf} EMA cross to downtrend`);
            }
        }

        if (id === 'heikin') {
            const el = document.getElementById('heikin-condition');
            const condition = el.dataset.state || el.value;
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
                            triggerAlert(id, `🚀 ${shortSymbol} ${tf} HEIKIN ASHI GREEN 🚀`, `${shortSymbol} ${tf} HEIKIN ASHI turned into GREEN color`);
                        }
                    } else if (condition === 'perfect-red') {
                        // Perfect Red: Close < Open AND No upper wick (High == Open)
                        if (haClose < haOpen && Math.abs(currentHaHigh - haOpen) < (haOpen * 0.00001)) {
                            triggerAlert(id, `💥 ${shortSymbol} ${tf} HEIKIN ASHI RED 💥`, `${shortSymbol} ${tf} HEIKIN ASHI turned into RED color`);
                        }
                    }
                }
            }
        }

        if (id === 'rawcandle') {
            // Auto-Stop logic: Stop 5 seconds before the candle closes
            const tfMs = tfToMs(tf);
            if (tfMs > 0) {
                const now = Date.now();
                const nextCandleTime = Math.ceil(now / tfMs) * tfMs;
                const msRemaining = nextCandleTime - now;

                if (msRemaining <= 5000) {
                    console.log(`Auto-stopping ${id} (5s before next candle)`);
                    toggleAlert(id);
                    return;
                }
            }

            const el = document.getElementById('rawcandle-condition');
            const condition = el.dataset.state || el.value;
            const klines = await fetchKlines(symbol, tf);
            if (klines.length < 1) return;

            const k = klines[klines.length - 1];
            if (condition === 'green') {
                if (k.close > k.open) {
                    triggerAlert(id, `🚀 ${shortSymbol} ${tf} RAW GREEN 🚀`, `${shortSymbol} ${tf} RAW candle turned into GREEN color`);
                }
            } else if (condition === 'red') {
                if (k.close < k.open) {
                    triggerAlert(id, `💥 ${shortSymbol} ${tf} RAW RED 💥`, `${shortSymbol} ${tf} RAW candle turned into RED color`);
                }
            }
        }

        if (id === 'ema-alert') {
            const elVal = document.getElementById('ema-alert-level');
            const period = parseInt(elVal.value) || parseInt(elVal.placeholder) || 20;
            const modeEl = document.getElementById('ema-alert-mode');
            const mode = modeEl.dataset.state;

            const klines = await fetchKlines(symbol, tf);
            if (klines.length < period + 1) return;

            const prices = klines.map(k => k.close);
            const currentCandle = klines[klines.length - 1];

            if (mode === 'touch') {
                const emaValCurrent = calculateEMA(prices, period);
                if (currentCandle.low <= emaValCurrent && currentCandle.high >= emaValCurrent) {
                    triggerAlert(id, `🔔 ${shortSymbol} ${tf} TOUCH ${period}EMA 🔔`, `${shortSymbol} ${tf} candle touched ${period} EMA`);
                }
            } else if (mode === 'close') {
                const condEl = document.getElementById('ema-alert-condition');
                const condition = condEl.dataset.state || condEl.value;
                const emaValPrev = calculateEMA(prices.slice(0, -1), period);
                const prevClose = klines[klines.length - 2].close;

                if (condition === 'above' && prevClose > emaValPrev) {
                    triggerAlert(id, `🚀 ${shortSymbol} ${tf} CLOSE ABOVE ${period}EMA 🚀`, `${shortSymbol} ${tf} candle closed above ${period} EMA`);
                } else if (condition === 'below' && prevClose < emaValPrev) {
                    triggerAlert(id, `💥 ${shortSymbol} ${tf} CLOSE BELOW ${period}EMA 💥`, `${shortSymbol} ${tf} candle closed below ${period} EMA`);
                }
            }
        }

        if (id === 'liquidity') {
            const tfSelectors = [
                document.getElementById('liquidity-1-tf-menu'),
                document.getElementById('liquidity-2-tf-menu'),
                document.getElementById('liquidity-3-tf-menu')
            ];
            const tfs = tfSelectors
                .filter(el => el !== null)
                .map(el => el.dataset.value);

            const uniqueTfs = [...new Set(tfs)];

            for (const currentTf of uniqueTfs) {
                const klines = await fetchKlines(symbol, currentTf);
                if (klines.length < 2) continue;

                const currentCandle = klines[klines.length - 1];
                const previousCandle = klines[klines.length - 2];

                // Guard: For 1h or higher, skip if the candle is less than 3 minutes old
                const isHtf = currentTf.includes('h') || currentTf.includes('d');
                if (isHtf) {
                    const candleAgeSeconds = (Date.now() - currentCandle.time) / 1000;
                    if (candleAgeSeconds < 180) {
                        continue; // Skip this TF for now
                    }
                }

                // Condition: current high >= 99.95% of previous high AND current candle is RED (close < open)
                if (currentCandle.high >= (previousCandle.high * 0.9995) && currentCandle.close < currentCandle.open) {
                    const voiceMsg = `${shortSymbol} ${currentTf} LIQUIDITY HUNT ACTIVATED.`;
                    triggerAlert(id, `🩸 ${shortSymbol} ${currentTf} LIQUIDITY HUNT 🩸`, voiceMsg);
                    break; // stop checking other TFs once one is triggered
                }
            }
        }


    } catch (e) {
        console.error(`Check failed for ${id}`, e);
    }
}

function triggerAlert(id, message, voiceMessage = null) {
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

    const textToSpeak = voiceMessage || message;

    // Helper to reset UI state
    const cleanUI = () => {
        if (alert.uiBackupTimeout) clearTimeout(alert.uiBackupTimeout);
        if (!alert.active) {
            btn.innerText = "START";
            btn.classList.remove('active');
            indicator.classList.remove('triggered');
            indicator.classList.add('inactive');
            statusText.innerText = "INACTIVE";

            const title = card.querySelector('.card-header h2');
            if (title) title.classList.remove('running-title');
        }
    };

    // Safety fallback: Reset UI after 10s even if speech callback fails
    alert.uiBackupTimeout = setTimeout(cleanUI, 10000);

    speak(textToSpeak, cleanUI);

    // Special channel for EMA Alert, EMA Cross, Heikin, and Shooting Star
    const wolvesRiseIds = ['ema-alert', 'ema-cross', 'heikin'];
    const telegramChatId = wolvesRiseIds.includes(id) ? "@futures_wolves_rise" : null;

    // Send Telegram Alert ONLY if enabled (Secret Toggle)
    if (window.telegramEnabled) {
        sendTelegramAlert(message, telegramChatId);
    }

    lastAlertMessages[id] = message;
    lastAlertTimes[id] = Date.now();
}

/**
 * Converts a timeframe string (e.g., "1m", "15m", "1h", "1d") into milliseconds.
 */
function tfToMs(tf) {
    if (!tf) return 0;
    const unit = tf.slice(-1);
    const val = parseInt(tf.slice(0, -1));
    if (isNaN(val)) return 0;

    if (unit === 'm') return val * 60 * 1000;
    if (unit === 'h') return val * 60 * 60 * 1000;
    if (unit === 'd') return val * 24 * 60 * 60 * 1000;
    return 0;
}
