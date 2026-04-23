import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server import app

# This allows Vercel to pick up the FastAPI app
handler = app
