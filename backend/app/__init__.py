"""
Flask Application Factory
==========================
Creates and configures the Flask application instance.
Registers API blueprints, root landing routes, health checks,
and custom error handlers for file size limits (HTTP 413).
"""

from flask import Flask

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
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register the main KPI calculation API blueprint under /api/v1 prefix
    app.register_blueprint(api_bp)

    @app.route("/")
    def root():
        """Root landing endpoint returning API project details and current version."""
        return {
            "message": f"Welcome to {app.config['PROJECT_NAME']}",
            "version": app.config["VERSION"],
        }

    @app.route("/health")
    def health():
        """Health check endpoint for monitoring uptime and service status."""
        return {"status": "healthy"}

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """
        Global error handler for HTTP 413 Payload Too Large.
        Triggered automatically when an uploaded Excel file exceeds MAX_CONTENT_LENGTH (50MB).
        """
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
        return {
            "error": f"Uploaded file is too large. Maximum allowed size is {max_mb} MB."
        }, 413

    return app
