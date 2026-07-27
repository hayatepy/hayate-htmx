"""Experimental Python 3.14 t-string renderer backed by :mod:`tdom`."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable, Mapping
from importlib import import_module
from inspect import isawaitable
from typing import cast

if sys.version_info < (3, 14):  # pragma: no cover - version-specific import guard
    raise ImportError("TdomRenderer requires Python 3.14 or newer")

from string.templatelib import Template  # type: ignore[import-not-found,unused-ignore]

try:
    _html = cast(Callable[[Template], str], import_module("tdom").html)
except ImportError as exc:  # pragma: no cover - exercised in isolated install tests
    raise ImportError(
        "TdomRenderer requires the 'tdom' extra; install hayate-htmx[tdom] on Python 3.14+"
    ) from exc

type TdomFactory = Callable[
    [Mapping[str, object]],
    Template | Awaitable[Template],
]
type TdomView = Template | TdomFactory


class TdomRenderer:
    """Render t-string templates while keeping the public boundary asynchronous."""

    async def render(
        self,
        view: TdomView,
        context: Mapping[str, object],
    ) -> str:
        """Render a template or context-aware component factory with safe interpolation."""
        if isinstance(view, Template):
            template = view
        else:
            produced = view(context)
            template = await produced if isawaitable(produced) else produced
        return _html(template)


__all__ = ["TdomFactory", "TdomRenderer", "TdomView"]
