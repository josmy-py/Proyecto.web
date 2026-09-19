"""
Generador de sprites del juego (assets/sprites/*.png).

Los sprites se generan de forma procedural con Pillow y se guardan en disco.
El juego SOLO necesita pygame para cargarlos; Pillow unicamente hace falta si
quieres volver a generarlos o modificarlos:

    pip install pillow numpy
    python tools/generate_sprites.py

Sistema de capas
----------------
Cada nave/enemigo se exporta en varias capas PNG:

  *_body.png    escala de grises -> se tinta en runtime con body_color
  *_wing.png    escala de grises -> se tinta en runtime con wing_color
  *_detail.png  a color, NO se tinta (cabina, toberas, luces, contornos)

Al tintar con BLEND_RGBA_MULT el gris 255 devuelve el color puro y los grises
mas oscuros producen el sombreado. Por eso cualquier color personalizado del
menu funciona sin tener que redibujar nada.
"""

import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4  # supersampling: se dibuja x4 y se reduce con LANCZOS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "sprites")

SHIP_W, SHIP_H = 160, 128
ROCK_SIZE = 128
ENEMY_SIZE = 128
BOSS_W, BOSS_H = 320, 170


# ---------------------------------------------------------------- utilidades

def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _blank_mask(w, h):
    return Image.new("L", (w * SS, h * SS), 0)


def _sc(points):
    return [(x * SS, y * SS) for x, y in points]


def _mirror(points, axis_x):
    return [(2 * axis_x - x, y) for x, y in points]


def mask_from_shapes(w, h, polys=(), ellipses=(), rrects=()):
    """Silueta (modo L) construida a partir de poligonos / elipses."""
    img = _blank_mask(w, h)
    d = ImageDraw.Draw(img)
    for p in polys:
        if len(p) >= 3:
            d.polygon(_sc(p), fill=255)
    for (x0, y0, x1, y1) in ellipses:
        d.ellipse([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=255)
    for (x0, y0, x1, y1, r) in rrects:
        d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS, fill=255)
    return img


def shading_field(w, h, light=(0.34, 0.20), body_falloff=95, bottom_dark=70, spec=55):
    """Mapa de luz base (numpy, resolucion SS) para volumen cilindrico."""
    W, H = w * SS, h * SS
    xs = np.linspace(0.0, 1.0, W)[None, :]
    ys = np.linspace(0.0, 1.0, H)[:, None]
    lx, ly = light

    v = np.full((H, W), 198.0)
    v += spec * np.exp(-(((xs - lx) ** 2) / 0.05 + ((ys - ly) ** 2) / 0.12))
    v -= body_falloff * np.abs(xs - 0.5) * 2.0
    v -= bottom_dark * np.clip((ys - 0.5) / 0.5, 0.0, 1.0)
    return v


def stamp(value, w, h, draw_fn, delta):
    """Aplica un delta de luminancia en las zonas pintadas por draw_fn."""
    layer = _blank_mask(w, h)
    draw_fn(ImageDraw.Draw(layer))
    arr = np.asarray(layer, dtype=np.float32) / 255.0
    return value + arr * delta


def to_rgba_tintable(value, mask_img, w, h):
    """Convierte (luminancia, silueta) en un PNG RGBA gris listo para tintar."""
    v = np.clip(value, 25, 255).astype(np.uint8)
    val_img = Image.fromarray(v, mode="L").resize((w, h), Image.LANCZOS)
    alpha = mask_img.resize((w, h), Image.LANCZOS)
    return Image.merge("RGBA", (val_img, val_img, val_img, alpha))


def outline_layers(mask_img, w, h, dark=(6, 8, 18), dark_a=170, rim=(255, 255, 255), rim_a=95):
    """Contorno oscuro + luz de borde superior izquierdo, sobre RGBA vacio."""
    small = mask_img.resize((w, h), Image.LANCZOS)
    solid = small.point(lambda p: 255 if p > 110 else 0)

    grown = solid.filter(ImageFilter.MaxFilter(3))
    edge = Image.fromarray(
        np.clip(np.asarray(grown, np.int16) - np.asarray(solid, np.int16), 0, 255).astype(np.uint8),
        mode="L",
    )

    shifted = Image.new("L", (w, h), 0)
    shifted.paste(solid, (2, 2))
    rim_mask = Image.fromarray(
        np.clip(np.asarray(solid, np.int16) - np.asarray(shifted, np.int16), 0, 255).astype(np.uint8),
        mode="L",
    )
    rim_mask = Image.fromarray(
        (np.asarray(rim_mask, np.float32) * (np.asarray(solid, np.float32) / 255.0)).astype(np.uint8),
        mode="L",
    )

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dark_layer = Image.new("RGBA", (w, h), (*dark, dark_a))
    out.paste(dark_layer, (0, 0), edge)
    rim_layer = Image.new("RGBA", (w, h), (*rim, rim_a))
    out.paste(rim_layer, (0, 0), rim_mask)
    return out


def vertical_gradient_rgba(w, h, top, bottom):
    top = np.array(top, dtype=np.float32)
    bottom = np.array(bottom, dtype=np.float32)
    t = np.linspace(0.0, 1.0, h)[:, None, None]
    grad = top[None, None, :] * (1 - t) + bottom[None, None, :] * t
    return Image.fromarray(np.repeat(grad, w, axis=1).astype(np.uint8), mode="RGBA")


def soft_glow(w, h, cx, cy, radius, color, alpha=140):
    layer = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 6
    for i in range(steps):
        r = radius * SS * (1 - i / (steps + 1.0))
        a = int(alpha * (i + 1) / steps * 0.35)
        d.ellipse(
            [cx * SS - r, cy * SS - r * 0.75, cx * SS + r, cy * SS + r * 0.75],
            fill=(*color, a),
        )
    return layer.resize((w, h), Image.LANCZOS)


def save(img, *parts):
    path = os.path.join(OUT_DIR, *parts)
    _ensure_dir(os.path.dirname(path))
    img.save(path)
    return path


# --------------------------------------------------------------------- naves

