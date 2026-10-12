"""
02 - A/B Testing & Experimentation
==================================
Helpers behind the notebook. The question they answer: B converts better
than A in the sample - is that a real effect or could it be chance, and
how many users would a reliable test need?
"""

from math import ceil, sqrt
from pathlib import Path

import pandas as pd
from scipy import stats

DATA_FILE = Path(__file__).resolve().parent / "ab_test.csv"


def load_test(path: Path = DATA_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    if set(df["group"]) != {"A", "B"}:
        raise ValueError("group must contain exactly A and B")
    if not df["converted"].isin([0, 1]).all():
        raise ValueError("converted must be 0 or 1")
    if df["user_id"].duplicated().any():
        raise ValueError("each user may appear only once")
    return df


def summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("group")["converted"].agg(users="count", conversions="sum")
    g["rate"] = g["conversions"] / g["users"]
    return g


def wilson_ci(successes: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Wilson score interval - reliable also for small n and rates near 0 or 1."""
    z = stats.norm.ppf(1 - (1 - level) / 2)
    p = successes / n
    centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return float(centre - half), float(centre + half)


def difference_ci(x_a: int, n_a: int, x_b: int, n_b: int, level: float = 0.95) -> tuple[float, float]:
    """Newcombe's hybrid score interval for p_B - p_A (built from two Wilson intervals)."""
    p_a, p_b = x_a / n_a, x_b / n_b
    l_a, u_a = wilson_ci(x_a, n_a, level)
    l_b, u_b = wilson_ci(x_b, n_b, level)
    d = p_b - p_a
    lower = d - sqrt((p_b - l_b) ** 2 + (u_a - p_a) ** 2)
    upper = d + sqrt((u_b - p_b) ** 2 + (p_a - l_a) ** 2)
    return float(lower), float(upper)


def tests(x_a: int, n_a: int, x_b: int, n_b: int) -> dict:
    """Two-sided tests. Fisher's exact test is the right choice for small
    samples; the z-test is shown because it is the usual textbook method."""
    table = [[x_b, n_b - x_b], [x_a, n_a - x_a]]
    _, p_fisher = stats.fisher_exact(table, alternative="two-sided")
    p_pool = (x_a + x_b) / (n_a + n_b)
    se = sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z = (x_b / n_b - x_a / n_a) / se
    p_z = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"z": float(z), "p_ztest": float(p_z), "p_fisher": float(p_fisher)}


def sample_size_per_group(p_a: float, p_b: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Users per group a two-sided two-proportion test needs (normal approximation)."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    p_bar = (p_a + p_b) / 2
    num = (z_a * sqrt(2 * p_bar * (1 - p_bar)) + z_b * sqrt(p_a * (1 - p_a) + p_b * (1 - p_b))) ** 2
    return ceil(num / (p_b - p_a) ** 2)


def power(p_a: float, p_b: float, n_per_group: int, alpha: float = 0.05) -> float:
    """Approximate power of the two-sided z-test at a given group size."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    p_bar = (p_a + p_b) / 2
    se0 = sqrt(2 * p_bar * (1 - p_bar) / n_per_group)
    se1 = sqrt((p_a * (1 - p_a) + p_b * (1 - p_b)) / n_per_group)
    return float(stats.norm.cdf((abs(p_b - p_a) - z_a * se0) / se1))
