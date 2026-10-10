"""Database models for the VELTRIX demonstration platform.

All monetary values use :class:`decimal.Decimal` (via ``Numeric``) so that
arithmetic is not subject to binary floating point rounding. The demo is a
paper-trading simulator: no model represents real money, custody, or a real
order sent to any venue.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

MONEY = Decimal("0.01")
QUANTITY = Decimal("0.00000001")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY)


def quantity(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(QUANTITY)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="client", index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    account = db.relationship(
        "DemoAccount", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    transactions = db.relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan",
        order_by="desc(Transaction.created_at)",
    )
    positions = db.relationship(
        "Position", back_populates="user", cascade="all, delete-orphan"
    )
    watchlist = db.relationship(
        "WatchlistItem", back_populates="user", cascade="all, delete-orphan"
    )
    support_requests = db.relationship(
        "SupportRequest", back_populates="user", cascade="all, delete-orphan",
        order_by="desc(SupportRequest.created_at)",
    )

    # --- Password handling ----------------------------------------------
    def set_password(self, raw_password: str) -> None:
        # werkzeug uses scrypt by default; never store or log the raw value.
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def cash_balance(self) -> Decimal:
        return self.account.cash_balance if self.account else Decimal("0.00")

    def owns(self, instrument) -> bool:
        pos = Position.query.filter_by(user_id=self.id, instrument_id=instrument.id).first()
        return bool(pos and pos.quantity > 0)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.id} {self.email} role={self.role}>"


class DemoAccount(db.Model):
    __tablename__ = "demo_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    currency = db.Column(db.String(8), nullable=False, default="USD")
    cash_balance = db.Column(db.Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="account")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DemoAccount user={self.user_id} {self.cash_balance} {self.currency}>"


class Instrument(db.Model):
    __tablename__ = "instruments"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    asset_class = db.Column(db.String(32), nullable=False, index=True)
    currency = db.Column(db.String(8), nullable=False, default="USD")
    price = db.Column(db.Numeric(18, 8), nullable=False)
    change_percent = db.Column(db.Numeric(8, 4), nullable=False, default=Decimal("0"))
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Instrument {self.symbol} {self.price}>"


class Position(db.Model):
    __tablename__ = "positions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "instrument_id", name="uq_position_user_instrument"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id = db.Column(
        db.Integer, db.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity = db.Column(db.Numeric(24, 8), nullable=False, default=Decimal("0"))
    avg_price = db.Column(db.Numeric(18, 8), nullable=False, default=Decimal("0"))
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="positions")
    instrument = db.relationship("Instrument")

    @property
    def market_value(self) -> Decimal:
        return money(self.quantity * (self.instrument.price if self.instrument else Decimal("0")))

    @property
    def cost_basis(self) -> Decimal:
        return money(self.quantity * self.avg_price)

    @property
    def unrealised_pnl(self) -> Decimal:
        return money(self.market_value - self.cost_basis)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Position user={self.user_id} inst={self.instrument_id} qty={self.quantity}>"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id = db.Column(
        db.Integer, db.ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    symbol = db.Column(db.String(24), nullable=False)
    side = db.Column(db.String(12), nullable=False)  # buy | sell | topup
    quantity = db.Column(db.Numeric(24, 8), nullable=False, default=Decimal("0"))
    execution_price = db.Column(db.Numeric(18, 8), nullable=False, default=Decimal("0"))
    amount = db.Column(db.Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    status = db.Column(db.String(20), nullable=False, default="simulated", index=True)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="transactions")
    instrument = db.relationship("Instrument")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction {self.id} {self.side} {self.symbol} {self.amount}>"


class WatchlistItem(db.Model):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        db.UniqueConstraint("user_id", "instrument_id", name="uq_watchlist_user_instrument"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id = db.Column(
        db.Integer, db.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="watchlist")
    instrument = db.relationship("Instrument")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WatchlistItem user={self.user_id} inst={self.instrument_id}>"


class SupportRequest(db.Model):
    __tablename__ = "support_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="support_requests")

    STATUSES = ("open", "in_progress", "resolved")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SupportRequest {self.id} {self.status}>"
