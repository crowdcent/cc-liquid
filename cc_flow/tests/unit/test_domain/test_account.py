"""
Unit tests for account domain models.

Tests for AccountInfo, Position, and PortfolioSnapshot models following
TDD principles with >90% coverage target.
"""

from datetime import UTC, datetime
from decimal import Decimal

from cc_flow.domain.account import AccountInfo, PortfolioSnapshot, Position


class TestAccountInfo:
    """Test suite for AccountInfo model."""

    def test_valid_instantiation_with_required_fields(self):
        """Test creating AccountInfo with all required fields."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
        )

        assert account.account_value == Decimal("10000.00")
        assert account.total_position_value == Decimal("5000.00")
        assert account.margin_used == Decimal("2500.00")
        assert account.free_collateral == Decimal("7500.00")
        assert account.cash_balance == Decimal("5000.00")
        assert account.withdrawable == Decimal("5000.00")
        assert account.current_leverage == Decimal("0.5")

    def test_leverage_percentage_property(self):
        """Test leverage_percentage computed property."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
        )

        assert account.leverage_percentage == 50.0

    def test_leverage_percentage_with_high_leverage(self):
        """Test leverage_percentage with leverage > 1."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("25000.00"),
            margin_used=Decimal("12500.00"),
            free_collateral=Decimal("2500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("1000.00"),
            current_leverage=Decimal("2.5"),
        )

        assert account.leverage_percentage == 250.0

    def test_with_optional_cross_margin_fields(self):
        """Test AccountInfo with optional cross-margin fields."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
            cross_leverage=Decimal("0.3"),
            cross_margin_used=Decimal("1500.00"),
            cross_maintenance_margin=Decimal("500.00"),
        )

        assert account.cross_leverage == Decimal("0.3")
        assert account.cross_margin_used == Decimal("1500.00")
        assert account.cross_maintenance_margin == Decimal("500.00")

    def test_with_raw_data(self):
        """Test AccountInfo with raw_data for debugging."""
        raw_data = {
            "accountValue": "10000.00",
            "marginSummary": {"accountValue": "10000.00"},
        }

        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
            raw_data=raw_data,
        )

        assert account.raw_data == raw_data

    def test_decimal_precision_preserved(self):
        """Test that Decimal precision is preserved."""
        account = AccountInfo(
            account_value=Decimal("10000.123456789"),
            total_position_value=Decimal("5000.987654321"),
            margin_used=Decimal("2500.50"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.500000001"),
        )

        assert account.account_value == Decimal("10000.123456789")
        assert account.total_position_value == Decimal("5000.987654321")
        assert account.current_leverage == Decimal("0.500000001")

    def test_model_dump_returns_dict(self):
        """Test model_dump() returns proper dict."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
        )

        data = account.model_dump()
        assert isinstance(data, dict)
        assert data["account_value"] == Decimal("10000.00")

    def test_model_dump_json_mode(self):
        """Test model_dump(mode='json') for JSON-compatible output."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
        )

        data = account.model_dump(mode="json")
        assert isinstance(data, dict)
        # In JSON mode, Decimals should be converted to strings or floats
        assert isinstance(data["account_value"], (str, float))

    def test_model_dump_json_returns_string(self):
        """Test model_dump_json() returns JSON string."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
        )

        json_str = account.model_dump_json()
        assert isinstance(json_str, str)
        assert "10000" in json_str

    def test_mutability_configuration(self):
        """Test that frozen=False allows mutation."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("5000.00"),
            margin_used=Decimal("2500.00"),
            free_collateral=Decimal("7500.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("0.5"),
        )

        # Should be able to update since frozen=False
        account.account_value = Decimal("12000.00")
        assert account.account_value == Decimal("12000.00")

    def test_zero_account_value(self):
        """Test handling of zero account value edge case."""
        account = AccountInfo(
            account_value=Decimal("0.00"),
            total_position_value=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            free_collateral=Decimal("0.00"),
            cash_balance=Decimal("0.00"),
            withdrawable=Decimal("0.00"),
            current_leverage=Decimal("0.0"),
        )

        assert account.account_value == Decimal("0.00")
        assert account.leverage_percentage == 0.0


