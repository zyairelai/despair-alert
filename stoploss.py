#!/usr/bin/python3

import time, socket, os, pandas, requests, argparse
from datetime import datetime
from termcolor import colored

parser = argparse.ArgumentParser(description='Stoploss monitor script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol

# Interactive Prompts
side_choice = input(f"Check {colored('LONG', 'green')} or {colored('SHORT', 'red')} stoploss? (l/s, default short): ").lower()
if side_choice in ['l', 'long', '1']:
    SIDE = "LONG"
    COLOR = "green"
else:
    SIDE = "SHORT"
    COLOR = "red"

INTERVAL = input("Enter timeframe (default 3m): ") or "3m"

WOLF_MSG = f"🐺 MONITORING {SIDE} STOPLOSS FOR {SYMBOL} ({INTERVAL}) 🐺"
print("\n" + colored(WOLF_MSG, COLOR))

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
    return pandas.DataFrame(result, columns=cols).sort_values("timestamp")

def stoploss_alert():
    df = get_klines(SYMBOL, INTERVAL)
    if len(df) < 2: return

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if SIDE == 'LONG':
        status_msg = f"[{INTERVAL}] {SYMBOL} LOW: {last['low']:.2f} (Prev Low: {prev['low']:.2f})"
        print(f"\r{status_msg}", end="", flush=True)
        if last['low'] < prev['low']:
            name = SYMBOL.replace('USDT', '')
            msg = f"🛑 {name} LONG STOPLOSS: Current Low ({last['low']:.2f}) < Previous Low ({prev['low']:.2f}) 🛑"
            print("\n")
            print(colored(msg, COLOR))
            telegram_bot_sendtext(msg)
            exit()
    else:
        status_msg = f"[{INTERVAL}] {SYMBOL} HIGH: {last['high']:.2f} (Prev High: {prev['high']:.2f})"
        print(f"\r{status_msg}", end="", flush=True)
        if last['high'] > prev['high']:
            name = SYMBOL.replace('USDT', '')
            msg = f"🛑 {name} SHORT STOPLOSS: Current High ({last['high']:.2f}) > Previous High ({prev['high']:.2f}) 🛑"
            print("\n")
            print(colored(msg, COLOR))
            telegram_bot_sendtext(msg)
            exit()

try:
    while True:
        try:
            stoploss_alert()
            time.sleep(2)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