def ship_geometry(kind):
    """Poligonos de cada clase de nave (canvas 160x128, morro arriba)."""
    cx = 80.0

    if kind == "scout":
        body = [[(80, 6), (92, 40), (97, 74), (92, 102), (68, 102), (63, 74), (68, 40)]]
        wing_r = [(97, 56), (140, 92), (134, 101), (95, 92)]
        wing_l = _mirror(wing_r, cx)
        fin_r = [(92, 86), (104, 108), (94, 106)]
        fin_l = _mirror(fin_r, cx)
        wings = [wing_r, wing_l, fin_r, fin_l]
        cockpit = [(80, 24), (89, 50), (80, 63), (71, 50)]
        nozzles = [(72, 96, 88, 110, 5)]
        lights = [(137, 96, 3, (255, 110, 110)), (23, 96, 3, (150, 255, 170))]
        lines = [[(68, 52), (92, 52)], [(66, 78), (94, 78)]]

    elif kind == "tank":
        body = [[(80, 12), (96, 32), (105, 58), (108, 94), (96, 112), (64, 112),
                 (52, 94), (55, 58), (64, 32)]]
        wing_r = [(105, 46), (150, 60), (152, 100), (106, 100)]
        wing_l = _mirror(wing_r, cx)
        shoulder_r = [(96, 30), (118, 40), (112, 56), (98, 48)]
        shoulder_l = _mirror(shoulder_r, cx)
        wings = [wing_r, wing_l, shoulder_r, shoulder_l]
        cockpit = [(80, 30), (92, 54), (80, 68), (68, 54)]
        nozzles = [(58, 100, 74, 116, 5), (86, 100, 102, 116, 5)]
        lights = [(148, 66, 3, (255, 110, 110)), (12, 66, 3, (150, 255, 170))]
        lines = [[(58, 60), (102, 60)], [(60, 84), (100, 84)], [(80, 60), (80, 84)]]

    elif kind == "interceptor":
        body = [[(80, 2), (88, 36), (91, 76), (86, 110), (74, 110), (69, 76), (72, 36)]]
        wing_r = [(90, 44), (146, 104), (124, 112), (86, 82)]
        wing_l = _mirror(wing_r, cx)
        canard_r = [(88, 28), (110, 42), (98, 46), (87, 40)]
        canard_l = _mirror(canard_r, cx)
        wings = [wing_r, wing_l, canard_r, canard_l]
        cockpit = [(80, 18), (87, 46), (80, 60), (73, 46)]
        nozzles = [(70, 100, 78, 116, 3), (82, 100, 90, 116, 3)]
        lights = [(136, 104, 3, (255, 110, 110)), (24, 104, 3, (150, 255, 170))]
        lines = [[(72, 54), (88, 54)], [(73, 84), (87, 84)]]

    else:  # bomber
        body = [[(80, 16), (99, 38), (107, 72), (101, 110), (59, 110), (53, 72), (61, 38)]]
        wing_r = [(105, 56), (154, 68), (154, 100), (103, 98)]
        wing_l = _mirror(wing_r, cx)
        wings = [wing_r, wing_l]
        cockpit = [(80, 32), (93, 58), (80, 72), (67, 58)]
        nozzles = [(58, 100, 72, 114, 4), (88, 100, 102, 114, 4),
                   (74, 104, 86, 116, 4)]
        lights = [(150, 82, 3, (255, 110, 110)), (10, 82, 3, (150, 255, 170))]
        lines = [[(58, 64), (102, 64)], [(60, 88), (100, 88)]]

    pods = []
    if kind == "bomber":
        pods = [(112, 70, 138, 96), (22, 70, 48, 96)]

    return {
        "body": body,
        "wings": wings,
        "cockpit": cockpit,
        "nozzles": nozzles,
        "lights": lights,
        "lines": lines,
        "pods": pods,
    }


def build_ship(kind):
    w, h = SHIP_W, SHIP_H
    geo = ship_geometry(kind)

    # ---- capa alas (tintable con wing_color)
    wing_mask = mask_from_shapes(w, h, polys=geo["wings"], ellipses=geo["pods"])
    wing_val = shading_field(w, h, light=(0.30, 0.30), body_falloff=70, bottom_dark=55, spec=35) - 22

    def _wing_ribs(d):
        for off in (0, 10, 20):
            d.line(_sc([(96, 62 + off), (152, 74 + off)]), fill=255, width=SS)
            d.line(_sc([(64, 62 + off), (8, 74 + off)]), fill=255, width=SS)

    wing_val = stamp(wing_val, w, h, _wing_ribs, -26)
    wing_rgba = to_rgba_tintable(wing_val, wing_mask, w, h)

    # ---- capa casco (tintable con body_color)
    body_mask = mask_from_shapes(w, h, polys=geo["body"])
    body_val = shading_field(w, h)

    def _panel_lines(d):
        for line in geo["lines"]:
            d.line(_sc(line), fill=255, width=max(1, SS))

    body_val = stamp(body_val, w, h, _panel_lines, -55)

    def _spine(d):
        d.polygon(_sc([(80, 20), (85, 70), (80, 96), (75, 70)]), fill=255)

    body_val = stamp(body_val, w, h, _spine, 26)
    body_rgba = to_rgba_tintable(body_val, body_mask, w, h)

    # ---- capa detalle (sin tintar)
    detail = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    full_mask = Image.fromarray(
        np.maximum(np.asarray(body_mask, np.uint8), np.asarray(wing_mask, np.uint8)), mode="L"
    )
    detail.alpha_composite(outline_layers(full_mask, w, h))

    # cabina de cristal
    cockpit_mask = mask_from_shapes(w, h, polys=[geo["cockpit"]]).resize((w, h), Image.LANCZOS)
    glass = vertical_gradient_rgba(w, h, (238, 250, 255, 235), (70, 130, 190, 190))
    detail.paste(glass, (0, 0), cockpit_mask)

    cd = ImageDraw.Draw(detail)
    cpx = [p[0] for p in geo["cockpit"]]
    cpy = [p[1] for p in geo["cockpit"]]
    gx0, gy0 = min(cpx), min(cpy)
    gx1, gy1 = max(cpx), max(cpy)
    cd.ellipse([gx0 + 4, gy0 + 3, gx0 + 11, gy0 + 12], fill=(255, 255, 255, 205))
    cd.line([(gx0 + 2, gy1 - 4), (gx1 - 2, gy1 - 4)], fill=(255, 255, 255, 70), width=1)

    # toberas
    for (x0, y0, x1, y1, r) in geo["nozzles"]:
        cd.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(34, 38, 52, 255),
                             outline=(120, 130, 155, 220), width=1)
        cd.rounded_rectangle([x0 + 2, y1 - 6, x1 - 2, y1 - 2], radius=2, fill=(150, 220, 255, 190))
        detail.alpha_composite(
            soft_glow(w, h, (x0 + x1) / 2.0, y1 - 1, (x1 - x0) * 0.8, (150, 220, 255), 150)
        )

    # luces de navegacion
    for (lx, ly, lr, lc) in geo["lights"]:
        detail.alpha_composite(soft_glow(w, h, lx, ly, lr * 3.2, lc, 150))
        cd.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(*lc, 255))
        cd.ellipse([lx - 1, ly - 1, lx + 1, ly + 1], fill=(255, 255, 255, 230))

    return {"body": body_rgba, "wing": wing_rgba, "detail": detail}


