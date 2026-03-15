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
autoload -U bashcompinit
bashcompinit

# Only zones.py currently has complex flag completion
eval "$(register-python-argcomplete --shell zsh /home/kali/despair-alert/zones.py)"
compdef _python_argcomplete zones
```
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
