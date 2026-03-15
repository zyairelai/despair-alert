function toggleTFMenu(id) {
    const menu = document.getElementById(`${id}-tf-menu`);
    const card = document.getElementById(`${id}-card`);
    const isShowing = menu.classList.contains('show');

    // Close all others and remove z-active
    document.querySelectorAll('.tf-dropdown-menu').forEach(m => m.classList.remove('show'));
    document.querySelectorAll('.alert-card').forEach(c => c.classList.remove('z-active'));

    if (!isShowing) {
        menu.classList.add('show');
        if (card) card.classList.add('z-active');
    }
}

function setTF(id, val) {
    const menu = document.getElementById(`${id}-tf-menu`);
    const trigger = document.getElementById(`${id}-tf-trigger`);
    const card = document.getElementById(`${id}-card`);
    if (!menu || !trigger) return;

    // Update data attribute
    menu.dataset.value = val;

    // Update trigger text
    trigger.innerText = val;

    // Update button states in grid
    const buttons = menu.querySelectorAll('.tf-btn');
    buttons.forEach(btn => {
        if (btn.innerText.toLowerCase() === val.toLowerCase()) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Close menu and remove z-active
    menu.classList.remove('show');
    if (card) card.classList.remove('z-active');
    console.log(`${id} timeframe set to: ${val}`);
}

function updateSelectColor(el) {
    const val = el.value.toUpperCase();
    if (val.includes('GREEN') || val.includes('UP') || val.includes('ABOVE')) {
        el.classList.remove('red-mode');
        el.classList.add('green-mode');
    } else if (val.includes('RED') || val.includes('DOWN') || val.includes('BELOW')) {
        el.classList.remove('green-mode');
        el.classList.add('red-mode');
    }
}

async function updateGlobalSymbol() {
    const symbol = document.getElementById('global-symbol').value;
    console.log("Global symbol updated to:", symbol);
    await fetchDailyLevels(symbol);
}
