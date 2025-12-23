from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest

from cc_liquid.backtester import BacktestConfig, Backtester, BacktestOptimizer


def _write_sample_data(tmp_path) -> tuple[str, str]:
    price_rows = []
    dates = [
        datetime(2023, 1, 1),
        datetime(2023, 1, 2),
        datetime(2023, 1, 3),
    ]
    aaa_prices = [100.0, 110.0, 121.0]
    bbb_prices = [100.0, 99.0, 98.0]

    for date, aaa_price, bbb_price in zip(dates, aaa_prices, bbb_prices):
        price_rows.append({"date": date, "id": "AAA", "close": aaa_price})
        price_rows.append({"date": date, "id": "BBB", "close": bbb_price})

    prices_df = pl.DataFrame(price_rows)
    prices_path = tmp_path / "prices.parquet"
    prices_df.write_parquet(prices_path)

    pred_rows = [
        {"release_date": datetime(2023, 1, 1), "id": "AAA", "pred_10d": 0.90},
        {"release_date": datetime(2023, 1, 1), "id": "BBB", "pred_10d": -0.10},
        {"release_date": datetime(2023, 1, 2), "id": "AAA", "pred_10d": 0.85},
        {"release_date": datetime(2023, 1, 2), "id": "BBB", "pred_10d": -0.20},
    ]
    preds_df = pl.DataFrame(pred_rows)
    preds_path = tmp_path / "predictions.parquet"
    preds_df.write_parquet(preds_path)

    return str(prices_path), str(preds_path)


def test_backtester_run_basic(tmp_path):  # noqa: D103
    prices_path, preds_path = _write_sample_data(tmp_path)

    config = BacktestConfig(
        prices_path=prices_path,
        predictions_path=preds_path,
        pred_value_column="pred_10d",
        start_date=datetime(2023, 1, 2),
        end_date=datetime(2023, 1, 3),
        num_long=1,
        num_short=0,
        target_leverage=1.0,
        rank_power=0.0,  # 0.0 = equal weight
        rebalance_every_n_days=1,
        prediction_lag_days=1,
        fee_bps=0.0,
        slippage_bps=0.0,
        start_capital=100.0,
        verbose=False,
    )

    result = Backtester(config).run()

    assert result.daily.height == 2
    assert result.rebalance_positions.height == 2
    assert set(result.rebalance_positions["id"].unique()) == {"AAA"}
    assert result.stats["final_equity"] == pytest.approx(110.0)
    assert result.stats["total_return"] == pytest.approx(0.10, abs=1e-6)
    assert result.stats["avg_turnover"] == pytest.approx(1.0)


def test_get_valid_trading_dates_respects_bounds(tmp_path):
    prices_path, preds_path = _write_sample_data(tmp_path)

    backtester = Backtester(
        BacktestConfig(
            prices_path=prices_path,
            predictions_path=preds_path,
            start_date=datetime(2023, 1, 2),
            end_date=datetime(2023, 1, 2),
            prediction_lag_days=1,
        )
    )

    returns_wide = pl.DataFrame(
        {
            "date": [
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
                datetime(2023, 1, 3),
            ],
            "AAA": [None, 0.1, 0.1],
            "BBB": [None, -0.01, -0.0101],
        }
    )

    predictions = pl.DataFrame(
        {
            "pred_date": [
                datetime(2023, 1, 1),
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
            ]
        }
    )

    valid_dates = backtester._get_valid_trading_dates_from_returns(
        returns_wide, predictions
    )

    assert valid_dates == [datetime(2023, 1, 2)]


def test_backtest_optimizer_run_single_backtest(tmp_path):
    prices_path, preds_path = _write_sample_data(tmp_path)

    base_config = BacktestConfig(
        prices_path=prices_path,
        predictions_path=preds_path,
        pred_value_column="pred_10d",
        start_date=datetime(2023, 1, 2),
        end_date=datetime(2023, 1, 3),
        num_long=1,
        num_short=0,
        target_leverage=1.0,
        rank_power=0.0,  # 0.0 = equal weight
        rebalance_every_n_days=1,
        prediction_lag_days=1,
        fee_bps=0.0,
        slippage_bps=0.0,
        start_capital=100.0,
        verbose=False,
    )

    optimizer = BacktestOptimizer(base_config)
    optimizer._cache_file = str(tmp_path / "cache.json")

    params = {"num_long": 1, "num_short": 0, "leverage": 1.0, "rebalance_days": 1, "rank_power": 0.0}

    result = optimizer._run_single_backtest(params)

    assert result is not None
    assert result["num_long"] == 1
    assert result["num_short"] == 0
    assert result["leverage"] == 1.0
    assert result["rebalance_days"] == 1
    assert result["rank_power"] == 0.0  # 0.0 = equal weight
    assert result["final_equity"] == pytest.approx(110.0)
    assert result["sharpe"] >= 0
