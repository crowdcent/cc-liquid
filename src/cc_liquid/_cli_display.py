"""Display utilities for rendering structured data."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from rich import box
from rich.box import DOUBLE
from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import re

if TYPE_CHECKING:
    from .trader import AccountInfo, PortfolioInfo


def strip_ansi_codes(text: str) -> str:
    """Strip ANSI escape codes from text to prevent Rich layout issues."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def create_setup_welcome_panel() -> Panel:
    """Build the setup wizard welcome panel used by init command."""
    welcome_text = Text.from_markup(
        "[bold cyan]Welcome to cc-liquid setup![/bold cyan]\n\n"
        "This wizard will help you create:\n"
        "• [cyan].env[/cyan] - for your private keys (never commit!)\n"
        "• [cyan]cc-liquid-config.yaml[/cyan] - for your trading configuration\n\n"
        "[dim]Press Ctrl+C anytime to cancel[/dim]"
    )
    return Panel(welcome_text, title="Setup Wizard", border_style="cyan")


def create_setup_summary_panel(
    is_testnet: bool,
    data_source: str,
    num_long: int,
    num_short: int,
    leverage: float,
) -> Panel:
    """Build the final setup summary panel used by init command."""
    summary_text = Text.from_markup(
        f"[bold green]✅ Setup Complete![/bold green]\n\n"
        f"Environment: [cyan]{'TESTNET' if is_testnet else 'MAINNET'}[/cyan]\n"
        f"Data source: [cyan]{data_source}[/cyan]\n"
        f"Portfolio: [green]{num_long}L[/green] / [red]{num_short}S[/red] @ [yellow]{leverage}x[/yellow]\n\n"
        "[bold]Next steps:[/bold]\n"
        "1. Fill in any missing values in [cyan].env[/cyan]\n"
        "2. Test connection: [cyan]cc-liquid account[/cyan]\n"
        "3. View config: [cyan]cc-liquid config[/cyan]\n"
        "4. First rebalance: [cyan]cc-liquid rebalance[/cyan]\n\n"
        "[dim]Optional: Install tab completion with 'cc-liquid completion install'[/dim]"
    )
    return Panel(
        summary_text,
        title="🎉 Ready to Trade",
        border_style="green",
    )


def create_plotext_panel(
    plot_func, title: str, width: int = 50, height: int = 10, style: str = "cyan"
) -> Panel:
    """Create a Rich panel with plotext content, handling ANSI codes properly."""
    import plotext as plt

    # Clear and configure plotext
    plt.clf()
    plt.plotsize(width, height)

    # Execute the plotting function
    plot_func(plt)

    # Get clean output
    chart_str = plt.build()
    clean_chart = strip_ansi_codes(chart_str)

    return Panel(Text(clean_chart, style=style), title=title, box=box.HEAVY)


def create_data_bar(
    value: float,
    max_value: float,
    width: int = 20,
    filled_char: str = "█",
    empty_char: str = "░",
) -> str:
    """Create a visual data bar for representing proportions."""
    if max_value == 0:
        filled_width = 0
    else:
        filled_width = int((value / max_value) * width)
    empty_width = width - filled_width
    return f"{filled_char * filled_width}{empty_char * empty_width}"


def format_currency(value: float, compact: bool = False) -> str:
    """Format currency values with appropriate styling.
    
    Dynamically adjusts decimal places for low-priced assets.
    """
    if compact and abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    
    # Dynamic decimal places based on magnitude
    thresholds = [(0.01, 6), (0.1, 5), (1, 4), (10, 3)]
    abs_val = abs(value)
    
    for threshold, decimals in thresholds:
        if abs_val < threshold:
            return f"${value:.{decimals}f}"
    
    return f"${value:,.2f}"


def create_metric_row(label: str, value: str, style: str = "") -> tuple:
    """Create a metric row tuple for tables."""
    return (f"[cyan]{label}[/cyan]", f"[{style}]{value}[/{style}]" if style else value)


def create_header_panel(base_title: str, is_rebalancing: bool = False) -> Panel:
    """Create a header panel for the dashboard view, optionally showing rebalancing status."""
    header_text = base_title
    if is_rebalancing:
        header_text += " :: [yellow blink]REBALANCING[/yellow blink]"
    return Panel(
        Text(header_text, style="bold cyan", justify="center"), box=DOUBLE, style="cyan"
    )


def create_account_metrics_table(account: "AccountInfo") -> Table:
    """Create a compact account metrics table for the metrics Panel of the dashboard view."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("", width=10)
    table.add_column("", justify="right")

    # Leverage color based on risk
    lev_color = (
        "green"
        if account.current_leverage <= 2
        else "yellow"
        if account.current_leverage <= 3
        else "red"
    )

    rows = [
        create_metric_row(
            "VALUE", format_currency(account.account_value), "bold green"
        ),
        create_metric_row("MARGIN", format_currency(account.margin_used)),
        create_metric_row("FREE", format_currency(account.free_collateral)),
        create_metric_row("LEVERAGE", f"{account.current_leverage:.2f}x", lev_color),
    ]

    for row in rows:
        table.add_row(*row)

    return table


def create_account_exposure_table(portfolio: "PortfolioInfo") -> Table:
    """Create a compact exposure analysis table for the metrics Panel of the dashboard view."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("", width=8)
    table.add_column("", justify="right", width=10)
    table.add_column("", width=18)

    account_val = (
        portfolio.account.account_value if portfolio.account.account_value > 0 else 1
    )

    # Calculate percentages
    long_pct = portfolio.total_long_value / account_val * 100
    short_pct = portfolio.total_short_value / account_val * 100
    net_pct = portfolio.net_exposure / account_val * 100
    gross_pct = long_pct + short_pct  # Just sum the percentages!

    # Build rows with visual bars for long/short
    net_color = "green" if portfolio.net_exposure >= 0 else "red"
    rows = [
        (
            "LONG",
            f"[green]{format_currency(portfolio.total_long_value, compact=True)}[/green]",
            f"[green]{create_data_bar(long_pct, 300, 12, '▓')} {long_pct:.0f}%[/green]",
        ),
        (
            "SHORT",
            f"[red]{format_currency(portfolio.total_short_value, compact=True)}[/red]",
            f"[red]{create_data_bar(short_pct, 300, 12, '▓')} {short_pct:.0f}%[/red]",
        ),
        (
            "NET",
            f"[{net_color}]{format_currency(portfolio.net_exposure, compact=True)}[/{net_color}]",
            f"[dim]{net_pct:+.0f}%[/dim]",
        ),
        (
            "GROSS",
            format_currency(portfolio.total_exposure, compact=True),
            f"[dim]{gross_pct:.0f}%[/dim]",
        ),
    ]

    for row in rows:
        table.add_row(*row)

    return table


def create_metrics_panel(portfolio: "PortfolioInfo") -> Panel:
    """Create portfolio metrics panel (account + exposure) for the dashboard view."""
    return Panel(
        Columns(
            [
                create_account_metrics_table(portfolio.account),
                create_account_exposure_table(portfolio),
            ],
            expand=True,
        ),
        title="[bold cyan]METRICS[/bold cyan]",
        box=box.HEAVY,
    )


def create_positions_panel(portfolio: "PortfolioInfo") -> Panel:
    """Create a panel displaying all open positions with summary statistics.

    The panel includes a table of positions (sorted by value), and a title summarizing
    the number of longs/shorts and total unrealized PnL.

    Args:
        portfolio (PortfolioInfo): The portfolio containing positions and account info.

    Returns:
        Panel: A rich Panel containing the positions table and summary.
    """
    positions = portfolio.positions

    if not portfolio.positions:
        return Panel(
            "[yellow]No open positions[/yellow]",
            box=box.HEAVY,
            title="[bold cyan]POSITIONS[/bold cyan]",
        )

    account_val = (
        portfolio.account.account_value if portfolio.account.account_value > 0 else 1
    )
    long_count = sum(1 for p in positions if p.side == "LONG")
    short_count = sum(1 for p in positions if p.side == "SHORT")
    total_pnl = sum(p.unrealized_pnl for p in positions)
    pnl_pct = total_pnl / account_val * 100
    pnl_color = "green" if total_pnl >= 0 else "red"

    title = (
        f"[bold cyan]POSITIONS[/bold cyan]  [dim]│[/dim]  "
        f"[green]{long_count}L[/green] [red]{short_count}S[/red]  [dim]│[/dim]  "
        f"UNREALIZED [{pnl_color}]${total_pnl:+,.2f} ({pnl_pct:+.1f}%)[/{pnl_color}]"
    )

    table = Table(
        box=box.HEAVY_HEAD,
        show_lines=False,
        header_style="bold cyan on #001926",
        expand=True,
    )

    # Define columns
    table.add_column("COIN", style="cyan", width=8)
    table.add_column("SIDE", justify="center", width=5)
    table.add_column("SIZE", justify="right", width=8)
    table.add_column("ENTRY", justify="right", width=10)
    table.add_column("MARK", justify="right", width=10)
    table.add_column("VALUE", justify="right", width=12)
    table.add_column("PNL", justify="right", width=10)
    table.add_column("PERF", justify="center", width=8)

    # Sort positions by absolute value
    sorted_positions = sorted(positions, key=lambda p: abs(p.value), reverse=True)

    for pos in sorted_positions:
        side_style = "green" if pos.side == "LONG" else "red"
        pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"

        # Format size based on magnitude
        if abs(pos.size) >= 1000:
            size_str = f"{pos.size:,.0f}"
        elif abs(pos.size) >= 1:
            size_str = f"{pos.size:.2f}"
        else:
            size_str = f"{pos.size:.4f}"

        table.add_row(
            f"[bold]{pos.coin}[/bold]",
            f"[{side_style}]{pos.side[:1]}[/{side_style}]",
            size_str,
            format_currency(pos.entry_price, compact=True),
            format_currency(pos.mark_price, compact=True),
            format_currency(abs(pos.value), compact=True),
            f"[{pnl_color}]${pos.unrealized_pnl:+,.2f}[/{pnl_color}]",
            f"[{pnl_color}]{pos.return_pct:+.1f}% [/{pnl_color}]",
        )

    return Panel(table, title=title, box=box.HEAVY)


