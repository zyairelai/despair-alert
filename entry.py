#!/usr/bin/python3

import pandas, requests, time, socket, os, sys, argparse, argcomplete
from datetime import datetime

# ----- Configuration -----
SYMBOL = "BTCUSDT"

print("\nThe PRECISE ENTRY script is running...\n")
def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    chat_id = "@futures_wolves_rise"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    response = requests.get(url, params=params)
    return response.json()

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
    heikin_ashi_df['body'] = (heikin_ashi_df['ha_close'] - heikin_ashi_df['ha_open']).abs()
    heikin_ashi_df['volume'] = klines['volume']
    heikin_ashi_df['color'] = heikin_ashi_df.apply(lambda row: 'GREEN' if row['ha_close'] >= row['ha_open'] else 'RED', axis=1)
    heikin_ashi_df['20MA'] = klines['close'].rolling(window=20).mean()
    heikin_ashi_df['10EMA'] = klines['close'].ewm(span=10, adjust=False).mean()
    heikin_ashi_df['20EMA'] = klines['close'].ewm(span=20, adjust=False).mean()
    heikin_ashi_df['100EMA'] = klines['close'].ewm(span=100, adjust=False).mean()
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', '20MA', '10EMA', '20EMA', '100EMA']
    for col in result_cols: heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def one_hour_direction(pair):
    timeframe = heikin_ashi(get_klines(pair, '1h'))
    if timeframe['20MA'].iloc[-2] > timeframe['ha_low'].iloc[-1]: return "Downtrend"
    if timeframe['20MA'].iloc[-2] < timeframe['ha_high'].iloc[-1]: return "Uptrend"

def is_downtrend(pair, interval):
    timeframe = get_klines(pair, interval)
    timeframe['20MA'] = timeframe['close'].rolling(window=20).mean()
    if timeframe['20MA'].iloc[-2] > timeframe['20MA'].iloc[-1] and \
       timeframe['20MA'].iloc[-2] > timeframe['close'].iloc[-2]: return True

def is_uptrend(pair, interval):
    timeframe = get_klines(pair, interval)
    timeframe['20MA'] = timeframe['close'].rolling(window=20).mean()
    if timeframe['20MA'].iloc[-2] < timeframe['20MA'].iloc[-1] and \
       timeframe['20MA'].iloc[-2] < timeframe['close'].iloc[-2]: return True

def all_condition_matched(pair, side, check_direction):
    trend = one_hour_direction(pair) if check_direction else None
    if check_direction and side != 'Both' and trend and trend.lower() != side: return

    if side in ['Downtrend', 'Both']:
        if not check_direction or trend == "Downtrend":
            if is_downtrend(pair, '15m') and is_downtrend(pair, '5m'):
                telegram_bot_sendtext("💥 15m + 5m Downtrend Alignment 💥")
                exit()

    if side in ['Uptrend', 'Both']:
        if not check_direction or trend == "Uptrend":
            if is_uptrend(pair, '15m') and is_uptrend(pair, '5m'):
                telegram_bot_sendtext("🚀 15m + 5m Uptrend Alignment 🚀")
                exit()

parser = argparse.ArgumentParser(description='Trade entry script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--both', action='store_true', help='Monitor both sides')
parser.add_argument('--uptrend', action='store_true', help='Monitor uptrend')
parser.add_argument('--downtrend', action='store_true', help='Monitor downtrend')
parser.add_argument('--direction', action='store_true', help='Monitor 1H direction alignment')
parser.add_argument('--smart', action='store_true', help='Both sides + 1H alignment')

argcomplete.autocomplete(parser)
args, unknown = parser.parse_known_args()
side = 'Downtrend'
if args.both: side = 'Both'
if args.uptrend: side = 'Uptrend'
if args.downtrend: side = 'Downtrend'

if args.smart:
    side = 'Both'
    args.direction = True

print(f"Monitoring {side} side{' (With 1H Direction)' if args.direction else ''}...\n")

try:
    while True:
        try:
            all_condition_matched(SYMBOL, side, args.direction)
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
