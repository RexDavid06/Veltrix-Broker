"""Shared Flask extension instances.

Kept in a separate module so blueprints and the application factory can import
them without creating circular imports.
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"
login_manager.session_protection = "strong"
