"""Helper functions for the myrientdownload package."""

import time


def wait_with_dots(seconds: int) -> None:
    """Wait for a specified number of seconds, printing dots to indicate progress."""
    for _ in range(seconds):
        print(".", end="", flush=True)  # noqa: T201
        time.sleep(1)
    print()  # Print a newline after the wait is complete  # noqa: T201