# ---------------------------------------------------------------- asteroides

# Cada variante nace de una "familia" de forma distinta para que el campo de
# asteroides se vea variado y no como el mismo bloque repetido con otra rotacion.
ASTEROID_FAMILIES = ("redonda", "alargada", "irregular", "fragmento", "afilada")


def build_asteroid(seed):
    """Genera una roca con forma, iluminacion y densidad de crateres propias
    segun su "familia" (ver ASTEROID_FAMILIES), para que las 14 variantes se
    vean realmente distintas entre si y no como la misma piedra rotada.
    """
    rng = random.Random(seed)
    s = ROCK_SIZE
    centro_x = centro_y = s / 2.0
    radio_base = s * 0.44

    familia = ASTEROID_FAMILIES[seed % len(ASTEROID_FAMILIES)]

    # Cada familia define: cuanto se estira la roca en X/Y, cuanta
    # irregularidad tiene el borde y cuantos vertices/octavas de ruido usa.
    if familia == "alargada":
        estiramiento_x = rng.uniform(1.10, 1.38)
        estiramiento_y = rng.uniform(0.68, 0.88)
        irregularidad, rango_vertices, rango_octavas = 0.08, (12, 16), (3, 4)
    elif familia == "irregular":
        estiramiento_x = rng.uniform(0.92, 1.10)
        estiramiento_y = rng.uniform(0.92, 1.10)
        irregularidad, rango_vertices, rango_octavas = 0.20, (15, 20), (5, 7)
    elif familia == "fragmento":
        estiramiento_x = rng.uniform(0.78, 0.96)
        estiramiento_y = rng.uniform(0.78, 0.96)
        irregularidad, rango_vertices, rango_octavas = 0.24, (9, 13), (3, 4)
    elif familia == "afilada":
        estiramiento_x = rng.uniform(0.95, 1.20)
        estiramiento_y = rng.uniform(0.85, 1.05)
        irregularidad, rango_vertices, rango_octavas = 0.30, (8, 11), (3, 3)
    else:  # redonda
        estiramiento_x = rng.uniform(0.94, 1.06)
        estiramiento_y = rng.uniform(0.94, 1.06)
        irregularidad, rango_vertices, rango_octavas = 0.07, (16, 20), (4, 6)

    # silueta con varias octavas de ruido para que no parezca un poligono regular
    puntos_silueta = []
    num_vertices = rng.randint(*rango_vertices)
    num_octavas = rng.randint(*rango_octavas)
    ruido_grueso = [rng.uniform(0.74, 1.04) for _ in range(num_octavas)]
    for i in range(num_vertices):
        angulo = 2 * math.pi * i / num_vertices
        factor_ruido = ruido_grueso[(i * len(ruido_grueso)) // num_vertices]
        radio_vertice = radio_base * factor_ruido * rng.uniform(1.0 - irregularidad, 1.0 + irregularidad)
        puntos_silueta.append((
            centro_x + math.cos(angulo) * radio_vertice * estiramiento_x,
            centro_y + math.sin(angulo) * radio_vertice * estiramiento_y,
        ))

    mask = mask_from_shapes(s, s, polys=[puntos_silueta])

    # la luz llega desde un angulo distinto en cada variante: evita que todas
    # las rocas del campo parezcan iluminadas por el mismo sol
    angulo_luz = rng.uniform(0, 2 * math.pi)
    luz = (0.5 + 0.24 * math.cos(angulo_luz), 0.5 + 0.24 * math.sin(angulo_luz))
    value = shading_field(
        s, s, light=luz,
        body_falloff=rng.uniform(42, 68),
        bottom_dark=rng.uniform(85, 118),
        spec=rng.uniform(35, 60),
    )

    rango_crateres = {
        "redonda": (6, 9), "alargada": (5, 8), "irregular": (7, 11),
        "fragmento": (3, 6), "afilada": (4, 7),
    }[familia]
    crateres = []
    for _ in range(rng.randint(*rango_crateres)):
        angulo = rng.uniform(0, 2 * math.pi)
        distancia = rng.uniform(0.08, 0.56) * radio_base
        crateres.append((
            centro_x + math.cos(angulo) * distancia * estiramiento_x,
            centro_y + math.sin(angulo) * distancia * estiramiento_y,
            rng.uniform(radio_base * 0.10, radio_base * 0.28),
        ))

    def _craters(d):
        for (crx, cry, cr) in crateres:
            d.ellipse([(crx - cr) * SS, (cry - cr) * SS,
                       (crx + cr) * SS, (cry + cr) * SS], fill=255)

    def _crater_shadow(d):
        for (crx, cry, cr) in crateres:
            off = cr * 0.24
            d.ellipse([(crx - cr + off) * SS, (cry - cr + off) * SS,
                       (crx + cr) * SS, (cry + cr) * SS], fill=255)

    def _crater_rims(d):
        for (crx, cry, cr) in crateres:
            d.arc([(crx - cr) * SS, (cry - cr) * SS, (crx + cr) * SS, (cry + cr) * SS],
                  start=200, end=340, fill=255, width=max(SS, int(cr * 0.28 * SS)))

    def _speckle(d):
        for _ in range(90):
            px = rng.uniform(0, s) * SS
            py = rng.uniform(0, s) * SS
            pr = rng.uniform(0.8, 2.4) * SS
            d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=255)

    def _cracks(d):
        for _ in range(rng.randint(2, 4)):
            angulo = rng.uniform(0, 2 * math.pi)
            px, py = centro_x, centro_y
            trayecto = [(px * SS, py * SS)]
            for _ in range(rng.randint(3, 5)):
                angulo += rng.uniform(-0.7, 0.7)
                paso = rng.uniform(6, 14)
                px += math.cos(angulo) * paso
                py += math.sin(angulo) * paso
                trayecto.append((px * SS, py * SS))
            d.line(trayecto, fill=255, width=SS)

    value = stamp(value, s, s, _craters, -30)
    value = stamp(value, s, s, _crater_shadow, -40)
    value = stamp(value, s, s, _crater_rims, 55)
    value = stamp(value, s, s, _speckle, -22)
    value = stamp(value, s, s, _cracks, -45)

    rock = to_rgba_tintable(value, mask, s, s)
    rock.alpha_composite(outline_layers(mask, s, s, dark_a=150, rim_a=85))
    return rock


