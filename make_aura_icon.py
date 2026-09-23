# -*- coding: utf-8 -*-
"""Generate Aura.ico — violet rounded square with white A."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:\Users\neno\Downloads\Aura\assets")
OUT.mkdir(parents=True, exist_ok=True)

def make(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    # rounded rect background
    d.rounded_rectangle([pad, pad, size - pad - 1, size - pad - 1], radius=size // 5,
                        fill=(88, 28, 135, 255))  # deep violet
    # inner glow
    d.rounded_rectangle([pad + size // 12, pad + size // 12, size - pad - size // 12 - 1, size - pad - size // 12 - 1],
                        radius=size // 6, fill=(168, 85, 247, 255))
    # letter A
    font_size = int(size * 0.58)
    font = None
    for name in [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(name, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    text = "A"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1] - size * 0.04
    d.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    return img

sizes = [16, 24, 32, 48, 64, 128, 256]
images = [make(s) for s in sizes]
ico_path = OUT / "Aura.ico"
images[-1].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
png_path = OUT / "Aura.png"
images[-1].save(png_path)
print("wrote", ico_path, ico_path.stat().st_size)
print("wrote", png_path)
