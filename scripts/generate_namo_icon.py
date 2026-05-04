"""
Generate namo_icon.ico from the NamoNexus brand colours.
Produces a multi-resolution ICO (16, 32, 48, 256 px) with a
purple lightning-bolt "N" on a dark background — matching favicon.svg.

Run from project root:
    .venv\Scripts\python.exe scripts\generate_namo_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# Brand colours (matches favicon.svg)
BG      = (14,  7, 28, 255)    # near-black purple
PURPLE  = (134, 59, 255, 255)  # #863bff
CYAN    = (71, 191, 255, 255)  # #47bfff
WHITE   = (255, 255, 255, 255)


def draw_frame(size: int) -> Image.Image:
    """Draw one NamoNexus icon frame at the given pixel size."""
    img = Image.new("RGBA", (size, size), BG)
    d   = ImageDraw.Draw(img)

    pad  = max(2, size // 16)
    s    = size - pad * 2          # usable area side

    # ── Lightning-bolt "N" shape (4-point polygon) ──────────────────────────
    # Proportions mirror the favicon.svg path (top-right → bottom diagonal → bottom-left)
    pts = [
        (pad + s * 0.60, pad),                           # top-right
        (pad + s * 0.20, pad + s * 0.50),                # mid-left
        (pad + s * 0.55, pad + s * 0.50),                # mid-right
        (pad + s * 0.40, pad + s),                        # bottom-left
        (pad + s * 0.80, pad + s * 0.50),                # mid-right lower
        (pad + s * 0.45, pad + s * 0.50),                # mid-left lower
    ]
    d.polygon(pts, fill=PURPLE)

    # Cyan highlight on top-right tip (mimics the SVG's cyan ellipse)
    tip_r = max(1, size // 10)
    tx = int(pad + s * 0.70)
    ty = int(pad + s * 0.08)
    d.ellipse([tx - tip_r, ty - tip_r, tx + tip_r, ty + tip_r], fill=CYAN)

    return img


def main() -> None:
    out = Path(__file__).resolve().parent / "namo_icon.ico"
    # Draw at max resolution, Pillow downscales to each requested size
    base = draw_frame(256)
    base.save(
        out,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
    )
    print(f"[OK] Icon saved: {out}  ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
