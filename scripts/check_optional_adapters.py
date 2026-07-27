"""Exercise the built wheel with no extras and with every renderer extra."""

from __future__ import annotations

import asyncio
import importlib
import sys
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast


def check_base() -> None:
    """The base wheel must not import or silently require optional renderers."""
    import hayate_htmx

    assert hayate_htmx.__version__ == version("hayate-htmx")
    assert "htpy" not in sys.modules
    assert "jx" not in sys.modules
    assert "tdom" not in sys.modules

    expected = {
        "hayate_htmx.htpy": "hayate-htmx[htpy]",
        "hayate_htmx.jx": "hayate-htmx[jx]",
        "hayate_htmx.tdom": "Python 3.14",
    }
    for module_name, message in expected.items():
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            assert message in str(exc), (module_name, str(exc))
        else:
            raise AssertionError(f"{module_name} imported without its extra")


async def check_adapter(adapter: str) -> None:
    """Every extra must install from wheel metadata and retain safe escaping."""
    unsafe = "<script>alert(1)</script>"

    if adapter == "htpy":
        from htpy import h1

        from hayate_htmx.htpy import HtpyRenderer

        rendered = await HtpyRenderer().render(h1[unsafe], {})
    elif adapter == "jx":
        from hayate_htmx.jx import JxRenderer

        with TemporaryDirectory() as directory:
            Path(directory, "component.jx").write_text(
                "{#def value #}<h1>{{ value }}</h1>",
                encoding="utf-8",
            )
            rendered = await JxRenderer(directory).render(
                "component.jx",
                {"value": unsafe},
            )
    elif adapter == "tdom":
        from string.templatelib import Template  # type: ignore[import-not-found]

        from hayate_htmx.tdom import TdomRenderer

        view = cast(Template, eval('t"<h1>{unsafe}</h1>"'))
        rendered = await TdomRenderer().render(view, {})
    else:
        raise AssertionError(f"unknown adapter: {adapter}")

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "<script>" not in rendered


def main() -> None:
    mode = sys.argv[1]
    if mode == "base":
        check_base()
    else:
        asyncio.run(check_adapter(mode))
    print(f"{mode} wheel contract: PASS")


if __name__ == "__main__":
    main()
