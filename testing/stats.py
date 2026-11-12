"""Statistical checks of random outcomes (drop rates, proc chances, block and hit rolls).

A random outcome is checked over many trials, never one: count how often it happened and compare the rate with the
expected value within a tolerance. The default tolerance is 4 standard deviations of a binomial rate, so a correct rule
fails about once in 16,000 runs while a wrong one (a rate off by more than the tolerance) fails nearly every time.

    hits = count(lambda rng: roll(rng) < 25, trials=20000, seed=9)   # a model, with a fixed seed: same result each run
    assert_rate(hits, 20000, 0.25)
    assert_rate(blocks_in_log, swings_in_log, 0.42, tolerance=0.02)  # counts read from a game log

Pure Python, no game. Use inside a `@check` function (an AssertionError is a failed check).
"""
from __future__ import annotations

import math
import random

SIGMAS = 4.0


def count(trial, trials: int, seed: int) -> int:
    """Runs `trial(rng)` `trials` times on one random.Random(seed); returns how many returned true."""
    rng = random.Random(seed)
    return sum(1 for _ in range(trials) if trial(rng))


def tolerance_for(expected: float, trials: int, sigmas: float = SIGMAS) -> float:
    """`sigmas` standard deviations of the rate of `trials` draws with chance `expected`."""
    return sigmas * math.sqrt(expected * (1 - expected) / trials)


def assert_rate(hits: int, trials: int, expected: float, tolerance: float | None = None) -> str:
    """Fails unless hits/trials is within `tolerance` (default: 4 standard deviations) of `expected`."""
    assert trials > 0, "no trials"
    assert 0 <= hits <= trials, f"{hits} hits out of {trials} trials"
    assert 0 <= expected <= 1, f"expected rate {expected} is not a probability"
    tol = tolerance_for(expected, trials) if tolerance is None else tolerance
    rate = hits / trials
    assert abs(rate - expected) <= tol, (f"rate {rate:.4f} ({hits}/{trials}) is not within {tol:.4f} of the expected "
                                         f"{expected:.4f}")
    return f"rate {rate:.4f} ({hits}/{trials}), expected {expected:.4f} +- {tol:.4f}"
