from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_page_and_fragment_must_share_the_renderer_view_type(tmp_path: Path) -> None:
    source = tmp_path / "invalid_renderer.py"
    source.write_text(
        """
from collections.abc import Mapping

from hayate import Context
from hayate_htmx import HtmxTemplates


class IntRenderer:
    async def render(
        self,
        view: int,
        context: Mapping[str, object],
    ) -> str:
        return str(view)


templates: HtmxTemplates[int] = HtmxTemplates(IntRenderer())


async def invalid(c: Context) -> None:
    await templates.render(c, page=1, fragment="wrong")
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--python-version",
            "3.12",
            str(source),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert 'Argument "fragment" to "render" of "HtmxTemplates"' in result.stdout
    assert 'incompatible type "str"; expected "int"' in result.stdout
