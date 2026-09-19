"""String utilities in the style of small OSS helper libraries."""


def slugify(text: str) -> str:
    """Convert free text into a URL slug.

    Lowercase the text, replace every non-alphanumeric character with a
    hyphen, collapse runs of hyphens into one, and strip leading/trailing
    hyphens.
    """
    parts = []
    for ch in text.lower():
        if ch.isalnum():
            parts.append(ch)
        else:
            parts.append("-")
    slug = "".join(parts)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def mask_email(email: str) -> str:
    """Mask an email address for logging.

    Keep the first character of the local part, replace the remaining local
    characters with '*', and keep the domain intact:
    'jsmith@example.com' -> 'j*****@example.com'.
    A single-character local part is kept as-is. Raise ValueError when '@'
    is missing or the local part / domain is empty.
    """
    if "@" not in email:
        raise ValueError("invalid email: missing '@'")
    local, _, domain = email.partition("@")
    if not local or not domain:
        raise ValueError("invalid email: empty local part or domain")
    if len(local) == 1:
        return local + "@" + domain
    return local[0] + "*" * (len(local) - 1) + "@" + domain


def truncate_with_ellipsis(text: str, max_len: int) -> str:
    """Truncate ``text`` to ``max_len`` characters.

    Text that already fits is returned unchanged. Longer text is cut and the
    cut point is indicated with a trailing '...' that counts towards
    ``max_len``. When ``max_len`` is too small to fit content plus ellipsis
    (max_len <= 3), the text is hard-cut without an ellipsis.
    Raise ValueError for negative ``max_len``; ``max_len == 0`` yields ''.
    """
    if max_len < 0:
        raise ValueError("max_len must be non-negative")
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."
