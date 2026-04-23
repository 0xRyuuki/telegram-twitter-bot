import os
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Use the main RapidAPI key (same as Twitter) — subscribe it to Reddit34 on RapidAPI
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# === SINGLE SUBREDDIT to minimize API calls ===
# r/CryptoCurrency is the largest crypto subreddit and covers all topics
CRYPTO_SUBREDDIT = "CryptoCurrency"

# === REDDIT ALPHA TOPIC FILTERS ===
REDDIT_TOPICS = {
    "signals": ["signal", "buy signal", "sell signal", "bullish", "bearish",
                "long", "short", "entry", "breakout", "breakdown", "reversal",
                "pump", "accumulation zone", "support", "resistance"],
    "chart_analysis": ["chart", "technical analysis", "ta ", "rsi", "macd",
                       "moving average", "fibonacci", "head and shoulders",
                       "cup and handle", "wedge", "pattern", "indicator",
                       "trend line", "volume profile"],
    "narrative": ["narrative", "next big", "upcoming", "meta shift", "rotation",
                  "sector rotation", "trend", "thesis", "alpha", "undervalued",
                  "sleeping giant", "gem", "moonshot", "100x"],
    "market_discussion": ["market cap", "dominance", "alt season",
                          "altseason", "btc dominance", "eth/btc", "correlation",
                          "macro", "fed", "inflation", "recession", "crash",
                          "rally", "correction", "capitulation"],
    "btc": ["bitcoin", "btc", "satoshi", "halvening", "halving", "lightning network"],
    "eth": ["ethereum", "eth", "vitalik", "merge", "eip", "layer 2", "l2",
            "rollup", "staking", "gas fee"],
    "altcoins": ["altcoin", "alt coin", "solana", "sol", "avax", "matic",
                 "polygon", "cardano", "ada", "polkadot", "dot", "chainlink",
                 "link", "arbitrum", "arb", "optimism", "base chain",
                 "memecoin", "meme coin", "defi", "rwa", "ai crypto"],
}

# === SPAM / LOW QUALITY FILTERS ===
REDDIT_SPAM_PHRASES = [
    "join my group", "telegram group", "discord link", "free signal",
    "guaranteed profit", "100% return", "send me crypto", "dm me",
    "check my profile", "link in bio", "not financial advice but trust me",
    "pump group", "insider info", "whale alert group", "vip access",
    "sign up now", "use my referral", "referral code", "promo code",
    "airdrop claim", "click here", "limited time", "act fast",
    "double your", "send btc to",
]

# Quality thresholds
MIN_SCORE = 20          # Minimum upvotes
MIN_COMMENTS = 5        # Minimum comments
MAX_AGE_HOURS = 6       # Only posts from last 6 hours


def _call_reddit_api(params):
    """Call Reddit34 RapidAPI — uses 1 API call."""
    if not RAPIDAPI_KEY:
        print("RapidAPI Key missing.")
        return None
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "reddit34.p.rapidapi.com"
    }
    try:
        response = requests.get(
            "https://reddit34.p.rapidapi.com/getPostsBySubreddit",
            headers=headers, params=params
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Reddit API Error: {e}")
        return None


def _classify_post(title, body):
    """Classify a Reddit post into matching topic categories."""
    combined = (title + " " + body).lower()
    matched = []
    for topic, keywords in REDDIT_TOPICS.items():
        for kw in keywords:
            if kw.lower() in combined:
                matched.append(topic)
                break
    return matched


def _is_spam(title, body):
    """Check if a reddit post is spam or low quality."""
    combined = (title + " " + body).lower()
    if any(phrase in combined for phrase in REDDIT_SPAM_PHRASES):
        return True
    if len(re.findall(r'https?://\S+', title + " " + body)) > 3:
        return True
    return False


def _format_time_ago(created_utc):
    """Convert UTC timestamp to a human-readable 'X ago' string."""
    diff = time.time() - created_utc
    if diff < 60:
        return "just now"
    elif diff < 3600:
        return f"{int(diff / 60)}m ago"
    elif diff < 86400:
        return f"{int(diff / 3600)}h ago"
    else:
        return f"{int(diff / 86400)}d ago"


def fetch_reddit_alpha(limit_per_sub=15):
    """
    Fetch HOT posts from r/CryptoCurrency via RapidAPI.
    Uses exactly 1 API call per invocation to conserve quota.
    Deduplication is handled by the database (seen_reddit_posts).
    """
    data = _call_reddit_api({
        "subreddit": CRYPTO_SUBREDDIT,
        "sort": "hot",
        "limit": str(limit_per_sub)
    })

    if not data or not data.get("success"):
        return []

    all_results = []
    posts = data.get("data", {}).get("posts", [])

    for post_wrapper in posts:
        p = post_wrapper.get("data", {})

        post_id = p.get("id", "")
        title = p.get("title", "")
        body = p.get("selftext", "")
        author = p.get("author", "unknown")
        score = p.get("score", 0) or 0
        num_comments = p.get("num_comments", 0) or 0
        created_utc = p.get("created_utc", 0)
        permalink = p.get("permalink", "")
        flair = p.get("link_flair_text", "") or ""

        # Skip posts older than MAX_AGE_HOURS
        if time.time() - created_utc > MAX_AGE_HOURS * 3600:
            continue

        # Skip bots
        if author.lower() in ["automoderator", "[deleted]", "snapshillbot"]:
            continue

        # Skip spam
        if _is_spam(title, body):
            continue

        # Quality filter
        if score < MIN_SCORE or num_comments < MIN_COMMENTS:
            continue

        # Classify into topics
        matched_topics = _classify_post(title, body)
        if not matched_topics:
            continue

        # Truncate body
        preview = body[:300].strip()
        if len(body) > 300:
            preview += "..."

        time_ago = _format_time_ago(created_utc)
        url = f"https://reddit.com{permalink}" if permalink else ""

        all_results.append({
            "id": f"reddit_{post_id}",
            "title": title,
            "body": preview,
            "author": f"u/{author}",
            "subreddit": f"r/{CRYPTO_SUBREDDIT}",
            "score": score,
            "comments": num_comments,
            "flair": flair,
            "topics": matched_topics,
            "time_ago": time_ago,
            "url": url,
        })

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results
