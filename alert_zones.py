#!/usr/bin/python3

import pandas, requests, time, socket, os, sys
from datetime import datetime, timedelta
from termcolor import colored

# ----- Configuration -----
SYMBOL = "BTCUSDT"
CANDLE_MUST_BE_GREEN = False
WHOLE_NUMBER = [100000, 60000]
BUFFER = 0.15
SLEEP_INTERVAL = "-"
ENABLED_MIDD_LINE = ["1d"]
ENABLED_TIMEFRAME = ["1d", "12h", "4h"]
# ENABLED_TIMEFRAME = ["1d", "12h"]

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
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
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
    if timeframe == "1d": return base_buffer
    if timeframe == "12h": return base_buffer * 0.7
    return 0 # else has 0 buffer

def check_duplicated(timeframe, val, levels_data):
    order = ["1d", "12h", "4h"]
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
    if timeframe not in ENABLED_TIMEFRAME and timeframe not in ENABLED_MIDD_LINE: return
    df = get_klines(SYMBOL, timeframe)
    high, low = df["high"].iloc[-2], df["low"].iloc[-2]
    middle = (high + low) / 2

    last_high, last_low = current_minute["high"].iloc[-1], current_minute["low"].iloc[-1]
    last_open, last_close = current_minute["open"].iloc[-1], current_minute["close"].iloc[-1]
    is_green = last_close > last_open

    if globals().get("CANDLE_MUST_BE_GREEN") and not is_green: return
    emoji = "🚨" * (3 if timeframe == "1d" else 2 if timeframe == "12h" else 1)

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

    # Middle Check
    if timeframe in ENABLED_MIDD_LINE:
        buffer_val = get_dynamic_buffer(timeframe)
        if buffer_val > 0:
            threshold = middle - (middle * (buffer_val / 100))
            triggered = (last_high >= threshold and last_low <= threshold) or (last_high >= middle and last_low <= middle)
        else: triggered = (last_high >= middle and last_low <= middle)

        if triggered:
            if check_duplicated(timeframe, middle, levels_data): return
            telegram_bot_sendtext(f"{emoji} {timeframe.upper()} Middle at {int(middle)}")

def check_whole_numbers(current_minute):
    if "WHOLE_NUMBER" not in globals() or not WHOLE_NUMBER: return
    last_high, last_low = current_minute["high"].iloc[-1], current_minute["low"].iloc[-1]
    last_open, last_close = current_minute["open"].iloc[-1], current_minute["close"].iloc[-1]
    is_green = last_close > last_open

    if globals().get("CANDLE_MUST_BE_GREEN") and not is_green: return
    for level in WHOLE_NUMBER:
        buffer_val = get_dynamic_buffer("whole") # Whole numbers have 0 buffer
        if buffer_val > 0:
            threshold = level - (level * (buffer_val / 100))
            triggered = (last_high >= threshold and last_low <= threshold) or (last_high >= level and last_low <= level)
        else: triggered = (last_high >= level and last_low <= level)
        if triggered: telegram_bot_sendtext(f"💥 WHOLE NUMBER TOUCH 💥 {level}")

def main():
    levels_data = {}
    for timeframe in ["1d", "12h", "4h"]:
        if timeframe not in ENABLED_TIMEFRAME and timeframe not in ENABLED_MIDD_LINE: continue

        df = get_klines(SYMBOL, timeframe)
        h, l = df["high"].iloc[-2], df["low"].iloc[-2]

        # Only store enabled levels for duplication checks
        temp_levels = {}
        if timeframe in ENABLED_TIMEFRAME:
            temp_levels["High"] = h
            temp_levels["Low"] = l
        if timeframe in ENABLED_MIDD_LINE:
            temp_levels["Middle"] = (h + l) / 2
        levels_data[timeframe] = temp_levels

        # Skip timeframe if both High and Low are duplicates
        if timeframe != "1d":
            if check_duplicated(timeframe, h, levels_data) and check_duplicated(timeframe, l, levels_data): continue

        print(f"\n--- {timeframe.upper()} ---")
        current_levels = []
        if timeframe in ENABLED_TIMEFRAME:
            current_levels.extend([("High", levels_data[timeframe]["High"]), ("Low", levels_data[timeframe]["Low"])])
        if timeframe in ENABLED_MIDD_LINE: current_levels.insert(1, ("Middle", levels_data[timeframe]["Middle"]))

        for name, val in current_levels:
            match = check_duplicated(timeframe, val, levels_data)
            label = "Mid" if name == "Middle" else name

            if match: print(f"Prev {timeframe.upper()} {label}: -")
            else:
                out_val = str(int(val))
                if timeframe == "12h":
                    if name == "Middle": out_val = colored(out_val, "magenta")
                    else: out_val = colored(out_val, "blue")
                elif timeframe == "1d" and name == "Middle": out_val = colored(out_val, "red")
                elif timeframe == "4h": out_val = colored(out_val, "green")
                print(f"Prev {timeframe.upper()} {label}: {out_val}")

    try:
        while True:
            try:
                current_minute = get_klines(SYMBOL, "15m")
                # print(current_minute.tail(3))
                check_whole_numbers(current_minute)
                for tf in ["1d", "12h", "4h"]: price_alert(tf, current_minute, levels_data)
                time.sleep(5)
            except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
                print(f"Error: {e}")
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()
