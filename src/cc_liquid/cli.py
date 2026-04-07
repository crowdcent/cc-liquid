"""Command-line interface for cc-liquid."""

import os
import yaml
import time
import traceback
from datetime import datetime, timezone, timedelta
import subprocess
import shutil
import shlex

import click
from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    MofNCompleteColumn,
)
from typing import Any

from .cli_callbacks import RichCLICallbacks
from .cli_display import (
    create_dashboard_layout,
    create_config_panel,
    create_header_panel,
    create_setup_welcome_panel,
    create_setup_summary_panel,
    display_portfolio,
    display_file_summary,
    display_backtest_summary,
    show_pre_alpha_warning,
    display_optimization_results,
    display_optimization_contours,
)
from .backtester import BacktestOptimizer, BacktestConfig, Backtester
from .config import config
from .config import apply_cli_overrides
from .data_loader import DataLoader
from .trader import CCLiquid
from .completion import detect_shell_from_env, install_completion


TMUX_SESSION_NAME = "cc-liquid"
TMUX_WINDOW_NAME = "cc-liquid"


@click.group()
def cli():
    """cc-liquid - A metamodel-based rebalancer for Hyperliquid."""
    # Suppress the pre-alpha banner during Click's completion mode to avoid
    # corrupting the generated completion script output.
    in_completion_mode = any(k.endswith("_COMPLETE") for k in os.environ)
    if not in_completion_mode:
        show_pre_alpha_warning()


@cli.command(name="init")
@click.option(
    "--non-interactive", is_flag=True, help="Skip interactive setup, use defaults"
)
def init_cmd(non_interactive: bool):
    """Interactive setup wizard for first-time users.

    Guides you through creating config files with validation and helpful defaults.
    """
    console = Console()
    from rich.prompt import Prompt, Confirm

    # Check existing files
    cfg_path = "cc-liquid-config.yaml"
    env_path = ".env"

    if os.path.exists(cfg_path) or os.path.exists(env_path):
        existing_files = []
        if os.path.exists(cfg_path):
            existing_files.append(cfg_path)
        if os.path.exists(env_path):
            existing_files.append(env_path)

        console.print(
            f"\n[yellow]⚠️  Found existing files: {', '.join(existing_files)}[/yellow]"
        )
        if not non_interactive:
            if not Confirm.ask("Overwrite existing files?", default=False):
                console.print("[red]Setup cancelled.[/red]")
                return

    # Gather all configuration based on mode
    if non_interactive:
        # All defaults in one place for non-interactive mode
        is_testnet = True
        data_source = "crowdcent"
        crowdcent_key = ""
        hyper_key_placeholder = "0x..."
        owner_address = None
        vault_address = None
        num_long = 10
        num_short = 10
        leverage = 1.0
    else:
        # Interactive flow
        console.print(create_setup_welcome_panel())

        # Step 1: Environment
        console.print("\n[bold]Step 1: Choose Environment[/bold]")
        console.print("[dim]Testnet is recommended for first-time users[/dim]")
        is_testnet = Confirm.ask("Use testnet?", default=True)

        # Step 2: Data source
        console.print("\n[bold]Step 2: Data Source[/bold]")
        console.print("Available sources:")
        console.print(
            "  • [cyan]crowdcent[/cyan] - CrowdCent metamodel (requires API key)"
        )
        console.print("  • [cyan]numerai[/cyan] - Numerai crypto signals (free)")
        console.print("  • [cyan]local[/cyan] - Your own prediction file")

        data_source = Prompt.ask(
            "Choose data source",
            choices=["crowdcent", "numerai", "local"],
            default="crowdcent",
        )

        # Step 3: API keys
        console.print("\n[bold]Step 3: API Keys[/bold]")

        crowdcent_key = ""
        if data_source == "crowdcent":
            console.print("\n[cyan]CrowdCent API Key[/cyan]")
            console.print("[dim]Get from: https://crowdcent.com/profile[/dim]")
            crowdcent_key = Prompt.ask(
                "Enter CrowdCent API key (or press Enter to add later)",
                default="",
                show_default=False,
            )

        console.print("\n[cyan]Hyperliquid Private Key[/cyan]")
        console.print("[dim]Get from: https://app.hyperliquid.xyz/API[/dim]")
        console.print(
            "[yellow]⚠️  Use an agent wallet key, not your main wallet![/yellow]"
        )
        hyper_key_input = Prompt.ask(
            "Enter Hyperliquid private key (or press Enter to add later)",
            default="",
            show_default=False,
            password=True,  # Hide input for security
        )
        hyper_key_placeholder = hyper_key_input if hyper_key_input else "0x..."

        # Step 4: Addresses
        console.print("\n[bold]Step 4: Addresses[/bold]")
        console.print("[dim]Leave blank to fill in later[/dim]")

        owner_address = Prompt.ask(
            "Owner address (your main wallet, NOT the agent wallet)",
            default="",
            show_default=False,
        )
        owner_address = owner_address if owner_address else None

        vault_address = Prompt.ask(
            "Vault address (optional, for managed vaults)",
            default="",
            show_default=False,
        )
        vault_address = vault_address if vault_address else None

        # Step 5: Portfolio settings
        console.print("\n[bold]Step 5: Portfolio Settings[/bold]")

        num_long = int(Prompt.ask("Number of long positions", default="10"))
        num_short = int(Prompt.ask("Number of short positions", default="10"))

        console.print("\n[yellow]⚠️  Leverage Warning:[/yellow]")
        console.print("[dim]1.0 = no leverage (safest)[/dim]")
        console.print("[dim]2.0 = 2x leverage (moderate risk)[/dim]")
        console.print("[dim]3.0+ = high risk of liquidation[/dim]")
        leverage = float(Prompt.ask("Target leverage", default="1.0"))

    # Compose configurations
    yaml_cfg: dict[str, Any] = {
        "active_profile": "default",
        "profiles": {
            "default": {
                "owner": owner_address,
                "vault": vault_address,
                "signer_env": "HYPERLIQUID_PRIVATE_KEY",
            }
        },
        "is_testnet": is_testnet,
        "data": {
            "source": data_source,
            "path": "predictions.parquet",
            **(
                {
                    "date_column": "date",
                    "asset_id_column": "symbol",
                    "prediction_column": "prediction",
                }
                if data_source == "numerai"
                else {
                    "date_column": "release_date",
                    "asset_id_column": "id",
                    "prediction_column": "pred_30d",
                }
            ),
        },
        "portfolio": {
            "num_long": num_long,
            "num_short": num_short,
            "target_leverage": leverage,
            "rebalancing": {"every_n_days": 10, "at_time": "18:15"},
        },
        "execution": {"slippage_tolerance": 0.005, "min_trade_value": 10.0},
    }

    env_lines = [
        "# Secrets only - NEVER commit this file to git!",
        "# Add to .gitignore immediately",
        "",
        "# CrowdCent API (https://crowdcent.com/profile)",
        f"CROWDCENT_API_KEY={crowdcent_key}",
        "",
        "# Hyperliquid Agent Wallet Private Key (https://app.hyperliquid.xyz/API)",
        "# ⚠️  Use an agent wallet, NOT your main wallet!",
        f"HYPERLIQUID_PRIVATE_KEY={hyper_key_placeholder}",
    ]

    # Write files
    try:
        with open(cfg_path, "w") as f:
            yaml.safe_dump(yaml_cfg, f, sort_keys=False)
        console.print(f"\n[green]✓[/green] Created [cyan]{cfg_path}[/cyan]")
    except Exception as e:
        console.print(f"[red]✗ Failed to write {cfg_path}:[/red] {e}")
        raise SystemExit(1)

    try:
        with open(env_path, "w") as f:
            f.write("\n".join(env_lines) + "\n")
        console.print(f"[green]✓[/green] Created [cyan]{env_path}[/cyan]")
    except Exception as e:
        console.print(f"[red]✗ Failed to write {env_path}:[/red] {e}")
        raise SystemExit(1)

    # Add to .gitignore if it exists
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            gitignore_content = f.read()
        if ".env" not in gitignore_content:
            with open(".gitignore", "a") as f:
                f.write("\n# cc-liquid secrets\n.env\n")
            console.print("[green]✓[/green] Added .env to .gitignore")

    # Summary and next steps
    summary = create_setup_summary_panel(
        is_testnet=is_testnet,
        data_source=data_source,
        num_long=num_long,
        num_short=num_short,
        leverage=leverage,
    )
    console.print("\n")
    console.print(summary)


