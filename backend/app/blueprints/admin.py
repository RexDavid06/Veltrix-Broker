"""Administrator-only operations. Authorization is enforced server-side."""
from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import desc, func

from ..decorators import admin_required
from ..extensions import db
from ..forms import AdminSupportForm
from ..models import DemoAccount, Instrument, SupportRequest, Transaction, User, utcnow

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _stats() -> dict:
    since = utcnow() - timedelta(days=7)
    return {
        "users": User.query.filter_by(role="client").count(),
        "admins": User.query.filter_by(role="admin").count(),
        "transactions": Transaction.query.count(),
        "open_support": SupportRequest.query.filter(SupportRequest.status != "resolved").count(),
        "instruments": Instrument.query.filter_by(is_active=True).count(),
        "cash_total": db.session.query(func.coalesce(func.sum(DemoAccount.cash_balance), 0)).scalar(),
        "new_users_7d": User.query.filter(User.created_at >= since).count(),
    }


@bp.get("/")
@login_required
@admin_required
def dashboard():
    recent_transactions = (
        Transaction.query.order_by(desc(Transaction.created_at)).limit(6).all()
    )
    recent_support = (
        SupportRequest.query.order_by(desc(SupportRequest.created_at)).limit(6).all()
    )
    return render_template(
        "admin/index.html",
        stats=_stats(),
        recent_transactions=recent_transactions,
        recent_support=recent_support,
    )


@bp.get("/users")
@login_required
@admin_required
def users():
    rows = User.query.order_by(desc(User.created_at)).all()
    return render_template("admin/users.html", users=rows)


@bp.get("/transactions")
@login_required
@admin_required
def transactions():
    rows = (
        Transaction.query.order_by(desc(Transaction.created_at), desc(Transaction.id))
        .limit(200)
        .all()
    )
    return render_template("admin/transactions.html", transactions=rows)


@bp.get("/support")
@login_required
@admin_required
def support():
    status = (request.args.get("status") or "").strip()
    stmt = SupportRequest.query
    if status in SupportRequest.STATUSES:
        stmt = stmt.filter_by(status=status)
    rows = stmt.order_by(desc(SupportRequest.created_at)).all()
    return render_template(
        "admin/support.html", requests=rows, form=AdminSupportForm(), active_status=status
    )


@bp.post("/support/<int:request_id>/status")
@login_required
@admin_required
def update_support_status(request_id: int):
    row = db.session.get(SupportRequest, request_id)
    if row is None:
        abort(404)
    form = AdminSupportForm()
    if form.validate_on_submit() and form.status.data in SupportRequest.STATUSES:
        row.status = form.status.data
        db.session.commit()
        flash(f"Request #{row.id} marked as {row.status.replace('_', ' ')}.", "success")
    else:
        flash("Could not update that request status.", "error")
    return redirect(request.referrer or url_for("admin.support"))
