#!/usr/bin/python3

import pandas, requests, os, sys, shutil
from datetime import datetime, timedelta, timezone
from termcolor import colored

# Constants
TZ = timezone(timedelta(hours=8)) # Change to 4 for Dubai Timezone
PREV_DAY, ASIA_SESSION, LONDON_SESSION = True, True, True

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

def clear_pycache():
    for root, dirs, _ in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try: shutil.rmtree(pycache_path)
            except: pass

def get_session_levels(df, date, start_hour, end_hour):
    """Filters klines for a specific date and hour range (MYT)."""
    # Convert timestamp to Local Time
    df['dt'] = pandas.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert(TZ)

    mask = (df['dt'].dt.date == date) & (df['dt'].dt.hour >= start_hour) & (df['dt'].dt.hour < end_hour)
    session_df = df[mask]

    if session_df.empty:
        return None, None

    return session_df['high'].max(), session_df['low'].min()

def main():
    global PREV_DAY, ASIA_SESSION, LONDON_SESSION
    SYMBOL = 'BTCUSDT'

    try:
        # 1. Previous 1D Levels
        df_1d = get_klines(SYMBOL, "1d", limit=2)
        prev_1d = df_1d.iloc[-2]
        h1d, l1d = prev_1d['high'], prev_1d['low']

        # 2. Fetch Data for Time & Session Logic
        df_1m = get_klines(SYMBOL, "1m", limit=1500)
        df_1m['dt'] = pandas.to_datetime(df_1m['timestamp'], unit='ms', utc=True).dt.tz_convert(TZ)

        last_candle_ms = df_1m.iloc[-1]['timestamp']
        now_local = datetime.fromtimestamp(last_candle_ms / 1000.0, tz=timezone.utc).astimezone(TZ)
        today = now_local.date()

        # DST & Reset Logic
        # US DST: 2nd Sunday March to 1st Sunday November
        us_dst_start = datetime(today.year, 3, 14) - timedelta(days=(datetime(today.year, 3, 14).weekday() + 1) % 7)
        us_dst_end = datetime(today.year, 11, 7) - timedelta(days=(datetime(today.year, 11, 7).weekday() + 1) % 7)
        is_us_dst = us_dst_start.date() <= today < us_dst_end.date()
        us_shift = 0 if is_us_dst else 1

        # UK DST: Last Sunday March to Last Sunday October
        uk_dst_start = datetime(today.year, 3, 31) - timedelta(days=(datetime(today.year, 3, 31).weekday() + 1) % 7)
        uk_dst_end = datetime(today.year, 10, 31) - timedelta(days=(datetime(today.year, 10, 31).weekday() + 1) % 7)
        is_uk_dst = uk_dst_start.date() <= today < uk_dst_end.date()
        uk_shift = 0 if is_uk_dst else 1

        # Use US shift for the day reset (following NY Daily Close)
        reset_hour = 5 + us_shift
        if now_local.hour < reset_hour:
            today = (now_local - timedelta(days=1)).date()

        # Pre-calculate Asia Session levels
        ah14, al14 = get_session_levels(df_1m, today, 8, 14)

        if PREV_DAY:
            title_text = f" Prev 1D "
            line = f"{title_text:=^30}"
            print(f"\n{colored(line, 'white', attrs=['bold'])}")
            print(f"Prev 1D High : {colored(format_price(h1d), 'white', attrs=['bold'])}")
            print(f"Prev 1D Low  : {colored(format_price(l1d), 'white', attrs=['bold'])}")

        if ASIA_SESSION:
            # Asia Session
            ah_start = 8
            asia_end = 14
            asia_end_dt = datetime.combine(today, datetime.min.time()).replace(hour=asia_end, tzinfo=TZ)
            # ah14, al14 already calculated above

            title_text = " Asia Session "
            line = f"{title_text:=^30}"
            print(f"\n{colored(line, 'red', attrs=['bold'])}")

            # Asia Session (0800-1400)
            time_range = f"{ah_start:02d}00-{asia_end:02d}00"
            if ah14 is not None and now_local >= asia_end_dt:
                print(f"{time_range} High: {colored(format_price(ah14), 'red', attrs=['bold'])}")
                print(f"{time_range} Low : {colored(format_price(al14), 'red', attrs=['bold'])}")
            else:
                print(f"{time_range} High: N/A")
                print(f"{time_range} Low : N/A")

        if LONDON_SESSION:
            # London Session (follows UK DST)
            lh_start = 15 + uk_shift

            start_time_london = datetime.combine(today, datetime.min.time()).replace(hour=lh_start, tzinfo=TZ)
            end_london = start_time_london + timedelta(hours=5, minutes=30)

            mask_london = (df_1m['dt'] >= start_time_london) & (df_1m['dt'] < end_london)

            time_range_london = f"{lh_start:02d}00-{lh_start+5:02d}30"

            title_text = " London Session "
            line = f"{title_text:=^30}"
            print(f"\n{colored(line, 'green', attrs=['bold'])}")

            df_london = df_1m[mask_london]
            if not df_london.empty:
                if now_local < end_london:
                    print(f"{time_range_london} High: N/A")
                    print(f"{time_range_london} Low : N/A")
                else:
                    lh, ll = df_london['high'].max(), df_london['low'].min()
                    print(f"{time_range_london} High: {colored(format_price(lh), 'green', attrs=['bold'])}")
                    print(f"{time_range_london} Low : {colored(format_price(ll), 'green', attrs=['bold'])}")
            else:
                print(f"{time_range_london} High: N/A")
                print(f"{time_range_london} Low : N/A")

        # Midnight Open (New York Midnight - follows US DST)
        midnight_hour = 12 + us_shift
        midnight_dt = datetime.combine(today, datetime.min.time()).replace(hour=midnight_hour, tzinfo=TZ)

        print("") # New line before Daily Open
        if now_local < midnight_dt:
            print("Daily Open : N/A")
        else:
            df_after = df_1m[df_1m['dt'] >= midnight_dt]
            if not df_after.empty:
                midnight_open = df_after.iloc[0]['open']
                print(f"Daily Open : {colored(format_price(midnight_open), 'blue', attrs=['bold'])}")
            else:
                print("Daily Open : N/A")

        # Current Price
        last_candle = df_1m.iloc[-1]
        cur_price = last_candle['close']
        cur_time = now_local.strftime("%H:%M")
        print(f"Current at : {format_price(cur_price)} at {cur_time}")

    except KeyboardInterrupt: print("\nAborted.")
    except Exception as e: print(f"Error: {e}")
    finally: clear_pycache()

if __name__ == "__main__":
    main()
