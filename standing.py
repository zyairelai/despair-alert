#!/usr/bin/python3

import time, socket, os, pandas, requests, argparse
from termcolor import colored

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    if not bot_token:
        print("Error: TELEGRAM_WOLVESRISE environment variable not set.")
        return None
    chat_id = "@futures_wolves_rise"
    send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=html&text={bot_message}'
    try:
        response = requests.get(send_text)
        return response.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

parser = argparse.ArgumentParser(description='Standing monitor script.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol

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
    return candlestick

def parse_interval(tf_input):
    tf = str(tf_input).strip().lower()
    if not tf: return "15m"
    if tf.endswith('h') or tf.endswith('m'): return tf
    if tf.isdigit(): return f"{tf}m"
    return "15m"

def check_standing(pair, interval, condition, period, ma_type='MA'):
    df = get_klines(pair, interval)
    ma_col = f'{period}{ma_type}'
    if ma_type.upper() == 'EMA': df[ma_col] = df['close'].ewm(span=period, adjust=False).mean()
    else: df[ma_col] = df['close'].rolling(window=period).mean()

    last_close = df['close'].iloc[-2]
    last_ma = df[ma_col].iloc[-2]

    if condition == 'above' and last_close > last_ma: return True, last_close, last_ma
    if condition == 'below' and last_close < last_ma: return True, last_close, last_ma
    return False, last_close, last_ma

print("The STANDING script is running...\n")

# Interactive Prompts
try:
    tf_input = input("Timeframe (e.g., 1m, 15m, 1h): ")
    interval = parse_interval(tf_input)

    ma_type_input = input("Indicator Type (MA or EMA, default MA): ").upper()
    ma_type = 'EMA' if ma_type_input == 'EMA' else 'MA'

    default_period = 100 if ma_type == 'EMA' else 10
    ma_period_input = input(f"Period (default {default_period}): ")
    ma_period = int(ma_period_input) if ma_period_input.isdigit() else default_period

    cond_input = input("Condition (above or below): ")
    condition = "below" if cond_input.lower().startswith('b') else "above"

except (KeyboardInterrupt, EOFError):
    print("\nAborted.")
    exit(1)

label = f"{interval} standing {condition.upper()} {ma_period}{ma_type}"
print(f"\nMonitoring {SYMBOL}: {label}...\n")

try:
    while True:
        try:
            is_met, close, ma = check_standing(SYMBOL, interval, condition, ma_period, ma_type)
            if is_met:
                msg = f"⚠️ {SYMBOL} {label}"
                telegram_bot_sendtext(msg)
                exit()
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt:
    print("\n\nAborted.")
