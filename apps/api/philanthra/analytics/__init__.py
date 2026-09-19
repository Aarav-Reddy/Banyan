"""Deterministic calculations; callers own authorization and persistence."""

from .allocation import allocate
from .finance import financial_signals
from .matching import benchmark, match_transfer
from .pooling import pool_observations

__all__ = ["allocate", "financial_signals", "benchmark", "match_transfer", "pool_observations"]
