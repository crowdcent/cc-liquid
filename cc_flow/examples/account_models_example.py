"""
Example usage of account domain models.

This script demonstrates how to create and use AccountInfo, Position,
and PortfolioSnapshot models with proper serialization.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import UTC, datetime
from decimal import Decimal

from domain.account import AccountInfo, PortfolioSnapshot, Position


def main() -> None:
    """Demonstrate account model usage."""

    # Create account information
    print("=" * 70)
    print("CREATING ACCOUNT INFO")
    print("=" * 70)

    account = AccountInfo(
        account_value=Decimal("100000.00"),
        total_position_value=Decimal("75000.00"),
        margin_used=Decimal("37500.00"),
        free_collateral=Decimal("62500.00"),
        cash_balance=Decimal("25000.00"),
        withdrawable=Decimal("20000.00"),
        current_leverage=Decimal("0.75"),
    )

    print(f"\nAccount Value: ${account.account_value:,.2f}")
    print(f"Current Leverage: {account.leverage_percentage:.1f}%")
    print(f"Free Collateral: ${account.free_collateral:,.2f}")

    # Create positions
    print("\n" + "=" * 70)
    print("CREATING POSITIONS")
    print("=" * 70)

    btc_position = Position(
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

    eth_position = Position(
        coin="ETH",
        side="SHORT",
        size=Decimal("20.0"),
        entry_price=Decimal("3000.00"),
        mark_price=Decimal("2900.00"),
        value=Decimal("58000.00"),
        unrealized_pnl=Decimal("2000.00"),
        return_pct=Decimal("0.0333"),
    )

    print("\nBTC Position:")
    print(f"  Side: {btc_position.side}")
    print(f"  Size: {btc_position.size} BTC (signed: {btc_position.signed_size})")
    print(f"  Entry: ${btc_position.entry_price:,.2f}")
    print(f"  Mark: ${btc_position.mark_price:,.2f}")
    print(f"  Unrealized P&L: ${btc_position.unrealized_pnl:,.2f}")
    print(f"  Return: {float(btc_position.return_pct) * 100:.2f}%")

    print("\nETH Position:")
    print(f"  Side: {eth_position.side}")
    print(f"  Size: {eth_position.size} ETH (signed: {eth_position.signed_size})")
    print(f"  Entry: ${eth_position.entry_price:,.2f}")
    print(f"  Mark: ${eth_position.mark_price:,.2f}")
    print(f"  Unrealized P&L: ${eth_position.unrealized_pnl:,.2f}")
    print(f"  Return: {float(eth_position.return_pct) * 100:.2f}%")

    # Create portfolio snapshot
    print("\n" + "=" * 70)
    print("CREATING PORTFOLIO SNAPSHOT")
    print("=" * 70)

    snapshot = PortfolioSnapshot(
        timestamp=datetime.now(UTC),
        account=account,
        positions=[btc_position, eth_position],
    )

    print(f"\nSnapshot Timestamp: {snapshot.timestamp}")
    print(f"Number of Positions: {len(snapshot.positions)}")
    print("\nPortfolio Metrics:")
    print(f"  Total Long Value: ${snapshot.total_long_value:,.2f}")
    print(f"  Total Short Value: ${snapshot.total_short_value:,.2f}")
    print(f"  Net Exposure: ${snapshot.net_exposure:,.2f}")
    print(f"  Total Unrealized P&L: ${snapshot.total_unrealized_pnl:,.2f}")

    # Demonstrate serialization
    print("\n" + "=" * 70)
    print("SERIALIZATION EXAMPLES")
    print("=" * 70)

    # model_dump() - returns dict with Decimal objects
    print("\n1. model_dump() - Internal dict with Decimals:")
    account_dict = account.model_dump()
    print(f"   Type: {type(account_dict)}")
    print(f"   account_value type: {type(account_dict['account_value'])}")
    print(f"   Sample: {{'account_value': {account_dict['account_value']}}}")

    # model_dump(mode="json") - returns JSON-compatible dict
    print("\n2. model_dump(mode='json') - JSON-compatible dict:")
    account_json_dict = account.model_dump(mode="json")
    print(f"   Type: {type(account_json_dict)}")
    print(f"   account_value type: {type(account_json_dict['account_value'])}")
    print(f"   Sample: {{'account_value': '{account_json_dict['account_value']}'}}")

    # model_dump_json() - returns JSON string
    print("\n3. model_dump_json() - JSON string:")
    position_json = btc_position.model_dump_json()
    print(f"   Type: {type(position_json)}")
    print(f"   Length: {len(position_json)} chars")
    print(f"   Preview: {position_json[:100]}...")

    # Nested serialization
    print("\n4. Nested model serialization (PortfolioSnapshot):")
    snapshot_dict = snapshot.model_dump(mode="json")
    print(f"   Keys: {list(snapshot_dict.keys())}")
    print(f"   Account type: {type(snapshot_dict['account'])}")
    print(f"   Positions type: {type(snapshot_dict['positions'])}")
    print(f"   Positions count: {len(snapshot_dict['positions'])}")

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
