# hayate-htmx

> **Hayate ecosystem:** [Start here](https://github.com/hayatepy/.github/blob/main/docs/START.md)
> · [Hayate](https://github.com/hayatepy/hayate)
> · [Frontend roadmap](https://github.com/hayatepy/roadmap/issues/10)

Typed server integration between [Hayate](https://github.com/hayatepy/hayate)
and [htmx](https://htmx.org).

`hayate-htmx` keeps htmx-specific request and response behavior outside the
standards-first Hayate core. The first layer has no template-engine or browser
asset dependency: it reads the `HX-*` request contract and applies `HX-*`
response controls to ordinary Hayate responses.

> **Status: alpha (0.1.x).** htmx 2.x is the stable production contract.
> htmx 4 request metadata is accepted additively while htmx 4 remains a
> pre-release. Template and fragment rendering is tracked separately in
> [issue #2](https://github.com/hayatepy/hayate-htmx/issues/2).

## Install

```sh
uv add hayate-htmx
```

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

This package does not escape or sanitize HTML. Until the safe renderer lands,
applications must use an autoescaping template engine and must not concatenate
untrusted values into `c.html()`.

## Development

```sh
uv sync --locked
uv run ruff check src tests typing_tests
uv run ruff format --check src tests typing_tests
uv run mypy src tests typing_tests
uv run pytest -q
```

