#!/usr/bin/python3
import pandas, requests, time, socket, os, sys, argparse
from termcolor import colored
from datetime import datetime

# Configuration
parser = argparse.ArgumentParser(description='Stoploss monitor script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol.upper()
if not (SYMBOL.endswith('USDT') or SYMBOL.endswith('USDC')):
    SYMBOL += 'USDT'

# Condition Selection
print("\nSelect condition to trigger:")
print("1. PRESSING EMA10")
print("2. SWALLOW EMA20 EMA50")
print("3. EMA Downtrend")
print("0. ALL")
choice = input("ENTER CONDITION: ").strip()
CONDITION_SELECTION = int(choice) if choice.isdigit() and choice in ['1', '2', '3'] else 0

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
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
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
    heikin_ashi_df['10EMA'] = klines['close'].ewm(span=10, adjust=False).mean()
    heikin_ashi_df['20EMA'] = klines['close'].ewm(span=20, adjust=False).mean()
    heikin_ashi_df['50EMA'] = klines['close'].ewm(span=50, adjust=False).mean()
    heikin_ashi_df['100EMA'] = klines['close'].ewm(span=100, adjust=False).mean()
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', '10EMA', '20EMA', '50EMA', '100EMA']
    for col in result_cols: heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v, 2) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def one_minute_short(pair, interval, label):
    try:
        timeframe = heikin_ashi(get_klines(pair, interval))
        last_candle = timeframe.iloc[-1]
        name = pair.replace('USDT', '')

        # 💥 Indicators to check 💥
        ema10 = last_candle['10EMA']
        ema20 = last_candle['20EMA']
        ema50 = last_candle['50EMA']

        # 1. Consecutive 3 candles open below EMA10
        if CONDITION_SELECTION in [0, 1]:
            last_3 = timeframe.tail(3)
            if len(last_3) == 3 and (last_3['ha_open'] < last_3['10EMA']).all() and (last_3['ha_open'] < last_3['20EMA']).all():
                telegram_bot_sendtext(f"🚨 {name} {label} PRESSING EMA 10 & 20 🚨")
                exit()

        # 2. Swallow EMA20 EMA50
        if CONDITION_SELECTION in [0, 2]:
            if last_candle['ha_close'] < min(ema20, ema50) and last_candle['ha_open'] > max(ema20, ema50):
                telegram_bot_sendtext(f"💥 {name} {label} SWALLOW EMA20 EMA50 💥")
                exit()

        # 3. EMA Downtrend
        if CONDITION_SELECTION in [0, 3]:
            if last_candle['ha_open'] < ema50 and ema20 > ema10:
                telegram_bot_sendtext(f"🚨 {name} {label} EMA Downtrend 🚨")
                exit()

    except Exception as e: print(f"Warning: Failed to fetch {pair} - {e}")
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
