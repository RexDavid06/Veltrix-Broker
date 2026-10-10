"""Seed the demo database.

Creates the illustrative instrument universe. An administrator account is only
created when ``ADMIN_EMAIL`` and ``ADMIN_PASSWORD`` are configured through the
environment, so no predictable admin password is ever shipped.
"""
from __future__ import annotations

from decimal import Decimal

from flask import current_app
from sqlalchemy import func

from .extensions import db
from .models import DemoAccount, Instrument, User, money

INSTRUMENTS = [
    # Stocks
    ("AAPL", "Apple Inc.", "Stocks", "185.64", "1.24"),
    ("MSFT", "Microsoft Corporation", "Stocks", "412.30", "0.86"),
    ("ASML", "ASML Holding N.V.", "Stocks", "742.10", "-0.42"),
    ("SAP", "SAP SE", "Stocks", "168.25", "0.33"),
    ("TSLA", "Tesla, Inc.", "Stocks", "238.90", "-1.18"),
    # Crypto
    ("BTC/USD", "Bitcoin / US Dollar", "Crypto", "67420.00", "1.42"),
    ("ETH/USD", "Ethereum / US Dollar", "Crypto", "3280.55", "0.74"),
    ("SOL/USD", "Solana / US Dollar", "Crypto", "146.20", "-2.05"),
    # Forex
    ("EUR/USD", "Euro / US Dollar", "Forex", "1.08420", "0.18"),
    ("GBP/USD", "British Pound / US Dollar", "Forex", "1.27160", "0.08"),
    ("USD/JPY", "US Dollar / Japanese Yen", "Forex", "151.240", "-0.12"),
    # Commodities
    ("XAU/USD", "Gold / US Dollar", "Commodities", "2356.80", "-0.24"),
    ("WTI/USD", "Crude Oil WTI / US Dollar", "Commodities", "78.35", "0.51"),
    # Indices
    ("NAS100", "Nasdaq 100 Index", "Indices", "18214.60", "0.62"),
    ("SPX500", "S&P 500 Index", "Indices", "5216.40", "0.41"),
    ("DAX40", "Germany 40 Index", "Indices", "18192.30", "-0.19"),
]


def seed_instruments() -> int:
    created = 0
    for symbol, name, asset_class, price, change in INSTRUMENTS:
        exists = Instrument.query.filter(
            func.lower(Instrument.symbol) == symbol.lower()
        ).first()
        if exists:
            continue
        db.session.add(
            Instrument(
                symbol=symbol,
                name=name,
                asset_class=asset_class,
                currency="USD",
                price=Decimal(price),
                change_percent=Decimal(change),
            )
        )
        created += 1
    db.session.commit()
    return created


def seed_admin() -> str | None:
    email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
    password = current_app.config.get("ADMIN_PASSWORD") or ""
    if not email or not password:
        return None
    if User.query.filter(func.lower(User.email) == email).first():
        return None
    admin = User(name=current_app.config.get("ADMIN_NAME", "Veltrix Admin"), email=email, role="admin")
    admin.set_password(password)
    admin.account = DemoAccount(
        currency=current_app.config["DEMO_CURRENCY"],
        cash_balance=money(Decimal("0.00")),
    )
    db.session.add(admin)
    db.session.commit()
    return email


def seed_all() -> dict:
    db.create_all()
    return {"instruments": seed_instruments(), "admin": seed_admin()}
