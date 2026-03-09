#!/usr/bin/python3

import pandas, requests, time, socket, os, sys
from datetime import datetime
from termcolor import colored

SYMBOL = "BTCUSDT"

# Determine timeframe
INTERVAL = input("Enter timeframe (default 3m): ") or "3m"

# Determine target trend
prompt = f"Check {colored('GREEN', 'green')} or {colored('RED', 'red')} candle? (Default {colored('RED', 'red')}): "
trend_choice = input(prompt).lower()
if trend_choice in ['g', 'green', '1']:
    TARGET_COLOR = "GREEN"
    COLOR_TERM = "green"
else:
    TARGET_COLOR = "RED"
    COLOR_TERM = "red"

WOLF_MSG = f"🐺 HUNTING FOR {TARGET_COLOR} ({INTERVAL}) 🐺"
print("\n" + colored(WOLF_MSG, COLOR_TERM))

def telegram_bot_sendtext(bot_message):
    print("Triggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S")))
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    if not bot_token:
        return
    chat_id = "@futures_wolves_rise"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    try:
        response = requests.get(url, params=params, timeout=5)
        return response.json()
    except Exception as e:
        print(f"Telegram error: {e}")

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

def heikin_ashi(klines):
    heikin_ashi_df = pandas.DataFrame(index=klines.index.values, columns=['ha_open', 'ha_high', 'ha_low', 'ha_close'])
    heikin_ashi_df['ha_close'] = (klines['open'] + klines['high'] + klines['low'] + klines['close']) / 4

    for i in range(len(klines)):
        if i == 0: heikin_ashi_df.iat[0, 0] = klines['open'].iloc[0]
        else: heikin_ashi_df.iat[i, 0] = (heikin_ashi_df.iat[i-1, 0] + heikin_ashi_df.iat[i-1, 3]) / 2

    heikin_ashi_df.insert(0,'timestamp', klines['timestamp'])
    heikin_ashi_df['ha_high'] = heikin_ashi_df.loc[:, ['ha_open', 'ha_close']].join(klines['high']).max(axis=1)
    heikin_ashi_df['ha_low']  = heikin_ashi_df.loc[:, ['ha_open', 'ha_close']].join(klines['low']).min(axis=1)
    heikin_ashi_df['volume'] = klines['volume']
    heikin_ashi_df['body'] = (heikin_ashi_df['ha_close'] - heikin_ashi_df['ha_open']).abs()
    heikin_ashi_df['upper_wick'] = heikin_ashi_df['ha_high'] - heikin_ashi_df[['ha_open', 'ha_close']].max(axis=1)
    heikin_ashi_df['lower_wick'] = heikin_ashi_df[['ha_open', 'ha_close']].min(axis=1) - heikin_ashi_df['ha_low']
    heikin_ashi_df['color'] = heikin_ashi_df.apply(lambda row: 'GREEN' if row['ha_close'] >= row['ha_open'] else 'RED', axis=1)
    heikin_ashi_df['perfect'] = False
    heikin_ashi_df.loc[heikin_ashi_df['color'] == 'GREEN', 'perfect'] = (heikin_ashi_df['ha_low'] == heikin_ashi_df['ha_open'])
    heikin_ashi_df.loc[heikin_ashi_df['color'] == 'RED', 'perfect'] = (heikin_ashi_df['ha_high'] == heikin_ashi_df['ha_open'])
    heikin_ashi_df['20MA'] = klines['close'].rolling(window=20).mean()
    heikin_ashi_df['100EMA'] = klines['close'].ewm(span=100, adjust=False).mean()
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', 'perfect', 'body', 'upper_wick', 'lower_wick', '20MA', '100EMA']
    for col in result_cols: 
        if col not in ['color', 'perfect']:
            heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v, 8) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def heikin_ashi_alert():
    timeframe = heikin_ashi(get_klines(SYMBOL, INTERVAL))
    last_candle = timeframe.iloc[-1]
    
    status_label = "(Perfect)" if last_candle['perfect'] else "(Indecisive)"
    status_msg = f"[{INTERVAL}] {SYMBOL} HEIKIN: {last_candle['color']} {status_label}"
    print(f"\r{status_msg}", end="", flush=True)

    if last_candle['color'] == TARGET_COLOR and last_candle['perfect']:
        emoji = "🚀" if TARGET_COLOR == "GREEN" else "💥"
        msg = f"{emoji} HEIKIN ASHI {INTERVAL} {TARGET_COLOR} {emoji}"
        print("\n")
        print(colored(msg, COLOR_TERM))
        telegram_bot_sendtext(msg)
        exit()

try:
    while True:
        try:
            heikin_ashi_alert()
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
