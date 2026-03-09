#!/usr/bin/python3

import pandas, requests, time, socket, os, sys, argparse
from datetime import datetime
from termcolor import colored

parser = argparse.ArgumentParser(description='Stoploss monitor script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol

# Determine timeframe
INTERVAL = input("Enter timeframe (default 3m): ") or "3m"

# Determine target trend
prompt = f"Check {colored('UPTREND', 'green')}, {colored('DOWNTREND', 'red')}, or {colored('BOTH', 'cyan')}? (Default down): "
trend_choice = input(prompt).lower()
if trend_choice in ['u', 'up', '1']:
    TARGET_TREND = "UPTREND"
    TARGET_COLOR = "green"
elif trend_choice in ['b', 'both', '3']:
    TARGET_TREND = "BOTH"
    TARGET_COLOR = "cyan"
else:
    TARGET_TREND = "DOWNTREND"
    TARGET_COLOR = "red"

WOLF_MSG = f"🐺 MONITORING EMA 10/20 FOR {TARGET_TREND} ({INTERVAL}) 🐺"
print("\n" + colored(WOLF_MSG, TARGET_COLOR))

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
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick['10EMA'] = candlestick['close'].ewm(span=10, adjust=False).mean()
    candlestick['20EMA'] = candlestick['close'].ewm(span=20, adjust=False).mean()
    return candlestick

PREV_CROSS = None

def monitor_ema():
    global PREV_CROSS
    df = get_klines(SYMBOL, INTERVAL)
    if len(df) < 4: return

    e10 = df['10EMA'].tolist()
    e20 = df['20EMA'].tolist()
    
    # Current state
    cur_e10, cur_e20 = e10[-1], e20[-1]
    current_trend = "UPTREND" if cur_e10 > cur_e20 else "DOWNTREND"
    
    # Movement detection for status message
    is_curving_up = (e10[-1] > e10[-2] > e10[-3] > e10[-4]) and (e20[-1] > e20[-2] > e20[-3] > e20[-4])
    is_curving_down = (e10[-1] < e10[-2] < e10[-3] < e10[-4]) and (e20[-1] < e20[-2] < e20[-3] < e20[-4])
    
    curve_status = "Curving Up" if is_curving_up else "Curving Down" if is_curving_down else "Flat"
    
    # Detect CROSS transitions
    is_cross_up = (current_trend == "UPTREND") and (PREV_CROSS == "DOWNTREND")
    is_cross_down = (current_trend == "DOWNTREND") and (PREV_CROSS == "UPTREND")
    
    # First run initialization
    if PREV_CROSS is None:
        PREV_CROSS = current_trend

    status_msg = f"[{INTERVAL}] {SYMBOL}: {current_trend} | {curve_status} (10: {cur_e10:.2f}, 20: {cur_e20:.2f})"
    print(f"\r{status_msg}", end="", flush=True)

    # Check for triggers based on targeting mode
    triggered = False
    trigger_type = ""
    trigger_trend = ""
    trigger_color = ""

    if TARGET_TREND == "UPTREND" or TARGET_TREND == "BOTH":
        if is_cross_up: triggered, trigger_type, trigger_trend, trigger_color = True, "CROSS", "UPTREND", "green"
        elif is_curving_up: triggered, trigger_type, trigger_trend, trigger_color = True, "CURVING", "UPTREND", "green"
        
    if not triggered and (TARGET_TREND == "DOWNTREND" or TARGET_TREND == "BOTH"):
        if is_cross_down: triggered, trigger_type, trigger_trend, trigger_color = True, "CROSS", "DOWNTREND", "red"
        elif is_curving_down: triggered, trigger_type, trigger_trend, trigger_color = True, "CURVING", "DOWNTREND", "red"

    if triggered:
        emoji = "🚀" if trigger_trend == "UPTREND" else "💥"
        name = SYMBOL.replace('USDT', '')
        msg = f"{emoji} {name} {INTERVAL} EMA 10/20 {trigger_type}: {trigger_trend} {emoji}"
        print("\n")
        print(colored(msg, trigger_color))
        telegram_bot_sendtext(msg)
        exit()

    PREV_CROSS = current_trend

try:
    while True:
        try:
            monitor_ema()
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
