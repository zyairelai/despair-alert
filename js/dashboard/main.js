const alerts = {
    price: { active: false, interval: null, lastTriggerCandleTime: null },
    'ema-cross': { active: false, interval: null },
    heikin: { active: false, interval: null },
    standing: { active: false, interval: null },
    'line-touch': { active: false, interval: null }
};

let lastAlertMessages = {};
let lastAlertTimes = {};

function toggleAlert(id) {
    const alert = alerts[id];
    const card = document.getElementById(`${id}-card`);
    if (!card) return;
    const btn = card.querySelector('.toggle-btn');
    const statusText = document.getElementById(`${id}-status`);
    const indicator = statusText.parentElement;

    if (alert.active || btn.innerText === "STOP") {
        console.log(`Stopping ${id}`);
        alert.active = false;
        if (alert.interval) clearInterval(alert.interval);
        alert.interval = null;

        window.speechSynthesis.cancel(); // Immediately silence when stopping

        btn.innerText = "START";
        btn.classList.remove('active');

        // Revert title color
        const title = card.querySelector('.card-header h2');
        if (title) title.classList.remove('running-title');

        indicator.classList.remove('monitoring', 'triggered');
        indicator.classList.add('inactive');
        statusText.innerText = "INACTIVE";
    } else {
        console.log(`Starting ${id}`);
        delete lastAlertMessages[id];
        delete lastAlertTimes[id];
        if (id === 'price') alert.lastTriggerCandleTime = null;

        alert.active = true;
        btn.innerText = "STOP";
        btn.classList.add('active');

        // Make title red
        const title = card.querySelector('.card-header h2');
        if (title) title.classList.add('running-title');

        indicator.classList.remove('inactive', 'triggered');
        indicator.classList.add('monitoring');
        statusText.innerText = "MONITORING";

        checkAlert(id);
        alert.interval = setInterval(() => checkAlert(id), 5000);
    }
}

function testTTS(id) {
    const symbol = document.getElementById('global-symbol').value.replace("USDT", "");
    const menuEl = document.getElementById(`${id}-tf-menu`);
    const tf = menuEl ? menuEl.dataset.value : "5m";
    let text = "";
    if (id === 'price') text = `${symbol} price alert test`;
    else if (id === 'ema-cross') text = `${symbol} ${tf} ema cross test`;
    else if (id === 'heikin') text = `${symbol} ${tf} heikin ashi change`;
    else if (id === 'standing') text = `${symbol} EMA STAND alert test`;
    else if (id === 'line-touch') text = `${symbol} EMA TOUCH alert test`;

    speak(text);
}

// Global click listener to close TF menus
document.addEventListener('click', (e) => {
    if (!e.target.closest('.tf-selector')) {
        document.querySelectorAll('.tf-dropdown-menu').forEach(menu => {
            menu.classList.remove('show');
        });
        document.querySelectorAll('.alert-card').forEach(card => {
            card.classList.remove('z-active');
        });
    }
});

// Initialize
window.speechSynthesis.onvoiceschanged = () => {
    console.log("Voices loaded");
};

// Start logic
updateGlobalSymbol();

// Init all selects for color-coded mode
document.querySelectorAll('select').forEach(sel => {
    if (sel.id !== 'global-symbol') {
        updateSelectColor(sel);
    }
});
