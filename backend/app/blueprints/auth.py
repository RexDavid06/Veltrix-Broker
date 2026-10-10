"""Authentication: registration, sign-in, sign-out."""
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from ..extensions import db
from ..forms import LoginForm, RegistrationForm
from ..models import DemoAccount, User, money

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str:
    """Only allow relative, same-site redirect targets."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("main.dashboard")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing = User.query.filter(func.lower(User.email) == email).first()
        if existing:
            form.email.errors.append("An account with this email already exists.")
        else:
            user = User(name=form.name.data.strip(), email=email, role="client")
            user.set_password(form.password.data)
            user.account = DemoAccount(
                currency=current_app.config["DEMO_CURRENCY"],
                cash_balance=money(current_app.config["DEMO_STARTING_BALANCE"]),
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Your demo account is ready. All balances and trades are simulated.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()
        # Generic message prevents account enumeration.
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password.", "error")
        else:
            login_user(user, remember=form.remember.data)
            flash("Signed in to the demo workspace.", "success")
            return redirect(_safe_next(request.args.get("next")))
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.landing"))
