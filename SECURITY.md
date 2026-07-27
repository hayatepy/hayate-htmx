# Security Policy

## Supported versions

The latest 0.x release receives security fixes. After 1.0, the latest minor
release of the newest major version will be supported.

## Reporting a vulnerability

Use GitHub private vulnerability reporting on this repository
(**Security → Report a vulnerability**). Do not open a public issue with
exploit details.

You can expect an initial response within seven days. Resolved reports are
released as patch versions and noted in the changelog after users have a safe
upgrade path.

## Scope notes

`JinjaRenderer` enables autoescaping, but it cannot make manually concatenated
HTML safe. Authentication and session security remain the responsibility of
`hayate-auth` and the application deployment. See `docs/AUTH.md` for the
reference integration and required production settings.
