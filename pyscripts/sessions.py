#!/usr/bin/python3
# python-argcomplete-ok

import pandas, requests, time, socket, os, sys, argparse, argcomplete, shutil
from datetime import datetime, timedelta, timezone
from termcolor import colored

# Constants
MYT = timezone(timedelta(hours=8))
NEAR_THRESHOLD = 0.002

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

def is_near(val, benchmarks, threshold=NEAR_THRESHOLD):
    """Returns True if val is within the threshold percentage of any benchmark."""
    if val is None or not benchmarks:
        return False
    for b in benchmarks:
        if b is not None and abs(val - b) / b <= threshold:
            return True
    return False

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    response = requests.get(url, params=params)
    return response.json()

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
    parser.add_argument('--symbol', dest='symbol', default='BTCUSDT', metavar='BTCUSDT', help='Trading pair (default: BTCUSDT)')
    parser.add_argument('--alert', action='store_true', help='Read alert if price hits Prev 1D High/Low')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    SYMBOL = args.symbol.upper()
    if not SYMBOL.endswith('USDT'):
        SYMBOL += 'USDT'

    try:
        first_run = True
        while True:
            # 1. Previous 1D Levels
            df_1d = get_klines(SYMBOL, "1d", limit=2)
            # index -2 is the previous completed day
            prev_1d = df_1d.iloc[-2]
            h1d, l1d = prev_1d['high'], prev_1d['low']
            m1d = (h1d + l1d) / 2

            triggered = False
            # Alert Logic
            if args.alert:
                # Fetch latest 1m kline for current price
                df_now = get_klines(SYMBOL, "1m", limit=1)
                curr_price = df_now.iloc[-1]['close']

                symbol_short = SYMBOL.replace('USDT', '')
                if curr_price >= h1d:
                    msg = f"{symbol_short} touch Prev High"
                    telegram_bot_sendtext(msg)
                    print(f"\n>>> ALERT: {msg} <<<")
                    triggered = True
                elif curr_price <= l1d:
                    msg = f"{symbol_short} touch Prev Low"
                    telegram_bot_sendtext(msg)
                    print(f"\n>>> ALERT: {msg} <<<")
                    triggered = True

            if first_run or not args.alert:
                title_text = f" Prev 1D "
                line = f"{title_text:=^30}"
                print(f"\n{colored(line, 'white', attrs=['bold'])}")
                print(f"Prev 1D High: {colored(format_price(h1d), 'white', attrs=['bold'])}")
                print(f"Prev 1D Mid : {colored(format_price(m1d), 'white', attrs=['bold'])}")
                print(f"Prev 1D Low : {colored(format_price(l1d), 'white', attrs=['bold'])}")

                # 2. Session Data (1m klines)
                # Fetch 1500 minutes to cover the full current day in MYT
                df_1m = get_klines(SYMBOL, "1m", limit=1500)

                now_myt = datetime.now(MYT)
                today = now_myt.date()

                # Benchmarks for duplication check (Highs and Lows kept separate)
                bench_h = [h1d]
                bench_l = [l1d]

                # Asia Session
                ah12, al12 = get_session_levels(df_1m, today, 8, 12)
                ah15, al15 = get_session_levels(df_1m, today, 8, 15)

                title_text = " Asia Session "
                line = f"{title_text:=^30}"
                print(f"\n{colored(line, 'red', attrs=['bold'])}")
                
                # 0800-1200
                if ah12 is not None:
                    h_near = is_near(ah12, bench_h)
                    l_near = is_near(al12, bench_l)
                    
                    h_display = colored("-", "white") if h_near else colored(format_price(ah12), 'red', attrs=['bold'])
                    l_display = colored("-", "white") if l_near else colored(format_price(al12), 'red', attrs=['bold'])
                    
                    print(f"0800-1200 High: {h_display}")
                    print(f"0800-1200 Low : {l_display}")
                    
                    if not h_near: bench_h.append(ah12)
                    if not l_near: bench_l.append(al12)
                else:
                    print("0800-1200 High: N/A")
                    print("0800-1200 Low : N/A")

                # 0800-1500
                if ah15 is not None:
                    h_near = is_near(ah15, bench_h)
                    l_near = is_near(al15, bench_l)
                    
                    h_display = colored("-", "white") if h_near else colored(format_price(ah15), 'red', attrs=['bold'])
                    l_display = colored("-", "white") if l_near else colored(format_price(al15), 'red', attrs=['bold'])
                    
                    print(f"0800-1500 High: {h_display}")
                    print(f"0800-1500 Low : {l_display}")
                    
                    if not h_near: bench_h.append(ah15)
                    if not l_near: bench_l.append(al15)
                else:
                    print("0800-1500 High: N/A")
                    print("0800-1500 Low : N/A")



                # 2.5 Opening Session (US Open)
                # US DST: 2nd Sun March to 1st Sun Nov
                dst_start = datetime(today.year, 3, 14) - timedelta(days=(datetime(today.year, 3, 14).weekday() + 1) % 7)
                dst_end = datetime(today.year, 11, 7) - timedelta(days=(datetime(today.year, 11, 7).weekday() + 1) % 7)
                is_dst = dst_start.date() <= today < dst_end.date()
                open_hour = 21 if is_dst else 22
                
                start_time = datetime.combine(today, datetime.min.time()).replace(hour=open_hour, minute=30, tzinfo=MYT)
                end_30m = start_time + timedelta(minutes=30)
                mask_30m = (df_1m['dt'] >= start_time) & (df_1m['dt'] < end_30m)
                
                time_range = f"{open_hour}30-{open_hour+1}00"
                title_text = " New York Session "
                line = f"{title_text:=^30}"
                print(f"\n{colored(line, 'green', attrs=['bold'])}")
                df_30m = df_1m[mask_30m]
                if not df_30m.empty:
                    if now_myt < end_30m:
                        print(f"{time_range} High: N/A")
                        print(f"{time_range} Low : N/A")
                    else:
                        h30, l30 = df_30m['high'].max(), df_30m['low'].min()
                        h_near = is_near(h30, bench_h)
                        l_near = is_near(l30, bench_l)
                        
                        h_display = colored("-", "white") if h_near else colored(format_price(h30), 'green', attrs=['bold'])
                        l_display = colored("-", "white") if l_near else colored(format_price(l30), 'green', attrs=['bold'])
                        
                        print(f"{time_range} High: {h_display}")
                        print(f"{time_range} Low : {l_display}")
                else:
                    print(f"{time_range} High: N/A")
                    print(f"{time_range} Low : N/A")

                # 3. Monday High/Low
                # Fetch last 10 days to ensure we get the last Monday
                df_monday = get_klines(SYMBOL, "1d", limit=10)
                df_monday['dt'] = pandas.to_datetime(df_monday['timestamp'], unit='ms', utc=True).dt.tz_convert(MYT)
                monday_candles = df_monday[df_monday['dt'].dt.weekday == 0]

                title_text = " Monday "
                line = f"{title_text:=^30}"
                print(f"\n{colored(line, 'blue', attrs=['bold'])}")
                if not monday_candles.empty:
                    last_monday = monday_candles.iloc[-1]
                    mh, ml = last_monday['high'], last_monday['low']
                    print(f"Monday High: {colored(format_price(mh), 'blue', attrs=['bold'])}")
                    print(f"Monday Low : {colored(format_price(ml), 'blue', attrs=['bold'])}")
                else:
                    print("Monday High: N/A")
                    print("Monday Low : N/A")

                # 4. Weekly High/Low
                df_1w = get_klines(SYMBOL, "1w", limit=2)
                title_text = " Weekly "
                line = f"{title_text:=^30}"
                print(f"\n{colored(line, 'magenta', attrs=['bold'])}")
                if len(df_1w) >= 2:
                    prev_week = df_1w.iloc[-2]
                    wh, wl = prev_week['high'], prev_week['low']
                    print(f"Prev Week High: {colored(format_price(wh), 'magenta', attrs=['bold'])}")
                    print(f"Prev Week Low : {colored(format_price(wl), 'magenta', attrs=['bold'])}")
                else:
                    print("Prev Week High: N/A")
                    print("Prev Week Low : N/A")

            if not args.alert or triggered:
                break

            if first_run:
                print(colored(f"\nMonitoring {SYMBOL} Alert..."))

            first_run = False
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nAborted.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        clear_pycache()

if __name__ == "__main__":
    main()
