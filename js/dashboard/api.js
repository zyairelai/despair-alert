async function fetchDailyLevels(symbol) {
    try {
        const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=1d&limit=2`;
        const resp = await fetch(url);
        const data = await resp.json();
        if (data && data.length >= 2) {
            const prevDay = data[0];
            const high = Math.round(parseFloat(prevDay[2]));
            const low = Math.round(parseFloat(prevDay[3]));
            const close = Math.round(parseFloat(prevDay[4]));

            const t1 = document.getElementById('price-target-1');
            const t2 = document.getElementById('price-target-2');
            const t3 = document.getElementById('price-target-3');

            if (t1) {
                t1.value = "";
                t1.placeholder = high;
            }
            if (t2) {
                t2.value = "";
                t2.placeholder = close;
            }
            if (t3) {
                t3.value = "";
                t3.placeholder = low;
            }
            console.log(`Updated placeholders for ${symbol}: High=${high}, Close=${close}, Low=${low}`);
        }
    } catch (e) {
        console.error("Failed to fetch daily levels", e);
    }
}


const klineCache = {};

async function fetchKlines(symbol, interval) {
    const cacheKey = `${symbol}_${interval}`;
    const now = Date.now();

    // 1. Check if there's a valid cache (less than 2s old)
    if (klineCache[cacheKey] && !klineCache[cacheKey].inFlight && (now - klineCache[cacheKey].timestamp < 2000)) {
        return klineCache[cacheKey].data;
    }

    // 2. Check if a request is already in flight for this exact symbol/tf
    if (klineCache[cacheKey] && klineCache[cacheKey].inFlight) {
        return klineCache[cacheKey].promise;
    }

    // 3. Otherwise, perform new fetch and store promise for coalescing
    const fetchPromise = (async () => {
        try {
            const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=${interval}&limit=100`;
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`Binance API error: ${resp.status}`);
            const data = await resp.json();
            const formatted = data.map(d => ({
                time: d[0],
                open: parseFloat(d[1]),
                high: parseFloat(d[2]),
                low: parseFloat(d[3]),
                close: parseFloat(d[4])
            }));

            // Update cache with fresh data
            klineCache[cacheKey] = {
                data: formatted,
                timestamp: Date.now(),
                inFlight: false,
                promise: null
            };
            return formatted;
        } catch (e) {
            delete klineCache[cacheKey]; // Clear cache on error so next attempt can retry
            throw e;
        }
    })();

    // Mark as in-flight
    klineCache[cacheKey] = {
        promise: fetchPromise,
        inFlight: true,
        timestamp: now
    };

    return fetchPromise;
}

async function sendTelegramAlert(message, customChatId = null) {
    const botToken = customChatId === "@futures_wolves_rise" ? ENV.TELEGRAM_WOLVESRISE : ENV.TELEGRAM_LIVERMORE;
    const chatId = customChatId || "@swinglivermore";

    if (!botToken) return;
    const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
    const params = new URLSearchParams({
        chat_id: chatId,
        parse_mode: 'html',
        text: message
    });
    try {
        await fetch(`${url}?${params}`);
    } catch (e) { }
}
