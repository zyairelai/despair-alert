import sys
sys.dont_write_bytecode = True

# Active Exchanges
exchanges = ['binance']
# exchanges = ['binance', 'bybit']

# Trading Parameters
pair = "BTCUSDT"
quantity = 0.01

# Command-line override for quantity
if len(sys.argv) > 1:
    try: quantity = float(sys.argv[1])
    except ValueError: pass
