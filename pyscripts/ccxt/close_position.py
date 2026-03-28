#!/usr/bin/python3
import sys, asyncio, requests, pandas, time, socket, arguments
sys.dont_write_bytecode = True
from api_universal import UniversalAPI
from termcolor import colored

session = requests.Session()

def get_klines(pair, interval):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 5}
    try:
        r = session.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
        cols = ["timestamp", "open", "high", "low", "close", "volume"]
        return pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
        print(f"\nError: {e}. Retrying in 30s...")
        time.sleep(30)
        return None
    except Exception as e:
        print(f"Error fetching klines: {e}")
        return None

async def execute_close(exchange_id):
    try:
        api = UniversalAPI(exchange_id)
        res = await api.market_close(arguments.pair)
        if res and res.get('id'):
            print(f"✅ {exchange_id.upper()}: POSITION HAS BEEN CLOSED SUCCESSFULLY ✅")
        await api.close()
    except Exception as e:
        print(f"Error on {exchange_id}: {e}")

async def main():
    target_price = None
    show_decimals = True
    if len(sys.argv) > 1:
        try:
            arg_str = sys.argv[1]
            target_price = float(arg_str)
            show_decimals = "." in arg_str
            display_price = target_price if show_decimals else int(target_price)
            print(f"\n🐺 {arguments.pair} LIMIT CLOSE AT {display_price} 🐺\n")
        except ValueError: pass

    if target_price is not None:
        is_major = any(s in arguments.pair for s in ["BTC", "ETH"])
        while True:
            df = get_klines(arguments.pair, "1m")
            if df is not None:
                last_candle = df.iloc[-1]
                h, l = last_candle['high'], last_candle['low']
                if is_major and not show_decimals:
                    h_disp, l_disp, t_disp = int(h), int(l), int(target_price)
                else:
                    h_disp, l_disp, t_disp = h, l, target_price
                pair_tag = colored(f"[{arguments.pair} 1m]", "blue")
                high_tag = colored(f"High: {h_disp}", "green")
                low_tag = colored(f"Low: {l_disp}", "red")
                target_tag = colored(f"Target: {t_disp}", "yellow")
                sys.stdout.write(f"\r🔍 {pair_tag} {high_tag} | {low_tag} | {target_tag}    ")
                sys.stdout.flush()

                if l <= target_price <= h:
                    print(f"\n\n🎯 TARGET PRICE HIT: {t_disp}. POSITION CLOSE. 🎯")
                    break
            await asyncio.sleep(1)

    tasks = [execute_close(eid) for eid in arguments.exchanges]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)
