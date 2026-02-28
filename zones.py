#!/usr/bin/python3

import pandas, requests, time, socket, os, sys, argparse, argcomplete
from datetime import datetime, timedelta, timezone
from termcolor import colored

# ----- Configuration -----
SYMBOL = "BTCUSDT"
BUFFER = 0.2
SLEEP_INTERVAL = "1h"

# Targets are now passed via CLI arguments
ENABLE_PREV_1D_MIDDLE = True
ENABLE_PREV_1D_CLOSE = False
ENABLED_TIMEFRAME = ["1d"]

parser = argparse.ArgumentParser(description='The ZONES script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument("--4h", dest="enable_4h", action="store_true", help="Enable 4H Timeframe")
parser.add_argument("--current", dest="current_mode", action="store_true", help="Use Current Timeframe")
parser.add_argument("--exit", dest="exit_mode", action="store_true", help="Exit after triggered")
parser.add_argument("--middle", dest="disable_middle", action="store_true", help="Disable 1D Middle")
parser.add_argument("--no-alert", dest="no_alert", action="store_true", help="Disable Telegram Notifications")
parser.add_argument("--price", dest="price", type=float, nargs='+', help="Set Custom Price(s) Alerts")

argcomplete.autocomplete(parser)
args = parser.parse_args()

if args.disable_middle: ENABLE_PREV_1D_MIDDLE = False
if args.current_mode: ENABLED_TIMEFRAME = ["1d"]
if args.enable_4h: ENABLED_TIMEFRAME.append("4h")
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

print("\nThe ZONES script is running...")
def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S")))
    if args.no_alert: return
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
    # result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    result = [[x[0], int(float(x[1])), int(float(x[2])), int(float(x[3])), int(float(x[4])), int(float(x[5]))] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    return candlestick

def get_dynamic_buffer(timeframe):
    base_buffer = globals().get("BUFFER")
    if base_buffer is None or base_buffer == 0: return 0
    if timeframe in ["1w", "1d"]: return base_buffer
    if timeframe == "12h": return base_buffer * 0.7
    return 0 # else has 0 buffer

def check_duplicated(timeframe, val, levels_data):
    order = ["1w", "1d", "4h"]
    for tf in order:
        if tf == timeframe: break
        if tf not in levels_data: continue
        for name, l_val in levels_data[tf].items():
            buffer_val = get_dynamic_buffer(timeframe) or 0.05 # Min 0.05% for suppression
            if buffer_val > 0:
                if abs(val - l_val) <= (val * (buffer_val / 100) * 2):
                    return f"Same as {tf} {name}"
            elif val == l_val: return f"Same as {tf} {name}"
    return None

def price_alert(timeframe, current_minute, levels_data):
    if timeframe not in ENABLED_TIMEFRAME and timeframe != "1d": return
    df = get_klines(SYMBOL, timeframe)
    idx = -1 if args.current_mode else -2
    high, low = df["high"].iloc[idx], df["low"].iloc[idx]
    middle = (high + low) / 2

    last_high, last_low = current_minute["high"].iloc[-1], current_minute["low"].iloc[-1]
    last_open, last_close = current_minute["open"].iloc[-1], current_minute["close"].iloc[-1]
    is_green = last_close > last_open

    emoji = "🚨" * (4 if timeframe == "1w" else 3 if timeframe == "1d" else 2 if timeframe == "12h" else 1)

    # High/Low Check (Resistance/Support)
    if timeframe in ENABLED_TIMEFRAME:
        for val, name in [(high, "High"), (low, "Low")]:
            buffer_val = get_dynamic_buffer(timeframe)
            if buffer_val > 0:
                threshold = val - (val * (buffer_val / 100))
                triggered = (last_high >= threshold and last_low <= threshold) or (last_high >= val and last_low <= val)
            else: triggered = (last_high >= val and last_low <= val)

            if triggered:
                if check_duplicated(timeframe, val, levels_data): continue
                telegram_bot_sendtext(f"\n{emoji} {timeframe.upper()} {name} at {int(val)}")

    # Middle Check (Only for 1D)
    if timeframe == "1d" and ENABLE_PREV_1D_MIDDLE:
        buffer_val = get_dynamic_buffer(timeframe)
        if buffer_val > 0:
            threshold = middle - (middle * (buffer_val / 100))
            triggered = (last_high >= threshold and last_low <= threshold) or (last_high >= middle and last_low <= middle)
        else: triggered = (last_high >= middle and last_low <= middle)

        if triggered:
            if check_duplicated(timeframe, middle, levels_data): return
            telegram_bot_sendtext(f"\n{emoji} {timeframe.upper()} Middle at {int(middle)}")

    # Custom Price Check
    if args.price:
        for val in args.price:
            if (last_high >= val and last_low <= val):
                # Using a marker to avoid duplicate alerts in the same loop if needed, 
                # but since this is exactly at price, we'll just send it.
                telegram_bot_sendtext(f"\n🎯 Custom Price Alert at {int(val)}")

def refresh_levels(levels_data):
    for timeframe in ["1w", "1d", "4h"]:
        if timeframe not in ENABLED_TIMEFRAME and timeframe != "1d": continue

        df = get_klines(SYMBOL, timeframe)
        idx = -1 if args.current_mode else -2
        h, l = df["high"].iloc[idx], df["low"].iloc[idx]
        c = df["close"].iloc[idx] if timeframe == "1d" else None

        # Only store enabled levels for duplication checks
        temp_levels = {}
        if timeframe in ENABLED_TIMEFRAME:
            temp_levels["High"] = h
            temp_levels["Low"] = l
        if timeframe == "1d" and ENABLE_PREV_1D_MIDDLE: temp_levels["Middle"] = (h + l) / 2
        if timeframe == "1d" and ENABLE_PREV_1D_CLOSE: temp_levels["Close"] = c
        levels_data[timeframe] = temp_levels

        print(f"\n======= {timeframe.upper()} =======")
        current_levels = []
        if timeframe in ENABLED_TIMEFRAME:
            current_levels.extend([("High", levels_data[timeframe]["High"]), ("Low", levels_data[timeframe]["Low"])])

        if timeframe == "1d":
            if ENABLE_PREV_1D_MIDDLE: current_levels.insert(1, ("Middle", levels_data[timeframe]["Middle"]))
            if ENABLE_PREV_1D_CLOSE: current_levels.append(("Close", levels_data[timeframe]["Close"]))

        # Check if all enabled levels are duplicated
        all_duplicated = True
        for name, val in current_levels:
            if not check_duplicated(timeframe, val, levels_data):
                all_duplicated = False
                break

        if all_duplicated and timeframe not in ["1w", "1d"] and not args.current_mode:
            print("DUPLICATED")
            continue

        for name, val in current_levels:
            match = check_duplicated(timeframe, val, levels_data)
            label = "Mid" if name == "Middle" else name

            if match:
                if args.current_mode:
                    out_val = str(int(val))
                    if timeframe == "4h": out_val = colored(out_val, "green")

                    # (dup with 1D high)
                    parts = match.split(" ")
                    tf_dup = parts[2].upper()
                    name_dup = parts[3].lower()
                    if name_dup == "middle": name_dup = "mid"
                    
                    dup_info = f"dup with {tf_dup} {name_dup}"
                    prefix = f"Current {timeframe.upper()}"
                    print(f"{prefix} {label}: {out_val} ({dup_info})")
                else:
                    prefix = f"Prev {timeframe.upper()}"
                    print(f"{prefix} {label}: -")
            else:
                out_val = str(int(val))
                if timeframe == "1w":
                    out_val = colored(out_val, "cyan")
                elif timeframe == "12h":
                    if name == "Middle": out_val = colored(out_val, "magenta")
                    else: out_val = colored(out_val, "blue")
                elif timeframe == "1d" and name == "Middle": out_val = colored(out_val, "red")
                elif timeframe == "1d" and name == "Close": out_val = f"\033[38;5;208m{out_val}\033[0m"
                elif timeframe == "4h": out_val = colored(out_val, "green")

                if timeframe == "1d" and name == "Close": print(f"Daily Open: {out_val}")
                else:
                    prefix = f"Current {timeframe.upper()}" if args.current_mode else f"Prev {timeframe.upper()}"
                    print(f"{prefix} {label}: {out_val}")

    if args.price:
        print("\n======= CUSTOM =======")
        for val in args.price:
            print(f"Price Target: {colored(str(int(val)), 'yellow')}")

def main():
    levels_data = {}
    refresh_levels(levels_data)
    last_refresh_time = None

    try:
        while True:
            try:
                now_utc = datetime.now(timezone.utc)
                refresh_hours = [0, 4, 8, 12, 16, 20]

                if now_utc.hour in refresh_hours and now_utc.minute == 0 and now_utc.second >= 10:
                    current_period = now_utc.replace(minute=0, second=0, microsecond=0)
                    if last_refresh_time != current_period:
                        print("\n==================\n= NEW 4H UPDATED =\n==================")
                        refresh_levels(levels_data)
                        last_refresh_time = current_period

                current_minute = get_klines(SYMBOL, "5m")
                # print(current_minute.tail(3))
                for tf in ["1w", "1d", "4h"]: price_alert(tf, current_minute, levels_data)
                time.sleep(5)
            except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
                print(f"Error: {e}")
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()
