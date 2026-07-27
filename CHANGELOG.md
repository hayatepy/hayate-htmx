# Changelog

All notable changes to hayate-htmx are documented here.

## Unreleased

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
