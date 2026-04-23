import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

EVENT_CATEGORIES = [
    "airdrop", "economy", "regulations", "listings", "sale", 
    "hack", "discussion", "TGE", "signals/moves", "AI AGENT"
]

AGENT_ACCOUNTS = [
    "@aixbt"
]

BLOCKED_USERS = [
    "aytanzania",
    "azenice",
    "whalemasterpro",
    "anilkum10140197",
    "chaitanyar79"
]

SHILL_PHRASES = [
    "join my group", "vip group", "premium group", "link in bio", 
    "join my telegram", "free signal", "join premium", "whatsapp group",
    "discord link", "100x gem", "next doge", "x100", "my group",
    "join our group", "free members", "premium signal", "vip channel",
    "tg link", "telegram link", "exclusive group", "my telegram",
    "pump signal", "1000x", "gem alert", "link below", "my bio",
    "join discord", "crypto signals", "follow us on telegram",
    "take-profits", "take profits", "take profit",
    "entry price:", "stop loss:", "free calls", "crypto call",
    "send a direct message", "how to buy", "how to claim",
    "direct message me", "dm us"
]

# === CATEGORY-SPECIFIC QUALITY FILTERS ===

# Only track listings from these major exchanges
MAJOR_EXCHANGES = ["binance", "bybit", "okx", "upbit"]
EXCHANGE_ACCOUNTS = ["binance", "bybit_official", "okx", "upbitglobal", "upbitenglish"]

# Notable projects to always allow through sale/presale filter
NOTABLE_PROJECTS = ["octra"]

# Extra spam phrases specific to airdrop/presale engagement bait
AIRDROP_SPAM_PHRASES = [
    "drop your wallet", "send me", "dm for airdrop",
    "retweet and follow", "rt + follow", "like and retweet",
    "follow and rt", "giveaway", "free mint", "drop wallet",
    "comment your address", "tag 3 friends", "share this post",
    "rt this", "must follow", "follow + like", "like + rt",
    "tag a friend", "retweet this", "comment below",
    "follow & retweet", "gleam.io", "enter giveaway"
]

# === TOPIC CLUSTERS (used for matching tweets to categories) ===
TOPIC_CLUSTERS = {
    "airdrop": ["airdrop", "airdrop live", "airdrop confirmed", "airdrop snapshot", "airdrop eligibility", "claim airdrop"],
    "economy": ["economy", "macro", "cpi", "fomc", "inflation", "gdp", "rate hike", "fed"],
    "regulations": ["sec", "gary gensler", "bill", "ban", "legal", "lawsuit", "regulation", "etf", "court"],
    "listings": ["listing", "listed on", "will list", "new listing", "listing announcement"],
    "sale": ["presale", "pre-sale", "token sale", "launchpad", "public sale"],
    "hack": ["hack", "exploit", "stolen", "compromised", "phishing", "drainer"],
    "discussion": ["thoughts", "opinion", "thread", "discuss", "what do you think"],
    "TGE": ["tge", "token generation event", "token launch", "now trading", "just launched", "trading live"],
    "signals/moves": ["bought", "buying", "sold", "added to bag", "long", "short", "position", "accumulate", "dip", "chart", "technical analysis", "ta ", "rsi", "macd", "moving average", "fibonacci", "head and shoulders", "cup and handle", "wedge", "pattern", "indicator", "trend line", "volume profile"],
    "AI AGENT": ["\"base ca\"", "base contract address", "\"ca on base\"", "launching on base", "deploying on base"]
}

# === CUSTOM SEARCH QUERIES (precise API queries per category) ===
SEARCH_QUERIES = {
    "airdrop": '(airdrop) (live OR confirmed OR eligible OR snapshot OR guide OR claim OR official OR announced) -filter:retweets (crypto OR token OR coin OR blockchain)',
    "listings": '(binance OR bybit OR okx OR upbit) (listing OR listed OR "will list" OR "new listing") -filter:retweets',
    "sale": '(presale OR "pre-sale" OR "token sale" OR launchpad) (live OR whitelist OR upcoming OR open OR official) -filter:retweets (crypto OR token) lang:en',
    "TGE": '("token launch" OR tge OR "token generation event" OR "now trading" OR "just launched" OR "trading live") -filter:retweets (crypto OR token OR dex OR cex)',
}

