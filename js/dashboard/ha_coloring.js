function calculateEMA(prices, period) {
    if (prices.length < period) return null;
    const k = 2 / (period + 1);
    let ema = prices.slice(0, period).reduce((acc, val) => acc + val, 0) / period;
    for (let i = period; i < prices.length; i++) {
        ema = (prices[i] - ema) * k + ema;
    }
    return ema;
}

async function updateTitleAndFavicon() {
    // Both Main Dashboard and Trend page now use 1m 10, 20, 50 EMA alignment
    const symbolEl = document.getElementById('global-symbol');
    if (!symbolEl) return;

    const symbol = symbolEl.innerText;
    try {
        const klines = await fetchKlines(symbol, "1m");
        if (!klines || klines.length < 50) {
            symbolEl.classList.remove('title-green', 'title-red');
            symbolEl.classList.add('title-yellow');
            updateFavicon("images/favicon_yellow.png");
            return;
        }

        const closes = klines.map(k => k.close);
        const ema10 = calculateEMA(closes, 10);
        const ema20 = calculateEMA(closes, 20);
        const ema50 = calculateEMA(closes, 50);

        if (ema10 === null || ema20 === null || ema50 === null) return;

        const isPerfectGreen = (ema10 > ema20) && (ema20 > ema50);
        const isPerfectRed = (ema50 > ema20) && (ema20 > ema10);

        let colorClass = "title-yellow";
        let faviconPath = "images/favicon_yellow.png";

        if (isPerfectGreen) {
            colorClass = "title-green";
            faviconPath = "images/favicon_green.png";
        } else if (isPerfectRed) {
            colorClass = "title-red";
            faviconPath = "images/favicon_red.png";
        }

        // Apply classes
        symbolEl.classList.remove('title-green', 'title-red', 'title-yellow');
        symbolEl.classList.add(colorClass);

        // Update Favicon (on all pages)
        updateFavicon(faviconPath);

    } catch (e) {
        console.error("1M EMA coloring update failed", e);
        symbolEl.classList.remove('title-green', 'title-red');
        symbolEl.classList.add('title-yellow');
        updateFavicon("images/favicon_yellow.png");
    }
}

function updateFavicon(faviconPath) {
    let link = document.querySelector("link[rel*='icon']");
    if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.getElementsByTagName('head')[0].appendChild(link);
    }
    link.href = faviconPath;
}

// Global script should handle the interval
window.haColoringInterval = setInterval(updateTitleAndFavicon, 5000); // 5s is plenty for 1d color
updateTitleAndFavicon(); // Initial run

// Expose globally for manual triggers (e.g. when symbol changes)
window.updateTitleAndFavicon = updateTitleAndFavicon;
