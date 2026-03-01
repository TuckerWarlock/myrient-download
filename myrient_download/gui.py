"""Tkinter GUI for Myrient Downloader configuration."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .config import MyrDLConfig, MyrDLDownloaderConfig
from .constants import KNOWN_SYSTEMS

_LOGO = Path(__file__).parent / "logo.png"


class MyrientGUI:
    """Main application window for configuring and launching downloads."""

    def __init__(self, config_path: Path) -> None:
        """Initialize GUI, load config from path."""
        self._config_path = config_path
        self._config = MyrDLConfig.load_config(config_path)

        self._root = tk.Tk()
        self._root.title("Myrient Downloader")
        self._root.resizable(False, False)

        # Window icon (PNG bundled alongside this module)
        if _LOGO.exists():
            try:
                self._icon = tk.PhotoImage(file=_LOGO)
                self._root.wm_iconphoto(True, self._icon)
            except tk.TclError:
                pass

        self._config_path_var = tk.StringVar(value=str(config_path))
        self._download_dir_var = tk.StringVar(value=str(self._config.download_dir))
        self._system_dirs_var = tk.BooleanVar(value=self._config.create_and_use_system_directories)
        self._db_dirs_var = tk.BooleanVar(value=self._config.create_and_use_database_directories)

        dl = self._config.myrient_downloader[0] if self._config.myrient_downloader else MyrDLDownloaderConfig()
        self._db_var = tk.StringVar(value=dl.myrient_path)
        self._verify_zips_var = tk.BooleanVar(value=dl.verify_existing_zips)
        self._system_vars: dict[str, tk.BooleanVar] = {}

        self._build_ui()
        self._populate_from_config(dl)

        # Center window on screen after layout is complete
        self._root.update_idletasks()
        w, h = self._root.winfo_reqwidth(), self._root.winfo_reqheight()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 2
        self._root.geometry(f"+{x}+{y}")

    # ── UI construction ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Build all widgets."""
        root = self._root
        root.columnconfigure(0, weight=1)

        outer = ttk.Frame(root, padding=10)
        outer.grid(sticky="nsew")
        outer.columnconfigure(0, weight=1)
        row = 0

        # Config file path
        ttk.Label(outer, text="Config file:").grid(row=row, column=0, sticky="w", padx=10, pady=4)
        row += 1
        cf = ttk.Frame(outer)
        cf.grid(row=row, column=0, sticky="ew", padx=10)
        cf.columnconfigure(0, weight=1)
        ttk.Entry(cf, textvariable=self._config_path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(cf, text="Browse…", command=self._browse_config).grid(row=0, column=1, padx=(4, 0))
        row += 1

        ttk.Separator(outer, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=6, padx=10)
        row += 1

        # Download directory
        ttk.Label(outer, text="Download directory:").grid(row=row, column=0, sticky="w", padx=10, pady=4)
        row += 1
        dd = ttk.Frame(outer)
        dd.grid(row=row, column=0, sticky="ew", padx=10)
        dd.columnconfigure(0, weight=1)
        ttk.Entry(dd, textvariable=self._download_dir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(dd, text="Browse…", command=self._browse_download_dir).grid(row=0, column=1, padx=(4, 0))
        row += 1

        ttk.Checkbutton(outer, text="Create system sub-directories", variable=self._system_dirs_var).grid(
            row=row, column=0, sticky="w", padx=10, pady=4
        )
        row += 1
        ttk.Checkbutton(outer, text="Create database sub-directories", variable=self._db_dirs_var).grid(
            row=row, column=0, sticky="w", padx=10, pady=4
        )
        row += 1

        ttk.Separator(outer, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=6, padx=10)
        row += 1

        ttk.Label(outer, text="Downloader Settings", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=4
        )
        row += 1

        db_row = ttk.Frame(outer)
        db_row.grid(row=row, column=0, sticky="w", padx=10, pady=2)
        ttk.Label(db_row, text="Database:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        db_combo = ttk.Combobox(
            db_row,
            textvariable=self._db_var,
            values=list(KNOWN_SYSTEMS.keys()),
            state="readonly",
            width=14,
        )
        db_combo.grid(row=0, column=1)
        db_combo.bind("<<ComboboxSelected>>", self._on_database_changed)
        row += 1

        ttk.Label(outer, text="Systems (check to include):").grid(row=row, column=0, sticky="w", padx=10, pady=4)
        row += 1
        self._systems_frame = ttk.LabelFrame(outer, text="", padding=6)
        self._systems_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
        self._systems_frame.columnconfigure((0, 1), weight=1)
        self._build_system_checkboxes()
        row += 1

        ttk.Label(outer, text="Game Allow List (one per line — blank = allow all):").grid(
            row=row, column=0, sticky="w", padx=10, pady=4
        )
        row += 1
        self._allow_text = scrolledtext.ScrolledText(outer, height=4, width=55)
        self._allow_text.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
        row += 1

        ttk.Label(outer, text="Game Disallow List (one per line):").grid(row=row, column=0, sticky="w", padx=10, pady=4)
        row += 1
        self._disallow_text = scrolledtext.ScrolledText(outer, height=4, width=55)
        self._disallow_text.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
        row += 1

        ttk.Checkbutton(outer, text="Verify existing ZIPs before skipping", variable=self._verify_zips_var).grid(
            row=row, column=0, sticky="w", padx=10, pady=4
        )
        row += 1

        ttk.Separator(outer, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=8, padx=10)
        row += 1

        btn = ttk.Frame(outer)
        btn.grid(row=row, column=0, sticky="e", padx=10, pady=(0, 12))
        ttk.Button(btn, text="Save Config", command=self._save_config).grid(row=0, column=0, padx=(0, 6))

    def _build_system_checkboxes(self) -> None:
        """Rebuild the systems checklist from the current database selection."""
        for widget in self._systems_frame.winfo_children():
            widget.destroy()
        self._system_vars.clear()

        db = self._db_var.get()
        systems = KNOWN_SYSTEMS.get(db, [])

        for i, system in enumerate(systems):
            var = tk.BooleanVar(value=False)
            self._system_vars[system] = var
            label = system.split(" - ", 1)[-1] if " - " in system else system
            ttk.Checkbutton(self._systems_frame, text=label, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", padx=4
            )

    def _populate_from_config(self, dl: MyrDLDownloaderConfig) -> None:
        """Set widget states from the loaded config."""
        self._allow_text.delete("1.0", tk.END)
        self._allow_text.insert(tk.END, "\n".join(dl.game_allow_list))
        self._disallow_text.delete("1.0", tk.END)
        self._disallow_text.insert(tk.END, "\n".join(dl.game_disallow_list))
        for system, var in self._system_vars.items():
            var.set(system in dl.systems)

    # ── Event handlers ─────────────────────────────────────────────────

    def _on_database_changed(self, _event: object) -> None:
        """Rebuild the systems checklist when the database dropdown changes."""
        self._build_system_checkboxes()

    def _browse_config(self) -> None:
        """Open a save-as dialog to choose the config file path."""
        path = filedialog.asksaveasfilename(
            defaultextension=".toml",
            filetypes=[("TOML files", "*.toml"), ("All files", "*")],
            initialfile=Path(self._config_path_var.get()).name,
        )
        if path:
            self._config_path_var.set(path)

    def _browse_download_dir(self) -> None:
        """Open a directory chooser for the download destination."""
        path = filedialog.askdirectory(initialdir=self._download_dir_var.get())
        if path:
            self._download_dir_var.set(path)

    # ── Config read/write ──────────────────────────────────────────────

    def _read_form(self) -> MyrDLConfig:
        """Build a MyrDLConfig from the current form state."""
        selected = [s for s, v in self._system_vars.items() if v.get()]

        allow_raw = self._allow_text.get("1.0", tk.END).strip()
        disallow_raw = self._disallow_text.get("1.0", tk.END).strip()
        allow_list = [ln.strip() for ln in allow_raw.splitlines() if ln.strip()]
        disallow_list = [ln.strip() for ln in disallow_raw.splitlines() if ln.strip()]

        dl = MyrDLDownloaderConfig(
            myrient_path=self._db_var.get(),
            systems=selected,
            game_allow_list=allow_list,
            game_disallow_list=disallow_list,
            verify_existing_zips=self._verify_zips_var.get(),
        )

        return MyrDLConfig(
            download_dir=Path(self._download_dir_var.get()),
            create_and_use_system_directories=self._system_dirs_var.get(),
            create_and_use_database_directories=self._db_dirs_var.get(),
            myrient_downloader=[dl],
        )

    def _save_config(self) -> None:
        """Validate the form, write the config file, and close the window."""
        try:
            config = self._read_form()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Validation Error", str(exc))
            return
        config_path = Path(self._config_path_var.get())
        config.write_config(config_path)
        cmd = f"uv run myrient-download --config {config_path}"
        msg = f"Configuration saved to {config_path}\n\nTo start downloading, run:\n{cmd}"
        messagebox.showinfo("Config Saved", msg)
        self._root.quit()

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self._root.mainloop()


def launch_gui(config_path: Path | None = None) -> None:
    """Entry point to launch the GUI."""
    resolved = (config_path or Path("config.toml")).expanduser().resolve()
    MyrientGUI(resolved).run()
