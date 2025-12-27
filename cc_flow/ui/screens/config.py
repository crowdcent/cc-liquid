"""Configuration screen for cc-flow UI.

This module provides the ConfigScreen that displays and manages
trading configuration including profiles, data sources, portfolio settings,
execution parameters, and risk management.

The screen provides read-only display of current configuration with
a refresh button to reload settings.

The EnhancedConfigScreen extends this with inline editing and save capabilities.

Example:
    >>> from cc_flow.domain.config import TradingConfig
    >>> config = TradingConfig(...)
    >>> screen = ConfigScreen(config)
    >>> app.push_screen(screen)
"""

from __future__ import annotations

import contextlib
import copy
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static

from cc_flow.ui.screens.config_display import ConfigDisplayHelper
from cc_flow.ui.screens.config_serializer import ConfigSerializer
from cc_flow.ui.screens.config_updater import ConfigUpdater
from cc_flow.ui.screens.config_validators import FieldValidator

if TYPE_CHECKING:
    from cc_flow.domain.config import TradingConfig


class ConfigScreen(Screen):
    """Configuration management screen.

    Displays all trading configuration sections including:
    - Active profile information
    - Data source configuration
    - Portfolio construction settings
    - Execution parameters
    - Rebalancing schedule
    - Stop loss configuration

    Attributes:
        config: Trading configuration to display

    Actions:
        refresh: Reload configuration from source

    Example:
        >>> config = TradingConfig(...)
        >>> screen = ConfigScreen(config)
        >>> screen.action_refresh()  # Reload config
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, config: TradingConfig, **kwargs) -> None:
        """Initialize configuration screen.

        Args:
            config: Trading configuration to display
            **kwargs: Additional arguments passed to Screen
        """
        super().__init__(**kwargs)
        self.config = config
        self.display_helper = ConfigDisplayHelper(config)

    def compose(self) -> ComposeResult:
        """Compose the configuration UI.

        Yields:
            Container with all configuration sections and refresh button
        """
        helper = self.display_helper
        with Container(id="config-screen"), VerticalScroll():
                yield Static(
                    helper.format_section("Active Profile", helper.get_profile_info()),
                    classes="config-section",
                )
                yield Static(
                    helper.format_section("Data Source", helper.get_data_source_info()),
                    classes="config-section",
                )
                yield Static(
                    helper.format_section("Portfolio", helper.get_portfolio_info()),
                    classes="config-section",
                )
                yield Static(
                    helper.format_section("Execution", helper.get_execution_info()),
                    classes="config-section",
                )
                yield Static(
                    helper.format_section("Rebalancing", helper.get_rebalancing_info()),
                    classes="config-section",
                )
                yield Static(
                    helper.format_section("Stop Loss", helper.get_stop_loss_info()),
                    classes="config-section",
                )
                yield Button("Refresh Configuration", id="btn-refresh", variant="primary")

    # Delegate to display helper for backwards compatibility
    def _get_profile_info(self) -> dict[str, str | bool]:
        """Delegate to display helper."""
        return self.display_helper.get_profile_info()

    def _get_data_source_info(self) -> dict[str, str]:
        """Delegate to display helper."""
        return self.display_helper.get_data_source_info()

    def _get_portfolio_info(self) -> dict[str, str | int | float]:
        """Delegate to display helper."""
        return self.display_helper.get_portfolio_info()

    def _get_execution_info(self) -> dict[str, str | float]:
        """Delegate to display helper."""
        return self.display_helper.get_execution_info()

    def _get_rebalancing_info(self) -> dict[str, str | int]:
        """Delegate to display helper."""
        return self.display_helper.get_rebalancing_info()

    def _get_stop_loss_info(self) -> dict[str, str | float]:
        """Delegate to display helper."""
        return self.display_helper.get_stop_loss_info()

    def _format_config_section(self, title: str, data: dict) -> str:
        """Delegate to display helper."""
        return ConfigDisplayHelper.format_section(title, data)

    def action_refresh(self) -> None:
        """Refresh configuration display.

        Reloads all configuration sections from the config object.
        This action is bound to the 'r' key.

        Example:
            >>> screen.action_refresh()  # Refresh displayed config
        """
        # For now, just re-render the screen
        # In future, this could reload from file
        self.refresh(layout=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button pressed event
        """
        if event.button.id == "btn-refresh":
            self.action_refresh()


