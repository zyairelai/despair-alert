#!/usr/bin/python3

import time, socket, os, pandas, requests
from termcolor import colored

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    if not bot_token:
        print("Error: TELEGRAM_WOLVESRISE environment variable not set.")
        return None
    chat_id = "@futures_wolves_rise"
    send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=html&text={bot_message}'
    try:
        response = requests.get(send_text)
        return response.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

session = requests.Session()
def get_klines(pair, interval):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    return candlestick

def check_standing(pair, interval, condition, ma_period):
    df = get_klines(pair, interval)
    ma_col = f'{ma_period}MA'
    df[ma_col] = df['close'].rolling(window=ma_period).mean()
    
    last_close = df['close'].iloc[-2]
    last_ma = df[ma_col].iloc[-2]
    
    if condition == 'above' and last_close > last_ma:
        return True, last_close, last_ma
    if condition == 'below' and last_close < last_ma:
        return True, last_close, last_ma
    return False, last_close, last_ma

print("The STANDING script is running...\n")

# Interactive Prompts
try:
    tf_input = input("Timeframe (5 or 15): ")
    interval = "5m" if tf_input == "5" else "15m"
    
    cond_input = input("Condition (above or below): ")
    condition = "below" if cond_input.lower().startswith('b') else "above"
    
    ma_period_input = input("MA Period (10 or 20): ")
    ma_period = 20 if ma_period_input == "20" else 10
except (KeyboardInterrupt, EOFError):
    print("\nAborted.")
    exit(1)

label = f"{interval} standing {condition.upper()} {ma_period}MA"
print(f"\nMonitoring: {label}...\n")

try:
    while True:
        try:
            is_met, close, ma = check_standing("BTCUSDT", interval, condition, ma_period)
            if is_met:
                msg = f"⚠️ BTCUSDT {label}"
                telegram_bot_sendtext(msg)
                exit()
            time.sleep(10)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt:
    print("\n\nAborted.")
