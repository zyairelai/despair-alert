#!/usr/bin/python3

import time, socket, os
try: import pandas, requests
except ImportError:
    print("Library not found, run:\npip3 install pandas requests --break-system-packages")
    exit(1)

targets = [67500, 66600]
for i, t in enumerate(targets, start=1):
    print(f"Target {i}: {t}")

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

# telegram_bot_sendtext("Telegram works!")

session = requests.Session()
def get_klines(pair, interval):
    spot_url = "https://api.binance.com/api/v1/klines"
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick["body"] = (candlestick["close"] - candlestick["open"]).abs()
    candlestick["upper_wick"] = candlestick["high"] - candlestick[["open", "close"]].max(axis=1)
    candlestick["lower_wick"] = candlestick[["open", "close"]].min(axis=1) - candlestick["low"]
    return candlestick

def price_alert():
    cutloss = get_klines("BTCUSDT", "1m")
    for target_price in targets:
        if cutloss["high"].iloc[-1] >= target_price >= cutloss["low"].iloc[-1]:
            telegram_bot_sendtext(f"Price touched target: {target_price}")
            exit()

try:
    while True:
        try:
            price_alert()
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(30)
            continue
except KeyboardInterrupt: print("\n\nAborted.\n")
