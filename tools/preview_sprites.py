"""Hoja de contacto para revisar los sprites ya tintados (solo desarrollo)."""

import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPR = os.path.join(ROOT, "assets", "sprites")


def tint(img, color):
    r, g, b = color
    px = img.split()
    from PIL import ImageChops
    solid = Image.new("RGB", img.size, (r, g, b))
    rgb = ImageChops.multiply(Image.merge("RGB", px[:3]), solid)
    return Image.merge("RGBA", (*rgb.split(), px[3]))


def compose(folder, kind, body_c, wing_c):
    base = Image.open(os.path.join(SPR, folder, f"{kind}_body.png")).convert("RGBA")
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    wing = Image.open(os.path.join(SPR, folder, f"{kind}_wing.png")).convert("RGBA")
    out.alpha_composite(tint(wing, wing_c))
    out.alpha_composite(tint(base, body_c))
    detail = Image.open(os.path.join(SPR, folder, f"{kind}_detail.png")).convert("RGBA")
    out.alpha_composite(detail)
    return out


def main():
    ships = ["scout", "tank", "interceptor", "bomber"]
    tints = [
        ((140, 210, 255), (100, 170, 255)),
        ((255, 190, 140), (200, 140, 100)),
        ((200, 150, 255), (255, 160, 210)),
        ((0, 255, 200), (0, 180, 255)),
        ((255, 215, 0), (200, 170, 0)),
    ]
    cell_w, cell_h = 170, 138
    sheet = Image.new("RGBA", (max(cell_w * len(ships), 990), cell_h * len(tints) + 900), (12, 12, 32, 255))

    for col, kind in enumerate(ships):
        for row, (bc, wc) in enumerate(tints):
            img = compose("ships", kind, bc, wc)
            sheet.alpha_composite(img, (col * cell_w + 5, row * cell_h + 5))

    y = cell_h * len(tints) + 10
    rocks = [(190, 165, 140), (150, 130, 120), (200, 190, 175), (130, 150, 160), (175, 155, 190)]
    cols = 7
    for i in range(14):
        rock = Image.open(os.path.join(SPR, "asteroids", f"asteroid_{i}.png")).convert("RGBA")
        rx = (i % cols) * 128
        ry = y + (i // cols) * 128
        sheet.alpha_composite(tint(rock, rocks[i % len(rocks)]), (rx, ry))

    y += 2 * 128 + 10
    enemy_tints = [(200, 150, 255), (255, 160, 210), (120, 255, 170)]
    for i, kind in enumerate(["fighter", "drone", "gunner"]):
        for j, c in enumerate(enemy_tints):
            img = compose("enemies", kind, c, tuple(max(0, v - 45) for v in c))
            sheet.alpha_composite(img, (j * 230 + i * 74, y))

    y += 140
    boss_tints = [
        ((170, 170, 190), (90, 190, 150)),
        ((190, 150, 220), (150, 90, 200)),
        ((230, 120, 140), (200, 70, 110)),
    ]
    for i, (bc, wc) in enumerate(boss_tints):
        img = compose("boss", "mothership", bc, wc)
        sheet.alpha_composite(img, (i * 330, y))

    out = os.path.join(ROOT, "tools", "_preview_sheet.png")
    sheet.convert("RGB").save(out)
    print(out)


if __name__ == "__main__":
    main()
