const alerts = {
    price: { active: false, interval: null, lastTriggerCandleTime: null },
    'ema-cross': { active: false, interval: null },
    heikin: { active: false, interval: null },
    rawcandle: { active: false, interval: null },
    standing: { active: false, interval: null },
    'line-touch': { active: false, interval: null },
    liquidity: { active: false, interval: null }
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

        clearSpeechQueue(); // Immediately silence when stopping
        if (alert.uiBackupTimeout) clearTimeout(alert.uiBackupTimeout);

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
// Secret Telegram Toggle (Main Dashboard Only)
window.telegramEnabled = false;
let teleBuffer = "";
document.addEventListener('keydown', (e) => {
    // Basic buffer logic to detect "te", "tt", "on", "off"
    teleBuffer += e.key.toLowerCase();
    if (teleBuffer.length > 5) teleBuffer = teleBuffer.slice(-5);

    const lastTwo = teleBuffer.slice(-2);
    const lastThree = teleBuffer.slice(-3);

    if (!window.telegramEnabled && (lastTwo === "te" || lastTwo === "tt" || lastTwo === "on")) {
        window.telegramEnabled = true;
        console.log("SECRET: Telegram Alerts Enabled.");

        // Play pickup sound
        const audio = new Audio('images/pickup.mp3');
        audio.play().catch(err => console.error("Sound play failed:", err));

        teleBuffer = ""; // Reset buffer
    } else if (window.telegramEnabled && (lastThree === "off" || lastTwo === "zz" || lastTwo === "oo")) {
        window.telegramEnabled = false;
        console.log("SECRET: Telegram Alerts Disabled.");

        // Play gameover sound
        const audio = new Audio('images/gameover.mp3');
        audio.play().catch(err => console.error("Sound play failed:", err));

        teleBuffer = ""; // Reset buffer
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const symbolBtn = document.getElementById('global-symbol');
    const storedSymbol = localStorage.getItem('globalSymbol') || 'BTCUSDT';
    if (symbolBtn) symbolBtn.innerText = storedSymbol;
});
updateGlobalSymbol();

// Init all condition elements for color-coded mode
document.querySelectorAll('select, .condition-toggle').forEach(el => {
    if (el.id !== 'global-symbol') {
        updateConditionUI(el);
    }
});
