from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import cast

import pytest

if sys.version_info < (3, 14):
    pytest.skip("tdom requires Python 3.14+", allow_module_level=True)

from string.templatelib import Template  # type: ignore[import-not-found,unused-ignore]

from hayate import Context, Hayate, Response

from hayate_htmx import HtmxTemplates
from hayate_htmx.tdom import TdomRenderer, TdomView

_EXPECTED_VARY = "HX-Request, HX-History-Restore-Request, HX-Request-Type"


def _todo_items(values: Mapping[str, object]) -> list[Template]:
    todos = values["todos"]
    assert isinstance(todos, list)
    assert all(isinstance(todo, str) for todo in todos)
    return [cast(Template, eval('t"<li>{todo}</li>"', {}, {"todo": todo})) for todo in todos]


async def _page(values: Mapping[str, object]) -> Template:
    items = _todo_items(values)
    return cast(
        Template,
        eval(
            't"<!doctype html><title>Todos</title>'
            '<main id=\\"todo-list\\"><ul>{items}</ul></main>"',
            {},
            {"items": items},
        ),
    )


def _fragment(values: Mapping[str, object]) -> Template:
    items = _todo_items(values)
    return cast(Template, eval('t"<ul>{items}</ul>"', {}, {"items": items}))


def _app() -> Hayate:
    templates: HtmxTemplates[TdomView] = HtmxTemplates(TdomRenderer())
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


async def test_tdom_renders_async_page_and_fragment_safely() -> None:
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

    assert page_html.lower().startswith("<!doctype html>")
    assert fragment_html.startswith("<ul>")
    assert (await restored.text()).lower().startswith("<!doctype html>")
    assert (await partial.text()).startswith("<ul>")
    assert (await forced_page.text()).lower().startswith("<!doctype html>")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page_html
    assert "<script>" not in page_html
    assert page.headers.get("content-type") == "text/html;charset=utf-8"
    assert page.headers.get("vary") == _EXPECTED_VARY


async def test_tdom_accepts_prebuilt_template_views() -> None:
    page = cast(Template, eval('t"<h1>Page</h1>"'))
    fragment = cast(Template, eval('t"<h1>Fragment</h1>"'))
    templates: HtmxTemplates[TdomView] = HtmxTemplates(TdomRenderer())
    app = Hayate()

    @app.get("/")
    async def index(c: Context) -> Response:
        return await templates.render(c, page=page, fragment=fragment)

    response = await app.request("/", headers={"HX-Request": "true"})

    assert await response.text() == "<h1>Fragment</h1>"