# ------------------------------------------------------------ naves enemigas

def enemy_geometry(kind):
    """Enemigos dibujados apuntando hacia ABAJO (miran al jugador)."""
    cx = 64.0

    if kind == "fighter":
        body = [[(64, 122), (78, 88), (82, 52), (72, 26), (56, 26), (46, 52), (50, 88)]]
        wing_r = [(80, 74), (122, 34), (126, 52), (82, 96)]
        wing_l = _mirror(wing_r, cx)
        claw_r = [(78, 96), (96, 118), (80, 112)]
        claw_l = _mirror(claw_r, cx)
        wings = [wing_r, wing_l, claw_r, claw_l]
        eye = [(64, 96), (74, 68), (64, 54), (54, 68)]
        pods = []
        vents = [(56, 22, 72, 34)]
        lights = [(120, 44, 2), (8, 44, 2)]

    elif kind == "drone":
        # platillo: disco ancho (alas) + cupula y panza (casco)
        body = []
        wings = [[(6, 62), (122, 62), (104, 82), (24, 82)]]
        pods = [(4, 56, 124, 80)]
        vents = [(38, 30, 90, 74), (30, 68, 98, 96)]
        eye = [(64, 78), (80, 54), (64, 38), (48, 54)]
        lights = [(18, 70, 3), (40, 78, 3), (64, 81, 3), (88, 78, 3), (110, 70, 3)]

    else:  # gunner
        body = [[(64, 112), (78, 92), (82, 56), (70, 30), (58, 30), (46, 56), (50, 92)]]
        arm_r = [(78, 58), (108, 50), (114, 66), (80, 74)]
        arm_l = _mirror(arm_r, cx)
        cannon_r = [(100, 62), (116, 62), (113, 116), (103, 116)]
        cannon_l = _mirror(cannon_r, cx)
        wings = [arm_r, arm_l, cannon_r, cannon_l]
        eye = [(64, 86), (76, 62), (64, 46), (52, 62)]
        pods = []
        vents = [(54, 26, 74, 40)]
        lights = [(108, 112, 3), (20, 112, 3)]

    return {
        "body": body,
        "wings": wings,
        "eye": eye,
        "pods": pods,
        "vents": vents,
        "lights": lights,
    }


def build_enemy(kind):
    s = ENEMY_SIZE
    geo = enemy_geometry(kind)

    wing_mask = mask_from_shapes(s, s, polys=geo["wings"], ellipses=geo["pods"])
    wing_val = shading_field(s, s, light=(0.32, 0.40), body_falloff=75, bottom_dark=60, spec=45) - 16
    wing_rgba = to_rgba_tintable(wing_val, wing_mask, s, s)

    body_mask = mask_from_shapes(s, s, polys=geo["body"], ellipses=geo["vents"])
    body_val = shading_field(s, s, light=(0.34, 0.34), body_falloff=95, bottom_dark=75, spec=60)

    def _ribs(d):
        for yy in range(40, 110, 12):
            d.line(_sc([(s / 2 - 22, yy), (s / 2 + 22, yy)]), fill=255, width=SS)

    body_val = stamp(body_val, s, s, _ribs, -42)
    body_rgba = to_rgba_tintable(body_val, body_mask, s, s)

    detail = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    full_mask = Image.fromarray(
        np.maximum(np.asarray(body_mask, np.uint8), np.asarray(wing_mask, np.uint8)), mode="L"
    )
    detail.alpha_composite(outline_layers(full_mask, s, s, dark_a=185, rim_a=80))

    eye_mask = mask_from_shapes(s, s, polys=[geo["eye"]]).resize((s, s), Image.LANCZOS)
    eye_grad = vertical_gradient_rgba(s, s, (255, 150, 230, 245), (90, 25, 90, 225))
    detail.paste(eye_grad, (0, 0), eye_mask)

    ex = sum(p[0] for p in geo["eye"]) / len(geo["eye"])
    ey = sum(p[1] for p in geo["eye"]) / len(geo["eye"])
    detail.alpha_composite(soft_glow(s, s, ex, ey, 24, (255, 120, 215), 175))

    dd = ImageDraw.Draw(detail)
    dd.ellipse([ex - 4, min(p[1] for p in geo["eye"]) + 6, ex + 4,
                min(p[1] for p in geo["eye"]) + 18], fill=(255, 245, 255, 235))

    for (lx, ly, lr) in geo.get("lights", []):
        detail.alpha_composite(soft_glow(s, s, lx, ly, lr * 3.4, (140, 255, 220), 150))
        dd.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(190, 255, 240, 255))

    return {"body": body_rgba, "wing": wing_rgba, "detail": detail}


# -------------------------------------------------------------- jefe final

# Geometria de la nodriza (vista desde arriba, como las rocas y enemigos).
# Estas fracciones (relativas a BOSS_W/BOSS_H) las usa tambien modules/systems/
# sprites.py para saber donde va la cupula animada y el anillo de luces sin
# tener que adivinar coordenadas: si cambias esta geometria, actualiza las
# constantes BOSS_* del otro archivo.
BOSS_CENTRO_X, BOSS_CENTRO_Y = BOSS_W / 2.0, BOSS_H / 2.0
BOSS_CASCO_RX, BOSS_CASCO_RY = 104.0, 30.0
BOSS_ANILLO_EXT_RX, BOSS_ANILLO_EXT_RY = 148.0, 44.0
BOSS_ANILLO_INT_RX, BOSS_ANILLO_INT_RY = 106.0, 29.0
BOSS_NUM_NODOS = 14
BOSS_NODO_RX = (BOSS_ANILLO_EXT_RX + BOSS_ANILLO_INT_RX) / 2.0
BOSS_NODO_RY = (BOSS_ANILLO_EXT_RY + BOSS_ANILLO_INT_RY) / 2.0
BOSS_PLATAFORMA_RX, BOSS_PLATAFORMA_RY = 44.0, 15.0
BOSS_PLATAFORMA_CY = BOSS_CENTRO_Y - 36.0


