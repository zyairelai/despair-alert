#!/usr/bin/python3
import pandas, requests, time, socket, os, sys, argparse
from datetime import datetime
from termcolor import colored
import shutil

parser = argparse.ArgumentParser(description='Continuous EMA Monitoring.', add_help=False)
parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
args, unknown = parser.parse_known_args()
SYMBOL = args.symbol.upper()
if not (SYMBOL.endswith('USDT') or SYMBOL.endswith('USDC')):
    SYMBOL += 'USDT'

# Configuration
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
    candlestick['50EMA'] = candlestick['close'].ewm(span=50, adjust=False).mean()
    return candlestick

def get_trend_at(df, idx):
    if idx < 0 or idx >= len(df): return "NEUTRAL"
    row = df.iloc[idx]
    ema10 = row['10EMA']
    ema20 = row['20EMA']
    ema50 = row['50EMA']

    if ema10 < ema20: return "DOWNTREND"
    if ema10 > ema20 and ema20 > ema50: return "UPTREND"
    return "NEUTRAL"

def monitor():
    global LAST_TREND, LAST_ALERT_TREND, LAST_ALERT_CANDLE, LAST_EMERGENCY_HOUR
    try:
        df_1h = get_klines(SYMBOL, "1h")
        df_ltf = get_klines(SYMBOL, LTF)

        last_1h = df_1h.iloc[-1]
        prev_1h = df_1h.iloc[-2]

        # Trend Determination Logic
        current_trend = "NO TRADE ZONE"

        # Indices for closed candles
        last_closed_idx = len(df_ltf) - 2
        last_closed_row = df_ltf.iloc[last_closed_idx]

        # 1. Downtrend check (Immediate on closed candle)
        if last_closed_row['10EMA'] < last_closed_row['20EMA']:
            current_trend = "DOWNTREND"
        # 2. Uptrend check (Requires 4 consecutive closed candles)
        else:
            is_uptrend_confirmed = True
            for i in range(4):
                if get_trend_at(df_ltf, last_closed_idx - i) != "UPTREND":
                    is_uptrend_confirmed = False
                    break
            if is_uptrend_confirmed:
                current_trend = "UPTREND"

        # Emergency 1h Logic: Current high > previous high AND current 1h candle is RED
        is_emergency = last_1h['high'] > prev_1h['high'] and last_1h['close'] < last_1h['open']

        trend_color = "green" if current_trend == "UPTREND" else "red" if current_trend == "DOWNTREND" else "yellow"
        display_trend = "EMERGENCY DOWNTREND" if is_emergency else current_trend
        # Output lines
        lines = [
            f"\r[{colored(SYMBOL, 'cyan')}]",
            colored(f" [+] OVERALL TREND: {display_trend}", trend_color)
        ]

        # Clear current lines and rewrite
        output_str = "\033[K" + "\n\033[K".join(lines)
        num_newlines = output_str.count('\n')
        sys.stdout.write(output_str + f"\033[{num_newlines}A")
        sys.stdout.flush()

        # Alert Logic: Trigger once per 5m candle change after candle close
        current_candle_ts = df_ltf.iloc[-1]['timestamp']
        current_hour_ts = last_1h['timestamp']

        is_new_candle = LAST_ALERT_CANDLE is None or current_candle_ts > LAST_ALERT_CANDLE
        is_new_emergency_hour = LAST_EMERGENCY_HOUR is None or current_hour_ts > LAST_EMERGENCY_HOUR

        # Cooldown: Mute until the NEXT hour + 30 seconds after an emergency alert
        is_after_cooldown = True
        if LAST_EMERGENCY_HOUR is not None:
            cooldown_end_ms = LAST_EMERGENCY_HOUR + (3600 * 1000) + 30000
            if (time.time() * 1000) < cooldown_end_ms:
                is_after_cooldown = False

        # Global Lock: If we are within the cooldown period of an emergency alert, all alerts are muted
        if not is_after_cooldown:
            LAST_TREND = current_trend
            return

        # 1. Emergency Case: Alert once per hour
        if is_emergency and is_new_emergency_hour:
            trigger_msg = f"🚨 {SYMBOL.replace('USDT', '')} 1H EMERGENCY DOWNTREND 🚨"
            telegram_bot_sendtext(trigger_msg)
            LAST_EMERGENCY_HOUR = current_hour_ts

        # 2. Standard Case: Alert based on refined status
        trigger_msg = None
        if current_trend == "UPTREND" and LAST_ALERT_TREND != "UPTREND":
            trigger_msg = f"🚀 {SYMBOL.replace('USDT', '')} trend: UPTREND 🚀"
            LAST_ALERT_TREND = "UPTREND"
        elif current_trend == "DOWNTREND" and LAST_ALERT_TREND != "DOWNTREND":
            trigger_msg = f"💥 {SYMBOL.replace('USDT', '')} trend: DOWNTREND 💥"
            LAST_ALERT_TREND = "DOWNTREND"
        elif current_trend == "NO TRADE ZONE" and LAST_ALERT_TREND != "NO TRADE ZONE":
            LAST_ALERT_TREND = "NO TRADE ZONE"

        if trigger_msg:
            telegram_bot_sendtext(trigger_msg)

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
