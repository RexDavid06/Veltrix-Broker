"""VELTRIX demonstration platform — application factory."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from flask import Flask, jsonify, request
from flask_wtf.csrf import CSRFError

from config import get_config

from .extensions import csrf, db, login_manager


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config(config_name))

    _register_extensions(app)
    _register_blueprints(app)
    _register_cli(app)
    _register_error_handlers(app)
    _register_template_helpers(app)
    _register_headers_and_cors(app)

    with app.app_context():
        # Importing models registers them with SQLAlchemy metadata.
        from . import models  # noqa: F401

        db.create_all()

    if app.config.get("SECRET_KEY_IS_DEFAULT"):
        app.logger.warning(
            "SECRET_KEY is using an insecure development default. "
            "Set the SECRET_KEY environment variable before deploying."
        )
    return app


def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        if user_id is None or not str(user_id).isdigit():
            return None
        return db.session.get(User, int(user_id))


def _register_blueprints(app: Flask) -> None:
    from .blueprints import admin, api, auth, main, markets, support, trading

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(markets.bp)
    app.register_blueprint(trading.bp)
    app.register_blueprint(support.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(api.bp)


def _register_cli(app: Flask) -> None:
    import click

    from .seed import seed_all

    @app.cli.command("seed")
    def seed_command():
        """Create tables and load demo instruments (and optional dev admin)."""
        seed_all()
        click.echo("Seed complete. Demo instruments are ready.")

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables without seeding data."""
        db.create_all()
        click.echo("Database tables created.")


def _register_error_handlers(app: Flask) -> None:
    from flask import render_template

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "not_found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "forbidden"}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover - defensive
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "csrf_failed", "reason": error.description}), 400
        from flask import flash, redirect

        flash("Your session expired or the form was invalid. Please try again.", "error")
        return redirect(request.referrer or "/")


def _register_template_helpers(app: Flask) -> None:
    @app.template_filter("usd")
    def usd(value):
        try:
            return f"{Decimal(str(value)):,.2f}"
        except Exception:  # pragma: no cover - defensive
            return value

    @app.template_filter("qty")
    def qty_filter(value):
        try:
            d = Decimal(str(value))
            text = f"{d:f}".rstrip("0").rstrip(".")
            return text or "0"
        except Exception:  # pragma: no cover
            return value

    @app.template_filter("nice_date")
    def nice_date(value: datetime | None):
        if value is None:
            return "—"
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.strftime("%d %b %Y, %H:%M UTC")

    @app.context_processor
    def inject_globals():
        from flask import current_app

        return {
            "demo_currency": current_app.config["DEMO_CURRENCY"],
            "current_year": datetime.now(timezone.utc).year,
        }


def _register_headers_and_cors(app: Flask) -> None:
    allowed = set(app.config.get("CORS_ORIGINS") or [])

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.path.startswith("/api/"):
            origin = request.headers.get("Origin")
            if origin and origin in allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
                response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

    @app.route("/api/<path:_path>", methods=["OPTIONS"])
    def api_preflight(_path):  # pragma: no cover - browser convenience
        return ("", 204)


def create_tables() -> None:
    with db.engine.begin() as conn:
        db.metadata.create_all(conn)
