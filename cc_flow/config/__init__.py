"""
Configuration management for cc-flow.

This module handles loading, validation, and management of application
configuration from YAML files, environment variables, and CLI arguments.

Components:
    - Configuration models (Pydantic)
    - Config file loading (YAML)
    - Environment variable handling (.env)
    - Profile management
    - Secrets management

Design:
    - Secrets in .env (API keys, private keys)
    - Settings in YAML (addresses, parameters)
    - Pydantic models for validation
    - Multi-profile support
"""

from cc_flow.config.defaults import (
    get_default_config,
    get_mainnet_config,
    get_testnet_config,
)
from cc_flow.config.loader import ConfigLoader
from cc_flow.config.validator import ConfigValidator

__all__ = [
    "ConfigLoader",
    "ConfigValidator",
    "get_default_config",
    "get_testnet_config",
    "get_mainnet_config",
]
