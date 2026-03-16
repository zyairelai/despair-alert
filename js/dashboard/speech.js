let speechQueue = [];
let isSpeaking = false;

function formatForSpeech(text) {
    if (!text) return text;
    let formatted = text;

    // Symbols
    formatted = formatted.replace(/\bBTC\b/g, "BTC");
    formatted = formatted.replace(/\bETH\b/g, "Ethereum");
    formatted = formatted.replace(/\bSOL\b/g, "Solana");
    formatted = formatted.replace(/\bEMA\b/g, "E M A");
    formatted = formatted.replace(/\bHEIKIN\b/gi, "Heikin");
    formatted = formatted.replace(/\bASH\b/gi, "Assh");
    formatted = formatted.replace(/\bASHI\b/gi, "Asshee");

    // Timeframes
    const tfMap = {
        '1m': 'one minute',
        '3m': 'three minute',
        '5m': 'five minute',
        '15m': 'fifteen minute',
        '30m': 'thirty minute',
        '1h': 'one hour',
        '2h': 'two hour',
        '4h': 'four hour',
        '6h': 'six hour',
        '12h': 'twelve hour',
        '1d': 'one day'
    };

    for (const [key, value] of Object.entries(tfMap)) {
        const regex = new RegExp(`\\b${key}\\b`, 'g');
        formatted = formatted.replace(regex, value);
    }

    return formatted;
}

function processSpeechQueue() {
    if (isSpeaking || speechQueue.length === 0) return;

    isSpeaking = true;
    const { text, callback } = speechQueue.shift();

    const spokenText = formatForSpeech(text);
    const msg = new SpeechSynthesisUtterance(spokenText);

    // Improved female voice selection
    const voices = window.speechSynthesis.getVoices();
    const femaleVoice = voices.find(v => {
        const name = v.name.toLowerCase();
        return name.includes('female') ||
            name.includes('zira') ||
            name.includes('samantha') ||
            name.includes('victoria') ||
            name.includes('moira') ||
            name.includes('tessa') ||
            (name.includes('google') && name.includes('uk english male') === false && (name.includes('en-us') || name.includes('en-gb')));
    });

    if (femaleVoice) msg.voice = femaleVoice;
    msg.rate = 1.0;
    msg.pitch = 1.1;

    const wrapCallback = () => {
        isSpeaking = false;
        if (callback) callback();
        processSpeechQueue();
    };

    msg.onend = wrapCallback;
    msg.onerror = (e) => {
        console.error("Speech error:", e);
        wrapCallback();
    };

    window.speechSynthesis.speak(msg);
}

function speak(text, callback) {
    if (!text) return;
    speechQueue.push({ text, callback });
    processSpeechQueue();
}

function clearSpeechQueue() {
    speechQueue = [];
    window.speechSynthesis.cancel();
    isSpeaking = false;
}

// Ensure voices are loaded
if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
