"""Read-only JSON API.

Exposes the illustrative instrument list so the static GitHub Pages frontend
can display the same demo market data. It is intentionally read-only: all
state-changing operations stay in the CSRF-protected server-rendered app.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from ..models import Instrument

bp = Blueprint("api", __name__, url_prefix="/api")


def _serialise(inst: Instrument) -> dict:
    return {
        "symbol": inst.symbol,
        "name": inst.name,
        "asset_class": inst.asset_class,
        "currency": inst.currency,
        "price": float(inst.price),
        "change_percent": float(inst.change_percent),
        "note": "Illustrative demo price — not live market data.",
    }


@bp.get("/instruments")
def instruments():
    query = (request.args.get("q") or "").strip().lower()
    asset = (request.args.get("asset") or "").strip()
    stmt = Instrument.query.filter_by(is_active=True)
    if query:
        like = f"%{query}%"
        stmt = stmt.filter(
            or_(func.lower(Instrument.symbol).like(like), func.lower(Instrument.name).like(like))
        )
    if asset:
        stmt = stmt.filter(Instrument.asset_class == asset)
    rows = stmt.order_by(Instrument.asset_class, Instrument.symbol).all()
    return jsonify(
        {
            "data": [_serialise(i) for i in rows],
            "disclaimer": "All prices are illustrative demo data and are not live market data.",
        }
    )


@bp.get("/instruments/<path:symbol>")
def instrument(symbol: str):
    inst = Instrument.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if inst is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"data": _serialise(inst)})
