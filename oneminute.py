#!/usr/bin/python3
import pandas, requests, time, socket, os, sys
from termcolor import colored
from datetime import datetime

# Configuration
SYMBOL = "BTCUSDT"

# Argument Parsing
INTERVAL = "1m"
TIMEFRAME_LABEL = "1 MINUTE"

if "--3m" in sys.argv:
    INTERVAL = "3m"
    TIMEFRAME_LABEL = "3 MINUTE"
elif "--5m" in sys.argv:
    INTERVAL = "5m"
    TIMEFRAME_LABEL = "5 MINUTE"
elif "--1m" in sys.argv:
    INTERVAL = "1m"
    TIMEFRAME_LABEL = "1 MINUTE"

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    chat_id = "@futures_wolves_rise"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    try:
        response = requests.get(url, params=params)
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
    candlestick['20EMA'] = candlestick['close'].ewm(span=20, adjust=False).mean()
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
    heikin_ashi_df['body'] = (heikin_ashi_df['ha_close'] - heikin_ashi_df['ha_open']).abs()
    heikin_ashi_df['volume'] = klines['volume']
    heikin_ashi_df['color'] = heikin_ashi_df.apply(lambda row: 'GREEN' if row['ha_close'] >= row['ha_open'] else 'RED', axis=1)
    heikin_ashi_df['20MA'] = klines['close'].rolling(window=20).mean()
    heikin_ashi_df['10EMA'] = klines['close'].ewm(span=10, adjust=False).mean()
    heikin_ashi_df['20EMA'] = klines['close'].ewm(span=20, adjust=False).mean()
    heikin_ashi_df['50EMA'] = klines['close'].ewm(span=50, adjust=False).mean()
    heikin_ashi_df['100EMA'] = klines['close'].ewm(span=100, adjust=False).mean()
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', '20MA', '10EMA', '20EMA', '50EMA', '100EMA']
    for col in result_cols: heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v, 2) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def one_minute_short(pair, interval, label):
    try:
        timeframe = heikin_ashi(get_klines(pair, interval))
        last_candle = timeframe.iloc[-1]
        
        # 💥 Indicators to check 💥
        ma20 = last_candle['20MA']
        ema10 = last_candle['10EMA']
        ema20 = last_candle['20EMA']
        ema50 = last_candle['50EMA']

        indicators = [ma20, ema10, ema20]
        min_ind = min(indicators)
        max_ind = max(indicators)

        if last_candle['color'] == 'RED':
            name = pair.replace('USDT', '')
            if last_candle['ha_low'] < min_ind and last_candle['ha_high'] > max_ind:
                telegram_bot_sendtext(f"💥 {name} {label} SWALLOW DUMP 💥")
                exit()

            if last_candle['ha_open'] < ema50 and ma20 > ema10 and ema20 > ema10:
                telegram_bot_sendtext(f"🚨 {name} {label} EMA Downtrend 🚨")
                exit()
    except Exception as e:
        print(f"Warning: Failed to fetch {pair} - {e}")

print(f"Monitoring {INTERVAL} {colored('SHORT', 'red')} entry for {SYMBOL}...")

try:
    while True:
        try:
            one_minute_short(SYMBOL, INTERVAL, TIMEFRAME_LABEL)
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
