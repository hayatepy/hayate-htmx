"""Identity-scoped CRUD and streaming with Hayate, hayate-auth, and htmx."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from typing import Any

from hayate import Context, Hayate, HTTPException, Next, Request, Response, SSEMessage
from hayate.middleware import static_files
from hayate_auth import Auth
from hayate_auth.adapters.sqlite import SQLiteAdapter
from hayate_auth.csrf import is_allowed

from hayate_htmx import (
    HtmxTemplates,
    JinjaRenderer,
    append_htmx_vary,
    with_htmx,
)

_ROOT = Path(__file__).parent
_FILTERS = frozenset({"all", "open", "done"})
_DEV_SECRET = "development-only-change-me-before-deploying"


@dataclass(slots=True)
class Todo:
    id: str
    title: str
    done: bool = False


class TodoStore:
    """Small in-memory store whose every operation is scoped by user ID."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Todo]] = {}
        self._ids = count(1)

    def list(self, user_id: str, selected_filter: str = "all") -> list[Todo]:
        todos = list(self._items.get(user_id, {}).values())
        if selected_filter == "open":
            return [todo for todo in todos if not todo.done]
        if selected_filter == "done":
            return [todo for todo in todos if todo.done]
        return todos

    def get(self, user_id: str, todo_id: str) -> Todo | None:
        return self._items.get(user_id, {}).get(todo_id)

    def create(self, user_id: str, title: str) -> Todo:
        todo = Todo(id=str(next(self._ids)), title=title)
        self._items.setdefault(user_id, {})[todo.id] = todo
        return todo

    def update(self, user_id: str, todo_id: str, title: str) -> Todo | None:
        todo = self.get(user_id, todo_id)
        if todo is not None:
            todo.title = title
        return todo

    def toggle(self, user_id: str, todo_id: str) -> Todo | None:
        todo = self.get(user_id, todo_id)
        if todo is not None:
            todo.done = not todo.done
        return todo

    def delete(self, user_id: str, todo_id: str) -> bool:
        items = self._items.get(user_id)
        return items is not None and items.pop(todo_id, None) is not None