def _caja_elipse(radio_x, radio_y, cx=BOSS_CENTRO_X, cy=BOSS_CENTRO_Y):
    """Bounding box (x0, y0, x1, y1) de una elipse centrada en (cx, cy)."""
    return (cx - radio_x, cy - radio_y, cx + radio_x, cy + radio_y)


def _puntos_de_caja(caja):
    """Convierte (x0, y0, x1, y1) en los dos puntos que espera ImageDraw."""
    x0, y0, x1, y1 = caja
    return [(x0, y0), (x1, y1)]


# Tipos de nave nodriza. Los tres comparten el anillo de nodos y la
# plataforma de la cupula (misma posicion/tamaño en los tres) porque
# boss.py y boss_system.py ubican encima, en tiempo real, la cupula
# animada, el piloto y las luces parpadeantes usando esas coordenadas fijas
# (ver BOSS_* en modules/systems/sprites.py). Lo que cambia por tipo es la
# silueta del casco central y sus detalles/remaches, para que cada jefe se
# sienta como una nave alienigena distinta.
BOSS_KINDS = ("saucer", "dragon", "titan")


def _silueta_casco(kind, rx, ry, cx=BOSS_CENTRO_X, cy=BOSS_CENTRO_Y):
    """Poligono del casco central segun el tipo de jefe, inscripto en la
    misma caja (rx, ry) que antes ocupaba la elipse original. None = elipse
    (silueta clasica de platillo, usada por "saucer")."""
    if kind == "dragon":
        # casco alargado tipo "huso" con la nariz afilada hacia la derecha,
        # como una nave-dragon serpenteante.
        return [
            (cx - rx, cy),
            (cx - rx * 0.5, cy - ry),
            (cx + rx * 0.15, cy - ry * 0.75),
            (cx + rx * 0.7, cy - ry * 0.45),
            (cx + rx, cy - ry * 0.08),
            (cx + rx, cy + ry * 0.08),
            (cx + rx * 0.7, cy + ry * 0.45),
            (cx + rx * 0.15, cy + ry * 0.75),
            (cx - rx * 0.5, cy + ry),
        ]
    if kind == "titan":
        # casco hexagonal, macizo y blindado, como una fortaleza voladora.
        return [
            (cx - rx, cy),
            (cx - rx * 0.55, cy - ry),
            (cx + rx * 0.55, cy - ry),
            (cx + rx, cy),
            (cx + rx * 0.55, cy + ry),
            (cx - rx * 0.55, cy + ry),
        ]
    return None


def _paneles_casco(kind, cx, cy, rx, ry):
    """Devuelve la funcion de dibujo (para stamp()) con las lineas de
    blindaje propias de cada tipo de casco."""
    if kind == "dragon":
        def _dibujar(d):
            for i in range(-3, 4):
                x0 = cx + i * rx * 0.26
                d.line(_sc([(x0, cy - ry * 0.95), (x0 - rx * 0.35, cy + ry * 0.95)]), fill=255, width=SS)
            d.line(_sc([(cx - rx * 0.95, cy), (cx + rx * 0.95, cy)]), fill=255, width=int(SS * 1.5))
        return _dibujar
    if kind == "titan":
        def _dibujar(d):
            for factor in (0.92, 0.6):
                pts = [
                    (cx - rx * factor, cy),
                    (cx - rx * 0.55 * factor, cy - ry * factor),
                    (cx + rx * 0.55 * factor, cy - ry * factor),
                    (cx + rx * factor, cy),
                    (cx + rx * 0.55 * factor, cy + ry * factor),
                    (cx - rx * 0.55 * factor, cy + ry * factor),
                ]
                d.polygon(_sc(pts), outline=255, width=SS)
        return _dibujar

    def _dibujar(d):
        # tres anillos concentricos mas pequeños, como lineas de blindaje
        for nivel in (1, 2, 3):
            factor = 1.0 - 0.24 * nivel
            caja = _caja_elipse(rx * factor, ry * factor, cx, cy)
            d.ellipse(_sc(_puntos_de_caja(caja)), outline=255, width=SS)
    return _dibujar


def _remaches_casco(kind, cx, cy, rx, ry):
    n, radio_factor, radio_remache = (14, 0.85, 2.6) if kind == "titan" else (10, 0.8, 2.2)

    def _dibujar(d):
        for i in range(n):
            angulo = 2 * math.pi * i / n
            remache_x = cx + math.cos(angulo) * rx * radio_factor
            remache_y = cy + math.sin(angulo) * ry * radio_factor
            d.ellipse(_sc([(remache_x - radio_remache, remache_y - radio_remache),
                           (remache_x + radio_remache, remache_y + radio_remache)]), fill=255)
    return _dibujar


def _detalle_extra_casco(kind, detalle, dibujo_detalle, cx, cy, rx, ry):
    """Adornos de color fijo (no se tiñen con el color del jefe) que le dan
    caracter de nave alienigena propia a cada tipo: colmillos y ojo
    luminoso para el dragon, remaches reforzados en las esquinas del titan."""
    if kind == "dragon":
        colmillos = [
            [(cx + rx * 0.72, cy - ry * 0.18), (cx + rx * 1.02, cy - ry * 0.02), (cx + rx * 0.78, cy + ry * 0.02)],
            [(cx + rx * 0.72, cy + ry * 0.18), (cx + rx * 1.02, cy + ry * 0.02), (cx + rx * 0.78, cy - ry * 0.02)],
        ]
        for colmillo in colmillos:
            dibujo_detalle.polygon(colmillo, fill=(235, 225, 210, 255), outline=(40, 20, 20, 255))
        ojo_x, ojo_y = cx + rx * 0.35, cy
        detalle.alpha_composite(soft_glow(BOSS_W, BOSS_H, ojo_x, ojo_y, 16, (255, 90, 40), 170))
        dibujo_detalle.ellipse([ojo_x - 5, ojo_y - 3, ojo_x + 5, ojo_y + 3], fill=(255, 150, 70, 255))
        dibujo_detalle.ellipse([ojo_x - 1.6, ojo_y - 1.2, ojo_x + 1.6, ojo_y + 1.2], fill=(255, 240, 220, 255))
    elif kind == "titan":
        for signo in (-1, 1):
            esquina_x = cx + signo * rx * 0.55
            for esquina_y in (cy - ry * 0.85, cy + ry * 0.85):
                dibujo_detalle.rectangle(
                    [esquina_x - 6, esquina_y - 6, esquina_x + 6, esquina_y + 6],
                    fill=(60, 60, 74, 255), outline=(20, 20, 30, 255),
                )
                dibujo_detalle.ellipse(
                    [esquina_x - 2.4, esquina_y - 2.4, esquina_x + 2.4, esquina_y + 2.4],
                    fill=(195, 195, 210, 230),
                )


