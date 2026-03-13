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
THTF = "1h"
HTF = "15m"
LTF = "5m"
VLTF = "1m"
LAST_TREND = None # Immediate trend for display
LAST_ALERT_TREND = None # Trend that was actually alerted
LAST_ALERT_CANDLE = None # Timestamp of the last candle we alerted on

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
    global LAST_TREND, LAST_ALERT_TREND, LAST_ALERT_CANDLE
    try:
        df_htf = get_klines(SYMBOL, HTF)
        df_ltf = get_klines(SYMBOL, LTF)
        df_vltf = get_klines(SYMBOL, VLTF)
        df_thtf = get_klines(SYMBOL, THTF)
        
        last_htf = df_htf.iloc[-1]
        last_ltf = df_ltf.iloc[-1]
        last_vltf = df_vltf.iloc[-1]
        last_thtf = df_thtf.iloc[-1]
        
        # Trend logic: UP (10 > 20 > 50), DOWN (10 < 20)
        htf_up = last_htf['10EMA'] > last_htf['20EMA'] > last_htf['50EMA']
        ltf_up = last_ltf['10EMA'] > last_ltf['20EMA'] > last_ltf['50EMA']
        thtf_up = last_thtf['10EMA'] > last_thtf['20EMA'] > last_thtf['50EMA']
        vltf_up = last_vltf['10EMA'] > last_vltf['20EMA']
        vltf_down = last_vltf['10EMA'] < last_vltf['20EMA']
        
        # Overall Trend (15m + 5m)
        if htf_up and ltf_up: current_trend = "UPTREND"
        elif not htf_up and not ltf_up: current_trend = "DOWNTREND"
        else: current_trend = "NO TRADE ZONE"
        
        htf_color = "green" if htf_up else "red"
        ltf_color = "green" if ltf_up else "red"
        thtf_color = "green" if thtf_up else "red"
        trend_color = "green" if current_trend == "UPTREND" else "red" if current_trend == "DOWNTREND" else "yellow"
        
        # Status labels: only use double space when alignment is needed (any one is DOWN)
        all_up = thtf_up and htf_up and ltf_up
        thtf_label = 'UP' if all_up else ('  UP' if thtf_up else 'DOWN')
        htf_label = 'UP' if all_up else ('  UP' if htf_up else 'DOWN')
        ltf_label = 'UP' if all_up else ('  UP' if ltf_up else 'DOWN')
        
        # Output lines with independent coloring
        # Note: Separating the empty line ensures \033[K clears the entire row
        lines = [
            f"\r[{colored(SYMBOL, 'cyan')}]",
            colored(f" {THTF}: {thtf_label} (EMA10:{last_thtf['10EMA']:.2f} | EMA20:{last_thtf['20EMA']:.2f} | EMA50:{last_thtf['50EMA']:.2f})", thtf_color),
            colored(f"{HTF}: {htf_label} (EMA10:{last_htf['10EMA']:.2f} | EMA20:{last_htf['20EMA']:.2f} | EMA50:{last_htf['50EMA']:.2f})", htf_color),
            colored(f" {LTF}: {ltf_label} (EMA10:{last_ltf['10EMA']:.2f} | EMA20:{last_ltf['20EMA']:.2f} | EMA50:{last_ltf['50EMA']:.2f})", ltf_color),
            "", # Spacer line
            colored(f" [+] OVERALL TREND: {current_trend}", trend_color)
        ]
        
        # Clear current lines and rewrite
        output_str = "\033[K" + "\n\033[K".join(lines)
        num_newlines = output_str.count('\n')
        sys.stdout.write(output_str + f"\033[{num_newlines}A")
        sys.stdout.flush()
        
        # Alert Logic: Trigger once per 5m candle on trend alignment
        current_candle_ts = last_ltf['timestamp']
        is_new_candle = LAST_ALERT_CANDLE is None or current_candle_ts > LAST_ALERT_CANDLE
        
        if is_new_candle and current_trend != LAST_ALERT_TREND:
            first_run = LAST_ALERT_TREND is None
            trigger_msg = None
            emoji = ""
            
            if current_trend == "NO TRADE ZONE":
                emoji = "⏳"
                trigger_msg = f"{emoji} {SYMBOL.replace('USDT', '')} Trend: {current_trend} {emoji}"
            elif current_trend == "UPTREND" and vltf_up:
                emoji = "🚀"
                trigger_msg = f"{emoji} {SYMBOL.replace('USDT', '')} Trend: {current_trend} {emoji}"
            elif current_trend == "DOWNTREND" and vltf_down:
                emoji = "💥"
                trigger_msg = f"{emoji} {SYMBOL.replace('USDT', '')} Trend: {current_trend} {emoji}"
            
            if trigger_msg and not first_run:
                telegram_bot_sendtext(trigger_msg)
            
            # Always record to prevent first-run alert
            LAST_ALERT_TREND = current_trend
            LAST_ALERT_CANDLE = current_candle_ts
            
        LAST_TREND = current_trend
        
    except Exception as e: pass

def main():
    print(colored(f"\n🐺 MONITORING {SYMBOL} {HTF}/{LTF} TREND CHANGES 🐺\n", "cyan"))
    try:
        while True:
            monitor()
            time.sleep(2)
    except KeyboardInterrupt: print("\n" * 7 + "Aborted.")
    finally: clear_pycache()

if __name__ == "__main__":
    main()
