"""Download management for Myrinet files."""

import asyncio
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self
from urllib.parse import quote

import aiohttp
from colorama import Fore, Style, init
from pydantic import BaseModel, Field, model_validator
from tqdm import tqdm

from .config import MyrDLConfig, MyrDLDownloaderConfig
from .constants import FUN_TQDM_LOADING_BAR, HTTP_HEADERS, REQUESTS_TIMEOUT, SYSTEM_URL_OVERRIDES, ZIP_VERIFICATION_TIMEOUT
from .logger import get_logger
from .files import get_files_list

logger = get_logger(__name__)

init()

NUM_WORKERS = 1


def _format_bytes(size: int) -> str:
    """Format a byte count into a human-readable string."""
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


@dataclass
class _SystemContext:
    myr_downloader: MyrDLDownloaderConfig
    system: str
    system_url: str


@dataclass
class _DownloadTask:
    file_name: str
    base_url: str
    system: str
    myr_downloader: MyrDLDownloaderConfig
    myrient_path: str


@dataclass
class DownloadStats:
    """Tracks and reports download statistics."""

    skipped: int = 0
    downloaded: int = 0
    failed: int = 0
    skip_streak: int = field(default=0, repr=False)

    def report_skipped(self) -> None:
        """Increment the skipped counter."""
        self.skipped += 1
        self.skip_streak += 1
        logger.debug("Status: skipped")

    def report_downloaded(self) -> None:
        """Increment the downloaded counter."""
        self.downloaded += 1
        logger.debug("Status: downloaded")

    def report_failed(self) -> None:
        """Increment the failed counter."""
        self.failed += 1
        logger.debug("Status: failed")

    def reset_skipped_streak(self) -> None:
        """Log and reset the skipped streak counter."""
        if self.skip_streak > 0:
            logger.info("Skipped %d existing files", self.skip_streak)
            self.skip_streak = 0

    def print_stats(self) -> None:
        """Print the download statistics."""
        msg = "\nDownload statistics:"
        for stat in ("skipped", "downloaded", "failed"):
            msg += f"\n  {stat.capitalize()}: {getattr(self, stat)}"
        logger.info(msg)


