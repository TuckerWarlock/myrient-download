"""Constants for the Myrient Download Script."""

HTTP_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # noqa: E501 # This line is just long
}

REQUESTS_TIMEOUT = 20  # Yep, it can be slow

FUN_TQDM_LOADING_BAR = " ▖▘▝▗▚▞█"

# Grouped by database for the GUI system picker
KNOWN_SYSTEMS: dict[str, list[str]] = {
    "No-Intro": [
        "Nintendo - Nintendo Entertainment System (Headered)",
        "Nintendo - Super Nintendo Entertainment System",
        "Nintendo - Game Boy",
        "Nintendo - Game Boy Color",
        "Nintendo - Game Boy Advance",
        "Nintendo - Nintendo 64",
        "Nintendo - Nintendo DS",
        "Nintendo - Nintendo DSi",
        "Sega - Master System - Mark III",
        "Sega - Game Gear",
        "Sega - Mega Drive - Genesis",
        "Sega - Saturn",
        "Sony - PlayStation Portable",
        "Atari - 2600",
        "Atari - 7800",
        "NEC - PC Engine - TurboGrafx-16",
        "SNK - Neo Geo Pocket Color",
    ],
    "Redump": [
        "Sony - PlayStation",
        "Sony - PlayStation 2",
        "Sony - PlayStation Portable",
        "Nintendo - GameCube",
        "Nintendo - Wii",
        "Sega - Saturn",
        "Sega - Dreamcast",
        "Microsoft - Xbox",
        "Microsoft - Xbox 360",
    ],
}
