import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    # Start the unified engine (FastAPI + Telegram Bot) with Hot Reload enabled.
    # This will automatically restart the bot and website whenever any file is saved.
    # Render provides 'PORT', local uses 'WEB_PORT'
    WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", 8000)))
    
    print("Starting Unified Alpha Engine...")
    print(f"Dashboard available at port {WEB_PORT}")
    
    uvicorn.run(
        "web_server:app", 
        host="0.0.0.0", 
        port=WEB_PORT, 
        reload=False,
        log_level="info"
    )
