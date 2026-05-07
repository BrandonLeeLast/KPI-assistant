import os
import sys
import PIL.Image
import PIL.ImageDraw
import pystray


def build_icon_image() -> PIL.Image.Image:
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__)))
    icon_path = os.path.join(base, "static", "KPEye.png")
    try:
        img = PIL.Image.open(icon_path).convert("RGBA").resize((64, 64), PIL.Image.LANCZOS)
        return img
    except Exception:
        img  = PIL.Image.new('RGB', (64, 64), '#11111b')
        draw = PIL.ImageDraw.Draw(img)
        draw.ellipse([8,  8,  56, 56], outline="#cba6f7", width=4)
        draw.ellipse([20, 20, 44, 44], fill="#cba6f7")
        return img


def create_tray_icon(on_show, on_toggle, on_exit) -> pystray.Icon:
    menu = pystray.Menu(
        pystray.MenuItem("Show Controller", on_show,   default=True),
        pystray.MenuItem("Toggle Daemon",   lambda *_: on_toggle()),
        pystray.MenuItem("Exit",            on_exit),
    )
    return pystray.Icon(
        "kpeye",
        build_icon_image(),
        "KPEye",
        menu,
    )
