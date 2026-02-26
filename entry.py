#!/usr/bin/python3

import pandas, requests, time, socket, os
from datetime import datetime

print("\nThe ENTRY script is running...\n")
def telegram_bot_sendtext(bot_message, interval):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    chat_id = "@futures_wolves_rise"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    sleep_or_exit(interval)
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

def waiting_for_entry(pair, interval):
    timeframe = get_klines(pair, interval)
    current_candle = -2

    # 1. Structure Break (Lower Low + Momentum)
    low_condition = timeframe['close'].iloc[current_candle] < timeframe['low'].iloc[current_candle-4:current_candle].min()
    momentum_condition = timeframe['body'].iloc[current_candle] > timeframe['body'].iloc[current_candle-4:current_candle].sum()
    decisive_breakdown = low_condition and momentum_condition

    # 2. Shooting Star
    # Use a slice that handles current_candle correctly for the 'last 5' window
    end_idx = current_candle + 1 if current_candle != -1 else None
    is_shooting_star = (
        timeframe['close'].iloc[current_candle] < timeframe['open'].iloc[current_candle] and
        timeframe['high'].iloc[current_candle] >= timeframe['high'].iloc[current_candle-4:end_idx].max() and
        timeframe['upper_wick'].iloc[current_candle] > timeframe['body'].iloc[current_candle] * 2 + timeframe['lower_wick'].iloc[current_candle]) or \
        timeframe['upper_wick'].iloc[current_candle] > (timeframe['body'].iloc[current_candle] + timeframe['lower_wick'].iloc[current_candle]) * 2

    # 3. Bearish Engulfing
    is_bearish_engulfing = (
        timeframe['close'].iloc[current_candle] < timeframe['low'].iloc[current_candle-2:current_candle].min() and
        timeframe['body'].iloc[current_candle] > timeframe['body'].iloc[current_candle-2:current_candle].max())

    if decisive_breakdown: telegram_bot_sendtext(f"📉 {interval} MOMENTUM BREAKDOWN 📉", interval)
    elif is_shooting_star: telegram_bot_sendtext(f"🎯 {interval} SHOOTING STAR 🎯", interval)
    elif is_bearish_engulfing: telegram_bot_sendtext(f"🐻 {interval} BEARISH ENGULFING 🐻", interval)

def sleep_or_exit(interval):
    # time.sleep({"5m": 300, "15m": 900, "1h": 3600}.get(interval, 300))
    exit()

try:
    while True:
        try:
            # waiting_for_entry("BTCUSDT", "1h")
            # waiting_for_entry("BTCUSDT", "5m")
            waiting_for_entry("BTCUSDT", "15m")
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
