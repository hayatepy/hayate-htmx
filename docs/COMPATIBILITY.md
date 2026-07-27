# Compatibility policy

## Production contract

| Component | Supported contract |
| --- | --- |
| Python | 3.12, 3.13, 3.14 |
| Hayate | 0.12.x and the latest compatible release |
| htmx | 2.0.10 |
| Jinja | 3.1.x |
| ASGI browser lane | Chromium through Playwright |

The normal CI matrix runs formatting, strict typing, direct request tests,
ASGI tests, package builds, dependency audit, and workflow audit on every
supported Python version. The browser workflow runs the production htmx 2.x
contract against the complete golden path.

## htmx 4 observation

htmx 4 is not a production compatibility promise in 0.1. The server accepts
the additive `HX-Request-Type: full | partial` and `HX-Source` metadata so
applications can experiment without changing their Hayate handlers.

The observational CI lane replaces only the vendored browser asset with the
pinned htmx 4.0.0-beta5 build and runs the browser smoke test with
`continue-on-error`.
Its result is evidence for future work, not a release blocker.

Known differences to review before declaring support:

- htmx 4 is prerelease software and its wire contract can still change;
- several htmx 2 request headers have changed or been removed in htmx 4;
- applications must treat `HX-Request-Type` as the representation authority;
- extensions and response handling need a separate migration review.

Do not silently serve htmx 4 to production applications expecting the 2.x
header set.
