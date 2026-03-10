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
ltf = "3m"

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
    return candlestick

def check_entry():
    df_htf = get_klines(SYMBOL, htf)
    df_ltf = get_klines(SYMBOL, ltf)

    last_htf = df_htf.iloc[-1]
    last_ltf = df_ltf.iloc[-1]

    trend_htf = "UP" if last_htf['10EMA'] > last_htf['20EMA'] else "DOWN"
    trend_ltf = "UP" if last_ltf['10EMA'] > last_ltf['20EMA'] else "DOWN"

    status_msg = f"[{SYMBOL}] {htf}: {trend_htf} | {ltf}: {trend_ltf} ({htf}_10: {last_htf['10EMA']:.2f}, {ltf}_10: {last_ltf['10EMA']:.2f})"
    print(f"\r{status_msg}", end="", flush=True)

    if trend_htf == trend_ltf:
        side = "LONG" if trend_htf == "UP" else "SHORT"
        trend_label = "UPTREND" if side == "LONG" else "DOWNTREND"
        color = "green" if side == "LONG" else "red"
        emoji = "🚀" if side == "LONG" else "💥"

        if TARGET_SIDE == "BOTH" or TARGET_SIDE == side:
            name = SYMBOL.replace('USDT', '')
            msg = f"{emoji} {name} {htf} + {ltf} EMA {trend_label} {emoji}"
            print("\n")
            print(colored(msg, color))
            telegram_bot_sendtext(msg)
            exit()

try:
    while True:
        try:
            check_entry()
            time.sleep(1)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
