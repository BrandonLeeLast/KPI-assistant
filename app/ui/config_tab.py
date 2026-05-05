import customtkinter as ctk
import tkinter as tk
from app.constants import (BG, SURFACE, SURFACE2, TEXT, SUBTEXT,
                            MAUVE, GREEN, RED, TEAL, BLUE, YELLOW, OVERLAY, HEADER_BG)
from app.ai_provider import PROVIDERS, DEFAULT_MODELS
from app.kpa_context import ALL_LEVELS


# ── Hotkey recorder helpers ───────────────────────────────────────────────────
def _get_root(widget):
    w = widget
    while w.master:
        w = w.master
    return w

def _tk_key_to_str(event) -> str | None:
    MODIFIER_MAP = {
        "Control_L": "ctrl", "Control_R": "ctrl",
        "Shift_L": "shift",  "Shift_R":  "shift",
        "Alt_L": "alt",      "Alt_R":    "alt",
        "Super_L": "win",    "Super_R":  "win",
    }
    sym = event.keysym
    if sym in MODIFIER_MAP:
        return MODIFIER_MAP[sym]
    if sym.startswith("F") and sym[1:].isdigit():
        return sym
    if len(sym) == 1:
        return sym.lower()
    return None

def _build_combo(keys: set) -> str:
    ORDER = ["ctrl", "shift", "alt", "win"]
    mods  = [k for k in ORDER if k in keys]
    rest  = [k for k in keys  if k not in ORDER]
    return "+".join(mods + sorted(rest))


