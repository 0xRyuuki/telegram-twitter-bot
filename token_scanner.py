import requests
import logging
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_goplus_chain_id(chain_name):
    """Maps DexScreener chain names to GoPlus API chain IDs."""
    mapping = {
        'base': '8453',
        'ethereum': '1',
        'bsc': '56',
        'arbitrum': '42161',
        'optimism': '10',
        'polygon': '137',
        # Monad is emerging, often ID is not fully mapped in GoPlus free tier yet
        'monad': None 
    }
    return mapping.get(chain_name.lower())

def fetch_latest_token_profiles():
    """Fetches the latest token profiles that were newly added or updated on DexScreener."""
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        logging.error(f"DexScreener latest profiles fetch failed: {e}")
        return []

def fetch_token_pairs(token_address):
    """Fetches pair data for a token to determine 1h volume, liquidity, etc."""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data.get('pairs', [])
    except Exception as e:
        logging.error(f"DexScreener pairs fetch failed for {token_address}: {e}")
        return []

def fetch_goplus_security(chain_name, token_address):
    """Fetches token security info from GoPlus (checks for honeypot)."""
    chain_id = get_goplus_chain_id(chain_name)
    if not chain_id:
        return {"honeypot": "Unknown (Chain not supported)"}
        
    url = f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={token_address}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('code') == 1 and data.get('result'):
            key = str(token_address).lower()
            security_info = data['result'].get(key)
            if security_info:
                is_honeypot = security_info.get('is_honeypot', '0')
                return {
                    "honeypot": "Yes" if is_honeypot == '1' else "No",
                    "details": security_info
                }
    except Exception as e:
        logging.error(f"GoPlus fetch failed for {token_address}: {e}")
    
    return {"honeypot": "Unknown (Error)"}

def extract_socials(profile):
    """Extracts twitter link from a token profile."""
    links = profile.get('links', [])
    socials = {}
    if links and isinstance(links, list):
        for link in links:
            t = link.get('type', '').lower()
            if t in ['twitter', 'telegram', 'website']:
                socials[t] = link.get('url')
    return socials

def scan_new_tokens():
    """Scans for new tokens on specified chains and prints their details."""
    target_chains = ['base', 'monad']
    logging.info(f"Scanning DexScreener for new profiles on chains: {', '.join(target_chains)}")
    
    profiles = fetch_latest_token_profiles()
    if not profiles:
        logging.warning("No profiles found or API error.")
        return

    # Filter for target chains
    filtered_profiles = [p for p in profiles if p.get('chainId', '').lower() in target_chains]
    
    if not filtered_profiles:
        logging.info("No new tokens found on target chains in the latest batch.")
        return
        
    logging.info(f"Found {len(filtered_profiles)} new token profiles on target chains.")
    
    for profile in filtered_profiles:
        chain = profile.get('chainId')
        address = profile.get('tokenAddress')
        description = profile.get('description', '')
        socials = extract_socials(profile)
        twitter_link = socials.get('twitter', 'No Twitter Link')
        
        logging.info(f"--- Analyzing Token: {address} on {chain.upper()} ---")
        logging.info(f"Twitter: {twitter_link}")
        
        # Fetch pairs to get liquidity, volume, and market cap
        pairs = fetch_token_pairs(address)
        if not pairs:
            logging.info("No trading pairs found or zero liquidity.")
            continue
            
        # Get the main pair (usually the one with highest liquidity or simply the first one returned)
        # We can sort by liquidity to be safe
        valid_pairs = [p for p in pairs if p.get('liquidity', {}).get('usd', 0) > 0]
        if not valid_pairs:
            valid_pairs = pairs # fallback to what we have
        main_pair = sorted(valid_pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0), reverse=True)[0]
        
        liquidity = main_pair.get('liquidity', {}).get('usd', 0)
        volume_1h = main_pair.get('volume', {}).get('h1', 0)
        market_cap = main_pair.get('marketCap', 0)
        if market_cap == 0:
            market_cap = main_pair.get('fdv', 0) # Fallback to FDV
            
        logging.info(f"Liquidity (USD): ${liquidity:,.2f}")
        logging.info(f"1H Volume (USD): ${volume_1h:,.2f}")
        logging.info(f"Market Cap (USD): ${market_cap:,.2f}")
        
        if volume_1h > 0:
            logging.info(">> This token has active 1H volume.")
            
        # Check Honeypot via GoPlus
        security = fetch_goplus_security(chain, address)
        logging.info(f"Honeypot Status: {security['honeypot']}")
        print() # empty line for readability
        time.sleep(1) # Add a slight delay to avoid rate limiting on API calls

if __name__ == "__main__":
    scan_new_tokens()
