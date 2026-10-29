"""
Application Entrypoint
======================
This module initializes and runs the Flask KPI Processing Server.
It binds to host 0.0.0.0 on port 5000 so the API can be accessed locally
or across the network.
"""

import os
import sys

# Ensure UTF-8 console output on Windows to avoid UnicodeEncodeError in logging
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add the backend root directory to Python's module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app

# Instantiate the Flask application using the Application Factory pattern
app = create_app()

if __name__ == "__main__":
    # Start the Flask server with dynamic PORT (Render/Heroku/Cloud) and configurable debug mode
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true")
    app.run(host="0.0.0.0", port=port, debug=debug)
