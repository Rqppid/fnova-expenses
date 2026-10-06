"""Receipt photo -> clean greyscale PDF that reads like a scan.

Greyscale, not 1-bit black and white: thresholding wipes out faded thermal print and small
VAT lines, and HMRC needs those legible. Several photos of one long receipt become one
multi-page PDF.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".bmp", ".tif", ".tiff"}
DPI = 200
MAX_LONG_SIDE = 2400        # pixels; about 30 cm at 200 dpi, plenty for a receipt


def _open(path: Path) -> Image.Image:
    if path.suffix.lower() in (".heic", ".heif"):
        import pillow_heif
        pillow_heif.register_heif_opener()
    img = Image.open(path)
    img.load()
    return img


def _trim_border(g: Image.Image, margin: int = 12) -> Image.Image:
    """Crop to the bright receipt paper when it sits on a darker background."""
    small = g.resize((max(1, g.width // 8), max(1, g.height // 8)))
    hist = small.histogram()
    total = sum(hist)
    # Paper threshold: the brightest 45% of pixels.
    acc, thr = 0, 255
    for level in range(255, -1, -1):
        acc += hist[level]
        if acc >= total * 0.45:
            thr = level
            break
    if thr < 120:                      # no clearly bright paper: leave as is
        return g
    mask = small.point(lambda v: 255 if v >= thr else 0)
    box = mask.getbbox()
    if not box:
        return g
    l, t, r, b = (v * 8 for v in box)
    l, t = max(0, l - margin), max(0, t - margin)
    r, b = min(g.width, r + margin), min(g.height, b + margin)
    if (r - l) * (b - t) < 0.25 * g.width * g.height:   # implausibly small: keep everything
        return g
    return g.crop((l, t, r, b))


def clean(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = bg
    g = img.convert("L")
    g = _trim_border(g)
    scale = MAX_LONG_SIDE / max(g.size)
    if scale < 1:
        g = g.resize((round(g.width * scale), round(g.height * scale)), Image.LANCZOS)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = g.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    return g


def to_pdf(sources: list[Path], dest: Path) -> Path:
    """Write the cleaned image(s) as one PDF. Raises if dest exists."""
    if dest.exists():
        raise FileExistsError(dest)
    pages = [clean(_open(Path(s))) for s in sources]
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.pdf")
    pages[0].save(tmp, "PDF", resolution=DPI, save_all=True, append_images=pages[1:])
    tmp.replace(dest)
    return dest


def is_image(path: Path) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXT
