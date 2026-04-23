import os
import logging

# bot_engine.py - Core Bot Logic (Unified Engine)
import asyncio
import re
import threading
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application, CallbackQueryHandler
from telegram.constants import ParseMode

import database as db
import twitter_tracker as tt
import reddit_tracker as rt


load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def setup_bot_application():
    """Build and configure the Telegram application."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Job queue to run every 300 seconds (5 mins) to prevent RapidAPI rate limits
    if app.job_queue:
        app.job_queue.run_repeating(check_global_category_updates, interval=300, first=5)
        app.job_queue.run_repeating(check_alpha_group_updates, interval=300, first=150)
        app.job_queue.run_repeating(check_reddit_alpha_updates, interval=1800, first=60)
        
    return app

def start_engine():
    """Traditional blocking start (for legacy use or debugging)."""
    logging.info("Starting bot in legacy blocking mode...")
    app = setup_bot_application()
    app.run_polling()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    chat_id = update.effective_chat.id
    db.add_chat(chat_id)
    
    # Pause tracking state until they click confirm
    db.set_preference_state(chat_id, 'system', 'is_tracking_active', False)
    
    menu_text = (
        "🦅 <b>Welcome to the Twitter/X Alpha Bot</b>\n\n"
        "Configure your tracking preferences below by toggling the buttons.\n"
        "Your bot will automatically filter and classify tweets for you."
    )
    
    await update.message.reply_text(text=menu_text, parse_mode=ParseMode.HTML, reply_markup=build_main_menu(chat_id))

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause alerts."""
    chat_id = update.effective_chat.id
    db.set_preference_state(chat_id, 'system', 'is_tracking_active', False)
    await update.message.reply_text("⏸️ Bot tracking suspended. You will not receive any alerts until you /resume or click Confirm & Apply in the menu.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume alerts."""
    chat_id = update.effective_chat.id
    db.set_preference_state(chat_id, 'system', 'is_tracking_active', True)
    await update.message.reply_text("▶️ Bot tracking resumed. You will now receive alerts based on your preferences.")

def build_main_menu(chat_id):
    prefs = db.get_user_preferences(chat_id)
    
    def is_active(p_type, val):
        for p in prefs:
            if p['type'] == p_type and p['value'] == val:
                return True
        return False
        
    def btn_label(p_type, val):
        icon = "✅" if is_active(p_type, val) else "⬜"
        return f"{icon} {val}"
        
    keyboard = []
    
    # Event Categories
    keyboard.append([InlineKeyboardButton("--- EVENT CATEGORIES ---", callback_data="none")])
    cat_row1 = [InlineKeyboardButton(btn_label("category", "All categories"), callback_data="tg_category_All categories"),
                InlineKeyboardButton(btn_label("category", "airdrop"), callback_data="tg_category_airdrop")]
    cat_row2 = [InlineKeyboardButton(btn_label("category", "economy"), callback_data="tg_category_economy"),
                InlineKeyboardButton(btn_label("category", "regulations"), callback_data="tg_category_regulations"),
                InlineKeyboardButton(btn_label("category", "listings"), callback_data="tg_category_listings")]
    cat_row3 = [InlineKeyboardButton(btn_label("category", "sale"), callback_data="tg_category_sale"),
                InlineKeyboardButton(btn_label("category", "hack"), callback_data="tg_category_hack"),
                InlineKeyboardButton(btn_label("category", "discussion"), callback_data="tg_category_discussion"),
                InlineKeyboardButton(btn_label("category", "TGE"), callback_data="tg_category_TGE")]
    cat_row4 = [InlineKeyboardButton(btn_label("category", "signals/moves"), callback_data="tg_category_signals/moves"),
                InlineKeyboardButton(btn_label("category", "AI AGENT"), callback_data="tg_category_AI AGENT")]
    
    keyboard.extend([cat_row1, cat_row2, cat_row3, cat_row4])
    
    # Alpha Groups
    keyboard.append([InlineKeyboardButton("--- ALPHA GROUPS ---", callback_data="none")])
    keyboard.append([InlineKeyboardButton(btn_label("group", "All groups"), callback_data="tg_group_All groups")])
    alpha_group_names = list(tt.ALPHA_GROUPS.keys())
    for i in range(0, len(alpha_group_names), 2):
        row = []
        for g in alpha_group_names[i:i+2]:
            row.append(InlineKeyboardButton(btn_label("group", g), callback_data=f"tg_group_{g}"))
        keyboard.append(row)

    # Reddit Alpha
    keyboard.append([InlineKeyboardButton("--- REDDIT ALPHA ---", callback_data="none")])
    keyboard.append([InlineKeyboardButton(btn_label("reddit", "Reddit Alpha"), callback_data="tg_reddit_Reddit Alpha")])

    # On-Chain Tracking
    keyboard.append([InlineKeyboardButton("--- ON-CHAIN TRACKING ---", callback_data="none")])
    keyboard.append([InlineKeyboardButton(btn_label("tracker", "DexScreener API"), callback_data="tg_tracker_DexScreener API")])

    # Confirm Command
    keyboard.append([
        InlineKeyboardButton("✅ Confirm & Apply", callback_data="confirm_req")
    ])
    return InlineKeyboardMarkup(keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    data = query.data
    
    if data.startswith("tg_"):
        _, p_type, val = data.split("_", 2)
        
        # When user clicks any toggle, the bot pauses until they hit Confirm
        db.set_preference_state(chat_id, 'system', 'is_tracking_active', False)
        
        if p_type == "category":
            if val == "All categories":
                prefs = db.get_user_preferences(chat_id, 'category')
                new_state = "All categories" not in prefs
                
                db.set_preference_state(chat_id, "category", "All categories", new_state)
                for cat in tt.EVENT_CATEGORIES:
                    db.set_preference_state(chat_id, "category", cat, new_state)
            else:
                db.set_preference_state(chat_id, "category", "All categories", False)
                db.toggle_preference(chat_id, p_type, val)
                
        elif p_type == "group":
            if val == "All groups":
                prefs = db.get_user_preferences(chat_id, 'group')
                new_state = "All groups" not in prefs
                
                db.set_preference_state(chat_id, "group", "All groups", new_state)
                for g in tt.ALPHA_GROUPS.keys():
                    db.set_preference_state(chat_id, "group", g, new_state)
            else:
                db.set_preference_state(chat_id, "group", "All groups", False)
                db.toggle_preference(chat_id, p_type, val)
                
        elif p_type == "reddit":
            db.toggle_preference(chat_id, p_type, val)
                
        elif p_type == "tracker":
            db.toggle_preference(chat_id, p_type, val)
                
        await query.message.edit_reply_markup(reply_markup=build_main_menu(chat_id))
    elif data == "none":
        pass
    elif data == "confirm_req":
        db.set_preference_state(chat_id, 'system', 'is_tracking_active', True)
        await query.message.reply_text("✅ Your preferences have been saved and applied! The bot is now tracking your selected keywords.")


async def check_global_category_updates(context: ContextTypes.DEFAULT_TYPE):
    """Background task to globally poll Twitter for the Event Categories."""
    if db.get_system_config('bot_active', '1') == '0':
        logging.info("Global tracking engine is paused. Skipping category update.")
        return
        
    logging.info("Checking for global event category tweets...")
    all_chats = db.get_all_chats()
    if not all_chats:
        return
        
    # Always track all categories for the web dashboard database
    active_categories = [c for c in tt.EVENT_CATEGORIES if c != "All categories"]
    
    user_prefs_map = {}
    for chat_id in all_chats:
        sys_prefs = db.get_user_preferences(chat_id, pref_type='system')
        # Skip preference mapping if user is inactive, but we still poll for the web
        if 'is_tracking_active' not in sys_prefs:
            continue
            
        cat_prefs = db.get_user_preferences(chat_id, pref_type='category')
        group_prefs = db.get_user_preferences(chat_id, pref_type='group')
        user_prefs_map[chat_id] = {'category': cat_prefs, 'group': group_prefs}
                    
    # Poll API for those specific categories globally
    for cat in active_categories:
        new_tweets = await asyncio.to_thread(tt.fetch_category_global, cat, limit=40)
        await asyncio.sleep(1.5) # Prevent rate limits
        
        for tweet in new_tweets:
            tweet_id = tweet['id']
            if not db.is_tweet_seen(tweet_id):
                db.mark_tweet_seen(tweet_id)
                if db.check_and_mark_spam(tweet['author'], tweet['text']):
                    logging.info(f"Spam filter blocked duplicate template tweet from {tweet['author']}")
                    continue
                
                alpha_users = {user.lower(): group for group, users in tt.ALPHA_GROUPS.items() for user in users}
                author_clean = tweet['author'].replace('@', '').lower()
                alpha_group = alpha_users.get(author_clean)
                priority_flag = False

                # Custom AI AGENT filtering and formatting
                if cat == "AI AGENT":
                    # Must contain a valid EVM contract address
                    if not re.search(r'0x[a-fA-F0-9]{40}', tweet['text']):
                        continue
                        
                    if tweet['author'].lower() in [a.lower() for a in tt.AGENT_ACCOUNTS]:
                        message = f"🚨 AI AGENT LAUNCH 🚨\nNew CA on Base from {tweet['author']} ({tweet.get('date', 'Unknown Date')}):\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                    elif alpha_group:
                        priority_flag = True
                        message = f"⚡🔥 ALPHA CROSSOVER ALERT 🔥⚡\n💎 CA DETECTED FROM [{alpha_group.upper()}] 💎\nAuthor: {tweet['author']}\nDate: {tweet.get('date', 'Unknown Date')}\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                    else:
                        message = f"🎯 EVENT CATEGORY [{cat.upper()}]:\nNew tweet from {tweet['author']} at {tweet.get('date', 'Unknown Date')}:\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                elif cat == "discussion":
                    if not re.search(r'\$[A-Za-z][A-Za-z0-9]{1,14}\b', tweet['text']):
                        continue
                    if alpha_group:
                        priority_flag = True
                        message = f"⚡🔥 ALPHA CROSSOVER ALERT 🔥⚡\n💎 [{alpha_group.upper()}] discussing [{cat.upper()}] 💎\nAuthor: {tweet['author']}\nDate: {tweet.get('date', 'Unknown Date')}\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                    else:
                        message = f"🎯 EVENT CATEGORY [{cat.upper()}]:\nNew tweet from {tweet['author']} at {tweet.get('date', 'Unknown Date')}:\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                else:
                    if alpha_group:
                        priority_flag = True
                        message = f"⚡🔥 ALPHA CROSSOVER ALERT 🔥⚡\n💎 [{alpha_group.upper()}] posted about [{cat.upper()}] 💎\nAuthor: {tweet['author']}\nDate: {tweet.get('date', 'Unknown Date')}\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                    else:
                        message = f"🎯 EVENT CATEGORY [{cat.upper()}]:\nNew tweet from {tweet['author']} at {tweet.get('date', 'Unknown Date')}:\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                
                # === Save to web dashboard feed ===
                db.save_feed_item(
                    source='twitter',
                    source_id=tweet_id,
                    category=cat,
                    group_name=alpha_group,
                    author=tweet['author'],
                    title=None,
                    body=tweet['text'],
                    url=tweet['url'],
                    priority='crossover' if priority_flag else 'normal',
                    extra={'date': tweet.get('date', '')}
                )

                for chat_id in all_chats:
                    prefs = user_prefs_map.get(chat_id, {'category': [], 'group': []})
                    cat_prefs = prefs.get('category', [])
                    group_prefs = prefs.get('group', [])
                    
                    is_cat_sub = "All categories" in cat_prefs or cat in cat_prefs
                    is_group_sub = alpha_group and ("All groups" in group_prefs or alpha_group in group_prefs)
                    
                    if is_cat_sub or (priority_flag and is_group_sub):
                        try:
                            await context.bot.send_message(chat_id=chat_id, text=message)
                        except Exception as e:
                            logging.error(f"Failed to send category alert to {chat_id}: {e}")

async def check_alpha_group_updates(context: ContextTypes.DEFAULT_TYPE):
    """Background task to poll Twitter for Alpha Group users."""
    if db.get_system_config('bot_active', '1') == '0':
        logging.info("Global tracking engine is paused. Skipping alpha group update.")
        return

    logging.info("Checking for alpha group tweets...")
    all_chats = db.get_all_chats()
    if not all_chats:
        return
        
    # Always track all alpha groups for the web dashboard database
    active_groups = [g for g in tt.ALPHA_GROUPS.keys() if g != "All groups"]
    
    user_prefs_map = {}
    for chat_id in all_chats:
        sys_prefs = db.get_user_preferences(chat_id, pref_type='system')
        # Skip preference mapping if user is inactive, but we still poll for the web
        if 'is_tracking_active' not in sys_prefs:
            continue
            
        cat_prefs = db.get_user_preferences(chat_id, pref_type='category')
        group_prefs = db.get_user_preferences(chat_id, pref_type='group')
        user_prefs_map[chat_id] = {'category': cat_prefs, 'group': group_prefs}
                    
    for g in active_groups:
        new_tweets = await asyncio.to_thread(tt.fetch_alpha_group, g, limit=10)
        await asyncio.sleep(1.5)
        
        for tweet in new_tweets:
            tweet_id = tweet['id']
            if not db.is_tweet_seen(tweet_id):
                db.mark_tweet_seen(tweet_id)
                if db.check_and_mark_spam(tweet['author'], tweet['text']):
                    logging.info(f"Spam filter blocked duplicate template tweet from {tweet['author']}")
                    continue
                    
                matched_cats = []
                text_lower = tweet['text'].lower()
                for c, words in tt.TOPIC_CLUSTERS.items():
                    for w in words:
                        clean_w = w.replace('"', '').lower()
                        if clean_w in text_lower:
                            if c == "AI AGENT" and not re.search(r'0x[a-fA-F0-9]{40}', text_lower):
                                continue
                            if c == "discussion" and not re.search(r'\$[A-Za-z][A-Za-z0-9]{1,14}\b', tweet['text']):
                                continue
                            matched_cats.append(c)
                            break
                            
                is_crossover = bool(matched_cats)
                if matched_cats:
                    cat_str = ", ".join([c.upper() for c in matched_cats])
                    message = f"⚡🔥 ALPHA CROSSOVER ALERT 🔥⚡\n💎 [{g.upper()}] posted about [{cat_str}] 💎\nAuthor: {tweet['author']}\nDate: {tweet.get('date', 'Unknown Date')}\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                else:
                    message = f"🦅 ALPHA GROUP [{g.upper()}]:\nNew tweet from {tweet['author']} at {tweet.get('date', 'Unknown Date')}:\n\n{tweet['text']}\n\nLink: {tweet['url']}"
                
                # === Save to web dashboard feed ===
                db.save_feed_item(
                    source='twitter',
                    source_id=tweet_id,
                    category=matched_cats[0] if matched_cats else None,
                    group_name=g,
                    author=tweet['author'],
                    title=None,
                    body=tweet['text'],
                    url=tweet['url'],
                    priority='crossover' if is_crossover else 'normal',
                    extra={'date': tweet.get('date', '')}
                )

                for chat_id in all_chats:
                    prefs = user_prefs_map.get(chat_id, {'category': [], 'group': []})
                    cat_prefs = prefs.get('category', [])
                    group_prefs = prefs.get('group', [])
                    
                    is_group_sub = "All groups" in group_prefs or g in group_prefs
                    is_cat_sub = bool(matched_cats) and any(c in cat_prefs for c in matched_cats)
                    if bool(matched_cats) and "All categories" in cat_prefs:
                        is_cat_sub = True
                        
                    if is_group_sub or is_cat_sub:
                        try:
                            await context.bot.send_message(chat_id=chat_id, text=message)
                        except Exception as e:
                            logging.error(f"Failed to send alpha group alert to {chat_id}: {e}")


async def check_reddit_alpha_updates(context: ContextTypes.DEFAULT_TYPE):
    """Background task to poll Reddit for crypto alpha posts."""
    if db.get_system_config('bot_active', '1') == '0':
        logging.info("Global tracking engine is paused. Skipping reddit update.")
        return

    logging.info("Checking for Reddit alpha posts...")
    all_chats = db.get_all_chats()
    if not all_chats:
        return

    # Check which users have Reddit Alpha enabled
    active_chats = []
    for chat_id in all_chats:
        sys_prefs = db.get_user_preferences(chat_id, pref_type='system')
        if 'is_tracking_active' not in sys_prefs:
            continue
        reddit_prefs = db.get_user_preferences(chat_id, pref_type='reddit')
        if 'Reddit Alpha' in reddit_prefs:
            active_chats.append(chat_id)

    # Fetch hot quality posts from crypto subreddits — ALWAYS poll for the web dashboard
    combined = await asyncio.to_thread(rt.fetch_reddit_alpha, limit_per_sub=10)

    for post in combined[:8]:  # Cap at 8 posts per cycle to avoid spam
        post_id = post['id']
        if db.is_reddit_post_seen(post_id):
            continue
        db.mark_tweet_seen(post_id) # Using same table for dedup consistency if needed, wait...
        # actually db.mark_reddit_post_seen is used in the original
        db.mark_reddit_post_seen(post_id)

        # Build topic tags
        topic_tags = " ".join([f"#{t.upper()}" for t in post['topics']])

        # Build the alert message
        flair_str = f" [{post['flair']}]" if post['flair'] else ""
        score_str = f"⬆️ {post['score']}" if post['score'] > 0 else f"⬇️ {post['score']}"

        message = (
            f"📡 REDDIT ALPHA{flair_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 {post['title']}\n\n"
        )

        if post['body']:
            message += f"{post['body']}\n\n"

        message += (
            f"👤 {post['author']} in {post['subreddit']}\n"
            f"{score_str} | 💬 {post['comments']} comments | ⏰ {post['time_ago']}\n"
            f"🏷️ {topic_tags}\n"
            f"🔗 {post['url']}"
        )

        # === Save to web dashboard feed ===
        db.save_feed_item(
            source='reddit',
            source_id=post_id,
            category=post['topics'][0] if post['topics'] else None,
            group_name=None,
            author=post['author'],
            title=post['title'],
            body=post.get('body', ''),
            url=post['url'],
            priority='normal',
            extra={'score': post['score'], 'comments': post['comments'],
                   'subreddit': post['subreddit'], 'flair': post['flair'],
                   'topics': post['topics']}
        )

        for chat_id in active_chats:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message)
                await asyncio.sleep(0.5)  # Prevent Telegram flood control
            except Exception as e:
                logging.error(f"Failed to send Reddit alert to {chat_id}: {e}")
                            

async def post_init(application: Application):
    """Set the initial bot commands to display in the Telegram menu button."""
    commands = [
        ("start", "Launch tracking dashboard"),
        ("stop", "Pause all alerts"),
        ("resume", "Resume tracking alerts")
    ]
    await application.bot.set_my_commands(commands)



