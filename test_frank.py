import os
import twitter_tracker as tt
from dotenv import load_dotenv

def test_frank_researcher():
    load_dotenv()
    
    token = os.getenv("RAPIDAPI_KEY")
    
    # MOCK DATA OVERRIDE IF NO REAL TOKEN
    if not token or token == "your_rapidapi_key_here":
        print("No real RAPIDAPI_KEY found in .env.")
        print("Using MOCK API behavior to demonstrate the logic...\n")
        
        # We override the fetch function inside the module just for this test execution
        def mock_fetch(group_name, limit=5):
            print(f"[API Call] Fetching most recent tweets for group {group_name}...")
            
            # If it's one of our hardcoded alpha groups, simulate an alpha drop!
            if group_name == "DAO Group":
                 return [{
                     'id': '999', 
                     'text': "Been looking into @NewGemToken recently. Their tech stack is insane.", 
                     'author': '@frankresearcher', 
                     'date': '2026-04-13 17:00:00', 
                     'matched_group': 'DAO Group',
                     'url': f'https://twitter.com/frankresearcher/status/999'
                 }]
            
            return []
        
        tt.fetch_alpha_group = mock_fetch

    print("Executing tracking check for DAO Group (including @FrankResearcher)...")
    
    new_tweets = tt.fetch_alpha_group("DAO Group")
    
    if not new_tweets:
        print("No recent Web3/cryptocurrency tweets found for DAO Group.")
    else:
        print(f"\n[SUCCESS] Found {len(new_tweets)} total alerts from your feed:\n")
        for tweet in new_tweets:
            print("-" * 50)
            if 'matched_group' in tweet:
                print(f"[{tweet['matched_group'].upper()} ALERT] {tweet['author']}")
            else:
                print(f"Author: {tweet['author']}")
                
            print(f"Date:   {tweet.get('date', 'Unknown Date')}")
            print(f"Message: {tweet['text']}")
            print(f"URL: {tweet['url']}")
            print("-" * 50)

if __name__ == "__main__":
    test_frank_researcher()
