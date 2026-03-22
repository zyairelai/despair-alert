function toggleTFMenu(id) {
    const menu = document.getElementById(`${id}-tf-menu`);
    const trigger = document.getElementById(`${id}-tf-trigger`);
    const selector = trigger ? trigger.closest('.tf-selector') : null;
    const card = menu ? menu.closest('.alert-card') : null;
    const isShowing = menu && menu.classList.contains('show');

    // Close all others and remove active states
    document.querySelectorAll('.tf-dropdown-menu').forEach(m => m.classList.remove('show'));
    document.querySelectorAll('.tf-selector').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.alert-card').forEach(c => c.classList.remove('z-active'));

    if (menu && !isShowing) {
        menu.classList.add('show');
        if (selector) selector.classList.add('active');
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

    // Close menu and remove active states
    menu.classList.remove('show');
    const selector = menu.closest('.tf-selector');
    if (selector) selector.classList.remove('active');
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
    if (!btn || btn.classList.contains('disabled-mode')) return;

    let currentState = btn.dataset.state;
    let nextState, nextText;

    if (id === 'heikin-condition') {
        nextState = currentState === 'perfect-green' ? 'perfect-red' : 'perfect-green';
        nextText = nextState === 'perfect-green' ? 'GREEN' : 'RED';
    } else if (id === 'rawcandle-condition') {
        nextState = currentState === 'green' ? 'red' : 'green';
        nextText = nextState === 'green' ? 'GREEN' : 'RED';
    } else if (id === 'ema-cross-condition') {
        nextState = currentState === 'up' ? 'down' : 'up';
        nextText = nextState === 'up' ? 'UP' : 'DOWN';
    } else if (id === 'ema-alert-condition') {
        nextState = currentState === 'above' ? 'below' : 'above';
        nextText = nextState === 'above' ? 'ABOVE' : 'BELOW';
    }

    btn.dataset.state = nextState;
    btn.innerText = nextText;
    updateConditionUI(btn);

    console.log(`${id} toggled to: ${nextState}`);
}

function toggleEMAAlertMode() {
    const btn = document.getElementById('ema-alert-mode');
    const sideRow = document.getElementById('ema-alert-side-row');
    if (!btn || !sideRow) return;

    const currentState = btn.dataset.state;
    const nextState = currentState === 'touch' ? 'close' : 'touch';
    const sideBtn = document.getElementById('ema-alert-condition');

    btn.dataset.state = nextState;
    btn.innerText = nextState.toUpperCase();

    if (nextState === 'close') {
        sideBtn.classList.remove('disabled-mode');
        sideBtn.innerText = sideBtn.dataset.state.toUpperCase();
        updateConditionUI(sideBtn);
    } else {
        sideBtn.classList.add('disabled-mode');
        sideBtn.classList.remove('green-mode', 'red-mode');
        sideBtn.innerText = "-";
    }

    console.log(`EMA Alert mode toggled to: ${nextState}`);
}

function toggleGlobalSymbol() {
    // const btn = document.getElementById('global-symbol');
    // if (!btn) return;

    // const currentSymbol = btn.innerText;
    // const nextSymbol = currentSymbol === 'BTCUSDT' ? 'ETHUSDT' : 'BTCUSDT';

    // btn.innerText = nextSymbol;
    // updateGlobalSymbol();
    console.log("Symbol toggle disabled (static BTC)");
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
// Input Validation for Numeric Fields
function setupNumericInputs() {
    const numericSelectors = [
        '#price-target-1', '#price-target-2', '#price-target-3',
        '#ema-cross-short', '#ema-cross-long',
        '#line-touch-price', '#standing-level', '#ema-alert-level'
    ];

    numericSelectors.forEach(selector => {
        const el = document.querySelector(selector);
        if (!el) return;

        // Block non-numeric characters on type
        el.addEventListener('keypress', (e) => {
            const charCode = e.which ? e.which : e.keyCode;
            const charStr = String.fromCharCode(charCode);

            // Allow numbers (0-9) and dot (.)
            if (!/[\d\.]/.test(charStr)) {
                e.preventDefault();
            }

            // Prevent multiple dots
            if (charStr === '.' && el.value.includes('.')) {
                e.preventDefault();
            }
        });

        // Block non-numeric content on paste or change (Sanitization)
        el.addEventListener('input', () => {
            el.value = el.value.replace(/[^\d\.]/g, '');
            // Ensure only one dot remains
            const parts = el.value.split('.');
            if (parts.length > 2) {
                el.value = parts[0] + '.' + parts.slice(1).join('');
            }
        });

        // Tab Key behavior
        if (selector.startsWith('#price-target-')) {
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Tab' && !e.shiftKey) {
                    // If input is empty and has a placeholder
                    if (el.value === "" && el.placeholder && el.placeholder !== "") {
                        e.preventDefault();
                        el.value = el.placeholder;
                        console.log(`Tab: Autofilled ${selector} with placeholder value: ${el.placeholder}`);
                    }
                }
            });
        }
    });
}

// Initialize validation on load
document.addEventListener('DOMContentLoaded', setupNumericInputs);
