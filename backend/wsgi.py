"""WSGI entry point for production servers (gunicorn/waitress).

Example (Linux):
    gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app

Example (Windows):
    waitress-serve --port=8000 wsgi:app
"""
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app("production")
