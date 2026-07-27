# Golden Hayate + htmx application

This application is the release-gate reference path for `hayate-htmx`. It
combines:

- Hayate request/response routing and SSE;
- `hayate-auth` email/password sessions;
- identity-scoped TODO CRUD;
- Jinja autoescaping;
- htmx page/fragment selection and history;
- a self-hosted, reviewed htmx 2.x asset;
- accessible validation fragments;
- strict same-origin security headers and CSP.

## Run

From the repository root:

```sh
uv sync --locked
export AUTH_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export HAYATE_HTMX_EXAMPLE_DB="./example.db"
uv run uvicorn examples.golden.app:app --reload
```

Open <http://127.0.0.1:8000/login>, create an account, and use the task app.
The checked-in development fallback secret is only for a zero-configuration
local launch. A deployment must set `AUTH_SECRET`.

## Test

Direct request, security, streaming, and asset-integrity tests are part of the
normal suite:

```sh
uv run pytest -q
```

The browser smoke path needs Chromium once:

```sh
uv run playwright install chromium
HAYATE_HTMX_BROWSER_TESTS=1 uv run pytest -m browser -q
```

The smoke test covers account creation, validation, create/edit/delete,
history navigation, SSE token streaming, same-origin asset loading, browser
console errors, and network failures.

See [authentication guidance](../../docs/AUTH.md),
[asset policy](../../docs/ASSETS.md), and
[compatibility policy](../../docs/COMPATIBILITY.md).
