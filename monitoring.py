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
        
        last_htf = df_htf.iloc[-1]
        last_ltf = df_ltf.iloc[-1]
        
        # Trend logic:
        # 15m (HTF): Simple check on previous close (-2 candle)
        # 5m (LTF): Remain 10/20 crossing for down, 10/20/50 for up
        
        prev_htf = df_htf.iloc[-2]
        htf_up = prev_htf['close'] > prev_htf['20EMA'] and prev_htf['close'] > prev_htf['50EMA']
        htf_down = prev_htf['close'] < prev_htf['20EMA']
        
        ltf_up = last_ltf['10EMA'] > last_ltf['20EMA'] > last_ltf['50EMA']
        ltf_down = last_ltf['10EMA'] < last_ltf['20EMA']
        
        if htf_up and ltf_up: current_trend = "UPTREND"
        elif htf_down and ltf_down: current_trend = "DOWNTREND"
        else: current_trend = "NO TRADE ZONE"
        
        htf_color = "green" if htf_up else "red" if htf_down else "yellow"
        ltf_color = "green" if ltf_up else "red" if ltf_down else "yellow"
        trend_color = "green" if current_trend == "UPTREND" else "red" if current_trend == "DOWNTREND" else "yellow"
        
        # Formatting: if one up one down (or neutral), give 2 space for that up
        all_up = htf_up and ltf_up
        htf_label = 'UP' if all_up else ('  UP' if htf_up else ('DOWN' if htf_down else 'NEUTRAL'))
        ltf_label = 'UP' if all_up else ('  UP' if ltf_up else ('DOWN' if ltf_down else 'NEUTRAL'))
        
        # Output lines with independent coloring
        lines = [
            f"\r[{colored(SYMBOL, 'cyan')}]",
            colored(f"{HTF}: {htf_label}", htf_color),
            colored(f" {LTF}: {ltf_label}", ltf_color),
            "", # Spacer line
            colored(f" [+] OVERALL TREND: {current_trend}", trend_color)
        ]
        
        # Clear current lines and rewrite
        output_str = "\033[K" + "\n\033[K".join(lines)
        num_newlines = output_str.count('\n')
        sys.stdout.write(output_str + f"\033[{num_newlines}A")
        sys.stdout.flush()
        
        # Alert Logic: Trigger once per 15m candle on trend alignment
        current_candle_ts = last_htf['timestamp']
        is_new_candle = LAST_ALERT_CANDLE is None or current_candle_ts > LAST_ALERT_CANDLE
        
        if is_new_candle and current_trend != LAST_ALERT_TREND:
            first_run = LAST_ALERT_TREND is None
            trigger_msg = None
            emoji = ""
            
            if current_trend == "UPTREND":
                emoji = "🚀"
                trigger_msg = f"{emoji} {SYMBOL.replace('USDT', '')} Trend: {current_trend} {emoji}"
            elif current_trend == "DOWNTREND":
                emoji = "💥"
                trigger_msg = f"{emoji} {SYMBOL.replace('USDT', '')} Trend: {current_trend} {emoji}"
            elif current_trend == "NO TRADE ZONE":
                emoji = "⏳"
                trigger_msg = f"{emoji} {SYMBOL.replace('USDT', '')} Trend: {current_trend} {emoji}"
            
            if trigger_msg and not first_run:
                telegram_bot_sendtext(trigger_msg)
            
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
