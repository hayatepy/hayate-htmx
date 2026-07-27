from typing import assert_type

from hayate import Request, Response

from hayate_htmx import HtmxRequest, RequestType, with_htmx

hx = HtmxRequest(Request("https://example.test/"))

assert_type(hx.is_htmx, bool)
assert_type(hx.request_type, RequestType | None)
assert_type(hx.source, str | None)
assert_type(
    with_htmx(Response(), retarget="#main", trigger={"loaded": {"id": "42"}}),
    Response,
)
