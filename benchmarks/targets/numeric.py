"""Numeric helpers in the style of small OSS helper libraries."""


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the closed interval [low, high].

    Raise ValueError when ``low > high``.
    """
    if low > high:
        raise ValueError("low must be <= high")
    if value < low:
        return low
    if value > high:
        return high
    return value


def integer_sqrt(n: int) -> int:
    """Return the largest integer ``k`` with ``k*k <= n`` (floor sqrt).

    Raise ValueError for negative ``n``. ``integer_sqrt(0) == 0`` and
    ``integer_sqrt(1) == 1``.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n < 2:
        return n
    lo, hi = 1, n // 2 + 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid * mid <= n:
            lo = mid
        else:
            hi = mid - 1
    return lo


def moving_average(values: list, window: int) -> list:
    """Simple moving average over a sequence of numbers.

    ``window`` must satisfy 1 <= window <= len(values) (ValueError otherwise);
    an empty input yields []. The result has ``len(values) - window + 1``
    entries; entry ``i`` is the mean of ``values[i:i+window]``.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    if not values:
        return []
    if window > len(values):
        raise ValueError("window larger than data")
    out = []
    for i in range(len(values) - window + 1):
        chunk = values[i : i + window]
        out.append(sum(chunk) / window)
    return out
