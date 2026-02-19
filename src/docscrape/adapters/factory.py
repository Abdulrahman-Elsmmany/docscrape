"""Factory for creating platform adapters."""

from docscrape.adapters.generic import GenericAdapter
from docscrape.core.interfaces import PlatformAdapter


def get_adapter(url: str) -> PlatformAdapter:
    """Create a generic adapter for the given URL.

    Args:
        url: Base URL of the documentation site.

    Returns:
        Platform adapter instance.
    """
    return GenericAdapter(base_url=url)
