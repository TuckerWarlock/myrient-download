from myrient_download.__main__ import main


def test_main_no_download(caplog, tmp_path, place_test_config, no_argparse, no_sleep):
    """Test the main function without downloading files."""

    place_test_config("valid_no_systems.toml", tmp_path)

    with caplog.at_level("INFO"):
        main()
