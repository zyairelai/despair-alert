#!/usr/bin/python3
import sys, asyncio
sys.dont_write_bytecode = True
import arguments
from api_universal import UniversalAPI

async def execute_long(exchange_id):
    try:
        api = UniversalAPI(exchange_id)
        res = await api.market_open_long(arguments.pair, arguments.quantity/2)
        if res and res.get('id'):
            print(f"🚀 {exchange_id.upper()}: LONG TO THE MOON 🚀")
        await api.close()
    except Exception as e:
        print(f"Error on {exchange_id}: {e}")

async def main():
    tasks = [execute_long(eid) for eid in arguments.exchanges]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
