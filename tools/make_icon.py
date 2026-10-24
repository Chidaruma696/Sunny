"""Generates sunny/assets/sunny.png and sunny.ico: a white sun on Sunny orange, square corners, ink border."""
import math
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[1] / "sunny" / "assets"
SUN = (240, 160, 32, 255)
INK = (43, 29, 8, 255)
WHITE = (255, 255, 255, 255)


def sun(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size * 0.03
    border = max(1, int(size * 0.045))
    d.rectangle([m, m, size - m, size - m], fill=SUN, outline=INK, width=border)
    cx = cy = size / 2
    r = size * 0.19
    w = max(1, int(size * 0.05))
    for k in range(12):
        a = math.radians(k * 30)
        inner, outer = r * 1.45, r * (2.1 if k % 2 == 0 else 1.8)
        d.line([cx + inner * math.cos(a), cy + inner * math.sin(a),
                cx + outer * math.cos(a), cy + outer * math.sin(a)], fill=WHITE, width=w)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE, outline=INK, width=max(1, int(size * 0.02)))
    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    big = sun(1024)
    big.resize((256, 256), Image.LANCZOS).save(ASSETS / "sunny.png")
    big.save(ASSETS / "sunny.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("ok", ASSETS)


if __name__ == "__main__":
    main()
