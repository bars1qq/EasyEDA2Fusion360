"""EasyEDA -> KiCad: a small GUI that converts components from a link."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

BASE = Path(__file__).resolve().parent
VENDOR = BASE / "vendor"
if VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

import core  # noqa: E402

APP_TITLE = "EasyEDA → KiCad"
WIN_W, WIN_H = 760, 620
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "EasyEDA2KiCad"
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_OUT = Path.home() / "Documents" / "EasyEDA2KiCad"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(data: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def open_folder(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.cfg = load_config()

        self.title(APP_TITLE)
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(680, 540)
        self.configure(bg="#f4f5f7")
        self._set_icon()

        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.last_dir: str | None = None
        self.busy = False

        self._init_style()
        self._build_ui()
        self._center_window()
        self._prefill_from_clipboard()
        self.after(80, self._poll_queue)

    def _set_icon(self) -> None:
        candidates = [
            BASE / "icon.ico",
            Path(getattr(sys, "_MEIPASS", str(BASE))) / "icon.ico",
        ]
        for icon in candidates:
            if icon.is_file():
                try:
                    self.iconbitmap(default=str(icon))
                    return
                except tk.TclError:
                    pass

    def _center_window(self) -> None:
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - WIN_W) // 2)
        y = max(0, (self.winfo_screenheight() - WIN_H) // 3)
        self.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

    # ------------------------------------------------------------------ UI
    def _init_style(self) -> None:
        style = ttk.Style(self)
        for theme in ("vista", "winnative", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("TFrame", background="#f4f5f7")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4f5f7", font=("Segoe UI", 10))
        style.configure(
            "Title.TLabel",
            background="#f4f5f7",
            font=("Segoe UI Semibold", 20),
            foreground="#111827",
        )
        style.configure(
            "Sub.TLabel",
            background="#f4f5f7",
            font=("Segoe UI", 10),
            foreground="#6b7280",
        )
        style.configure("Card.TLabel", background="#ffffff", font=("Segoe UI", 9))
        style.configure("TCheckbutton", background="#f4f5f7", font=("Segoe UI", 10))
        style.configure("TEntry", padding=6)
        style.configure("Status.TLabel", background="#f4f5f7", font=("Segoe UI", 9))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=(20, 16, 20, 12))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Paste a link to get a KiCad symbol, footprint and STEP model.",
            style="Sub.TLabel",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        # --- link
        ttk.Label(outer, text="Component link", style="TLabel").pack(anchor="w")
        link_row = ttk.Frame(outer)
        link_row.pack(fill="x", pady=(4, 12))
        self.url_var = tk.StringVar(value=self.cfg.get("last_link", ""))
        self.url_entry = ttk.Entry(link_row, textvariable=self.url_var, font=("Consolas", 10))
        self.url_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(link_row, text="Paste", command=self._paste).pack(side="left", padx=(8, 0))

        # --- output
        ttk.Label(outer, text="Save to", style="TLabel").pack(anchor="w")
        out_row = ttk.Frame(outer)
        out_row.pack(fill="x", pady=(4, 12))
        self.out_var = tk.StringVar(value=self.cfg.get("out_dir") or str(DEFAULT_OUT))
        ttk.Entry(out_row, textvariable=self.out_var, font=("Segoe UI", 9)).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(out_row, text="Browse…", command=self._choose_dir).pack(
            side="left", padx=(8, 0)
        )

        # --- options
        opts = ttk.Frame(outer)
        opts.pack(fill="x", pady=(0, 12))
        self.want_symbol = tk.BooleanVar(value=self.cfg.get("want_symbol", True))
        self.want_footprint = tk.BooleanVar(value=self.cfg.get("want_footprint", True))
        self.want_3d = tk.BooleanVar(value=self.cfg.get("want_3d", True))
        ttk.Checkbutton(opts, text="Symbol", variable=self.want_symbol).pack(side="left")
        ttk.Checkbutton(opts, text="Footprint", variable=self.want_footprint).pack(
            side="left", padx=(16, 0)
        )
        ttk.Checkbutton(opts, text="3D model (STEP + WRL)", variable=self.want_3d).pack(
            side="left", padx=(16, 0)
        )

        # --- action
        self.convert_btn = tk.Button(
            outer,
            text="Convert",
            command=self._start,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            font=("Segoe UI Semibold", 11),
            cursor="hand2",
            pady=9,
        )
        self.convert_btn.pack(fill="x", pady=(0, 14))

        # --- log
        log_frame = tk.Frame(outer, bg="#0f172a", highlightthickness=0)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(
            log_frame,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            padx=12,
            pady=10,
            height=8,
            width=20,
            state="disabled",
        )
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.log.tag_configure("ok", foreground="#4ade80")
        self.log.tag_configure("warn", foreground="#fbbf24")
        self.log.tag_configure("err", foreground="#f87171")
        self.log.tag_configure("dim", foreground="#94a3b8")

        # --- footer
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(10, 0))
        self.open_btn = ttk.Button(
            footer, text="Open folder", command=self._open_last, state="disabled"
        )
        self.open_btn.pack(side="left")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").pack(
            side="right"
        )

        self.url_entry.bind("<Return>", lambda _e: self._start())

    # --------------------------------------------------------------- helpers
    def _paste(self) -> None:
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return
        if text:
            self.url_var.set(text)

    def _prefill_from_clipboard(self) -> None:
        if self.url_var.get().strip():
            return
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return
        if core.UUID_RE.search(text):
            self.url_var.set(text)

    def _choose_dir(self) -> None:
        chosen = filedialog.askdirectory(
            title="Choose output folder", initialdir=self.out_var.get() or str(Path.home())
        )
        if chosen:
            self.out_var.set(chosen)

    def _open_last(self) -> None:
        if self.last_dir and Path(self.last_dir).is_dir():
            open_folder(self.last_dir)

    def _log(self, message: str, tag: str | None = None) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log_clear(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ---------------------------------------------------------------- actions
    def _start(self) -> None:
        if self.busy:
            return
        link = self.url_var.get().strip()
        try:
            core.parse_uuid(link)
        except core.ConversionError as exc:
            messagebox.showwarning(APP_TITLE, str(exc), parent=self)
            return
        if not (self.want_symbol.get() or self.want_footprint.get() or self.want_3d.get()):
            messagebox.showwarning(
                APP_TITLE, "Select at least one file type.", parent=self
            )
            return

        out_dir = self.out_var.get().strip() or str(DEFAULT_OUT)
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                APP_TITLE, f"Could not create folder:\n{exc}", parent=self
            )
            return

        self.cfg.update(
            {
                "last_link": link,
                "out_dir": out_dir,
                "want_symbol": self.want_symbol.get(),
                "want_footprint": self.want_footprint.get(),
                "want_3d": self.want_3d.get(),
            }
        )
        save_config(self.cfg)

        self.busy = True
        self.convert_btn.configure(state="disabled", bg="#93c5fd", cursor="watch")
        self.open_btn.configure(state="disabled")
        self.status_var.set("Converting…")
        self._log_clear()
        self._log(link, "dim")

        threading.Thread(
            target=self._worker,
            args=(
                link,
                out_dir,
                self.want_symbol.get(),
                self.want_footprint.get(),
                self.want_3d.get(),
            ),
            daemon=True,
        ).start()

    def _worker(self, link: str, out_dir: str, sym: bool, fp: bool, d3: bool) -> None:
        try:
            info = core.convert(
                link,
                out_dir,
                want_symbol=sym,
                want_footprint=fp,
                want_3d=d3,
                log=lambda m: self.queue.put(("log", m)),
            )
            self.queue.put(("done", info))
        except core.ConversionError as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001
            self.queue.put(("error", f"Unexpected error: {exc}"))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self._log(str(payload))
                elif kind == "done":
                    self._finish(payload)  # type: ignore[arg-type]
                elif kind == "error":
                    self._fail(str(payload))
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    def _finish(self, info: dict) -> None:
        self.busy = False
        self.convert_btn.configure(state="normal", bg="#2563eb", cursor="hand2")
        self.last_dir = info.get("dir")
        self.open_btn.configure(state="normal" if self.last_dir else "disabled")
        self.status_var.set(f"Done: {info.get('title', '')}")

        for warning in info.get("warnings") or []:
            self._log("! " + warning, "warn")

        produced = []
        if info.get("symbol"):
            produced.append("symbol")
        if info.get("footprint"):
            produced.append("footprint")
        if info.get("step"):
            produced.append("STEP")
        if info.get("wrl"):
            produced.append("WRL")
        self._log("Files: " + ", ".join(produced), "ok")
        self._log("Folder: " + str(info.get("dir")), "dim")

    def _fail(self, message: str) -> None:
        self.busy = False
        self.convert_btn.configure(state="normal", bg="#2563eb", cursor="hand2")
        self.status_var.set("Error")
        self._log("Error: " + message, "err")
        messagebox.showerror(APP_TITLE, message, parent=self)


def run_cli(argv: list[str]) -> int:
    """Hidden CLI mode used for automated checks: --convert URL --out DIR."""
    link = None
    out = None
    sym = fp = d3 = True
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--convert" and i + 1 < len(argv):
            link = argv[i + 1]
            i += 2
        elif arg == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
        elif arg == "--no-symbol":
            sym = False
            i += 1
        elif arg == "--no-footprint":
            fp = False
            i += 1
        elif arg == "--no-3d":
            d3 = False
            i += 1
        else:
            i += 1
    if not link:
        return 2
    out = out or str(DEFAULT_OUT)
    log_path = Path(out) / "convert.log"
    lines: list[str] = []

    def log(message: str) -> None:
        lines.append(message)

    try:
        info = core.convert(
            link, out, want_symbol=sym, want_footprint=fp, want_3d=d3, log=log
        )
    except Exception as exc:  # noqa: BLE001
        lines.append(f"ERROR: {exc}")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines), encoding="utf-8-sig")
        return 1
    lines.append(json.dumps(info, ensure_ascii=False, indent=2))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return 0


def main() -> int:
    if "--convert" in sys.argv:
        return run_cli(sys.argv[1:])
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
