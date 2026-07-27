from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlencode

from examples.golden.app import create_app
from hayate import Hayate

_FORM_HEADERS = {
    "content-type": "application/x-www-form-urlencoded",
    "origin": "http://localhost",
}


async def _sign_up(app: Hayate, email: str) -> str:
    response = await app.request(
        "/session/sign-up",
        method="POST",
        headers=_FORM_HEADERS,
        body=urlencode(
            {
                "email": email,
                "password": "correct horse battery staple",
            }
        ),
    )

    assert response.status == 303
    assert response.headers.get("location") == "/todos"
    cookie = response.headers.get("set-cookie")
    assert cookie is not None
    return cookie.split(";", 1)[0]


def _authed_form_headers(cookie: str) -> dict[str, str]:
    return {**_FORM_HEADERS, "cookie": cookie, "HX-Request": "true"}


async def test_identity_scoped_crud_validation_and_csrf(tmp_path: Path) -> None:
    app = create_app(database=tmp_path / "auth.db", auth_secret="test-secret")
    owner = await _sign_up(app, "owner@example.test")
    other = await _sign_up(app, "other@example.test")

    page = await app.request("/todos", headers={"cookie": owner})
    assert page.status == 200
    assert "<!doctype html>" in await page.text()
    assert page.headers.get("content-security-policy") is not None

    invalid = await app.request(
        "/todos",
        method="POST",
        headers=_authed_form_headers(owner),
        body=urlencode({"title": "   "}),
    )
    assert invalid.status == 200
    assert invalid.headers.get("hx-retarget") == "#todo-form-errors"
    assert 'role="alert"' in await invalid.text()

    malicious_title = '<img src=x onerror="alert(1)">'
    created = await app.request(
        "/todos",
        method="POST",
        headers=_authed_form_headers(owner),
        body=urlencode({"title": malicious_title}),
    )
    created_html = await created.text()
    assert created.status == 201
    assert "&lt;img" in created_html
    assert "<img" not in created_html
    assert created.headers.get("hx-trigger") == '{"todo:created":{"id":"1"}}'

    isolated = await app.request(
        "/todos",
        headers={"cookie": other, "HX-Request": "true"},
    )
    assert malicious_title not in await isolated.text()
    forbidden_delete = await app.request(
        "/todos/1",
        method="DELETE",
        headers=_authed_form_headers(other),
    )
    assert forbidden_delete.status == 404

    edit = await app.request(
        "/todos/1/edit",
        headers={"cookie": owner, "HX-Request": "true"},
    )
    assert 'value="&lt;img' in await edit.text()

    updated = await app.request(
        "/todos/1",
        method="PATCH",
        headers=_authed_form_headers(owner),
        body=urlencode({"title": "Ship the reference app"}),
    )
    assert "Ship the reference app" in await updated.text()

    toggled = await app.request(
        "/todos/1/toggle?filter=done",
        method="PATCH",
        headers=_authed_form_headers(owner),
        body="",
    )
    toggled_html = await toggled.text()
    assert 'data-filter="done"' in toggled_html
    assert "Ship the reference app" in toggled_html

    cross_origin = await app.request(
        "/todos",
        method="POST",
        headers={
            **_authed_form_headers(owner),
            "origin": "https://attacker.example",
        },
        body=urlencode({"title": "stolen"}),
    )
    assert cross_origin.status == 403

    deleted = await app.request(
        "/todos/1",
        method="DELETE",
        headers=_authed_form_headers(owner),
    )
    assert "Ship the reference app" not in await deleted.text()


async def test_history_restore_asset_and_stream_contract(tmp_path: Path) -> None:
    app = create_app(database=tmp_path / "auth.db", auth_secret="test-secret")
    cookie = await _sign_up(app, "stream@example.test")

    fragment = await app.request(
        "/todos",
        headers={"cookie": cookie, "HX-Request": "true"},
    )
    restored = await app.request(
        "/todos",
        headers={
            "cookie": cookie,
            "HX-Request": "true",
            "HX-History-Restore-Request": "true",
        },
    )
    assert (await fragment.text()).startswith('<section id="todo-list"')
    assert (await restored.text()).startswith("<!doctype html>")

    asset = await app.request("/static/vendor/htmx-2.0.10.min.js")
    assert asset.status == 200
    assert asset.headers.get("cache-control") == "public, max-age=31536000, immutable"
    assert b"var htmx=" in await asset.bytes()

    stream = await app.request("/todos/stream", headers={"cookie": cookie})
    stream_body = await stream.text()
    assert stream.headers.get("content-type") == "text/event-stream"
    assert 'event: token\ndata: {"token":"Hypermedia"}' in stream_body
    assert "event: done\ndata: complete" in stream_body


def test_vendored_htmx_asset_is_the_reviewed_2_0_10_build() -> None:
    asset = Path(__file__).parents[1] / "examples/golden/static/vendor/htmx-2.0.10.min.js"

    assert hashlib.sha256(asset.read_bytes()).hexdigest() == (
        "71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de"
    )
