#!/usr/bin/python3
# python-argcomplete-ok

import pandas, requests, time, socket, os, sys, argparse, argcomplete
from datetime import datetime, timedelta, timezone
from termcolor import colored

BUFFER = 0.2
SLEEP_INTERVAL = "1h"
# CUSTOM_BTC_ZONES = [73137, 70545, 62868]

parser = argparse.ArgumentParser(description='The ZONES script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument("--alert", dest="alert_mode", action="store_true", help="Enable Alert Mode")
parser.add_argument("--current", dest="current_mode", action="store_true", help="Use Current Timeframe")
parser.add_argument("--exit", dest="exit_mode", action="store_true", help="Exit after triggered")
parser.add_argument("--fibonacci", dest="fibonacci", action="store_true", help="Enable Fibonacci Levels")
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)

argcomplete.autocomplete(parser)
args = parser.parse_args()
SYMBOL = args.symbol.upper()
if not (SYMBOL.endswith('USDT') or SYMBOL.endswith('USDC')):
    SYMBOL += 'USDT'
if args.exit_mode: SLEEP_INTERVAL = "-"

def sleep_until_next(interval):
    now = datetime.now()
    if interval.endswith("h"):
        hours = int(interval.replace("h", ""))
        hours_to_add = hours - (now.hour % hours)
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=hours_to_add)
        next_time += timedelta(seconds=10)
    elif interval.endswith("m"):
        minutes = int(interval.replace("m", ""))
        minutes_to_add = minutes - (now.minute % minutes)
        next_time = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
        next_time += timedelta(seconds=10)
    else: sys.exit(0)
    sleep_seconds = (next_time - now).total_seconds()
    if sleep_seconds > 0: time.sleep(sleep_seconds)

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    response = requests.get(url, params=params)
    sleep_until_next(globals().get("SLEEP_INTERVAL", "-"))
    return response.json()

session = requests.Session()
def get_klines(pair, interval):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], int(float(x[1])), int(float(x[2])), int(float(x[3])), int(float(x[4])), int(float(x[5]))] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    return candlestick

def get_levels():
    df = get_klines(SYMBOL, "1d")
    idx = -1 if args.current_mode else -2
    h, l = df["high"].iloc[idx], df["low"].iloc[idx]
    mid = (h + l) / 2

    levels = [("High", h, "white")]
    # If not in alert mode (default print mode) or fibonacci is requested, show more levels
    if args.fibonacci or not args.alert_mode: levels.append(("Mid-Up", (h + mid) / 2, "green"))
    levels.append(("Middle", mid, "red"))
    if args.fibonacci or not args.alert_mode: levels.append(("Mid-Low", (mid + l) / 2, "green"))
    levels.append(("Low", l, "white"))
    return levels

def get_4h_levels():
    df = get_klines(SYMBOL, "4h")
    idx = -1 if args.current_mode else -2
    h, l = df["high"].iloc[idx], df["low"].iloc[idx]
    return [("High", h, "white"), ("Low", l, "white")]

def print_levels(levels, timeframe="1D"):
    prefix = f"{'Current' if args.current_mode else 'Prev'} {timeframe}"
    print(f"\n{f' {prefix} ':=^30}")
    for name, val, color in levels:
        print(f"{prefix} {name}: {colored(str(int(val)), color)}")

def main():
    print("\nThe ZONES script is running...")
    levels = get_levels()
    print_levels(levels, "1D")

    if not args.alert_mode:
        levels_4h = get_4h_levels()
        print_levels(levels_4h, "4H")
        return
    try:
        while True:
            try:
                # Use 15m klines to check for touches in the current period
                current_minute = get_klines(SYMBOL, "15m")
                last_high, last_low = current_minute["high"].iloc[-1], current_minute["low"].iloc[-1]

                for name, val, color in levels:
                    threshold = val - (val * (BUFFER / 100))
                    if (last_high >= threshold and last_low <= threshold) or (last_high >= val and last_low <= val):
                        telegram_bot_sendtext(f"\n🚨 1D {name} at {int(val)}")

                time.sleep(5)
            except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
                print(f"Error: {e}")
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()
