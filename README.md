# despair-alert
别人恐惧我GG

### `nano ~/.zshrc`
```
alias web='python3 -m http.server 80'
alias webserver='python3 -m http.server 80'

alias despair="/home/kali/despair-alert/despair.py"
alias entry="/home/kali/despair-alert/entry.py"
alias stoploss="/home/kali/despair-alert/stoploss.py"
alias pricealert="/home/kali/despair-alert/pricealert.py"
alias zones="/home/kali/despair-alert/zones.py"

alias e="/home/kali/despair-alert/entry.py"
alias z="/home/kali/despair-alert/zones.py"
```
```
# Enable python-argcomplete
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete --shell zsh /home/kali/despair-alert/entry.py)"
eval "$(register-python-argcomplete --shell zsh /home/kali/despair-alert/zones.py)"
eval "$(register-python-argcomplete --shell zsh /home/kali/despair-alert/stoploss.py)"
compdef _python_argcomplete e
compdef _python_argcomplete entry
compdef _python_argcomplete z
compdef _python_argcomplete zones
compdef _python_argcomplete stoploss
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
