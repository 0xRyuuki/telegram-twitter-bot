# DexScreener Alpha Tracking Agent Plan

This document outlines the approach for creating a Telegram bot agent that tracks new tokens, significant buyers, liquidity locks, and insider supply on the Base and Monad chains.

## User Review Required

> [!WARNING]  
> **API Limitations & Solutions:** 
> 1. **Significant Buyers:** DexScreener's free API does not provide a live feed of individual wallet transactions (you can't query "who bought how much"). **Proposed Solution:** The agent will track newly profiled tokens and alert you based on significant 5m or 1h **transaction volume** and **price momentum** instead.
> 2. **Liquidity Locks & Insider Supply:** DexScreener API does not provide liquidity lock status or team holding metrics. **Proposed Solution:** We will integrate **GoPlus Security API** (a free Web3 security API) to fetch the token's Creator Address, Creator Holding Percentage (Insider Supply), and Honeypot/Lock status.
> 3. **Monad Support:** Base chain is heavily supported by security APIs. Monad might have limited data available on GoPlus natively depending on its current mainnet status, but the DexScreener portion will still work.

Are you comfortable using GoPlus Security for the security checks and focusing on high-volume momentum instead of specific wallet-level buy tracking?

## Proposed Changes

---

### New Module: `dex_agent.py`

#### [NEW] `dex_agent.py`
We will create a dedicated module to handle the external API fetching and logic for this agent.
It will include functions for:
- Polling `https://api.dexscreener.com/token-profiles/latest/v1` (to find new tokens / twitter links).
- Filtering for `chainId == 'base'` and `chainId == 'monad'`.
- Querying `https://api.dexscreener.com/latest/dex/tokens/{address}` to get the liquidity, 1h volume, and price changes.
- Querying GoPlus Labs Token Security API (`https://api.gopluslabs.io/api/v1/token_security/8453?contract_addresses={address}`) to extract:
  - `creator_address`
  - `creator_percent` (Team/Insider supply)
  - `is_honeypot` / Lock warnings

### Bot integration updates

#### [MODIFY] `main.py`
- Add a new background task (`check_new_dex_tokens`) using the `JobQueue` to run every 2-5 minutes.
- Integrate a new Telegram message format:
  ```
  🚀 **NEW ALPHA DETECTED: $TICKER (Base)**
  🔗 Twitter: @TokenTwitter
  
  🔥 **Momentum**: 1h Vol: $50k / 1h PnL: +150%
  💧 **Liquidity**: $25k
  
  🕵️ **Security & Insiders (GoPlus)**:
  - Creator: 0x12..34
  - Creator holds: 5% of supply
  - Status: Liquidity Locked ✅ / No Honeypot ✅
  ```
- Add toggle buttons in `build_main_menu` for the user to turn the "DexScreener Agent" ON or OFF.

#### [MODIFY] `database.py`
- Add tracking functions so the bot remembers which token contracts it has already alerted on (to prevent spamming the same token multiple times).

## Open Questions

> [!IMPORTANT]
> 1. For "significant buyers", would you prefer alerts to trigger only if 1-hour volume passes a specific threshold (e.g., >$50,000 Volume)? 
> 2. Do you want the bot to filter out tokens that show as "Honeypots" by GoPlus entirely, or just alert you with a warning?
> 3. Are you okay with using GoPlus Labs free API for the insider supply / lock checking?

## Verification Plan

### Automated Tests
- Create a test script `test_dex.py` to fetch a known Base token address through our new `dex_agent.py` functions to verify GoPlus and DexScreener parsing works correctly.

### Manual Verification
- Start the telegram bot locally.
- Enable the "DexScreener Agent" toggle in the menu.
- Wait for a new token alert to arrive in the Telegram chat and verify the format, Twitter links, and insider supply math.
