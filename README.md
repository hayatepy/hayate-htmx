# hayate-htmx

> **Hayate ecosystem:** [Start here](https://github.com/hayatepy/.github/blob/main/docs/START.md)
> · [Hayate](https://github.com/hayatepy/hayate)
> · [Frontend roadmap](https://github.com/hayatepy/roadmap/issues/10)

Full-stack hypermedia integration between
[Hayate](https://github.com/hayatepy/hayate) and [htmx](https://htmx.org).

`hayate-htmx` keeps htmx-specific request and response behavior outside the
standards-first Hayate core. It provides typed `HX-*` metadata, safe Jinja
rendering, explicit page/fragment selection, and response controls that remain
ordinary Hayate responses.

> **Status: alpha (0.1.x).** htmx 2.x is the stable production contract.
> htmx 4 request metadata is accepted additively while htmx 4 remains a
> pre-release.

## Install

```sh
uv add hayate-htmx
```

This installs Jinja as the batteries-included HTML renderer. Hayate itself
remains template-engine independent.

## Golden full-stack application

[`examples/golden`](examples/golden) is the executable reference path:

- account creation and session cookies through `hayate-auth`;
- identity-scoped create/edit/toggle/delete operations;
- accessible server-rendered validation errors;
- htmx history navigation with full-page restoration;
- a native SSE token stream suitable for incremental AI output;
- a self-hosted, integrity-pinned htmx 2.0.10 asset;
- CSP, Origin/Fetch-Metadata CSRF checks, and no unsafe HTML concatenation.

Run it from a fresh checkout:

```sh
uv sync --locked
export AUTH_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
uv run uvicorn examples.golden.app:app --reload
```

Then open <http://127.0.0.1:8000/login>. The
[example README](examples/golden/README.md) includes the browser smoke command.
Operational details live in the [authentication](docs/AUTH.md),
[asset](docs/ASSETS.md), [compatibility](docs/COMPATIBILITY.md), and
[release](docs/RELEASING.md) guides.

## Full-page and fragment rendering

Define the complete document and its replaceable fragment as separate named
templates. The complete page can include the fragment, so the markup still has
one source of truth.

```html
<!-- templates/todos/page.html -->
<!doctype html>
<title>Todos</title>
<main id="todo-list">{% include "todos/_list.html" %}</main>
```

```html
<!-- templates/todos/_list.html -->
<ul>
  {% for todo in todos %}
    <li>{{ todo }}</li>
  {% endfor %}
</ul>
```

One handler serves both representations:

```python
from hayate import Hayate
from hayate_htmx import HtmxTemplates, JinjaRenderer

app = Hayate()
templates = HtmxTemplates(JinjaRenderer("templates"))

@app.get("/todos")
async def todos(c):
    return await templates.render(
        c,
        page="todos/page.html",
        fragment="todos/_list.html",
        values={"todos": ["Write docs", "Ship release"]},
    )
```

The selection rules are deterministic:

| Request | Representation |
| --- | --- |
| ordinary browser request | complete page |
| htmx 2 `HX-Request: true` | fragment |
| htmx 2 history restore | complete page |
| htmx 4 `HX-Request-Type: partial` | fragment |
| htmx 4 `HX-Request-Type: full` | complete page |

`HX-Request-Type` is authoritative when present. Jinja autoescaping is enabled
by default for HTML, including values rendered by fragment templates.

`TemplateNotFoundError` is raised with its `template_name` when a page,
fragment, or included template cannot be loaded. Empty page or fragment names
raise `ValueError`.

### Caching and ETags

Every adaptive response composes this header:

```http
Vary: HX-Request, HX-History-Restore-Request, HX-Request-Type
```

Standards-compliant HTTP caches therefore keep complete pages and fragments in
separate variants. Hayate's `etag()` middleware also produces different ETags
for their different bodies and preserves `Vary` on `304 Not Modified`.

Do not put Hayate 0.12's in-process `cache()` middleware in front of an
adaptive route: that micro-cache currently keys only by URL and does not
interpret `Vary`. Use an HTTP cache that honors `Vary`, disable that middleware
for adaptive routes, or expose distinct URLs.

## Rendering engines

Jinja2 remains the batteries-included default. Optional first-party adapters
use the same typed page/fragment selection contract:

| Renderer | Install | View | Status |
| --- | --- | --- | --- |
| Jinja2 | `hayate-htmx` | template name | stable default |
| htpy | `hayate-htmx[htpy]` | typed renderable or component factory | supported |
| Jx | `hayate-htmx[jx]` | catalog component name | supported |
| tdom | `hayate-htmx[tdom]` | t-string template or factory | experimental, Python 3.14+ |

The optional modules are lazy boundaries. Importing `hayate_htmx` never
imports htpy, Jx, or tdom, and the tdom adapter does not raise the package's
Python 3.12 minimum.

```python
from hayate_htmx import HtmxTemplates
from hayate_htmx.htpy import HtpyRenderer

views = HtmxTemplates(HtpyRenderer())
```

```python
from hayate_htmx import HtmxTemplates
from hayate_htmx.jx import JxRenderer

views = HtmxTemplates(JxRenderer("components"))
```

On Python 3.14, tdom component factories return a t-string `Template`:

```python
from hayate_htmx import HtmxTemplates
from hayate_htmx.tdom import TdomRenderer

views = HtmxTemplates(TdomRenderer())
```

htpy consumes async component children through `aiter_chunks()`. Jx reuses one
`Catalog`, including its props, slots, and asset graph. Every adapter preserves
its renderer's safe escaping defaults; trusted/raw markup remains an explicit
renderer-native operation. See [renderer compatibility](docs/RENDERERS.md)
before choosing a Workers deployment path.

## Custom renderers

The htmx selection layer depends on the async generic `Renderer[ViewT]`
protocol. The same view type is required for both page and fragment targets:

```python
from collections.abc import Mapping

from hayate_htmx import HtmxTemplates, Renderer

class MyRenderer:
    async def render(
        self,
        view: str,
        context: Mapping[str, object],
    ) -> str: ...

renderer: Renderer[str] = MyRenderer()
templates = HtmxTemplates(renderer)
```

`TemplateRenderer` remains available as the compatible specialization for
string template names during the 0.x transition.

## Handler integration

```python
from hayate import Hayate
from hayate_htmx import HtmxRequest, with_htmx

app = Hayate()

@app.post("/app/todos")
async def create_todo(c):
    hx = HtmxRequest.from_context(c)
    todo_id = "42"

    if not hx.is_htmx:
        return c.redirect(f"/app/todos/{todo_id}")

    return with_htmx(
        c.html(f'<li id="todo-{todo_id}">Created</li>'),
        retarget="#todo-list",
        reswap="beforeend",
        trigger={"todo:created": {"id": todo_id}},
    )
```

`with_htmx()` mutates the supplied response headers and returns the same
`hayate.Response`, so it composes with every Hayate adapter and test path.

## Request metadata

```python
hx = HtmxRequest(c.req)

hx.is_htmx          # HX-Request
hx.boosted          # HX-Boosted
hx.current_url      # HX-Current-URL
hx.history_restore  # HX-History-Restore-Request (htmx 2)
hx.target           # HX-Target
hx.trigger          # HX-Trigger (htmx 2)
hx.trigger_name     # HX-Trigger-Name (htmx 2)
hx.request_type     # HX-Request-Type: "full" | "partial" (htmx 4)
hx.source           # HX-Source (htmx 4)
```

Unknown `HX-Request-Type` values are returned as `None`; callers therefore
cannot accidentally treat a future value as one of the two currently
documented htmx 4 modes.

## Response controls

`with_htmx()` and `HtmxResponseHeaders` support:

- `HX-Location`
- `HX-Push-Url`
- `HX-Redirect`
- `HX-Refresh`
- `HX-Replace-Url`
- `HX-Reswap`
- `HX-Retarget`
- `HX-Reselect`
- `HX-Trigger`

Structured `HX-Location` and `HX-Trigger` values use compact, deterministic
JSON. A sequence of trigger names becomes the comma-separated event form.

```python
from hayate_htmx import HtmxResponseHeaders

controls = HtmxResponseHeaders(
    push_url="/app/todos",
    trigger=("todo:created", "notifications:refresh"),
)
return controls.apply(c.html("<li>Created</li>"))
```

`c.html()` and custom renderers do not gain automatic escaping. The safety
guarantee applies to values rendered through the included `JinjaRenderer`;
applications must still avoid concatenating untrusted strings into HTML.

## Development

```sh
uv sync --locked
uv run ruff check src examples tests typing_tests
uv run ruff format --check src examples tests typing_tests
uv run mypy src examples tests typing_tests
uv run pytest -q
```

For the real-browser release gate:

```sh
uv run playwright install chromium
HAYATE_HTMX_BROWSER_TESTS=1 uv run pytest -m browser -q
```
