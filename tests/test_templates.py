from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from hayate import Context, Hayate, Response
from hayate.middleware import etag

from hayate_htmx import (
    HtmxTemplates,
    JinjaRenderer,
    TemplateNotFoundError,
)

_EXPECTED_VARY = "HX-Request, HX-History-Restore-Request, HX-Request-Type"


def _write_todo_templates(root: Path) -> None:
    (root / "todos").mkdir()
    (root / "todos/page.html").write_text(
        """<!doctype html>
<title>Todos</title>
<main id="todo-list">{% include "todos/_list.html" %}</main>""",
        encoding="utf-8",
    )
    (root / "todos/_list.html").write_text(
        "<ul>{% for todo in todos %}<li>{{ todo }}</li>{% endfor %}</ul>",
        encoding="utf-8",
    )


def _todo_app(root: Path, *, use_etag: bool = False) -> Hayate:
    _write_todo_templates(root)
    templates = HtmxTemplates(JinjaRenderer(root))
    app = Hayate()
    if use_etag:
        app.use(etag())

    @app.get("/todos")
    async def todos(c: Context) -> Response:
        return await templates.render(
            c,
            page="todos/page.html",
            fragment="todos/_list.html",
            values={"todos": ["<script>alert(1)</script>", "Ship it"]},
        )

    return app


async def test_renders_full_page_and_escapes_values_by_default(tmp_path: Path) -> None:
    app = _todo_app(tmp_path)

    response = await app.request("/todos")
    html = await response.text()

    assert html.startswith("<!doctype html>")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html
    assert response.headers.get("content-type") == "text/html;charset=utf-8"
    assert response.headers.get("vary") == _EXPECTED_VARY


async def test_renders_htmx_2_fragment_but_full_page_for_history_restore(
    tmp_path: Path,
) -> None:
    app = _todo_app(tmp_path)

    fragment = await app.request("/todos", headers={"HX-Request": "true"})
    restored = await app.request(
        "/todos",
        headers={
            "HX-Request": "true",
            "HX-History-Restore-Request": "true",
        },
    )
    fragment_html = await fragment.text()

    assert fragment_html.startswith("<ul>")
    assert "<!doctype html>" not in fragment_html
    assert (await restored.text()).startswith("<!doctype html>")


async def test_htmx_4_request_type_is_authoritative(tmp_path: Path) -> None:
    app = _todo_app(tmp_path)

    fragment = await app.request(
        "/todos",
        headers={"HX-Request-Type": "partial"},
    )
    page = await app.request(
        "/todos",
        headers={"HX-Request": "true", "HX-Request-Type": "full"},
    )

    assert (await fragment.text()).startswith("<ul>")
    assert (await page.text()).startswith("<!doctype html>")


async def test_vary_composes_without_duplicates(tmp_path: Path) -> None:
    _write_todo_templates(tmp_path)
    templates = HtmxTemplates(JinjaRenderer(tmp_path))
    app = Hayate()

    @app.get("/todos")
    async def todos(c: Context) -> Response:
        return await templates.render(
            c,
            page="todos/page.html",
            fragment="todos/_list.html",
            headers={"Vary": "Accept-Encoding, HX-Request"},
        )

    response = await app.request("/todos")

    assert response.headers.get("vary") == (
        "Accept-Encoding, HX-Request, HX-History-Restore-Request, HX-Request-Type"
    )


async def test_etags_are_representation_specific(tmp_path: Path) -> None:
    app = _todo_app(tmp_path, use_etag=True)

    page = await app.request("/todos")
    fragment = await app.request("/todos", headers={"HX-Request": "true"})
    page_tag = page.headers.get("etag")
    fragment_tag = fragment.headers.get("etag")

    assert page_tag is not None
    assert fragment_tag is not None
    assert page_tag != fragment_tag

    wrong_variant = await app.request(
        "/todos",
        headers={"HX-Request": "true", "If-None-Match": page_tag},
    )
    matching_variant = await app.request(
        "/todos",
        headers={"HX-Request": "true", "If-None-Match": fragment_tag},
    )

    assert wrong_variant.status == 200
    assert matching_variant.status == 304
    assert matching_variant.headers.get("vary") == _EXPECTED_VARY


async def test_normalizes_missing_page_fragment_and_include_errors(tmp_path: Path) -> None:
    renderer = JinjaRenderer(tmp_path)

    with pytest.raises(TemplateNotFoundError, match=r"missing-page\.html") as page_error:
        await renderer.render("missing-page.html", {})
    assert page_error.value.template_name == "missing-page.html"

    with pytest.raises(TemplateNotFoundError, match=r"missing-fragment\.html"):
        await renderer.render("missing-fragment.html", {})

    (tmp_path / "page.html").write_text(
        '{% include "missing-include.html" %}',
        encoding="utf-8",
    )
    with pytest.raises(TemplateNotFoundError, match=r"missing-include\.html"):
        await renderer.render("page.html", {})


class RecordingRenderer:
    def __init__(self) -> None:
        self.names: list[str] = []

    async def render(
        self,
        template_name: str,
        context: Mapping[str, object],
    ) -> str:
        self.names.append(template_name)
        return f"{template_name}:{context['value']}"


async def test_template_selection_is_renderer_independent() -> None:
    renderer = RecordingRenderer()
    templates = HtmxTemplates(renderer)
    app = Hayate()

    @app.get("/")
    async def index(c: Context) -> Response:
        return await templates.render(
            c,
            page="page",
            fragment="fragment",
            values={"value": "rendered"},
        )

    response = await app.request("/", headers={"HX-Request": "true"})

    assert renderer.names == ["fragment"]
    assert await response.text() == "fragment:rendered"


async def _call_asgi(
    app: Hayate,
    *,
    headers: tuple[tuple[str, str], ...] = (),
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    inbox: list[dict[str, Any]] = [{"type": "http.request", "body": b"", "more_body": False}]

    async def receive() -> dict[str, Any]:
        if inbox:
            return inbox.pop(0)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/todos",
        "raw_path": b"/todos",
        "query_string": b"",
        "headers": [(name.encode(), value.encode()) for name, value in headers],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
    }
    await app(scope, receive, send)
    return messages


async def test_fragment_renders_through_asgi(tmp_path: Path) -> None:
    app = _todo_app(tmp_path)

    messages = await _call_asgi(app, headers=(("hx-request", "true"),))
    start = messages[0]
    body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    headers = dict(start["headers"])

    assert start["status"] == 200
    assert body.startswith(b"<ul>")
    assert headers[b"content-type"] == b"text/html;charset=utf-8"
    assert headers[b"vary"] == _EXPECTED_VARY.encode()
