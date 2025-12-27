"""Tests for history command and PNL aggregation."""

import pytest
from datetime import datetime, timezone


# Sample fill history data 
@pytest.fixture
def sample_fills():
    """Sample fill history with various PNL scenarios."""
    return [
        # BTC trades
        {
            "time": int(datetime(2024, 10, 26, 4, 48, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "BTC",
            "side": "A",
            "dir": "Close Long",
            "sz": "0.0004",
            "px": "110577.00",
            "fee": "0.02",
            "closedPnl": "-5.91",
            "oid": 4172812081,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 55, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "BTC",
            "side": "B",
            "dir": "Open Long",
            "sz": "0.0004",
            "px": "125341.00",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4026434298,
        },
        # SOL trades
        {
            "time": int(datetime(2024, 10, 26, 4, 46, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "SOL",
            "side": "B",
            "dir": "Open Long",
            "sz": "0.1600",
            "px": "189.00",
            "fee": "0.01",
            "closedPnl": "0.0",
            "oid": 4172807304,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 55, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "SOL",
            "side": "B",
            "dir": "Open Long",
            "sz": "0.2100",
            "px": "235.20",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4026434782,
        },
        # ETH trades
        {
            "time": int(datetime(2024, 10, 26, 4, 46, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "ETH",
            "side": "B",
            "dir": "Open Long",
            "sz": "0.0079",
            "px": "3851.40",
            "fee": "0.01",
            "closedPnl": "0.0",
            "oid": 4172805889,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 55, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "ETH",
            "side": "B",
            "dir": "Open Long",
            "sz": "0.0100",
            "px": "4702.60",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4026434667,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 55, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "ETH",
            "side": "B",
            "dir": "Open Long",
            "sz": "0.0006",
            "px": "4703.20",
            "fee": "0.00",
            "closedPnl": "0.0",
            "oid": 4026434667,
        },
        # APE - closed with loss
        {
            "time": int(datetime(2024, 10, 26, 4, 45, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "APE",
            "side": "A",
            "dir": "Close Long",
            "sz": "112.6000",
            "px": "0.44",
            "fee": "0.02",
            "closedPnl": "-0.15",
            "oid": 4172805310,
        },
        {
            "time": int(datetime(2024, 10, 26, 4, 27, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "APE",
            "side": "B",
            "dir": "Open Long",
            "sz": "112.6000",
            "px": "0.44",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4172769095,
        },
        # GRASS - closed with profit
        {
            "time": int(datetime(2024, 10, 26, 4, 45, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "GRASS",
            "side": "B",
            "dir": "Close Short",
            "sz": "114.9000",
            "px": "0.43",
            "fee": "0.02",
            "closedPnl": "0.10",
            "oid": 4172805253,
        },
        {
            "time": int(datetime(2024, 10, 26, 4, 27, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "GRASS",
            "side": "A",
            "dir": "Open Short",
            "sz": "114.9000",
            "px": "0.43",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4172769529,
        },
        # MAV - closed with profit
        {
            "time": int(datetime(2024, 10, 26, 4, 27, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "MAV",
            "side": "B",
            "dir": "Close Short",
            "sz": "844.0000",
            "px": "0.04",
            "fee": "0.01",
            "closedPnl": "17.26",
            "oid": 4172768974,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 56, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "MAV",
            "side": "A",
            "dir": "Open Short",
            "sz": "844.0000",
            "px": "0.06",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4026435452,
        },
        # APT - closed with loss
        {
            "time": int(datetime(2024, 10, 26, 4, 27, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "APT",
            "side": "A",
            "dir": "Close Long",
            "sz": "9.2400",
            "px": "3.30",
            "fee": "0.01",
            "closedPnl": "-19.45",
            "oid": 4172768912,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 55, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "APT",
            "side": "B",
            "dir": "Open Long",
            "sz": "9.2400",
            "px": "5.41",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4026434856,
        },
        # RSR - closed with profit
        {
            "time": int(datetime(2024, 10, 26, 4, 27, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "RSR",
            "side": "B",
            "dir": "Close Short",
            "sz": "7629.0000",
            "px": "0.01",
            "fee": "0.02",
            "closedPnl": "8.51",
            "oid": 4172768705,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 56, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "RSR",
            "side": "A",
            "dir": "Open Short",
            "sz": "7629.0000",
            "px": "0.01",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4026436090,
        },
        # BNB - closed with loss
        {
            "time": int(datetime(2024, 10, 26, 4, 27, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "BNB",
            "side": "A",
            "dir": "Close Long",
            "sz": "0.0410",
            "px": "1118.50",
            "fee": "0.02",
            "closedPnl": "-4.34",
            "oid": 4172768002,
        },
        {
            "time": int(datetime(2024, 10, 6, 19, 55, tzinfo=timezone.utc).timestamp() * 1000),
            "coin": "BNB",
            "side": "B",
            "dir": "Open Long",
            "sz": "0.0410",
            "px": "1224.40",
            "fee": "0.02",
            "closedPnl": "0.0",
            "oid": 4026433914,
        },
    ]


@pytest.fixture
def sample_positions():
    """Sample current open positions for unrealized PNL."""
    from cc_liquid.trader import Position

    return [
        Position(
            coin="SOL",
            size=0.37,  # 0.16 + 0.21 from fills
            side="LONG",
            entry_price=215.54,  # weighted average
            mark_price=220.00,
            unrealized_pnl=1.65,
            value=81.40,
            return_pct=0.02,
            liquidation_price=None,
            margin_used=81.35,
        ),
        Position(
            coin="ETH",
            size=0.0185,  # 0.0079 + 0.01 + 0.0006
            side="LONG",
            entry_price=4500.00,
            mark_price=4600.00,
            unrealized_pnl=1.85,
            value=85.10,
            return_pct=0.02,
            liquidation_price=None,
            margin_used=83.25,
        ),
        Position(
            coin="BTC",
            size=0.0,  # Closed position, no unrealized PNL
            side="LONG",
            entry_price=0.0,
            mark_price=110000.00,
            unrealized_pnl=0.0,
            value=0.0,
            return_pct=0.0,
            liquidation_price=None,
            margin_used=0.0,
        ),
    ]


def test_aggregate_pnl_by_currency(sample_fills, sample_positions):
    """Test PNL aggregation by currency."""
    from cc_liquid.trader import aggregate_pnl_by_currency

    # Aggregate PNL from fills and positions
    pnl_summary = aggregate_pnl_by_currency(sample_fills, sample_positions)

    # Check that we have entries for all currencies with activity
    assert "BTC" in pnl_summary
    assert "SOL" in pnl_summary
    assert "ETH" in pnl_summary
    assert "APE" in pnl_summary
    assert "GRASS" in pnl_summary
    assert "MAV" in pnl_summary
    assert "APT" in pnl_summary
    assert "RSR" in pnl_summary
    assert "BNB" in pnl_summary

    # Check realized PNL calculations
    assert pnl_summary["BTC"]["realized_pnl"] == -5.91
    assert pnl_summary["APE"]["realized_pnl"] == -0.15
    assert pnl_summary["GRASS"]["realized_pnl"] == 0.10
    assert pnl_summary["MAV"]["realized_pnl"] == 17.26
    assert pnl_summary["APT"]["realized_pnl"] == -19.45
    assert pnl_summary["RSR"]["realized_pnl"] == 8.51
    assert pnl_summary["BNB"]["realized_pnl"] == -4.34

    # SOL and ETH have no closed positions, only opens
    assert pnl_summary["SOL"]["realized_pnl"] == 0.0
    assert pnl_summary["ETH"]["realized_pnl"] == 0.0

    # Check unrealized PNL from positions
    assert pnl_summary["SOL"]["unrealized_pnl"] == 1.65
    assert pnl_summary["ETH"]["unrealized_pnl"] == 1.85
    assert pnl_summary["BTC"]["unrealized_pnl"] == 0.0  # Closed position

    # Currencies with no open positions should have 0 unrealized PNL
    assert pnl_summary["APE"]["unrealized_pnl"] == 0.0
    assert pnl_summary["MAV"]["unrealized_pnl"] == 0.0


def test_aggregate_pnl_total():
    """Test total PNL calculation."""
    from cc_liquid.trader import aggregate_pnl_by_currency

    fills = [
        {"coin": "BTC", "closedPnl": "10.5", "fee": "0.01", "sz": "1.0", "px": "100.0"},
        {"coin": "ETH", "closedPnl": "-5.3", "fee": "0.02", "sz": "2.0", "px": "50.0"},
        {"coin": "BTC", "closedPnl": "2.1", "fee": "0.01", "sz": "0.5", "px": "100.0"},
    ]

    positions = []

    pnl_summary = aggregate_pnl_by_currency(fills, positions)

    # Calculate totals
    total_realized = sum(item["realized_pnl"] for item in pnl_summary.values())
    total_unrealized = sum(item["unrealized_pnl"] for item in pnl_summary.values())

    assert total_realized == pytest.approx(7.3)  # 10.5 - 5.3 + 2.1
    assert total_unrealized == 0.0


def test_aggregate_pnl_with_time_filter(sample_fills):
    """Test PNL aggregation with time range filtering."""
    from cc_liquid.trader import aggregate_pnl_by_currency
    from datetime import datetime, timezone

    # Filter fills after Oct 26, 2024
    cutoff = int(datetime(2024, 10, 26, tzinfo=timezone.utc).timestamp() * 1000)
    filtered_fills = [f for f in sample_fills if f["time"] >= cutoff]

    pnl_summary = aggregate_pnl_by_currency(filtered_fills, [])

    # Should only include trades from Oct 26
    # BTC close: -5.91
    # APE close: -0.15
    # GRASS close: 0.10
    # MAV close: 17.26
    # APT close: -19.45
    # RSR close: 8.51
    # BNB close: -4.34

    total_realized = sum(item["realized_pnl"] for item in pnl_summary.values())
    assert total_realized == pytest.approx(-5.91 - 0.15 + 0.10 + 17.26 - 19.45 + 8.51 - 4.34)


def test_filter_fills_by_coin(sample_fills):
    """Test filtering fills by specific coin."""
    btc_fills = [f for f in sample_fills if f["coin"] == "BTC"]

    assert len(btc_fills) == 2
    assert all(f["coin"] == "BTC" for f in btc_fills)

    eth_fills = [f for f in sample_fills if f["coin"] == "ETH"]
    assert len(eth_fills) == 3
    assert all(f["coin"] == "ETH" for f in eth_fills)


def test_aggregate_pnl_empty_fills():
    """Test PNL aggregation with no fills."""
    from cc_liquid.trader import aggregate_pnl_by_currency

    pnl_summary = aggregate_pnl_by_currency([], [])
    assert pnl_summary == {}


def test_aggregate_pnl_sorting():
    """Test that PNL summary is sorted alphabetically by currency."""
    from cc_liquid.trader import aggregate_pnl_by_currency

    fills = [
        {"coin": "ZEC", "closedPnl": "1.0", "fee": "0.01", "sz": "1.0", "px": "10.0"},
        {"coin": "APE", "closedPnl": "2.0", "fee": "0.01", "sz": "1.0", "px": "10.0"},
        {"coin": "BTC", "closedPnl": "3.0", "fee": "0.01", "sz": "1.0", "px": "10.0"},
        {"coin": "ETH", "closedPnl": "4.0", "fee": "0.01", "sz": "1.0", "px": "10.0"},
    ]

    pnl_summary = aggregate_pnl_by_currency(fills, [])

    # Check alphabetical ordering
    keys = list(pnl_summary.keys())
    assert keys == sorted(keys)
    assert keys == ["APE", "BTC", "ETH", "ZEC"]


def test_aggregate_pnl_fees_and_volume():
    """Test that fees and volume are correctly aggregated."""
    from cc_liquid.trader import aggregate_pnl_by_currency

    fills = [
        {"coin": "BTC", "closedPnl": "10.5", "fee": "0.05", "sz": "1.0", "px": "50000.0"},
        {"coin": "BTC", "closedPnl": "2.1", "fee": "0.03", "sz": "0.5", "px": "50000.0"},
        {"coin": "ETH", "closedPnl": "-5.3", "fee": "0.10", "sz": "10.0", "px": "3000.0"},
    ]

    positions = []

    pnl_summary = aggregate_pnl_by_currency(fills, positions)

    # Check BTC aggregation: two trades
    # Fees: 0.05 + 0.03 = 0.08
    # Volume: (1.0 * 50000) + (0.5 * 50000) = 50000 + 25000 = 75000
    assert pnl_summary["BTC"]["fees"] == pytest.approx(0.08)
    assert pnl_summary["BTC"]["volume"] == pytest.approx(75000.0)

    # Check ETH aggregation: one trade
    # Fees: 0.10
    # Volume: 10.0 * 3000 = 30000
    assert pnl_summary["ETH"]["fees"] == pytest.approx(0.10)
    assert pnl_summary["ETH"]["volume"] == pytest.approx(30000.0)