@cli.command(name="config")
def show_config():
    """Show the current configuration."""
    console = Console()
    config_dict = config.to_dict()
    panel = create_config_panel(config_dict)
    console.print(panel)


@cli.group()
def completion():
    """Shell completion utilities."""


@completion.command(name="install")
@click.option(
    "--shell",
    "shell_opt",
    type=click.Choice(["bash", "zsh", "fish"], case_sensitive=False),
    default=None,
    help="Target shell. Defaults to auto-detect from $SHELL.",
)
@click.option(
    "--prog-name",
    default="cc-liquid",
    show_default=True,
    help="Program name to install completion for (as installed on PATH).",
)
def completion_install(shell_opt: str | None, prog_name: str):
    """Install shell completion for the current user.

    Writes the generated completion script to a standard location and, for
    Bash/Zsh, appends a source line to the user's rc file idempotently.
    """
    console = Console()
    shell = shell_opt or detect_shell_from_env()
    if shell is None:
        console.print(
            "[red]Could not detect shell from $SHELL. Specify with[/red] "
            "[bold]--shell {bash|zsh|fish}[/bold]."
        )
        raise SystemExit(2)

    result = install_completion(prog_name, shell)

    console.print(
        f"[green]✓[/green] Installed completion for [bold]{shell}[/bold] at "
        f"[cyan]{result.script_path}[/cyan]"
        + (" (updated)" if result.script_written else " (no changes)")
    )

    if result.rc_path is not None:
        console.print(
            f"[blue]•[/blue] Ensured rc entry in [cyan]{result.rc_path}[/cyan] "
            + ("(added)" if result.rc_line_added else "(already present)")
        )

    console.print(
        "[dim]Restart your shell or 'source' your rc file to activate completion.[/dim]"
    )


@cli.group()
def profile():
    """Manage configuration profiles (owner/vault/signer)."""


@profile.command(name="list")
def profile_list():
    """List available profiles from YAML and highlight the active one."""
    console = Console()
    profiles = config.profiles or {}
    if not profiles:
        console.print("[yellow]No profiles found in cc-liquid-config.yaml[/yellow]")
        return
    from rich.table import Table

    table = Table(title="Profiles", show_lines=False, header_style="bold cyan")
    table.add_column("NAME", style="cyan")
    table.add_column("OWNER")
    table.add_column("VAULT")
    table.add_column("SIGNER ENV")
    for name, prof in profiles.items():
        owner = (prof or {}).get("owner") or "-"
        vault = (prof or {}).get("vault") or "-"
        signer_env = (prof or {}).get("signer_env", "HYPERLIQUID_PRIVATE_KEY")
        label = f"[bold]{name}[/bold]" + (
            " [green](active)[/green]" if name == config.active_profile else ""
        )
        table.add_row(label, owner, vault, signer_env)
    console.print(table)


@profile.command(name="show")
@click.argument("name", required=False)
def profile_show(name: str | None):
    """Show details for a profile (defaults to active)."""
    console = Console()
    target = name or config.active_profile
    if not target:
        console.print("[red]No active profile set and no name provided[/red]")
        raise SystemExit(2)
    prof = (config.profiles or {}).get(target)
    if prof is None:
        console.print(f"[red]Profile '{target}' not found[/red]")
        raise SystemExit(2)
    data = {
        "name": target,
        "owner": prof.get("owner"),
        "vault": prof.get("vault"),
        "signer_env": prof.get("signer_env", "HYPERLIQUID_PRIVATE_KEY"),
        "is_active": target == config.active_profile,
    }
    panel = create_config_panel(
        {
            "is_testnet": config.is_testnet,
            "profile": {
                "active": data["name"] if data["is_active"] else config.active_profile,
                "owner": data["owner"],
                "vault": data["vault"],
                "signer_env": data["signer_env"],
            },
            "data": config.data.__dict__,
            "portfolio": config.portfolio.__dict__
            | {"rebalancing": config.portfolio.rebalancing.__dict__},
            "execution": config.execution.__dict__,
        }
    )
    console.print(panel)


@profile.command(name="use")
@click.argument("name", required=True)
def profile_use(name: str):
    """Set active profile and persist to YAML."""
    console = Console()
    profiles = config.profiles or {}
    if name not in profiles:
        console.print(f"[red]Profile '{name}' not found in cc-liquid-config.yaml[/red]")
        raise SystemExit(2)

    # Update file
    cfg_path = "cc-liquid-config.yaml"
    try:
        y: dict = {}
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                y = yaml.safe_load(f) or {}
        y["active_profile"] = name
        with open(cfg_path, "w") as f:
            yaml.safe_dump(y, f, sort_keys=False)
    except Exception as e:
        console.print(f"[red]Failed to update {cfg_path}: {e}[/red]")
        raise SystemExit(1)

    # Update runtime
    config.active_profile = name
    try:
        config.refresh_runtime()
    except Exception as e:
        console.print(f"[red]Failed to activate profile: {e}[/red]")
        raise SystemExit(1)
    console.print(f"[green]✓[/green] Active profile set to [bold]{name}[/bold]")


