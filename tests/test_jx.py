from __future__ import annotations

from pathlib import Path

import pytest
from hayate import Context, Hayate, Response

from hayate_htmx import HtmxTemplates
from hayate_htmx.jx import ComponentNotFoundError, JxRenderer

_EXPECTED_VARY = "HX-Request, HX-History-Restore-Request, HX-Request-Type"


def _write_components(root: Path) -> None:
    root.mkdir()
    (root / "page.jx").write_text(
        """{#import "_list.jx" as TodoList #}
{#def todos #}
<!doctype html>
<title>Todos</title>
<main id="todo-list"><TodoList todos={{ todos }} /></main>""",
        encoding="utf-8",
    )
    (root / "_list.jx").write_text(
        """{#def todos #}
<ul>{% for todo in todos %}<li>{{ todo }}</li>{% endfor %}</ul>""",
        encoding="utf-8",
    )


def _app(root: Path) -> Hayate:
    _write_components(root)
    templates = HtmxTemplates(JxRenderer(root))
    app = Hayate()

    @app.get("/todos")
    async def todos(c: Context) -> Response:
        return await templates.render(
            c,
            page="page.jx",
            fragment="_list.jx",
            values={"todos": ["<script>alert(1)</script>", "Ship it"]},
        )

    return app


async def test_jx_renders_components_props_and_selection_safely(tmp_path: Path) -> None:
    app = _app(tmp_path / "components")

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


async def test_jx_reuses_catalog_and_preserves_missing_component_identity(
    tmp_path: Path,
) -> None:
    renderer = JxRenderer(tmp_path)
    catalog = renderer.catalog

    with pytest.raises(ComponentNotFoundError, match=r"missing\.jx") as error:
        await renderer.render("missing.jx", {})

    assert renderer.catalog is catalog
    assert error.value.component_name == "missing.jx"


async def test_jx_preserves_slots_and_component_asset_dependencies(
    tmp_path: Path,
) -> None:
    root = tmp_path / "components"
    root.mkdir()
    (root / "page.jx").write_text(
        """{#import "_card.jx" as Card #}
{#def title, header, body, footer #}
<!doctype html>
<head>{{ assets.render() }}</head>
<body>
<Card title={{ title }}>
  {% fill header %}<strong>{{ header }}</strong>{% endfill %}
  <p>{{ body }}</p>
  {% fill footer %}<small>{{ footer }}</small>{% endfill %}
</Card>
</body>""",
        encoding="utf-8",
    )
    (root / "_card.jx").write_text(
        """{#css /static/card.css #}
{#js /static/card.js #}
{#def title #}
<article>
  <h1>{{ title }}</h1>
  <header>{% slot header %}Default header{% endslot %}</header>
  <main>{{ content }}</main>
  <footer>{% slot footer %}Default footer{% endslot %}</footer>
</article>""",
        encoding="utf-8",
    )
    renderer = JxRenderer(root)

    html = await renderer.render(
        "page.jx",
        {
            "title": "Profile",
            "header": "<unsafe-header>",
            "body": "<unsafe-body>",
            "footer": "<unsafe-footer>",
        },
    )

    assert '<link rel="stylesheet" href="/static/card.css">' in html
    assert '<script type="module" src="/static/card.js"></script>' in html
    assert "<strong>&lt;unsafe-header&gt;</strong>" in html
    assert "<p>&lt;unsafe-body&gt;</p>" in html
    assert "<small>&lt;unsafe-footer&gt;</small>" in html
    assert "Default header" not in html
    assert "Default footer" not in html
