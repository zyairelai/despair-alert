#!/usr/bin/python3

import pandas, requests, time, socket, os, sys, argparse

def print_usage(): print(f"[i] Usage: {os.path.basename(sys.argv[0])} [target1] [target2] [target3]....")
if "-h" in sys.argv or "--help" in sys.argv:
    print_usage()
    sys.exit(0)

targets = []
if len(sys.argv) == 1:
    try:
        target_input = input("[+] Enter target price: ")
        if target_input.strip():
            targets = [target_input.strip()]
            print(f"Set Price Alert: {targets[0]}")
        else:
            print_usage()
            sys.exit(1)
    except ValueError:
        print("[!] Invalid price format.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)
    # Handle hidden flags when no positional targets provided
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
    args, _ = parser.parse_known_args()
    SYMBOL = args.symbol
else:
    parser = argparse.ArgumentParser(add_help=False)
    parser.error = lambda message: (print_usage(), sys.exit(1))
    parser.add_argument('targets', type=str, nargs='*')
    parser.add_argument('--symbol', '--pair', dest='symbol', default='BTCUSDT', help=argparse.SUPPRESS)
    args = parser.parse_args()
    targets = args.targets
    SYMBOL = args.symbol

    if len(targets) == 1:
        print(f"Set Price Alert: {targets[0]}")
    else:
        for i, t in enumerate(targets, start=1):
            print(f"Target {i}: {t}")

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'parse_mode': 'html', 'text': bot_message}
    response = requests.get(url, params=params)
    return response.json()

# telegram_bot_sendtext("Telegram works!")

session = requests.Session()
def get_klines(pair, interval, limit=100):
    spot_url = "https://api.binance.com/api/v1/klines"
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": limit}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick["body"] = (candlestick["close"] - candlestick["open"]).abs()
    candlestick["upper_wick"] = candlestick["high"] - candlestick[["open", "close"]].max(axis=1)
    candlestick["lower_wick"] = candlestick[["open", "close"]].min(axis=1) - candlestick["low"]
    return candlestick

INITIAL_PRICE = None

def price_alert(symbol):
    global INITIAL_PRICE
    df = get_klines(symbol, "1m", limit=1)
    now_candle = df.iloc[-1]
    
    if INITIAL_PRICE is None:
        INITIAL_PRICE = now_candle['close']
        print(f"Monitoring... (Current Price: {INITIAL_PRICE})")
        return

    for target_price_str in targets:
        try: target_p = float(target_price_str)
        except ValueError: continue

        # Swallowing logic: Trigger if target is hit or passed by the 1m High/Low
        if INITIAL_PRICE < target_p:
            if now_candle["high"] >= target_p:
                telegram_bot_sendtext(f"{symbol} touched target: {target_price_str}")
                exit()
        else:
            if now_candle["low"] <= target_p:
                telegram_bot_sendtext(f"{symbol} touched target: {target_price_str}")
                exit()

try:
    while True:
        try:
            price_alert(SYMBOL)
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(30)
            continue
except KeyboardInterrupt: print("\n\nAborted.\n")
