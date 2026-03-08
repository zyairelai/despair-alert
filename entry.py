#!/usr/bin/python3
# python-argcomplete-ok

import pandas, requests, time, socket, os, sys, argparse, argcomplete
from termcolor import colored
from datetime import datetime

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    response = requests.get(url, params=params)
    return response.json()

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
    heikin_ashi_df['100EMA'] = klines['close'].ewm(span=100, adjust=False).mean()
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', '20MA', '10EMA', '20EMA', '100EMA']
    for col in result_cols: heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def main_direction(pair):
    timeframe = heikin_ashi(get_klines(pair, '2h'))
    if timeframe['color'].iloc[-1] == 'RED': return "Down"
    if timeframe['color'].iloc[-1] == 'GREEN': return "Up"
    return None

def check_entry(pair, side, trend):
    if trend and side != 'Both' and trend != side: return
    minute_15m = get_klines(pair, '15m')
    minute_5m = get_klines(pair, '5m')

    if side in ['Down', 'Both'] and (trend == "Down" or trend is None):
        if minute_15m['close'].iloc[-2] >= minute_15m['20EMA'].iloc[-2] and \
            minute_15m['close'].iloc[-1] < minute_15m['20EMA'].iloc[-1] and \
            minute_5m['close'].iloc[-1] < minute_5m['20EMA'].iloc[-1]:
            telegram_bot_sendtext("💥 15m + 5m Trend Crossover (Short) 💥")
            exit()

    if side in ['Up', 'Both'] and (trend == "Up" or trend is None):
        if minute_15m['close'].iloc[-2] <= minute_15m['20EMA'].iloc[-2] and \
            minute_15m['close'].iloc[-1] > minute_15m['20EMA'].iloc[-1] and \
            minute_5m['close'].iloc[-1] > minute_5m['20EMA'].iloc[-1]:
            telegram_bot_sendtext("🚀 15m + 5m Trend Crossover (Long) 🚀")
            exit()

parser = argparse.ArgumentParser(description='Trade entry script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
parser.add_argument('--both', dest='both', action='store_true', help='Monitor BOTH sides')
parser.add_argument('--long-only', action='store_true', help='Monitor LONG')
parser.add_argument('--short-only', action='store_true', help='Monitor SHORT')
parser.add_argument('--direction', action='store_true', help='Use 2H trend direction')

argcomplete.autocomplete(parser)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol

if args.both: side = 'BOTH'
elif args.long_only: side = 'LONG'
elif args.short_only: side = 'SHORT'
else: side = 'BOTH'  # Default is now BOTH

current_direction = "INITIALIZING"
try:
    while True:
        try:
            trend = main_direction(SYMBOL) if args.direction else None
            if trend != current_direction:
                if current_direction != "INITIALIZING" and args.direction:
                    print(f"\n{colored('[!!] Direction Changed!', 'yellow', attrs=['bold'])}")

                if args.direction:
                    color = "green" if trend == "Up" else "red" if trend == "Down" else "white"
                    print(f"Main Direction: {colored(trend, color)}")
                    trend_side = "LONG" if trend == "Up" else "SHORT"
                    monitoring_side = trend_side if (side == 'BOTH' or side == trend_side) else f"Waiting for {side} alignment..."
                else:
                    monitoring_side = side
                    color = "white"

                if args.direction or current_direction == "INITIALIZING":
                    print(f"Monitoring 15m + 5m {colored(monitoring_side, color)} entry...")

                current_direction = trend

            target_side = side.capitalize().replace('Short', 'Down').replace('Long', 'Up')
            check_entry(SYMBOL, target_side, trend)
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
