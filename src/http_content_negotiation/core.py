from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class _ParsedMediaRange:
    """A media range with its specificity and quality factor.

    Lower specificity sorts later (less preferred). In RFC 9110, a media range
    with both type and subtype is more specific than `type/*`, which is more
    specific than `*/*`.
    """
    type: str
    subtype: str
    specificity: int  # 2 = full, 1 = type/*, 0 = */*
    quality: float


@dataclass(frozen=True)
class _ParsedToken:
    """A single coding token (used for encoding and language).

    The `value` field carries a string used for display matching, regardless of
    whether it came from the left or right side of the `q=` separator. The
    `type_` flag records which side it came from so `*` can be allowed only as
    a right-hand wildcard, per RFC 9110 §12.5.1.
    """
    value: str
    type_: str  # 'value' if left of '=', 'param' if right of '='
    specificity: int  # 1 = concrete, 0 = *
    quality: float


def _parse_quality(params: list[str]) -> float:
    """Extract the q-value from the tail of a token's parameters.

    RFC 9110 defines q-values in the range [0, 1] with up to three decimal
    places. Anything outside that range is rejected as malformed (the whole
    item is dropped), rather than clamped, because a clamp silently hides a
    client bug.
    """
    for raw in params:
        if not raw.startswith("q="):
            continue
        try:
            value = float(raw[2:])
        except ValueError:
            raise ValueError("bad q")
        if not (0.0 <= value <= 1.0):
            raise ValueError("q out of range")
        return value
    return 1.0


def _split_clean(s: str, sep: str) -> list[str]:
    return [p.strip() for p in s.split(sep) if p.strip()]


def _parse_accept(header: str) -> list[tuple[_ParsedMediaRange, int]]:
    """Parse an Accept header into media ranges tagged with original order.

    The order tag is kept because `*/*` in position 0 and `*/*` in position 5
    are not the same: clients conventionally list their strongest preference
    first, and the tie-break for equal specificity falls back to textual order
    per RFC 9110 §12.5.1.
    """
    out: list[tuple[_ParsedMediaRange, int]] = []
    for idx, item in enumerate(_split_clean(header, ",")):
        bits = _split_clean(item, ";")
        if not bits:
            continue
        main = bits[0]
        if "/" not in main:
            continue
        type_, _, subtype = main.partition("/")
        type_ = type_.strip().lower()
        subtype = subtype.strip().lower()
        if type_ == "*" and subtype != "*":
            continue
        if type_ == "*" and subtype == "*":
            spec = 0
        elif subtype == "*":
            spec = 1
        else:
            spec = 2
        try:
            q = _parse_quality(bits[1:])
        except ValueError:
            continue
        out.append((_ParsedMediaRange(type_, subtype, spec, q), idx))
    return out


def match_accept(header: str, available: list[str]) -> Optional[str]:
    """Return the best-supported media type for an Accept header, or None.

    `available` is a list of concrete media types (e.g. `application/json`).
    Wildcards are ignored on the server side because a server offering `*/*`
    has no way to actually send it.
    """
    parsed = _parse_accept(header)
    candidates: list[tuple[float, int, int, str]] = []
    for avail in available:
        if "/" not in avail:
            continue
        at, _, asub = avail.partition("/")
        at = at.strip().lower()
        asub = asub.strip().lower()
        if not at or not asub or at == "*" or asub == "*":
            continue
        best: Optional[tuple[int, float, int]] = None
        for rng, idx in parsed:
            if rng.quality <= 0.0:
                continue
            if rng.type == "*":
                mspec = 0
            elif rng.type != at:
                continue
            elif rng.subtype == "*":
                mspec = 1
            elif rng.subtype == asub:
                mspec = 2
            else:
                continue
            cand = (mspec, rng.quality, idx)
            if best is None or cand > best:
                best = cand
        if best is None:
            continue
        mspec, q, pos_idx = best
        candidates.append((q, mspec, -pos_idx, avail))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][3]


def _parse_tokens(header: str) -> list[tuple[_ParsedToken, int]]:
    """Parse a comma-separated coding/language header.

    The same parser handles both Accept-Encoding and Accept-Language because
    their structure is identical: `token` or `token;q=N`, optionally a bare
    `*` as a right-hand wildcard (§12.5.1 of RFC 9110, §5.3.4 of RFC 7231 for
    Accept-Language where the wildcard does not appear explicitly but is
    functionally accepted by most implementations).
    """
    out: list[tuple[_ParsedToken, int]] = []
    for idx, item in enumerate(_split_clean(header, ",")):
        bits = _split_clean(item, ";")
        if not bits:
            continue
        raw = bits[0]
        is_param = "=" in raw
        if is_param:
            key, _, val = raw.partition("=")
            key = key.strip().lower()
            val = val.strip().lower()
            if key != "q":
                continue
            try:
                q = float(val)
            except ValueError:
                continue
            if not (0.0 <= q <= 1.0):
                continue
            out.append((_ParsedToken("*", "param", 0, q), idx))
            continue
        val = raw.lower()
        spec = 0 if val == "*" else 1
        try:
            q = _parse_quality(bits[1:])
        except ValueError:
            continue
        out.append((_ParsedToken(val, "value", spec, q), idx))
    return out


def _match_tokens(parsed: list[tuple[_ParsedToken, int]], available: list[str]) -> Optional[str]:
    candidates: list[tuple[float, int, int, str]] = []
    for avail in available:
        al = avail.lower()
        if not al or al == "*":
            continue
        best: Optional[tuple[int, float, int]] = None
        for tok, idx in parsed:
            if tok.quality <= 0.0:
                continue
            if tok.type_ == "value":
                if tok.value == "*":
                    mspec = 0
                elif tok.value == al:
                    mspec = 1
                else:
                    continue
            else:
                mspec = 0
            cand = (mspec, tok.quality, idx)
            if best is None or cand > best:
                best = cand
        if best is None:
            continue
        mspec, q, pos_idx = best
        candidates.append((q, mspec, -pos_idx, avail))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][3]


def match_accept_encoding(header: str, available: list[str]) -> Optional[str]:
    """Return the best-supported encoding for an Accept-Encoding header, or None."""
    return _match_tokens(_parse_tokens(header), available)


def match_accept_language(header: str, available: list[str]) -> Optional[str]:
    """Return the best-supported language for an Accept-Language header, or None.

    A full language-range (RFC 4647 §2.1) is used literally; subtag prefix
    matching is not implemented. That keeps the rule simple and predictable:
    `en-US` only matches `en-US`, not `en`. Clients who want a fallback to
    `en` should list it explicitly.
    """
    return _match_tokens(_parse_tokens(header), available)
