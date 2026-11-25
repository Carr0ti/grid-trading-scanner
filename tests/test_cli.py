
from grid_scanner import cli


def sample_results():
    return [
        {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "last": 60000.0,
            "quote_volume_usdt": 100000000.0,
            "bid": 59990.0,
            "ask": 60010.0,
            "spread_percent": 0.0333,
            "status": "POTENTIAL_GRID_CANDIDATE",
            "reasons": ["Low directional persistence."],
            "candle_counts": {
                "1h": 500,
                "4h": 500,
                "1d": 500,
            },
            "timeframes": {
                "1h": {
                    "atr_percent": 0.45,
                    "path_efficiency": 0.20,
                },
                "4h": {
                    "atr_percent": 1.20,
                    "path_efficiency": 0.15,
                },
                "1d": {
                    "atr_percent": 3.50,
                    "path_efficiency": 0.25,
                },
            },
        }
    ]


def test_cli_runs_pipeline_and_saves_report(monkeypatch, tmp_path):
    output_path = tmp_path / "research.csv"
    calls = []

    def fake_pipeline(**kwargs):
        calls.append(kwargs)
        return sample_results()

    monkeypatch.setattr(
        cli,
        "run_binance_pipeline",
        fake_pipeline,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-scanner",
            "--limit",
            "5",
            "--min-volume",
            "6000000",
            "--max-spread",
            "0.10",
            "--candle-limit",
            "300",
            "--csv",
            str(output_path),
        ],
    )

    cli.main()

    assert calls == [
        {
            "limit": 5,
            "minimum_quote_volume": 6000000.0,
            "maximum_spread_percent": 0.10,
            "candle_limit": 300,
        }
    ]

    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "BTC/USDT" in content
    assert "POTENTIAL_GRID_CANDIDATE" in content


def test_cli_stops_when_no_candidates(monkeypatch, tmp_path):
    output_path = tmp_path / "empty.csv"

    monkeypatch.setattr(
        cli,
        "run_binance_pipeline",
        lambda **kwargs: [],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-scanner",
            "--csv",
            str(output_path),
        ],
    )

    try:
        cli.main()
    except SystemExit as exc:
        assert "No markets passed" in str(exc)
    else:
        raise AssertionError("CLI should stop without candidates")

    assert not output_path.exists()


def test_cli_displays_analysis_failures(monkeypatch, tmp_path, capsys):
    failed_result = sample_results()[0].copy()
    failed_result["status"] = "ANALYSIS_FAILED"
    failed_result["reasons"] = ["Binance candle request failed."]

    monkeypatch.setattr(
        cli,
        "run_binance_pipeline",
        lambda **kwargs: [failed_result],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-scanner",
            "--csv",
            str(tmp_path / "failed.csv"),
        ],
    )

    cli.main()

    output = capsys.readouterr().out

    assert "ANALYSIS_FAILED" in output
    assert "Binance candle request failed." in output
    assert "No trades were placed." in output
