"""Same-site logic: registrable-domain comparison without a full public
suffix list.

Heuristic: the registrable domain is the last two labels of the host, or the
last three when the second-to-last label is a well-known second-level suffix
under a short TLD (co.uk, ac.jp, gov.au and friends). Good enough for
conformance checking; documented in SPEC.md.
"""

from __future__ import annotations

_SECOND_LEVEL = {"co", "ac", "gov", "org", "net", "com", "edu", "sch", "mil", "or", "ne"}


def registrable_domain(host: str) -> str:
    host = host.lower().rstrip(".")
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    if labels[-2] in _SECOND_LEVEL and len(labels[-1]) <= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def same_site(host_a: str, host_b: str) -> bool:
    return registrable_domain(host_a) == registrable_domain(host_b)
