"""
FastAPI Web Server for Crypto Alpha Dashboard.
Serves the web dashboard and REST API for feed items.
"""
import os
import uvicorn
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
from contextlib import asynccontextmanager

import database as db
import twitter_tracker as tt
import bot_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the FastAPI app and the Telegram bot."""
    # 1. Setup and start the bot
    bot_app = bot_engine.setup_bot_application()
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    
    print("Bot tracking engine unified with web loop.")
    
    yield
    
    # 2. Cleanup and stop the bot
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    print("Bot tracking engine shut down.")


app = FastAPI(title="Crypto Alpha Dashboard", lifespan=lifespan)

# Serve static files (CSS, JS)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def dashboard():
    """Serve the main dashboard page."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/feed")
async def get_feed(
    source: Optional[str] = Query(None, description="Filter: twitter, reddit, dex"),
    category: Optional[str] = Query(None, description="Filter by category"),
    group_name: Optional[str] = Query(None, description="Filter by alpha group"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    since_id: Optional[int] = Query(None, description="Only items newer than this ID"),
):
    """Get feed items with optional filters."""
    items = db.get_feed_items(
        source=source,
        category=category,
        group_name=group_name,
        limit=limit,
        offset=offset,
        since_id=since_id,
    )
    return JSONResponse(content={"items": items, "count": len(items)})


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    stats = db.get_feed_stats()
    return JSONResponse(content=stats)


@app.get("/api/filters")
async def get_filters():
    """Get available filter options for the sidebar."""
    categories = list(tt.EVENT_CATEGORIES)
    groups = list(tt.ALPHA_GROUPS.keys())
    return JSONResponse(content={
        "categories": categories,
        "groups": groups,
        "sources": ["twitter", "reddit", "dex"],
    })
    

@app.get("/api/bot/status")
async def get_bot_status():
    """Get the current status of the bot engine."""
    is_active = db.get_system_config('bot_active', '1') == '1'
    return JSONResponse(content={
        "status": "online" if is_active else "paused",
        "is_active": is_active
    })


@app.post("/api/bot/toggle")
async def toggle_bot_status():
    """Toggle the bot engine on/off."""
    current = db.get_system_config('bot_active', '1') == '1'
    new_state = not current
    db.set_system_config('bot_active', '1' if new_state else '0')
    return JSONResponse(content={
        "status": "online" if new_state else "paused",
        "is_active": new_state
    })


def run_server(host="0.0.0.0", port=8000):
    """Run the web server (blocking)."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
