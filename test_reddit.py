import requests
import ssl
import praw

# Test 1: old.reddit.com
print("=== Test 1: old.reddit.com ===")
try:
    r = requests.get('https://old.reddit.com/r/CryptoCurrency/hot.json?limit=2', 
                     headers={'User-Agent': 'crypto-alpha-bot/1.0'}, timeout=10)
    print(f"Status: {r.status_code}")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")

# Test 2: oauth.reddit.com (API endpoint)
print("\n=== Test 2: oauth.reddit.com ===")
try:
    r = requests.get('https://oauth.reddit.com/r/CryptoCurrency/hot?limit=2',
                     headers={'User-Agent': 'crypto-alpha-bot/1.0'}, timeout=10)
    print(f"Status: {r.status_code}")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")

# Test 3: PRAW (without credentials, just test connection)
print("\n=== Test 3: PRAW read-only ===")
try:
    reddit = praw.Reddit(
        client_id="test_id",
        client_secret="test_secret", 
        user_agent="crypto-alpha-bot/1.0"
    )
    # This will fail auth but tests SSL connectivity
    for post in reddit.subreddit("CryptoCurrency").hot(limit=1):
        print(f"OK: {post.title[:60]}")
except Exception as e:
    print(f"Result: {type(e).__name__}: {str(e)[:200]}")

# Test 4: Check Python SSL version
print(f"\n=== SSL Info ===")
print(f"OpenSSL: {ssl.OPENSSL_VERSION}")
