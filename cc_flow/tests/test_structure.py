"""
Test suite for verifying cc-flow project structure.

This test ensures that all required directories and __init__.py files
are present and that basic imports work correctly.
"""

import sys
from pathlib import Path

import pytest

# Get the cc-flow root directory
CC_FLOW_ROOT = Path(__file__).parent.parent


class TestProjectStructure:
    """Test that the project structure matches the PRD specification."""

    def test_root_directory_exists(self):
        """Verify cc-flow root directory exists."""
        assert CC_FLOW_ROOT.exists(), "cc-flow directory should exist"
        assert CC_FLOW_ROOT.is_dir(), "cc-flow should be a directory"

    def test_required_directories_exist(self):
        """Verify all required top-level directories exist."""
        required_dirs = [
            "core",
            "domain",
            "exchanges",
            "data_sources",
            "ui",
            "utils",
            "config",
            "tests",
        ]

        for dir_name in required_dirs:
            dir_path = CC_FLOW_ROOT / dir_name
            assert dir_path.exists(), f"Directory {dir_name} should exist"
            assert dir_path.is_dir(), f"{dir_name} should be a directory"

    def test_ui_subdirectories_exist(self):
        """Verify UI module subdirectories exist."""
        ui_subdirs = ["screens", "widgets", "styles"]

        for subdir in ui_subdirs:
            dir_path = CC_FLOW_ROOT / "ui" / subdir
            assert dir_path.exists(), f"UI subdirectory {subdir} should exist"
            assert dir_path.is_dir(), f"ui/{subdir} should be a directory"

    def test_tests_subdirectories_exist(self):
        """Verify test directory structure exists."""
        test_subdirs = [
            "unit",
            "unit/test_exchanges",
            "unit/test_data_sources",
            "integration",
            "fixtures",
        ]

        for subdir in test_subdirs:
            dir_path = CC_FLOW_ROOT / "tests" / subdir
            assert dir_path.exists(), f"Test subdirectory {subdir} should exist"
            assert dir_path.is_dir(), f"tests/{subdir} should be a directory"

    def test_init_files_exist(self):
        """Verify all required __init__.py files exist."""
        init_files = [
            "__init__.py",
            "core/__init__.py",
            "domain/__init__.py",
            "exchanges/__init__.py",
            "data_sources/__init__.py",
            "ui/__init__.py",
            "ui/screens/__init__.py",
            "ui/widgets/__init__.py",
            "ui/styles/__init__.py",
            "utils/__init__.py",
            "config/__init__.py",
            "tests/__init__.py",
            "tests/unit/__init__.py",
            "tests/unit/test_exchanges/__init__.py",
            "tests/unit/test_data_sources/__init__.py",
            "tests/integration/__init__.py",
            "tests/fixtures/__init__.py",
        ]

        for init_file in init_files:
            file_path = CC_FLOW_ROOT / init_file
            assert file_path.exists(), f"File {init_file} should exist"
            assert file_path.is_file(), f"{init_file} should be a file"

    def test_pyproject_toml_exists(self):
        """Verify pyproject.toml exists in cc-flow root."""
        pyproject_path = CC_FLOW_ROOT / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml should exist"
        assert pyproject_path.is_file(), "pyproject.toml should be a file"


class TestBasicImports:
    """Test that basic module imports work correctly."""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """Add cc-flow to sys.path for imports."""
        cc_flow_parent = CC_FLOW_ROOT.parent
        if str(cc_flow_parent) not in sys.path:
            sys.path.insert(0, str(cc_flow_parent))

    def test_import_cc_flow(self):
        """Test importing the main cc_flow package."""
        try:
            import cc_flow
            assert cc_flow is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow: {e}")

    def test_import_core(self):
        """Test importing cc_flow.core module."""
        try:
            import cc_flow.core
            assert cc_flow.core is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.core: {e}")

    def test_import_domain(self):
        """Test importing cc_flow.domain module."""
        try:
            import cc_flow.domain
            assert cc_flow.domain is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.domain: {e}")

    def test_import_exchanges(self):
        """Test importing cc_flow.exchanges module."""
        try:
            import cc_flow.exchanges
            assert cc_flow.exchanges is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.exchanges: {e}")

    def test_import_data_sources(self):
        """Test importing cc_flow.data_sources module."""
        try:
            import cc_flow.data_sources
            assert cc_flow.data_sources is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.data_sources: {e}")

    def test_import_ui(self):
        """Test importing cc_flow.ui module."""
        try:
            import cc_flow.ui
            assert cc_flow.ui is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.ui: {e}")

    def test_import_ui_screens(self):
        """Test importing cc_flow.ui.screens module."""
        try:
            import cc_flow.ui.screens
            assert cc_flow.ui.screens is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.ui.screens: {e}")

    def test_import_ui_widgets(self):
        """Test importing cc_flow.ui.widgets module."""
        try:
            import cc_flow.ui.widgets
            assert cc_flow.ui.widgets is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.ui.widgets: {e}")

    def test_import_ui_styles(self):
        """Test importing cc_flow.ui.styles module."""
        try:
            import cc_flow.ui.styles
            assert cc_flow.ui.styles is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.ui.styles: {e}")

    def test_import_utils(self):
        """Test importing cc_flow.utils module."""
        try:
            import cc_flow.utils
            assert cc_flow.utils is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.utils: {e}")

    def test_import_config(self):
        """Test importing cc_flow.config module."""
        try:
            import cc_flow.config
            assert cc_flow.config is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cc_flow.config: {e}")
