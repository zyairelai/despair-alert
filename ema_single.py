#!/usr/bin/python3

import pandas, requests, time, socket, os, sys, argparse
from datetime import datetime
from termcolor import colored

parser = argparse.ArgumentParser(description='Stoploss monitor script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol

# Configuration
INTERVAL = input("Enter timeframe (default 5m): ") or "5m"

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

def telegram_bot_sendtext(bot_message):
    print("Triggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    if not bot_token:
        return
    chat_id = "@swinglivermore"
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

def ema_single():
    global PREV_CROSS
    try:
        df = get_klines(SYMBOL, INTERVAL)
        if len(df) < 4: return

        e10 = df['10EMA'].tolist()
        e20 = df['20EMA'].tolist()

        # Current state
        cur_e10, cur_e20 = e10[-1], e20[-1]
        current_trend = "UPTREND" if cur_e10 > cur_e20 else "DOWNTREND"
        current_color = "green" if current_trend == "UPTREND" else "red"

        # Detect CROSS transitions
        is_cross_up = (current_trend == "UPTREND") and (PREV_CROSS == "DOWNTREND")
        is_cross_down = (current_trend == "DOWNTREND") and (PREV_CROSS == "UPTREND")

        # First run initialization
        if PREV_CROSS is None: PREV_CROSS = current_trend

        # Display lines
        lines = [
            f"\n\r[{colored(SYMBOL, 'cyan')}]",
            colored(WOLF_MSG, TARGET_COLOR),
            "", # Spacer line
            colored(f"CURRENT: {current_trend} ", current_color) + f"(10: {cur_e10:.2f}, 20: {cur_e20:.2f})"
        ]

        # Clear current lines and rewrite dynamically
        output_str = "\033[K" + "\n\033[K".join(lines)
        num_newlines = output_str.count('\n')
        sys.stdout.write(output_str + f"\033[{num_newlines}A")
        sys.stdout.flush()

        # Check for triggers based on targeting mode
        triggered = False
        trigger_trend = ""
        trigger_color = ""

        if (TARGET_TREND == "UPTREND" or TARGET_TREND == "BOTH") and is_cross_up:
            triggered, trigger_trend, trigger_color = True, "UPTREND", "green"

        if not triggered and (TARGET_TREND == "DOWNTREND" or TARGET_TREND == "BOTH") and is_cross_down:
            triggered, trigger_trend, trigger_color = True, "DOWNTREND", "red"

        if triggered:
            emoji = "🚀" if trigger_trend == "UPTREND" else "💥"
            name = SYMBOL.replace('USDT', '')
            msg = f"{emoji} {name} {INTERVAL} EMA 10/20 CROSS: {trigger_trend} {emoji}"
            print("\n" * 5 + colored(msg, trigger_color))
            telegram_bot_sendtext(msg)
            exit()

        PREV_CROSS = current_trend
    except: pass

try:
    while True:
        try:
            ema_single()
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
