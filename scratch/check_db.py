import sqlite3
import json

DB_PATH = 'bot_database.db'

def check_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, source, author, created_at FROM feed_items ORDER BY id DESC LIMIT 5")
    recent = cursor.fetchall()
    
    for row in recent:
        print(f"ID: {row[0]}, Source: {row[1]}, Author: {row[2]}, Created At: {row[3]}")
    
    cursor.execute("SELECT source, COUNT(*) FROM feed_items GROUP BY source")
    counts = cursor.fetchall()
    print("\nSource Counts:")
    for row in counts:
        print(f"{row[0]}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