def build_boss(kind="saucer"):
    """Nave nodriza extraterrestre: anillo exterior + casco central +
    plataforma de la cupula. La cupula de cristal, el piloto y las luces
    parpadeantes siguen dibujandose en tiempo real (boss.py /
    boss_system.py) porque cambian de color segun la fase de la pelea; el
    sprite aporta el volumen, la silueta y el detalle fijo.

    kind: "saucer" (platillo clasico, jefe Centinela y Anomalia Final),
    "dragon" (casco alargado y colmillos, jefe Dragon Espacial) o "titan"
    (casco hexagonal blindado, jefe Titan del Vacio).
    """
    w, h = BOSS_W, BOSS_H
    cx, cy = BOSS_CENTRO_X, BOSS_CENTRO_Y

    # ---- anillo exterior (tintable con el color secundario -> "wing")
    # Identico en los tres tipos: aqui es donde el juego dibuja el anillo de
    # luces parpadeantes, asi que su posicion no puede variar por tipo.
    mascara_anillo = _blank_mask(w, h)
    dibujo_anillo = ImageDraw.Draw(mascara_anillo)
    dibujo_anillo.ellipse(_sc(_puntos_de_caja(_caja_elipse(BOSS_ANILLO_EXT_RX, BOSS_ANILLO_EXT_RY))), fill=255)
    dibujo_anillo.ellipse(_sc(_puntos_de_caja(_caja_elipse(BOSS_ANILLO_INT_RX, BOSS_ANILLO_INT_RY))), fill=0)
    for i in range(BOSS_NUM_NODOS):
        angulo = 2 * math.pi * i / BOSS_NUM_NODOS
        nodo_x = cx + math.cos(angulo) * BOSS_NODO_RX
        nodo_y = cy + math.sin(angulo) * BOSS_NODO_RY
        dibujo_anillo.ellipse(_sc(_puntos_de_caja((nodo_x - 8, nodo_y - 8, nodo_x + 8, nodo_y + 8))), fill=255)

    valor_anillo = shading_field(w, h, light=(0.30, 0.14), body_falloff=60, bottom_dark=95, spec=55)

    def _paneles_anillo(d):
        # lineas radiales entre nodos, como las juntas de una estructura metalica
        for i in range(BOSS_NUM_NODOS):
            angulo = 2 * math.pi * (i + 0.5) / BOSS_NUM_NODOS
            x0 = cx + math.cos(angulo) * BOSS_ANILLO_INT_RX * 1.02
            y0 = cy + math.sin(angulo) * BOSS_ANILLO_INT_RY * 1.02
            x1 = cx + math.cos(angulo) * BOSS_ANILLO_EXT_RX * 0.99
            y1 = cy + math.sin(angulo) * BOSS_ANILLO_EXT_RY * 0.99
            d.line(_sc([(x0, y0), (x1, y1)]), fill=255, width=SS)

    valor_anillo = stamp(valor_anillo, w, h, _paneles_anillo, -38)
    anillo_rgba = to_rgba_tintable(valor_anillo, mascara_anillo, w, h)

    # ---- casco central (tintable con el color principal -> "body")
    silueta = _silueta_casco(kind, BOSS_CASCO_RX, BOSS_CASCO_RY)
    if silueta is not None:
        mascara_casco = mask_from_shapes(w, h, polys=[silueta])
    else:
        mascara_casco = mask_from_shapes(w, h, ellipses=[_caja_elipse(BOSS_CASCO_RX, BOSS_CASCO_RY)])

    luz_por_tipo = {
        "dragon": (0.30, 0.20),
        "titan": (0.36, 0.18),
    }.get(kind, (0.34, 0.16))
    valor_casco = shading_field(w, h, light=luz_por_tipo, body_falloff=88, bottom_dark=100, spec=62)
    valor_casco = stamp(valor_casco, w, h, _paneles_casco(kind, cx, cy, BOSS_CASCO_RX, BOSS_CASCO_RY), -28)
    valor_casco = stamp(valor_casco, w, h, _remaches_casco(kind, cx, cy, BOSS_CASCO_RX, BOSS_CASCO_RY), 45)
    casco_rgba = to_rgba_tintable(valor_casco, mascara_casco, w, h)

    # ---- detalle (sin tintar): contorno, remaches con brillo, plataforma
    detalle = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mascara_completa = Image.fromarray(
        np.maximum(np.asarray(mascara_casco, np.uint8), np.asarray(mascara_anillo, np.uint8)), mode="L"
    )
    detalle.alpha_composite(outline_layers(mascara_completa, w, h, dark_a=185, rim_a=95))

    dibujo_detalle = ImageDraw.Draw(detalle)
    caja_plataforma = (
        cx - BOSS_PLATAFORMA_RX, BOSS_PLATAFORMA_CY - BOSS_PLATAFORMA_RY,
        cx + BOSS_PLATAFORMA_RX, BOSS_PLATAFORMA_CY + BOSS_PLATAFORMA_RY,
    )
    dibujo_detalle.ellipse(caja_plataforma, fill=(66, 66, 82, 255))
    dibujo_detalle.ellipse(caja_plataforma, outline=(18, 18, 28, 255), width=2)
    detalle.alpha_composite(
        soft_glow(w, h, cx, BOSS_PLATAFORMA_CY, BOSS_PLATAFORMA_RX * 1.3, (120, 220, 255), 90)
    )

    for i in range(BOSS_NUM_NODOS):
        angulo = 2 * math.pi * i / BOSS_NUM_NODOS
        nodo_x = cx + math.cos(angulo) * BOSS_NODO_RX
        nodo_y = cy + math.sin(angulo) * BOSS_NODO_RY
        detalle.alpha_composite(soft_glow(w, h, nodo_x, nodo_y, 11, (255, 255, 255), 55))
        dibujo_detalle.ellipse([nodo_x - 3.4, nodo_y - 3.4, nodo_x + 3.4, nodo_y + 3.4], fill=(35, 35, 48, 255))
        dibujo_detalle.ellipse([nodo_x - 1.3, nodo_y - 1.3, nodo_x + 1.3, nodo_y + 1.3], fill=(210, 230, 255, 200))

    _detalle_extra_casco(kind, detalle, dibujo_detalle, cx, cy, BOSS_CASCO_RX, BOSS_CASCO_RY)

    return {"body": casco_rgba, "wing": anillo_rgba, "detail": detalle}


