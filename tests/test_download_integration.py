"""Integration tests for downloading actual ROMs from Myrient."""

import pytest

from myrient_download.config import MyrDLConfig, MyrDLDownloaderConfig
from myrient_download.download import MyrDownloader


@pytest.mark.asyncio
@pytest.mark.slow
class TestDownloadIntegration:
    """Integration tests that download actual files from Myrient."""

    async def test_download_single_file_from_each_system(self, tmp_path):
        """Test downloading one small ROM from each available system (integration test).

        This test downloads a real file from Myrient for each system to verify:
        - Network connectivity to Myrient
        - File filtering and download pipeline works end-to-end
        - Timeout and retry logic works with real network conditions
        """
        # Create a downloader config that targets one file per system
        systems_to_test = [
            # No-Intro systems - pick small/common games
            "Nintendo - Game Boy",
            "Atari - 2600",
        ]

        for system in systems_to_test:
            downloader_config = MyrDLDownloaderConfig(
                myrient_path="No-Intro",
                systems=[system],
                game_allow_list=["(USA)"],
                game_disallow_list=["Demo", "BIOS", "Proto", "Beta", "Program"],
                download_timeout_seconds=600,
            )

            config = MyrDLConfig(
                download_dir=tmp_path,
                create_and_use_system_directories=True,
                myrient_downloader=[downloader_config],
            )

            downloader = MyrDownloader(config)
            await downloader.download_from_system_list()

            # Verify at least one file was downloaded or skipped (not just errors)
            stats = downloader.stats
            total_processed = stats.downloaded + stats.skipped
            assert total_processed > 0, f"No files processed for {system}"

    async def test_download_respects_allow_list(self, tmp_path):
        """Test that allow list filtering works during download."""
        downloader_config = MyrDLDownloaderConfig(
            myrient_path="No-Intro",
            systems=["Nintendo - Game Boy"],
            game_allow_list=["(USA)", "(World)"],
            game_disallow_list=["Demo", "BIOS"],
            download_timeout_seconds=600,
        )

        config = MyrDLConfig(
            download_dir=tmp_path,
            create_and_use_system_directories=True,
            myrient_downloader=[downloader_config],
        )

        downloader = MyrDownloader(config)
        await downloader.download_from_system_list()

        # If any files were downloaded, they should match the allow list
        if downloader.stats.downloaded > 0:
            for file in tmp_path.rglob("*.zip"):
                allow_terms = ["(USA)", "(World)"]
                assert any(term in file.name for term in allow_terms), (
                    f"File {file.name} doesn't match allow list"
                )

    async def test_download_respects_disallow_list(self, tmp_path):
        """Test that disallow list filtering works during download."""
        downloader_config = MyrDLDownloaderConfig(
            myrient_path="No-Intro",
            systems=["Atari - 2600"],
            game_allow_list=[],
            game_disallow_list=["BIOS", "Demo"],
            download_timeout_seconds=600,
        )

        config = MyrDLConfig(
            download_dir=tmp_path,
            create_and_use_system_directories=True,
            myrient_downloader=[downloader_config],
        )

        downloader = MyrDownloader(config)
        await downloader.download_from_system_list()

        # If any files were downloaded, they should not match the disallow list
        if downloader.stats.downloaded > 0:
            for file in tmp_path.rglob("*.zip"):
                disallow_terms = ["BIOS", "Demo"]
                assert not any(term in file.name for term in disallow_terms), (
                    f"File {file.name} matches disallow list"
                )