class MyrDownloader(BaseModel):
    """Class to manage downloading files from Myrinet."""

    config: MyrDLConfig = Field(default_factory=MyrDLConfig)
    stats: DownloadStats = Field(default_factory=DownloadStats)

    def __init__(self, config: MyrDLConfig) -> None:
        """Initialize the downloader with the given configuration."""
        super().__init__(config=config, stats=DownloadStats())

    @model_validator(mode="after")
    def _validate_config(self) -> Self:
        """Validate the configuration after initialization."""
        if not isinstance(self.config, MyrDLConfig):
            msg = "Invalid configuration object. Expected MyrDLConfig."
            raise TypeError(msg)

        return self

    # region Download methods

    async def download_from_system_list(self) -> None:
        """Download files from the list of systems in the configuration."""
        logger.info("Starting download from Myrient...")

        async with aiohttp.ClientSession() as session:
            system_contexts, all_file_lists = await self._fetch_file_lists(session)
            await self._download_files(session, system_contexts, all_file_lists)

        self.stats.print_stats()
        logger.info("Download complete!")

    async def _fetch_file_lists(
        self, session: aiohttp.ClientSession
    ) -> tuple[list[_SystemContext], list[list[tuple[str, int]]]]:
        """Fetch file lists for all systems concurrently."""
        fetch_tasks = []
        system_contexts: list[_SystemContext] = []

        for myr_downloader in self.config.myrient_downloader:
            for system in myr_downloader.systems:
                url_system = SYSTEM_URL_OVERRIDES.get(myr_downloader.myrient_path, {}).get(system, system)
                system_url = f"{myr_downloader.myrient_url}/{myr_downloader.myrient_path}/{url_system}/"
                fetch_tasks.append(get_files_list(session, system_url))
                system_contexts.append(
                    _SystemContext(myr_downloader=myr_downloader, system=system, system_url=system_url)
                )

        all_file_lists: list[list[tuple[str, int]]] = list(await asyncio.gather(*fetch_tasks))
        return system_contexts, all_file_lists

    async def _download_files(
        self,
        session: aiohttp.ClientSession,
        system_contexts: list[_SystemContext],
        all_file_lists: list[list[tuple[str, int]]],
    ) -> None:
        """Build the download queue and drain it with workers."""
        # Clean up leftover .part files before starting workers
        seen_dirs: set[Path] = set()
        for ctx in system_contexts:
            d = self._get_download_dir(system=ctx.system, myrient_path=ctx.myr_downloader.myrient_path)
            if d not in seen_dirs:
                seen_dirs.add(d)
                for part_file in d.glob("*.part"):
                    logger.warning("Deleting incomplete file: %s", part_file)
                    part_file.unlink()

        queue: asyncio.Queue[_DownloadTask | None] = asyncio.Queue()

        total_size = 0
        for ctx, files_list in zip(system_contexts, all_file_lists, strict=True):
            if ctx.myr_downloader.game_allow_list == []:
                ctx.myr_downloader.game_allow_list = ["."]
            filtered_files = [
                (name, size)
                for name, size in files_list
                if any(term in name for term in ctx.myr_downloader.game_allow_list)
                and not any(term in name for term in ctx.myr_downloader.game_disallow_list)
            ]

            if filtered_files:
                system_size = sum(size for _, size in filtered_files)
                total_size += system_size
                logger.info(
                    "Found %d matching files for %s (%s)",
                    len(filtered_files),
                    ctx.system,
                    _format_bytes(system_size),
                )
                for file_name, _ in filtered_files:
                    await queue.put(
                        _DownloadTask(
                            file_name=file_name,
                            base_url=ctx.system_url,
                            system=ctx.system,
                            myr_downloader=ctx.myr_downloader,
                            myrient_path=ctx.myr_downloader.myrient_path,
                        )
                    )
            else:
                logger.info("No matching files found for %s", ctx.system)

        if total_size > 0:
            logger.info("Total estimated download size: %s", _format_bytes(total_size))

        workers = [
            asyncio.create_task(self._download_worker(session, queue, worker_id=i)) for i in range(NUM_WORKERS)
        ]
        await queue.join()

        for _ in range(NUM_WORKERS):
            await queue.put(None)
        await asyncio.gather(*workers)

    async def _download_worker(
        self,
        session: aiohttp.ClientSession,
        queue: asyncio.Queue[_DownloadTask | None],
        *,
        worker_id: int,
    ) -> None:
        """Worker coroutine that pulls tasks from the queue and downloads them."""
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                await self._process_download_item(session, item, worker_id=worker_id)
            finally:
                queue.task_done()

    async def _process_download_item(
        self,
        session: aiohttp.ClientSession,
        task: _DownloadTask,
        *,
        worker_id: int,
    ) -> None:
        """Process a single download item: skip check, verify, download with retries."""
        download_dir = self._get_download_dir(system=task.system, myrient_path=task.myrient_path)
        output_file = download_dir / task.file_name

        if task.myr_downloader.verify_existing_zips and output_file.is_file():
            try:
                timeout = self._calculate_verification_timeout(output_file)
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, self._check_zip_file, output_file),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("ZIP verification timeout: %s (removing file)", output_file)
                output_file.unlink()

        if output_file.exists():
            logger.debug("Skipping %s - already exists", task.file_name)
            self.stats.report_skipped()
            return

        self.stats.reset_skipped_streak()

        def magenta_str(s: str) -> str:
            return f"{Fore.MAGENTA}{s}{Style.RESET_ALL}"

        logger.info("%s %s %s", task.system, magenta_str("»"), task.file_name)

        file_url = f"{task.base_url}{task.file_name}"
        logger.debug("Downloading %s to: %s", file_url, output_file)

        for attempt in range(3):
            try:
                download_timeout: float | None = task.myr_downloader.download_timeout_seconds or None
                if await asyncio.wait_for(
                    self._download_file(session, file_url, output_file, task.base_url, worker_id=worker_id),
                    timeout=download_timeout,
                ):
                    self.stats.report_downloaded()
                    break
            except asyncio.TimeoutError:
                logger.warning("Download timeout for %s", task.file_name)
                if output_file.with_suffix(".part").exists():
                    output_file.with_suffix(".part").unlink()
                self.stats.report_failed()
                continue
            if attempt != 2:
                backoff_seconds = 5 * (2 ** attempt)  # 5s, 10s, 20s
                await asyncio.sleep(backoff_seconds)
                logger.warning("Retrying download for %s (waiting %ds)", task.file_name, backoff_seconds)
        else:
            if not output_file.exists():
                logger.warning("NOT downloaded: %s", task.file_name)

        if output_file.exists():
            try:
                timeout = self._calculate_verification_timeout(output_file)
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._check_zip_file(output_file, print_verification=True)
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("ZIP verification timeout: %s (removing file)", output_file)
                output_file.unlink()
                self.stats.report_failed()

    async def _download_file(
        self,
        session: aiohttp.ClientSession,
        url: str,
        destination: Path,
        base_url: str,
        *,
        worker_id: int,
    ) -> bool:
        """Download an individual file."""
        try:
            encoded_url = quote(url, safe=":/")

            headers = HTTP_HEADERS.copy()
            headers["Referer"] = base_url

            async with session.get(
                encoded_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUESTS_TIMEOUT),
            ) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("Content-Length", 0))
                destination_temp = destination.with_suffix(".part")

                with (
                    destination_temp.open("wb") as f,
                    tqdm(
                        total=total_size,
                        unit="iB",
                        unit_scale=True,
                        ascii=FUN_TQDM_LOADING_BAR,
                        leave=False,
                        position=worker_id,
                        desc=destination.name[:30],
                        disable=total_size < 100 * 1024 * 1024,
                    ) as pbar,
                ):
                    async for chunk in response.content.iter_chunked(8192):
                        if chunk:
                            size = f.write(chunk)
                            pbar.update(size)

            destination_temp.rename(destination)

        except (aiohttp.ClientError, aiohttp.ClientPayloadError) as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Connection error: %s", url)
            else:
                error_short = type(e).__name__
                logger.error("%s: %s", error_short, url)  # noqa: TRY400
            self.stats.report_failed()
            return False

        return True

    def _calculate_verification_timeout(self, file_path: Path) -> float:
        """Calculate ZIP verification timeout based on file size.

        Formula: Base 120 seconds + 3 seconds per MB
        Examples: 3.2MB = 129.6s, 100MB = 420s, 500MB = 1620s
        Accounts for slow connections and Myrient rate limiting.
        """
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            return 120 + (file_size_mb * 3)
        except (OSError, ValueError):
            return ZIP_VERIFICATION_TIMEOUT

    def _get_download_dir(self, system: str, myrient_path: str) -> Path:
        """Get the download directory based on the configuration and system."""
        download_dir = self.config.download_dir
        if self.config.create_and_use_system_directories:
            if self.config.create_and_use_database_directories:
                download_dir = self.config.download_dir / myrient_path / system
            else:
                download_dir = self.config.download_dir / system
        if self.config.create_and_use_database_directories and not self.config.create_and_use_system_directories:
            msg = "Cannot create database directories without system directories"
            msg += "\nPlease set create_and_use_system_directories to True"
            raise ValueError(msg)

        download_dir.mkdir(parents=True, exist_ok=True)
        return download_dir

    def _check_zip_file(self, output_file: Path, *, print_verification: bool = False) -> None:
        """Check if the zip file is valid."""
        if output_file.suffix != ".zip":
            logger.info("File is not a zip: %s", output_file)

        if print_verification:
            logger.info("Verifying zip file: %s", output_file)

        try:
            with zipfile.ZipFile(output_file, "r") as zf:
                zf.testzip()  # Test the zip file
        except zipfile.BadZipFile:
            logger.warning("Bad zip file: %s", output_file)
            output_file.unlink()
            self.stats.report_failed()
