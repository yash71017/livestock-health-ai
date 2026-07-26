"""
app.py — Flask application entry point.

Usage:
    python app.py              # development server on :5000
    gunicorn app:app           # production
"""

import os
from dotenv import load_dotenv

# Load .env BEFORE any other imports that might need env vars
load_dotenv()

from flask import Flask
from flask_cors import CORS
from api.routes import api_bp, load_models
from database.neo4j_connector import close_driver


def create_app():
    app = Flask(__name__)

    # CORS: allow frontend origin (default localhost:3000 for dev)
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
    CORS(app, resources={r"/api/*": {"origins": [frontend_origin, "http://localhost:3000"]}})

    # Register routes
    app.register_blueprint(api_bp)

    # Load ML models
    load_models()

    # Health check
    @app.route("/api/health", methods=["GET"])
    def health():
        from database.neo4j_connector import get_driver
        import api.routes as routes

        try:
            get_driver().verify_connectivity()
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"

        return {
            "status": "ok",
            "database": db_status,
            "diseaseModel": "loaded" if routes.disease_artifact else "NOT LOADED - run train_all.py",
            "milkModel": "loaded" if routes.milk_artifact else "NOT LOADED - run train_all.py",
            "vocab": "loaded" if routes.vocab else "NOT LOADED - run clean_data.py",
        }

    # Cleanup on shutdown
    @app.teardown_appcontext
    def shutdown(exception=None):
        pass  # Driver cleanup handled by atexit

    import atexit
    atexit.register(close_driver)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    print(f"Starting server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
