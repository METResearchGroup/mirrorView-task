"""Beta-binomial helpers for per-post remove probability scoring.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.ambiguous_cases_2026_08_16.src.beta_binomial import fit_beta_binomial"
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import betaln


def beta_binomial_loglik(
    alpha: float,
    beta: float,
    remove_counts: np.ndarray,
    n_raters: np.ndarray,
) -> float:
    """Return the beta-binomial log likelihood for observed remove counts."""
    if alpha <= 0.0 or beta <= 0.0:
        return -np.inf
    return float(
        np.sum(
            betaln(remove_counts + alpha, n_raters - remove_counts + beta)
            - betaln(alpha, beta)
        )
    )


def fit_beta_binomial(
    remove_counts: np.ndarray,
    n_raters: np.ndarray,
) -> tuple[float, float]:
    """Fit Beta(alpha, beta) prior parameters by maximum likelihood.

    Parameters
    ----------
    remove_counts
        Per-post remove counts.
    n_raters
        Per-post rater counts.

    Returns
    -------
    tuple[float, float]
        Fitted ``(alpha, beta)``.
    """
    remove_counts = np.asarray(remove_counts, dtype=float)
    n_raters = np.asarray(n_raters, dtype=float)

    def objective(params: np.ndarray) -> float:
        alpha, beta = np.exp(params)
        return -beta_binomial_loglik(alpha, beta, remove_counts, n_raters)

    result = minimize(objective, x0=np.array([0.0, 0.0]), method="L-BFGS-B")
    if not result.success:
        raise RuntimeError(f"Beta-binomial fit failed: {result.message}")
    alpha_hat, beta_hat = np.exp(result.x)
    return float(alpha_hat), float(beta_hat)


def posterior_mean_p(
    remove_count: float,
    n_raters: float,
    alpha: float,
    beta: float,
) -> float:
    """Return the posterior mean of remove probability for one post."""
    return float((alpha + remove_count) / (alpha + beta + n_raters))


def posterior_prob_in_band(
    remove_count: float,
    n_raters: float,
    alpha: float,
    beta: float,
    lower: float = 0.25,
    upper: float = 0.75,
    grid_size: int = 1001,
) -> float:
    """Approximate posterior Prob(p in [lower, upper]) on a dense grid.

    Parameters
    ----------
    remove_count
        Observed removes.
    n_raters
        Observed raters.
    alpha, beta
        Prior parameters.
    lower, upper
        Inclusive middle band endpoints.
    grid_size
        Number of grid points on (0, 1).

    Returns
    -------
    float
        Approximate posterior mass inside the band.
    """
    a_post = alpha + remove_count
    b_post = beta + (n_raters - remove_count)
    grid = np.linspace(1e-6, 1.0 - 1e-6, grid_size)
    # log Beta density up to a constant: (a-1)log p + (b-1)log(1-p)
    log_dens = (a_post - 1.0) * np.log(grid) + (b_post - 1.0) * np.log(1.0 - grid)
    log_dens -= np.max(log_dens)
    dens = np.exp(log_dens)
    dens /= dens.sum()
    mask = (grid >= lower) & (grid <= upper)
    return float(dens[mask].sum())


def four_cell_label(
    keep_count: int,
    remove_count: int,
    n_raters: int,
) -> str:
    """Return the four-cell or tie label for a post."""
    if keep_count == remove_count:
        return "tie"
    if keep_count == n_raters:
        return "unanimous_keep"
    if remove_count == n_raters:
        return "unanimous_remove"
    if keep_count > remove_count:
        return "majority_keep"
    return "majority_remove"
