
"""Fetch historical Binance Spot candlestick data."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from grid_scanner.exchanges import fetch_binance_json


SUPPORTED_INTERVALS = ("1h", "4h", "1d")
DEFAULT_CANDLE_LIMIT = 500


def fetch_binance_klines(
    symbol: str,
    interval: str,
    limit: int = DEFAULT_CANDLE_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch historical candles for a Binance Spot symbol."""
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")

    if not symbol or "/" in symbol:
        raise ValueError("Use Binance symbol format, e.g. BTCUSDT")

    if not 1 <= limit <= 1000:
        raise ValueError("Candle limit must be between 1 and 1000")

    query = urlencode(
        {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
    )

    raw_candles = fetch_binance_json(
        f"/api/v3/klines?{query}"
    )

    if not isinstance(raw_candles, list):
        raise ValueError("Unexpected Binance candle response")

    candles = []

    for item in raw_candles:
        if not isinstance(item, list) or len(item) < 11:
            continue

        try:
            candles.append(
                {
                    "open_time": int(item[0]),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5]),
                    "close_time": int(item[6]),
                    "quote_volume": float(item[7]),
                    "trades": int(item[8]),
                }
            )
        except (TypeError, ValueError):
            continue

    return candles
