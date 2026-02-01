"""Platform-specific adapters for documentation extraction."""

from docscrape.adapters.factory import PlatformAdapterFactory
from docscrape.adapters.generic import GenericAdapter
from docscrape.adapters.livekit import LiveKitAdapter
from docscrape.adapters.pipecat import PipecatAdapter
from docscrape.adapters.retellai import RetellAIAdapter

__all__ = [
    "PlatformAdapterFactory",
    "GenericAdapter",
    "LiveKitAdapter",
    "PipecatAdapter",
    "RetellAIAdapter",
]
