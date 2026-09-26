# http-content-negotiation

A small library for evaluating `Accept`, `Accept-Encoding`, and `Accept-Language` HTTP request headers against a list of media types, encodings, or languages that a server can actually serve, returning the best supported one.

```python
from http_content_negotiation import (
    match_accept,
    match_accept_encoding,
    match_accept_language,
)

best = match_accept("text/html, application/json;q=0.9", ["application/json", "text/html"])
# -> "text/html"

enc = match_accept_encoding("gzip, br;q=0.8", ["br"])
# -> "br"

lang = match_accept_language("en-US, fr-FR;q=0.9", ["en-US", "fr-FR"])
# -> "en-US"
```

## Why

Content negotiation looks trivial until you sit down to write it: there are quality factors, wildcards, tie-breaks by specificity, tie-breaks by textual order, malformed input, and the difference between an empty header and a header whose only entry has `q=0`. This library exists to handle all of that in under 200 lines of standard-library Python, with no dependencies and no surprises.

The trade-off is simplicity over spec breadth. `Accept-Language` does not do RFC 4647 prefix matching: `en` in the header will not match `en-US` on the server, and clients who want that fallback must list it explicitly. This avoids the most common bug in negotiators — silently serving `en-US` to a client that asked for `en` — and keeps the matching rule a single literal comparison.

## Edge cases

- A malformed `q` value (non-numeric or out of `[0, 1]`) drops the item it appears on, not the whole header.
- `q=0` excludes that item entirely; it is not a fallback.
- Wildcards in the *server's* `available` list are ignored — a server cannot actually serve `*/*`, so it would be a lie to match it.
- When an item matches multiple ranges, the most specific range wins, then the highest `q`, then the earliest position in the header.
