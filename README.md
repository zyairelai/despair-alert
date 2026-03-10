# despair-alert
别人恐惧我GG

### `nano ~/.zshrc`
```
alias web='python3 -m http.server 80'
alias webserver='python3 -m http.server 80'

alias despair="/home/kali/despair-alert/despair.py"
alias emacross="/home/kali/despair-alert/emacross.py"
alias entry="/home/kali/despair-alert/entry.py"
alias heikin="/home/kali/despair-alert/heikin.py"
alias linetouch="/home/kali/despair-alert/linetouch.py"
alias oneminute="/home/kali/despair-alert/oneminute.py"
alias pricealert="/home/kali/despair-alert/pricealert.py"
alias standing="/home/kali/despair-alert/standing.py"
alias stoploss="/home/kali/despair-alert/stoploss.py"
alias zones="/home/kali/despair-alert/zones.py"
```
```
# Enable python-argcomplete
autoload -U bashcompinit
bashcompinit

eval "$(register-python-argcomplete --shell zsh /home/kali/despair-alert/zones.py)"
compdef _python_argcomplete zones
```

### To-Do
- One click order for all exchanges
- https://docs.ccxt.com/Exchange-Markets
- Binance
- BingX
- BitGet
- Bybit
- Crypto
- Kucoin
- MEXC
- OKX
