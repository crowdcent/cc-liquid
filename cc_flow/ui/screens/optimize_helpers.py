"""Helper functions for optimization screen.

This module provides utility functions for:
- CSV parsing
- Parameter validation
- Mock optimization execution
"""

from __future__ import annotations

import itertools
import random
from typing import TYPE_CHECKING

import polars as pl

from cc_flow.utils.logger_config import log

if TYPE_CHECKING:
    pass


def parse_csv_range(
    csv_string: str, value_type: type[int] | type[float]
) -> list[int] | list[float]:
    """Parse CSV string into list of values.

    Args:
        csv_string: Comma-separated values (e.g., "5,10,15")
        value_type: Type to convert values to (int or float)

    Returns:
        List of parsed values

    Raises:
        ValueError: If CSV string is empty or contains invalid values
    """
    csv_string = csv_string.strip()
    if not csv_string:
        raise ValueError("Parameter range cannot be empty")

    try:
        values = [value_type(x.strip()) for x in csv_string.split(",")]
        return values
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid format in parameter range: {csv_string}") from e


def validate_parameter_ranges(
    param_grid: dict[str, list]
) -> tuple[bool, str | None]:
    """Validate parameter ranges.

    Args:
        param_grid: Dictionary of parameter names to value lists

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for empty ranges
    for param_name, values in param_grid.items():
        if not values:
            return False, f"Parameter range for {param_name} is empty"

    # Check for negative values
    for param_name, values in param_grid.items():
        if any(v < 0 for v in values):
            return False, f"Parameter {param_name} contains negative values"

    # Check that at least one position type has non-zero values
    has_long = any(v > 0 for v in param_grid["num_long"])
    has_short = any(v > 0 for v in param_grid["num_short"])

    if not has_long and not has_short:
        return (
            False,
            "At least one position (long or short) must be greater than zero",
        )

    return True, None


async def run_optimization_mock(
    param_grid: dict[str, list], metric: str
) -> pl.DataFrame:
    """Run optimization grid search (mock implementation).

    Args:
        param_grid: Dictionary of parameter names to value lists
        metric: Metric name to optimize

    Returns:
        DataFrame with optimization results sorted by metric
    """
    log.info(f"Running mock optimization with metric: {metric}")

    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]

    combinations = list(itertools.product(*param_values))

    # Create mock results for each combination
    results_data = {name: [] for name in param_names}
    results_data[metric] = []

    random.seed(42)  # For reproducible mock results

    for combo in combinations:
        for i, name in enumerate(param_names):
            results_data[name].append(combo[i])

        # Generate mock metric value based on parameters
        # Higher num_long/short and moderate leverage tend to be better
        num_long = combo[0]
        num_short = combo[1]
        leverage = combo[2]
        rank_power = combo[3]

        # Simple heuristic for mock values
        base_value = (num_long + num_short) * 0.05
        leverage_factor = 1.0 + (2.0 - leverage) * 0.2
        rank_power_factor = 1.0 + rank_power * 0.1
        noise = random.uniform(-0.1, 0.1)

        metric_value = base_value * leverage_factor * rank_power_factor + noise
        results_data[metric].append(round(metric_value, 2))

    # Create DataFrame and sort by metric (descending)
    results_df = pl.DataFrame(results_data)
    results_df = results_df.sort(metric, descending=True)

    log.info(f"Generated {len(results_df)} optimization results")
    return results_df
