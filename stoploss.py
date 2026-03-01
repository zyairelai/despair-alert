#!/usr/bin/python3
# python-argcomplete-ok

import time, socket, os, pandas, requests, argparse, argcomplete
from termcolor import colored

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    chat_id = "@futures_wolves_rise"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

# telegram_bot_sendtext("Telegram works!")
print("The STOPLOSS script is running...\n")

session = requests.Session()
def get_klines(pair, interval):
    spot_url = "https://api.binance.com/api/v1/klines"
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick["body"] = (candlestick["close"] - candlestick["open"]).abs()
    candlestick["upper_wick"] = candlestick["high"] - candlestick[["open", "close"]].max(axis=1)
    candlestick["lower_wick"] = candlestick[["open", "close"]].min(axis=1) - candlestick["low"]
    return candlestick

def stoploss_alert(pair, side):
    timeframe = get_klines(pair, '15m')
    timeframe['10MA'] = timeframe['close'].rolling(window=10).mean()
    
    if side == 'SHORT':
        if timeframe['close'].iloc[-2] > timeframe['10MA'].iloc[-2]:
            telegram_bot_sendtext("🛑 SHORT STOPLOSS: 15m standing ABOVE 10MA")
            exit()
    elif side == 'LONG':
        if timeframe['close'].iloc[-2] < timeframe['10MA'].iloc[-2]:
            telegram_bot_sendtext("🛑 LONG STOPLOSS: 15m standing BELOW 10MA")
            exit()

parser = argparse.ArgumentParser(description='Stoploss monitor script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--close-short', action='store_true', help='Monitor SHORT stoploss (default)')
parser.add_argument('--close-long', action='store_true', help='Monitor LONG stoploss')

argcomplete.autocomplete(parser)
args, unknown = parser.parse_known_args()

if args.close_long: side = 'LONG'
else: side = 'SHORT'

color = "red" if side == "SHORT" else "green"
print(f"Monitoring {colored(side, color)} stoploss...\n")

try:
    while True:
        try:
            stoploss_alert("BTCUSDT", side)
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
