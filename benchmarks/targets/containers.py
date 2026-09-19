"""Container helpers in the style of small OSS helper libraries."""


def flatten(nested: list, max_depth: int = 8) -> list:
    """Flatten arbitrarily nested lists/tuples into a flat list.

    Order is preserved (depth-first, left to right). Non-sequence items are
    kept as-is; strings are atomic. Nesting deeper than ``max_depth`` levels
    raises ValueError.
    """
    out = []
    for item in nested:
        if isinstance(item, (list, tuple)):
            if max_depth <= 0:
                raise ValueError("nesting too deep")
            out.extend(flatten(item, max_depth - 1))
        else:
            out.append(item)
    return out


def chunk(items: list, size: int) -> list:
    """Split ``items`` into consecutive chunks of at most ``size`` elements.

    The last chunk may be shorter. Raise ValueError when ``size < 1``.
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    return [items[i : i + size] for i in range(0, len(items), size)]


def most_frequent(items: list):
    """Return the most frequent element; ties are broken by first occurrence.

    Raise ValueError on empty input. Elements must be hashable.
    """
    if not items:
        raise ValueError("empty input")
    counts = {}
    order = []
    for x in items:
        if x not in counts:
            counts[x] = 0
            order.append(x)
        counts[x] += 1
    best = order[0]
    for x in order:
        if counts[x] > counts[best]:
            best = x
    return best