# --------------------------------------------------------------- power-ups

# Cada bonus se ve como una capsula/caja metalica tipo recreativa de los 90
# (piensa en las cajas de armas de Metal Slug): un cuerpo solido con
# remaches y una tapa brillante, tintado en tiempo real con el color propio
# del bonus, y grabado encima con un icono blanco de trazo grueso y borde
# oscuro para que se lea igual sin importar el color de la capsula.
POWERUP_SIZE = 96

POWERUP_KINDS = (
    "extra_life", "fast_shoot", "triple_shot", "shield", "piercing", "attract",
    "damage_up", "speed_up", "max_life_up", "rapid_fire", "lightning_field",
)


def build_powerup_body():
    """Cuerpo tintable de la capsula: comun a los 10 tipos de bonus."""
    s = POWERUP_SIZE
    cx = cy = s / 2.0
    r = s * 0.40

    mascara = mask_from_shapes(s, s, rrects=[(cx - r, cy - r, cx + r, cy + r, r * 0.30)])
    valor = shading_field(s, s, light=(0.32, 0.22), body_falloff=75, bottom_dark=95, spec=70)

    def _tapa(d):
        d.rounded_rectangle(
            [(cx - r * 0.76) * SS, (cy - r * 0.76) * SS, (cx + r * 0.76) * SS, (cy - r * 0.10) * SS],
            radius=r * 0.22 * SS, fill=255,
        )
    valor = stamp(valor, s, s, _tapa, 32)

    def _remaches(d):
        for signo_x in (-1, 1):
            for signo_y in (-1, 1):
                rx = cx + signo_x * r * 0.64
                ry = cy + signo_y * r * 0.64
                d.ellipse([(rx - 3.2) * SS, (ry - 3.2) * SS, (rx + 3.2) * SS, (ry + 3.2) * SS], fill=255)
    valor = stamp(valor, s, s, _remaches, -35)

    return to_rgba_tintable(valor, mascara, s, s), mascara


