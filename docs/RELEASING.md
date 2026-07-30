# Releasing hayate-htmx

The release workflow builds from a tag, verifies version consistency, runs the
test and audit gates, builds wheel and source archives, generates an SPDX JSON
SBOM, and attests both artifacts and SBOM through GitHub's OIDC provenance.
Publishing uses PyPI Trusted Publishing; no long-lived PyPI token is stored.

## One-time repository setup

Configure a PyPI pending publisher or project publisher with:

- owner: `hayatepy`
- repository: `hayate-htmx`
- workflow: `release.yml`
- environment: `pypi`

Protect the `pypi` environment and enable GitHub private vulnerability
reporting.

For the initial publication, preserve the immutable order:

1. rerun the existing signed `v0.1.0` workflow after saving the pending
   publisher;
2. verify `hayate-htmx==0.1.0` from the public index;
3. create signed `v0.2.0` only from the reviewed current main commit.

Never move `v0.1.0`, and never create `v0.2.0` before the first public project
exists.

## Release checklist

1. Confirm `CHANGELOG.md` describes the release.
2. Confirm `pyproject.toml`, `hayate_htmx.__version__`, and `uv.lock` all
   contain the intended version.
3. Run:

   ```sh
   uv sync --locked
   uv run ruff check src examples tests typing_tests
   uv run ruff format --check src examples tests typing_tests
   uv run mypy src examples tests typing_tests
   uv run pytest -q
   uv build
   uv run --with pip-audit==2.10.0 pip-audit
   uvx zizmor==1.28.0 .github/workflows
   ```

4. Run the Chromium smoke path documented in the golden example.
5. Merge only with all blocking GitHub checks green.
6. Create and push an annotated `v<version>` tag from the reviewed merge commit.
   Do not move or reuse a published tag.
7. Verify the release workflow's PyPI publish, attestations, SPDX SBOM, and
   GitHub release assets.
8. Install the wheel from PyPI into a clean environment and run the README
   example.

The workflow refuses a tag whose name differs from the package version.
