#!/usr/bin/python3
# python-argcomplete-ok

import pandas, requests, time, socket, os, sys, argparse, argcomplete, shutil
from datetime import datetime, timedelta, timezone
from termcolor import colored

# Constants
MYT = timezone(timedelta(hours=8))

# Initialize session for performance
session = requests.Session()

def get_klines(pair, interval, limit=100):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": limit}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    # Extract timestamp, open, high, low, close, volume
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    df = pandas.DataFrame(result, columns=cols)
    return df

def format_price(price):
    if price is None: return "N/A"
    p = float(price)
    if p >= 10000: return f"{int(p)}"
    if p >= 1000: return f"{p:.1f}"
    if p >= 10: return f"{p:.2f}"
    # Return original string if it's a very small number or other
    return str(price).rstrip('0').rstrip('.') if '.' in str(price) else str(price)

def telegram_bot_sendtext(bot_message):
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    response = requests.get(url, params=params)
    return response.json()

def clear_pycache():
    for root, dirs, _ in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try: shutil.rmtree(pycache_path)
            except: pass

def get_session_levels(df, date, start_hour, end_hour):
    """Filters klines for a specific date and hour range (MYT)."""
    # Convert timestamp to MYT
    df['dt'] = pandas.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert(MYT)

    mask = (df['dt'].dt.date == date) & (df['dt'].dt.hour >= start_hour) & (df['dt'].dt.hour < end_hour)
    session_df = df[mask]

    if session_df.empty:
        return None, None

    return session_df['high'].max(), session_df['low'].min()

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    parser.add_argument('--alert', action='store_true', help='Enable Telegram Alert')
    parser.add_argument('--symbol', dest='symbol', default='BTCUSDT', help='Default BTCUSDT')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    SYMBOL = args.symbol.upper()
    if not (SYMBOL.endswith('USDT') or SYMBOL.endswith('USDC')):
        SYMBOL += 'USDT'

    try:
        first_run = True
        while True:
            # 1. Previous 1D Levels
            df_1d = get_klines(SYMBOL, "1d", limit=2)
            prev_1d = df_1d.iloc[-2]
            h1d, l1d = prev_1d['high'], prev_1d['low']

            # 2. Fetch Data for Time & Session Logic (Required for both Alert & Display)
            df_1m = get_klines(SYMBOL, "1m", limit=1500)
            df_1m['dt'] = pandas.to_datetime(df_1m['timestamp'], unit='ms', utc=True).dt.tz_convert(MYT)

            last_candle_ms = df_1m.iloc[-1]['timestamp']
            now_myt = datetime.fromtimestamp(last_candle_ms / 1000.0, tz=timezone.utc).astimezone(MYT)
            today = now_myt.date()

            # US DST & Reset Logic
            dst_start = datetime(today.year, 3, 14) - timedelta(days=(datetime(today.year, 3, 14).weekday() + 1) % 7)
            dst_end = datetime(today.year, 11, 7) - timedelta(days=(datetime(today.year, 11, 7).weekday() + 1) % 7)
            is_dst = dst_start.date() <= today < dst_end.date()
            hour_shift = 0 if is_dst else 1
            reset_hour = 5 + hour_shift
            if now_myt.hour < reset_hour:
                today = (now_myt - timedelta(days=1)).date()

            # Pre-calculate Asia Session levels for alert logic
            ah14, al14 = get_session_levels(df_1m, today, 8, 14)

            if first_run or not args.alert:
                # 1. Prev 1D
                title_1d = " Prev 1D "
                line_1d = f"{title_1d:=^30}"
                print(f"\n{colored(line_1d, 'white', attrs=['bold'])}")
                print(f"Prev 1D High : {colored(format_price(h1d), 'white', attrs=['bold'])}")
                print(f"Prev 1D Low  : {colored(format_price(l1d), 'white', attrs=['bold'])}")

                # 2. Asia Session
                title_asia = " Asia Session "
                line_asia = f"{title_asia:=^30}"
                print(f"\n{colored(line_asia, 'red', attrs=['bold'])}")
                
                asia_end_2_dt = datetime.combine(today, datetime.min.time()).replace(hour=14, tzinfo=MYT)
                if ah14 is not None and now_myt >= asia_end_2_dt:
                    print(f"0800-1400 High: {colored(format_price(ah14), 'red', attrs=['bold'])}")
                    print(f"0800-1400 Low : {colored(format_price(al14), 'red', attrs=['bold'])}")
                else:
                    print("0800-1400 High: N/A")
                    print("0800-1400 Low : N/A")

                # 3. NY Midnight Open
                midnight_hour = 12 + hour_shift
                midnight_dt = datetime.combine(today, datetime.min.time()).replace(hour=midnight_hour, tzinfo=MYT)
                print("") # Spacer
                if now_myt < midnight_dt:
                    print("NY Midnight Open : N/A")
                else:
                    df_after = df_1m[df_1m['dt'] >= midnight_dt]
                    if not df_after.empty:
                        midnight_open = df_after.iloc[0]['open']
                        print(f"NY Midnight Open : {colored(format_price(midnight_open), 'green', attrs=['bold'])}")
                    else:
                        print("NY Midnight Open : N/A")

                # 4. Current Price
                last_candle = df_1m.iloc[-1]
                cur_price = last_candle['close']
                cur_time = now_myt.strftime("%H:%M")
                print(f"Current @ : {format_price(cur_price)} at {cur_time}")

            if first_run and args.alert:
                symbol_short = SYMBOL.replace('USDT', '').replace('USDC', '')
                print(colored(f"\nMonitoring {symbol_short} Alert...\n"))

            triggered = False
            # Alert Logic
            if args.alert:
                # Fetch latest 5m kline for current price check as requested
                df_now = get_klines(SYMBOL, "5m", limit=1)
                now_candle = df_now.iloc[-1]
                symbol_short = SYMBOL.replace('USDT', '').replace('USDC', '')
                
                alerts = []
                # Buffer 0.25% in the inner range (High - 0.25%, Low + 0.25%)
                BUFFER = 0.0025
                if now_candle['high'] >= h1d * (1-BUFFER): alerts.append("Prev High")
                if now_candle['low'] <= l1d * (1+BUFFER): alerts.append("Prev Low")
                
                # Asia Session (0800-1400) Alert
                asia_end_2_dt = datetime.combine(today, datetime.min.time()).replace(hour=14, tzinfo=MYT)
                if now_myt >= asia_end_2_dt and ah14 is not None:
                    if now_candle['high'] >= ah14 * 0.997: alerts.append("Asia High")
                    if now_candle['low'] <= al14 * 1.003: alerts.append("Asia Low")
                
                if alerts:
                    msg = f"{symbol_short} near " + " & ".join(alerts)
                    telegram_bot_sendtext(msg)
                    
                    timestamp = datetime.now(MYT).strftime("%d-%m-%Y @ %H:%M:%S")
                    print(f"\n>>> ALERT: {msg} <<<")
                    print(f"Triggered at: {timestamp}")
                    triggered = True

            if args.alert and not triggered and not first_run:
                last_candle = df_1m.iloc[-1]
                cur_price = last_candle['close']
                cur_time = now_myt.strftime("%H:%M")
                # Move up 4 lines to update "Current @" then return
                sys.stdout.write("\033[4A")
                sys.stdout.write(f"\rCurrent @ : {format_price(cur_price)} at {cur_time}   ")
                sys.stdout.write("\033[4B")
                sys.stdout.flush()

            if not args.alert or triggered:
                if args.alert: print("") # Move to next line after alert or break
                break

            first_run = False
            time.sleep(2)

    except KeyboardInterrupt: print("\nAborted.")
    except Exception as e: print(f"Error: {e}")
    finally: clear_pycache()

if __name__ == "__main__":
    main()