def _icono_powerup(kind, d, cx, cy, r):
    """Dibuja el simbolo grabado de cada bonus. Blanco solido con contorno
    oscuro fino, para que se lea igual sobre cualquier color de capsula."""
    blanco = (255, 255, 255, 255)
    borde = (30, 22, 18, 255)
    w = max(2, int(r * 0.14))

    if kind == "extra_life":
        d.polygon([
            (cx, cy + r * 0.55), (cx - r * 0.62, cy - r * 0.05), (cx - r * 0.62, cy - r * 0.35),
            (cx - r * 0.32, cy - r * 0.58), (cx, cy - r * 0.30), (cx + r * 0.32, cy - r * 0.58),
            (cx + r * 0.62, cy - r * 0.35), (cx + r * 0.62, cy - r * 0.05),
        ], fill=blanco, outline=borde, width=w)

    elif kind == "fast_shoot" or kind == "rapid_fire":
        def _rayo(off_x):
            pts = [
                (cx + off_x, cy - r * 0.62), (cx + off_x + r * 0.18, cy - r * 0.08),
                (cx + off_x - r * 0.06, cy - r * 0.08), (cx + off_x + r * 0.1, cy + r * 0.62),
                (cx + off_x - r * 0.28, cy + r * 0.02), (cx + off_x + r * 0.02, cy + r * 0.02),
            ]
            d.polygon(pts, fill=blanco, outline=borde, width=w)
        if kind == "rapid_fire":
            _rayo(-r * 0.22)
            _rayo(r * 0.22)
        else:
            _rayo(0)

    elif kind == "triple_shot":
        # tres balas en abanico (disparo triple/spread)
        for ang in (-30, 0, 30):
            rad = math.radians(ang - 90)
            dx, dy = math.cos(rad), math.sin(rad)
            nx, ny = -dy, dx
            px = cx + dx * r * 0.42
            py = cy + dy * r * 0.42
            largo, ancho = r * 0.38, r * 0.17
            d.polygon([
                (px + dx * largo, py + dy * largo),
                (px + nx * ancho, py + ny * ancho),
                (px - dx * largo * 0.5, py - dy * largo * 0.5),
                (px - nx * ancho, py - ny * ancho),
            ], fill=blanco, outline=borde, width=w)

    elif kind == "shield":
        pts = [
            (cx, cy - r * 0.65), (cx + r * 0.55, cy - r * 0.35), (cx + r * 0.55, cy + r * 0.15),
            (cx, cy + r * 0.65), (cx - r * 0.55, cy + r * 0.15), (cx - r * 0.55, cy - r * 0.35),
        ]
        d.polygon(pts, fill=blanco, outline=borde, width=w)
        pts_in = [
            (cx, cy - r * 0.35), (cx + r * 0.28, cy - r * 0.18), (cx + r * 0.28, cy + r * 0.08),
            (cx, cy + r * 0.35), (cx - r * 0.28, cy + r * 0.08), (cx - r * 0.28, cy - r * 0.18),
        ]
        d.polygon(pts_in, fill=borde)

    elif kind == "piercing":
        # flecha atravesando un anillo: "perfora" el objetivo
        d.ellipse([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], outline=blanco, width=w)
        d.line([(cx - r * 0.7, cy), (cx + r * 0.4, cy)], fill=blanco, width=int(w * 1.8))
        d.polygon([
            (cx + r * 0.15, cy - r * 0.4), (cx + r * 0.75, cy), (cx + r * 0.15, cy + r * 0.4),
        ], fill=blanco, outline=borde, width=w)

    elif kind == "attract":
        d.arc([cx - r * 0.5, cy - r * 0.55, cx + r * 0.5, cy + r * 0.45], start=200, end=340,
              fill=blanco, width=w * 2)
        for signo in (-1, 1):
            px = cx + signo * r * 0.5
            d.rectangle([px - r * 0.14, cy - r * 0.05, px + r * 0.14, cy + r * 0.5], fill=blanco)
            d.rectangle([px - r * 0.14, cy + r * 0.28, px + r * 0.14, cy + r * 0.5],
                        fill=(210, 60, 60, 255))
            d.rectangle([px - r * 0.14, cy - r * 0.05, px + r * 0.14, cy + r * 0.5],
                        outline=borde, width=max(1, w // 2))

    elif kind == "damage_up":
        # espada: hoja apuntando arriba, cruz y mango abajo (icono de "ataque")
        d.polygon([
            (cx, cy - r * 0.78), (cx + r * 0.15, cy - r * 0.52), (cx + r * 0.15, cy + r * 0.14),
            (cx - r * 0.15, cy + r * 0.14), (cx - r * 0.15, cy - r * 0.52),
        ], fill=blanco, outline=borde, width=w)
        d.line([(cx - r * 0.42, cy + r * 0.2), (cx + r * 0.42, cy + r * 0.2)], fill=blanco, width=w)
        d.rectangle([cx - r * 0.09, cy + r * 0.2, cx + r * 0.09, cy + r * 0.66],
                    fill=blanco, outline=borde, width=max(1, w // 2))

    elif kind == "speed_up":
        # doble flecha hacia adelante (avance rapido, como el boton >> )
        for off in (-r * 0.24, r * 0.24):
            d.polygon([
                (cx - r * 0.55, cy + off - r * 0.26), (cx + r * 0.2, cy + off),
                (cx - r * 0.55, cy + off + r * 0.26),
            ], fill=blanco, outline=borde, width=w)

    elif kind == "max_life_up":
        _icono_powerup("extra_life", d, cx, cy - r * 0.08, r * 0.8)
        d.line([(cx + r * 0.55, cy - r * 0.62), (cx + r * 0.55, cy - r * 0.26)], fill=blanco, width=w * 2)
        d.line([(cx + r * 0.37, cy - r * 0.44), (cx + r * 0.73, cy - r * 0.44)], fill=blanco, width=w * 2)

    elif kind == "lightning_field":
        # anillo de "campo/aura" con un rayo grueso en el centro: se
        # distingue del rayo simple (fast_shoot) y el rayo doble (rapid_fire)
        d.ellipse([cx - r * 0.68, cy - r * 0.68, cx + r * 0.68, cy + r * 0.68], outline=blanco, width=w)
        for ang in (40, 140, 220, 320):
            rad = math.radians(ang)
            x0 = cx + math.cos(rad) * r * 0.68
            y0 = cy + math.sin(rad) * r * 0.68
            x1 = cx + math.cos(rad) * r * 0.86
            y1 = cy + math.sin(rad) * r * 0.86
            d.line([(x0, y0), (x1, y1)], fill=blanco, width=w)
        d.polygon([
            (cx + r * 0.1, cy - r * 0.5), (cx - r * 0.15, cy - r * 0.02), (cx + r * 0.08, cy - r * 0.02),
            (cx - r * 0.1, cy + r * 0.5), (cx + r * 0.18, cy + r * 0.05), (cx - r * 0.03, cy + r * 0.05),
        ], fill=blanco, outline=borde, width=max(1, w // 2))

    else:
        d.ellipse([cx - r * 0.4, cy - r * 0.4, cx + r * 0.4, cy + r * 0.4], fill=blanco, outline=borde, width=w)


def build_powerup_detail(kind, mascara_cuerpo):
    """Capa sin tintar: contorno del casco + icono grabado del tipo de bonus."""
    s = POWERUP_SIZE
    cx = cy = s / 2.0
    r = s * 0.40

    detalle = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    detalle.alpha_composite(outline_layers(mascara_cuerpo, s, s, dark_a=195, rim_a=100))

    d = ImageDraw.Draw(detalle)
    _icono_powerup(kind, d, cx, cy - r * 0.06, r * 0.85)

    return detalle


def build_powerup(kind, cuerpo_compartido):
    body_rgba, mascara = cuerpo_compartido
    detail = build_powerup_detail(kind, mascara)
    return {"body": body_rgba, "detail": detail}


# ----------------------------------------------------------------- ejecucion

SHIP_KINDS = ["scout", "tank", "interceptor", "bomber"]
ENEMY_KINDS = ["fighter", "drone", "gunner"]
ASTEROID_VARIANTS = 14


def generate_all(verbose=True):
    _ensure_dir(OUT_DIR)
    written = []

    for kind in SHIP_KINDS:
        layers = build_ship(kind)
        for layer_name, img in layers.items():
            written.append(save(img, "ships", f"{kind}_{layer_name}.png"))

    for i in range(ASTEROID_VARIANTS):
        written.append(save(build_asteroid(1000 + i), "asteroids", f"asteroid_{i}.png"))

    for kind in ENEMY_KINDS:
        layers = build_enemy(kind)
        for layer_name, img in layers.items():
            written.append(save(img, "enemies", f"{kind}_{layer_name}.png"))

    # "saucer" se guarda como "mothership" por compatibilidad: es el sprite
    # que ya usaba el jefe final (La Anomalia Final) y el Centinela Corrupto
    # lo reutiliza tambien (ver BOSS_SPRITE_PREFIX en modules/systems/sprites.py).
    BOSS_FILE_PREFIX = {"saucer": "mothership", "dragon": "dragon", "titan": "titan"}
    for kind in BOSS_KINDS:
        boss_layers = build_boss(kind)
        prefix = BOSS_FILE_PREFIX[kind]
        for layer_name, img in boss_layers.items():
            written.append(save(img, "boss", f"{prefix}_{layer_name}.png"))

    cuerpo_powerup = build_powerup_body()
    for kind in POWERUP_KINDS:
        powerup_layers = build_powerup(kind, cuerpo_powerup)
        for layer_name, img in powerup_layers.items():
            written.append(save(img, "powerups", f"{kind}_{layer_name}.png"))

    if verbose:
        print(f"{len(written)} sprites generados en {OUT_DIR}")
    return written


if __name__ == "__main__":
    generate_all()
