"""Parsing helpers in the style of small OSS helper libraries."""


def parse_csv_line(line: str) -> list:
    """Parse a single CSV line into fields.

    Supports double-quoted fields containing commas and escaped quotes
    (``""`` inside quotes is one literal quote).
    """
    fields, buf = [], []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    buf.append('"')
                    i += 1
                else:
                    in_quotes = False
            else:
                buf.append(ch)
        else:
            if ch == '"':
                in_quotes = True
            elif ch == ",":
                fields.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        i += 1
    fields.append("".join(buf))
    return fields


def parse_version(version: str) -> tuple:
    """Parse ``major.minor.patch`` into a tuple of ints.

    A single leading 'v' is ignored. Every part must be numeric and at most
    999; anything else raises ValueError.
    """
    v = version[1:] if version.startswith("v") else version
    parts = v.split(".")
    if len(parts) != 3:
        raise ValueError("expected major.minor.patch")
    nums = []
    for p in parts:
        if not p.isdigit():
            raise ValueError("non-numeric part")
        n = int(p)
        if n > 999:
            raise ValueError("part out of range")
        nums.append(n)
    return (nums[0], nums[1], nums[2])


def parse_kv_pairs(text: str) -> dict:
    """Parse ``a=1,b=2`` into ``{'a': '1', 'b': '2'}``.

    Whitespace around keys and values is stripped; empty text yields {}.
    The first '=' inside an entry splits key and value; an entry without
    '=' raises ValueError.
    """
    result = {}
    if not text.strip():
        return result
    for entry in text.split(","):
        if "=" not in entry:
            raise ValueError(f"bad entry: {entry!r}")
        k, _, v = entry.partition("=")
        result[k.strip()] = v.strip()
    return result
