import customtkinter as ctk
from app.constants import (BG, SURFACE, SURFACE2, TEXT, SUBTEXT,
                            MAUVE, LAVENDER, GREEN, RED, OVERLAY, HEADER_BG)


# ── Hotkey recorder helpers ───────────────────────────────────────────────────
def _get_root(widget):
    """Walk up to the Tk root window."""
    w = widget
    while w.master:
        w = w.master
    return w


def _tk_key_to_str(event) -> str | None:
    """Convert a Tkinter KeyPress event to a pynput-friendly key name."""
    MODIFIER_MAP = {
        "Control_L": "ctrl", "Control_R": "ctrl",
        "Shift_L":   "shift", "Shift_R":  "shift",
        "Alt_L":     "alt",   "Alt_R":    "alt",
        "Super_L":   "win",   "Super_R":  "win",
    }
    sym = event.keysym
    if sym in MODIFIER_MAP:
        return MODIFIER_MAP[sym]
    if sym.startswith("F") and sym[1:].isdigit():
        return sym          # F1–F12
    if len(sym) == 1:
        return sym.lower()  # regular character
    return None


def _build_combo(keys: set) -> str:
    """Order: ctrl → shift → alt → regular key."""
    ORDER = ["ctrl", "shift", "alt", "win"]
    mods  = [k for k in ORDER if k in keys]
    rest  = [k for k in keys  if k not in ORDER]
    return "+".join(mods + sorted(rest))


