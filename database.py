import sqlite3
import os

DB_PATH = os.getenv('DB_PATH', 'bot_database.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table to store which Telegram chats are active
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY
        )
    ''')
    
    # Table to store tracked targets (usernames or keywords) for each chat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            target TEXT,
            target_type TEXT, -- 'user' or 'keyword'
            FOREIGN KEY(chat_id) REFERENCES chats(chat_id),
            UNIQUE(chat_id, target)
        )
    ''')
    
    # Table to store tweet IDs that have already been sent to avoid duplicates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_tweets (
            tweet_id TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table to store DexScreener tokens that have already been alerted
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_dex_tokens (
            token_address TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table to store Reddit post IDs that have already been sent
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_reddit_posts (
            post_id TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table to store user preferences for categories and tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            chat_id INTEGER,
            preference_type TEXT, -- 'category' or 'tag'
            value TEXT,
            PRIMARY KEY (chat_id, preference_type, value)
        )
    ''')
    
    # Table to store text signatures for spam prevention
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spam_filter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT,
            clean_text TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(author, clean_text)
        )
    ''')

    # Table to store full feed items for the web dashboard
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feed_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT UNIQUE,
            category TEXT,
            group_name TEXT,
            author TEXT,
            title TEXT,
            body TEXT,
            url TEXT,
            priority TEXT DEFAULT 'normal',
            extra_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table for tracking user following lists for change detection
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_followings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alpha_handle TEXT NOT NULL,
            followed_handle TEXT NOT NULL,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(alpha_handle, followed_handle)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_source ON feed_items(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_category ON feed_items(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_created ON feed_items(created_at DESC)')

    # Table for global system settings (e.g., bot_active)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Default bot_active to '1' (True) if not set
    cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('bot_active', '1')")

    conn.commit()
    conn.close()

def add_chat(chat_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('INSERT OR IGNORE INTO chats (chat_id) VALUES (?)', (chat_id,))
        conn.commit()
    finally:
        conn.close()

def add_mark(chat_id, target, target_type):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('INSERT OR IGNORE INTO marks (chat_id, target, target_type) VALUES (?, ?, ?)', (chat_id, target, target_type))
        conn.commit()
    finally:
        conn.close()

def remove_mark(chat_id, target):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('DELETE FROM marks WHERE chat_id = ? AND target = ?', (chat_id, target))
        conn.commit()
    finally:
        conn.close()

def get_marks(chat_id=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if chat_id:
        cursor.execute('SELECT * FROM marks WHERE chat_id = ?', (chat_id,))
    else:
        cursor.execute('SELECT * FROM marks')
    marks = cursor.fetchall()
    conn.close()
    return marks

def is_tweet_seen(tweet_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM seen_tweets WHERE tweet_id = ?', (tweet_id,))
    seen = cursor.fetchone() is not None
    conn.close()
    return seen

def mark_tweet_seen(tweet_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('INSERT OR IGNORE INTO seen_tweets (tweet_id) VALUES (?)', (tweet_id,))
        conn.commit()
    finally:
        conn.close()

def is_dex_token_seen(token_address):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM seen_dex_tokens WHERE token_address = ?', (token_address.lower(),))
    seen = cursor.fetchone() is not None
    conn.close()
    return seen

def mark_dex_token_seen(token_address):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('INSERT OR IGNORE INTO seen_dex_tokens (token_address) VALUES (?)', (token_address.lower(),))
        conn.commit()
    finally:
        conn.close()

def is_reddit_post_seen(post_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM seen_reddit_posts WHERE post_id = ?', (post_id,))
    seen = cursor.fetchone() is not None
    conn.close()
    return seen

def mark_reddit_post_seen(post_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('INSERT OR IGNORE INTO seen_reddit_posts (post_id) VALUES (?)', (post_id,))
        conn.commit()
    finally:
        conn.close()

def get_all_chats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM chats')
    chats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chats

def toggle_preference(chat_id, pref_type, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM user_preferences WHERE chat_id = ? AND preference_type = ? AND value = ?', (chat_id, pref_type, value))
    exists = cursor.fetchone() is not None
    
    if exists:
        cursor.execute('DELETE FROM user_preferences WHERE chat_id = ? AND preference_type = ? AND value = ?', (chat_id, pref_type, value))
        toggled_on = False
    else:
        cursor.execute('INSERT INTO user_preferences (chat_id, preference_type, value) VALUES (?, ?, ?)', (chat_id, pref_type, value))
        toggled_on = True
        
    conn.commit()
    conn.close()
    return toggled_on

def set_preference_state(chat_id, pref_type, value, state: bool):
    """Explicitly SET a preference to True or False without toggling blindly."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if state:
        cursor.execute('INSERT OR IGNORE INTO user_preferences (chat_id, preference_type, value) VALUES (?, ?, ?)', (chat_id, pref_type, value))
    else:
        cursor.execute('DELETE FROM user_preferences WHERE chat_id = ? AND preference_type = ? AND value = ?', (chat_id, pref_type, value))
    conn.commit()
    conn.close()

def clear_other_preferences(chat_id, pref_type, keep_value):
    """Deletes all preferences of a specific type except the keep_value, drastically speeding up bulk toggles."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_preferences WHERE chat_id = ? AND preference_type = ? AND value != ?', (chat_id, pref_type, keep_value))
    conn.commit()
    conn.close()

def get_user_preferences(chat_id, pref_type=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if pref_type:
        cursor.execute('SELECT value FROM user_preferences WHERE chat_id = ? AND preference_type = ?', (chat_id, pref_type))
    else:
        cursor.execute('SELECT preference_type, value FROM user_preferences WHERE chat_id = ?', (chat_id,))
    prefs = cursor.fetchall()
    conn.close()
    if pref_type:
        return [row[0] for row in prefs]
    else:
        return [{'type': row[0], 'value': row[1]} for row in prefs]

# Initialize DB on load
init_db()

import json

def save_feed_item(source, source_id, category=None, group_name=None, author='', title='', body='', url='', priority='normal', extra=None):
    """Save a full feed item for the web dashboard."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('''
            INSERT OR IGNORE INTO feed_items 
            (source, source_id, category, group_name, author, title, body, url, priority, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (source, source_id, category, group_name, author, title, body, url, priority,
              json.dumps(extra) if extra else None))
        conn.commit()
    finally:
        conn.close()

def get_feed_items(source=None, category=None, group_name=None, limit=50, offset=0, since_id=None):
    """Query feed items with optional filters for the web API."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM feed_items WHERE 1=1'
    params = []
    
    if source:
        query += ' AND source = ?'
        params.append(source)
    if category:
        query += ' AND category = ?'
        params.append(category)
    if group_name:
        query += ' AND group_name = ?'
        params.append(group_name)
    if since_id:
        query += ' AND id > ?'
        params.append(since_id)
    
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def get_feed_stats():
    """Get aggregated stats for the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM feed_items")
    stats['total'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM feed_items WHERE created_at >= datetime('now', '-24 hours')")
    stats['today'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT source, COUNT(*) as cnt FROM feed_items GROUP BY source")
    stats['by_source'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute("""
        SELECT category, COUNT(*) as cnt FROM feed_items 
        WHERE category IS NOT NULL 
        GROUP BY category ORDER BY cnt DESC
    """)
    stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute("""
        SELECT group_name, COUNT(*) as cnt FROM feed_items 
        WHERE group_name IS NOT NULL 
        GROUP BY group_name ORDER BY cnt DESC
    """)
    stats['by_group'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute("SELECT COUNT(*) FROM feed_items WHERE priority = 'crossover'")
    stats['crossovers'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

import re
def clean_for_spam(text):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9]', '', text)
    return text.lower()

def check_and_mark_spam(author, text):
    clean_text = clean_for_spam(text)
    # Require slightly longer string to avoid blocking universal short crypto phrases globally
    if not clean_text or len(clean_text) < 20:  
        return False
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Check if ANY author has recently posted this exact clean phrase
    cursor.execute('SELECT 1 FROM spam_filter WHERE clean_text = ?', (clean_text,))
    exists = cursor.fetchone() is not None
    
    if not exists:
        try:
            cursor.execute('INSERT INTO spam_filter (author, clean_text) VALUES (?, ?)', (author, clean_text))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    conn.close()
    return exists

def get_system_config(key, default=None):
    """Retrieve a global system setting."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM system_config WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_system_config(key, value):
    """Set a global system setting."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)', (key, str(value)))
        conn.commit()
    finally:
        conn.close()

# === FOLLOW TRACKING FUNCTIONS ===

def get_user_following(alpha_handle):
    """Returns a set of handles that this alpha account is already known to follow."""
    with get_db() as conn:
        cursor = conn.execute('SELECT followed_handle FROM user_followings WHERE alpha_handle = ?', (alpha_handle,))
        return {row[0] for row in cursor.fetchall()}

def add_user_following(alpha_handle, followed_handle):
    """Records that an alpha account follows a specific handle."""
    with get_db() as conn:
        try:
            conn.execute('INSERT INTO user_followings (alpha_handle, followed_handle) VALUES (?, ?)', 
                         (alpha_handle, followed_handle))
            conn.commit()
        except Exception:
            pass # Already exists or other error


