function getHAForColoring(klines) {
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

async function updateTitleAndFavicon() {
    // Both Main Dashboard and Trend page now use this logic
    const symbolEl = document.getElementById('global-symbol');
    if (!symbolEl) return;

    const symbol = symbolEl.innerText;
    try {
        const klines = await fetchKlines(symbol, "1h");
        if (!klines || klines.length < 50) {
            symbolEl.classList.remove('title-green', 'title-red');
            symbolEl.classList.add('title-yellow');
            updateFavicon("images/favicon_yellow.png");
            return;
        }

        const ha1h = getHAForColoring(klines);
        if (!ha1h) return;

        const isPerfectGreen = ha1h.color === "GREEN" && ha1h.low >= ha1h.open - (ha1h.open * 0.0001);
        const isPerfectRed = ha1h.color === "RED" && ha1h.high <= ha1h.open + (ha1h.open * 0.0001);

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
        console.error("1H coloring update failed", e);
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
