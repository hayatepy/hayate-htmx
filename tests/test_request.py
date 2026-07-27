from hayate import Hayate, Request

from hayate_htmx import HtmxRequest


def test_request_defaults_without_htmx_headers() -> None:
    hx = HtmxRequest(Request("https://example.test/app"))

    assert hx.is_htmx is False
    assert hx.boosted is False
    assert hx.current_url is None
    assert hx.history_restore is False
    assert hx.target is None
    assert hx.trigger is None
    assert hx.trigger_name is None
    assert hx.request_type is None
    assert hx.source is None


def test_reads_htmx_2_and_4_metadata() -> None:
    hx = HtmxRequest(
        Request(
            "https://example.test/app",
            headers={
                "HX-Request": "TRUE",
                "HX-Boosted": "true",
                "HX-Current-URL": "https://example.test/app?page=2",
                "HX-History-Restore-Request": "true",
                "HX-Target": "div#results",
                "HX-Trigger": "submit",
                "HX-Trigger-Name": "save",
                "HX-Request-Type": "partial",
                "HX-Source": "button#submit",
            },
        )
    )

    assert hx.is_htmx is True
    assert hx.boosted is True
    assert hx.current_url == "https://example.test/app?page=2"
    assert hx.history_restore is True
    assert hx.target == "div#results"
    assert hx.trigger == "submit"
    assert hx.trigger_name == "save"
    assert hx.request_type == "partial"
    assert hx.source == "button#submit"


def test_rejects_unknown_request_type() -> None:
    hx = HtmxRequest(
        Request("https://example.test/app", headers={"HX-Request-Type": "future-mode"})
    )

    assert hx.request_type is None


async def test_builds_from_real_hayate_context() -> None:
    app = Hayate()

    @app.get("/")
    async def index(c):  # type: ignore[no-untyped-def]
        hx = HtmxRequest.from_context(c)
        return c.json(
            {
                "is_htmx": hx.is_htmx,
                "request_type": hx.request_type,
                "source": hx.source,
            }
        )

    response = await app.request(
        "/",
        headers={
            "HX-Request": "true",
            "HX-Request-Type": "full",
            "HX-Source": "a#home",
        },
    )

    assert await response.json() == {
        "is_htmx": True,
        "request_type": "full",
        "source": "a#home",
    }
