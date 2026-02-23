"""File wrangling for Myrient."""

from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

from .constants import HTTP_HEADERS, REQUESTS_TIMEOUT
from .logger import get_logger

logger = get_logger(__name__)


async def get_files_list(session: aiohttp.ClientSession, url: str) -> list[str]:
    """Get the list of files from the Myrient website."""
    logger.info("Getting file list from: %s", url)
    files = []
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
            for link in table.find_all("a"):
                href = link.get("title")
                if isinstance(href, str) and href.endswith(".zip"):
                    files.append(href)

    except Exception:
        logger.exception("Error getting file list")

    logger.trace("Files found: %s", files)
    logger.debug("Found %d files", len(files))

    return files
