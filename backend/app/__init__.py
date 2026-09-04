import os
from flask import Flask, jsonify, send_from_directory

from app.api.routes import api_bp
from app.core.config import Config


def create_app(config_class: type[Config] = Config) -> Flask:
    """
    Application Factory function.
    
    Args:
        config_class: Configuration class object to load application settings from.
        
    Returns:
        Configured Flask application instance.
    """
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
    app = Flask(__name__, static_folder=frontend_dist, static_url_path="")
    app.config.from_object(config_class)

    # Register the main KPI calculation API blueprint under /api/v1 prefix
    app.register_blueprint(api_bp)

    # Enable CORS for production deployments (e.g. Render)
    try:
        from flask_cors import CORS
        CORS(app)
    except ImportError:
        pass

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str):
        """Serves built React static assets from frontend/dist if present, else fallback to index.html or API welcome message."""
        # Never return HTML for API requests
        if path.startswith("api/") or path == "api":
            return jsonify({"error": f"API endpoint '/{path}' not found"}), 404

        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        index_file = os.path.join(app.static_folder, "index.html")
        if os.path.exists(index_file) and not app.config.get("TESTING"):
            return send_from_directory(app.static_folder, "index.html")
        return jsonify({
            "message": f"Welcome to {app.config['PROJECT_NAME']}",
            "version": app.config["VERSION"],
        })

    @app.route("/health")
    def health():
        """Health check endpoint for monitoring uptime and service status."""
        return jsonify({"status": "healthy"})

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """
        Global error handler for HTTP 413 Payload Too Large.
        Triggered automatically when an uploaded Excel file exceeds MAX_CONTENT_LENGTH (50MB).
        """
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
        return jsonify({
            "error": f"Uploaded file is too large. Maximum allowed size is {max_mb} MB."
        }), 413

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def handle_global_exception(error):
        """Global fallback error handler ensuring 500 server errors always return JSON instead of HTML."""
        err_msg = str(error) if error else "Internal server error"
        return jsonify({"error": f"Server Error: {err_msg}"}), 500

    return app