@cli.command()
def account():
    """Show comprehensive account and positions summary."""
    console = Console()
    trader = CCLiquid(config, callbacks=RichCLICallbacks())

    # Get structured portfolio info
    portfolio = trader.get_portfolio_info()
    
    # Get open orders
    open_orders = trader.get_open_orders()

    # Display using reusable display function with config and open orders
    display_portfolio(portfolio, console, config.to_dict(), open_orders=open_orders)


@cli.command()
def orders():
    """Show current open orders."""
    console = Console()
    trader = CCLiquid(config, callbacks=RichCLICallbacks())

    try:
        open_orders = trader.get_open_orders()

        if not open_orders:
            console.print("[yellow]No open orders[/yellow]")
            return

        from rich.table import Table

        table = Table(title="Open Orders", show_header=True, header_style="bold cyan")
        table.add_column("OID", style="dim")
        table.add_column("COIN", style="cyan")
        table.add_column("SIDE", justify="center")
        table.add_column("SIZE", justify="right")
        table.add_column("LIMIT PX", justify="right")
        table.add_column("TIMESTAMP", justify="right")

        for order in open_orders:
            side = "BUY" if order["side"] == "B" else "SELL"
            side_style = "green" if side == "BUY" else "red"
            timestamp = datetime.fromtimestamp(order["timestamp"] / 1000).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            table.add_row(
                str(order["oid"]),
                order["coin"],
                f"[{side_style}]{side}[/{side_style}]",
                order["sz"],
                f"${float(order['limitPx']):,.2f}",
                timestamp,
            )

        console.print(table)
        console.print(f"\n[cyan]Total open orders: {len(open_orders)}[/cyan]")

    except Exception as e:
        console.print(f"[red]✗ Error fetching orders:[/red] {e}")
        raise


@cli.command(name="cancel-orders")
@click.option("--coin", help="Cancel orders for specific coin only")
@click.option("--skip-confirm", is_flag=True, help="Skip confirmation prompt")
def cancel_orders(coin, skip_confirm):
    """Cancel open orders."""
    console = Console()
    trader = CCLiquid(config, callbacks=RichCLICallbacks())

    try:
        # Get open orders first
        open_orders = trader.get_open_orders()

        if not open_orders:
            console.print("[yellow]No open orders to cancel[/yellow]")
            return

        # Filter by coin if specified
        if coin:
            orders_to_show = [o for o in open_orders if o["coin"] == coin]
            if not orders_to_show:
                console.print(f"[yellow]No open orders found for {coin}[/yellow]")
                return
        else:
            orders_to_show = open_orders

        # Show orders to be cancelled
        from rich.table import Table

        table = Table(title="Orders to Cancel", show_header=True, header_style="bold yellow")
        table.add_column("COIN", style="cyan")
        table.add_column("SIDE", justify="center")
        table.add_column("SIZE", justify="right")
        table.add_column("LIMIT PX", justify="right")

        for order in orders_to_show:
            side = "BUY" if order["side"] == "B" else "SELL"
            side_style = "green" if side == "BUY" else "red"

            table.add_row(
                order["coin"],
                f"[{side_style}]{side}[/{side_style}]",
                order["sz"],
                f"${float(order['limitPx']):,.2f}",
            )

        console.print(table)

        # Confirm cancellation
        if not skip_confirm:
            from rich.prompt import Confirm

            if not Confirm.ask(
                f"\n[bold yellow]Cancel {len(orders_to_show)} order(s)?[/bold yellow]"
            ):
                console.print("[yellow]Cancelled by user[/yellow]")
                return

        # Execute cancellation
        result = trader.cancel_open_orders(coin)

        if result.get("status") == "ok":
            console.print(f"[green]✓ Cancelled {len(orders_to_show)} order(s)[/green]")
        else:
            console.print(f"[red]✗ Error cancelling orders:[/red] {result}")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise


