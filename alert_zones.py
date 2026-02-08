#!/usr/bin/python3

import time, socket, os, sys
from datetime import datetime, timedelta
try: import pandas, requests
except ImportError:
    print("Library not found, run:\npip3 install pandas requests --break-system-packages")
    exit(1)

# --- Configuration ---
SYMBOL = "BTCUSDT"
WHOLE_NUMBER = [60000, 70000, 80000]

BUFFER = 0.1
ENABLE_4H = True
ENABLE_1D_MIDDLE_LINE = True
ENABLE_12H_MIDDLE_LINE = True
SLEEP_INTERVAL = "1h"

def sleep_until_next(interval):
    if not interval or interval.lower() in ["-", "none", "na"]: sys.exit(0)
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
        next_time += timedelta(seconds=1)
    else:
        print(f"Unknown interval format: {interval}")
        sys.exit(1)

    sleep_seconds = (next_time - now).total_seconds()
    if sleep_seconds > 0: time.sleep(sleep_seconds)

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

session = requests.Session()
def get_klines(pair, interval):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = []
    for x in data: result.append([x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])])
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    return candlestick

def prepare_zones(timeframe):
    df = get_klines(SYMBOL, timeframe)

    high = df["high"].iloc[-2]
    low = df["low"].iloc[-2]
    diff = high - low

    zones = {"high": high, "low": low, "middle": (high + low) / 2}

    if timeframe in ["12h", "1d"]:
        current_buffer = BUFFER
        zones["high_lower"] = high - int(diff * current_buffer)
        zones["low_lower"] = low - int(diff * current_buffer)

        # zones["middle_lower"] = zones["middle"] - int(diff * current_buffer / 2)
        # zones["middle_lower"] = zones["middle"] - int(zones['middle'] / 1000)
        zones["middle_lower"] = zones["middle"]

    return zones

def price_alert(zones, timeframe, five_minute):
    last_high = five_minute["high"].iloc[-1]
    last_low = five_minute["low"].iloc[-1]
    emoji = "🚨" * (3 if timeframe == "1d" else 2 if timeframe == "12h" else 1)

    # 12h Zones
    if timeframe == "12h":
        # High Zone Check
        hf_high = int(zones['high'] / 1000)
        high_touch = (last_high >= zones['high_lower'] and last_high <= zones['high'])
        high_cross = (last_high >= (zones['high'] - hf_high) and last_low <= (zones['high'] + hf_high))
        if high_touch or high_cross:
            telegram_bot_sendtext(f"{emoji} {timeframe} High {int(zones['high'])}-{int(zones['high_lower'])}")
            sleep_until_next(SLEEP_INTERVAL)

        # Low Zone Check
        hf_low = int(zones['low'] / 1000)
        low_touch = (last_high >= zones['low_lower'] and last_high <= zones['low'])
        low_cross = (last_high >= (zones['low'] - hf_low) and last_low <= (zones['low'] + hf_low))
        if low_touch or low_cross:
            telegram_bot_sendtext(f"{emoji} {timeframe} Low {int(zones['low'])}-{int(zones['low_lower'])}")
            sleep_until_next(SLEEP_INTERVAL)

    # 4h Levels (No Zones, only crossing)
    if timeframe == "4h":
        if last_high >= zones['high'] and last_low <= zones['high']:
            telegram_bot_sendtext(f"{emoji} {timeframe} High Cross at {int(zones['high'])}")
            sleep_until_next(SLEEP_INTERVAL)
        if last_high >= zones['low'] and last_low <= zones['low']:
            telegram_bot_sendtext(f"{emoji} {timeframe} Low Cross at {int(zones['low'])}")
            sleep_until_next(SLEEP_INTERVAL)

    # Middle Line Check (1d and 12h only)
    should_alert_middle = False
    if timeframe == "1d": should_alert_middle = ENABLE_1D_MIDDLE_LINE and zones.get("monitor_mid", True)
    elif timeframe == "12h": should_alert_middle = ENABLE_12H_MIDDLE_LINE

    if should_alert_middle:
        hf_mid = int(zones['middle'] / 1000)
        mid_touch = (last_high >= zones['middle_lower'] and last_high <= zones['middle'])
        mid_cross = (last_high >= (zones['middle'] - hf_mid) and last_low <= (zones['middle'] + hf_mid))
        if mid_touch or mid_cross:
            telegram_bot_sendtext(f"{emoji} {timeframe} Middle {int(zones['middle'])}-{int(zones['middle_lower'])}")
            sleep_until_next(SLEEP_INTERVAL)

def check_whole_numbers(five_minute):
    last_high = five_minute["high"].iloc[-1]
    last_low = five_minute["low"].iloc[-1]
    for level in WHOLE_NUMBER:
        buffer = int(level / 1000)
        if last_high >= (level - buffer) and last_low <= (level + buffer):
            telegram_bot_sendtext(f"💥 WHOLE NUMBER TOUCH 💥 {level}")
            sleep_until_next(SLEEP_INTERVAL)

def main():
    timeframes = ["12h"]
    if ENABLE_1D_MIDDLE_LINE: timeframes.insert(0, "1d")
    if ENABLE_4H: timeframes.append("4h")
    # print(f"Monitoring timeframes: {', '.join(timeframes)}")

    zones_map = {}
    for tf in timeframes: zones_map[tf] = prepare_zones(tf)

    # Filter 1d Middle based on 12h Range
    if "1d" in zones_map and "12h" in zones_map:
        mid_1d = zones_map["1d"]["middle"]
        high_12h = zones_map["12h"]["high"]
        low_12h = zones_map["12h"]["low"]
        if mid_1d > high_12h or mid_1d < low_12h:
            zones_map["1d"]["monitor_mid"] = False
        else:
            zones_map["1d"]["monitor_mid"] = True

    # Show Levels
    for tf in timeframes:
        zones = zones_map[tf]
        if tf == "1d":
            if zones.get("monitor_mid", True):
                print(f"Previous {tf} Middle Line: {int(zones['middle'])}")
        elif tf == "12h":
            print(f"\nPrevious {tf} High Zone: {int(zones['high'])} - {int(zones['high_lower'])}")
            print(f"Previous {tf} Low Zone : {int(zones['low'])} - {int(zones['low_lower'])}")
            print(f"Previous {tf} Mid Zone : {int(zones['middle'])} - {int(zones['middle_lower'])}")
        elif tf == "4h":
            print(f"\nPrevious {tf} High Level: {int(zones['high'])}")
            print(f"Previous {tf} Low Level : {int(zones['low'])}")

    try:
        while True:
            try:
                five_minute = get_klines(SYMBOL, "5m")
                check_whole_numbers(five_minute)

                for tf, zones in zones_map.items():
                    price_alert(zones, tf, five_minute)
                time.sleep(5)
            except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
                print(f"Error: {e}")
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()
