"""
app.py — Flask application entry point.

Two modes:
  1. Dev (default): serves the API only on :5000. Run the React dev server
     separately on :3000.
  2. Demo/prod: if frontend/build exists, ALSO serves the built React app,
     so the whole thing runs from ONE server on ONE port (needed for tunnels
     like cloudflared / ngrok, and for real deployment).

Usage:
    python app.py              # development server on :5000
    gunicorn app:app           # production
"""

import os
import re
from dotenv import load_dotenv

# Load .env BEFORE any other imports that might need env vars
load_dotenv()

from flask import Flask, send_from_directory, abort
from flask_cors import CORS
from api.routes import api_bp, load_models
from database.neo4j_connector import close_driver

# Where the built React app lives (created by `npm run build`)
BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")


def create_app():
    # static_folder=None: we handle all static serving ourselves in the
    # catch-all below, so it doesn't fight the API routes.
    app = Flask(__name__, static_folder=None)

    # ── CORS ──
    # Allow requests from:
    #   - any *.vercel.app domain (production + preview deployments, which get
    #     a new URL per branch, so an exact match would break constantly)
    #   - localhost during development
    #   - whatever FRONTEND_ORIGIN is set to (optional override / custom domain)
    #
    # Using a regex avoids the classic failure where a trailing slash or a new
    # preview URL silently blocks every API call.
    allowed_origins = [
        re.compile(r"^https://.*\.vercel\.app$"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    extra_origin = os.environ.get("FRONTEND_ORIGIN")
    if extra_origin:
        allowed_origins.append(extra_origin.rstrip("/"))

    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # Register API routes (all under /api)
    app.register_blueprint(api_bp)

    # Load ML models
    load_models()

    # ── Health check ──
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

    # ── Serve the built React app (demo/prod only) ──
    # If frontend/build exists, serve index.html at "/" and let client-side
    # routing handle the rest. Any real file (JS/CSS/images) is served directly.
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        # Never let the catch-all swallow API calls
        if path.startswith("api/"):
            abort(404)

        index_path = os.path.join(BUILD_DIR, "index.html")
        if not os.path.exists(index_path):
            # Dev mode: no build present. Nudge instead of a blank 404.
            return (
                "<h2>Backend is running.</h2>"
                "<p>API is at <a href='/api/health'>/api/health</a>.</p>"
                "<p>The React app isn't built yet. In dev, open "
                "<a href='http://localhost:3000'>http://localhost:3000</a>. "
                "For a single-server demo, run <code>npm run build</code> in the "
                "frontend folder, then restart this server.</p>"
            ), 200

        # Serve the requested static file if it exists, else index.html
        # (so React Router routes like /diagnosis work on refresh).
        requested = os.path.join(BUILD_DIR, path)
        if path and os.path.exists(requested) and os.path.isfile(requested):
            return send_from_directory(BUILD_DIR, path)
        return send_from_directory(BUILD_DIR, "index.html")

    import atexit
    atexit.register(close_driver)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    serving_frontend = os.path.exists(os.path.join(BUILD_DIR, "index.html"))
    print(f"Starting server on http://localhost:{port}")
    if serving_frontend:
        print("Serving built React app from frontend/build (single-server mode)")
    app.run(host="0.0.0.0", port=port, debug=debug)