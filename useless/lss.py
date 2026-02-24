#!/usr/bin/python3

import pandas, requests, time, socket, os, sys
from datetime import datetime, timedelta
from termcolor import colored

# ----- Configuration -----
SYMBOL = "BTCUSDT"
CANDLE_MUST_BE_GREEN = False
BUFFER = 0.15
ENABLED_LSS = True
ENABLED_MIDD_LINE = ["1d"]
ENABLED_TIMEFRAME = ["1d"]

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    exit()
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

def get_dynamic_buffer(timeframe):
    base_buffer = globals().get("BUFFER")
    if base_buffer is None or base_buffer == 0: return 0
    if timeframe == "1d": return base_buffer
    return 0

def price_alert(timeframe, current_minute, levels_data):
    if timeframe not in ENABLED_TIMEFRAME and timeframe not in ENABLED_MIDD_LINE: return
    df = get_klines(SYMBOL, timeframe)
    high, low = df["high"].iloc[-2], df["low"].iloc[-2]
    middle = (high + low) / 2

    last_high, last_low = current_minute["high"].iloc[-1], current_minute["low"].iloc[-1]
    last_open, last_close = current_minute["open"].iloc[-1], current_minute["close"].iloc[-1]
    is_green = last_close > last_open

    if globals().get("CANDLE_MUST_BE_GREEN") and not is_green: return
    emoji = "🚨🚨🚨"

    # High/Low Check
    for val, name in [(high, "High"), (low, "Low")]:
        buffer_val = get_dynamic_buffer(timeframe)
        if buffer_val > 0:
            threshold = val - (val * (buffer_val / 100))
            triggered = (last_high >= threshold and last_low <= threshold) or (last_high >= val and last_low <= val)
        else: triggered = (last_high >= val and last_low <= val)
        if triggered: telegram_bot_sendtext(f"\n{emoji} {timeframe.upper()} {name} at {int(val)}")

    # Middle Check
    buffer_val = get_dynamic_buffer(timeframe)
    if buffer_val > 0:
        threshold = middle - (middle * (buffer_val / 100))
        triggered = (last_high >= threshold and last_low <= threshold) or (last_high >= middle and last_low <= middle)
    else: triggered = (last_high >= middle and last_low <= middle)
    if triggered: telegram_bot_sendtext(f"{emoji} {timeframe.upper()} Middle at {int(middle)}")

    # LSS Pivot Check
    lss_pivot = levels_data.get(timeframe, {}).get("LSS Pivot")
    if lss_pivot:
        buffer_val = get_dynamic_buffer(timeframe)
        if buffer_val > 0:
            threshold = lss_pivot - (lss_pivot * (buffer_val / 100))
            triggered = (last_high >= threshold and last_low <= threshold) or (last_high >= lss_pivot and last_low <= lss_pivot)
        else: triggered = (last_high >= lss_pivot and last_low <= lss_pivot)
        if triggered: telegram_bot_sendtext(f"\n{emoji} {timeframe.upper()} LSS Pivot at {int(lss_pivot)}")

def main():
    levels_data = {}
    timeframe = "1d"
    df = get_klines(SYMBOL, timeframe)
    h, l, c = df["high"].iloc[-2], df["low"].iloc[-2], df["close"].iloc[-2]

    x_lss = (h + l + c) / 3
    lss_sell = (2 * x_lss) - l
    lss_buy = (2 * x_lss) - h

    levels_data[timeframe] = {
        "High": h,
        "Low": l,
        "Mid": (h + l) / 2,
        "Close": c,
        "LSS Pivot": x_lss,
        "LSS Sell": lss_sell,
        "LSS Buy": lss_buy
    }

    print(f"\n--- {timeframe.upper()} ---")
    print(f"Prev 1D High: {int(h)}")
    print(f"Prev 1D Mid: {colored(str(int(levels_data[timeframe]['Mid'])), 'red')}")
    print(f"Prev 1D Low: {int(l)}")
    print(f"Prev 1D Close: {int(c)}")

    print(f"\n--- LSS ---")
    print(f"LSS Pivot: {colored(str(int(x_lss)), 'blue')}")
    print(f"LSS Buy Number: {colored(str(int(lss_buy)), 'green')}")
    print(f"LSS Sell Number: {colored(str(int(lss_sell)), 'yellow')}")

    try:
        while True:
            try:
                current_minute = get_klines(SYMBOL, "15m")
                price_alert(timeframe, current_minute, levels_data)
                time.sleep(5)
            except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
                print(f"Error: {e}")
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()
