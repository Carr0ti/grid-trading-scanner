
"""Run historical Binance Spot Grid backtests for multiple pairs."""

from __future__ import annotations

from typing import Any, Iterable

from grid_scanner.backtest_runner import (
    run_binance_spot_grid_backtest,
)


def run_binance_spot_grid_batch_backtest(
    symbols: Iterable[str],
    interval: str = "1h",
    candle_limit: int = 500,
    initial_capital: float = 500.0,
    grid_spacing_percent: float = 0.5,
    levels_each_side: int = 10,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> dict[str, Any]:
    """Backtest multiple Binance Spot pairs independently.

    A failed pair is recorded and does not stop the remaining
    pairs from being tested.
    """
    if isinstance(symbols, str):
        raise ValueError("Symbols must be a list of trading pairs")

    pair_list = list(symbols)

    if not pair_list:
        raise ValueError("At least one trading pair is required")

    results = []
    errors = []

    for symbol in pair_list:
        try:
            result = run_binance_spot_grid_backtest(
                symbol=symbol,
                interval=interval,
                candle_limit=candle_limit,
                initial_capital=initial_capital,
                grid_spacing_percent=grid_spacing_percent,
                levels_each_side=levels_each_side,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
            results.append(result)

        except Exception as error:
            errors.append(
                {
                    "symbol": str(symbol),
                    "error": str(error),
                }
            )

    return {
        "exchange": "binance",
        "interval": interval,
        "requested_count": len(pair_list),
        "success_count": len(results),
        "failure_count": len(errors),
        "results": results,
        "errors": errors,
    }
