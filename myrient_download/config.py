"""Config loading, setup, validating, writing."""

import datetime
import json
from pathlib import Path
from typing import Self

import tomlkit
from colorama import Back, Fore, Style, init
from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import PROGRAM_NAME, URL, __version__
from .helpers import wait_with_dots
from .logger import get_logger

logger = get_logger(__name__)
init(autoreset=True)


class MyrDLDownloaderConfig(BaseModel):
    """Settings for the Myrient downloader."""

    model_config = ConfigDict(extra="ignore")  # This is fine for config

    myrient_url: str = "https://myrient.erista.me/files"
    myrient_path: str = "No-Intro"  # Database name, see the website
    verify_existing_zips: bool = False  # Check existing zips are valid before skipping
    systems: list[str] = [
        "Nintendo - Nintendo Entertainment System (Headered)",
        "Nintendo - Super Nintendo Entertainment System",
    ]
    system_allow_list: list[str] = []
    system_disallow_list: list[str] = []
    game_allow_list: list[str] = ["(USA)"]
    game_disallow_list: list[str] = ["Demo", "BIOS", "(Proto)", "(Beta)", "(Program)"]


class MyrDLConfig(BaseSettings):
    """Settings loaded from a TOML file."""

    model_config = SettingsConfigDict(extra="ignore")  # This is fine for config

    # Default values for our settings
    myrient_downloader: list[MyrDLDownloaderConfig] = [MyrDLDownloaderConfig()]
    download_dir: Path = Path.cwd() / "output"
    create_and_use_system_directories: bool = True  # System name, per the list
    create_and_use_database_directories: bool = False  # No-Intro, Redump, etc.

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        """Validate the settings after initialization."""
        total_systems = [
            system for myrient_downloader in self.myrient_downloader for system in myrient_downloader.systems
        ]

        if not self.create_and_use_system_directories and len(total_systems) > 1:
            msg = "Cannot set 'create_and_use_system_directories' to True when multiple systems are specified."
            raise ValueError(msg)

        return self

    def print_config_overview(self) -> None:
        """Print the configuration overview."""
        print_green = Fore.GREEN + Back.BLACK
        print_red = Fore.RED + Back.BLACK

        def str_magenta(text: Path | str | list[str]) -> str:
            return f"{Fore.MAGENTA}{Back.BLACK}{text}{Style.RESET_ALL}"

        def will_will_not(*, condition: bool, thing: str) -> str:
            if condition:
                return f"{print_green}Will {thing}{Style.RESET_ALL}"
            return f"{print_red}Will NOT {thing}{Style.RESET_ALL}"

        msg = f"""
Global Settings:
  Download Directory: {str_magenta(self.download_dir)}
  {will_will_not(condition=self.create_and_use_system_directories, thing="create system directories")}
  {will_will_not(condition=self.create_and_use_database_directories, thing="create database directories")}
"""

        for n, myr_downloader in enumerate(self.myrient_downloader):
            msg += f"""
Myrient Downloader {n + 1}:
  Resolved Myrinet URL: {str_magenta(f"{myr_downloader.myrient_url}/{str_magenta(myr_downloader.myrient_path)}")}
  {will_will_not(condition=myr_downloader.verify_existing_zips, thing="verify existing zips")}
  Systems:
    {"\n    ".join(myr_downloader.systems)}
  System Allow List: {str_magenta(", ".join(myr_downloader.system_allow_list) if myr_downloader.system_allow_list else "<All>")}
  System Disallow List: {str_magenta(", ".join(myr_downloader.system_disallow_list) if myr_downloader.system_disallow_list else "<None>")}
  Game Allow List: {str_magenta(", ".join(myr_downloader.game_allow_list) if myr_downloader.game_allow_list else "<All>")}
  Game Disallow List: {str_magenta(", ".join(myr_downloader.game_disallow_list) if myr_downloader.game_disallow_list else "<None>")}
"""  # noqa: E501 # Not going to do anything about a `"""`
        logger.info(msg)
        wait_with_dots(5)  # Pause to allow the user to read the config overview

    def write_config(self, config_location: Path) -> None:
        """Write the current settings to a TOML file."""
        config_location.parent.mkdir(parents=True, exist_ok=True)

        config_data = json.loads(self.model_dump_json())  # This is how we make the object safe for tomlkit
        if not config_location.exists():
            logger.warning("Config file does not exist, creating it at %s", config_location)
            config_location.touch()
            existing_data = config_data
        else:
            with config_location.open("r") as f:
                existing_data = tomlkit.load(f)

        logger.info("Writing config to %s", config_location)

        new_file_content_str = f"# Configuration file for {PROGRAM_NAME} v{__version__} {URL}\n"
        new_file_content_str += tomlkit.dumps(config_data)

        if existing_data != config_data:  # The new object will be valid, so we back up the old one
            time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            backup_file = config_location.parent / f"{config_location.stem}_{time_str}{config_location.suffix}.bak"
            logger.warning("Validation has changed the config file, backing up the old one to %s", backup_file)
            with backup_file.open("w") as f:
                f.write(tomlkit.dumps(existing_data))

        with config_location.open("w") as f:
            f.write(new_file_content_str)

    @classmethod
    def load_config(cls, config_path: Path) -> Self:
        """Load the configuration file."""
        if not config_path.exists():
            return cls()

        with config_path.open("r") as f:
            config = tomlkit.load(f)

        return cls(**config)
