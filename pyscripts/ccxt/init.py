#!/usr/bin/python3
import sys, asyncio
sys.dont_write_bytecode = True
import arguments
from api_universal import UniversalAPI

async def execute_init(exchange_id):
    try:
        api = UniversalAPI(exchange_id)
        print(f"--- Initializing {exchange_id.upper()} ---")
        await api.set_leverage(arguments.pair, 50)
        await api.set_margin_type(arguments.pair, "ISOLATED")
        await api.set_position_mode(hedge_mode=False)
        pos = await api.position_information(arguments.pair)
        if pos: print(f"[{exchange_id}] {pos}")
        await api.close()
    except Exception as e:
        print(f"Error on {exchange_id} init: {e}")

async def main():
    tasks = [execute_init(eid) for eid in arguments.exchanges]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
