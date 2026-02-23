"""Main entry point for CLI."""

import argparse
import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

from . import DESCRIPTION, PROGRAM_NAME, __version__
from .config import MyrDLConfig
from .logger import get_logger, setup_logger
from .download import MyrDownloader

setup_logger()
logger = get_logger(__name__)

try:
    import uvloop as _uvloop

    def _run(coro: Coroutine[Any, Any, None]) -> None:
        """Run coroutine with uvloop."""
        asyncio.set_event_loop_policy(_uvloop.EventLoopPolicy())
        asyncio.run(coro)

except ImportError:
    def _run(coro: Coroutine[Any, Any, None]) -> None:
        """Run coroutine with default asyncio."""
        asyncio.run(coro)


def main() -> None:
    """Main CLI."""
    parser = argparse.ArgumentParser(description="Download files from Myrient.")
    parser.add_argument("--log-level", type=str, default="INFO")
    parser.add_argument("--directory", type=str, default="")
    parser.add_argument(
        "--config",
        type=str,
        default="config.toml",
        help="Path to the configuration file (default: config.toml)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical configuration editor",
    )
    args = parser.parse_args()

    logger.info("%s v%s %s", PROGRAM_NAME, __version__, DESCRIPTION)
    setup_logger(args.log_level)

    config_path = Path(args.config).expanduser().resolve()

    if args.gui:
        from .gui import launch_gui  # noqa: PLC0415
        launch_gui(config_path)
        return

    config = MyrDLConfig.load_config(config_path)
    if args.directory:
        config.download_dir = Path(args.directory)
    config.print_config_overview()
    config.write_config(config_path)

    myr_downloader = MyrDownloader(config)
    _run(myr_downloader.download_from_system_list())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Download interrupted by user.")