def create_sidebar_panel(config_dict: dict | None, empty_label: str) -> Panel:
    """Create sidebar panel containing config or a standardized empty state."""
    if config_dict:
        return create_config_panel(config_dict)
    return Panel(empty_label, box=box.HEAVY)


def create_footer_panel(
    next_rebalance_time: datetime | None,
    last_rebalance_time: datetime | None,
    refresh_seconds: float | None,
) -> Panel:
    """Create monitoring footer with countdown and status details."""
    now = datetime.now(timezone.utc)

    # Next rebalance countdown
    countdown_str = ""
    if next_rebalance_time:
        time_until = next_rebalance_time - now
        if time_until.total_seconds() > 0:
            total_seconds = int(time_until.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 24:
                days = hours // 24
                hours = hours % 24
                countdown = f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                countdown = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            if total_seconds < 60:
                countdown_str = f"[bold yellow blink]{countdown}[/bold yellow blink]"
            elif total_seconds < 3600:
                countdown_str = f"[yellow]{countdown}[/yellow]"
            else:
                countdown_str = f"[green]{countdown}[/green]"
        else:
            countdown_str = "[bold red blink]REBALANCING[/bold red blink]"
    else:
        countdown_str = "[dim]Calculating...[/dim]"

    # Last rebalance string
    last_rebalance_str = "[dim]Never[/dim]"
    if last_rebalance_time:
        time_since = now - last_rebalance_time
        hours_ago = time_since.total_seconds() / 3600
        if hours_ago < 24:
            last_rebalance_str = f"[dim]{hours_ago:.1f}h ago[/dim]"
        else:
            days_ago = hours_ago / 24
            last_rebalance_str = f"[dim]{days_ago:.1f}d ago[/dim]"

    status_grid = Table.grid(expand=True)
    status_grid.add_column(justify="left")
    status_grid.add_column(justify="center")
    status_grid.add_column(justify="center")
    status_grid.add_column(justify="right")

    status_grid.add_row(
        f"[bold cyan]Next rebalance: {countdown_str}[/bold cyan]",
        f"[dim]Last: {last_rebalance_str}[/dim]",
        f"[dim]Monitor refresh: {refresh_seconds:.1f}s[/dim]"
        if refresh_seconds is not None
        else "",
        "[red]Press Ctrl+C to exit[/red]",
    )

    return Panel(status_grid, box=box.HEAVY)


def create_dashboard_layout(
    portfolio: "PortfolioInfo",
    config_dict: dict | None = None,
    *,
    next_rebalance_time: datetime | None = None,
    last_rebalance_time: datetime | None = None,
    is_rebalancing: bool = False,
    refresh_seconds: float | None = None,
    open_orders: list[dict] | None = None,
) -> Layout:
    """Unified portfolio dashboard builder.

    - Builds the common header, body (metrics, positions, sidebar)
    - Optionally adds a monitoring footer when scheduling data is provided
    """
    has_footer = any(
        value is not None
        for value in (next_rebalance_time, last_rebalance_time, refresh_seconds)
    )

    layout = Layout()

    if has_footer:
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
    else:
        layout.split_column(Layout(name="header", size=3), Layout(name="body"))

    # Header
    header_title = (
        "CC-LIQUID MONITOR :: METAMODEL REBALANCER"
        if has_footer
        else "CC-LIQUID :: METAMODEL REBALANCER"
    )
    layout["header"].update(
        create_header_panel(header_title, is_rebalancing if has_footer else False)
    )

    # Body: split into main area and sidebar
    layout["body"].split_row(
        Layout(name="main", ratio=2), Layout(name="sidebar", ratio=1)
    )

    # Main area: metrics + positions
    layout["main"].split_column(
        Layout(name="metrics", size=8), Layout(name="positions")
    )

    layout["metrics"].update(create_metrics_panel(portfolio))
    layout["positions"].update(create_positions_panel(portfolio))

    # Sidebar: split into config (top) and open orders (bottom)
    layout["sidebar"].split_column(
        Layout(name="config", ratio=2),
        Layout(name="open_orders", ratio=1)
    )

    empty_sidebar_text = (
        "[dim]No config loaded[/dim]" if has_footer else "[dim]No config[/dim]"
    )
    layout["sidebar"]["config"].update(create_sidebar_panel(config_dict, empty_sidebar_text))
    layout["sidebar"]["open_orders"].update(
        create_open_orders_panel(open_orders or [])
    )

    # Footer (optional)
    if has_footer:
        footer = create_footer_panel(
            next_rebalance_time, last_rebalance_time, refresh_seconds
        )
        layout["footer"].update(footer)

    return layout


def create_config_tree_table(config_dict: dict) -> Table:
    """Create config display as a tree structure (reusable)."""
    table = Table(show_header=False, box=None, padding=(0, 0))
    table.add_column("Setting", style="cyan", width=20, no_wrap=True)
    table.add_column("Value", style="white")

    # Environment section
    network = "TESTNET" if config_dict.get("is_testnet", False) else "MAINNET"
    network_color = "yellow" if config_dict.get("is_testnet", False) else "green"

    # Data source section
    data_config = config_dict.get("data", {})
    source = data_config.get("source", "crowdcent")
    source_color = (
        "green"
        if source == "crowdcent"
        else "yellow"
        if source == "numerai"
        else "white"
    )

    # Portfolio section
    portfolio_config = config_dict.get("portfolio", {})
    leverage = portfolio_config.get("target_leverage", 1.0)
    leverage_color = "green" if leverage <= 2 else "yellow" if leverage <= 3 else "red"
    rebalancing = portfolio_config.get("rebalancing", {})
    rank_power = portfolio_config.get("rank_power", 0.0)

    # Execution section
    execution_config = config_dict.get("execution", {})
    slippage_pct = execution_config.get("slippage_tolerance", 0.005) * 100
    slippage_color = (
        "green" if slippage_pct <= 0.5 else "yellow" if slippage_pct <= 1.0 else "red"
    )
    min_trade_value = execution_config.get("min_trade_value", 10.0)
    order_type = execution_config.get("order_type", "market")
    order_type_display = order_type.capitalize()
    order_type_color = "green" if order_type == "limit" else "white"
    time_in_force = execution_config.get("time_in_force", "Ioc")
    limit_price_offset_pct = execution_config.get("limit_price_offset", 0.0) * 100

    # Profile section (owner/vault and signer env name)
    profile_cfg = config_dict.get("profile", {})
    owner = profile_cfg.get("owner") or "[dim]-[/dim]"
    vault = profile_cfg.get("vault") or "[dim]-[/dim]"
    active_profile = profile_cfg.get("active") or "[dim]-[/dim]"
    signer_env = profile_cfg.get("signer_env") or "HYPERLIQUID_PRIVATE_KEY"

    # Check if stop loss is enabled
    stop_loss_config = portfolio_config.get("stop_loss", {})
    stop_loss_sides = stop_loss_config.get("sides", "none")
    stop_loss_enabled = stop_loss_sides != "none"
    
    # Build all rows
    rows = [
        ("[bold]ENVIRONMENT[/bold]", ""),
        ("├─ Network", f"[{network_color}]{network}[/{network_color}]"),
        ("├─ Active Profile", f"[white]{active_profile}[/white]"),
        ("├─ Owner", f"[white]{owner}[/white]"),
        ("├─ Vault", f"[white]{vault}[/white]"),
        ("└─ Signer Env", f"[white]{signer_env}[/white]"),
        ("", ""),
        ("[bold]DATA SOURCE[/bold]", ""),
        ("├─ Provider", f"[{source_color}]{source}[/{source_color}]"),
        ("├─ Path", data_config.get("path", "predictions.parquet")),
        ("└─ Prediction", data_config.get("prediction_column", "pred_30d")),
        ("", ""),
        ("[bold]PORTFOLIO[/bold]", ""),
        ("├─ Long Positions", f"[green]{portfolio_config.get('num_long', 10)}[/green]"),
        ("├─ Short Positions", f"[red]{portfolio_config.get('num_short', 10)}[/red]"),
        ("├─ Target Leverage", f"[{leverage_color}]{leverage:.1f}x[/{leverage_color}]"),
        ("├─ Rank Power", f"{rank_power:.1f}"),
    ]
    
    sides_color = "green" if stop_loss_sides == "both" else "yellow" if stop_loss_enabled else "dim"
    rows.append(("├─ Stop Loss", f"[{sides_color}]{stop_loss_sides}[/{sides_color}]"))
    
    if stop_loss_enabled:
        stop_pct = stop_loss_config.get("pct", 0.17) * 100
        slippage = stop_loss_config.get("slippage", 0.05) * 100
        
        rows.extend([
            ("│  ├─ Trigger", f"{stop_pct:.0f}%"),
            ("│  └─ Slippage", f"{slippage:.0f}%"),
        ])
    
    # Determine frequency string based on mode
    if rebalancing.get("mode") == "rolling":
        freq_str = "Daily (rolling)"
    else:
        freq_str = f"Every {rebalancing.get('every_n_days', 10)} days"

    rows.extend([
        ("└─ Rebalancing", ""),
        ("   ├─ Frequency", freq_str),
        ("   └─ Time (UTC)", rebalancing.get("at_time", "18:15")),
        ("", ""),
        ("[bold]EXECUTION[/bold]", ""),
        ("├─ Order Type", f"[{order_type_color}]{order_type_display}[/{order_type_color}]"),
    ])
    
    # Add order-type-specific fields
    if order_type == "limit":
        rows.extend([
            ("├─ Time In Force", f"[white]{time_in_force}[/white]"),
            ("├─ Limit Offset", f"[white]{limit_price_offset_pct:.2f}%[/white]"),
        ])
    else:  # market
        rows.append(("├─ Slippage", f"[{slippage_color}]{slippage_pct:.1f}%[/{slippage_color}]"))
    
    rows.append(("└─ Min Trade Value", format_currency(min_trade_value, compact=False)))

    for row in rows:
        table.add_row(*row)

    return table


def display_portfolio(
    portfolio: "PortfolioInfo",
    console: Console | None = None,
    config_dict: dict | None = None,
    open_orders: list[dict] | None = None,
) -> None:
    """Display portfolio information in a compact dashboard."""
    if console is None:
        console = Console()

    # Use the new dashboard layout
    layout = create_dashboard_layout(portfolio, config_dict, open_orders=open_orders)
    console.print(layout)


def create_config_panel(config_dict: dict) -> Panel:
    """Create display Panel for the config view. Can be used standalone or as part of the dashboard view."""
    return Panel(
        create_config_tree_table(config_dict),
        title="[bold cyan]CONFIG[/bold cyan]",
        box=box.HEAVY,
    )


def create_open_orders_panel(open_orders: list[dict]) -> Panel:
    """Create panel displaying open orders table."""
    if not open_orders:
        return Panel(
            "[dim]No open orders[/dim]",
            title="[bold cyan]OPEN ORDERS[/bold cyan]",
            box=box.HEAVY,
        )
    
    table = Table(
        box=box.SIMPLE_HEAD,
        show_lines=False,
        header_style="bold cyan on #001926",
        expand=True,
    )
    
    table.add_column("COIN", style="cyan", width=8)
    table.add_column("SIDE", justify="center", width=6)
    table.add_column("SIZE", justify="right", width=10)
    table.add_column("PRICE", justify="right", width=10)
    
    for order in open_orders:
        side = "BUY" if order["side"] == "B" else "SELL"
        side_style = "green" if side == "BUY" else "red"
        
        table.add_row(
            order["coin"],
            f"[{side_style}]{side}[/{side_style}]",
            order["sz"],
            format_currency(float(order['limitPx'])),
        )
    
    title = f"[bold cyan]OPEN ORDERS[/bold cyan]  [dim]│[/dim]  {len(open_orders)} active"
    return Panel(table, title=title, box=box.HEAVY)


def display_file_summary(
    console: Console, predictions, output_path: str, model_name: str
) -> None:
    """Display a summary of downloaded predictions file."""
    console.print(f"[green]✓[/green] Downloaded {model_name} to {output_path}")
    console.print(f"[cyan]Shape:[/cyan] {predictions.shape}")
    console.print(f"[cyan]Columns:[/cyan] {list(predictions.columns)}")


def show_pre_alpha_warning() -> None:
    """Display pre-alpha warning to users."""
    console = Console()
    warning_copy = """
This is pre-alpha software provided as a reference implementation only.
• Using this software may result in COMPLETE LOSS of funds.
• CrowdCent makes NO WARRANTIES and assumes NO LIABILITY for any losses.
• Users must comply with all Hyperliquid and CrowdCent terms of service.
• We do NOT endorse any vaults or strategies using this tool.

[bold yellow]By continuing, you acknowledge that you understand and accept ALL risks.[/bold yellow]
    """
    warning_text = Text.from_markup(warning_copy, justify="left")
    panel = Panel(
        warning_text,
        title="[bold cyan]CC-LIQUID ::[/bold cyan] [bold red] PRE-ALPHA SOFTWARE - USE AT YOUR OWN RISK [/bold red]",
        border_style="red",
        box=box.HEAVY,
    )
    console.print(panel)


def show_rebalancing_plan(
    console: Console,
    target_positions: dict,
    trades: list,
    account_value: float,
    leverage: float,
) -> None:
    """Create a comprehensive rebalancing dashboard layout."""
    # Header
    header = Panel(
        Text("REBALANCING PLAN", style="bold cyan", justify="center"),
        box=DOUBLE,
        style="cyan",
    )
    console.print(header)

    # Metrics row: account + rebalancing summary
    metrics_content = create_rebalancing_metrics_panel(
        account_value, leverage, trades, target_positions
    )
    console.print(metrics_content)

    # Trades panel
    trades_panel = create_trades_panel(trades)
    console.print(trades_panel)

    # Check if we have skipped trades
    skipped_count = sum(1 for t in trades if t.get("skipped", False))
    if skipped_count > 0:
        console.print(
            f"\n[bold yellow]⚠️ WARNING: {skipped_count} trade(s) marked as SKIPPED[/bold yellow]\n"
            f"[yellow]These positions cannot be resized due to minimum trade size constraints.[/yellow]\n"
            f"[yellow]They will remain at their current sizes, causing portfolio imbalance.[/yellow]\n"
            f"[dim]Consider: increasing account value, using higher leverage, or reducing position count.[/dim]"
        )


def create_rebalancing_metrics_panel(
    account_value: float, leverage: float, trades: list, target_positions: dict
) -> Panel:
    """Create rebalancing metrics panel."""
    # Position counts using the type field
    executable_trades = [t for t in trades if not t.get("skipped", False)]
    opens = sum(1 for t in executable_trades if t.get("type") == "open")
    closes = sum(1 for t in executable_trades if t.get("type") == "close")
    flips = sum(1 for t in executable_trades if t.get("type") == "flip")
    reduces = sum(1 for t in executable_trades if t.get("type") == "reduce")
    increases = sum(1 for t in executable_trades if t.get("type") == "increase")

    # Target portfolio metrics
    total_long_value = sum(v for v in target_positions.values() if v > 0)
    total_short_value = abs(sum(v for v in target_positions.values() if v < 0))
    
    # Calculate total estimated fees
    total_estimated_fees = sum(t.get("estimated_fee", 0) for t in executable_trades)

    # Create two columns
    left_table = Table(show_header=False, box=None, padding=(0, 1))
    left_table.add_column("", width=12)
    left_table.add_column("", justify="right")

    left_table.add_row("ACCOUNT", format_currency(account_value, compact=False))
    left_table.add_row(
        "LEVERAGE",
        f"[{'green' if leverage <= 2 else 'yellow' if leverage <= 3 else 'red'}]{leverage:.1f}x[/{'green' if leverage <= 2 else 'yellow' if leverage <= 3 else 'red'}]",
    )
    left_table.add_row("MAX EXPOSURE", format_currency(account_value * leverage))
    left_table.add_row("", "")  # spacer
    left_table.add_row(
        "TARGET LONG",
        f"[green]{format_currency(total_long_value, compact=True)}[/green]",
    )
    left_table.add_row(
        "TARGET SHORT", f"[red]{format_currency(total_short_value, compact=True)}[/red]"
    )
    left_table.add_row("EST. FEES", f"${total_estimated_fees:.2f}")

    right_table = Table(show_header=False, box=None, padding=(0, 1))
    right_table.add_column("", width=12)
    right_table.add_column("", justify="right")

    right_table.add_row("TRADES", f"[bold]{len(executable_trades)}[/bold]")
    if opens > 0:
        right_table.add_row("OPEN", f"[green]{opens}[/green]")
    if closes > 0:
        right_table.add_row("CLOSE", f"[red]{closes}[/red]")
    if flips > 0:
        right_table.add_row("FLIP", f"[yellow]{flips}[/yellow]")
    if reduces > 0:
        right_table.add_row("REDUCE", f"[blue]{reduces}[/blue]")
    if increases > 0:
        right_table.add_row("ADD", f"[cyan]{increases}[/cyan]")

    return Panel(
        Columns([left_table, right_table], expand=True),
        title="[bold cyan]METRICS[/bold cyan]",
        box=box.HEAVY,
    )


def create_trades_panel(trades: list) -> Panel:
    """Create a panel for the trades table matching the positions table style."""
    # Handle no trades
    if not trades:
        return Panel(
            "[yellow]No trades required - portfolio is already balanced[/yellow]",
            box=box.HEAVY,
            title="[bold cyan]TRADES[/bold cyan]",
        )

    # Separate executable and skipped trades
    executable_trades = [t for t in trades if not t.get("skipped", False)]
    skipped_trades = [t for t in trades if t.get("skipped", False)]

    # Calculate summary for title (only executable trades)
    total_volume = sum(abs(t.get("delta_value", 0)) for t in executable_trades)
    buy_count = sum(1 for t in executable_trades if t.get("is_buy"))
    sell_count = len(executable_trades) - buy_count
    buy_volume = sum(
        abs(t.get("delta_value", 0)) for t in executable_trades if t.get("is_buy")
    )
    sell_volume = sum(
        abs(t.get("delta_value", 0)) for t in executable_trades if not t.get("is_buy")
    )

    # Add skipped count to title if any
    skipped_info = ""
    if skipped_trades:
        skipped_info = f"  [dim]│[/dim]  [yellow]{len(skipped_trades)} SKIPPED[/yellow]"

    title = (
        f"[bold cyan]TRADES[/bold cyan]  [dim]│[/dim]  "
        f"[green]{buy_count} BUY (${buy_volume:,.2f})[/green] "
        f"[red]{sell_count} SELL (${sell_volume:,.2f})[/red]  [dim]│[/dim]  "
        f"VOLUME [bold]${total_volume:,.2f}[/bold]"
        f"{skipped_info}"
    )

    table = Table(
        box=box.HEAVY_HEAD,
        show_lines=False,
        header_style="bold cyan on #001926",
        expand=True,
    )

    # Define columns
    table.add_column("COIN", style="cyan", width=8)
    table.add_column("ACTION", justify="center", width=7)
    table.add_column("CURRENT", justify="right", width=10)
    table.add_column("→", justify="center", width=1, style="dim")
    table.add_column("TARGET", justify="right", width=10)
    table.add_column("DELTA", justify="right", width=10)
    table.add_column("TRADE", justify="center", width=6)
    table.add_column("SIZE", justify="right", width=10)
    table.add_column("PRICE", justify="right", width=10)
    table.add_column("EST FEE", justify="right", width=8)

    # Sort trades by absolute delta value, with executable trades first
    sorted_trades = sorted(
        trades, key=lambda t: (t.get("skipped", False), -abs(t.get("delta_value", 0)))
    )

    for trade in sorted_trades:
        coin = trade["coin"]
        is_buy = trade.get("is_buy", False)  # Skipped trades may not have this
        current_value = trade.get("current_value", 0)
        target_value = trade.get("target_value", 0)
        delta_value = trade.get("delta_value", 0)

        # Use the type field from trade calculation
        trade_type = trade.get("type", "increase")  # fallback for old data
        action_styles = {
            "open": "[green]OPEN[/green]",
            "close": "[red]CLOSE[/red]",
            "flip": "[yellow]FLIP[/yellow]",
            "reduce": "[blue]REDUCE[/blue]",
            "increase": "[cyan]ADD[/cyan]",
        }
        action = action_styles.get(trade_type, "[dim]ADJUST[/dim]")

        # Format current and target with side indicators
        if current_value == 0:
            current_str = "[dim]-[/dim]"
        else:
            side = "L" if current_value > 0 else "S"
            side_color = "green" if current_value > 0 else "red"
            current_str = f"{format_currency(abs(current_value), compact=True)} [{side_color}]{side}[/{side_color}]"

        if target_value == 0:
            target_str = "[dim]-[/dim]"
        else:
            side = "L" if target_value > 0 else "S"
            side_color = "green" if target_value > 0 else "red"
            target_str = f"{format_currency(abs(target_value), compact=True)} [{side_color}]{side}[/{side_color}]"

        # Trade direction
        trade_action = "[green]BUY[/green]" if is_buy else "[red]SELL[/red]"

        # Delta with color
        delta_color = "green" if delta_value > 0 else "red"
        delta_str = f"[{delta_color}]{delta_value:+,.2f}[/{delta_color}]"

        # Style differently if trade is skipped
        if trade.get("skipped", False):
            # Show the skip reason in the trade column
            trade_action = "[yellow]SKIP[/yellow]"
            # Dim the entire row for skipped trades
            coin_str = f"[dim]{coin}[/dim]"
            action = f"[dim]{action}[/dim]"
            current_str = f"[dim]{current_str}[/dim]"
            target_str = f"[dim]{target_str}[/dim]"
            delta_str = f"[dim yellow]{delta_value:+,.2f}[/dim yellow]"
            size_str = "[dim]-[/dim]"  # No size since it won't execute
            price_str = "[dim]-[/dim]"  # No price since it won't execute
            fee_str = "[dim]-[/dim]"  # No fee for skipped trades
        else:
            coin_str = f"[bold]{coin}[/bold]"
            size_str = f"{trade.get('sz', 0):.4f}" if "sz" in trade else "[dim]-[/dim]"
            price_str = (
                format_currency(trade["price"], compact=True)
                if "price" in trade
                else "[dim]-[/dim]"
            )
            fee_str = f"${trade.get('estimated_fee', 0):.2f}"

        table.add_row(
            coin_str,
            action,
            current_str,
            "→",
            target_str,
            delta_str,
            trade_action,
            size_str,
            price_str,
            fee_str,
        )

    return Panel(table, title=title, box=box.HEAVY, expand=True)


def create_execution_metrics_panel(
    successful_trades: list[dict],
    all_trades: list[dict],
    target_positions: dict,
    account_value: float,
) -> Panel:
    """Create execution summary metrics panel."""
    total_success = len(successful_trades)
    total_failed = len(all_trades) - total_success

    # Calculate portfolio metrics
    total_long_value = sum(v for v in target_positions.values() if v > 0)
    total_short_value = abs(sum(v for v in target_positions.values() if v < 0))
    total_exposure = total_long_value + total_short_value
    net_exposure = total_long_value - total_short_value
    leverage = total_exposure / account_value if account_value > 0 else 0

    # Calculate slippage stats from successful trades
    if successful_trades:
        slippages = [t.get("slippage_pct", 0) for t in successful_trades]
        avg_slippage = sum(slippages) / len(slippages)
        max_slippage = max(slippages)
        min_slippage = min(slippages)
    else:
        avg_slippage = max_slippage = min_slippage = 0
    
    # Calculate total actual fees from successful trades
    total_actual_fees = sum(t.get("actual_fee", 0) for t in successful_trades)

    # Create two columns
    left_table = Table(show_header=False, box=None, padding=(0, 1))
    left_table.add_column("", width=15)
    left_table.add_column("", justify="right")

    # Execution results
    left_table.add_row(
        "EXECUTED", f"[green]{total_success}[/green]" if total_success > 0 else "0"
    )
    if total_failed > 0:
        left_table.add_row("FAILED", f"[red]{total_failed}[/red]")
    left_table.add_row(
        "SUCCESS RATE",
        f"[bold]{total_success / len(all_trades) * 100:.1f}%[/bold]"
        if all_trades
        else "N/A",
    )
    left_table.add_row("", "")  # spacer

    # Slippage stats
    if successful_trades:
        left_table.add_row(
            "AVG SLIPPAGE",
            f"[{'green' if avg_slippage <= 0 else 'red'}]{avg_slippage:+.3f}%[/{'green' if avg_slippage <= 0 else 'red'}]",
        )
        left_table.add_row("MAX SLIPPAGE", f"{max_slippage:+.3f}%")
        left_table.add_row("MIN SLIPPAGE", f"{min_slippage:+.3f}%")
        left_table.add_row("", "")  # spacer
        left_table.add_row("ACTUAL FEES", f"${total_actual_fees:.2f}")

    right_table = Table(show_header=False, box=None, padding=(0, 1))
    right_table.add_column("", width=15)
    right_table.add_column("", justify="right")

    # Portfolio metrics
    right_table.add_row("TOTAL EXPOSURE", format_currency(total_exposure))
    right_table.add_row("NET EXPOSURE", format_currency(net_exposure))
    right_table.add_row(
        "LEVERAGE",
        f"[{'green' if leverage <= 2 else 'yellow' if leverage <= 3 else 'red'}]{leverage:.2f}x[/{'green' if leverage <= 2 else 'yellow' if leverage <= 3 else 'red'}]",
    )
    right_table.add_row("", "")  # spacer
    right_table.add_row(
        "LONG VALUE",
        f"[green]{format_currency(total_long_value, compact=True)}[/green]",
    )
    right_table.add_row(
        "SHORT VALUE", f"[red]{format_currency(total_short_value, compact=True)}[/red]"
    )
    right_table.add_row(
        "NET % OF NAV",
        f"{net_exposure / account_value * 100:+.1f}%" if account_value > 0 else "N/A",
    )

    return Panel(
        Columns([left_table, right_table], expand=True),
        title="[bold cyan]METRICS[/bold cyan]",
        box=box.HEAVY,
    )


def create_execution_details_panel(
    successful_trades: list[dict], all_trades: list[dict]
) -> Panel:
    """Create execution details table."""
    # Create a set of successful trade identifiers (coin + is_buy combination)
    successful_ids = {(t["coin"], t["is_buy"]) for t in successful_trades}
    failed_trades = [
        t for t in all_trades if (t["coin"], t["is_buy"]) not in successful_ids
    ]

    # Calculate volumes for successful trades
    success_volume = sum(
        float(t.get("fill_data", {}).get("totalSz", 0))
        * float(t.get("fill_data", {}).get("avgPx", 0))
        for t in successful_trades
        if "fill_data" in t
    )

    title = (
        f"[bold cyan]EXECUTION DETAILS[/bold cyan]  [dim]│[/dim]  "
        f"[green]{len(successful_trades)} SUCCESS (${success_volume:,.2f})[/green] "
        f"[red]{len(failed_trades)} FAILED[/red]"
    )

    table = Table(
        box=box.HEAVY_HEAD,
        show_lines=False,
        header_style="bold cyan on #001926",
        title_style="bold cyan",
    )

    # Define columns
    table.add_column("COIN", style="cyan", width=8)
    table.add_column("SIDE", justify="center", width=6)
    table.add_column("ACTION", justify="center", width=8)
    table.add_column("SIZE", justify="right", width=10)
    table.add_column("EXPECTED", justify="right", width=10)
    table.add_column("FILLED", justify="right", width=10)
    table.add_column("SLIPPAGE", justify="right", width=10)
    table.add_column("VALUE", justify="right", width=12)
    table.add_column("FEE", justify="right", width=8)
    table.add_column("STATUS", justify="center", width=8)
    
    # Action styling (matching create_trades_panel)
    action_styles = {
        "open": "[green]OPEN[/green]",
        "close": "[red]CLOSE[/red]",
        "flip": "[yellow]FLIP[/yellow]",
        "reduce": "[blue]REDUCE[/blue]",
        "increase": "[cyan]ADD[/cyan]",
    }

    # Add successful trades first
    for trade in successful_trades:
        if "fill_data" in trade:
            fill = trade["fill_data"]
            side = "BUY" if trade["is_buy"] else "SELL"
            side_style = "green" if side == "BUY" else "red"
            slippage_style = "green" if trade.get("slippage_pct", 0) <= 0 else "red"
            
            # Get action type
            trade_type = trade.get("type", "increase")
            action = action_styles.get(trade_type, "[dim]ADJUST[/dim]")

            table.add_row(
                f"[bold]{trade['coin']}[/bold]",
                f"[{side_style}]{side}[/{side_style}]",
                action,
                f"{float(fill['totalSz']):.4f}",
                format_currency(trade["price"], compact=True),
                format_currency(float(fill["avgPx"]), compact=True),
                f"[{slippage_style}]{trade.get('slippage_pct', 0):+.3f}%[/{slippage_style}]",
                format_currency(float(fill["totalSz"]) * float(fill["avgPx"])),
                f"${trade.get('actual_fee', 0):.2f}",
                "[green]✓[/green]",
            )
        elif trade.get("resting"):
            # Handle resting orders (Gtc/Alo orders posted to book)
            side = "BUY" if trade["is_buy"] else "SELL"
            side_style = "green" if side == "BUY" else "red"
            oid = trade.get("oid", "")
            oid_short = str(oid)[:8] if oid else "-"
            
            # Get action type
            trade_type = trade.get("type", "increase")
            action = action_styles.get(trade_type, "[dim]ADJUST[/dim]")

            table.add_row(
                f"[bold]{trade['coin']}[/bold]",
                f"[{side_style}]{side}[/{side_style}]",
                action,
                f"{trade['sz']:.4f}",
                format_currency(trade["price"], compact=True),
                f"[yellow]OPEN[/yellow]",
                f"[dim]OID:{oid_short}[/dim]",
                format_currency(trade["sz"] * trade["price"]),
                "[dim]-[/dim]",
                "[yellow]●[/yellow]",
            )

    # Add failed trades
    for trade in failed_trades:
        side = "BUY" if trade["is_buy"] else "SELL"
        side_style = "green" if side == "BUY" else "red"
        
        # Get action type
        trade_type = trade.get("type", "increase")
        action = action_styles.get(trade_type, "[dim]ADJUST[/dim]")

        table.add_row(
            f"[bold]{trade['coin']}[/bold]",
            f"[{side_style}]{side}[/{side_style}]",
            action,
            f"{trade['sz']:.4f}",
            format_currency(trade["price"], compact=True),
            "[red]-[/red]",
            "[red]-[/red]",
            "[red]-[/red]",
            "[dim]-[/dim]",
            "[red]✗[/red]",
        )

    panel = Panel(table, title=title, box=box.HEAVY)
    return panel


def display_execution_summary(
    console: Console,
    successful_trades: list[dict],
    all_trades: list[dict],
    target_positions: dict,
    account_value: float,
) -> None:
    """Display execution summary after trades complete.

    Prints panels sequentially (header → summary metrics → details),
    matching the style of the trade plan output.
    """
    # Header
    header = Panel(
        Text("EXECUTION SUMMARY", style="bold cyan", justify="center"),
        box=DOUBLE,
        style="cyan",
    )
    console.print("\n")
    console.print(header)

    # Summary metrics
    summary_panel = create_execution_metrics_panel(
        successful_trades, all_trades, target_positions, account_value
    )
    console.print(summary_panel)

    # Details (only when there were any trades or failures)
    if successful_trades or (len(all_trades) > len(successful_trades)):
        details_panel = create_execution_details_panel(successful_trades, all_trades)
        console.print(details_panel)
    else:
        console.print(Panel("[dim]No trades executed[/dim]", box=box.HEAVY))


def display_backtest_summary(
    console: Console, result, config=None, show_positions=False
):
    """Display comprehensive backtest results in a cleaner sequential layout

    Args:
        console: Rich console for output
        result: BacktestResult with daily data and stats
        config: Optional BacktestConfig to display
        show_positions: Whether to show the detailed position analysis table
    """

    # 0. Disclaimer warning
    disclaimer = Panel(
        Text.from_markup(
            "[yellow]\n Past performance does not guarantee future results. "
            "These results are hypothetical and subject to limitations.[/yellow]\n",
            justify="center",
        ),
        title="[bold yellow] BACKTEST DISCLAIMER [/bold yellow]",
        box=box.HEAVY,
        border_style="yellow",
    )
    console.print(disclaimer)

    # 1. Header
    header = Panel(
        Text(
            "BACKTEST RESULTS :: PERFORMANCE ANALYSIS",
            style="bold cyan",
            justify="center",
        ),
        box=DOUBLE,
        style="cyan",
    )
    console.print(header)

    # 2-3. Metrics + Charts stacked on the left, Config as a persistent right sidebar
    metrics_panel = create_backtest_metrics_panel(result.stats)

    if len(result.daily) > 0:
        equity_panel = create_linechart_panel(
            result.daily, "equity", "cyan", "Equity ($)"
        )
        drawdown_panel = create_linechart_panel(
            result.daily, "drawdown", "red", "Drawdown (%)"
        )
        dist_panel = create_backtest_distributions(result.daily)
    else:
        equity_panel = Panel("[dim]No data[/dim]", box=box.HEAVY)
        drawdown_panel = Panel("[dim]No data[/dim]", box=box.HEAVY)
        dist_panel = Panel("[dim]No distribution data[/dim]", box=box.HEAVY)

    top_row = Columns([equity_panel, drawdown_panel], expand=True)
    left_group = Group(metrics_panel, top_row, dist_panel)

    summary_layout = Layout()
    summary_layout.split_row(
        Layout(name="main", ratio=3), Layout(name="config", ratio=1)
    )

    summary_layout["main"].update(left_group)
    summary_layout["config"].update(
        create_backtest_config_panel(config)
        if config
        else Panel(
            "[dim]No configuration data[/dim]",
            box=box.HEAVY,
            title="[bold cyan]BACKTEST CONFIG[/bold cyan]",
        )
    )

    console.print(summary_layout)

    # 4. Positions table (full width) - only if flag is set
    if show_positions and len(result.rebalance_positions) > 0:
        positions_table = create_enhanced_positions_table(
            result.rebalance_positions, result.daily
        )
        console.print(positions_table)


def create_backtest_config_panel(config) -> Panel:
    """Create configuration panel for backtest sidebar using tree-like layout."""
    tree = Table(show_header=False, box=None, padding=(0, 0))
    tree.add_column("Setting", style="cyan", width=18, no_wrap=True)
    tree.add_column("Value", style="white")

    # Environment/date range
    if config.start_date or config.end_date:
        start_str = (
            config.start_date.strftime("%Y-%m-%d") if config.start_date else "start"
        )
        end_str = config.end_date.strftime("%Y-%m-%d") if config.end_date else "end"
        tree.add_row("[bold]RANGE[/bold]", "")
        tree.add_row("├─ From", start_str)
        tree.add_row("└─ To", end_str)
        tree.add_row("", "")

    # Portfolio
    leverage_color = (
        "green"
        if config.target_leverage <= 2
        else "yellow"
        if config.target_leverage <= 3
        else "red"
    )
    tree.add_row("[bold]PORTFOLIO[/bold]", "")
    tree.add_row("├─ Long", f"[green]{config.num_long}[/green]")
    tree.add_row("├─ Short", f"[red]{config.num_short}[/red]")
    tree.add_row(
        "├─ Leverage",
        f"[{leverage_color}]{config.target_leverage:.1f}x[/{leverage_color}]",
    )
    tree.add_row("├─ Rebalance", f"{config.rebalance_every_n_days}d")
    weighting_method = getattr(config, "weighting_method", "rank_power")
    method_color = "cyan" if weighting_method in ("hrp", "hrp_lw") else "white"
    tree.add_row("└─ Method", f"[{method_color}]{weighting_method}[/{method_color}]")
    tree.add_row("", "")

    # Costs
    tree.add_row("[bold]COSTS[/bold]", "")
    tree.add_row("├─ Fee", f"{config.fee_bps:.1f}bps")
    tree.add_row("└─ Slippage", f"{config.slippage_bps:.1f}bps")
    tree.add_row("", "")

    # Data
    source_name = (
        config.predictions_path.split("/")[-1]
        if "/" in config.predictions_path
        else config.predictions_path
    )
    provider = getattr(config, "data_provider", None)
    provider_color = (
        "green"
        if provider == "crowdcent"
        else "yellow"
        if provider == "numerai"
        else "white"
    )
    tree.add_row("[bold]DATA[/bold]", "")
    if provider:
        tree.add_row("├─ Provider", f"[{provider_color}]{provider}[/{provider_color}]")
    tree.add_row("├─ Source", source_name)
    tree.add_row("└─ Pred Col", str(config.pred_value_column))

    return Panel(tree, title="[bold cyan]BACKTEST CONFIG[/bold cyan]", box=box.HEAVY)


def create_backtest_metrics_panel(stats: dict) -> Panel:
    """Create metrics panel for backtest results."""
    # Create two-column layout for metrics
    left_table = Table(show_header=False, box=None, padding=(0, 1))
    left_table.add_column("", width=15)
    left_table.add_column("", justify="right")

    right_table = Table(show_header=False, box=None, padding=(0, 1))
    right_table.add_column("", width=15)
    right_table.add_column("", justify="right")

    # Left column: Returns and basic metrics
    total_return = stats.get("total_return", 0)
    cagr = stats.get("cagr", 0)
    final_equity = stats.get("final_equity", 0)

    ret_color = "green" if total_return >= 0 else "red"
    cagr_color = "green" if cagr >= 0 else "red"

    left_table.add_row("DAYS", f"{stats.get('days', 0):,}")
    left_table.add_row("FINAL EQUITY", format_currency(final_equity, compact=True))
    left_table.add_row("TOTAL RETURN", f"[{ret_color}]{total_return:.1%}[/{ret_color}]")
    left_table.add_row("CAGR", f"[{cagr_color}]{cagr:.1%}[/{cagr_color}]")
    left_table.add_row("WIN RATE", f"{stats.get('win_rate', 0):.1%}")

    # Right column: Risk metrics
    sharpe = stats.get("sharpe_ratio", 0)
    sortino = stats.get("sortino_ratio", 0)
    calmar = stats.get("calmar_ratio", 0)
    max_dd = stats.get("max_drawdown", 0)
    vol = stats.get("annual_volatility", 0)

    # Color code risk metrics
    sharpe_color = "green" if sharpe > 1 else "yellow" if sharpe > 0.5 else "red"
    dd_color = "green" if max_dd > -0.1 else "yellow" if max_dd > -0.2 else "red"

    right_table.add_row("SHARPE", f"[{sharpe_color}]{sharpe:.2f}[/{sharpe_color}]")
    right_table.add_row("SORTINO", f"{sortino:.2f}")
    right_table.add_row("CALMAR", f"{calmar:.2f}")
    right_table.add_row("MAX DRAWDOWN", f"[{dd_color}]{max_dd:.1%}[/{dd_color}]")
    right_table.add_row("VOLATILITY", f"{vol:.1%}")

    return Panel(
        Columns([left_table, right_table], expand=True),
        title="[bold cyan]PERFORMANCE METRICS[/bold cyan]",
        box=box.HEAVY,
    )


def create_linechart_panel(daily_df, metric: str, color: str, y_label: str) -> Panel:
    """Create line chart panel using plotext."""

    def plot_line(plt):
        plt.plot(daily_df[metric], marker="braille", color=color)
        plt.xlabel("Days")
        plt.ylabel(y_label)

    return create_plotext_panel(
        plot_line,
        f"[bold cyan]{metric.upper()}[/bold cyan]",
        style=color,
        height=9,
        width=40,
    )


def create_backtest_distributions(daily_df) -> Panel:
    """Create backtest distributions using standardized small-multiples like optimize."""
    series_map: dict[str, dict[str, Any]] = {}

    # Returns distribution
    if "returns" in daily_df.columns:
        returns = daily_df["returns"].to_list()
        if returns:
            series_map["RETURNS"] = {"values": returns, "color": "green", "bins": 15}

    # Drawdown distribution
    if "drawdown" in daily_df.columns:
        drawdowns = daily_df["drawdown"].to_list()
        if drawdowns:
            series_map["DRAWDOWN"] = {"values": drawdowns, "color": "red", "bins": 15}

    # Turnover distribution (non-zero only)
    if "turnover" in daily_df.columns:
        turnovers = daily_df["turnover"].to_list()
        turnovers_nz = [t for t in turnovers if t and t != 0]
        if turnovers_nz:
            series_map["TURNOVER"] = {
                "values": turnovers_nz,
                "color": "yellow",
                "bins": 15,
            }

    panel = (
        create_small_multiples_panel(
            series_map, "[bold cyan]DAILY DISTRIBUTIONS[/bold cyan]"
        )
        if series_map
        else None
    )
    if panel is not None:
        return panel
    return Panel("[dim]No distribution data available[/dim]", box=box.HEAVY)


def create_latest_positions_panel(positions_df) -> Panel:
    """Create panel showing latest position snapshot."""
    import polars as pl

    if len(positions_df) == 0:
        return Panel("[dim]No position data[/dim]", box=box.HEAVY)

    # Get last rebalance date
    latest_date = positions_df["date"].max()
    latest_positions = positions_df.filter(positions_df["date"] == latest_date)

    # Sort by absolute weight
    latest_positions = latest_positions.with_columns(
        pl.col("weight").abs().alias("abs_weight")
    ).sort("abs_weight", descending=True)

    table = Table(
        show_header=True,
        box=box.SIMPLE_HEAD,
        header_style="bold cyan on #001926",
        padding=(0, 1),
    )

    table.add_column("COIN", style="cyan")
    table.add_column("WEIGHT", justify="right")

    # Count positions
    long_count = sum(
        1 for row in latest_positions.iter_rows(named=True) if row["weight"] > 0
    )
    short_count = len(latest_positions) - long_count

    for row in latest_positions.iter_rows(named=True):
        weight = row["weight"]
        weight_style = "green" if weight > 0 else "red"

        table.add_row(
            row["id"],
            f"[{weight_style}]{abs(weight):.1%}[/{weight_style}]",
        )

    title = (
        f"[bold cyan]FINAL POSITIONS[/bold cyan] [dim]│[/dim] "
        f"[green]{long_count}L[/green] [red]{short_count}S[/red] [dim]│[/dim] "
        f"{latest_date.strftime('%Y-%m-%d')}"
    )

    return Panel(table, title=title, box=box.HEAVY)


def create_enhanced_positions_table(positions_df, daily_df) -> Panel:
    """Create enhanced positions table with detailed statistics."""
    import polars as pl

    if len(positions_df) == 0:
        return Panel("[dim]No position data[/dim]", box=box.HEAVY)

    # Get unique dates for counting
    unique_dates = positions_df["date"].unique().sort()
    total_periods = len(unique_dates)

    # Get last rebalance date
    latest_date = positions_df["date"].max()

    # Calculate statistics for each asset
    position_stats = (
        positions_df.group_by("id")
        .agg(
            [
                # Count how many times this asset was held
                pl.col("weight")
                .filter(pl.col("weight") != 0)
                .count()
                .alias("times_held"),
                # Average weight when held (non-zero)
                pl.col("weight")
                .filter(pl.col("weight") != 0)
                .mean()
                .alias("avg_weight"),
                # Count longs vs shorts
                pl.col("weight")
                .filter(pl.col("weight") > 0)
                .count()
                .alias("times_long"),
                pl.col("weight")
                .filter(pl.col("weight") < 0)
                .count()
                .alias("times_short"),
                # First and last appearance
                pl.col("date").min().alias("first_date"),
                pl.col("date").max().alias("last_date"),
                # Current weight (from latest date)
                pl.col("weight")
                .filter(pl.col("date") == latest_date)
                .first()
                .alias("current_weight"),
            ]
        )
        .filter(pl.col("times_held") > 0)  # Only include assets that were held
    )

    # Add a column for predominant side
    position_stats = position_stats.with_columns(
        pl.when(pl.col("times_long") > pl.col("times_short"))
        .then(pl.lit("LONG"))
        .when(pl.col("times_short") > pl.col("times_long"))
        .then(pl.lit("SHORT"))
        .otherwise(pl.lit("MIXED"))
        .alias("predominant_side")
    )

    # Sort by times held (frequency) and then by absolute average weight
    position_stats = position_stats.sort(
        [
            pl.col("times_held").is_not_null(),  # Non-null first
            pl.col("times_held"),
            pl.col("avg_weight").abs(),
        ],
        descending=[True, True, True],
    )

    # Create the table
    table = Table(
        box=box.HEAVY_HEAD,
        show_lines=False,
        header_style="bold cyan on #001926",
        expand=True,
    )

    # Define columns
    table.add_column("COIN", style="cyan", width=8)
    table.add_column("SIDE", justify="center", width=8)
    table.add_column("FREQUENCY", justify="right", width=10)
    table.add_column("AVG WEIGHT", justify="right", width=10)
    table.add_column("CURRENT", justify="right", width=10)
    table.add_column("FIRST HELD", justify="center", width=12)
    table.add_column("LAST HELD", justify="center", width=12)
    table.add_column("CONSISTENCY", justify="center", width=12)

    # Add rows
    for row in position_stats.iter_rows(named=True):
        coin = row["id"]
        side = row["predominant_side"]
        times_held = row["times_held"] or 0
        avg_weight = row["avg_weight"] or 0
        current_weight = row["current_weight"] or 0
        first_date = row["first_date"]
        last_date = row["last_date"]

        # Determine side color
        if side == "LONG":
            side_style = "green"
        elif side == "SHORT":
            side_style = "red"
        else:
            side_style = "yellow"

        # Format frequency as fraction and percentage
        freq_pct = (times_held / total_periods * 100) if total_periods > 0 else 0
        freq_str = f"{times_held}/{total_periods} ({freq_pct:.0f}%)"

        # Format average weight
        avg_weight_str = f"[{'green' if avg_weight > 0 else 'red'}]{abs(avg_weight):.1%}[/{'green' if avg_weight > 0 else 'red'}]"

        # Format current weight
        if current_weight == 0:
            current_str = "[dim]-[/dim]"
        else:
            current_str = f"[{'green' if current_weight > 0 else 'red'}]{abs(current_weight):.1%}[/{'green' if current_weight > 0 else 'red'}]"

        # Format dates
        first_str = first_date.strftime("%Y-%m-%d") if first_date else "-"
        last_str = last_date.strftime("%Y-%m-%d") if last_date else "-"

        # Consistency indicator (visual bar)
        consistency_bar = create_data_bar(
            freq_pct, 100, width=8, filled_char="▓", empty_char="░"
        )
        consistency_color = (
            "green" if freq_pct >= 75 else "yellow" if freq_pct >= 50 else "dim"
        )
        consistency_str = (
            f"[{consistency_color}]{consistency_bar}[/{consistency_color}]"
        )

        table.add_row(
            f"[bold]{coin}[/bold]",
            f"[{side_style}]{side}[/{side_style}]",
            freq_str,
            avg_weight_str,
            current_str,
            first_str,
            last_str,
            consistency_str,
        )

    # Count current positions
    current_positions = position_stats.filter(pl.col("current_weight") != 0)
    current_longs = len(current_positions.filter(pl.col("current_weight") > 0))
    current_shorts = len(current_positions.filter(pl.col("current_weight") < 0))

    # Calculate some summary stats
    total_unique_assets = len(position_stats)
    most_consistent = position_stats.head(1)
    if len(most_consistent) > 0:
        top_asset = most_consistent["id"][0]
        top_freq = most_consistent["times_held"][0]
        top_pct = (top_freq / total_periods * 100) if total_periods > 0 else 0
        consistency_note = f"Most consistent: {top_asset} ({top_pct:.0f}%)"
    else:
        consistency_note = ""

    title = (
        f"[bold cyan]POSITION ANALYSIS[/bold cyan]  [dim]│[/dim]  "
        f"{total_unique_assets} unique assets over {total_periods} periods  [dim]│[/dim]  "
        f"Current: [green]{current_longs}L[/green] [red]{current_shorts}S[/red]"
    )

    if consistency_note:
        title += f"  [dim]│[/dim]  {consistency_note}"

    return Panel(table, title=title, box=box.HEAVY)


def display_optimization_results(
    console: Console, results_df, metric: str, top_n: int = 20, config=None
):
    """Display optimization results."""

    # Disclaimer warning first
    disclaimer = Panel(
        Text.from_markup(
            "[yellow]\n Optimized parameters are based on historical data and may be overfit. "
            "Past optimal parameters may not remain optimal in future market conditions.[/yellow]\n",
            justify="center",
        ),
        title="[bold yellow] OPTIMIZATION DISCLAIMER [/bold yellow]",
        box=box.HEAVY,
        border_style="yellow",
    )
    console.print(disclaimer)

    layout = Layout()
    layout.split_column(Layout(name="header", size=3), Layout(name="body"))

    # Header
    header = Panel(
        Text(
            f"OPTIMIZATION RESULTS :: {metric.upper()}",
            style="bold cyan",
            justify="center",
        ),
        box=DOUBLE,
        style="cyan",
    )
    layout["header"].update(header)

    # Body: Main results + best params summary
    layout["body"].split_row(
        Layout(name="results", ratio=3), Layout(name="summary", ratio=1)
    )

    # Results table
    results_panel = create_optimization_results_table(results_df, metric, top_n)
    layout["results"].update(results_panel)

    # Summary panel with best parameters
    if len(results_df) > 0:
        summary_panel = create_optimization_summary_panel(
            results_df.head(1), metric, config
        )
        layout["summary"].update(summary_panel)
    else:
        layout["summary"].update(Panel("[dim]No results[/dim]", box=box.HEAVY))

    console.print(layout)

    sm_panel = create_optimization_small_multiples_panel(results_df)
    if sm_panel is not None:
        console.print(sm_panel)


def _create_hist_panel(
    values, title: str, color: str, bins: int = 15, width: int = 24, height: int = 6
) -> Panel:
    """Create a compact histogram panel for small multiples."""

    def plot_hist(plt):
        if not values:
            return
        plt.hist(values, bins=bins, color=color)
        plt.xlabel("")
        plt.ylabel("")

    return create_plotext_panel(
        plot_hist, f"[bold]{title}[/bold]", width=width, height=height, style=color
    )


def create_small_multiples_panel(
    series_map: dict[str, dict[str, Any]], title: str
) -> Panel | None:
    """Create a small-multiples panel from a mapping of label -> values."""
    panels = []
    # Fixed sizes to encourage consistent visual scale
    for label, conf in series_map.items():
        values = conf.get("values", [])
        if values is None:
            values = []
        color = conf.get("color", "cyan")
        bins = conf.get("bins", 15)
        p = _create_hist_panel(values, label, color=color, bins=bins)
        panels.append(p)
    if not panels:
        return None
    return Panel(Columns(panels, expand=True), title=title, box=box.HEAVY)


def create_optimization_small_multiples_panel(results_df) -> Panel | None:
    """Build small-multiples histograms for optimization metrics: Sharpe, CAGR, Calmar, Max DD, Volatility."""
    try:
        cols = set(results_df.columns)
        series_map = {}
        if "sharpe" in cols:
            series_map["SHARPE"] = {
                "values": results_df["sharpe"].to_list(),
                "color": "cyan",
            }
        if "cagr" in cols:
            series_map["CAGR"] = {
                "values": results_df["cagr"].to_list(),
                "color": "green",
            }
        if "calmar" in cols:
            series_map["CALMAR"] = {
                "values": results_df["calmar"].to_list(),
                "color": "blue",
            }
        if "max_dd" in cols:
            series_map["MAX DD"] = {
                "values": results_df["max_dd"].to_list(),
                "color": "red",
            }
        if "volatility" in cols:
            series_map["VOL"] = {
                "values": results_df["volatility"].to_list(),
                "color": "yellow",
            }
        if not series_map:
            return None
        return create_small_multiples_panel(
            series_map, "[bold cyan]METRIC DISTRIBUTIONS[/bold cyan]"
        )
    except Exception:
        return None


def create_optimization_results_table(results_df, metric: str, top_n: int) -> Panel:
    """Create optimization results table panel."""
    table = Table(
        box=box.HEAVY_HEAD,
        show_lines=False,
        header_style="bold cyan on #001926",
        expand=True,
    )

    # Add columns with consistent styling
    table.add_column("RANK", style="dim", width=4, justify="right")
    table.add_column("LONG", style="green", justify="right", width=6)
    table.add_column("SHORT", style="red", justify="right", width=6)
    table.add_column("LEV", style="yellow", justify="right", width=6)
    table.add_column("DAYS", style="cyan", justify="right", width=6)
    table.add_column("POWER", style="magenta", justify="right", width=6)
    table.add_column(
        "SHARPE",
        justify="right",
        width=8,
        style="bold white" if metric == "sharpe" else "dim",
    )
    table.add_column(
        "CAGR",
        justify="right",
        width=8,
        style="bold white" if metric == "cagr" else "dim",
    )
    table.add_column(
        "CALMAR",
        justify="right",
        width=8,
        style="bold white" if metric == "calmar" else "dim",
    )
    table.add_column("MAX DD", justify="right", width=8)
    table.add_column("EQUITY", justify="right", width=10)

    for i, row in enumerate(results_df.head(top_n).iter_rows(named=True), 1):
        # Color code metrics based on performance
        sharpe = row["sharpe"]
        sharpe_color = "green" if sharpe > 1 else "yellow" if sharpe > 0.5 else "red"

        dd = row["max_dd"]
        dd_color = "green" if dd > -0.1 else "yellow" if dd > -0.2 else "red"

        cagr = row["cagr"]
        cagr_color = "green" if cagr > 0.2 else "yellow" if cagr > 0 else "red"

        # Special highlighting for top 3
        rank_style = "bold cyan" if i == 1 else "cyan" if i <= 3 else "dim"

        table.add_row(
            f"[{rank_style}]{i}[/{rank_style}]",
            str(row["num_long"]),
            str(row["num_short"]),
            f"{row['leverage']:.1f}x",
            str(row["rebalance_days"]),
            f"{row['rank_power']:.1f}",
            f"[{sharpe_color}]{sharpe:.2f}[/{sharpe_color}]",
            f"[{cagr_color}]{cagr:.1%}[/{cagr_color}]",
            f"{row['calmar']:.2f}",
            f"[{dd_color}]{dd:.1%}[/{dd_color}]",
            format_currency(row["final_equity"], compact=True),
        )

    # Calculate title with statistics
    total_tested = len(results_df)
    positive_sharpe = sum(
        1 for row in results_df.iter_rows(named=True) if row["sharpe"] > 0
    )

    title = (
        f"[bold cyan]TOP {top_n} COMBINATIONS[/bold cyan]  [dim]│[/dim]  "
        f"Tested {total_tested}  [dim]│[/dim]  "
        f"Positive Sharpe {positive_sharpe}/{total_tested} ({positive_sharpe / total_tested * 100:.1f}%)"
    )

    return Panel(table, title=title, box=box.HEAVY)


def create_optimization_summary_panel(best_row_df, metric: str, config=None) -> Panel:
    """Create summary panel for best parameters."""
    best = best_row_df.iter_rows(named=True).__next__()

    # Create metrics table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("", width=12)
    table.add_column("", justify="right")

    # Best configuration
    table.add_row("[bold]BEST CONFIG[/bold]", "")
    table.add_row("", "")
    table.add_row("LONG", f"[green]{best['num_long']}[/green]")
    table.add_row("SHORT", f"[red]{best['num_short']}[/red]")
    table.add_row("LEVERAGE", f"[yellow]{best['leverage']:.1f}x[/yellow]")
    table.add_row("REBALANCE", f"{best['rebalance_days']} days")
    table.add_row("RANK POWER", f"[magenta]{best['rank_power']:.1f}[/magenta]")
    table.add_row("", "")

    # Performance metrics
    table.add_row("[bold]METRICS[/bold]", "")
    table.add_row("", "")

    # Highlight the optimization metric
    if metric == "sharpe":
        table.add_row("SHARPE", f"[bold cyan]{best['sharpe']:.2f}[/bold cyan]")
        table.add_row("CAGR", f"{best['cagr']:.1%}")
        table.add_row("CALMAR", f"{best['calmar']:.2f}")
    elif metric == "cagr":
        table.add_row("SHARPE", f"{best['sharpe']:.2f}")
        table.add_row("CAGR", f"[bold cyan]{best['cagr']:.1%}[/bold cyan]")
        table.add_row("CALMAR", f"{best['calmar']:.2f}")
    else:  # calmar
        table.add_row("SHARPE", f"{best['sharpe']:.2f}")
        table.add_row("CAGR", f"{best['cagr']:.1%}")
        table.add_row("CALMAR", f"[bold cyan]{best['calmar']:.2f}[/bold cyan]")

    table.add_row("MAX DD", f"{best['max_dd']:.1%}")
    table.add_row("VOLATILITY", f"{best['volatility']:.1%}")
    table.add_row("", "")
    table.add_row("FINAL EQUITY", format_currency(best["final_equity"]))

    # Add data source information if config is provided
    if config:
        table.add_row("", "")
        table.add_row("[bold]DATA[/bold]", "")
        table.add_row("", "")

        # Provider
        provider = getattr(config, "data_provider", None)
        if provider:
            provider_color = (
                "green"
                if provider == "crowdcent"
                else "yellow"
                if provider == "numerai"
                else "white"
            )
            table.add_row(
                "PROVIDER", f"[{provider_color}]{provider}[/{provider_color}]"
            )

        # Source file
        source_name = (
            config.predictions_path.split("/")[-1]
            if "/" in config.predictions_path
            else config.predictions_path
        )
        table.add_row(
            "SOURCE", source_name[:12] + "..." if len(source_name) > 15 else source_name
        )

        # Prediction column
        table.add_row("PRED COL", str(config.pred_value_column)[:15])

    return Panel(
        table, title=f"[bold cyan]BEST BY {metric.upper()}[/bold cyan]", box=box.HEAVY
    )


def create_optimization_progress_display(
    current: int,
    total: int,
    current_params: dict,
    best_so_far: dict | None = None,
    elapsed_time: float = 0,
) -> Layout:
    """Create live progress display for optimization."""
    from rich.layout import Layout
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.align import Align

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", size=12),
        Layout(name="footer", size=3),
    )

    # Header
    header = Panel(
        Text("OPTIMIZATION IN PROGRESS", style="bold cyan blink", justify="center"),
        box=DOUBLE,
        style="cyan",
    )
    layout["header"].update(header)

    # Body: Progress bar and current/best params
    layout["body"].split_column(
        Layout(name="progress", size=5), Layout(name="params", size=7)
    )

    # Create progress bar
    progress = Progress(
        TextColumn("[bold cyan]Testing:[/bold cyan]"),
        BarColumn(bar_width=40, style="cyan", complete_style="green"),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("[cyan]{task.percentage:>3.0f}%[/cyan]"),
        TimeRemainingColumn(),
        expand=False,
    )

    task = progress.add_task("Optimization", total=total, completed=current)
    progress.update(task, completed=current)

    progress_panel = Panel(
        Align.center(progress, vertical="middle"),
        box=box.HEAVY,
        title="[bold cyan]PROGRESS[/bold cyan]",
    )
    layout["progress"].update(progress_panel)

    # Parameters display
    layout["params"].split_row(
        Layout(name="current", ratio=1), Layout(name="best", ratio=1)
    )

    # Current parameters
    current_table = Table(show_header=False, box=None, padding=(0, 1))
    current_table.add_column("", width=12)
    current_table.add_column("", justify="right")

    current_table.add_row("COMBINATION", f"{current}/{total}")
    current_table.add_row("", "")
    current_table.add_row(
        "LONG", f"[green]{current_params.get('num_long', '-')}[/green]"
    )
    current_table.add_row("SHORT", f"[red]{current_params.get('num_short', '-')}[/red]")
    current_table.add_row(
        "LEVERAGE", f"[yellow]{current_params.get('leverage', 0):.1f}x[/yellow]"
    )
    current_table.add_row("DAYS", f"{current_params.get('rebalance_days', '-')}")

    layout["current"].update(
        Panel(current_table, title="[bold cyan]TESTING[/bold cyan]", box=box.HEAVY)
    )

    # Best so far
    if best_so_far:
        best_table = Table(show_header=False, box=None, padding=(0, 1))
        best_table.add_column("", width=12)
        best_table.add_column("", justify="right")

        best_table.add_row(
            "SHARPE", f"[green]{best_so_far.get('sharpe', 0):.2f}[/green]"
        )
        best_table.add_row("CAGR", f"{best_so_far.get('cagr', 0):.1%}")
        best_table.add_row("", "")
        best_table.add_row("CONFIG", "")
        best_table.add_row(
            "L/S",
            f"{best_so_far.get('num_long', '-')}/{best_so_far.get('num_short', '-')}",
        )
        best_table.add_row("LEV", f"{best_so_far.get('leverage', 0):.1f}x")

        layout["best"].update(
            Panel(
                best_table,
                title="[bold green]BEST SO FAR[/bold green]",
                box=box.HEAVY,
                border_style="green",
            )
        )
    else:
        layout["best"].update(
            Panel(
                "[dim]No results yet[/dim]",
                title="[bold]BEST SO FAR[/bold]",
                box=box.HEAVY,
            )
        )

    # Footer
    eta = (elapsed_time / current * (total - current)) if current > 0 else 0
    eta_str = f"{int(eta // 60)}:{int(eta % 60):02d}" if eta > 0 else "--:--"

    footer_text = (
        f"[dim]Elapsed: {int(elapsed_time // 60)}:{int(elapsed_time % 60):02d} │ "
        f"ETA: {eta_str} │ "
        f"Rate: {current / elapsed_time:.1f}/s[/dim]"
        if elapsed_time > 0
        else "[dim]Starting...[/dim]"
    )

    layout["footer"].update(Panel(footer_text, box=box.HEAVY, style="dim"))

    return layout


