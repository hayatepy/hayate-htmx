from __future__ import annotations

from collections.abc import Mapping

from hayate import Context, Hayate, Response
from htpy import Renderable, body, h1, html, li, main, ul

from hayate_htmx import HtmxTemplates
from hayate_htmx.htpy import HtpyRenderer, HtpyView

_EXPECTED_VARY = "HX-Request, HX-History-Restore-Request, HX-Request-Type"


def _todos(values: Mapping[str, object]) -> list[str]:
    todos = values["todos"]
    assert isinstance(todos, list)
    assert all(isinstance(todo, str) for todo in todos)
    return todos


async def _page(values: Mapping[str, object]) -> Renderable:
    return html[body[h1["Todos"], main(id="todo-list")[_fragment(values)]]]


def _fragment(values: Mapping[str, object]) -> Renderable:
    return ul[(li[todo] for todo in _todos(values))]


def _app() -> Hayate:
    renderer = HtpyRenderer()
    templates: HtmxTemplates[HtpyView] = HtmxTemplates(renderer)
    app = Hayate()

    @app.get("/todos")
    async def todos(c: Context) -> Response:
        return await templates.render(
            c,
            page=_page,
            fragment=_fragment,
            values={"todos": ["<script>alert(1)</script>", "Ship it"]},
        )

    return app


async def test_htpy_renders_async_page_and_sync_fragment_safely() -> None:
    app = _app()

    page = await app.request("/todos")
    fragment = await app.request("/todos", headers={"HX-Request": "true"})
    restored = await app.request(
        "/todos",
        headers={
            "HX-Request": "true",
            "HX-History-Restore-Request": "true",
        },
    )
    partial = await app.request("/todos", headers={"HX-Request-Type": "partial"})
    forced_page = await app.request(
        "/todos",
        headers={"HX-Request": "true", "HX-Request-Type": "full"},
    )
    page_html = await page.text()
    fragment_html = await fragment.text()

    assert page_html.startswith("<!doctype html>")
    assert fragment_html.startswith("<ul>")
    assert (await restored.text()).startswith("<!doctype html>")
    assert (await partial.text()).startswith("<ul>")
    assert (await forced_page.text()).startswith("<!doctype html>")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page_html
    assert "<script>" not in page_html
    assert page.headers.get("content-type") == "text/html;charset=utf-8"
    assert page.headers.get("vary") == _EXPECTED_VARY


async def test_htpy_accepts_prebuilt_renderable_views() -> None:
    templates: HtmxTemplates[HtpyView] = HtmxTemplates(HtpyRenderer())
    app = Hayate()

    @app.get("/")
    async def index(c: Context) -> Response:
        return await templates.render(
            c,
            page=html[body[h1["Page"]]],
            fragment=h1["Fragment"],
        )

    response = await app.request("/", headers={"HX-Request": "true"})

    assert await response.text() == "<h1>Fragment</h1>"
