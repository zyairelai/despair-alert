#!/usr/bin/python3
import os, time, sys
sys.dont_write_bytecode = True
from binance.client import Client
from params import pair, quantity

# Get environment variables
binance_key = os.environ.get('BINANCE_KEY')
binance_sec = os.environ.get('BINANCE_SECRET')
binance_client = Client(binance_key, binance_sec)

def market_open_short(pair, quantity):
    return binance_client.futures_create_order(
        symbol=pair,
        quantity=quantity,
        type="MARKET",
        side="SELL",
        timestamp=int(time.time() * 1000)
    )

if __name__ == "__main__":
    res = market_open_short(pair, quantity)
    if res and res.get('orderId'): print("💥 SHORT DESPAIR 💥")
