"""Run the optional htpy renderer through real workerd/Pyodide."""

from __future__ import annotations

import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VARY = "HX-Request, HX-History-Restore-Request, HX-Request-Type"


def _write_project(project: Path) -> Path:
    source = project / "src"
    source.mkdir()
    shutil.copytree(ROOT / "src" / "hayate_htmx", source / "hayate_htmx")
    (project / "pyproject.toml").write_text(
        """[project]
name = "hayate-htmx-workerd-contract"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
  "hayate>=0.12,<0.13",
  "htpy>=26.5,<27",
  "jinja2>=3.1.6,<4",
  "markupsafe==3.0.2; sys_platform == 'emscripten' and python_version < '3.14'",
]

[dependency-groups]
dev = ["workers-py>=1.15,<2"]
""",
        encoding="utf-8",
    )
    (project / "wrangler.toml").write_text(
        """name = "hayate-htmx-workerd-contract"
main = "src/entry.py"
compatibility_date = "2026-07-01"
compatibility_flags = ["python_workers"]

[python_modules]
exclude = [
  "**/*.pyc",
  "**/__pycache__/**",
  "**/*.dist-info/**",
  "asgi.py",
  "hayate/adapters/asgi.py",
  "hayate/adapters/aws.py",
  "workers/wsgi.py",
]
""",
        encoding="utf-8",
    )
    (source / "entry.py").write_text(
        """from collections.abc import Mapping

from hayate import Context, Hayate, Response
from hayate.adapters.workers import to_workers
from htpy import Renderable, body, h1, html

from hayate_htmx import HtmxTemplates
from hayate_htmx.htpy import HtpyRenderer, HtpyView


async def page(values: Mapping[str, object]) -> Renderable:
    return html[body[h1[str(values["value"])]]]


def fragment(values: Mapping[str, object]) -> Renderable:
    return h1[str(values["value"])]


views: HtmxTemplates[HtpyView] = HtmxTemplates(HtpyRenderer())
app = Hayate()


@app.get("/")
async def index(c: Context) -> Response:
    return await views.render(
        c,
        page=page,
        fragment=fragment,
        values={"value": "<script>alert(1)</script>"},
    )


Default = to_workers(app)
""",
        encoding="utf-8",
    )

    shim = project / "node-shim" / "node"
    shim.parent.mkdir()
    shim.write_text(
        "#!/bin/sh\nexec "
        f"{shlex.quote(sys.executable)} {shlex.quote(str(ROOT / 'scripts/node_compat.py'))} "
        '"$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return shim.parent


def _run(command: list[str], *, cwd: Path, environment: dict[str, str]) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _fetch(url: str, *, htmx: bool = False) -> tuple[str, str, str]:
    request = Request(url, headers={"HX-Request": "true"} if htmx else {})
    with urlopen(request, timeout=2) as response:
        return (
            response.read().decode(),
            response.headers.get("Content-Type", ""),
            response.headers.get("Vary", ""),
        )


def _wait_for_server(process: subprocess.Popen[str], url: str) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout is not None else ""
            raise RuntimeError(f"workerd exited before readiness\n{output}")
        try:
            _fetch(url)
            return
        except (URLError, ConnectionError, TimeoutError):
            time.sleep(0.25)
    raise TimeoutError("workerd did not become ready within 90 seconds")


def main() -> None:
    uv = shutil.which("uv")
    real_node = shutil.which("node")
    if uv is None or real_node is None:
        raise RuntimeError("uv and Node.js 24 are required")

    with TemporaryDirectory(prefix="hayate-htmx-workerd-") as raw_project:
        project = Path(raw_project)
        shim = _write_project(project)
        environment = os.environ.copy()
        environment.pop("UV_PYTHON", None)
        environment["HAYATE_HTMX_REAL_NODE"] = real_node
        environment["PATH"] = f"{shim}{os.pathsep}{environment.get('PATH', '')}"

        _run([uv, "sync"], cwd=project, environment=environment)
        pywrangler = project / ".venv" / "bin" / "pywrangler"
        _run([str(pywrangler), "sync"], cwd=project, environment=environment)

        port = _free_port()
        url = f"http://127.0.0.1:{port}/"
        process = subprocess.Popen(
            [
                str(pywrangler),
                "dev",
                "--ip",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=project,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_server(process, url)
            page, content_type, vary = _fetch(url)
            fragment, fragment_type, fragment_vary = _fetch(url, htmx=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)

        escaped = "&lt;script&gt;alert(1)&lt;/script&gt;"
        assert page.startswith("<!doctype html>")
        assert fragment.startswith("<h1>")
        assert escaped in page and escaped in fragment
        assert "<script>" not in page and "<script>" not in fragment
        assert content_type == fragment_type == "text/html;charset=utf-8"
        assert vary == fragment_vary == EXPECTED_VARY

    print("htpy real-workerd contract: PASS")


if __name__ == "__main__":
    main()
