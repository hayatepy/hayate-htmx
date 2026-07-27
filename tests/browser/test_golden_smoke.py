from __future__ import annotations

import asyncio
import os
import socket
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
import uvicorn
from examples.golden.app import create_app
from playwright.async_api import Page, async_playwright

pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(
        os.environ.get("HAYATE_HTMX_BROWSER_TESTS") != "1",
        reason="set HAYATE_HTMX_BROWSER_TESTS=1 after installing Chromium",
    ),
]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest_asyncio.fixture
async def live_url(tmp_path: Path) -> AsyncIterator[str]:
    port = _free_port()
    app = create_app(database=tmp_path / "browser.db", auth_secret="browser-secret")
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            log_level="warning",
        )
    )
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.02)
    else:
        server.should_exit = True
        await task
        raise RuntimeError("test server did not start")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task


async def _assert_htmx_ready(page: Page) -> None:
    await page.wait_for_function("window.htmx && window.htmx.version")
    expected = os.environ.get("HAYATE_HTMX_EXPECTED_VERSION", "2.0.10")
    assert await page.evaluate("window.htmx.version") == expected


async def test_navigation_crud_validation_history_and_stream(live_url: str) -> None:
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    request_urls: list[str] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text) if message.type == "error" else None
            ),
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: request_failures.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )
        page.on("request", lambda request: request_urls.append(request.url))

        await page.goto(f"{live_url}/login")
        await page.locator("#sign-up-email").fill("browser@example.test")
        await page.locator("#sign-up-password").fill("correct horse battery staple")
        await page.get_by_role("button", name="Create account").click()
        await page.wait_for_url(f"{live_url}/todos")
        await _assert_htmx_ready(page)

        create_form = page.locator("#todo-create")
        await create_form.get_by_label("What needs doing?").fill("   ")
        await create_form.get_by_role("button", name="Add task").click()
        await page.get_by_role("alert").wait_for()
        assert "Enter a title" in await page.get_by_role("alert").inner_text()

        await create_form.get_by_label("What needs doing?").fill("First task")
        await create_form.get_by_role("button", name="Add task").click()
        item = page.locator("#todo-1")
        await item.wait_for()
        assert "First task" in await item.inner_text()

        await item.get_by_role("button", name="Edit").click()
        editing = page.locator("#todo-1")
        await editing.get_by_label("Title").fill("Renamed task")
        await editing.get_by_role("button", name="Save").click()
        item = page.locator("#todo-1")
        await item.get_by_text("Renamed task").wait_for()

        await page.get_by_role("link", name="Completed").click()
        await page.wait_for_url(f"{live_url}/todos?filter=done")
        assert await page.locator("#todo-list").get_attribute("data-filter") == "done"
        await page.go_back()
        await page.wait_for_url(f"{live_url}/todos")
        await page.get_by_text("Renamed task").wait_for()

        await page.get_by_role("button", name="Run stream demo").click()
        output = page.locator("#stream-output")
        await output.get_by_text(
            "Hypermedia answers, one safe token at a time.",
            exact=True,
        ).wait_for()

        item = page.locator("#todo-1")
        await item.get_by_role("button", name="Delete").click()
        await item.wait_for(state="detached")

        assert console_errors == []
        assert page_errors == []
        assert request_failures == []
        assert all(url.startswith(live_url) or url.startswith("data:") for url in request_urls)
        assert any(url.endswith("/static/vendor/htmx-2.0.10.min.js") for url in request_urls)

        await context.close()
        await browser.close()
