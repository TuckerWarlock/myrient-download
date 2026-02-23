import argparse
import asyncio
import shutil
from pathlib import Path

import pytest

from myrient_download.config import MyrDLConfig

TEST_CONFIGS_LOCATION = Path.cwd() / "tests" / "configs"


def pytest_configure():
    """Magic function to set module level variables."""
    pytest.TEST_CONFIGS_LOCATION = TEST_CONFIGS_LOCATION


@pytest.fixture
def myr_default_config(tmp_path, no_sleep) -> MyrDLConfig:
    """Fixture for a default MyrDLConfig."""
    return MyrDLConfig()


@pytest.fixture
def no_sleep(monkeypatch):
    """Fixture to disable sleep."""

    async def _no_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


@pytest.fixture
def place_test_config():
    """Fixture that places a config in the tmp_path."""

    def _place_test_config(config_name, path):
        filepath = Path(pytest.TEST_CONFIGS_LOCATION) / config_name
        shutil.copyfile(filepath, Path(path) / "config.toml")

    return _place_test_config


@pytest.fixture
def no_argparse(monkeypatch, tmp_path):
    """Fixture to disable argparse."""
    config_path = tmp_path / "config.toml"
    mock_args = argparse.Namespace(log_level="INFO", config=config_path, directory=tmp_path, gui=False)
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)