@cli.command()
def vintages():
    """Show active vintages in rolling rebalance mode.

    Displays the "layers" of the portfolio - each vintage represents
    positions opened on a specific date that will expire after rolling_days.
    """
    console = Console()

    # Check if rolling mode is configured
    if config.portfolio.rebalancing.mode != "rolling":
        console.print(
            "[yellow]Rolling mode is not enabled. "
            "Set portfolio.rebalancing.mode=rolling in config.[/yellow]"
        )
        return

    trader = CCLiquid(config, callbacks=RichCLICallbacks())

    try:
        summary = trader.get_vintages_summary()

        if not summary:
            console.print(
                "[yellow]No active vintages. Run 'cc-liquid rebalance' first.[/yellow]"
            )
            return

        from rich.table import Table

        rolling_days = config.portfolio.rebalancing.rolling_days

        table = Table(
            title=f"Active Vintages ({rolling_days}-day rolling)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Birth Date", style="cyan")
        table.add_column("Age", justify="right")
        table.add_column("Expires In", justify="right")
        table.add_column("Positions", justify="right")
        table.add_column("Value", justify="right")

        total_value = 0.0
        for v in summary:
            age_str = f"{v['age_days']}d"
            expires_str = f"{v['expires_in_days']}d"
            if v["expires_in_days"] <= 1:
                expires_str = f"[yellow]{expires_str}[/yellow]"

            table.add_row(
                v["date"],
                age_str,
                expires_str,
                str(v["num_positions"]),
                f"${v['value_usd']:,.2f}",
            )
            total_value += v["value_usd"]

        console.print(table)
        console.print(f"\n[cyan]Total vintage value: ${total_value:,.2f}[/cyan]")
        console.print(f"[dim]Active vintages: {len(summary)} of {rolling_days}[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise


@cli.command()
@click.option("--days", type=int, help="Show fills from last N days")
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", type=int, default=50, help="Max number of fills to show")
def history(days, start, end, limit):
    """Show trade fill history."""
    console = Console()
    trader = CCLiquid(config, callbacks=RichCLICallbacks())

    try:
        # Calculate time range
        start_time = None
        end_time = None

        if days:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=days)
            start_time = int(start_dt.timestamp() * 1000)
            end_time = int(end_dt.timestamp() * 1000)
        elif start:
            start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            start_time = int(start_dt.timestamp() * 1000)
            if end:
                end_dt = datetime.strptime(end, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                end_time = int(end_dt.timestamp() * 1000)

        # Get fills
        fills = trader.get_fill_history(start_time, end_time)

        if not fills:
            console.print("[yellow]No fills found[/yellow]")
            return

        # Sort by time (most recent first) but don't limit yet
        all_fills = sorted(fills, key=lambda x: x["time"], reverse=True)
        total_fills = len(all_fills)

        from rich.table import Table

        # Get fee summary for rate calculation (for estimation comparison)
        fee_info = trader.get_fee_summary()
        taker_rate = float(fee_info.get("userCrossRate", 0.00035))

        # Calculate aggregate statistics from ALL fills
        actual_total_fees = 0.0
        estimated_total_fees = 0.0
        total_volume = 0.0
        missing_fee_count = 0

        for fill in all_fills:
            size = float(fill["sz"])
            price = float(fill["px"])
            value = size * price
            total_volume += value

            # Actual fee from API
            actual_fee = float(fill.get("fee", 0))
            if actual_fee == 0 and "fee" not in fill:
                missing_fee_count += 1
            actual_total_fees += actual_fee

            # Estimated fee for comparison
            estimated_fee = value * taker_rate
            estimated_total_fees += estimated_fee

        # Now limit fills for display
        fills_to_display = all_fills[:limit]

        # Build display table with new columns
        table = Table(title="Fill History", show_header=True, header_style="bold cyan")
        table.add_column("TIME", style="dim", width=11)
        table.add_column("COIN", style="cyan", width=8)
        table.add_column("SIDE", justify="center", width=4)
        table.add_column("DIR", justify="left", width=11)
        table.add_column("SIZE", justify="right", width=10)
        table.add_column("PRICE", justify="right", width=10)
        table.add_column("VALUE", justify="right", width=11)
        table.add_column("FEE", justify="right", width=8)
        table.add_column("PNL", justify="right", width=10)
        table.add_column("OID", style="dim", justify="right", width=10)

        for fill in fills_to_display:
            side = fill["side"]
            side_style = "green" if side == "B" else "red"
            timestamp = datetime.fromtimestamp(fill["time"] / 1000).strftime(
                "%m-%d %H:%M"
            )

            size = float(fill["sz"])
            price = float(fill["px"])
            value = size * price

            # Use actual fee from API
            actual_fee = float(fill.get("fee", 0))

            # Get direction (e.g., "Open Long", "Close Short")
            direction = fill.get("dir", "-")

            # Get order ID
            oid = fill.get("oid", "-")
            if oid != "-":
                # Truncate long OIDs for display
                oid = str(oid)[:10] if len(str(oid)) > 10 else str(oid)

            pnl = float(fill.get("closedPnl", 0))
            pnl_style = "green" if pnl >= 0 else "red"

            table.add_row(
                timestamp,
                fill["coin"],
                f"[{side_style}]{side}[/{side_style}]",
                direction,
                f"{size:.4f}",
                f"${price:,.2f}",
                f"${value:,.2f}",
                f"${actual_fee:.2f}",
                f"[{pnl_style}]${pnl:+,.2f}[/{pnl_style}]" if pnl != 0 else "-",
                oid,
            )

        console.print(table)

        # Build summary message
        if total_fills > limit:
            summary_prefix = f"Showing {len(fills_to_display)} of {total_fills} fills (use --limit to show more)"
        else:
            summary_prefix = f"Showing all {total_fills} fills"

        # Show both actual and estimated fees for validation
        if actual_total_fees > 0:
            fee_diff_pct = abs(actual_total_fees - estimated_total_fees) / actual_total_fees * 100
            fee_summary = (
                f"Actual fees: ${actual_total_fees:,.2f}  │  "
                f"Estimated: ${estimated_total_fees:,.2f} ({fee_diff_pct:.2f}% diff)"
            )
        else:
            # Fallback to estimated if no actual fees available
            fee_summary = f"Estimated fees: ${estimated_total_fees:,.2f}"
            if missing_fee_count > 0:
                console.print(
                    f"[yellow]⚠️  Warning: {missing_fee_count}/{total_fills} fills missing 'fee' field, using estimation[/yellow]"
                )

        console.print(
            f"\n[cyan]{summary_prefix}[/cyan]\n"
            f"[cyan]Total volume: ${total_volume:,.2f}  │  {fee_summary}[/cyan]"
        )

    except Exception as e:
        console.print(f"[red]✗ Error fetching history:[/red] {e}")
        raise


@cli.command()
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output file path (defaults to path in config).",
)
def download_crowdcent(output):
    """Download the CrowdCent meta model."""
    console = Console()
    if output is None:
        output = config.data.path
    try:
        predictions = DataLoader.from_crowdcent_api(
            api_key=config.CROWDCENT_API_KEY, download_path=output
        )
        display_file_summary(console, predictions, output, "CrowdCent meta model")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to download CrowdCent meta model: {e}")
        raise


@cli.command()
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output file path (defaults to path in config).",
)
def download_numerai(output):
    """Download the Numerai meta model."""
    console = Console()
    if output is None:
        output = config.data.path
    try:
        predictions = DataLoader.from_numerai_api(download_path=output)
        display_file_summary(console, predictions, output, "Numerai meta model")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to download Numerai meta model: {e}")
        raise


@cli.command()
@click.option(
    "--skip-confirm",
    is_flag=True,
    help="Skip confirmation prompt for closing positions.",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    help="Override config values (e.g., --set is_testnet=true)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force close positions below min notional by composing a two-step workaround.",
)
def close_all(skip_confirm, set_overrides, force):
    """Close all positions and return to cash."""
    console = Console()

    # Apply CLI overrides to config
    overrides_applied = apply_cli_overrides(config, set_overrides)

    # Create callbacks and trader
    callbacks = RichCLICallbacks()
    trader = CCLiquid(config, callbacks=callbacks)

    # Show applied overrides through callbacks
    callbacks.on_config_override(overrides_applied)

    try:
        # Preview plan first (no execution)
        plan = trader.plan_close_all_positions(force=force)

        # Render plan via callbacks
        all_trades = plan["trades"] + plan["skipped_trades"]
        callbacks.show_trade_plan(
            plan["target_positions"],
            all_trades,
            plan["account_value"],
            plan["leverage"],
        )

        # Confirm/auto-confirm
        if skip_confirm or callbacks.ask_confirmation("Close all positions?"):
            # Execute
            result = trader.execute_plan(plan)
            callbacks.show_execution_summary(
                result["successful_trades"],
                result["all_trades"],
                plan["target_positions"],
                plan["account_value"],
            )
        else:
            callbacks.info("Cancelled by user")
    except Exception as e:
        console.print(f"[red]✗ Error closing positions:[/red] {e}")
        traceback.print_exc()


