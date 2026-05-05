import tkinter as tk
import customtkinter as ctk
from app.constants import (BG, BG2, SURFACE, SURFACE2, OVERLAY,
                            TEXT, SUBTEXT, GREEN, RED, BLUE, TEAL, YELLOW, HEADER_BG)
from app.ui.widgets import StatCard


def build(parent: ctk.CTkFrame, app) -> dict:
    """
    Build the Dashboard tab. Returns widget refs the app shell needs:
      btn_toggle, btn_update, card_queued, card_filed, card_errors, log_text
    """
    refs = {}

    # ── stat cards ────────────────────────────────────────────────────────────
    cards_row = ctk.CTkFrame(parent, fg_color="transparent")
    cards_row.pack(fill="x", padx=20, pady=(16, 8))
    cards_row.columnconfigure((0, 1, 2), weight=1, uniform="card")

    refs["card_queued"] = StatCard(cards_row, "QUEUED", YELLOW)
    refs["card_filed"]  = StatCard(cards_row, "FILED",  GREEN)
    refs["card_errors"] = StatCard(cards_row, "ERRORS", RED)

    refs["card_queued"].grid(row=0, column=0, padx=(0, 6), sticky="ew")
    refs["card_filed"].grid( row=0, column=1, padx=6,      sticky="ew")
    refs["card_errors"].grid(row=0, column=2, padx=(6, 0), sticky="ew")

    # ── action buttons ────────────────────────────────────────────────────────
    btn_row = ctk.CTkFrame(parent, fg_color="transparent")
    btn_row.pack(fill="x", padx=20, pady=(4, 12))

    refs["btn_toggle"] = ctk.CTkButton(
        btn_row, text="⏹  Stop Daemon",
        fg_color=RED, hover_color="#e0728a", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
        corner_radius=8, height=36,
        command=app.toggle_service,
    )
    refs["btn_toggle"].pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_row, text="🔍  Scan Backlog",
        fg_color=BLUE, hover_color="#6fa8e8", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
        corner_radius=8, height=36,
        command=app.run_manual_backlog_scan,
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_row, text="↗  Evidence Folder",
        fg_color=TEAL, hover_color="#78c9bf", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
        corner_radius=8, height=36,
        command=app.open_evidence_folder,
    ).pack(side="left")

    refs["btn_update"] = ctk.CTkButton(
        btn_row, text="☁  Updates",
        fg_color=SURFACE2, hover_color="#585b70", text_color=TEXT,
        font=ctk.CTkFont("Segoe UI", 12),
        corner_radius=8, height=36,
        command=app.manual_update_check,
    )
    refs["btn_update"].pack(side="right")

    # ── log console ───────────────────────────────────────────────────────────
    log_card = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=12)
    log_card.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    log_hdr = ctk.CTkFrame(log_card, fg_color="transparent", height=32)
    log_hdr.pack(fill="x", padx=14, pady=(10, 0))
    log_hdr.pack_propagate(False)

    ctk.CTkLabel(log_hdr, text="SYSTEM LOG", text_color=OVERLAY,
                 font=ctk.CTkFont("Segoe UI", 10, weight="bold")).pack(side="left")

    ctk.CTkButton(
        log_hdr, text="Clear", width=50, height=22,
        fg_color=SURFACE, hover_color=SURFACE2, text_color=SUBTEXT,
        font=ctk.CTkFont("Segoe UI", 10), corner_radius=6,
        command=lambda: _clear_log(refs["log_text"]),
    ).pack(side="right")

    # scrollable text box
    log_frame = ctk.CTkFrame(log_card, fg_color="transparent")
    log_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    log_text = tk.Text(
        log_frame,
        bg=BG2, fg=SUBTEXT,
        insertbackground=TEXT,
        font=("Cascadia Code", 9) if _font_exists("Cascadia Code") else ("Consolas", 9),
        state="disabled",
        wrap="word",
        relief="flat",
        bd=0,
        padx=8, pady=4,
        selectbackground=SURFACE2,
    )

    scrollbar = ctk.CTkScrollbar(log_frame, command=log_text.yview,
                                  fg_color=BG2, button_color=SURFACE2,
                                  button_hover_color=OVERLAY)
    scrollbar.pack(side="right", fill="y")
    log_text.configure(yscrollcommand=scrollbar.set)
    log_text.pack(side="left", fill="both", expand=True)

    log_text.tag_config("ts",      foreground=OVERLAY)
    log_text.tag_config("info",    foreground=SUBTEXT)
    log_text.tag_config("success", foreground=GREEN)
    log_text.tag_config("warn",    foreground=YELLOW)
    log_text.tag_config("error",   foreground=RED)

    refs["log_text"] = log_text
    return refs


def _clear_log(log_text: tk.Text) -> None:
    log_text.config(state="normal")
    log_text.delete("1.0", tk.END)
    log_text.config(state="disabled")


def _font_exists(name: str) -> bool:
    import tkinter.font as tkfont
    return name in tkfont.families()
