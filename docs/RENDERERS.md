# Renderer compatibility

`hayate-htmx` selects a complete page or fragment before it asks a renderer to
produce HTML. Request metadata, htmx 2 history restoration, htmx 4 full or
partial selection, status, response headers, content type, and `Vary` are
therefore identical across rendering engines.

## Support matrix

| Adapter | Package line | Python | CPython/ASGI | Workers |
| --- | --- | --- | --- | --- |
| `JinjaRenderer` | Jinja2 3.1.x | 3.12+ | supported | proven by the golden application |
| `HtpyRenderer` | htpy 26.x | 3.12+ | supported | supported; real workerd gate |
| `JxRenderer` | Jx 0.11.x | 3.12+ | supported | not yet claimed |
| `TdomRenderer` | tdom 0.1.x | 3.14+ | experimental | not yet claimed |

“Not yet claimed” is deliberate. CPython unit tests are not evidence that a
package imports and renders correctly through Pywrangler/Pyodide. htpy passes
the real-workerd lane with the Emscripten-only MarkupSafe wheel constraint;
each remaining optional adapter needs equivalent evidence before this table
changes.

## htpy

Install with:

```sh
uv add "hayate-htmx[htpy]"
```

`HtpyRenderer` accepts a prebuilt `htpy.Renderable` or a component factory
whose single argument is the values mapping. A factory may return a renderable
synchronously or asynchronously. Rendering always consumes
`aiter_chunks()`, so async child components are awaited rather than forced
through `str()`.

```python
from collections.abc import Mapping

from htpy import Renderable, h1
from hayate_htmx.htpy import HtpyRenderer

def heading(values: Mapping[str, object]) -> Renderable:
    return h1[str(values["title"])]

html = await HtpyRenderer().render(heading, {"title": "Hello"})
```

htpy escapes string children. Raw markup requires htpy/MarkupSafe's explicit
safe-markup operation.

## Jx

Install with:

```sh
uv add "hayate-htmx[jx]"
```

`JxRenderer` accepts either a component folder or an existing `jx.Catalog`.
The catalog instance is retained across requests so component indexes, props,
slots, and asset dependency state are not rebuilt for every render.

```python
from hayate_htmx.jx import JxRenderer

renderer = JxRenderer("components", auto_reload=False)
html = await renderer.render("pages/todos.jx", {"todos": ["Ship it"]})
```

Jx's default environment has HTML autoescaping enabled. A missing component is
normalized to `hayate_htmx.jx.ComponentNotFoundError`, whose
`component_name` preserves the requested identity.

## tdom

Install on Python 3.14 or newer:

```sh
uv add "hayate-htmx[tdom]"
```

`TdomRenderer` accepts a prebuilt `string.templatelib.Template` or a sync/async
factory that returns one. The base `hayate_htmx` package never imports tdom.
Importing `hayate_htmx.tdom` on Python 3.12 or 3.13 instead raises an
actionable Python-version error.

tdom is pre-alpha and remains experimental. Its interpolations escape
untrusted values by default; raw markup requires tdom's explicit safe
operation.
