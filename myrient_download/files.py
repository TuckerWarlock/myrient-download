"""File wrangling for Myrient."""

from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

from .constants import HTTP_HEADERS, REQUESTS_TIMEOUT
from .logger import get_logger

logger = get_logger(__name__)


def _parse_size(size_str: str) -> int:
    """Parse a human-readable size string into bytes."""
    units = {
        "B": 1,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
    }
    parts = size_str.split()
    if len(parts) != 2:
        return 0
    try:
        return int(float(parts[0]) * units.get(parts[1], 0))
    except ValueError:
        return 0


async def get_files_list(session: aiohttp.ClientSession, url: str) -> list[tuple[str, int]]:
    """Get the list of files and their sizes from the Myrient website."""
    logger.info("Getting file list from: %s", url)
    files: list[tuple[str, int]] = []
    try:
        encoded_url = quote(url, safe=":/")
        async with session.get(
            encoded_url,
            headers=HTTP_HEADERS,
            timeout=aiohttp.ClientTimeout(total=REQUESTS_TIMEOUT),
        ) as response:
            response.raise_for_status()
            text = await response.text()

        soup = BeautifulSoup(text, "html.parser")
        table = soup.find("table", id="list")
        if table:
            for row in table.find_all("tr"):
                link = row.find("a")
                if link is None:
                    continue
                href = link.get("title")
                if not isinstance(href, str) or not href.endswith(".zip"):
                    continue
                size_cell = row.find("td", class_="size")
                size_bytes = _parse_size(size_cell.get_text(strip=True)) if size_cell else 0
                files.append((href, size_bytes))

    except Exception:
        logger.exception("Error getting file list")

    logger.trace("Files found: %s", files)
    logger.debug("Found %d files", len(files))

    return files