@cli.command()
@click.option(
    "--skip-confirm",
    is_flag=True,
    help="Skip confirmation prompt for executing trades.",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    help="Override config values (e.g., --set data.source=numerai --set portfolio.num_long=10)",
)
@click.option(
    "--cancel-open-orders",
    is_flag=True,
    help="Cancel all open orders before rebalancing (useful with Gtc orders).",
)
def rebalance(skip_confirm, set_overrides, cancel_open_orders):
    """Execute rebalancing based on the configured data source."""

    # Apply CLI overrides to config
    overrides_applied = apply_cli_overrides(config, set_overrides)

    # Create callbacks and trader
    callbacks = RichCLICallbacks()
    trader = CCLiquid(config, callbacks=callbacks)

    # Show applied overrides through callbacks
    callbacks.on_config_override(overrides_applied)

    # Handle open orders before planning
    if cancel_open_orders:
        # Auto-cancel if flag is set
        open_orders = trader.get_open_orders()
        if open_orders:
            callbacks.info(f"Cancelling {len(open_orders)} open order(s)...")
            result = trader.cancel_open_orders()
            if result.get("status") == "ok":
                callbacks.info(f"✓ Cancelled {len(open_orders)} order(s)")
            else:
                callbacks.warn(f"Failed to cancel orders: {result}")
        else:
            callbacks.info("No open orders to cancel")

    # Preview plan first (no execution) - dispatch based on mode
    plan = trader.plan_rebalance_auto()

    # Check for open orders if not already cancelled
    if not cancel_open_orders and plan.get("open_orders"):
        from rich.prompt import Confirm
        console = Console()
        
        open_orders = plan["open_orders"]
        console.print(
            f"\n[bold yellow]⚠️  Found {len(open_orders)} open order(s) that may conflict with rebalancing[/bold yellow]"
        )
        
        if Confirm.ask("Cancel open orders before proceeding?", default=False):
            callbacks.info(f"Cancelling {len(open_orders)} open order(s)...")
            result = trader.cancel_open_orders()
            if result.get("status") == "ok":
                callbacks.info(f"✓ Cancelled {len(open_orders)} order(s)")
                # Re-plan after cancelling orders
                plan = trader.plan_rebalance_auto()
            else:
                callbacks.warn(f"Failed to cancel orders: {result}")

    # Render plan via callbacks
    all_trades = plan["trades"] + plan["skipped_trades"]
    callbacks.show_trade_plan(
        plan["target_positions"], all_trades, plan["account_value"], plan["leverage"]
    )

    # Confirm/auto-confirm
    if skip_confirm or callbacks.ask_confirmation("Execute these trades?"):
        result = trader.execute_plan(plan)
        callbacks.show_execution_summary(
            result["successful_trades"],
            result["all_trades"],
            plan["target_positions"],
            plan["account_value"],
        )
    else:
        callbacks.info("Trading cancelled by user")


@cli.command(name="apply-stops")
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    help="Override config values (e.g., --set portfolio.stop_loss.sides=both)",
)
def apply_stops(set_overrides):
    """Manually apply stop losses to all open positions.
    
    Useful after:
    - Limit orders fill (were resting on book during rebalance)
    - Manual trades outside the bot
    - Bot restart with existing positions
    - Changing stop loss configuration
    """
    console = Console()
    
    # Apply CLI overrides
    overrides_applied = apply_cli_overrides(config, set_overrides)
    
    # Create trader
    callbacks = RichCLICallbacks()
    trader = CCLiquid(config, callbacks=callbacks)
    
    # Show overrides
    callbacks.on_config_override(overrides_applied)
    
    try:
        # Show what we're doing
        console.print("\n[cyan]Applying stop losses to open positions...[/cyan]")
        
        # Apply stop losses
        result = trader.apply_stop_losses()
        
        # Display results
        if result.get("status") == "disabled":
            console.print(f"[yellow]{result['message']}[/yellow]")
            return
        
        applied = result.get("applied", [])
        skipped = result.get("skipped", [])
        errors = result.get("errors", [])
        
        # Count side-filtered skips vs other skips
        side_skips = [s for s in skipped if "not configured" in s.get("reason", "")]
        other_skips = [s for s in skipped if "not configured" not in s.get("reason", "")]
        
        # Summary
        console.print(f"\n[bold cyan]Stop Loss Application Summary[/bold cyan]")
        console.print(f"[green]✓ Applied: {len(applied)}[/green]")
        if side_skips:
            console.print(f"[dim]⊘ Skipped (side filter): {len(side_skips)}[/dim]")
        if other_skips:
            console.print(f"[yellow]⊘ Skipped (other): {len(other_skips)}[/yellow]")
        if errors:
            console.print(f"[red]✗ Errors: {len(errors)}[/red]")
        
        # Details table
        if applied:
            from rich.table import Table
            from .cli_display import format_currency
            
            table = Table(title="Applied Stop Losses", show_header=True, header_style="bold cyan")
            table.add_column("COIN", style="cyan")
            table.add_column("SIDE", justify="center")
            table.add_column("ENTRY", justify="right")
            table.add_column("TRIGGER", justify="right")
            table.add_column("LIMIT", justify="right")
            
            for sl in applied:
                side_style = "green" if sl["side"] == "LONG" else "red"
                table.add_row(
                    sl["coin"],
                    f"[{side_style}]{sl['side']}[/{side_style}]",
                    format_currency(sl['entry_px']),
                    format_currency(sl['trigger_px']),
                    format_currency(sl['limit_px']),
                )
            console.print(table)
        
        # Only show non-side-filtered skips (actual issues)
        if other_skips:
            console.print("\n[yellow]Skipped positions (issues):[/yellow]")
            for s in other_skips:
                console.print(f"  • {s['coin']}: {s['reason']}")
        
        if errors:
            console.print("\n[red]Errors:[/red]")
            for e in errors:
                console.print(f"  • {e['coin']}: {e['error']}")
                
    except Exception as e:
        console.print(f"[red]✗ Error applying stop losses:[/red] {e}")
        raise