def display_optimization_contours(console: Console, results_df, metric: str):
    """Display parameter heatmaps using ASCII visualization as small multiples."""
    import polars as pl

    leverages = results_df["leverage"].unique().sort().to_list()
    if not leverages:
        console.print(Panel("[dim]No data to visualize[/dim]", box=box.HEAVY))
        return

    header = Panel(
        Text(
            f"PARAMETER HEATMAPS :: {metric.upper()}",
            style="bold cyan",
            justify="center",
        ),
        box=DOUBLE,
        style="cyan",
    )
    console.print(header)

    # Collect heatmap panels for a grid layout (up to 2x3)
    heatmap_panels = []
    for leverage in leverages:
        df = results_df.filter(pl.col("leverage") == leverage)

        if len(df) < 4:
            heatmap_panels.append(
                Panel(
                    "[dim]Insufficient data[/dim]",
                    title=f"[bold]LEV {leverage:.1f}x[/bold]",
                    box=box.HEAVY,
                    height=12,
                )
            )
            continue

        pivot = df.pivot(
            index="num_long", on="num_short", values=metric, aggregate_function="mean"
        )

        longs = sorted(pivot["num_long"].to_list())
        shorts = sorted([c for c in pivot.columns if c != "num_long"])

        heatmap_str = create_ascii_heatmap(pivot, longs, shorts, metric)
        best = df[metric].max()
        worst = df[metric].min()
        subtitle = (
            f"[bold cyan]LEV {leverage:.1f}x[/bold cyan]  [dim]│[/dim]  "
            f"Best {best:.3f}  [dim]│[/dim]  Worst {worst:.3f}"
        )

        heatmap_panels.append(
            Panel(
                heatmap_str,
                title=subtitle,
                box=box.HEAVY,
                height=12,
            )
        )

    # Arrange panels into small multiples grid and print once
    if heatmap_panels:
        num_panels = len(heatmap_panels)
        # Choose columns per row for pleasant layout
        if num_panels == 1:
            cols_per_row = 1
        elif num_panels in (2, 4):
            cols_per_row = 2
        else:
            cols_per_row = 3

        rows = []
        for i in range(0, num_panels, cols_per_row):
            rows.append(Columns(heatmap_panels[i : i + cols_per_row], expand=True))

        from rich.table import Table as RichTable

        container = RichTable.grid(expand=True)
        for row in rows:
            container.add_row(row)

        console.print(container)


