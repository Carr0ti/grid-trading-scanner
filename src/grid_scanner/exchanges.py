
"""Read public Spot market data from supported exchanges."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

import ccxt


SUPPORTED_EXCHANGES = ("binance", "okx", "bybit", "bitget", "mexc")

BINANCE_DATA_API = "https://data-api.binance.vision"


def create_exchange(exchange_id: str) -> ccxt.Exchange:
    """Create a rate-limited exchange client without credentials."""
    if exchange_id not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange: {exchange_id}")

    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def fetch_binance_json(endpoint: str) -> Any:
    """Fetch JSON from Binance's public market-data API."""
    request = Request(
        f"{BINANCE_DATA_API}{endpoint}",
        headers={"User-Agent": "grid-trading-scanner/0.1.0"},
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _quote_to_usdt_rates(
    markets: list[dict[str, Any]],
    tickers: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Estimate quote-asset conversion rates into USDT."""
    rates = {"USDT": 1.0}

    for market in markets:
        if market.get("status") != "TRADING":
            continue

        if market.get("isSpotTradingAllowed") is not True:
            continue

        base = market.get("baseAsset")
        quote = market.get("quoteAsset")
        symbol = market.get("symbol")

        if not base or not quote or not symbol:
            continue

        ticker = tickers.get(symbol)

        if not ticker:
            continue

        try:
            price = float(ticker["lastPrice"])
        except (KeyError, TypeError, ValueError):
            continue

        if price <= 0:
            continue

        if quote == "USDT":
            rates[base] = price

        elif base == "USDT":
            rates[quote] = 1.0 / price

    return rates


def _market_filters(
    market: dict[str, Any],
) -> dict[str, Any]:
    """Extract Binance order filters needed for future simulations."""
    result: dict[str, Any] = {}

    for item in market.get("filters", []):
        filter_type = item.get("filterType")

        if filter_type == "PRICE_FILTER":
            result["tick_size"] = item.get("tickSize")

        elif filter_type == "LOT_SIZE":
            result["step_size"] = item.get("stepSize")
            result["min_quantity"] = item.get("minQty")

        elif filter_type in ("MIN_NOTIONAL", "NOTIONAL"):
            result["min_notional"] = (
                item.get("minNotional")
                or item.get("notional")
            )

    return result


def scan_binance(
    quote_currency: str | None = None,
    minimum_quote_volume: float = 5_000_000,
    maximum_spread_percent: float = 0.15,
) -> list[dict[str, Any]]:
    """Scan all eligible Binance Spot markets.

    If quote_currency is None, all quote currencies are included.
    Volume is normalized approximately into USDT for comparison.
    """
    if minimum_quote_volume < 0:
        raise ValueError("Minimum quote volume cannot be negative")

    if maximum_spread_percent < 0:
        raise ValueError("Maximum spread cannot be negative")

    market_data = fetch_binance_json("/api/v3/exchangeInfo")
    ticker_data = fetch_binance_json("/api/v3/ticker/24hr")
    book_data = fetch_binance_json("/api/v3/ticker/bookTicker")

    markets = market_data.get("symbols", [])

    tickers = {
        item["symbol"]: item
        for item in ticker_data
        if isinstance(item, dict) and "symbol" in item
    }

    books = {
        item["symbol"]: item
        for item in book_data
        if isinstance(item, dict) and "symbol" in item
    }

    conversion_rates = _quote_to_usdt_rates(markets, tickers)

    results: list[dict[str, Any]] = []

    for market in markets:
        symbol = market.get("symbol")
        base_asset = market.get("baseAsset")
        market_quote = market.get("quoteAsset")

        if not symbol or not base_asset or not market_quote:
            continue

        if market.get("status") != "TRADING":
            continue

        if market.get("isSpotTradingAllowed") is not True:
            continue

        if quote_currency and market_quote != quote_currency:
            continue

        conversion_rate = conversion_rates.get(market_quote)

        # Skip markets whose quote asset cannot be normalized
        # reliably into USDT using a direct conversion market.
        if conversion_rate is None:
            continue

        ticker = tickers.get(symbol)
        book = books.get(symbol)

        if not ticker or not book:
            continue

        try:
            quote_volume = float(ticker["quoteVolume"])
            last = float(ticker["lastPrice"])
            bid = float(book["bidPrice"])
            ask = float(book["askPrice"])
        except (KeyError, TypeError, ValueError):
            continue

        if quote_volume < 0 or last <= 0:
            continue

        if bid <= 0 or ask <= 0 or ask < bid:
            continue

        quote_volume_usdt = quote_volume * conversion_rate

        if quote_volume_usdt < minimum_quote_volume:
            continue

        midpoint = (bid + ask) / 2
        spread_percent = ((ask - bid) / midpoint) * 100

        if spread_percent > maximum_spread_percent:
            continue

        results.append(
            {
                "exchange": "binance",
                "symbol": f"{base_asset}/{market_quote}",
                "base_asset": base_asset,
                "quote_asset": market_quote,
                "last": last,
                "quote_volume": quote_volume,
                "quote_volume_usdt": quote_volume_usdt,
                "quote_to_usdt_rate": conversion_rate,
                "bid": bid,
                "ask": ask,
                "spread_percent": spread_percent,
                **_market_filters(market),
            }
        )

    return sorted(
        results,
        key=lambda item: item["quote_volume_usdt"],
        reverse=True,
    )


def is_eligible_spot_market(
    market: dict[str, Any],
    ticker: dict[str, Any],
    quote_currency: str = "USDT",
    minimum_quote_volume: float = 5_000_000,
    maximum_spread_percent: float = 0.15,
) -> bool:
    """Apply initial liquidity and spread filters."""
    if market.get("spot") is not True:
        return False

    if market.get("quote") != quote_currency:
        return False

    if market.get("active") is False:
        return False

    quote_volume = ticker.get("quoteVolume")
    bid = ticker.get("bid")
    ask = ticker.get("ask")

    if not isinstance(quote_volume, (int, float)):
        return False

    if quote_volume < minimum_quote_volume:
        return False

    if not isinstance(bid, (int, float)):
        return False

    if not isinstance(ask, (int, float)):
        return False

    if bid <= 0 or ask <= 0 or ask < bid:
        return False

    midpoint = (bid + ask) / 2
    spread_percent = ((ask - bid) / midpoint) * 100

    return spread_percent <= maximum_spread_percent


def scan_exchange(
    exchange_id: str,
    quote_currency: str | None = None,
    minimum_quote_volume: float = 5_000_000,
    maximum_spread_percent: float = 0.15,
) -> list[dict[str, Any]]:
    """Fetch public Spot tickers and return eligible markets by volume."""
    if exchange_id not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange: {exchange_id}")

    if exchange_id == "binance":
        return scan_binance(
            quote_currency=quote_currency,
            minimum_quote_volume=minimum_quote_volume,
            maximum_spread_percent=maximum_spread_percent,
        )

    exchange = create_exchange(exchange_id)

    try:
        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()

        results: list[dict[str, Any]] = []

        for symbol, market in markets.items():
            ticker = tickers.get(symbol)

            if not ticker:
                continue

            if quote_currency and market.get("quote") != quote_currency:
                continue

            if not is_eligible_spot_market(
                market,
                ticker,
                quote_currency=market.get("quote", ""),
                minimum_quote_volume=minimum_quote_volume,
                maximum_spread_percent=maximum_spread_percent,
            ):
                continue

            bid = ticker["bid"]
            ask = ticker["ask"]
            midpoint = (bid + ask) / 2

            results.append(
                {
                    "exchange": exchange_id,
                    "symbol": symbol,
                    "base_asset": market.get("base"),
                    "quote_asset": market.get("quote"),
                    "last": ticker.get("last"),
                    "quote_volume": ticker.get("quoteVolume"),
                    "quote_volume_usdt": ticker.get("quoteVolume"),
                    "bid": bid,
                    "ask": ask,
                    "spread_percent": ((ask - bid) / midpoint) * 100,
                }
            )

        return sorted(
            results,
            key=lambda item: item["quote_volume_usdt"],
            reverse=True,
        )

    finally:
        exchange.close()
