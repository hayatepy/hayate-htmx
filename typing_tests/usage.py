from typing import assert_type

from hayate import Context, Request, Response

from hayate_htmx import (
    HtmxRequest,
    HtmxTemplates,
    JinjaRenderer,
    Renderer,
    RequestType,
    TemplateRenderer,
    with_htmx,
)
from hayate_htmx.htpy import HtpyRenderer, HtpyView
from hayate_htmx.jx import JxRenderer

hx = HtmxRequest(Request("https://example.test/"))

assert_type(hx.is_htmx, bool)
assert_type(hx.request_type, RequestType | None)
assert_type(hx.source, str | None)
assert_type(
    with_htmx(Response(), retarget="#main", trigger={"loaded": {"id": "42"}}),
    Response,
)

renderer: TemplateRenderer = JinjaRenderer("templates")
templates: HtmxTemplates[str] = HtmxTemplates(renderer)
htpy_renderer: Renderer[HtpyView] = HtpyRenderer()
htpy_templates: HtmxTemplates[HtpyView] = HtmxTemplates(htpy_renderer)
jx_renderer: Renderer[str] = JxRenderer("components")
jx_templates: HtmxTemplates[str] = HtmxTemplates(jx_renderer)


async def render_todos(c: Context) -> Response:
    return await templates.render(
        c,
        page="todos/page.html",
        fragment="todos/_list.html",
        values={"todos": ["Ship it"]},
    )
