#!/usr/bin/python3

import pandas, requests, time, socket, os, sys, argparse
from datetime import datetime
from termcolor import colored

parser = argparse.ArgumentParser(description='Stoploss monitor script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol
htf = "15m"
ltf = "5m"

# Determine target side
prompt = f"Check {colored('LONG', 'green')}, {colored('SHORT', 'red')}, or {colored('BOTH', 'cyan')}? (Default both): "
side_choice = input(prompt).lower()
if side_choice in ['l', 'long', '1']:
    TARGET_SIDE = "LONG"
    TARGET_COLOR = "green"
elif side_choice in ['s', 'short', '2']:
    TARGET_SIDE = "SHORT"
    TARGET_COLOR = "red"
else:
    TARGET_SIDE = "BOTH"
    TARGET_COLOR = "cyan"

WOLF_MSG = f"🐺 MONITORING {htf} + {ltf} EMA ALIGNMENT FOR {TARGET_SIDE} 🐺"
print("\n" + colored(WOLF_MSG, TARGET_COLOR))

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
    candlestick['50EMA'] = candlestick['close'].ewm(span=50, adjust=False).mean()
    return candlestick

def get_trend_label(df_row, side="UP"):
    if side == "UP":
        # Stricter UP: 10 > 20 > 50
        if df_row['10EMA'] > df_row['20EMA'] > df_row['50EMA']: return colored("UP", "green")
        if df_row['10EMA'] < df_row['20EMA']: return colored("DOWN", "red")
    else:
        # DOWN: 10 < 20 (stays same)
        if df_row['10EMA'] < df_row['20EMA']: return colored("DOWN", "red")
        if df_row['10EMA'] > df_row['20EMA']: return colored("UP", "green")
    return colored("NONE", "yellow")

def ema_double():
    df_htf = get_klines(SYMBOL, htf)
    df_ltf = get_klines(SYMBOL, ltf)

    last_htf = df_htf.iloc[-1]
    last_ltf = df_ltf.iloc[-1]

    # Stricter Long check for HTF/LTF
    trend_htf_val = "UP" if last_htf['10EMA'] > last_htf['20EMA'] > last_htf['50EMA'] else "DOWN" if last_htf['10EMA'] < last_htf['20EMA'] else "NONE"
    trend_ltf_val = "UP" if last_ltf['10EMA'] > last_ltf['20EMA'] > last_ltf['50EMA'] else "DOWN" if last_ltf['10EMA'] < last_ltf['20EMA'] else "NONE"
    
    label_htf = get_trend_label(last_htf, "UP")
    label_ltf = get_trend_label(last_ltf, "UP")

    # Determine Overall status
    if trend_htf_val == trend_ltf_val and trend_htf_val != "NONE":
        overall_side = "LONG" if trend_htf_val == "UP" else "SHORT"
        overall_label = colored(overall_side, "green" if overall_side == "LONG" else "red")
    else:
        overall_side = "INDECISIVE"
        overall_label = colored(overall_side, "yellow")

    # Multi-line output
    output = [
        f"\r[{colored(SYMBOL, 'cyan')}]",
        f"{htf}: {label_htf} (EMA10: {last_htf['10EMA']:.2f} | EMA20: {last_htf['20EMA']:.2f})",
        f"{ltf}: {label_ltf} (EMA10: {last_ltf['10EMA']:.2f} | EMA20: {last_ltf['20EMA']:.2f})",
        f"Overall: {overall_label}"
    ]
    
    # Use ANSI escape sequences to clear the lines and move cursor up
    sys.stdout.write("\033[K" + "\n\033[K".join(output) + f"\033[{len(output)-1}A")
    sys.stdout.flush()

    if overall_side in ["LONG", "SHORT"]:
        if TARGET_SIDE == "BOTH" or TARGET_SIDE == overall_side:
            emoji = "🚀" if overall_side == "LONG" else "💥"
            trend_name = "UPTREND" if overall_side == "LONG" else "DOWNTREND"
            name = SYMBOL.replace('USDT', '')
            msg = f"{emoji} {name} {htf} + {ltf} EMA {trend_name} {emoji}"
            print("\n" * len(output)) # Move past the live status
            print(colored(msg, "green" if overall_side == "LONG" else "red"))
            telegram_bot_sendtext(msg)
            exit()

try:
    while True:
        try:
            ema_double()
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n" * 4 + "Aborted.")
