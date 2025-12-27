"""Entry point for cc-liquid TUI."""

from pathlib import Path

from cc_flow.config.defaults import get_default_config
from cc_flow.config.loader import ConfigLoader
from cc_flow.data_sources.mock import MockDataSource
from cc_flow.exchanges.mock import MockExchange
from cc_flow.ui.app import CCLiquidApp
from cc_flow.utils.logger_config import log


def main():
    """Run the TUI application."""
    # Load configuration
    config_path = Path.cwd() / "cc-liquid-config.yaml"

    if config_path.exists():
        log.info(f"Loading config from {config_path}")
        loader = ConfigLoader(config_path=str(config_path))
        config = loader.load_config()
    else:
        log.info("Using default configuration")
        config = get_default_config()

    # Create mock services for testing
    # In production, these would be real Hyperliquid connections
    exchange = MockExchange(
        account_value=10000,
        positions=[],
        prices={"BTC": 50000, "ETH": 3000},
    )

    data_source = MockDataSource(num_assets=20)

    log.info("Starting cc-liquid TUI...")

    # Run app
    app = CCLiquidApp(
        exchange=exchange,
        data_source=data_source,
        config=config,
    )
    app.run()


if __name__ == "__main__":
    main()
