async function updateTitleAndFavicon() {
    // Both Main Dashboard and Trend page now use this logic


    const symbol = document.getElementById('global-symbol').innerText;
    try {
        const klines = await fetchKlines(symbol, "2h");
        if (klines.length < 50) return;

        // Stable HA Calculation
        let haOpen = (klines[0].open + klines[0].close) / 2;
        let haClose = (klines[0].open + klines[0].high + klines[0].low + klines[0].close) / 4;

        for (let i = 1; i < klines.length; i++) {
            const k = klines[i];
            const currentHaClose = (k.open + k.high + k.low + k.close) / 4;
            const currentHaOpen = (haOpen + haClose) / 2;
            haOpen = currentHaOpen;
            haClose = currentHaClose;
        }

        const titleEl = document.getElementById('global-symbol');
        let colorClass = (haClose > haOpen) ? "title-green" : "title-red";
        let faviconPath = (haClose > haOpen) ? "images/favicon_green.png" : "images/favicon_red.png";

        // Apply classes
        titleEl.classList.remove('title-green', 'title-red');
        titleEl.classList.add(colorClass);

        // Update Favicon (on all pages)
        updateFavicon(faviconPath);

    } catch (e) {
        console.error("HA coloring update failed", e);
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
setInterval(updateTitleAndFavicon, 10000);
updateTitleAndFavicon(); // Initial run
