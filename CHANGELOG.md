# Changelog

All notable changes to hayate-htmx are documented here.

## Unreleased

## [0.2.0] - 2026-07-30

### Added

- Add an engine-neutral, generic `Renderer[ViewT]` boundary while preserving
  the existing string-based `TemplateRenderer` protocol.
- Add optional htpy 26.x, Jx 0.11.x, and experimental Python 3.14 tdom 0.1.x
  adapters with shared page/fragment, htmx 2/4, escaping, and response
  contract tests.
- Add `htpy`, `jx`, `tdom`, and environment-aware `all` package extras.
- Pin the current Pyodide-compatible MarkupSafe wheel only on Emscripten and
  prove htpy rendering, escaping, page/fragment selection, and response
  headers through real workerd.

### Changed

- Route package discovery, start, and tested-compatibility links through
  `hayatepy.dev`, including the PyPI project homepage.
- Update the documented scaffold command to the released `create-hayate`
  0.13.2.

## [0.1.0] - 2026-07-27

### Added

- Add a typed view over htmx 2 and 4 request metadata.
- Add response controls for htmx location, history, redirect, swap, target,
  selection, refresh, and event headers.
- Add compact deterministic JSON encoding for structured response controls.
- Add engine-independent full-page/fragment selection for htmx 2 and 4.
- Add a Jinja renderer with HTML autoescaping enabled by default.
- Add representation-safe `Vary` composition and normalized missing-template
  errors.
- Add an identity-scoped full-stack TODO reference app with accessible CRUD,
  history navigation, and SSE token streaming.
- Vendor and integrity-pin the production htmx 2.0.10 browser asset.
- Add Chromium smoke tests, Hayate compatibility checks, an observational
  htmx 4 lane, release attestations, and an SPDX SBOM gate.
- Add authentication, CSRF, compatibility, asset, security, and release
  guidance.