# ── Builder ───────────────────────────────────────────────────────────────────
def build(parent: ctk.CTkFrame, app) -> None:

    scroll = ctk.CTkScrollableFrame(
        parent, fg_color="transparent",
        scrollbar_button_color=SURFACE2,
        scrollbar_button_hover_color=OVERLAY,
    )
    scroll.pack(fill="both", expand=True, padx=20, pady=12)

    # ── Fix mouse wheel scrolling on Windows ──────────────────────────────────
    def _on_mousewheel(event):
        scroll._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        for child in widget.winfo_children():
            _bind_mousewheel(child)

    # Re-bind after each widget is added
    def _rebind(*_):
        _bind_mousewheel(scroll)

    scroll.bind("<Configure>", _rebind)
    scroll.bind("<MouseWheel>", _on_mousewheel)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def section(text: str, color: str = MAUVE) -> None:
        # Single-line row: coloured left pip + bold label, fixed height, no expansion
        row = ctk.CTkFrame(scroll, fg_color="transparent", height=24)
        row.pack(fill="x", pady=(10, 3))
        row.pack_propagate(False)
        pip = ctk.CTkFrame(row, fg_color=color, width=3, height=16, corner_radius=2)
        pip.place(x=0, y=4)
        ctk.CTkLabel(row, text=text, text_color=color,
                     font=ctk.CTkFont("Segoe UI", 11, weight="bold"),
                     anchor="w").place(x=11, y=2)

    def hint(text: str) -> None:
        ctk.CTkLabel(scroll, text=text, text_color=OVERLAY,
                     font=ctk.CTkFont("Segoe UI", 10),
                     anchor="w", justify="left").pack(fill="x", pady=(0, 2))

    def divider() -> None:
        ctk.CTkFrame(scroll, fg_color=SURFACE, height=1,
                     corner_radius=0).pack(fill="x", pady=(8, 0))

    def entry(var, show=None, placeholder="") -> ctk.CTkEntry:
        e = ctk.CTkEntry(
            scroll, textvariable=var,
            fg_color=SURFACE, border_color=SURFACE2,
            text_color=TEXT, placeholder_text=placeholder,
            placeholder_text_color=OVERLAY,
            font=ctk.CTkFont("Segoe UI", 11),
            corner_radius=8, height=34, border_width=1,
        )
        if show:
            e.configure(show=show)
        e.pack(fill="x", pady=(0, 2))
        return e

    def folder_row(var) -> None:
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 2))
        ctk.CTkEntry(
            row, textvariable=var,
            fg_color=SURFACE, border_color=SURFACE2,
            text_color=TEXT, font=ctk.CTkFont("Segoe UI", 11),
            corner_radius=8, height=34, border_width=1,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            row, text="Browse", width=72, height=34,
            fg_color=SURFACE2, hover_color="#585b70", text_color=TEXT,
            font=ctk.CTkFont("Segoe UI", 10), corner_radius=8,
            command=lambda: app.browse_folder(var),
        ).pack(side="right")

    # ══════════════════════════════════════════════════════════════════════════
    # 1. AI PROVIDER
    # ══════════════════════════════════════════════════════════════════════════
    section("🤖  AI PROVIDER", MAUVE)
    hint("Choose which AI processes your screenshots. Each requires its own API key.")

    provider_row = ctk.CTkFrame(scroll, fg_color="transparent")
    provider_row.pack(fill="x", pady=(0, 4))

    provider_var = app.provider_var
    for name in PROVIDERS:
        color  = {
            "Gemini": MAUVE, "Claude": TEAL,
            "OpenAI": GREEN, "Ollama": YELLOW,
        }.get(name, SURFACE2)
        rb = ctk.CTkRadioButton(
            provider_row, text=name,
            variable=provider_var, value=name,
            fg_color=color, hover_color=color,
            text_color=TEXT, font=ctk.CTkFont("Segoe UI", 11),
        )
        rb.pack(side="left", padx=(0, 20))

    # Model field — auto-fills when provider changes
    ctk.CTkLabel(scroll, text="Model", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(2, 0))
    entry(app.model_var, placeholder="e.g. gemini-2.0-flash / claude-opus-4-5 / gpt-4o")

    # API Key
    ctk.CTkLabel(scroll, text="API Key", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(4, 0))

    key_row = ctk.CTkFrame(scroll, fg_color="transparent")
    key_row.pack(fill="x", pady=(0, 2))

    key_entry = ctk.CTkEntry(
        key_row, textvariable=app.api_key_var,
        fg_color=SURFACE, border_color=SURFACE2,
        text_color=TEXT, font=ctk.CTkFont("Segoe UI", 12),
        corner_radius=8, height=38, border_width=1, show="•",
    )
    key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    show_var = tk.BooleanVar(value=False)
    def _toggle_show():
        key_entry.configure(show="" if show_var.get() else "•")
    ctk.CTkCheckBox(
        key_row, text="Show", variable=show_var,
        fg_color=MAUVE, hover_color="#b09de8", text_color=SUBTEXT,
        font=ctk.CTkFont("Segoe UI", 10), command=_toggle_show, width=60,
    ).pack(side="right")

    # Ollama note
    hint("For Ollama: leave API Key blank or enter your server URL (default: http://localhost:11434)")

    # Auto-fill model when provider radio changes
    def _on_provider_change(*_):
        from app.ai_provider import DEFAULT_MODELS, PROVIDERS
        key  = PROVIDERS.get(provider_var.get(), "gemini")
        default = DEFAULT_MODELS.get(key, "")
        if not app.model_var.get() or app.model_var.get() in DEFAULT_MODELS.values():
            app.model_var.set(default)
    provider_var.trace_add("write", _on_provider_change)

    divider()

    # ══════════════════════════════════════════════════════════════════════════
    # 2. DEVELOPER LEVEL
    # ══════════════════════════════════════════════════════════════════════════
    section("🎯  DEVELOPER LEVEL", BLUE)
    hint("Sets the performance benchmark referenced in AI prompts.")

    ctk.CTkOptionMenu(
        scroll,
        values=ALL_LEVELS,
        variable=app.level_var,
        fg_color=SURFACE, button_color=BLUE, button_hover_color="#6fa8e8",
        dropdown_fg_color=SURFACE, dropdown_hover_color=SURFACE2,
        text_color=TEXT, dropdown_text_color=TEXT,
        font=ctk.CTkFont("Segoe UI", 12), dropdown_font=ctk.CTkFont("Segoe UI", 11),
        corner_radius=8, height=36,
    ).pack(fill="x")

    divider()

    # ══════════════════════════════════════════════════════════════════════════
    # 3. FOLDERS
    # ══════════════════════════════════════════════════════════════════════════
    section("📁  FOLDERS", TEAL)

    ctk.CTkLabel(scroll, text="Screenshot Watch Folder", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(2, 0))
    hint("Auto-picked up and processed when a new image lands here.")
    folder_row(app.watch_folder_var)

    ctk.CTkLabel(scroll, text="KPI Evidence Folder", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(4, 0))
    hint("Classified screenshots are organised into subfolders here.")
    folder_row(app.evidence_folder_var)

    divider()

    # ══════════════════════════════════════════════════════════════════════════
    # 4. SCREENSHOT CAPTURE
    # ══════════════════════════════════════════════════════════════════════════
    section("📸  SCREENSHOT CAPTURE", GREEN)

    ctk.CTkLabel(scroll, text="Global Hotkey", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(2, 2))

    hotkey_row = ctk.CTkFrame(scroll, fg_color="transparent")
    hotkey_row.pack(fill="x", pady=(0, 2))

    ctk.CTkLabel(
        hotkey_row, textvariable=app.hotkey_var,
        fg_color=SURFACE, text_color=GREEN,
        font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
        corner_radius=8, padx=16, pady=8, anchor="center",
    ).pack(side="left", fill="x", expand=True, padx=(0, 8))

    record_btn = ctk.CTkButton(
        hotkey_row, text="⏺  Record", width=110, height=38,
        fg_color=SURFACE2, hover_color="#585b70", text_color=TEXT,
        font=ctk.CTkFont("Segoe UI", 11, weight="bold"), corner_radius=8,
    )
    record_btn.pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        hotkey_row, text="Apply", width=80, height=38,
        fg_color=GREEN, hover_color="#8ecf8a", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 11, weight="bold"), corner_radius=8,
        command=app.apply_hotkey,
    ).pack(side="left")

    # Hotkey recorder logic
    _recording = [False]
    _held_keys  = set()

    def _start_recording():
        _recording[0] = True
        _held_keys.clear()
        record_btn.configure(text="⏹  Press keys…", fg_color=RED, hover_color=RED)
        app.hotkey_var.set("…")
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
            app.hotkey_var.set(_build_combo(_held_keys))

    def _on_key_release(event):
        if not _recording[0]:
            return
        key = _tk_key_to_str(event)
        if key and key not in ("ctrl", "shift", "alt", "win"):
            _stop_recording()

    record_btn.configure(command=_start_recording)

    # Capture format
    ctk.CTkLabel(scroll, text="Save Format", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(6, 2))
    ctk.CTkSegmentedButton(
        scroll, values=["PNG", "JPG"],
        variable=app.capture_format_var,
        fg_color=SURFACE,
        selected_color=GREEN, selected_hover_color="#8ecf8a",
        unselected_color=SURFACE, unselected_hover_color=SURFACE2,
        text_color=TEXT, font=ctk.CTkFont("Segoe UI", 11),
        corner_radius=8, height=30, width=140,
    ).pack(anchor="w")

    divider()

    # ══════════════════════════════════════════════════════════════════════════
    # 5. PROCESSING
    # ══════════════════════════════════════════════════════════════════════════
    section("⚙️  PROCESSING", YELLOW)

    toggle_row2 = lambda label, var, color, h=None: (
        [
            r := ctk.CTkFrame(scroll, fg_color="transparent"),
            r.pack(fill="x", pady=(2, 0)),
            ctk.CTkLabel(r, text=label, text_color=TEXT,
                         font=ctk.CTkFont("Segoe UI", 11)).pack(side="left"),
            ctk.CTkSwitch(r, text="", variable=var,
                          fg_color=SURFACE2, progress_color=color,
                          width=44).pack(side="right"),
            ctk.CTkLabel(scroll, text=h, text_color=OVERLAY,
                         font=ctk.CTkFont("Segoe UI", 10),
                         anchor="w", justify="left").pack(fill="x") if h else None,
        ]
    )

    toggle_row2(
        "Auto-process on capture",
        app.auto_process_var, YELLOW,
        "When on: context window appears automatically after each capture.",
    )
    toggle_row2(
        "Show context window",
        app.show_context_var, MAUVE,
        "When off: screenshots are sent straight to AI with no prompt — zero friction mode.",
    )

    ctk.CTkLabel(scroll, text="KPA Categories (comma-separated)", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(6, 0))
    entry(app.kpa_categories_var, placeholder="Technical Mastery, Engineering Operations, …")

    ctk.CTkLabel(scroll, text="Custom AI Prompt (appended to base instructions)", text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x", pady=(4, 0))
    prompt_box = ctk.CTkTextbox(
        scroll, height=60,
        fg_color=SURFACE, border_color=SURFACE2, border_width=1,
        text_color=TEXT, font=ctk.CTkFont("Segoe UI", 11),
        corner_radius=8, wrap="word",
    )
    prompt_box.insert("1.0", app.context_prompt_var.get())
    prompt_box.pack(fill="x", pady=(0, 4))

    def _sync_prompt(*_):
        app.context_prompt_var.set(prompt_box.get("1.0", tk.END).strip())
    prompt_box.bind("<FocusOut>", lambda _: _sync_prompt())

    divider()

    # ══════════════════════════════════════════════════════════════════════════
    # 6. NOTIFICATIONS
    # ══════════════════════════════════════════════════════════════════════════
    section("🔔  NOTIFICATIONS", TEAL)

    def toggle_row(label: str, var: tk.BooleanVar, color: str) -> None:
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(row, text=label, text_color=TEXT,
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")
        ctk.CTkSwitch(row, text="", variable=var,
                      fg_color=SURFACE2, progress_color=color,
                      width=44).pack(side="right")

    toggle_row("Notify on successful classification", app.notify_success_var, GREEN)
    toggle_row("Notify on processing failure",        app.notify_failure_var, RED)

    # ══════════════════════════════════════════════════════════════════════════
    # SAVE BUTTON
    # ══════════════════════════════════════════════════════════════════════════
    ctk.CTkFrame(scroll, fg_color=SURFACE, height=1, corner_radius=0).pack(fill="x", pady=(10, 0))
    ctk.CTkButton(
        scroll, text="Save Configuration",
        fg_color=MAUVE, hover_color="#b09de8", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
        corner_radius=8, height=38,
        command=app.save_settings,
    ).pack(fill="x", pady=(6, 8))