@cli.command()
@click.option(
    "--prices",
    default="raw_data.parquet",
    help="Path to price data (parquet file with date, id, close columns)",
)
@click.option(
    "--start-date",
    type=click.DateTime(),
    help="Start date for backtest (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(),
    help="End date for backtest (YYYY-MM-DD)",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    help="Override config values (e.g., --set portfolio.num_long=15 --set data.source=numerai)",
)
@click.option(
    "--fee-bps",
    type=float,
    default=4.0,
    help="Trading fee in basis points",
)
@click.option(
    "--slippage-bps",
    type=float,
    default=50.0,
    help="Slippage cost in basis points",
)
@click.option(
    "--prediction-lag",
    type=int,
    default=1,
    help="Days between prediction date and trading date (default: 1, use higher values to avoid look-ahead bias)",
)
@click.option(
    "--save-daily",
    help="Save daily results to CSV file",
)
@click.option(
    "--show-positions",
    is_flag=True,
    help="Show detailed position analysis table",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed progress",
)
def analyze(
    prices,
    start_date,
    end_date,
    set_overrides,
    fee_bps,
    slippage_bps,
    prediction_lag,
    save_daily,
    show_positions,
    verbose,
):
    """Run backtest analysis on historical data.

    ⚠️ IMPORTANT DISCLAIMER:
    Past performance does not guarantee future results. Backtesting results are
    hypothetical and have inherent limitations. Actual trading results may differ
    significantly. Always consider market conditions, liquidity, and execution costs
    that may not be fully captured in simulations.
    """
    from .backtester import Backtester, BacktestConfig
    from .config import config

    console = Console()

    # Apply CLI overrides to config (includes smart defaults for data.source changes)
    overrides_applied = apply_cli_overrides(config, set_overrides)

    # Show applied overrides through console
    if overrides_applied:
        console.print("[cyan]Configuration overrides applied:[/cyan]")
        for override in overrides_applied:
            console.print(f"  • {override}")
        console.print()

    # Now use the config value (which may have been overridden)
    predictions = config.data.path

    # Determine effective mode and rolling days
    if config.portfolio.rebalancing.mode == "rolling":
        console.print(f"[cyan]Using rolling mode with {config.portfolio.rebalancing.rolling_days}-day vintages[/cyan]\n")

    # Create backtest config using the updated config values
    bt_config = BacktestConfig(
        prices_path=prices,
        predictions_path=predictions,
        # Use config columns for predictions
        pred_date_column=config.data.date_column,
        pred_id_column=config.data.asset_id_column,
        pred_value_column=config.data.prediction_column,
        data_provider=config.data.source,
        start_date=start_date,
        end_date=end_date,
        num_long=config.portfolio.num_long,
        num_short=config.portfolio.num_short,
        target_leverage=config.portfolio.target_leverage,
        rank_power=config.portfolio.rank_power,
        weighting_method=config.portfolio.weighting_method,
        hrp_lookback_days=config.portfolio.hrp_lookback_days,
        mhrp_ewma_lambda=config.portfolio.mhrp_ewma_lambda,
        mhrp_vol_target=config.portfolio.mhrp_vol_target,
        mhrp_annual_factor=config.portfolio.mhrp_annual_factor,
        rebalance_every_n_days=config.portfolio.rebalancing.every_n_days,
        prediction_lag_days=prediction_lag,
        mode=config.portfolio.rebalancing.mode,
        rolling_days=config.portfolio.rebalancing.rolling_days,
        seed_full=config.portfolio.rebalancing.seed_full,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        verbose=verbose,
    )

    try:
        # Run backtest with spinner
        from rich.spinner import Spinner
        from rich.live import Live

        with Live(
            Spinner("dots", text="Running backtest..."), console=console, transient=True
        ):
            backtester = Backtester(bt_config)
            result = backtester.run()

        display_backtest_summary(
            console, result, bt_config, show_positions=show_positions
        )

        # Save daily results if requested
        if save_daily:
            result.daily.write_csv(save_daily)
            console.print(f"\n[green]✓[/green] Saved daily results to {save_daily}")

    except Exception as e:
        from rich.markup import escape

        console.print(f"[red]✗ Backtest failed: {escape(str(e))}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()


@cli.command()
@click.option(
    "--prices",
    default="raw_data.parquet",
    help="Path to price data",
)
@click.option(
    "--start-date",
    type=click.DateTime(),
    help="Start date for backtest (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(),
    help="End date for backtest (YYYY-MM-DD)",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    help="Override config values (e.g., --set data.source=numerai)",
)
@click.option(
    "--num-longs",
    default="10,20,30,40,50",
    help="Comma-separated list of long positions to test",
)
@click.option(
    "--num-shorts",
    default="10,20,30,40,50",
    help="Comma-separated list of short positions to test",
)
@click.option(
    "--leverages",
    default="1.0,2.0,3.0,4.0,5.0",
    help="Comma-separated list of leverage values to test",
)
@click.option(
    "--rebalance-days",
    default="8,10,12",
    help="Comma-separated list of rebalance frequencies to test",
)
@click.option(
    "--rank-powers",
    default="0.0,0.5,1.0,1.5,2.0",
    help="Comma-separated list of rank power values to test (0=equal weight)",
)
@click.option(
    "--metric",
    type=click.Choice(["sharpe", "cagr", "calmar"]),
    default="sharpe",
    help="Optimization metric",
)
@click.option(
    "--max-drawdown",
    type=float,
    help="Maximum drawdown constraint (e.g., 0.2 for 20%)",
)
@click.option(
    "--fee-bps",
    type=float,
    default=4.0,
    help="Trading fee in basis points",
)
@click.option(
    "--slippage-bps",
    type=float,
    default=50.0,
    help="Slippage cost in basis points",
)
@click.option(
    "--prediction-lag",
    type=int,
    default=1,
    help="Days between prediction date and trading date (default: 1, use higher values to avoid look-ahead bias)",
)
@click.option(
    "--top-n",
    type=int,
    default=20,
    help="Show top N results",
)
@click.option(
    "--apply-best",
    is_flag=True,
    help="Run full analysis with best parameters",
)
@click.option(
    "--save-results",
    help="Save optimization results to CSV",
)
@click.option(
    "--plot",
    is_flag=True,
    help="Show contour plots of results",
)
@click.option(
    "--max-workers",
    type=int,
    help="Number of parallel workers (default: auto)",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear cached optimization results",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed progress",
)
def optimize(
    prices,
    start_date,
    end_date,
    set_overrides,
    num_longs,
    num_shorts,
    leverages,
    rebalance_days,
    rank_powers,
    metric,
    max_drawdown,
    fee_bps,
    slippage_bps,
    prediction_lag,
    top_n,
    apply_best,
    save_results,
    plot,
    max_workers,
    clear_cache,
    verbose,
):
    """Optimize backtest parameters using parallel grid search.

    ⚠️ IMPORTANT DISCLAIMER:
    Optimization results are based on historical data and are subject to overfitting.
    Parameters that performed well in the past may not perform well in the future.
    Always use out-of-sample testing and forward walk analysis. Consider that
    optimized parameters may be curve-fit to historical noise rather than true patterns.
    """
    console = Console()

    # Apply CLI overrides to config (includes smart defaults for data.source changes)
    overrides_applied = apply_cli_overrides(config, set_overrides)

    # Show applied overrides through console
    if overrides_applied:
        console.print("[cyan]Configuration overrides applied:[/cyan]")
        for override in overrides_applied:
            console.print(f"  • {override}")
        console.print()

    # Parse parameter lists
    num_longs_list = [int(x.strip()) for x in num_longs.split(",")]
    num_shorts_list = [int(x.strip()) for x in num_shorts.split(",")]
    leverages_list = [float(x.strip()) for x in leverages.split(",")]
    rebalance_days_list = [int(x.strip()) for x in rebalance_days.split(",")]
    rank_powers_list = [float(x.strip()) for x in rank_powers.split(",")]

    # Now use the config value (which may have been overridden)
    predictions = config.data.path

    # Create base config with all parameters
    base_config = BacktestConfig(
        prices_path=prices,
        predictions_path=predictions,
        pred_date_column=config.data.date_column,
        pred_id_column=config.data.asset_id_column,
        pred_value_column=config.data.prediction_column,
        data_provider=config.data.source,
        start_date=start_date,
        end_date=end_date,
        rank_power=config.portfolio.rank_power,
        weighting_method=config.portfolio.weighting_method,
        hrp_lookback_days=config.portfolio.hrp_lookback_days,
        mhrp_ewma_lambda=config.portfolio.mhrp_ewma_lambda,
        mhrp_vol_target=config.portfolio.mhrp_vol_target,
        mhrp_annual_factor=config.portfolio.mhrp_annual_factor,
        prediction_lag_days=prediction_lag,
        mode=config.portfolio.rebalancing.mode,
        rolling_days=config.portfolio.rebalancing.rolling_days,
        seed_full=config.portfolio.rebalancing.seed_full,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        verbose=verbose,
    )

    try:
        # Calculate total combinations
        total_combos = (
            len(num_longs_list)
            * len(num_shorts_list)
            * len(leverages_list)
            * len(rebalance_days_list)
        )

        # Create optimizer
        optimizer = BacktestOptimizer(base_config)

        # Clear cache if requested
        if clear_cache:
            optimizer.clear_cache()
            console.print("[yellow]Cache cleared[/yellow]\n")

        # Show optimization header
        header = create_header_panel(f"OPTIMIZATION :: {total_combos} COMBINATIONS")
        console.print(header)
        console.print(f"\nOptimizing for: [bold yellow]{metric.upper()}[/bold yellow]")
        if max_drawdown:
            console.print(
                f"Max drawdown constraint: [yellow]{max_drawdown:.1%}[/yellow]"
            )
        console.print(
            f"Parameters: L={num_longs_list} S={num_shorts_list} Lev={leverages_list} Days={rebalance_days_list} Power={rank_powers_list}"
        )

        if max_workers:
            console.print(f"Parallel workers: [cyan]{max_workers}[/cyan]")
        else:
            import multiprocessing as mp

            auto_workers = min(mp.cpu_count(), 24)
            console.print(f"Parallel workers: [cyan]{auto_workers}[/cyan] (auto)")
        console.print()

        # Run optimization with Rich Progress
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
            expand=False,
        ) as progress:
            # Run parallel optimization
            results_df = optimizer.grid_search_parallel(
                num_longs=num_longs_list,
                num_shorts=num_shorts_list,
                leverages=leverages_list,
                rebalance_days=rebalance_days_list,
                rank_powers=rank_powers_list,
                metric=metric,
                max_drawdown_limit=max_drawdown,
                max_workers=max_workers,
                progress_callback=progress,
            )

        if len(results_df) == 0:
            console.print("[red]No valid results found[/red]")
            return

        # Display results
        console.print()  # Space after progress
        display_optimization_results(console, results_df, metric, top_n, base_config)

        # Show contour plots if requested
        if plot:
            display_optimization_contours(console, results_df, metric)

        # Save results if requested
        if save_results:
            results_df.write_csv(save_results)
            console.print(f"\n[green]✓[/green] Saved results to {save_results}")

        # Apply best parameters if requested
        if apply_best:
            best_params = optimizer.get_best_params(results_df, metric)
            if best_params:
                console.print(
                    "\n[bold cyan]Running full analysis with best parameters...[/bold cyan]"
                )
                console.print(
                    f"Best params: L={best_params['num_long']}, S={best_params['num_short']}, "
                    f"Lev={best_params['target_leverage']:.1f}x, Days={best_params['rebalance_every_n_days']}, "
                    f"Power={best_params['rank_power']}"
                )

                # Create config with best params and all other settings
                best_config = BacktestConfig(
                    prices_path=prices,
                    predictions_path=predictions,
                    pred_date_column=config.data.date_column,
                    pred_id_column=config.data.asset_id_column,
                    pred_value_column=config.data.prediction_column,
                    data_provider=config.data.source,
                    start_date=start_date,
                    end_date=end_date,
                    num_long=best_params["num_long"],
                    num_short=best_params["num_short"],
                    target_leverage=best_params["target_leverage"],
                    rebalance_every_n_days=best_params["rebalance_every_n_days"],
                    rank_power=best_params["rank_power"],
                    weighting_method=config.portfolio.weighting_method,
                    hrp_lookback_days=config.portfolio.hrp_lookback_days,
                    prediction_lag_days=prediction_lag,
                    mode=config.portfolio.rebalancing.mode,
                    rolling_days=config.portfolio.rebalancing.rolling_days,
                    seed_full=config.portfolio.rebalancing.seed_full,
                    fee_bps=fee_bps,
                    slippage_bps=slippage_bps,
                    verbose=False,
                )

                # Run backtest
                backtester = Backtester(best_config)
                result = backtester.run()

                display_backtest_summary(
                    console, result, best_config, show_positions=False
                )

    except Exception as e:
        from rich.markup import escape

        console.print(f"[red]✗ Optimization failed: {escape(str(e))}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()


@cli.command()
@click.option(
    "--skip-confirm",
    is_flag=True,
    help="Skip confirmation prompt for executing trades.",
)
@click.option(
    "--set",
    "set_overrides",
    multiple=True,
    help="Override config values (e.g., --set is_testnet=true)",
)
@click.option(
    "--refresh",
    type=float,
    default=1.0,
    show_default=True,
    help="Dashboard update cadence in seconds.",
)
@click.option(
    "--tmux",
    is_flag=True,
    help="Run inside a fixed tmux session (attach if exists, else create and run).",
)
def run(skip_confirm, set_overrides, refresh, tmux):
    """Start continuous monitoring and automatic rebalancing with live dashboard."""
    # Minimal tmux wrapper: attach-or-create a fixed session, with recursion guard
    if tmux and os.environ.get("CCLIQUID_TMUX_CHILD") != "1":
        if shutil.which("tmux") is None:
            raise click.ClickException(
                "tmux not found in PATH. Please install tmux to use --tmux."
            )

        inside_tmux = bool(os.environ.get("TMUX"))

        # Check if fixed session exists
        session_exists = (
            subprocess.call(
                ["tmux", "has-session", "-t", TMUX_SESSION_NAME],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            == 0
        )

        if session_exists:
            # Attach or switch to existing session
            if inside_tmux:
                subprocess.check_call(
                    ["tmux", "switch-client", "-t", TMUX_SESSION_NAME]
                )
                return
            else:
                os.execvp("tmux", ["tmux", "attach", "-t", TMUX_SESSION_NAME])

        # Create the session and run inner command with guard set
        inner_cmd = [
            "uv",
            "run",
            "-m",
            "cc_liquid.cli",
            "run",
        ]
        if skip_confirm:
            inner_cmd.append("--skip-confirm")
        for override in set_overrides:
            inner_cmd.extend(["--set", override])
        inner_cmd.extend(["--refresh", str(refresh)])

        # Build a single shell-quoted command string with guard env var
        command_string = f"CCLIQUID_TMUX_CHILD=1 {shlex.join(inner_cmd)}"

        subprocess.check_call(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                TMUX_SESSION_NAME,
                "-n",
                TMUX_WINDOW_NAME,
                command_string,
            ]
        )

        if inside_tmux:
            subprocess.check_call(["tmux", "switch-client", "-t", TMUX_SESSION_NAME])
            return
        else:
            os.execvp("tmux", ["tmux", "attach", "-t", TMUX_SESSION_NAME])

    # Normal, non-tmux path
    overrides_applied = apply_cli_overrides(config, set_overrides)
    run_live_cli(config, skip_confirm, overrides_applied, refresh)


def run_live_cli(
    config_obj,
    skip_confirm: bool,
    overrides_applied: list[str],
    refresh_seconds: float = 1.0,
):
    """Run continuous monitoring with live dashboard.

    Args:
        config_obj: The configuration object
        skip_confirm: Whether to skip confirmations during rebalancing
        overrides_applied: List of CLI overrides applied (for display)
        refresh_seconds: UI update cadence in seconds
    """
    console = Console()

    # Create trader with initial callbacks and load state
    callbacks = RichCLICallbacks()
    trader = CCLiquid(config_obj, callbacks=callbacks)

    # Show applied overrides if any (route via callbacks)
    callbacks.on_config_override(overrides_applied)
    if overrides_applied:
        time.sleep(2)  # Brief pause to show overrides

    last_rebalance_date = trader.load_state()

    # converts seconds per refresh to Live's refresh-per-second value
    live_rps = 1.0 / refresh_seconds if refresh_seconds > 0 else 1.0
    from rich.spinner import Spinner
    from rich.live import Live

    spinner = Spinner("dots", text="Loading...")
    with Live(
        spinner,
        console=console,
        screen=True,  # Use alternate screen
        refresh_per_second=live_rps,
        transient=False,
    ) as live:
        # quick loading screen
        try:
            while True:
                # Get current portfolio state
                portfolio = trader.get_portfolio_info()
                
                # Get open orders
                open_orders = trader.get_open_orders()

                # Calculate next rebalance time and determine if due
                next_action_time = trader.compute_next_rebalance_time(
                    last_rebalance_date
                )
                now = datetime.now(timezone.utc)
                should_rebalance = now >= next_action_time

                if should_rebalance:
                    # Stop the live display to run the standard rebalancing flow
                    live.stop()

                    try:
                        console.print(
                            "\n[bold yellow]-- Scheduled rebalance started --[/bold yellow]"
                        )
                        # Preview plan
                        plan = trader.plan_rebalance_auto()
                        all_trades = plan["trades"] + plan["skipped_trades"]
                        callbacks.show_trade_plan(
                            plan["target_positions"],
                            all_trades,
                            plan["account_value"],
                            plan["leverage"],
                        )

                        proceed = skip_confirm or callbacks.ask_confirmation(
                            "Execute these trades?"
                        )
                        if proceed:
                            result = trader.execute_plan(plan)
                            callbacks.show_execution_summary(
                                result["successful_trades"],
                                result["all_trades"],
                                plan["target_positions"],
                                plan["account_value"],
                            )
                        else:
                            callbacks.info("Trading cancelled by user")

                        # Update state on successful completion
                        last_rebalance_date = datetime.now(timezone.utc)
                        trader.save_state(last_rebalance_date)

                        if not skip_confirm:
                            console.input(
                                "\n[bold green]✓ Rebalance cycle finished. Press [bold]Enter[/bold] to resume dashboard...[/bold green]"
                            )

                    except Exception as e:
                        console.print(
                            f"\n[bold red]✗ Rebalancing failed:[/bold red] {e}"
                        )
                        traceback.print_exc()
                        if not skip_confirm:
                            console.input(
                                "\n[yellow]Press [bold]Enter[/bold] to resume dashboard...[/yellow]"
                            )
                    finally:
                        # Resume the live dashboard
                        live.start()
                        # Continue to the next loop iteration to immediately refresh the dashboard
                        continue

                else:
                    # Normal monitoring dashboard
                    dashboard = create_dashboard_layout(
                        portfolio=portfolio,
                        next_rebalance_time=next_action_time,
                        last_rebalance_time=last_rebalance_date,
                        is_rebalancing=False,
                        config_dict=config_obj.to_dict(),
                        refresh_seconds=refresh_seconds,
                        open_orders=open_orders,
                    )
                    live.update(dashboard)

                # Sleep to control dashboard update cadence and API usage
                time.sleep(refresh_seconds if refresh_seconds > 0 else 1)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            console.print(f"[red]✗ Error:[/red] {e}")
            traceback.print_exc()


if __name__ == "__main__":
    cli()