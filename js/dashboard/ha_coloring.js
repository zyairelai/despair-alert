async function updateTitleAndFavicon() {
    // Both Main Dashboard and Trend page now use this logic
    const symbol = document.getElementById('global-symbol').innerText;
    try {
        const klines = await fetchKlines(symbol, "1d");
        if (klines.length === 0) return;

        const last = klines[klines.length - 1];
        const isGreen = last.close > last.open;

        const titleEl = document.getElementById('global-symbol');
        let colorClass = isGreen ? "title-green" : "title-red";
        let faviconPath = isGreen ? "images/favicon_green.png" : "images/favicon_red.png";

        // Apply classes
        titleEl.classList.remove('title-green', 'title-red', 'title-yellow');
        titleEl.classList.add(colorClass);

        // Update Favicon (on all pages)
        updateFavicon(faviconPath);

    } catch (e) {
        console.error("1D coloring update failed", e);
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
setInterval(updateTitleAndFavicon, 5000); // 5s is plenty for 1d color
updateTitleAndFavicon(); // Initial run
