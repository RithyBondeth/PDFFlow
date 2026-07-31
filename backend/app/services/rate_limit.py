"""Rate limiting.

With no accounts there is no identity to key on, so limits are per client IP
and deriving that IP correctly *is* the security of this module.

The subtlety that matters: nginx forwards with ``$proxy_add_x_forwarded_for``,
which **appends** the real peer to whatever ``X-Forwarded-For`` the caller
sent. A request carrying ``X-Forwarded-For: 1.2.3.4`` therefore reaches the app
as ``1.2.3.4, <real peer>`` — so reading the *left* of that list keys the
limiter on a value the caller chose, and rotating it per request slips every
limit. The client is the rightmost entry that is not one of our own proxies.

Header values are only consulted when the request actually arrived from a
trusted proxy. Pointed straight at the API — which the deployment notes warn
can happen — the peer address is used and the headers are ignored entirely.

Counters live in Redis so several API replicas share one budget.
"""

from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


@lru_cache(maxsize=8)
def _parse_networks(values: tuple[str, ...]) -> tuple[Network, ...]:
    """Parse the configured CIDRs once. A malformed entry is dropped rather
    than raised: a typo must not take the API down, but it must be visible."""
    networks: list[Network] = []
    for raw in values:
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            logger.warning("invalid_trusted_proxy", extra={"value": raw})
    return tuple(networks)


def _is_trusted(host: str, networks: tuple[Network, ...]) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False  # not an address at all — never trust it
    return any(address in network for network in networks)


def client_key(request: Request) -> str:
    peer = request.client.host if request.client else None
    if peer is None:
        return get_remote_address(request)

    networks = _parse_networks(tuple(settings.trusted_proxies))
    if not _is_trusted(peer, networks):
        # Direct connection: no header on it is ours to believe.
        return peer

    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted(hop, networks):
            return hop

    # Every hop is one of ours, or the header is absent: the peer is the best
    # answer available, and it is one we control.
    return peer


limiter = Limiter(
    key_func=client_key,
    storage_uri=settings.redis_url,
    headers_enabled=True,
)