class TestPosition:
    """Test suite for Position model."""

    def test_long_position_valid_instantiation(self):
        """Test creating a LONG position with all required fields."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("52000.00"),
            value=Decimal("78000.00"),
            unrealized_pnl=Decimal("3000.00"),
            return_pct=Decimal("0.04"),
        )

        assert position.coin == "BTC"
        assert position.side == "LONG"
        assert position.size == Decimal("1.5")
        assert position.entry_price == Decimal("50000.00")
        assert position.mark_price == Decimal("52000.00")
        assert position.value == Decimal("78000.00")
        assert position.unrealized_pnl == Decimal("3000.00")
        assert position.return_pct == Decimal("0.04")

    def test_short_position_valid_instantiation(self):
        """Test creating a SHORT position with all required fields."""
        position = Position(
            coin="ETH",
            side="SHORT",
            size=Decimal("10.0"),
            entry_price=Decimal("3000.00"),
            mark_price=Decimal("2900.00"),
            value=Decimal("29000.00"),
            unrealized_pnl=Decimal("1000.00"),
            return_pct=Decimal("0.0333"),
        )

        assert position.coin == "ETH"
        assert position.side == "SHORT"
        assert position.size == Decimal("10.0")

    def test_long_position_signed_size(self):
        """Test signed_size property for LONG position returns positive."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("52000.00"),
            value=Decimal("78000.00"),
            unrealized_pnl=Decimal("3000.00"),
            return_pct=Decimal("0.04"),
        )

        assert position.signed_size == Decimal("1.5")

    def test_short_position_signed_size(self):
        """Test signed_size property for SHORT position returns negative."""
        position = Position(
            coin="ETH",
            side="SHORT",
            size=Decimal("10.0"),
            entry_price=Decimal("3000.00"),
            mark_price=Decimal("2900.00"),
            value=Decimal("29000.00"),
            unrealized_pnl=Decimal("1000.00"),
            return_pct=Decimal("0.0333"),
        )

        assert position.signed_size == Decimal("-10.0")

    def test_with_optional_liquidation_price(self):
        """Test Position with optional liquidation_price field."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("52000.00"),
            value=Decimal("78000.00"),
            unrealized_pnl=Decimal("3000.00"),
            return_pct=Decimal("0.04"),
            liquidation_price=Decimal("45000.00"),
        )

        assert position.liquidation_price == Decimal("45000.00")

    def test_with_optional_margin_used(self):
        """Test Position with optional margin_used field."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("52000.00"),
            value=Decimal("78000.00"),
            unrealized_pnl=Decimal("3000.00"),
            return_pct=Decimal("0.04"),
            margin_used=Decimal("15000.00"),
        )

        assert position.margin_used == Decimal("15000.00")

    def test_with_all_optional_fields(self):
        """Test Position with all optional fields populated."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("52000.00"),
            value=Decimal("78000.00"),
            unrealized_pnl=Decimal("3000.00"),
            return_pct=Decimal("0.04"),
            liquidation_price=Decimal("45000.00"),
            margin_used=Decimal("15000.00"),
        )

        assert position.liquidation_price == Decimal("45000.00")
        assert position.margin_used == Decimal("15000.00")

    def test_negative_pnl(self):
        """Test Position with negative unrealized PNL."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("48000.00"),
            value=Decimal("72000.00"),
            unrealized_pnl=Decimal("-3000.00"),
            return_pct=Decimal("-0.04"),
        )

        assert position.unrealized_pnl == Decimal("-3000.00")
        assert position.return_pct == Decimal("-0.04")

    def test_decimal_precision_preserved(self):
        """Test that Decimal precision is preserved in Position."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.123456789"),
            entry_price=Decimal("50000.123456"),
            mark_price=Decimal("52000.654321"),
            value=Decimal("78000.987654"),
            unrealized_pnl=Decimal("3000.111111"),
            return_pct=Decimal("0.040001"),
        )

        assert position.size == Decimal("1.123456789")
        assert position.entry_price == Decimal("50000.123456")

    def test_model_dump_serialization(self):
        """Test Position serialization with model_dump()."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("52000.00"),
            value=Decimal("78000.00"),
            unrealized_pnl=Decimal("3000.00"),
            return_pct=Decimal("0.04"),
        )

        data = position.model_dump()
        assert isinstance(data, dict)
        assert data["coin"] == "BTC"
        assert data["size"] == Decimal("1.5")

    def test_model_dump_json_mode(self):
        """Test Position serialization with model_dump(mode='json')."""
        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.5"),
            entry_price=Decimal("50000.00"),
            mark_price=Decimal("52000.00"),
            value=Decimal("78000.00"),
            unrealized_pnl=Decimal("3000.00"),
            return_pct=Decimal("0.04"),
        )

        data = position.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["coin"] == "BTC"


