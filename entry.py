#!/usr/bin/python3

import time, socket, os
from datetime import datetime
try: import pandas, requests
except ImportError:
    print("Library not found, run:\npip3 install pandas requests --break-system-packages")
    exit(1)

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    chat_id = "@futures_wolves_rise"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

# telegram_bot_sendtext("Telegram works!")
print("Waiting for entry...\n")

session = requests.Session()
def get_klines(pair, interval):
    spot_url = "https://api.binance.com/api/v1/klines"
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = []
    for x in data: result.append([x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])])
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick["body"] = (candlestick["close"] - candlestick["open"]).abs()
    candlestick["upper_wick"] = candlestick["high"] - candlestick[["open", "close"]].max(axis=1)
    candlestick["lower_wick"] = candlestick[["open", "close"]].min(axis=1) - candlestick["low"]
    return candlestick

def waiting_for_entry(pair, interval):
    timeframe = get_klines(pair, interval)

    # 1. Structure Break (Lower Low + Momentum)
    low_condition = timeframe['close'].iloc[-1] < timeframe['low'].iloc[-5:-1].min()
    momentum_condition = timeframe['body'].iloc[-1] > timeframe['body'].iloc[-5:-1].sum()
    decisive_breakdown = low_condition and momentum_condition

    # 2. Shooting Star
    is_shooting_star = (
        timeframe['close'].iloc[-1] < timeframe['open'].iloc[-1] and
        timeframe['high'].iloc[-1] >= timeframe['high'].iloc[-5:].max() and
        timeframe['upper_wick'].iloc[-1] > timeframe['body'].iloc[-1] * 2 + timeframe['lower_wick'].iloc[-1]) or \
        timeframe['upper_wick'].iloc[-1] > (timeframe['body'].iloc[-1] + timeframe['lower_wick'].iloc[-1]) * 2

    # 3. Bearish Engulfing
    is_bearish_engulfing = (
        timeframe['close'].iloc[-1] < timeframe['low'].iloc[-3:-1].min() and
        timeframe['body'].iloc[-1] > timeframe['body'].iloc[-3:-1].max())

    if decisive_breakdown:
        telegram_bot_sendtext(f"📉 {interval} MOMENTUM BREAKDOWN 📉")
        sleep_or_exit(interval)
    elif is_shooting_star:
        telegram_bot_sendtext(f"🎯 {interval} SHOOTING STAR 🎯")
        sleep_or_exit(interval)
    elif is_bearish_engulfing:
        telegram_bot_sendtext(f"🐻 {interval} BEARISH ENGULFING 🐻")
        sleep_or_exit(interval)

def sleep_or_exit(interval):
    time.sleep({"5m": 300, "15m": 900, "1h": 3600}.get(interval, 300))
    # exit()

try:
    while True:
        try:
            waiting_for_entry("BTCUSDT", "1h")
            waiting_for_entry("BTCUSDT", "15m")
            waiting_for_entry("BTCUSDT", "5m")
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.\n")
