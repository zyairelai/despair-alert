#!/usr/bin/python3
import sys
sys.dont_write_bytecode = True
import time, arguments

def get_timestamp():
    return int(time.time() * 1000)

def position_information(pair):
    return arguments.binance_client.futures_position_information(symbol=pair, timestamp=get_timestamp())

def change_leverage(pair, leverage):
    return arguments.binance_client.futures_change_leverage(symbol=pair, leverage=leverage, timestamp=get_timestamp())

def change_margin_to_ISOLATED(pair):
    try: return arguments.binance_client.futures_change_margin_type(symbol=pair, marginType="ISOLATED", timestamp=get_timestamp())
    except Exception as e: print(e)

def change_position_mode():
    try: return arguments.binance_client.futures_change_position_mode(dualSidePosition="false", timestamp=get_timestamp())
    except Exception as e: print(e)

if __name__ == "__main__":
    print(change_leverage(arguments.pair, 50))
    print(change_margin_to_ISOLATED(arguments.pair))
    print(change_position_mode())
    
    print("\nPosition Information:")
    print(position_information(arguments.pair))
