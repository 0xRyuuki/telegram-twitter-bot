import os
import twitter_tracker as tt
from dotenv import load_dotenv

load_dotenv()

def test_fetch():
    print("Testing RapidAPI fetch for category 'signals/moves'...")
    results = tt.fetch_category_global("signals/moves", limit=2)
    print(f"Results found: {len(results)}")
    for res in results:
        print(f"- {res['author']}: {res['text'][:50]}...")

if __name__ == '__main__':
    test_fetch()
