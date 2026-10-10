"""Development entry point.

Usage:
    python run.py

Environment variables are read from a local ``.env`` file when present.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # must run before the app imports its configuration module

from app import create_app  # noqa: E402

app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))
