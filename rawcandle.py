#!/usr/bin/python3
import pandas, requests, time, socket, os, sys, argparse
from termcolor import colored
import shutil

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
    prev_5 = df.iloc[-6:-1]
    prev_2 = df.iloc[-3:-1]
    
    # 1. Structure Break (Lower Low + Momentum)
    low_condition = current['close'] < prev_5['low'].min()
    momentum_condition = current['body'] > prev_5['body'].sum()
    if low_condition and momentum_condition: return "MOMENTUM BREAKDOWN", "📉"

    # 2. Shooting Star
    is_shooting_star = (
        current['close'] < current['open'] and
        current['high'] >= prev_5['high'].max() and
        (current['upper_wick'] > (current['body'] * 2 + current['lower_wick']) or 
         current['upper_wick'] > (current['body'] + current['lower_wick']) * 2)
    )
    if is_shooting_star: return "SHOOTING STAR", "🎯"

    # 3. Bearish Engulfing
    is_bearish_engulfing = (
        current['close'] < prev_2['low'].min() and
        current['body'] > prev_2['body'].max()
    )
    if is_bearish_engulfing: return "BEARISH ENGULFING", "🐻"

    # 4. Bullish Engulfing
    is_bullish_engulfing = (
        current['close'] > prev_2['high'].max() and
        current['body'] > prev_2['body'].max()
    )
    if is_bullish_engulfing: return "BULLISH ENGULFING", "🐮"

    # 5. Hanging Man
    is_hanging_man = (
        current['close'] > current['open'] and
        current['close'] <= prev_5['low'].min() and
        current['lower_wick'] > (current['body'] * 2 + current['upper_wick'])
    )
    if is_hanging_man: return "HANGING MAN", "🪂"

    return None, None

def monitor():
    global LAST_ALERT_CANDLE, LAST_ALERT_PATTERN
    try:
        df = get_klines(SYMBOL, INTERVAL)
        last_candle = df.iloc[-1]
        pattern, emoji = detect_pattern(df)
        
        # UI Rendering
        status_line = f"[{colored(SYMBOL, 'cyan')}] {INTERVAL} Candle: O:{last_candle['open']:.2f} H:{last_candle['high']:.2f} L:{last_candle['low']:.2f} C:{last_candle['close']:.2f}"
        pattern_line = f" [+] Current Pattern: {colored(pattern if pattern else 'None', 'yellow')}"
        
        lines = [status_line, pattern_line]
        output_str = "\033[K" + "\n\033[K".join(lines)
        num_newlines = output_str.count('\n')
        sys.stdout.write(output_str + f"\033[{num_newlines}A")
        sys.stdout.flush()

        # Alert Logic
        current_candle_ts = last_candle['timestamp']
        if pattern and (current_candle_ts != LAST_ALERT_CANDLE or pattern != LAST_ALERT_PATTERN):
            msg = f"{emoji} {SYMBOL} {INTERVAL} {pattern} {emoji}"
            telegram_bot_sendtext(msg)
            LAST_ALERT_CANDLE = current_candle_ts
            LAST_ALERT_PATTERN = pattern
            
    except Exception as e:
        # print(f"Error: {e}") # Debug
        pass

def main():
    print(colored(f"\n🐺 MONITORING {SYMBOL} {INTERVAL} CANDLE PATTERNS 🐺\n", "cyan"))
    try:
        while True:
            monitor()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n" * 3 + "Aborted.")
    finally:
        clear_pycache()

if __name__ == "__main__":
    main()
