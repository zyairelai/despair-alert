async function updateTitleAndFavicon() {
    // Both Main Dashboard and Trend page now use this logic
    const symbolEl = document.getElementById('global-symbol');
    if (!symbolEl) return;

    const symbol = symbolEl.innerText;
    try {
        const klines = await fetchKlines(symbol, "1d");
        if (!klines || klines.length === 0) {
            symbolEl.classList.remove('title-green', 'title-red');
            symbolEl.classList.add('title-yellow');
            return;
        }

        const last = klines[klines.length - 1];
        const isGreen = last.close > last.open;

        let colorClass = isGreen ? "title-green" : "title-red";
        let faviconPath = isGreen ? "images/favicon_green.png" : "images/favicon_red.png";

        // Apply classes
        symbolEl.classList.remove('title-green', 'title-red', 'title-yellow');
        symbolEl.classList.add(colorClass);

        // Update Favicon (on all pages)
        updateFavicon(faviconPath);

    } catch (e) {
        console.error("1D coloring update failed", e);
        symbolEl.classList.remove('title-green', 'title-red');
        symbolEl.classList.add('title-yellow');
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
