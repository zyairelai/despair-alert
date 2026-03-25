#!/usr/bin/python3
import sys
sys.dont_write_bytecode = True
import time, arguments

def market_open_long(pair, quantity):
    return arguments.binance_client.futures_create_order(
        symbol=pair,
        quantity=quantity,
        type="MARKET",
        side="BUY",
        timestamp=int(time.time() * 1000)
    )

if __name__ == "__main__":
    res = market_open_long(arguments.pair, arguments.quantity)
    if res and res.get('orderId'): print("🚀 LONG TO THE MOON 🚀")
