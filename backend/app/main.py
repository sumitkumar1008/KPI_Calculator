"""
Application Entrypoint
======================
This module initializes and runs the Flask KPI Processing Server.
It binds to host 0.0.0.0 on port 5000 so the API can be accessed locally
or across the network.
"""

import os
import sys

# Add the backend root directory to Python's module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app

# Instantiate the Flask application using the Application Factory pattern
app = create_app()

if __name__ == "__main__":
    # Start the Flask development server on host 0.0.0.0, port 5000 with debug mode enabled
    app.run(host="0.0.0.0", port=5000, debug=True)
