import os, time
from binance.client import Client

# Trading Parameters
pair = "BTCUSDT"
quantity = 0.01

# Get environment variables
binance_key = os.environ.get('BINANCE_KEY')
binance_sec = os.environ.get('BINANCE_SECRET')
binance_client = Client(binance_key, binance_sec)
