"""Factory for creating platform adapters."""

from docscrape.core.interfaces import PlatformAdapter


class PlatformAdapterFactory:
    """Factory for creating platform-specific adapters."""

    # Registry of known platforms (lazy-loaded to avoid circular imports)
    _PLATFORMS: dict[str, type[PlatformAdapter]] | None = None

    # URL patterns to auto-detect platform
    _URL_PATTERNS: dict[str, str] = {
        "docs.livekit.io": "livekit",
        "livekit.io/docs": "livekit",
        "docs.pipecat.ai": "pipecat",
        "pipecat.ai/docs": "pipecat",
        "docs.retellai.com": "retellai",
        "retellai.com/docs": "retellai",
    }

    @classmethod
    def _load_platforms(cls) -> dict[str, type[PlatformAdapter]]:
        """Lazy-load platform adapters to avoid circular imports."""
        if cls._PLATFORMS is None:
            from docscrape.adapters.livekit import LiveKitAdapter
            from docscrape.adapters.pipecat import PipecatAdapter
            from docscrape.adapters.retellai import RetellAIAdapter

            cls._PLATFORMS = {
                "livekit": LiveKitAdapter,
                "pipecat": PipecatAdapter,
                "retellai": RetellAIAdapter,
            }
        return cls._PLATFORMS

    @classmethod
    def get_adapter(
        cls,
        platform: str | None = None,
        url: str | None = None,
    ) -> PlatformAdapter:
        """Get a platform adapter.

        Args:
            platform: Platform name (e.g., "livekit", "pipecat").
            url: URL to auto-detect platform from.

        Returns:
            Platform adapter instance.

        Raises:
            ValueError: If neither platform nor url is provided.
        """
        platforms = cls._load_platforms()

        # If platform is specified, use it
        if platform:
            platform_lower = platform.lower()
            if platform_lower in platforms:
                return platforms[platform_lower]()

        # Try to auto-detect from URL
        if url:
            for pattern, platform_name in cls._URL_PATTERNS.items():
                if pattern in url:
                    return platforms[platform_name]()

            # Fall back to generic adapter
            from docscrape.adapters.generic import GenericAdapter

            return GenericAdapter(base_url=url)

        raise ValueError("Either platform or url must be provided")

    @classmethod
    def list_platforms(cls) -> list[str]:
        """List all known platforms."""
        return list(cls._load_platforms().keys())

    @classmethod
    def register_platform(
        cls,
        name: str,
        adapter_class: type[PlatformAdapter],
        url_patterns: list[str] | None = None,
    ) -> None:
        """Register a new platform adapter.

        Args:
            name: Platform name.
            adapter_class: Adapter class.
            url_patterns: URL patterns for auto-detection.
        """
        platforms = cls._load_platforms()
        platforms[name.lower()] = adapter_class

        if url_patterns:
            for pattern in url_patterns:
                cls._URL_PATTERNS[pattern] = name.lower()
