# despair-alert
别人恐惧我GG

### `nano ~/.zshrc`
```
alias web='python3 -m http.server 80'
alias webserver='python3 -m http.server 80'

alias de="/home/kali/despair-alert/despair.py"
alias despair="/home/kali/despair-alert/despair.py"
alias hourbreak="/home/kali/despair-alert/hourbreak.py"
alias monitoring="/home/kali/despair-alert/monitoring.py"
alias oneminute="/home/kali/despair-alert/oneminute.py"
alias zones="/home/kali/despair-alert/zones.py"
```
```
# Enable python-argcomplete
eval "$(register-python-argcomplete sessions.py)"
```
```

### To-Do
- One click order for all exchanges
- https://docs.ccxt.com/Exchange-Markets
- Binance
- BingX
- BitGet
- Bybit
- Crypto.com
- Kucoin
- MEXC
- OKX

### Perfect BEEP
```
function beep() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        if (ctx.state === 'suspended') ctx.resume();
        const osc = ctx.createOscillator();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1000, ctx.currentTime);
        osc.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.3);
    } catch (e) {
        console.error("Beep failed:", e);
    }
}
```