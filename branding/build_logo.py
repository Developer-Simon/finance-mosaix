"""Generates every logo file of the project from the mark below and the Sora font.

Run from the repository root: python branding/build_logo.py
Needs fontTools (Python) and ImageMagick with SVG support (magick) for the PNG/ICO files.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "branding" / "fonts" / "Sora[wght].ttf"
DASHBOARD = ROOT / "src" / "finance_mosaix" / "dashboard" / "assets"
ELECTRON = ROOT / "electron" / "assets"
DOCS = ROOT / "docs" / "img"
FAVICONS = ROOT / "docs" / "assets" / "img" / "favicons"  # where the Chirpy theme looks for them

# Mosaik-M on a 64 unit grid: two legs of three tiles and a wedge in the middle.
MARK = """<rect x="4" y="4" width="16" height="16" rx="2" fill="#4F46E5"/>
<rect x="4" y="24" width="16" height="16" rx="2" fill="#6366F1"/>
<rect x="4" y="44" width="16" height="16" rx="2" fill="#4F46E5"/>
<rect x="44" y="4" width="16" height="16" rx="2" fill="#818CF8"/>
<rect x="44" y="24" width="16" height="16" rx="2" fill="#6366F1"/>
<rect x="44" y="44" width="16" height="16" rx="2" fill="#818CF8"/>
<path d="M24 4H40L32 30Z" fill="#EC4899"/>"""

FONT_SIZE = 30.4  # wordmark size next to the 64 unit mark
GAP = 16          # space between mark and wordmark
LIGHT_INK = "#31333F"  # Streamlit text colour, light theme
DARK_INK = "#FAFAFA"   # Streamlit text colour, dark theme
LABEL = 'role="img" aria-label="finance mosaix"'
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)


def svg(view_box, body):
    _, _, w, h = view_box.split()
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{w}" height="{h}" {LABEL}>\n{body}\n</svg>\n'


def text_path(font, text, x, baseline):
    """Outlines text as one SVG path (no kerning) and returns it with the end position."""
    scale = FONT_SIZE / font["head"].unitsPerEm
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    for ch in text:
        name = cmap[ord(ch)]
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
        x += hmtx[name][0] * scale
    return pen.getCommands(), x


def lockup(ink):
    light = instancer.instantiateVariableFont(TTFont(FONT), {"wght": 300})
    bold = instancer.instantiateVariableFont(TTFont(FONT), {"wght": 700})
    # Centre the x-height on the mark.
    x_height = light["OS/2"].sxHeight * FONT_SIZE / light["head"].unitsPerEm
    baseline = 32 + x_height / 2
    d_light, x = text_path(light, "finance", 64 + GAP, baseline)
    d_bold, x = text_path(bold, "mosaix", x, baseline)
    return svg(f"0 0 {round(x + 2)} 64", f'{MARK}\n<g fill="{ink}"><path d="{d_light}"/><path d="{d_bold}"/></g>')


def rasterize(source, target, size, *extra):
    subprocess.run(["magick", "-background", "none", "-density", "1200", str(source),
                    "-resize", f"{size}x{size}", "-depth", "8", "-strip", *extra, str(target)], check=True)


def main():
    mark = svg("0 0 64 64", MARK)
    files = {
        DASHBOARD / "logo-mark.svg": mark,
        DASHBOARD / "logo-light.svg": lockup(LIGHT_INK),
        DASHBOARD / "logo-dark.svg": lockup(DARK_INK),
        ELECTRON / "icon.svg": mark,
        ELECTRON / "logo.svg": lockup("currentColor"),  # title bar, inherits the bar colour
        FAVICONS / "favicon.svg": mark,
        # The docs avatar is cropped to a circle; the margin keeps the tile corners inside it.
        DOCS / "logo.svg": svg("-12 -12 88 88", MARK),
    }
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print("wrote", path.relative_to(ROOT))

    if not shutil.which("magick"):
        print("magick not found: PNG and ICO files were not updated")
        return
    icon = ELECTRON / "icon.svg"
    rasterize(icon, ELECTRON / "icon.png", 512)
    for size in ICON_SIZES:
        rasterize(icon, ELECTRON / "icons" / f"{size}x{size}.png", size)
    rasterize(icon, FAVICONS / "favicon-96x96.png", 96)
    rasterize(icon, FAVICONS / "favicon.ico", 256, "-define", "icon:auto-resize=48,32,16")
    # Home screen icons need an opaque background; the margin keeps the mark inside
    # the safe zone of a maskable icon (a circle of 80 % of the size).
    with tempfile.TemporaryDirectory() as tmp:
        tile = Path(tmp) / "tile.svg"
        tile.write_text(svg("-18 -18 100 100", f'<rect x="-18" y="-18" width="100" height="100" fill="#FFFFFF"/>\n{MARK}'))
        rasterize(tile, FAVICONS / "apple-touch-icon.png", 180)
        for size in (192, 512):
            rasterize(tile, FAVICONS / f"web-app-manifest-{size}x{size}.png", size)
    print("wrote PNG icons and favicons")


if __name__ == "__main__":
    main()
