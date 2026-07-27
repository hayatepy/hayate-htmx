from importlib.metadata import version

import hayate_htmx


def test_distribution_and_public_versions_match() -> None:
    assert version("hayate-htmx") == hayate_htmx.__version__
