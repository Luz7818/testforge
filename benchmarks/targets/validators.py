"""Input validation helpers in the style of CLI libraries (e.g. click)."""


def validate_username(name: str) -> str:
    """Validate a username and return it unchanged.

    Rules: 3..16 characters, only letters, digits and underscore, and it must
    start with a letter. Violations raise ValueError.
    """
    if not (3 <= len(name) <= 16):
        raise ValueError("length must be 3..16")
    if not name[0].isalpha():
        raise ValueError("must start with a letter")
    for ch in name:
        if not (ch.isalnum() or ch == "_"):
            raise ValueError("illegal character")
    return name


def validate_port(port: int) -> int:
    """Validate a TCP port and return it unchanged.

    Accepts ints in 1..65535. bools are rejected even though bool is an int
    subtype; anything else raises ValueError.
    """
    if isinstance(port, bool):
        raise ValueError("port must be an integer")
    if not isinstance(port, int):
        raise ValueError("port must be an integer")
    if not (1 <= port <= 65535):
        raise ValueError("port out of range")
    return port


def normalize_hex_color(color: str) -> str:
    """Normalize a hex color to the '#RRGGBB' uppercase form.

    '#abc' expands to '#AABBCC'; '#aabbcc' uppercases to '#AABBCC'.
    Anything not matching #RGB or #RRGGBB raises ValueError.
    """
    if not color.startswith("#"):
        raise ValueError("must start with '#'")
    body = color[1:]
    if len(body) == 3:
        body = "".join(c * 2 for c in body)
    if len(body) != 6:
        raise ValueError("must be #RGB or #RRGGBB")
    try:
        value = int(body, 16)
    except ValueError:
        raise ValueError("invalid hex digits") from None
    return f"#{value:06X}"
