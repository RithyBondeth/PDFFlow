"""Which IP the limiter keys on.

This is the whole security of the app-layer limiter: key on something the
caller controls and the limit is decorative, because rotating that value
buys an unlimited budget.
"""

from __future__ import annotations

import pytest

from app.services.rate_limit import client_key


class _Client:
    def __init__(self, host: str) -> None:
        self.host = host


class _Request:
    """Just enough of a Starlette request for the key function."""

    def __init__(self, peer: str | None, headers: dict[str, str] | None = None) -> None:
        self.client = _Client(peer) if peer else None
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}


PROXY = "172.18.0.5"  # a docker-network address, inside the trusted default


def test_spoofed_forwarded_for_is_ignored():
    """The attack this function exists to stop.

    nginx appends the real peer, so a caller-supplied X-Forwarded-For ends up
    on the LEFT. Keying on it would let one client mint a fresh bucket per
    request just by changing a header.
    """
    request = _Request(PROXY, {"X-Forwarded-For": "1.2.3.4, 203.0.113.9"})

    assert client_key(request) == "203.0.113.9"


def test_a_spoofed_chain_cannot_bury_the_real_peer():
    """Padding the header with many fake hops must not shift the answer."""
    forged = ", ".join(f"9.9.9.{n}" for n in range(1, 20))
    request = _Request(PROXY, {"X-Forwarded-For": f"{forged}, 203.0.113.9"})

    assert client_key(request) == "203.0.113.9"


def test_private_looking_spoof_is_not_skipped_into():
    """A caller claiming a trusted-range address must not be able to make the
    walk step past the real peer and land on their own value."""
    request = _Request(PROXY, {"X-Forwarded-For": "10.0.0.1, 203.0.113.9"})

    assert client_key(request) == "203.0.113.9"


def test_headers_from_an_untrusted_peer_are_ignored_entirely():
    """Exposed directly, with no proxy in front: the peer is the only fact."""
    request = _Request("203.0.113.9", {"X-Forwarded-For": "1.2.3.4"})

    assert client_key(request) == "203.0.113.9"


def test_a_chain_of_proxies_resolves_to_the_client():
    """LB → nginx → api, with the load balancer inside the trusted range."""
    request = _Request(PROXY, {"X-Forwarded-For": "203.0.113.9, 10.1.2.3"})

    assert client_key(request) == "203.0.113.9"


def test_missing_header_falls_back_to_the_peer():
    assert client_key(_Request(PROXY)) == PROXY


def test_garbage_in_the_header_is_not_treated_as_an_address():
    """A non-address entry is untrusted, so it is returned as the key rather
    than silently skipped — it still buckets, and it cannot impersonate a
    trusted hop."""
    request = _Request(PROXY, {"X-Forwarded-For": "not-an-ip"})

    assert client_key(request) == "not-an-ip"


def test_trusted_proxies_can_be_narrowed(monkeypatch: pytest.MonkeyPatch):
    """With the docker ranges removed, nginx itself stops being trusted and
    its forwarded header is ignored."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "trusted_proxies", ["127.0.0.0/8"])
    request = _Request(PROXY, {"X-Forwarded-For": "203.0.113.9"})

    assert client_key(request) == PROXY


def test_a_malformed_cidr_does_not_break_the_key(monkeypatch: pytest.MonkeyPatch):
    """A typo in configuration must not take the API down."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "trusted_proxies", ["not-a-cidr", "172.16.0.0/12"])
    request = _Request(PROXY, {"X-Forwarded-For": "203.0.113.9"})

    assert client_key(request) == "203.0.113.9"
