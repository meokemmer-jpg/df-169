from __future__ import annotations

import math


def factorize(n: int) -> dict[int, int]:
    """Return the prime factorization of n as {prime: exponent}."""
    if n < 1:
        raise ValueError("n must be a positive integer")

    factors: dict[int, int] = {}
    remainder = n

    count = 0
    while remainder % 2 == 0:
        remainder //= 2
        count += 1
    if count:
        factors[2] = count

    divisor = 3
    while divisor * divisor <= remainder:
        count = 0
        while remainder % divisor == 0:
            remainder //= divisor
            count += 1
        if count:
            factors[divisor] = count
        divisor += 2

    if remainder > 1:
        factors[remainder] = factors.get(remainder, 0) + 1

    return factors


def is_perfect_square(n: int) -> bool:
    """Return True if n is a perfect square."""
    if n < 0:
        return False
    root = math.isqrt(n)
    return root * root == n


def mission_signature(n: int) -> str:
    """
    Return a canonical signature for a positive integer.

    Example:
        169 -> '169=13^2;square=yes'
    """
    if n < 1:
        raise ValueError("n must be a positive integer")

    parts = []
    for prime, exponent in sorted(factorize(n).items()):
        if exponent == 1:
            parts.append(str(prime))
        else:
            parts.append(f"{prime}^{exponent}")

    square_flag = "yes" if is_perfect_square(n) else "no"
    return f"{n}={'*'.join(parts)};square={square_flag}"
# [CRUX-MK]
