"""Support centre. Requests are stored, but no live human service is connected."""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc

from ..extensions import db
from ..forms import SupportForm
from ..models import SupportRequest

bp = Blueprint("support", __name__, url_prefix="/support")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    form = SupportForm()
    if form.validate_on_submit():
        request_row = SupportRequest(
            user_id=current_user.id,
            subject=form.subject.data.strip(),
            message=form.message.data.strip(),
            status="open",
        )
        db.session.add(request_row)
        db.session.commit()
        flash(
            "Your demo support request was saved. Status is 'open'. This is a demo queue — "
            "no human agent is connected and non-operational support is not staffed.",
            "success",
        )
        return redirect(url_for("support.index"))
    requests = (
        SupportRequest.query.filter_by(user_id=current_user.id)
        .order_by(desc(SupportRequest.created_at))
        .all()
    )
    return render_template("support/index.html", form=form, requests=requests)
