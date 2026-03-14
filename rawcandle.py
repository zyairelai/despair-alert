#!/usr/bin/python3
import pandas, requests, time, socket, os, sys, argparse, shutil
from termcolor import colored

# Argument Parsing
parser = argparse.ArgumentParser(description='Continuous Candle Pattern Monitoring.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol

# Configuration
INTERVAL = "5m"
LAST_ALERT_CANDLE = None # Timestamp of the last candle we alerted on
LAST_ALERT_PATTERN = None

def telegram_bot_sendtext(bot_message):
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    if not bot_token: return
    chat_id = "@futures_wolves_rise"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    try: requests.get(url, params=params, timeout=5)
    except: pass

def clear_pycache():
    count = 0
    for root, dirs, _ in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(pycache_path)
                count += 1
            except: pass

def get_klines(pair, interval):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    df = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    
    # Calculate Candle Components
    df["body"] = (df["close"] - df["open"]).abs()
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    return df

def detect_pattern(df):
    current = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Simple Short Condition:
    is_short = (
        current['upper_wick'] > prev['body'] and
        current['upper_wick'] > prev['upper_wick'] and
        current['upper_wick'] > prev['lower_wick']
    )
    
    if is_short: return "LONG WICK DETECTED", "💥"
    return None, None

def monitor():
    global LAST_ALERT_CANDLE, LAST_ALERT_PATTERN
    try:
        df = get_klines(SYMBOL, INTERVAL)
        last_candle = df.iloc[-1]
        pattern, emoji = detect_pattern(df)
        
        # UI Rendering
        candle_status = colored("GREEN", "green") if last_candle['close'] > last_candle['open'] else colored("RED", "red")
        
        lines = [
            f"[{colored(SYMBOL, 'cyan')}]",
            f"{INTERVAL} Candle: {candle_status}"
        ]
        
        if pattern: lines.append(f"{emoji} {pattern} {emoji}")
        
        # Clear current lines and rewrite
        output_str = "\033[K" + "\n\033[K".join(lines)
        num_newlines = output_str.count('\n')
        sys.stdout.write(output_str + f"\033[{num_newlines}A\r")
        sys.stdout.flush()

        # Alert Logic
        current_candle_ts = last_candle['timestamp']
        if pattern and (current_candle_ts != LAST_ALERT_CANDLE or pattern != LAST_ALERT_PATTERN):
            msg = f"{emoji} {SYMBOL.replace('USDT', '')} {pattern} {emoji}"
            telegram_bot_sendtext(msg)
            LAST_ALERT_CANDLE = current_candle_ts
            LAST_ALERT_PATTERN = pattern
            
    except Exception as e: pass

def main():
    print(colored(f"\n🐺 MONITORING {SYMBOL} {INTERVAL} CANDLE PATTERNS 🐺\n", "cyan"))
    try:
        while True:
            monitor()
            time.sleep(2)
    except KeyboardInterrupt: print("\n" * 3 + "Aborted.")
    finally: clear_pycache()

if __name__ == "__main__":
    main()