def build(parent: ctk.CTkFrame, app) -> None:
    """Build the Configuration tab contents."""

    # scrollable container so it works at any window height
    scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                     scrollbar_button_color=SURFACE2,
                                     scrollbar_button_hover_color=OVERLAY)
    scroll.pack(fill="both", expand=True, padx=20, pady=12)

    def section_label(text: str) -> None:
        ctk.CTkLabel(scroll, text=text, text_color=MAUVE,
                     font=ctk.CTkFont("Segoe UI", 11, weight="bold"),
                     anchor="w").pack(fill="x", pady=(18, 4))

    def divider() -> None:
        ctk.CTkFrame(scroll, fg_color=SURFACE, height=1,
                     corner_radius=0).pack(fill="x", pady=(4, 0))

    def text_entry(var, show: str = None) -> ctk.CTkEntry:
        e = ctk.CTkEntry(
            scroll, textvariable=var,
            fg_color=SURFACE, border_color=SURFACE2,
            text_color=TEXT, placeholder_text_color=SUBTEXT,
            font=ctk.CTkFont("Segoe UI", 12),
            corner_radius=8, height=38, border_width=1,
        )
        if show:
            e.configure(show=show)
        e.pack(fill="x", pady=(0, 4))
        return e

    def folder_row(var) -> None:
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 4))
        ctk.CTkEntry(
            row, textvariable=var,
            fg_color=SURFACE, border_color=SURFACE2,
            text_color=TEXT,
            font=ctk.CTkFont("Segoe UI", 12),
            corner_radius=8, height=38, border_width=1,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            row, text="Browse", width=80, height=38,
            fg_color=SURFACE2, hover_color="#585b70", text_color=TEXT,
            font=ctk.CTkFont("Segoe UI", 11), corner_radius=8,
            command=lambda: app.browse_folder(var),
        ).pack(side="right")

    # ── API Key ───────────────────────────────────────────────────────────────
    section_label("GEMINI API KEY")
    text_entry(app.api_key_var, show="•")
    ctk.CTkLabel(scroll,
                 text="Used for screenshot classification. Get yours at aistudio.google.com",
                 text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 10),
                 anchor="w").pack(fill="x")

    divider()

    # ── Developer Level ───────────────────────────────────────────────────────
    section_label("DEVELOPER LEVEL")
    ctk.CTkLabel(scroll, text="Sets the performance benchmark used in Gemini prompts.",
                 text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 10),
                 anchor="w").pack(fill="x", pady=(0, 8))

    seg = ctk.CTkSegmentedButton(
        scroll,
        values=["Junior", "Intermediate", "Senior", "Lead"],
        variable=app.level_var,
        fg_color=SURFACE,
        selected_color=MAUVE,
        selected_hover_color="#b09de8",
        unselected_color=SURFACE,
        unselected_hover_color=SURFACE2,
        text_color=TEXT,
        font=ctk.CTkFont("Segoe UI", 12),
        corner_radius=8,
        height=36,
    )
    seg.pack(fill="x")

    divider()

    # ── Watch Folder ──────────────────────────────────────────────────────────
    section_label("SHAREX WATCH FOLDER")
    ctk.CTkLabel(scroll, text="ShareX should save screenshots directly into this folder.",
                 text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 10),
                 anchor="w").pack(fill="x", pady=(0, 6))
    folder_row(app.watch_folder_var)

    divider()

    # ── Evidence Folder ───────────────────────────────────────────────────────
    section_label("KPI EVIDENCE FOLDER")
    ctk.CTkLabel(scroll, text="Classified screenshots are filed into subfolders here.",
                 text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 10),
                 anchor="w").pack(fill="x", pady=(0, 6))
    folder_row(app.evidence_folder_var)

    divider()

    # ── Screenshot Hotkey ─────────────────────────────────────────────────────
    section_label("SCREENSHOT HOTKEY")
    ctk.CTkLabel(scroll,
                 text="Click 'Record' then press your desired key combination. Works system-wide.",
                 text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 10),
                 anchor="w").pack(fill="x", pady=(0, 8))

    hotkey_row = ctk.CTkFrame(scroll, fg_color="transparent")
    hotkey_row.pack(fill="x", pady=(0, 4))

    # Display label showing current hotkey
    hotkey_display = ctk.CTkLabel(
        hotkey_row,
        textvariable=app.hotkey_var,
        fg_color=SURFACE, text_color=MAUVE,
        font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
        corner_radius=8, padx=16, pady=8,
        anchor="center",
    )
    hotkey_display.pack(side="left", fill="x", expand=True, padx=(0, 8))

    record_btn = ctk.CTkButton(
        hotkey_row, text="⏺  Record", width=110, height=38,
        fg_color=SURFACE2, hover_color="#585b70", text_color=TEXT,
        font=ctk.CTkFont("Segoe UI", 11, weight="bold"), corner_radius=8,
    )
    record_btn.pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        hotkey_row, text="Apply", width=80, height=38,
        fg_color=MAUVE, hover_color="#b09de8", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 11, weight="bold"), corner_radius=8,
        command=app.apply_hotkey,
    ).pack(side="left")

    # ── Recorder logic ────────────────────────────────────────────────────────
    _recording   = [False]
    _held_keys   = set()

    def _start_recording():
        _recording[0] = True
        _held_keys.clear()
        record_btn.configure(text="⏹  Press keys…", fg_color=RED, hover_color=RED)
        app.hotkey_var.set("…")
        # Temporarily bind key events to the scroll frame's root window
        _get_root(scroll).bind("<KeyPress>",   _on_key_press,   add="+")
        _get_root(scroll).bind("<KeyRelease>", _on_key_release, add="+")

    def _stop_recording():
        _recording[0] = False
        record_btn.configure(text="⏺  Record", fg_color=SURFACE2, hover_color="#585b70")
        _get_root(scroll).unbind("<KeyPress>")
        _get_root(scroll).unbind("<KeyRelease>")

    def _on_key_press(event):
        if not _recording[0]:
            return
        key = _tk_key_to_str(event)
        if key:
            _held_keys.add(key)
            combo = _build_combo(_held_keys)
            app.hotkey_var.set(combo)

    def _on_key_release(event):
        if not _recording[0]:
            return
        key = _tk_key_to_str(event)
        # Stop recording once any key is released — combo is locked in
        if key and key not in ("ctrl", "shift", "alt"):
            _stop_recording()

    record_btn.configure(command=_start_recording)

    # ── Save ──────────────────────────────────────────────────────────────────
    ctk.CTkButton(
        scroll, text="Save Configuration",
        fg_color=GREEN, hover_color="#8ecf8a", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
        corner_radius=10, height=44,
        command=app.save_settings,
    ).pack(fill="x", pady=(24, 8))