class TestPortfolioSnapshot:
    """Test suite for PortfolioSnapshot model."""

    def test_empty_portfolio_instantiation(self):
        """Test creating PortfolioSnapshot with no positions."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            free_collateral=Decimal("10000.00"),
            cash_balance=Decimal("10000.00"),
            withdrawable=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
        )

        snapshot = PortfolioSnapshot(account=account, positions=[])

        assert snapshot.account == account
        assert snapshot.positions == []
        assert isinstance(snapshot.timestamp, datetime)

    def test_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            free_collateral=Decimal("10000.00"),
            cash_balance=Decimal("10000.00"),
            withdrawable=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
        )

        snapshot = PortfolioSnapshot(account=account)

        assert isinstance(snapshot.timestamp, datetime)
        # Timestamp should be recent (within last minute)
        time_diff = (datetime.now(UTC) - snapshot.timestamp).total_seconds()
        assert time_diff < 60

    def test_custom_timestamp(self):
        """Test setting custom timestamp."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            free_collateral=Decimal("10000.00"),
            cash_balance=Decimal("10000.00"),
            withdrawable=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
        )

        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        snapshot = PortfolioSnapshot(account=account, timestamp=custom_time)

        assert snapshot.timestamp == custom_time

    def test_total_long_value_with_multiple_long_positions(self):
        """Test total_long_value with multiple LONG positions."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("10000.00"),
            margin_used=Decimal("5000.00"),
            free_collateral=Decimal("5000.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("1.0"),
        )

        positions = [
            Position(
                coin="BTC",
                side="LONG",
                size=Decimal("1.0"),
                entry_price=Decimal("50000.00"),
                mark_price=Decimal("52000.00"),
                value=Decimal("52000.00"),
                unrealized_pnl=Decimal("2000.00"),
                return_pct=Decimal("0.04"),
            ),
            Position(
                coin="ETH",
                side="LONG",
                size=Decimal("10.0"),
                entry_price=Decimal("3000.00"),
                mark_price=Decimal("3100.00"),
                value=Decimal("31000.00"),
                unrealized_pnl=Decimal("1000.00"),
                return_pct=Decimal("0.0333"),
            ),
        ]

        snapshot = PortfolioSnapshot(account=account, positions=positions)

        assert snapshot.total_long_value == Decimal("83000.00")

    def test_total_short_value_with_multiple_short_positions(self):
        """Test total_short_value with multiple SHORT positions."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("10000.00"),
            margin_used=Decimal("5000.00"),
            free_collateral=Decimal("5000.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("1.0"),
        )

        positions = [
            Position(
                coin="BTC",
                side="SHORT",
                size=Decimal("0.5"),
                entry_price=Decimal("50000.00"),
                mark_price=Decimal("48000.00"),
                value=Decimal("24000.00"),
                unrealized_pnl=Decimal("1000.00"),
                return_pct=Decimal("0.02"),
            ),
            Position(
                coin="ETH",
                side="SHORT",
                size=Decimal("5.0"),
                entry_price=Decimal("3000.00"),
                mark_price=Decimal("2900.00"),
                value=Decimal("14500.00"),
                unrealized_pnl=Decimal("500.00"),
                return_pct=Decimal("0.0333"),
            ),
        ]

        snapshot = PortfolioSnapshot(account=account, positions=positions)

        assert snapshot.total_short_value == Decimal("38500.00")

    def test_net_exposure_with_mixed_positions(self):
        """Test net_exposure calculation with mixed long/short positions."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("10000.00"),
            margin_used=Decimal("5000.00"),
            free_collateral=Decimal("5000.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("1.0"),
        )

        positions = [
            Position(
                coin="BTC",
                side="LONG",
                size=Decimal("1.0"),
                entry_price=Decimal("50000.00"),
                mark_price=Decimal("52000.00"),
                value=Decimal("52000.00"),
                unrealized_pnl=Decimal("2000.00"),
                return_pct=Decimal("0.04"),
            ),
            Position(
                coin="ETH",
                side="SHORT",
                size=Decimal("5.0"),
                entry_price=Decimal("3000.00"),
                mark_price=Decimal("2900.00"),
                value=Decimal("14500.00"),
                unrealized_pnl=Decimal("500.00"),
                return_pct=Decimal("0.0333"),
            ),
        ]

        snapshot = PortfolioSnapshot(account=account, positions=positions)

        # net_exposure = total_long_value - total_short_value
        # = 52000.00 - 14500.00 = 37500.00
        assert snapshot.net_exposure == Decimal("37500.00")

    def test_total_unrealized_pnl(self):
        """Test total_unrealized_pnl calculation."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("10000.00"),
            margin_used=Decimal("5000.00"),
            free_collateral=Decimal("5000.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("1.0"),
        )

        positions = [
            Position(
                coin="BTC",
                side="LONG",
                size=Decimal("1.0"),
                entry_price=Decimal("50000.00"),
                mark_price=Decimal("52000.00"),
                value=Decimal("52000.00"),
                unrealized_pnl=Decimal("2000.00"),
                return_pct=Decimal("0.04"),
            ),
            Position(
                coin="ETH",
                side="SHORT",
                size=Decimal("5.0"),
                entry_price=Decimal("3000.00"),
                mark_price=Decimal("2900.00"),
                value=Decimal("14500.00"),
                unrealized_pnl=Decimal("500.00"),
                return_pct=Decimal("0.0333"),
            ),
            Position(
                coin="SOL",
                side="LONG",
                size=Decimal("100.0"),
                entry_price=Decimal("100.00"),
                mark_price=Decimal("95.00"),
                value=Decimal("9500.00"),
                unrealized_pnl=Decimal("-500.00"),
                return_pct=Decimal("-0.05"),
            ),
        ]

        snapshot = PortfolioSnapshot(account=account, positions=positions)

        # total_unrealized_pnl = 2000 + 500 - 500 = 2000
        assert snapshot.total_unrealized_pnl == Decimal("2000.00")

    def test_all_computed_properties_with_empty_positions(self):
        """Test all computed properties return zero with empty positions."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            free_collateral=Decimal("10000.00"),
            cash_balance=Decimal("10000.00"),
            withdrawable=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
        )

        snapshot = PortfolioSnapshot(account=account, positions=[])

        assert snapshot.total_long_value == Decimal("0")
        assert snapshot.total_short_value == Decimal("0")
        assert snapshot.net_exposure == Decimal("0")
        assert snapshot.total_unrealized_pnl == Decimal("0")

    def test_serialization_with_nested_models(self):
        """Test model_dump() with nested AccountInfo and Position models."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("10000.00"),
            margin_used=Decimal("5000.00"),
            free_collateral=Decimal("5000.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("1.0"),
        )

        positions = [
            Position(
                coin="BTC",
                side="LONG",
                size=Decimal("1.0"),
                entry_price=Decimal("50000.00"),
                mark_price=Decimal("52000.00"),
                value=Decimal("52000.00"),
                unrealized_pnl=Decimal("2000.00"),
                return_pct=Decimal("0.04"),
            ),
        ]

        snapshot = PortfolioSnapshot(account=account, positions=positions)
        data = snapshot.model_dump()

        assert isinstance(data, dict)
        assert "account" in data
        assert "positions" in data
        assert isinstance(data["account"], dict)
        assert isinstance(data["positions"], list)
        assert len(data["positions"]) == 1

    def test_model_dump_json_mode(self):
        """Test model_dump(mode='json') for JSON-compatible output."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            free_collateral=Decimal("10000.00"),
            cash_balance=Decimal("10000.00"),
            withdrawable=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
        )

        snapshot = PortfolioSnapshot(account=account)
        data = snapshot.model_dump(mode="json")

        assert isinstance(data, dict)
        assert "timestamp" in data
        # Timestamp should be serialized as string in JSON mode
        assert isinstance(data["timestamp"], str)

    def test_model_dump_json_returns_string(self):
        """Test model_dump_json() returns JSON string."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            free_collateral=Decimal("10000.00"),
            cash_balance=Decimal("10000.00"),
            withdrawable=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
        )

        snapshot = PortfolioSnapshot(account=account)
        json_str = snapshot.model_dump_json()

        assert isinstance(json_str, str)
        assert "account_value" in json_str
        assert "timestamp" in json_str

    def test_negative_net_exposure(self):
        """Test net_exposure with more short value than long value."""
        account = AccountInfo(
            account_value=Decimal("10000.00"),
            total_position_value=Decimal("10000.00"),
            margin_used=Decimal("5000.00"),
            free_collateral=Decimal("5000.00"),
            cash_balance=Decimal("5000.00"),
            withdrawable=Decimal("5000.00"),
            current_leverage=Decimal("1.0"),
        )

        positions = [
            Position(
                coin="BTC",
                side="LONG",
                size=Decimal("0.5"),
                entry_price=Decimal("50000.00"),
                mark_price=Decimal("52000.00"),
                value=Decimal("26000.00"),
                unrealized_pnl=Decimal("1000.00"),
                return_pct=Decimal("0.04"),
            ),
            Position(
                coin="ETH",
                side="SHORT",
                size=Decimal("15.0"),
                entry_price=Decimal("3000.00"),
                mark_price=Decimal("2900.00"),
                value=Decimal("43500.00"),
                unrealized_pnl=Decimal("1500.00"),
                return_pct=Decimal("0.0333"),
            ),
        ]

        snapshot = PortfolioSnapshot(account=account, positions=positions)

        # net_exposure = 26000 - 43500 = -17500
        assert snapshot.net_exposure == Decimal("-17500.00")

    def test_very_large_decimals(self):
        """Test handling of very large decimal values."""
        account = AccountInfo(
            account_value=Decimal("9999999999.99"),
            total_position_value=Decimal("5000000000.00"),
            margin_used=Decimal("2500000000.00"),
            free_collateral=Decimal("7500000000.00"),
            cash_balance=Decimal("5000000000.00"),
            withdrawable=Decimal("5000000000.00"),
            current_leverage=Decimal("0.5"),
        )

        positions = [
            Position(
                coin="BTC",
                side="LONG",
                size=Decimal("100000.0"),
                entry_price=Decimal("50000.00"),
                mark_price=Decimal("52000.00"),
                value=Decimal("5200000000.00"),
                unrealized_pnl=Decimal("200000000.00"),
                return_pct=Decimal("0.04"),
            ),
        ]

        snapshot = PortfolioSnapshot(account=account, positions=positions)

        assert snapshot.total_long_value == Decimal("5200000000.00")
        assert snapshot.total_unrealized_pnl == Decimal("200000000.00")
