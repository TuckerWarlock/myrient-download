# Copilot Instructions for myrient-download

## Build, Test, and Lint Commands

**Install dependencies:**
```bash
uv sync
```

**Run all tests:**
```bash
uv run pytest -q
```

**Run a specific test:**
```bash
uv run pytest tests/test_download.py::test_function_name -v
```

**GUI tests (requires display):**
```bash
uv run pytest tests/test_gui.py -v
```

**Run full code checks locally (same as CI):**
```bash
./scripts/run_ci_local.sh
```

**Linting:**
- **Ruff (primary):** `uv run ruff check myrient_download/ tests/` (also used for formatting)
- **Flake8 (backup):** `uv run flake8 myrient_download/ tests/`
- **Mypy (type checking):** `uv run mypy myrient_download/`

**Code formatting:** `uv run ruff format myrient_download/ tests/`

## High-Level Architecture

**Core Components:**

1. **Config System** (`config.py`):
   - Uses Pydantic BaseSettings for TOML file loading
   - `MyrDLDownloaderConfig`: Per-downloader settings (system list, allow/disallow filters)
   - `MyrDLConfig`: Global settings (download directory, create structure options)
   - Validates config and creates backups when auto-modified

2. **Download Pipeline** (`download.py`):
   - Async-first design with 3 concurrent worker threads
   - `MyrDownloader`: Main orchestrator class
   - Flow: Fetch file lists from Myrient → queue download tasks → workers process downloads
   - Uses `aiohttp.ClientSession` for HTTP operations
   - Supports retry logic (3 attempts) with 5-second delays on connection errors
   - Optional ZIP verification with automatic corrupt file removal

3. **File Management** (`files.py`):
   - `get_files_list()`: Scrapes Myrient HTML to extract system/game lists
   - `filter_games()`: Applies allow/disallow list filters
   - Handles safe partial downloads (.part files renamed on success)

4. **GUI** (`gui.py`):
   - PySimpleGUI desktop window for interactive config creation
   - Grouped system checklist (No-Intro vs Redump databases)
   - Real-time filter validation

5. **Utilities:**
   - `logger.py`: Colored logging with custom TRACE level and rotating file logs
   - `constants.py`: HTTP headers, retry timeouts, tqdm styling
   - `helpers.py`: Helper functions (e.g., animated wait dots)

**Data Flow:**
```
CLI args → Load TOML config → GUI (optional) → Download pipeline → 
  Fetch file lists → Filter games → Queue tasks → Worker pool → 
  Download & verify ZIPs → Output directory structure
```

## Key Conventions

**Async/Concurrency:**
- All I/O operations use `async`/`await`
- Entry point (`__main__.py`) uses uvloop when available for performance, falls back to asyncio
- Worker pool pattern: 3 concurrent tasks via `asyncio.Queue`, not thread pool
- CPU-bound operations (ZIP verification) delegated to executor pool: `asyncio.get_event_loop().run_in_executor()`

**Validation & Type Safety:**
- All public models inherit from Pydantic `BaseModel` or `BaseSettings`
- Strict mypy mode enabled (`strict = true` in pyproject.toml)
- Use `model_validator` decorator for cross-field validation
- Explicit type hints required everywhere (strict mode enforced in CI)

**Error Handling:**
- Connection errors trigger automatic retry (max 3 attempts with 5-second backoff)
- Corrupt ZIPs logged as warnings, automatically removed, then re-queued for download
- Configuration mismatches create `.bak` backup of original file before auto-fix

**Code Style:**
- Ruff is primary linter + formatter (overrides flake8 for consistency)
- Line length: 120 characters
- Google-style docstrings (enforced by Pydantic config)
- Import sorting via ruff (`extend-fixable = ["B", "I001"]`)
- Per-file ignores for tests: ARG, FBT, ANN, D (argument names, type hints, docstrings)
- Test files exempt from many linting rules (see pyproject.toml `[tool.ruff.lint.per-file-ignores]`)

**Logging:**
- Use `get_logger(__name__)` in every module
- Available levels: TRACE (custom), DEBUG, INFO, WARNING, ERROR
- TRACE level for detailed async operation tracking
- Log files rotate and are saved alongside terminal output

**Configuration Patterns:**
- `myrient_path`: "No-Intro" or "Redump" (database selection)
- `systems`: List of exact system names from Myrient (must match precisely)
- Filters: `allow_list` (include only matches) takes precedence; `disallow_list` (exclude matches) as backup
- `create_and_use_system_directories`: Organize downloads into per-system folders
- `verify_existing_zips`: Expensive check; only enable if needed

**Testing:**
- Config: `pytest.ini_options` enables coverage (HTML report in `htmlcov/`)
- `pytest-random-order` randomizes test order to detect ordering dependencies
- `detect-test-pollution` flag to catch state leaks between tests
- GUI tests excluded from default run (require display; run manually if needed)
