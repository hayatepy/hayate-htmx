# Authentication and CSRF integration

The golden app uses `hayate-auth` as the owner of authentication state and
cookie behavior. `hayate-htmx` does not define a second session or CSRF model.

## Session boundary

`Auth.register(app)` mounts the JSON authentication API. Successful sign-up or
sign-in responses set the `hayate-auth` session cookie; the golden form adapter
copies every `Set-Cookie` header unchanged onto its redirect. Protected routes
use `auth.require_session()`, which exposes the current public `user` and
`session` on the Hayate context.

Application records must be scoped by `c.get("user")["id"]` on every read and
write. Treating a TODO ID as globally authorizing is an insecure direct object
reference; the example store therefore requires the user ID for get, update,
toggle, and delete.

## CSRF

`hayate-auth` uses a layered browser-native defense:

1. session cookies are `HttpOnly` and `SameSite=Lax`;
2. unsafe authentication requests check `Origin`;
3. when `Origin` is absent, Fetch Metadata (`Sec-Fetch-Site`) is checked.

The same `hayate_auth.csrf.is_allowed()` predicate protects the golden app's
authenticated POST, PATCH, and DELETE routes. htmx sends normal same-origin
browser requests, so no token needs to be embedded in HTML.

Do not manufacture a trusted `Origin` when adapting a form to the auth JSON
API. Forward the browser's original `Origin`, `Sec-Fetch-Site`, and `Cookie`
headers, as the golden app does. Cross-origin requests must reach
`hayate-auth` with their untrusted origin intact so they are rejected.

For a cross-origin frontend, enumerate exact trusted origins in the `Auth`
configuration, configure cookie behavior deliberately, and add a separate
integration test. Do not use a wildcard origin with ambient credentials.

## Deployment

- Set a high-entropy `AUTH_SECRET`; never deploy the checked-in development
  fallback.
- Serve over HTTPS so `hayate-auth` can issue the `__Host-` cookie.
- Persist the auth adapter database and apply the matching `hayate-auth`
  schema before serving traffic.
- Rate-limit sign-up and sign-in endpoints.
- Keep the example CSP or replace it with an equally strict policy.
