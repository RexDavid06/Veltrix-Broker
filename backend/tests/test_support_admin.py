"""Support requests, cross-user isolation and admin status updates."""
from conftest import create_user, get_csrf, login, logout, register

from app.models import SupportRequest, User


def submit_support(client, subject, message):
    token = get_csrf(client, "/support/")
    return client.post(
        "/support/",
        data={"csrf_token": token, "subject": subject, "message": message},
        follow_redirects=True,
    )


def test_support_request_created_and_listed(client, app):
    register(client, email="support@example.com")
    response = submit_support(client, "Help with demo", "How do demo funds work exactly?")
    assert response.status_code == 200
    user = User.query.filter_by(email="support@example.com").first()
    row = SupportRequest.query.filter_by(user_id=user.id).first()
    assert row is not None
    assert row.status == "open"
    assert "Help with demo" in client.get("/support/").get_data(as_text=True)


def test_support_request_validation(client, app):
    register(client, email="support@example.com")
    token = get_csrf(client, "/support/")
    client.post("/support/", data={"csrf_token": token, "subject": "", "message": ""})
    assert SupportRequest.query.count() == 0


def test_support_requests_isolated_between_users(client, app):
    register(client, email="alice@example.com")
    submit_support(client, "Alice private", "Alice secret message about her account.")
    logout(client)

    register(client, email="bob@example.com")
    body = client.get("/support/").get_data(as_text=True)
    assert "Alice secret message" not in body


def test_admin_can_update_support_status(client, app):
    register(client, email="support@example.com")
    submit_support(client, "Needs review", "Please review this demo request for me.")
    row = SupportRequest.query.first()
    logout(client)

    create_user(app, "admin@example.com", role="admin")
    login(client, "admin@example.com")

    token = get_csrf(client, "/admin/support")
    response = client.post(
        f"/admin/support/{row.id}/status",
        data={"csrf_token": token, "status": "resolved"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert SupportRequest.query.get(row.id).status == "resolved"


def test_client_cannot_update_support_status(client, app):
    register(client, email="support@example.com")
    submit_support(client, "Needs review", "Please review this demo request for me.")
    row = SupportRequest.query.first()
    token = get_csrf(client, "/support/")
    response = client.post(
        f"/admin/support/{row.id}/status",
        data={"csrf_token": token, "status": "resolved"},
    )
    assert response.status_code == 403
    assert SupportRequest.query.get(row.id).status == "open"


def test_admin_sees_all_support_requests(client, app):
    register(client, email="alice@example.com")
    submit_support(client, "Alice ticket", "A message from Alice for the admin.")
    logout(client)

    create_user(app, "admin@example.com", role="admin")
    login(client, "admin@example.com")
    body = client.get("/admin/support").get_data(as_text=True)
    assert "Alice ticket" in body
