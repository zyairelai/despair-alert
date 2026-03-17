function toggleTFMenu(id) {
    const menu = document.getElementById(`${id}-tf-menu`);
    const card = menu ? menu.closest('.alert-card') : null;
    const isShowing = menu && menu.classList.contains('show');

    // Close all others and remove z-active
    document.querySelectorAll('.tf-dropdown-menu').forEach(m => m.classList.remove('show'));
    document.querySelectorAll('.alert-card').forEach(c => c.classList.remove('z-active'));

    if (menu && !isShowing) {
        menu.classList.add('show');
        if (card) card.classList.add('z-active');
    }
}

function setTF(id, val) {
    const menu = document.getElementById(`${id}-tf-menu`);
    const trigger = document.getElementById(`${id}-tf-trigger`);
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
    const card = menu.closest('.alert-card');
    if (card) card.classList.remove('z-active');
    console.log(`${id} timeframe set to: ${val}`);
}

function updateConditionUI(el) {
    const text = el.innerText.toUpperCase();
    const val = (el.value || text).toUpperCase();
    if (val.includes('GREEN') || val.includes('UP') || val.includes('ABOVE')) {
        el.classList.remove('red-mode');
        el.classList.add('green-mode');
    } else if (val.includes('RED') || val.includes('DOWN') || val.includes('BELOW')) {
        el.classList.remove('green-mode');
        el.classList.add('red-mode');
    }
}

function toggleConditionState(id) {
    const btn = document.getElementById(id);
    if (!btn) return;

    let currentState = btn.dataset.state;
    let nextState, nextText;

    if (id === 'heikin-condition') {
        nextState = currentState === 'perfect-green' ? 'perfect-red' : 'perfect-green';
        nextText = nextState === 'perfect-green' ? 'GREEN' : 'RED';
    } else if (id === 'ema-cross-condition') {
        nextState = currentState === 'up' ? 'down' : 'up';
        nextText = nextState === 'up' ? 'UP' : 'DOWN';
    } else if (id === 'standing-condition') {
        nextState = currentState === 'above' ? 'below' : 'above';
        nextText = nextState === 'above' ? 'ABOVE' : 'BELOW';
    }

    btn.dataset.state = nextState;
    btn.innerText = nextText;
    updateConditionUI(btn);

    console.log(`${id} toggled to: ${nextState}`);
}

function toggleGlobalSymbol() {
    const btn = document.getElementById('global-symbol');
    if (!btn) return;

    const currentSymbol = btn.innerText;
    const nextSymbol = currentSymbol === 'BTCUSDT' ? 'ETHUSDT' : 'BTCUSDT';

    btn.innerText = nextSymbol;
    updateGlobalSymbol();
}

async function updateGlobalSymbol() {
    const btn = document.getElementById('global-symbol');
    if (!btn) return;
    const symbol = btn.innerText;
    console.log("Global symbol switch ->", symbol);

    // Save for cross-page persistence
    localStorage.setItem('globalSymbol', symbol);

    // 1. AUTO-STOP all active monitoring to prevent "BTC targets on ETH"
    if (typeof alerts !== 'undefined') {
        Object.keys(alerts).forEach(id => {
            if (alerts[id].active) {
                console.log(`Auto-stopping ${id} due to symbol switch`);
                toggleAlert(id); // Use existing toggle logic to clean up UI
            }
        });
    }

    // 2. CLEAR price target inputs
    ['price-target-1', 'price-target-2', 'price-target-3'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });

    // 3. REFRESH placeholders/levels
    if (typeof fetchDailyLevels === 'function') {
        await fetchDailyLevels(symbol);
    }
}
