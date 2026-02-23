from myrient_download.download import MyrDownloader


def test_myr_downloader_init(myr_default_config):
    """Test MyrDownloader initialization."""
    MyrDownloader(myr_default_config)
