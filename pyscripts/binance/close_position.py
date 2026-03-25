#!/usr/bin/python3
import sys
sys.dont_write_bytecode = True
import time, arguments

def position_information(pair):
    return arguments.binance_client.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))

def market_close_long(pair, response):
    return arguments.binance_client.futures_create_order(
        symbol=pair,
        quantity=abs(float(response[0].get('positionAmt'))),
        side="SELL",
        type="MARKET",
        timestamp=int(time.time() * 1000)
    )

def market_close_short(pair, response):
    return arguments.binance_client.futures_create_order(
        symbol=pair,
        quantity=abs(float(response[0].get('positionAmt'))),
        side="BUY",
        type="MARKET",
        timestamp=int(time.time() * 1000)
    )

if __name__ == "__main__":
    response = position_information(arguments.pair)

    if response and float(response[0].get('positionAmt')) != 0:
        res = None
        if float(response[0].get('positionAmt')) < 0: res = market_close_short(pair, response)
        elif float(response[0].get('positionAmt')) > 0: res = market_close_long(pair, response)
        if res and res.get('orderId'): print("✅ POSITION HAS BEEN CLOSED SUCCESSFULLY ✅")
    else: print("❌ NO POSITION TO CLOSE ❌")
