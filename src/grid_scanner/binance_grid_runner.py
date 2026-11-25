
"""Run Binance-style Manual Spot Grid backtests on historical candles."""

from __future__ import annotations

import time
from typing import Any

from grid_scanner.binance_grid import (
    DEFAULT_FEE_RATE,
    DEFAULT_GRID_COUNT,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_SLIPPAGE_RATE,
    backtest_binance_spot_grid,
)
from grid_scanner.history import fetch_binance_klines
from grid_scanner.research import to_binance_symbol


DEFAULT_INTERVAL = "1h"
DEFAULT_CANDLE_LIMIT = 500


def run_binance_manual_grid_backtest(
    symbol: str,
    lower_price: float,
    upper_price: float,
    grid_count: int = DEFAULT_GRID_COUNT,
    mode: str = "arithmetic",
    interval: str = DEFAULT_INTERVAL,
    candle_limit: int = DEFAULT_CANDLE_LIMIT,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    fee_rate: float = DEFAULT_FEE_RATE,
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE,
) -> dict[str, Any]:
    """Fetch completed Binance candles and run a manual grid backtest."""

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("A trading pair is required")

    if interval not in ("1h", "4h", "1d"):
        raise ValueError("Interval must be 1h, 4h, or 1d")

    if (
        not isinstance(candle_limit, int)
        or isinstance(candle_limit, bool)
        or not 2 <= candle_limit <= 1000
    ):
        raise ValueError("Candle limit must be between 2 and 1000")

    binance_symbol = to_binance_symbol(symbol)

    candles = fetch_binance_klines(
        binance_symbol,
        interval,
        limit=candle_limit,
    )

    # Exclude the currently forming candle.
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

    result = backtest_binance_spot_grid(
        completed_candles,
        initial_capital=initial_capital,
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=grid_count,
        mode=mode,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
    )

    result.update(
        {
            "exchange": "binance",
            "symbol": symbol.upper().strip(),
            "binance_symbol": binance_symbol,
            "interval": interval,
            "first_candle_time": completed_candles[0]["open_time"],
            "last_candle_time": completed_candles[-1]["open_time"],
            "completed_candle_count": len(completed_candles),
        }
    )

    return result
