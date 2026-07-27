"""Optional Jinja-component renderer backed by :mod:`jx`."""

from __future__ import annotations

from collections.abc import Mapping
from os import PathLike
from typing import cast

try:
    from jx import Catalog  # type: ignore[import-untyped]
    from jx import (
        ComponentNotFoundError as _JxComponentNotFoundError,
    )
except ImportError as exc:  # pragma: no cover - exercised in isolated install tests
    raise ImportError("JxRenderer requires the 'jx' extra; install hayate-htmx[jx]") from exc


class ComponentNotFoundError(LookupError):
    """A named Jx component could not be loaded."""

    def __init__(self, component_name: str) -> None:
        self.component_name = component_name
        super().__init__(f"component not found: {component_name}")


class JxRenderer:
    """Render named Jx components through one reusable catalog."""

    def __init__(
        self,
        source: str | PathLike[str] | Catalog,
        *,
        auto_reload: bool = False,
    ) -> None:
        self.catalog = (
            source if isinstance(source, Catalog) else Catalog(source, auto_reload=auto_reload)
        )

    async def render(
        self,
        component_name: str,
        context: Mapping[str, object],
    ) -> str:
        """Render one named component and preserve missing-component identity."""
        try:
            return cast(str, self.catalog.render(component_name, **context))
        except _JxComponentNotFoundError as exc:
            raise ComponentNotFoundError(component_name) from exc


__all__ = ["ComponentNotFoundError", "JxRenderer"]
