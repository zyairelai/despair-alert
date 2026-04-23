#!/usr/bin/python3
# python-argcomplete-ok

import pandas, requests, time, socket, os, sys, argparse, argcomplete
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

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    response = requests.get(url, params=params)
    return response.json()

def get_session_levels(df, date, start_hour, end_hour):
    """Filters klines for a specific date and hour range (MYT)."""
    # Convert timestamp to MYT
    df['dt'] = pandas.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert(MYT)
    
    mask = (df['dt'].dt.date == date) & (df['dt'].dt.hour >= start_hour) & (df['dt'].dt.hour < end_hour)
    session_df = df[mask]
    
    if session_df.empty:
        return None, None
    
    return int(session_df['high'].max()), int(session_df['low'].min())

def main():
    parser = argparse.ArgumentParser(description='The SESSIONS script.')
    parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help='Trading pair (default: BTCUSDT)')
    parser.add_argument('--alert', action='store_true', help='Read alert if price hits Prev 1D High/Low')
    
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    SYMBOL = args.symbol

    try:
        first_run = True
        while True:
            # 1. Previous 1D Levels
            df_1d = get_klines(SYMBOL, "1d", limit=2)
            # index -2 is the previous completed day
            prev_1d = df_1d.iloc[-2]
            h1d, l1d = int(prev_1d['high']), int(prev_1d['low'])
            m1d = int((h1d + l1d) / 2)

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
                    print(colored(f"\n>>> ALERT: {msg} <<<", "yellow", attrs=["bold"]))
                    triggered = True
                elif curr_price <= l1d:
                    msg = f"{symbol_short} touch Prev Low"
                    telegram_bot_sendtext(msg)
                    print(colored(f"\n>>> ALERT: {msg} <<<", "yellow", attrs=["bold"]))
                    triggered = True

            if first_run or not args.alert:
                print(f"\n{' Prev 1D ':=^30}")
                print(f"Prev 1D High: {colored(str(h1d), 'white', attrs=['bold'])}")
                print(f"Prev 1D Mid : {colored(str(m1d), 'white', attrs=['bold'])}")
                print(f"Prev 1D Low : {colored(str(l1d), 'white', attrs=['bold'])}")

                # 2. Session Data (1m klines)
                # Fetch 1500 minutes to cover the full current day in MYT
                df_1m = get_klines(SYMBOL, "1m", limit=1500)
                
                now_myt = datetime.now(MYT)
                today = now_myt.date()

                # Tokyo Session: 08:00 - 15:00 MYT
                th, tl = get_session_levels(df_1m, today, 8, 15)
                print(f"\n{' Tokyo Session ':=^30}")
                if th is not None:
                    print(f"Tokyo High: {colored(str(th), 'red', attrs=['bold'])}")
                    print(f"Tokyo Low : {colored(str(tl), 'red', attrs=['bold'])}")
                else:
                    print("Tokyo High: N/A (Not started or no data)")
                    print("Tokyo Low : N/A (Not started or no data)")

                # London Session: 16:00 - 20:00 MYT
                lh, ll = get_session_levels(df_1m, today, 16, 20)
                print(f"\n{' London Session ':=^30}")
                if lh is not None:
                    print(f"London High: {colored(str(lh), 'green', attrs=['bold'])}")
                    print(f"London Low : {colored(str(ll), 'green', attrs=['bold'])}")
                else:
                    print("London High: N/A (Not started or no data)")
                    print("London Low : N/A (Not started or no data)")

                # 2.5 Opening Session (US Open)
                # 21:30 - 21:45 (15m)
                # 21:30 - 22:00 (30m)
                start_time = datetime.combine(today, datetime.min.time()).replace(hour=21, minute=30, tzinfo=MYT)
                end_15m = start_time + timedelta(minutes=15)
                end_30m = start_time + timedelta(minutes=30)
                
                mask_15m = (df_1m['dt'] >= start_time) & (df_1m['dt'] < end_15m)
                mask_30m = (df_1m['dt'] >= start_time) & (df_1m['dt'] < end_30m)
                
                # 15m
                print(f"\n{' Opening 15m ':=^30}")
                df_15m = df_1m[mask_15m]
                if not df_15m.empty:
                    if now_myt < end_15m:
                        print(f"15m High: {colored('[developing]', 'yellow')}")
                        print(f"15m Low : {colored('[developing]', 'yellow')}")
                    else:
                        h15, l15 = int(df_15m['high'].max()), int(df_15m['low'].min())
                        print(f"15m High: {colored(str(h15), 'yellow', attrs=['bold'])}")
                        print(f"15m Low : {colored(str(l15), 'yellow', attrs=['bold'])}")
                else:
                    print("15m High: N/A")
                    print("15m Low : N/A")
                    
                # 30m
                print(f"\n{' Opening 30m ':=^30}")
                df_30m = df_1m[mask_30m]
                if not df_30m.empty:
                    if now_myt < end_30m:
                        print(f"30m High: {colored('[developing]', 'yellow')}")
                        print(f"30m Low : {colored('[developing]', 'yellow')}")
                    else:
                        h30, l30 = int(df_30m['high'].max()), int(df_30m['low'].min())
                        print(f"30m High: {colored(str(h30), 'yellow', attrs=['bold'])}")
                        print(f"30m Low : {colored(str(l30), 'yellow', attrs=['bold'])}")
                else:
                    print("30m High: N/A")
                    print("30m Low : N/A")

                # 3. Monday High/Low
                # Fetch last 10 days to ensure we get the last Monday
                df_monday = get_klines(SYMBOL, "1d", limit=10)
                df_monday['dt'] = pandas.to_datetime(df_monday['timestamp'], unit='ms', utc=True).dt.tz_convert(MYT)
                monday_candles = df_monday[df_monday['dt'].dt.weekday == 0]
                
                print(f"\n{' Monday ':=^30}")
                if not monday_candles.empty:
                    last_monday = monday_candles.iloc[-1]
                    mh, ml = int(last_monday['high']), int(last_monday['low'])
                    print(f"Monday High: {colored(str(mh), 'blue', attrs=['bold'])}")
                    print(f"Monday Low : {colored(str(ml), 'blue', attrs=['bold'])}")
                else:
                    print("Monday High: N/A")
                    print("Monday Low : N/A")

            if not args.alert or triggered:
                break
            
            if first_run:
                print(colored(f"\nMonitoring {SYMBOL} Alert..."))
            
            first_run = False
            time.sleep(5)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
