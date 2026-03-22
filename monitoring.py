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
SYMBOL = args.symbol
LTF = "5m"
LAST_TREND = None # Immediate trend for display
LAST_ALERT_TREND = None # Trend that was actually alerted
LAST_ALERT_CANDLE = None # Timestamp of the last candle we alerted on
LAST_EMERGENCY_HOUR = None # Timestamp of the last emergency alert (hourly lock)

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
    params = {"symbol": pair, "interval": interval, "limit": 200}
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick['10EMA'] = candlestick['close'].ewm(span=10, adjust=False).mean()
    candlestick['20EMA'] = candlestick['close'].ewm(span=20, adjust=False).mean()
    return candlestick

def monitor():
    global LAST_TREND, LAST_ALERT_TREND, LAST_ALERT_CANDLE, LAST_EMERGENCY_HOUR
    try:
        df_1h = get_klines(SYMBOL, "1h")
        df_ltf = get_klines(SYMBOL, LTF)
        
        last_1h = df_1h.iloc[-1]
        prev_1h = df_1h.iloc[-2]
        
        # 5m candles: last_closed is iloc[-2], current is iloc[-1]
        last_closed = df_ltf.iloc[-2]
        current_ltf = df_ltf.iloc[-1]
        
        # Emergency 1h Logic: Current high > previous high AND current 1h candle is RED
        is_emergency = last_1h['high'] > prev_1h['high'] and last_1h['close'] < last_1h['open']

        # Trend logic (Alerting on closed candle):
        # 5m (LTF): 10/20 EMA cross
        ltf_up = last_closed['10EMA'] > last_closed['20EMA']
        ltf_down = last_closed['10EMA'] < last_closed['20EMA']
        
        if is_emergency: current_trend = "DOWNTREND"
        elif ltf_up: current_trend = "UPTREND"
        elif ltf_down: current_trend = "DOWNTREND"
        else: current_trend = "NO TRADE ZONE"
        
        ltf_color = "green" if ltf_up else "red" if ltf_down else "yellow"
        trend_color = "green" if current_trend == "UPTREND" else "red" if current_trend == "DOWNTREND" else "yellow"
        
        ltf_label = 'UP' if ltf_up else ('DOWN' if ltf_down else 'NO TRADE ZONE')
        
        # Output lines with independent coloring
        display_trend = "EMERGENCY DOWNTREND" if is_emergency else current_trend
        lines = [
            f"\r[{colored(SYMBOL, 'cyan')}]",
            colored(f" {LTF}: {ltf_label}", ltf_color),
            "", # Spacer line
            colored(f" [+] OVERALL TREND: {display_trend}", trend_color)
        ]
        
        # Clear current lines and rewrite
        output_str = "\033[K" + "\n\033[K".join(lines)
        num_newlines = output_str.count('\n')
        sys.stdout.write(output_str + f"\033[{num_newlines}A")
        sys.stdout.flush()
        
        # Alert Logic: Trigger once per 5m candle change after candle close
        current_candle_ts = current_ltf['timestamp']
        current_hour_ts = last_1h['timestamp']
        
        is_new_candle = LAST_ALERT_CANDLE is None or current_candle_ts > LAST_ALERT_CANDLE
        is_new_emergency_hour = LAST_EMERGENCY_HOUR is None or current_hour_ts > LAST_EMERGENCY_HOUR

        # Cooldown: Delay the reset by 30 seconds at the start of the hour
        seconds_past_hour = time.time() % 3600
        if is_new_emergency_hour and seconds_past_hour < 30:
            is_new_emergency_hour = False

        # Global Lock: If an emergency alert was sent this hour, all Telegram alerts are muted
        if not is_new_emergency_hour:
            LAST_TREND = current_trend
            return

        # 1. Emergency Case: Bypass candle rule
        if is_emergency:
            trigger_msg = f"🚨 {SYMBOL.replace('USDT', '')} 1H EMERGENCY DOWNTREND 🚨"
            telegram_bot_sendtext(trigger_msg)
            LAST_ALERT_TREND = "DOWNTREND"
            LAST_ALERT_CANDLE = current_candle_ts
            LAST_EMERGENCY_HOUR = current_hour_ts
            LAST_TREND = current_trend
            return

        # 2. Standard Case: Once per 5m candle start, check if trend of CLOSED candle changed
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
            
            if trigger_msg and not first_run:
                telegram_bot_sendtext(trigger_msg)
            
            LAST_ALERT_TREND = current_trend
            LAST_ALERT_CANDLE = current_candle_ts
            
        LAST_TREND = current_trend
    except Exception as e: pass

def main():
    print(colored(f"\n🐺 MONITORING {SYMBOL} {LTF} TREND CHANGES 🐺\n", "cyan"))
    try:
        while True:
            monitor()
            time.sleep(2)
    except KeyboardInterrupt: print("\n" * 7 + "Aborted.")
    finally: clear_pycache()

if __name__ == "__main__":
    main()
