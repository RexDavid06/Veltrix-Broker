"""Public landing page, client dashboard and health endpoint."""
from decimal import Decimal

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import desc

from ..extensions import db
from ..models import Instrument, Position, Transaction, WatchlistItem, money

bp = Blueprint("main", __name__)


def _snapshot(limit: int = 4):
    return (
        Instrument.query.filter_by(is_active=True)
        .order_by(Instrument.asset_class, Instrument.symbol)
        .limit(limit)
        .all()
    )


@bp.get("/")
def landing():
    return render_template("landing.html", instruments=_snapshot())


@bp.get("/dashboard")
@login_required
def dashboard():
    positions = [p for p in Position.query.filter_by(user_id=current_user.id).all() if p.quantity > 0]
    portfolio_value = sum((p.market_value for p in positions), Decimal("0.00"))
    market_summary = (
        Instrument.query.filter_by(is_active=True)
        .order_by(Instrument.asset_class, Instrument.symbol)
        .limit(6)
        .all()
    )
    recent = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(desc(Transaction.created_at))
        .limit(5)
        .all()
    )
    watchlist = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    cash = money(current_user.account.cash_balance) if current_user.account else Decimal("0.00")
    return render_template(
        "dashboard/index.html",
        positions=positions,
        cash=cash,
        portfolio_value=portfolio_value,
        total_equity=money(cash + portfolio_value),
        cost_basis=sum((p.cost_basis for p in positions), Decimal("0.00")),
        unrealised=sum((p.unrealised_pnl for p in positions), Decimal("0.00")),
        market_summary=market_summary,
        recent=recent,
        watchlist=watchlist,
    )


@bp.get("/health")
def health():
    """Lightweight liveness probe used by deployments and tests."""
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception:  # pragma: no cover - defensive
        db_ok = False
    return (
        jsonify(
            {
                "status": "ok" if db_ok else "degraded",
                "service": "veltrix-demo",
                "database": "up" if db_ok else "down",
                "mode": "simulation",
                "disclaimer": "Demo only. No real trading, funds, or payments.",
            }
        ),
        200 if db_ok else 503,
    )
