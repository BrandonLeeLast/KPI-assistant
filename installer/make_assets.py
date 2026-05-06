"""
Generate Inno Setup wizard images programmatically.
Runs in CI before ISCC so no binary assets need to be committed.

Outputs:
  installer/wizard.bmp       164x314  — left panel (Welcome + Finish pages)
  installer/wizard_small.bmp  55x58  — top-right header (inner pages)
  installer/app_icon.ico             — app icon for EXE/uninstaller
"""

from PIL import Image, ImageDraw, ImageFont
import os
import struct
import zlib

OUT = os.path.dirname(os.path.abspath(__file__))

# ── Palette (Catppuccin Mocha) ────────────────────────────────────────────────
BG      = (30,  30,  46)   # base
SURFACE = (49,  50,  68)   # surface0
MAUVE   = (203, 166, 247)  # mauve
TEXT    = (205, 214, 244)  # text
OVERLAY = (108, 112, 134)  # overlay0
TEAL    = (148, 226, 213)  # teal


def _font(size: int):
    """Try Segoe UI, fall back to default."""
    try:
        return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
    except Exception:
        return ImageFont.load_default()


def make_wizard_panel():
    """
    164x314 left panel.
    If wizard_source.png exists, crop/resize it to fit and overlay
    a subtle dark gradient + app name text on top.
    Falls back to generated dark panel if no source image found.
    """
    source = next(
        (os.path.join(OUT, f) for f in ("wizard_source.png", "wizard_source.jpeg", "wizard_source.jpg")
         if os.path.exists(os.path.join(OUT, f))),
        None
    )
    if source is None:
        source = ""  # trigger fallback

    if source and os.path.exists(source):
        # Load source, smart-crop to 164x314 (centre crop)
        src = Image.open(source).convert("RGB")
        sw, sh = src.size
        target_ratio = 164 / 314

        # Crop to target aspect ratio from centre
        src_ratio = sw / sh
        if src_ratio > target_ratio:
            # wider than needed — crop sides
            new_w = int(sh * target_ratio)
            x0 = (sw - new_w) // 2
            src = src.crop((x0, 0, x0 + new_w, sh))
        else:
            # taller than needed — crop top/bottom, bias toward top (more interesting)
            new_h = int(sw / target_ratio)
            src = src.crop((0, 0, sw, new_h))

        img = src.resize((164, 314), Image.LANCZOS)

        # Dark gradient overlay at bottom so text is readable
        overlay = Image.new("RGBA", (164, 314), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        for y in range(100, 314):
            alpha = int(180 * ((y - 100) / 214))
            ov_draw.line([(0, y), (163, y)], fill=(0, 0, 0, alpha))

        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay).convert("RGB")

    else:
        # Fallback: generated dark panel
        print("  wizard_source.png not found — using generated panel")
        img = Image.new("RGB", (164, 314), BG)
        for y in range(314):
            factor = 1.0 - (y / 314) * 0.15
            r, g, b = [int(c * factor) for c in BG]
            ImageDraw.Draw(img).line([(0, y), (163, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(img)

    # App name + tagline overlay at bottom
    draw.text((12, 220), "KPI Assistant", font=_font(16), fill=TEXT)
    draw.text((12, 242), "Born to explore", font=_font(9), fill=MAUVE)
    draw.text((12, 254), "the cosmos.", font=_font(9), fill=MAUVE)
    draw.text((12, 268), "Forced to watch", font=_font(9), fill=OVERLAY)
    draw.text((12, 280), "KPI_Proof.", font=_font(9), fill=OVERLAY)

    img.save(os.path.join(OUT, "wizard.bmp"), "BMP")
    print("wizard.bmp generated")


def make_wizard_small():
    """55x58 top-right header icon — hex on dark background."""
    img  = Image.new("RGB", (55, 58), BG)
    draw = ImageDraw.Draw(img)
    draw.text((4, 2), "⬡", font=_font(46), fill=MAUVE)
    img.save(os.path.join(OUT, "wizard_small.bmp"), "BMP")
    print("wizard_small.bmp generated")


def make_icon():
    """
    Generate a simple .ico file with multiple sizes.
    Uses a dark circle with the hex ⬡ symbol.
    """
    sizes = [256, 128, 64, 48, 32, 16]
    frames = []

    for size in sizes:
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark circle background
        pad = size // 16
        draw.ellipse([pad, pad, size - pad, size - pad], fill=(*BG, 255))

        # Hex symbol centred
        font_size = int(size * 0.65)
        fnt = _font(font_size)
        try:
            bbox = draw.textbbox((0, 0), "⬡", font=fnt)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except Exception:
            tw, th = font_size, font_size
        x = (size - tw) // 2 - 1
        y = (size - th) // 2 - 2
        draw.text((x, y), "⬡", font=fnt, fill=(*MAUVE, 255))

        frames.append(img)

    frames[0].save(
        os.path.join(OUT, "app_icon.ico"),
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print("app_icon.ico generated")


if __name__ == "__main__":
    make_wizard_panel()
    make_wizard_small()
    make_icon()
    print("All installer assets generated.")