class EnhancedConfigScreen(Screen):
    """Enhanced configuration screen with edit and save capabilities.

    Extends the base ConfigScreen to support inline editing of configuration
    values and saving changes back to the YAML configuration file.

    Features:
        - Inline value editing with validation
        - Save changes to YAML file
        - Cancel/revert functionality
        - Field-level validation
        - Backup and restore

    Attributes:
        config: Trading configuration to display and edit
        config_path: Path to YAML configuration file
        is_editing: Whether currently in edit mode
        validator: Field value validator instance
        _backup: Backup copy of original configuration

    Example:
        >>> config = TradingConfig(...)
        >>> screen = EnhancedConfigScreen(config, config_path="config.yaml")
        >>> screen.action_enter_edit_mode()  # Start editing
        >>> screen._update_field("portfolio.num_long", "15")  # Edit field
        >>> screen.action_save()  # Save changes
    """

    BINDINGS = [
        ("e", "enter_edit_mode", "Edit"),
        ("s", "save", "Save"),
        ("c", "cancel_edit", "Cancel"),
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(
        self, config: TradingConfig, config_path: str, **kwargs
    ) -> None:
        """Initialize enhanced config screen.

        Args:
            config: Trading configuration to display and edit
            config_path: Path to YAML configuration file
            **kwargs: Additional arguments passed to Screen
        """
        super().__init__(**kwargs)
        self.config = config
        self.config_path = config_path
        self.is_editing = False
        self.validator = FieldValidator()
        self.updater = ConfigUpdater(config, self.validator)
        self.serializer = ConfigSerializer()
        self.display_helper = ConfigDisplayHelper(config)
        self._backup: TradingConfig | None = None

    def compose(self) -> ComposeResult:
        """Compose the enhanced configuration UI.

        Yields:
            Container with all configuration sections and action buttons
        """
        helper = self.display_helper
        with Container(id="config-screen"), VerticalScroll():
            yield Static(
                helper.format_section("Active Profile", helper.get_profile_info()),
                classes="config-section",
            )
            yield Static(
                helper.format_section("Data Source", helper.get_data_source_info()),
                classes="config-section",
            )
            yield Static(
                helper.format_section("Portfolio", helper.get_portfolio_info()),
                classes="config-section",
            )
            yield Static(
                helper.format_section("Execution", helper.get_execution_info()),
                classes="config-section",
            )
            yield Static(
                helper.format_section("Rebalancing", helper.get_rebalancing_info()),
                classes="config-section",
            )
            yield Static(
                helper.format_section("Stop Loss", helper.get_stop_loss_info()),
                classes="config-section",
            )
            yield Button("Save Configuration", id="btn-save", variant="success")

    def action_enter_edit_mode(self) -> None:
        """Enter edit mode and create backup."""
        self.is_editing = True
        self._create_backup()

    def action_exit_edit_mode(self) -> None:
        """Exit edit mode without saving."""
        self.is_editing = False

    def action_cancel_edit(self) -> None:
        """Cancel editing and restore from backup."""
        if self._backup:
            self._restore_backup()
        self.is_editing = False

    def action_save(self) -> None:
        """Save configuration to YAML file."""
        self._save_to_yaml()
        self.is_editing = False
        self._backup = None

    def _validate_field_value(self, field_name: str, value: str) -> bool:
        """Validate a field value using the validator."""
        return self.validator.validate(field_name, value)

    def _update_field(self, field_path: str, value: str) -> bool:
        """Update a configuration field value via updater."""
        return self.updater.update_field(field_path, value)

    def _create_backup(self) -> None:
        """Create a deep copy backup of current configuration."""
        self._backup = copy.deepcopy(self.config)

    def _restore_backup(self) -> None:
        """Restore configuration from backup."""
        if self._backup:
            self.config = copy.deepcopy(self._backup)

    def _save_to_yaml(self) -> None:
        """Save current configuration to YAML file using serializer."""
        # Error already logged by serializer
        with contextlib.suppress(Exception):
            self.serializer.save(self.config, self.config_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn-save":
            self.action_save()
