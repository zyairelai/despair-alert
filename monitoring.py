#!/usr/bin/python3
import pandas, requests, time, socket, os, sys, argparse
from datetime import datetime
from termcolor import colored
import shutil

parser = argparse.ArgumentParser(description='Continuous EMA Monitoring.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol

# Configuration
HTF = "15m"
LTF = "5m"
LAST_TREND = None

def telegram_bot_sendtext(bot_message):
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    if not bot_token: return
    chat_id = "@swinglivermore"
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
    if count > 0: print(f"\n[i] Cleaned up {count} __pycache__ folder(s).")

def get_klines(pair, interval):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick['10EMA'] = candlestick['close'].ewm(span=10, adjust=False).mean()
    candlestick['20EMA'] = candlestick['close'].ewm(span=20, adjust=False).mean()
    candlestick['50EMA'] = candlestick['close'].ewm(span=50, adjust=False).mean()
    return candlestick

def monitor():
    global LAST_TREND
    try:
        df_htf = get_klines(SYMBOL, HTF)
        df_ltf = get_klines(SYMBOL, LTF)
        
        last_htf = df_htf.iloc[-1]
        last_ltf = df_ltf.iloc[-1]
        
        # Trend logic: UP (10 > 20 > 50), DOWN (10 < 20)
        htf_up = last_htf['10EMA'] > last_htf['20EMA'] > last_htf['50EMA']
        ltf_up = last_ltf['10EMA'] > last_ltf['20EMA'] > last_ltf['50EMA']
        
        # Overall Trend
        if htf_up and ltf_up: current_trend = "UPTREND"
        elif not htf_up and not ltf_up: current_trend = "DOWNTREND"
        else: current_trend = "NO TRADE ZONE"
        
        htf_color = "green" if htf_up else "red"
        ltf_color = "green" if ltf_up else "red"
        trend_color = "green" if current_trend == "UPTREND" else "red" if current_trend == "DOWNTREND" else "yellow"
        
        # Output lines with independent coloring
        lines = [
            f"\r[{colored(SYMBOL, 'cyan')}]",
            colored(f"{HTF}: {'  UP' if htf_up else 'DOWN'} (10:{last_htf['10EMA']:.2f} | 20:{last_htf['20EMA']:.2f} | 50:{last_htf['50EMA']:.2f})", htf_color),
            colored(f" {LTF}: {'  UP' if ltf_up else 'DOWN'} (10:{last_ltf['10EMA']:.2f} | 20:{last_ltf['20EMA']:.2f} | 50:{last_ltf['50EMA']:.2f})", ltf_color),
            colored(f"OVERALL TREND: {current_trend}", trend_color)
        ]
        
        # Clear current lines and rewrite
        sys.stdout.write("\033[K" + "\n\033[K".join(lines) + f"\033[{len(lines)-1}A")
        sys.stdout.flush()
        
        # Telegram Alert only on Change
        if LAST_TREND is not None and current_trend != LAST_TREND:
            emoji = "🚀" if current_trend == "UPTREND" else "💥" if current_trend == "DOWNTREND" else "⏳"
            name = SYMBOL.replace('USDT', '')
            msg = f"{emoji} {name} Trend: {current_trend} {emoji}"
            telegram_bot_sendtext(msg)
            
        LAST_TREND = current_trend
        
    except Exception as e:
        # Avoid crashing the loop on network errors
        pass

def main():
    print(colored(f"\n🐺 MONITORING {SYMBOL} {HTF}/{LTF} TREND CHANGES 🐺\n", "cyan"))
    try:
        while True:
            monitor()
            time.sleep(2)
    except KeyboardInterrupt:
        # Fix: Print newlines to move past the live output before showing "Aborted"
        print("\n" * 4 + "Aborted.")
    finally:
        clear_pycache()

if __name__ == "__main__":
    main()