def _title_error(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "Enter a title before adding the task."
    if len(value.strip()) > 120:
        return "Keep the title to 120 characters or fewer."
    return None


def _selected_filter(c: Context) -> str:
    value = c.req.query("filter") or "all"
    return value if value in _FILTERS else "all"


def _user(c: Context) -> dict[str, Any]:
    user = c.get("user")
    if not isinstance(user, dict) or not isinstance(user.get("id"), str):
        raise RuntimeError("authenticated route has no user")
    return user


def _copy_auth_cookies(source: Response, target: Response) -> Response:
    for cookie in source.headers.set_cookie_list():
        target.headers.append("set-cookie", cookie)
    return target


def create_app(
    *,
    database: str | os.PathLike[str] = ":memory:",
    auth_secret: str = _DEV_SECRET,
) -> Hayate:
    """Build an isolated golden app; tests provide a temporary database."""
    adapter = SQLiteAdapter(str(database))
    adapter.create_tables()
    auth = Auth(secret=auth_secret, adapter=adapter)
    store = TodoStore()
    renderer = JinjaRenderer(_ROOT / "templates")
    pages = HtmxTemplates(renderer)
    app = Hayate()

    async def security_headers(c: Context, next_: Next) -> None:
        await next_()
        response = c.res
        if response is None:
            return
        response.headers.set(
            "content-security-policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'",
        )
        response.headers.set("referrer-policy", "same-origin")
        response.headers.set("x-content-type-options", "nosniff")
        if c.req.url.pathname.startswith("/static/vendor/"):
            response.headers.set("cache-control", "public, max-age=31536000, immutable")

    async def csrf_guard(c: Context, next_: Next) -> None:
        if not is_allowed(c.req.raw, frozenset()):
            raise HTTPException(403, title="Cross-origin request rejected")
        await next_()

    app.use(security_headers)
    app.use(
        "/static/*",
        static_files(root=_ROOT / "static", strip_prefix="/static"),
    )
    auth.register(app)

    async def render_login(c: Context, *, error: str | None = None, status: int = 200) -> Response:
        html = await renderer.render("login.html", {"error": error})
        return c.html(html, status)

    async def proxy_auth_form(c: Context, endpoint: str) -> Response:
        form = await c.req.form_data()
        email = form.get("email")
        password = form.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            return await render_login(c, error="Email and password are required.", status=422)

        forwarded_headers: dict[str, str] = {"content-type": "application/json"}
        for name in ("origin", "sec-fetch-site", "cookie"):
            value = c.req.header(name)
            if value is not None:
                forwarded_headers[name] = value
        request = Request(
            f"{c.req.url.origin}{auth.base_path}/{endpoint}",
            method="POST",
            headers=forwarded_headers,
            body=json.dumps({"email": email, "password": password}),
        )
        auth_response = await auth.fetch(request)
        if auth_response.ok:
            return _copy_auth_cookies(auth_response, c.redirect("/todos", 303))

        problem = await auth_response.json()
        title = problem.get("title") if isinstance(problem, dict) else None
        message = title if isinstance(title, str) else "Authentication failed."
        return await render_login(c, error=message, status=auth_response.status)

    @app.get("/")
    @app.get("/login")
    async def login(c: Context) -> Response:
        if await auth.get_session(c.req.raw) is not None:
            return c.redirect("/todos")
        return await render_login(c)

    @app.post("/session/sign-up")
    async def sign_up(c: Context) -> Response:
        return await proxy_auth_form(c, "sign-up/email")

    @app.post("/session/sign-in")
    async def sign_in(c: Context) -> Response:
        return await proxy_auth_form(c, "sign-in/email")

    @app.post("/session/sign-out")
    async def sign_out(c: Context) -> Response:
        headers: dict[str, str] = {"content-type": "application/json"}
        for name in ("origin", "sec-fetch-site", "cookie"):
            value = c.req.header(name)
            if value is not None:
                headers[name] = value
        request = Request(
            f"{c.req.url.origin}{auth.base_path}/sign-out",
            method="POST",
            headers=headers,
            body="{}",
        )
        auth_response = await auth.fetch(request)
        if not auth_response.ok:
            return auth_response
        return _copy_auth_cookies(auth_response, c.redirect("/login", 303))

    def page_values(c: Context) -> dict[str, object]:
        user = _user(c)
        selected_filter = _selected_filter(c)
        return {
            "current_filter": selected_filter,
            "todos": store.list(user["id"], selected_filter),
            "user": user,
        }

    @app.get("/todos", auth.require_session())
    async def list_todos(c: Context) -> Response:
        return await pages.render(
            c,
            page="todos/page.html",
            fragment="todos/_list.html",
            values=page_values(c),
        )

    @app.get("/todos/stream", auth.require_session())
    async def stream_demo(c: Context) -> Response:
        async def tokens() -> AsyncIterator[SSEMessage]:
            for token in (
                "Hypermedia",
                " answers",
                ", one",
                " safe",
                " token",
                " at",
                " a",
                " time.",
            ):
                await asyncio.sleep(0.01)
                yield {"event": "token", "data": {"token": token}}
            yield {"event": "done", "data": "complete"}

        return c.event_stream(tokens(), headers={"x-accel-buffering": "no"})

    @app.post("/todos", csrf_guard, auth.require_session())
    async def create_todo(c: Context) -> Response:
        form = await c.req.form_data()
        raw_title = form.get("title")
        error = _title_error(raw_title)
        if error is not None:
            html = await renderer.render("todos/_create_error.html", {"error": error})
            response = append_htmx_vary(c.html(html))
            return with_htmx(
                response,
                retarget="#todo-form-errors",
                reswap="innerHTML",
            )

        assert isinstance(raw_title, str)
        todo = store.create(_user(c)["id"], raw_title.strip())
        response = await pages.render(
            c,
            page="todos/page.html",
            fragment="todos/_list.html",
            values=page_values(c),
            status=201,
        )
        return with_htmx(response, trigger={"todo:created": {"id": todo.id}})

    @app.get("/todos/:id/edit", auth.require_session())
    async def edit_todo(c: Context) -> Response:
        todo = store.get(_user(c)["id"], c.req.param("id") or "")
        if todo is None:
            return c.not_found()
        html = await renderer.render("todos/_edit.html", {"error": None, "todo": todo})
        return c.html(html)

    @app.patch("/todos/:id", csrf_guard, auth.require_session())
    async def update_todo(c: Context) -> Response:
        user_id = _user(c)["id"]
        todo_id = c.req.param("id") or ""
        todo = store.get(user_id, todo_id)
        if todo is None:
            return c.not_found()
        form = await c.req.form_data()
        raw_title = form.get("title")
        error = _title_error(raw_title)
        if error is not None:
            html = await renderer.render("todos/_edit.html", {"error": error, "todo": todo})
            return with_htmx(
                c.html(html),
                retarget=f"#todo-{todo.id}",
                reswap="outerHTML",
            )

        assert isinstance(raw_title, str)
        store.update(user_id, todo_id, raw_title.strip())
        html = await renderer.render(
            "todos/_item.html",
            {"current_filter": _selected_filter(c), "todo": todo},
        )
        return c.html(html)

    @app.patch("/todos/:id/toggle", csrf_guard, auth.require_session())
    async def toggle_todo(c: Context) -> Response:
        if store.toggle(_user(c)["id"], c.req.param("id") or "") is None:
            return c.not_found()
        html = await renderer.render("todos/_list.html", page_values(c))
        return c.html(html)

    @app.delete("/todos/:id", csrf_guard, auth.require_session())
    async def delete_todo(c: Context) -> Response:
        if not store.delete(_user(c)["id"], c.req.param("id") or ""):
            return c.not_found()
        html = await renderer.render("todos/_list.html", page_values(c))
        return c.html(html)

    return app


app = create_app(
    database=os.environ.get("HAYATE_HTMX_EXAMPLE_DB", ":memory:"),
    auth_secret=os.environ.get("AUTH_SECRET", _DEV_SECRET),
)
