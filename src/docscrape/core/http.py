"""Shared HTTP client factory for all discovery and crawl code.

Uses curl_cffi with Chrome TLS fingerprint impersonation so Cloudflare-fronted
sites (e.g. readthedocs.io) don't reject us at the TLS handshake. Default
httpx/requests clients announce a Python-shaped JA3 signature and get 403'd
before the User-Agent header is even inspected.
"""

from typing import Literal

from curl_cffi.requests import AsyncSession, Response
from curl_cffi.requests.exceptions import HTTPError, RequestException

# curl_cffi.requests.AsyncSession is generic over the Response type; pin the
# concrete alias here so call sites don't need to know about the type
# parameter.
DocAsyncSession = AsyncSession[Response]

IMPERSONATE: Literal["chrome"] = "chrome"

__all__ = ["make_session", "DocAsyncSession", "HTTPError", "RequestException"]


def make_session(timeout: float = 30.0) -> DocAsyncSession:
    """Return an AsyncSession configured for docscrape's scraping needs.

    Use as::

        async with make_session() as session:
            response = await session.get(url)

    Args:
        timeout: Per-request timeout in seconds.
    """
    return AsyncSession(
        impersonate=IMPERSONATE,
        timeout=timeout,
        allow_redirects=True,
    )