def create_ascii_heatmap(pivot_df, longs: list, shorts: list, metric: str) -> str:
    """Create an ASCII heatmap representation with sorted axes, legend-aware colors, and best-cell emphasis."""
    import polars as pl

    # Ensure numeric sort order (5, 10, 15 ...)
    longs = sorted(longs)
    shorts = sorted(shorts)

    # Find best cell for emphasis
    best_val = None
    best_coord = None
    for long_val in longs:
        row = pivot_df.filter(pl.col("num_long") == long_val)
        for short_val in shorts:
            if len(row) > 0 and str(short_val) in row.columns:
                val = row[str(short_val)][0]
                if val is not None and (best_val is None or val > best_val):
                    best_val = val
                    best_coord = (long_val, short_val)

    # Build the heatmap as a string
    lines = []
    header = "     L\\S  │ " + " ".join(f"{s:>4}" for s in shorts)
    lines.append(header)
    lines.append("─" * len(header))

    for long_val in longs:
        row_data = pivot_df.filter(pl.col("num_long") == long_val)
        row_str = f"  {long_val:>6} │ "
        if len(row_data) > 0:
            for short_val in shorts:
                if str(short_val) in row_data.columns:
                    val = row_data[str(short_val)][0]
                    if val is not None:
                        # Color buckets for sharpe-like metrics
                        if metric == "sharpe":
                            if val > 1.5:
                                txt = f"[green]{val:>4.1f}[/green]"
                            elif val > 0:
                                txt = f"[yellow]{val:>4.1f}[/yellow]"
                            else:
                                txt = f"[red]{val:>4.1f}[/red]"
                        else:
                            txt = f"{val:>4.1f}"
                        # Emphasize best cell
                        if best_coord == (long_val, short_val):
                            txt = f"[bold]{txt}[/bold]"
                        row_str += txt + " "
                    else:
                        row_str += "   - "
                else:
                    row_str += "   - "
        else:
            row_str += "   - " * len(shorts)
        lines.append(row_str)
    return "\n".join(lines)