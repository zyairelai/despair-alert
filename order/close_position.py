#!/usr/bin/python3
import os, time, sys
sys.dont_write_bytecode = True
from binance.client import Client
from params import pair

# Get environment variables
binance_key = os.environ.get('BINANCE_KEY')
binance_sec = os.environ.get('BINANCE_SECRET')
binance_client = Client(binance_key, binance_sec)

def position_information(pair):
    return binance_client.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))

def market_close_long(pair, response):
    return binance_client.futures_create_order(
        symbol=pair,
        quantity=abs(float(response[0].get('positionAmt'))),
        side="SELL",
        type="MARKET",
        timestamp=int(time.time() * 1000)
    )

def market_close_short(pair, response):
    return binance_client.futures_create_order(
        symbol=pair,
        quantity=abs(float(response[0].get('positionAmt'))),
        side="BUY",
        type="MARKET",
        timestamp=int(time.time() * 1000)
    )

if __name__ == "__main__":
    response = position_information(pair)

    if response and float(response[0].get('positionAmt')) != 0:
        res = None
        if float(response[0].get('positionAmt')) < 0: res = market_close_short(pair, response)
        elif float(response[0].get('positionAmt')) > 0: res = market_close_long(pair, response)
        if res and res.get('orderId'): print("✅ Position has been closed successfully.")
    else: print("No position to close.")
