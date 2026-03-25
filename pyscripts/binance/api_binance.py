import os, time, config, requests
from binance.client import Client

# Get environment variables
binance_key = os.environ.get('BINANCE_KEY')
binance_sec = os.environ.get('BINANCE_SECRET')
binance_client = Client(binance_key, binance_sec)

def get_timestamp():
    return int(time.time() * 1000)

def position_information(pair):
    return binance_client.futures_position_information(symbol=pair, timestamp=get_timestamp())

def account_trades(pair, timestamp) :
    return binance_client.futures_account_trades(symbol=pair, timestamp=get_timestamp(), startTime=timestamp)

def LONG_SIDE(response):
    if float(response[0].get('positionAmt')) > 0: return "LONGING"
    elif float(response[0].get('positionAmt')) == 0: return "NO_POSITION"

def SHORT_SIDE(response):
    if float(response[0].get('positionAmt')) < 0 : return "SHORTING"
    elif float(response[0].get('positionAmt')) == 0: return "NO_POSITION"

def change_leverage(pair, leverage):
    return binance_client.futures_change_leverage(symbol=pair, leverage=leverage, timestamp=get_timestamp())

def change_margin_to_ISOLATED(pair):
    return binance_client.futures_change_margin_type(symbol=pair, marginType="ISOLATED", timestamp=get_timestamp())

def market_open_long(pair, quantity):
    binance_client.futures_create_order(symbol=pair, quantity=quantity, side="BUY", type="MARKET", timestamp=get_timestamp())
 
def market_open_short(pair, quantity):
    binance_client.futures_create_order(symbol=pair, quantity=quantity, side="SELL", type="MARKET", timestamp=get_timestamp())

def market_close_long(pair, response):
    binance_client.futures_create_order(symbol=pair, quantity=abs(float(response[0].get('positionAmt'))), side="SELL", type="MARKET", timestamp=get_timestamp())

def market_close_short(pair, response):
    binance_client.futures_create_order(symbol=pair, quantity=abs(float(response[0].get('positionAmt'))), side="BUY", type="MARKET", timestamp=get_timestamp())

# https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info