ALPHA_GROUPS = {}
try:
    with open("ALPHA TWITTER ACC.txt", "r", encoding="utf-8") as f:
        current_group = None
        for line in f.read().splitlines():
            line = line.strip()
            if not line:
                continue
            if not line.startswith("@"):
                current_group = line
                ALPHA_GROUPS[current_group] = []
            else:
                if current_group:
                    ALPHA_GROUPS[current_group].append(line.replace("@", ""))
except Exception as e:
    print(f"Error loading ALPHA TWITTER ACC.txt: {e}")

def _call_rapidapi(url, querystring):
    if not RAPIDAPI_KEY:
        print("RapidAPI Key missing. Please set RAPIDAPI_KEY in .env.")
        return None
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "twitter-api45.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"RapidAPI Error fetching {url}: {e}")
        return None

def fetch_category_global(category_name, limit=5):
    """
    Fetches real-time tweets for a category with precision filtering.
    Uses custom search queries for airdrop/listings/sale/TGE to reduce noise.
    """
    if category_name not in TOPIC_CLUSTERS:
        return []
        
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    
    # Use custom search query if available, otherwise build from topic clusters
    if category_name in SEARCH_QUERIES:
        query_str = SEARCH_QUERIES[category_name]
    else:
        cluster_words = TOPIC_CLUSTERS[category_name]
        query_str = "(" + " OR ".join(cluster_words[:5]) + ") -filter:retweets"
        query_str += " (crypto OR cryptocurrency OR token OR coin OR eth OR btc OR sol OR altcoin OR memecoin)"
        if category_name == "sale":
            query_str += " lang:en"
        
    querystring = {"query": query_str, "search_type": "Latest"}
    
    data = _call_rapidapi(url, querystring)
    if not data or 'timeline' not in data:
        return []
            
    results = []
    for t in data['timeline'][:limit]:
        if t.get('type') != 'tweet':
            continue
            
        t_id = t.get('tweet_id', '')
        text = t.get('text', '')
        date = t.get('created_at', 'Unknown Date')
        author_name = t.get('screen_name', 'UnknownUser')
        
        display_name = t.get('user_info', {}).get('name', '').lower()
        if 'support' in display_name or 'helpdesk' in display_name or 'customer service' in display_name:
            continue
        
        if author_name.lower() in [u.lower() for u in BLOCKED_USERS]:
            continue
            
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in SHILL_PHRASES):
            continue
            
        if len(re.findall(r'#\w+', text)) > 1:
            continue
            
        long_words = re.findall(r'\b[a-zA-Z0-9]{30,100}\b', text)
        if any(not w.lower().startswith('0x') for w in long_words):
            continue
        
        # =============================================
        # CATEGORY-SPECIFIC POST-FILTERING
        # =============================================
        
        # --- AIRDROP: Block engagement-bait, require actual airdrop context ---
        if category_name == "airdrop":
            if any(phrase in text_lower for phrase in AIRDROP_SPAM_PHRASES):
                continue
            # Must actually talk about an airdrop
            if "airdrop" not in text_lower:
                continue
        
        # --- LISTINGS: Only Binance, Bybit, OKX, Upbit ---
        if category_name == "listings":
            if not any(ex in text_lower for ex in MAJOR_EXCHANGES):
                continue
            # Must have listing context (not just mentioning the exchange)
            if not any(w in text_lower for w in ["listing", "listed", "will list", "list", "lists"]):
                continue
            # Prefer tweets from official exchange accounts
            author_lower = author_name.lower()
            is_official = any(ex_acc == author_lower for ex_acc in EXCHANGE_ACCOUNTS)
        
        # --- SALE/PRESALE: Quality filter using engagement metrics ---
        if category_name == "sale":
            if any(phrase in text_lower for phrase in AIRDROP_SPAM_PHRASES):
                continue
            # Must mention presale or related term
            if not any(w in text_lower for w in ["presale", "pre-sale", "token sale", "launchpad", "public sale"]):
                continue
            # Check engagement metrics as quality signal
            reply_count = t.get('replies', 0) or 0
            like_count = t.get('favorites', 0) or 0
            retweet_count = t.get('retweets', 0) or 0
            total_engagement = reply_count + like_count + retweet_count
            # Always allow notable projects through
            is_notable = any(proj in text_lower for proj in NOTABLE_PROJECTS)
            # Skip low-engagement tweets (likely spam) unless it's a notable project
            if not is_notable and total_engagement < 5:
                continue
        
        # --- TGE: Must have clear launch info ---
        if category_name == "TGE":
            tge_keywords = ["tge", "token generation", "token launch", "now trading",
                            "just launched", "trading live", "launched on", "live on",
                            "launch date", "launching"]
            if not any(w in text_lower for w in tge_keywords):
                continue
            # Should mention a project name or have a contract address
            has_ca = bool(re.search(r'0x[a-fA-F0-9]{40}', text))
            has_ticker = bool(re.search(r'\$[A-Za-z][A-Za-z0-9]{1,14}\b', text))
            has_exchange = any(ex in text_lower for ex in ["binance", "bybit", "okx", "upbit", "uniswap", "raydium", "pancakeswap", "dex", "cex"])
            # At least one concrete identifier
            if not (has_ca or has_ticker or has_exchange):
                continue
        
        results.append({
            'id': str(t_id),
            'text': text,
            'author': f"@{author_name}",
            'date': date,
            'matched_category': category_name,
            'url': f'https://twitter.com/{author_name}/status/{t_id}'
        })
    return results

