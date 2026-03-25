#!/usr/bin/python3
import ccxt.async_support as ccxt
import os, sys, asyncio
sys.dont_write_bytecode = True

def get_exchange(exchange_id):
    """Factory function to get a CCXT async exchange instance."""
    exchange_class = getattr(ccxt, exchange_id)
    # Binance uses 'future' or 'swap' for USDT-M futures in CCXT
    default_type = 'future' if exchange_id == 'binance' else 'linear'
    return exchange_class({
        'apiKey': os.environ.get(f'{exchange_id.upper()}_KEY'),
        'secret': os.environ.get(f'{exchange_id.upper()}_SECRET'),
        'options': {'defaultType': default_type}
    })

class UniversalAPI:
    def __init__(self, exchange_id):
        self.exchange = get_exchange(exchange_id)

    def has_credentials(self):
        """Checks if both API Key and Secret are present."""
        return self.exchange.apiKey and self.exchange.secret

    async def close(self):
        """Closes the exchange connection."""
        await self.exchange.close()

    async def position_information(self, pair):
        if not self.has_credentials():
            print(f"⚠️  [{self.exchange.id}] Skipping: API Key not found.")
            return None
        try:
            positions = await self.exchange.fetch_positions([pair])
            # Return dummy zero-position if empty, so we know the call succeeded
            return positions[0] if positions else {'contracts': 0}
        except Exception as e:
            print(f"❌ [{self.exchange.id}] Error fetching position: {e}")
        return None

    async def set_leverage(self, pair, leverage):
        if not self.has_credentials(): return
        try: return await self.exchange.set_leverage(leverage, pair)
        except Exception as e: print(f"❌ [{self.exchange.id}] Error setting leverage: {e}")

    async def set_margin_type(self, pair, margin_type="ISOLATED"):
        if not self.has_credentials(): return
        try: return await self.exchange.set_margin_mode(margin_type, pair)
        except Exception as e: print(f"❌ [{self.exchange.id}] Error setting margin type: {e}")

    async def set_position_mode(self, hedge_mode=False):
        if not self.has_credentials(): return
        try: return await self.exchange.set_position_mode(hedge_mode)
        except Exception as e: print(f"❌ [{self.exchange.id}] Error setting position mode: {e}")

    async def market_open_long(self, pair, qty):
        if not self.has_credentials():
            print(f"⚠️  [{self.exchange.id}] Skipping: API Key not found.")
            return None
        try:
            res = await self.exchange.create_market_buy_order(pair, qty)
            if res and res.get('id'): print(f"🚀 [{self.exchange.id}] GO_LONG {pair} {qty} 🚀")
            return res
        except Exception as e:
            print(f"❌ [{self.exchange.id}] Error opening LONG: {e}")

    async def market_open_short(self, pair, qty):
        if not self.has_credentials():
            print(f"⚠️  [{self.exchange.id}] Skipping: API Key not found.")
            return None
        try:
            res = await self.exchange.create_market_sell_order(pair, qty)
            if res and res.get('id'): print(f"💥 [{self.exchange.id}] GO_SHORT {pair} {qty} 💥")
            return res
        except Exception as e:
            print(f"❌ [{self.exchange.id}] Error opening SHORT: {e}")

    async def market_close(self, pair):
        if not self.has_credentials():
            print(f"⚠️  [{self.exchange.id}] Skipping: API Key not found.")
            return None
        try:
            pos = await self.position_information(pair)
            if pos and float(pos.get('contracts', 0)) != 0:
                side = 'sell' if float(pos['contracts']) > 0 else 'buy'
                res = await self.exchange.create_order(pair, 'market', side, abs(float(pos['contracts'])), None, {'reduceOnly': True})
                if res and res.get('id'): print(f"💰 [{self.exchange.id}] CLOSED {pair} 💰")
                return res
            # Only print this if we actually verified there's no position (pos is not None)
            elif pos is not None:
                print(f"[{self.exchange.id}] No position to close.")
        except Exception as e:
            print(f"❌ [{self.exchange.id}] Error closing position: {e}")
