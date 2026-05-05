import customtkinter as ctk
from app.constants import (BG, SURFACE, SURFACE2, TEXT, SUBTEXT,
                            MAUVE, LAVENDER, GREEN, OVERLAY, HEADER_BG)


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

    # ── Save ──────────────────────────────────────────────────────────────────
    ctk.CTkButton(
        scroll, text="Save Configuration",
        fg_color=GREEN, hover_color="#8ecf8a", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
        corner_radius=10, height=44,
        command=app.save_settings,
    ).pack(fill="x", pady=(24, 8))
