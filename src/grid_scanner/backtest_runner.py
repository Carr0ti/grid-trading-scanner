
"""Run Spot Grid backtests using historical Binance Spot candles."""

from __future__ import annotations

import time
from typing import Any

from grid_scanner.backtest import backtest_spot_grid
from grid_scanner.history import fetch_binance_klines
from grid_scanner.research import to_binance_symbol


DEFAULT_BACKTEST_INTERVAL = "1h"
DEFAULT_BACKTEST_CANDLE_LIMIT = 500


def run_binance_spot_grid_backtest(
    symbol: str,
    interval: str = DEFAULT_BACKTEST_INTERVAL,
    candle_limit: int = DEFAULT_BACKTEST_CANDLE_LIMIT,
    initial_capital: float = 500.0,
    grid_spacing_percent: float = 0.5,
    levels_each_side: int = 10,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> dict[str, Any]:
    """Fetch completed Binance candles and run a Spot Grid backtest."""
    binance_symbol = to_binance_symbol(symbol)

    candles = fetch_binance_klines(
        binance_symbol,
        interval,
        limit=candle_limit,
    )

    # Binance may include the currently forming candle.
    # Only completed candles are suitable for this backtest.
    current_time_ms = int(time.time() * 1000)

    completed_candles = [
        candle
        for candle in candles
        if (
            isinstance(candle.get("close_time"), (int, float))
            and candle["close_time"] <= current_time_ms
        )
    ]

    if len(completed_candles) < 2:
        raise ValueError(
            "At least two completed historical candles are required"
        )

    result = backtest_spot_grid(
        completed_candles,
        initial_capital=initial_capital,
        grid_spacing_percent=grid_spacing_percent,
        levels_each_side=levels_each_side,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
    )

    result.update(
        {
            "exchange": "binance",
            "symbol": symbol.upper(),
            "binance_symbol": binance_symbol,
            "interval": interval,
            "first_candle_time": completed_candles[0]["open_time"],
            "last_candle_time": completed_candles[-1]["open_time"],
        }
    )

    return result
