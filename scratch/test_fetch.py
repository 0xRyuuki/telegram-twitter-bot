import asyncio
import twitter_tracker as tt
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    print("Testing fetch for ChineseCabals...")
    results = await asyncio.to_thread(tt.fetch_alpha_group, "ChineseCabals", limit=5)
    print(f"Results found: {len(results)}")
    for r in results:
        print(f" - {r['author']}: {r['text'][:50]}...")

if __name__ == "__main__":
    asyncio.run(test())
