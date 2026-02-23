"""GUI tests — require a display. Excluded from default CI run.

Run manually: uv run pytest tests/test_gui.py -v
"""

from pathlib import Path

import pytest

from myrient_download.config import MyrDLConfig
from myrient_download.gui import MyrientGUI


@pytest.fixture
def gui(tmp_path: Path):
    """Create a MyrientGUI instance with a non-existent config (uses defaults)."""
    config_path = tmp_path / "config.toml"
    app = MyrientGUI(config_path)
    yield app
    app._root.destroy()


def test_gui_loads_defaults(gui: MyrientGUI) -> None:
    """GUI initializes without error and download_dir is set."""
    assert gui._download_dir_var.get() != ""
    assert isinstance(gui._system_dirs_var.get(), bool)


def test_gui_read_form_returns_config(gui: MyrientGUI) -> None:
    """_read_form() returns a valid MyrDLConfig."""
    config = gui._read_form()
    assert isinstance(config, MyrDLConfig)


def test_gui_save_config_creates_file(gui: MyrientGUI, tmp_path: Path) -> None:
    """Save config writes a TOML file."""
    config_path = tmp_path / "out.toml"
    gui._config_path_var.set(str(config_path))
    # Patch messagebox so the test doesn't block on a dialog
    import unittest.mock as mock
    with mock.patch("myrient_download.gui.messagebox.showinfo"):
        gui._save_config()
    assert config_path.exists()


def test_gui_system_vars_populated(gui: MyrientGUI) -> None:
    """System checkboxes are created after build."""
    assert isinstance(gui._system_vars, dict)
    assert len(gui._system_vars) > 0


def test_gui_database_change_rebuilds_checkboxes(gui: MyrientGUI) -> None:
    """Changing the database dropdown rebuilds the system checklist."""
    gui._db_var.set("Redump")
    gui._on_database_changed(None)
    redump_count = len(gui._system_vars)
    gui._db_var.set("No-Intro")
    gui._on_database_changed(None)
    no_intro_count = len(gui._system_vars)
    # Both databases have systems, and they have different counts
    assert redump_count > 0
    assert no_intro_count > 0
    assert redump_count != no_intro_count
