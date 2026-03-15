async function fetchDailyLevels(symbol) {
    try {
        const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=1d&limit=2`;
        const resp = await fetch(url);
        const data = await resp.json();
        if (data && data.length >= 2) {
            const prevDay = data[0];
            const high = Math.round(parseFloat(prevDay[2]));
            const low = Math.round(parseFloat(prevDay[3]));
            const mid = Math.round((high + low) / 2);

            const t1 = document.getElementById('price-target-1');
            const t2 = document.getElementById('price-target-2');
            const t3 = document.getElementById('price-target-3');

            if (t1) {
                t1.value = "";
                t1.placeholder = high;
            }
            if (t2) {
                t2.value = "";
                t2.placeholder = mid;
            }
            if (t3) {
                t3.value = "";
                t3.placeholder = low;
            }
            console.log(`Updated placeholders for ${symbol}: High=${high}, Mid=${mid}, Low=${low}`);
        }
    } catch (e) {
        console.error("Failed to fetch daily levels", e);
    }
}

async function fetchPrice(symbol) {
    const url = `https://fapi.binance.com/fapi/v1/ticker/price?symbol=${symbol}`;
    const resp = await fetch(url);
    const data = await resp.json();
    return parseFloat(data.price);
}

async function fetchKlines(symbol, interval) {
    const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=${interval}&limit=100`;
    const resp = await fetch(url);
    const data = await resp.json();
    return data.map(d => ({
        time: d[0],
        open: parseFloat(d[1]),
        high: parseFloat(d[2]),
        low: parseFloat(d[3]),
        close: parseFloat(d[4])
    }));
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
