#!/usr/bin/python3

import time, socket, os, sys
from datetime import datetime, timedelta
try: import pandas, requests
except ImportError:
    print("Library not found, run:\npip3 install pandas requests --break-system-packages")
    exit(1)

# --- Configuration ---
SLEEP = True
SYMBOL = "BTCUSDT"

def sleep_until_next_hour():
    now = datetime.now()
    next_hour = (now.replace(minute=0, second=10, microsecond=0) + timedelta(hours=1))
    sleep_seconds = (next_hour - now).total_seconds()
    if sleep_seconds > 0: time.sleep(sleep_seconds)

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    if not bot_token:
        print("Error: TELEGRAM_LIVERMORE environment variable not set.")
        return
    chat_id = "@swinglivermore"
    send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=html&text={bot_message}'
    try:
        response = requests.get(send_text, timeout=10)
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
    result = []
    for x in data: result.append([x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])])
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    return candlestick

def prepare_levels():
    levels = {}

    # 1d Middle
    df_1d = get_klines(SYMBOL, "1d")
    h_1d = df_1d["high"].iloc[-2]
    l_1d = df_1d["low"].iloc[-2]
    levels["1d_middle"] = (h_1d + l_1d) / 2

    # 12h High/Low/Middle
    df_12h = get_klines(SYMBOL, "12h")
    h_12h = df_12h["high"].iloc[-2]
    l_12h = df_12h["low"].iloc[-2]
    levels["12h_high"] = h_12h
    levels["12h_low"] = l_12h
    levels["12h_middle"] = (h_12h + l_12h) / 2

    # 4h High/Low
    df_4h = get_klines(SYMBOL, "4h")
    levels["4h_high"] = df_4h["high"].iloc[-2]
    levels["4h_low"] = df_4h["low"].iloc[-2]
    print("\n1d")
    print(f"middle : {int(levels['1d_middle'])}")
    print("\n12h")
    print(f"high   : {int(levels['12h_high'])}")
    print(f"low    : {int(levels['12h_low'])}")
    print(f"middle : {int(levels['12h_middle'])}")
    print("\n4h")
    print(f"high   : {int(levels['4h_high'])}")
    print(f"low    : {int(levels['4h_low'])}\n")

    return levels

def check_crossings(levels):
    five_minute = get_klines(SYMBOL, "5m")
    last_h = five_minute["high"].iloc[-1]
    last_l = five_minute["low"].iloc[-1]

    for label, price in levels.items():
        if last_h > price and last_l < price:
            emoji = "🎯"
            if "1d" in label: emoji = "🚨🚨🚨"
            elif "12h" in label: emoji = "🚨🚨"
            else: emoji = "🚨"

            msg = f"{emoji} BTC Cross {label.replace('_', ' ').title()} at {int(price)}"
            telegram_bot_sendtext(msg)
            if SLEEP:
                sleep_until_next_hour()
                return True
    return False

def main():
    print(f"Monitoring levels for {SYMBOL}...")

    while True:
        try:
            levels = prepare_levels()
            start_time = time.time()
            while time.time() - start_time < 300: # Refresh levels every 5 mins
                if check_crossings(levels):
                    break
                time.sleep(10)

        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Error: {e}")
            time.sleep(30)
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit()

if __name__ == "__main__":
    main()
