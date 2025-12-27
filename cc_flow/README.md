# cc-flow

Textualize-based Terminal User Interface (TUI) for cc-liquid portfolio rebalancing.

## Project Status

Version: 0.1.0a1 (Pre-Alpha)

This is a from-scratch reimplementation of cc-liquid using the Textual framework for a modern, interactive terminal UI experience.

## Directory Structure

```
cc_flow/
├── __init__.py              # Package initialization and metadata
├── pyproject.toml           # Project configuration and dependencies
├── README.md                # This file
│
├── core/                    # Core business logic
│   └── __init__.py          # Portfolio, rebalancing, backtesting
│
├── domain/                  # Domain models and types
│   └── __init__.py          # Pydantic models for Position, Trade, Portfolio, etc.
│
├── exchanges/               # Exchange connectors
│   └── __init__.py          # Hyperliquid and future exchange integrations
│
├── data_sources/            # Data source integrations
│   └── __init__.py          # CrowdCent, Numerai, local file sources
│
├── ui/                      # Textual TUI components
│   ├── __init__.py
│   ├── screens/             # Top-level application screens
│   │   └── __init__.py
│   ├── widgets/             # Reusable UI components
│   │   └── __init__.py
│   └── styles/              # TCSS styling and themes
│       └── __init__.py
│
├── utils/                   # Shared utilities
│   └── __init__.py          # Logging, formatting, helpers
│
├── config/                  # Configuration management
│   └── __init__.py          # YAML/env config handling
│
└── tests/                   # Test suite
    ├── __init__.py
    ├── test_structure.py    # Project structure validation tests
    ├── unit/                # Unit tests
    │   ├── __init__.py
    │   ├── test_exchanges/
    │   │   └── __init__.py
    │   └── test_data_sources/
    │       └── __init__.py
    ├── integration/         # Integration tests
    │   └── __init__.py
    └── fixtures/            # Shared test fixtures
        └── __init__.py
```

## Development Setup

This project uses `uv` as the package manager.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run structure validation tests
uv run pytest cc_flow/tests/test_structure.py -v

# Run with coverage
uv run pytest --cov=cc_flow
```

### Code Quality

```bash
# Linting
uv run ruff check
uv run ruff check --fix

# Formatting
uv run ruff format

# Type checking
uv run mypy cc_flow
```

## Architecture Principles

### SOLID Principles
- **Single Responsibility**: Each module has one clear purpose
- **Open/Closed**: Extensible through inheritance and protocols
- **Liskov Substitution**: Derived classes are substitutable
- **Interface Segregation**: Focused, minimal interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

### Code Standards
- Maximum 300 lines per module
- Complete type hints on all functions and classes
- Pydantic v2 for all data models
- Loguru for structured logging
- Comprehensive unit tests

### Design Patterns
- **Adapter Pattern**: Exchange connectors
- **Strategy Pattern**: Portfolio weighting schemes
- **Observer Pattern**: UI callbacks
- **Repository Pattern**: Data source access

## Key Dependencies

- **textual**: Terminal UI framework
- **pydantic**: Data validation and settings
- **polars**: Fast dataframe operations
- **hyperliquid-python-sdk**: Exchange integration
- **rich**: Terminal formatting
- **loguru**: Structured logging
- **pytest**: Testing framework

## Next Steps

See `CC-TODO.md` in the project root for the implementation roadmap.

## Contributing

This is pre-alpha software under active development. All code follows:
- Test-Driven Development (TDD)
- Type safety with complete annotations
- SOLID and DRY principles
- Comprehensive documentation

## License

MIT License - See LICENSE file in project root.

## Warning

This software controls real financial assets. Use with extreme caution:
- Always test on testnet first
- Never commit secrets (API keys, private keys)
- Validate all addresses before execution
- Understand the risks of automated trading
- High risk of complete loss of funds
