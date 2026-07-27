from typing import cast

import pytest
from hayate import Hayate, Response

from hayate_htmx import HtmxResponseHeaders, TriggerValue, with_htmx


def test_applies_every_response_control_to_the_same_response() -> None:
    response = Response("created", headers={"x-existing": "preserved"})

    returned = with_htmx(
        response,
        location={"target": "#main", "path": "/app/todos"},
        push_url="/app/todos",
        redirect="/sign-in",
        refresh=True,
        replace_url=False,
        reswap="beforeend",
        retarget="#todo-list",
        reselect="#created",
        trigger={"todo:created": {"visible": True, "id": "42"}},
    )

    assert returned is response
    assert response.headers.get("x-existing") == "preserved"
    assert response.headers.get("hx-location") == '{"path":"/app/todos","target":"#main"}'
    assert response.headers.get("hx-push-url") == "/app/todos"
    assert response.headers.get("hx-redirect") == "/sign-in"
    assert response.headers.get("hx-refresh") == "true"
    assert response.headers.get("hx-replace-url") == "false"
    assert response.headers.get("hx-reswap") == "beforeend"
    assert response.headers.get("hx-retarget") == "#todo-list"
    assert response.headers.get("hx-reselect") == "#created"
    assert response.headers.get("hx-trigger") == ('{"todo:created":{"id":"42","visible":true}}')


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("todo:created", "todo:created"),
        (("todo:created", "notifications:refresh"), "todo:created, notifications:refresh"),
        (
            {"todo:created": {"id": "日本語"}},
            '{"todo:created":{"id":"\\u65e5\\u672c\\u8a9e"}}',
        ),
    ],
)
def test_trigger_wire_formats(value: TriggerValue, expected: str) -> None:
    response = HtmxResponseHeaders(trigger=value).apply(Response())

    assert response.headers.get("hx-trigger") == expected


def test_rejects_empty_or_invalid_trigger_sequences() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        with_htmx(Response(), trigger=cast(TriggerValue, []))

    with pytest.raises(TypeError, match="non-empty strings"):
        with_htmx(Response(), trigger=cast(TriggerValue, [1]))


def test_rejects_non_finite_structured_values() -> None:
    with pytest.raises(ValueError, match="Out of range float values"):
        with_htmx(Response(), trigger={"metric": {"value": float("nan")}})


async def test_integrates_with_a_hayate_handler() -> None:
    app = Hayate()

    @app.post("/")
    async def create(c):  # type: ignore[no-untyped-def]
        return with_htmx(
            c.html('<li id="todo-42">Created</li>'),
            retarget="#todo-list",
            trigger=("todo:created", "count:refresh"),
        )

    response = await app.request("/", method="POST", headers={"HX-Request": "true"})

    assert response.status == 200
    assert response.headers.get("content-type") == "text/html;charset=utf-8"
    assert response.headers.get("hx-retarget") == "#todo-list"
    assert response.headers.get("hx-trigger") == "todo:created, count:refresh"
    assert await response.text() == '<li id="todo-42">Created</li>'
