#!/usr/bin/python3
import sys, asyncio
sys.dont_write_bytecode = True
import arguments
from api_universal import UniversalAPI

async def execute_short(exchange_id):
    try:
        api = UniversalAPI(exchange_id)
        res = await api.market_open_short(arguments.pair, arguments.quantity)
        if res and res.get('id'):
            print(f"💥 {exchange_id.upper()}: SHORT DESPAIR 💥")
        await api.close()
    except Exception as e:
        print(f"Error on {exchange_id}: {e}")

async def main():
    tasks = [execute_short(eid) for eid in arguments.exchanges]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