def fetch_alpha_group(group_name, limit=5):
    """
    Fetches real-time cryptocurrency tweets from a specific Alpha Group by chunking queries.
    """
    if group_name not in ALPHA_GROUPS:
        return []
        
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    users = ALPHA_GROUPS[group_name]
    if not users:
        return []
        
    batch_size = 10
    all_results = []
    
    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        from_queries = " OR ".join([f"from:{u}" for u in batch])
        
        query_str = f"({from_queries}) -filter:retweets"
        query_str += " (crypto OR cryptocurrency OR token OR coin OR eth OR btc OR sol OR altcoin OR memecoin)"
        
        querystring = {"query": query_str, "search_type": "Latest"}
        
        data = _call_rapidapi(url, querystring)
        if not data or 'timeline' not in data:
            continue
            
        for t in data['timeline']:
            if t.get('type') != 'tweet':
                continue
                
            t_id = t.get('tweet_id', '')
            text = t.get('text', '')
            date = t.get('created_at', 'Unknown Date')
            author_name = t.get('screen_name', 'UnknownUser')
            
            display_name = t.get('user_info', {}).get('name', '').lower()
            if 'support' in display_name or 'helpdesk' in display_name or 'customer service' in display_name:
                continue
            
            if author_name.lower() in [u.lower() for u in BLOCKED_USERS]:
                continue
                
            text_lower = text.lower()
            if any(phrase in text_lower for phrase in SHILL_PHRASES):
                continue
                
            if len(re.findall(r'#\w+', text)) > 1:
                continue
                
            long_words = re.findall(r'\b[a-zA-Z0-9]{30,100}\b', text)
            if any(not w.lower().startswith('0x') for w in long_words):
                continue
            
            all_results.append({
                'id': str(t_id),
                'text': text,
                'author': f"@{author_name}",
                'date': date,
                'matched_group': group_name,
                'url': f'https://twitter.com/{author_name}/status/{t_id}'
            })
            
    return all_results[:limit]
