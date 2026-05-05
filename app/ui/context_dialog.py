"""
Custom STAR context prompt dialog — replaces pyautogui.prompt().
Shows the screenshot thumbnail alongside the input field, all styled
to match the Catppuccin Mocha dark theme.
"""

import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

from app.constants import (BG, BG2, SURFACE, SURFACE2, OVERLAY,
                            TEXT, SUBTEXT, MAUVE, GREEN, RED, HEADER_BG, LAVENDER)


def ask_context(file_path: str, level: str) -> str | None:
    """
    Show a themed modal dialog with a thumbnail of the screenshot.

    Returns the entered context string, or None if the user cancelled.
    Blocks until the dialog is closed (uses its own mainloop via wait_window).
    """
    result: dict = {"value": None}  # mutable container to capture value from inner scope

    # ── Window ────────────────────────────────────────────────────────────────
    dlg = ctk.CTkToplevel()
    dlg.title("KPI Assistant  ·  Add Context")
    dlg.geometry("520x400")
    dlg.resizable(False, False)
    dlg.configure(fg_color=BG)
    dlg.attributes("-topmost", True)
    dlg.grab_set()  # block interaction with the main window

    # Centre on screen
    dlg.update_idletasks()
    x = (dlg.winfo_screenwidth()  - 520) // 2
    y = (dlg.winfo_screenheight() - 400) // 2
    dlg.geometry(f"520x400+{x}+{y}")

    # ── Header bar ────────────────────────────────────────────────────────────
    header = ctk.CTkFrame(dlg, fg_color=HEADER_BG, corner_radius=0, height=48)
    header.pack(fill="x")
    header.pack_propagate(False)

    ctk.CTkLabel(header, text="⬡", text_color=MAUVE,
                 font=ctk.CTkFont("Segoe UI", 20)).pack(side="left", padx=(14, 6), pady=8)
    ctk.CTkLabel(header, text="New Screenshot Detected", text_color=TEXT,
                 font=ctk.CTkFont("Segoe UI", 13, weight="bold")).pack(side="left")
    ctk.CTkLabel(header, text=f"{level} Level", fg_color=SURFACE, text_color=MAUVE,
                 corner_radius=6, font=ctk.CTkFont("Segoe UI", 9),
                 padx=8, pady=2).pack(side="right", padx=14)

    # ── Body ──────────────────────────────────────────────────────────────────
    body = ctk.CTkFrame(dlg, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=16, pady=12)

    # Left: thumbnail
    thumb_frame = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=10, width=160, height=120)
    thumb_frame.pack(side="left", padx=(0, 14))
    thumb_frame.pack_propagate(False)

    try:
        # Open, resize into memory, close immediately — never hold the file handle
        with Image.open(file_path) as raw:
            thumb = raw.copy()
        thumb.thumbnail((148, 108))
        photo = ImageTk.PhotoImage(thumb)
        thumb_lbl = tk.Label(thumb_frame, image=photo, bg=SURFACE, bd=0)
        thumb_lbl.image = photo  # keep reference so GC doesn't collect it
        thumb_lbl.place(relx=0.5, rely=0.5, anchor="center")
    except Exception:
        ctk.CTkLabel(thumb_frame, text="No\nPreview", text_color=OVERLAY,
                     font=ctk.CTkFont("Segoe UI", 11)).place(relx=0.5, rely=0.5, anchor="center")

    # Right: filename + input
    right = ctk.CTkFrame(body, fg_color="transparent")
    right.pack(side="left", fill="both", expand=True)

    import os
    filename = os.path.basename(file_path)
    ctk.CTkLabel(right, text=filename, text_color=SUBTEXT,
                 font=ctk.CTkFont("Segoe UI", 9),
                 wraplength=300, anchor="w").pack(anchor="w", pady=(0, 8))

    ctk.CTkLabel(right, text="STAR Context", text_color=MAUVE,
                 font=ctk.CTkFont("Segoe UI", 11, weight="bold"),
                 anchor="w").pack(anchor="w")

    ctk.CTkLabel(right,
                 text="Briefly describe the Situation, Action, and Result\nshown in this screenshot — or leave blank to skip.",
                 text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 10),
                 justify="left", anchor="w").pack(anchor="w", pady=(2, 8))

    text_box = ctk.CTkTextbox(
        right, height=90,
        fg_color=SURFACE, border_color=SURFACE2, border_width=1,
        text_color=TEXT, font=ctk.CTkFont("Segoe UI", 11),
        corner_radius=8,
        wrap="word",
    )
    text_box.pack(fill="x")
    text_box.focus_set()

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_row = ctk.CTkFrame(dlg, fg_color=BG2, corner_radius=0, height=56)
    btn_row.pack(fill="x", side="bottom")
    btn_row.pack_propagate(False)

    def on_submit():
        raw = text_box.get("1.0", tk.END).strip()
        result["value"] = raw  # empty string = user chose to skip
        dlg.destroy()

    def on_cancel():
        result["value"] = None  # None = user explicitly cancelled
        dlg.destroy()

    ctk.CTkButton(
        btn_row, text="Cancel", width=100, height=34,
        fg_color=SURFACE2, hover_color=SURFACE, text_color=SUBTEXT,
        font=ctk.CTkFont("Segoe UI", 11), corner_radius=8,
        command=on_cancel,
    ).pack(side="right", padx=(8, 16), pady=11)

    ctk.CTkButton(
        btn_row, text="Classify  →", width=130, height=34,
        fg_color=MAUVE, hover_color="#b09de8", text_color=HEADER_BG,
        font=ctk.CTkFont("Segoe UI", 11, weight="bold"), corner_radius=8,
        command=on_submit,
    ).pack(side="right", padx=(0, 8), pady=11)

    ctk.CTkLabel(btn_row, text="Press Enter to classify, Esc to cancel",
                 text_color=OVERLAY, font=ctk.CTkFont("Segoe UI", 9)).pack(side="left", padx=16)

    # Keyboard shortcuts
    dlg.bind("<Return>",  lambda _: on_submit())
    dlg.bind("<Escape>",  lambda _: on_cancel())

    dlg.wait_window()
    return result["value"]
