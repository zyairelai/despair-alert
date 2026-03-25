#!/usr/bin/python3
import sys, asyncio
sys.dont_write_bytecode = True
import arguments
from api_universal import UniversalAPI

async def execute_close(exchange_id):
    try:
        api = UniversalAPI(exchange_id)
        res = await api.market_close(arguments.pair)
        if res and res.get('id'):
            print(f"✅ {exchange_id.upper()}: POSITION HAS BEEN CLOSED SUCCESSFULLY ✅")
        await api.close()
    except Exception as e:
        print(f"Error on {exchange_id}: {e}")

async def main():
    tasks = [execute_close(eid) for eid in arguments.exchanges]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
