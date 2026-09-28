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


def _seed_de(texto):
    """Semilla entera estable a partir de texto (hash() de str varia entre
    procesos por PYTHONHASHSEED; esto no)."""
    total = 0
    for i, c in enumerate(str(texto)):
        total = (total * 131 + ord(c) + i) & 0xffffffff
    return total


def grain_noise(w, h, seed, octaves=((8, 14), (20, 8), (48, 4))):
    """Ruido de valor multi-octava (grillas aleatorias chicas + reescalado
    bicubico, sumadas) en la misma resolucion SS que el resto de las
    capas de sombreado: da textura de superficie real -grano de roca,
    moteado organico- en vez de un relleno perfectamente liso. Cada
    octava es (celdas, amplitud); mas celdas = grano mas fino."""
    rng = np.random.default_rng(seed)
    W, H = w * SS, h * SS
    total = np.zeros((H, W), dtype=np.float32)
    for cells, amp in octaves:
        celda = rng.uniform(-1.0, 1.0, size=(cells, cells)).astype(np.float32)
        img = Image.fromarray(((celda * 0.5 + 0.5) * 255).astype(np.uint8), mode="L").resize((W, H), Image.BICUBIC)
        arr = (np.asarray(img, dtype=np.float32) / 255.0 - 0.5) * 2 * amp
        total += arr
    return total


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
    wing_val = wing_val + grain_noise(w, h, _seed_de(f"wing-{kind}"), octaves=((12, 5), (28, 2.5)))

    def _wing_ribs(d):
        for off in (0, 10, 20):
            d.line(_sc([(96, 62 + off), (152, 74 + off)]), fill=255, width=SS)
            d.line(_sc([(64, 62 + off), (8, 74 + off)]), fill=255, width=SS)

    wing_val = stamp(wing_val, w, h, _wing_ribs, -26)
    wing_rgba = to_rgba_tintable(wing_val, wing_mask, w, h)

    # ---- capa casco (tintable con body_color)
    body_mask = mask_from_shapes(w, h, polys=geo["body"])
    body_val = shading_field(w, h)
    body_val = body_val + grain_noise(w, h, _seed_de(f"ship-{kind}"), octaves=((12, 5), (28, 2.5)))

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
                  start=195, end=345, fill=255, width=max(SS, int(cr * 0.24 * SS)))

    def _crater_rims_finos(d):
        # segundo anillo, mas fino y mas cerca del borde interior: remata
        # el labio del crater para que no se lea como un circulo plano
        # con un solo tono de relleno.
        for (crx, cry, cr) in crateres:
            d.arc([(crx - cr) * SS, (cry - cr) * SS, (crx + cr) * SS, (cry + cr) * SS],
                  start=15, end=165, fill=255, width=max(SS, int(cr * 0.12 * SS)))

    def _speckle(d):
        for _ in range(90):
            px = rng.uniform(0, s) * SS
            py = rng.uniform(0, s) * SS
            pr = rng.uniform(0.8, 2.4) * SS
            d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=255)

    def _mineral_flecos(d):
        # motas brillantes puntuales (vetas de mineral reflejando luz),
        # distintas del moteado oscuro de _speckle.
        for _ in range(22):
            px = rng.uniform(0, s) * SS
            py = rng.uniform(0, s) * SS
            pr = rng.uniform(0.6, 1.4) * SS
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

    # grano de roca real (multi-octava) ANTES de los crateres: asi el
    # relleno deja de ser un degrade perfectamente liso incluso en zonas
    # sin crater, y el moteado/grietas de encima quedan mejor integrados.
    value = value + grain_noise(s, s, seed, octaves=((7, 11), (17, 7), (44, 3.5)))

    value = stamp(value, s, s, _craters, -34)
    value = stamp(value, s, s, _crater_shadow, -68)
    value = stamp(value, s, s, _crater_rims, 78)
    value = stamp(value, s, s, _crater_rims_finos, -50)
    value = stamp(value, s, s, _speckle, -22)
    value = stamp(value, s, s, _mineral_flecos, 60)
    value = stamp(value, s, s, _cracks, -50)

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
    wing_val = wing_val + grain_noise(s, s, _seed_de(f"ewing-{kind}"), octaves=((12, 5), (28, 2.5)))
    wing_rgba = to_rgba_tintable(wing_val, wing_mask, s, s)

    body_mask = mask_from_shapes(s, s, polys=geo["body"], ellipses=geo["vents"])
    body_val = shading_field(s, s, light=(0.34, 0.34), body_falloff=95, bottom_dark=75, spec=60)
    body_val = body_val + grain_noise(s, s, _seed_de(f"ebody-{kind}"), octaves=((12, 5), (28, 2.5)))

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

# Titan (pulpo mecanico) no comparte el anillo/cupula de los demas (ver
# build_boss), asi que su casco puede ser mas grande sin invadir esa
# geometria: se infla la caja rx/ry solo para el, para que se sienta mas
# imponente que un jefe de oleada comun. Ademas titan_boss.py vuelve a
# escalar el sprite ya compuesto (ver TITAN_DISPLAY_SCALE en
# modules/systems/sprites.py) para que en pantalla se vea claramente mas
# grande que saucer/dragon/anomaly.
TITAN_RX_SCALE = 1.28
TITAN_RY_SCALE = 1.45
TITAN_CASCO_RX = BOSS_CASCO_RX * TITAN_RX_SCALE
TITAN_CASCO_RY = BOSS_CASCO_RY * TITAN_RY_SCALE

# Ojo mecanico central: posicion/radio fijos (fraccion de BOSS_W/BOSS_H)
# para que modules/systems/sprites.py y titan_boss.py sepan donde dibujar
# la pupila que sigue al jugador en tiempo real sin tener que adivinar
# coordenadas (mismo criterio que BOSS_PLATAFORMA_*). El PNG solo trae el
# aro/iris mecanico fijo: la pupila en si no se hornea, es 100% dinamica.
TITAN_OJO_CX = BOSS_CENTRO_X
TITAN_OJO_CY = BOSS_CENTRO_Y - TITAN_CASCO_RY * 0.22
TITAN_OJO_R = 26.0

# Anomaly (calavera glicheada) tampoco comparte el anillo/cupula: su caja
# tambien se infla, pero mas alta que ancha (una calavera, no un platillo)
# en vez de mas ancha como Titan. La caja no puede pasarse de la mitad de
# BOSS_H (85px) o se recorta contra el borde del canvas.
ANOMALY_RX_SCALE = 0.88
ANOMALY_RY_SCALE = 2.0
ANOMALY_CASCO_RX = BOSS_CASCO_RX * ANOMALY_RX_SCALE
ANOMALY_CASCO_RY = BOSS_CASCO_RY * ANOMALY_RY_SCALE

# Dos ojos (no uno solo como Titan): posicion/radio fijos para que
# modules/systems/sprites.py y boss.py sepan donde dibujar las pupilas que
# siguen a la nave en tiempo real. Las cuencas ya vienen horneadas en el
# PNG (oscuras, vacias); la pupila es 100% dinamica.
ANOMALY_OJO_DX = ANOMALY_CASCO_RX * 0.40      # offset horizontal desde el centro, cada ojo
ANOMALY_OJO_CY = BOSS_CENTRO_Y - ANOMALY_CASCO_RY * 0.05
ANOMALY_OJO_R = ANOMALY_CASCO_RY * 0.32


def _caja_elipse(radio_x, radio_y, cx=BOSS_CENTRO_X, cy=BOSS_CENTRO_Y):
    """Bounding box (x0, y0, x1, y1) de una elipse centrada en (cx, cy)."""
    return (cx - radio_x, cy - radio_y, cx + radio_x, cy + radio_y)


def _puntos_de_caja(caja):
    """Convierte (x0, y0, x1, y1) en los dos puntos que espera ImageDraw."""
    x0, y0, x1, y1 = caja
    return [(x0, y0), (x1, y1)]


# Tipos de nave nodriza. Los cuatro comparten el anillo de nodos y la
# plataforma de la cupula (misma posicion/tamaño en los cuatro) porque
# boss.py y boss_system.py ubican encima, en tiempo real, la cupula
# animada, el piloto y las luces parpadeantes usando esas coordenadas fijas
# (ver BOSS_* en modules/systems/sprites.py). Lo que cambia por tipo es la
# silueta del casco central y sus detalles/remaches, para que cada jefe se
# sienta como una nave alienigena distinta. "anomaly" (La Anomalia Final,
# oleada 20) tenia la misma silueta que "saucer" (el Centinela); ahora tiene
# la suya propia -fracturada, con un nucleo de vacio pulsante- para que se
# note que es un jefe aparte y no una reskin del Centinela.
BOSS_KINDS = ("saucer", "dragon", "titan", "anomaly")


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
        # manto de pulpo mecanico visto desde arriba: cresta angular y
        # blindada arriba (nada de domo liso "tierno" - placas rectas que
        # se cierran en punta al centro, como una cresta de guerra),
        # hombros/pauldrones redondeados y bien anchos a los costados
        # -mas fisico y corpulento, no una cresta flaca- y anclajes en
        # garra abajo para los tentaculos (que se dibujan en tiempo real
        # en titan_boss.py -oscilando/atacando- via sprites propios, no
        # pueden ser parte de este PNG fijo).
        pts = [
            (cx - rx * 1.0, cy - ry * 0.02),
            (cx - rx * 0.90, cy - ry * 0.60),
            (cx - rx * 0.66, cy - ry * 1.0),
            (cx - rx * 0.24, cy - ry * 1.18),
            (cx, cy - ry * 1.38),
            (cx + rx * 0.24, cy - ry * 1.18),
            (cx + rx * 0.66, cy - ry * 1.0),
            (cx + rx * 0.90, cy - ry * 0.60),
            (cx + rx * 1.0, cy - ry * 0.02),
            # pauldron derecho: bulto redondeado que sobresale del casco
            # antes de bajar hacia las garras - le da hombros de verdad.
            (cx + rx * 1.16, cy + ry * 0.16),
            (cx + rx * 1.08, cy + ry * 0.40),
            (cx + rx * 0.86, cy + ry * 0.46),
        ]
        n_anclajes = 5
        for i in range(n_anclajes):
            t = i / (n_anclajes - 1)
            x = cx + rx * 0.80 * (1.0 - 2.0 * t)
            y = cy + ry * (1.28 if i % 2 == 0 else 0.55)
            pts.append((x, y))
        pts += [
            (cx - rx * 0.86, cy + ry * 0.46),
            (cx - rx * 1.08, cy + ry * 0.40),
            (cx - rx * 1.16, cy + ry * 0.16),
        ]
        return pts
    if kind == "anomaly":
        # calavera de frente, no una nave vista desde arriba: craneo
        # redondeado arriba, sienes anchas, pomulos y quijada quebrados en
        # punta (nada de curvas humanas suaves - hasta la silueta esta
        # "glicheada"/fracturada, no solo el casco de las otras tres).
        return [
            (cx, cy - ry * 1.0),
            (cx + rx * 0.55, cy - ry * 0.85),
            (cx + rx * 0.92, cy - ry * 0.45),
            (cx + rx * 0.85, cy - ry * 0.05),
            (cx + rx * 0.97, cy + ry * 0.25),
            (cx + rx * 0.55, cy + ry * 0.35),
            (cx + rx * 0.35, cy + ry * 0.75),
            (cx, cy + ry * 1.0),
            (cx - rx * 0.35, cy + ry * 0.75),
            (cx - rx * 0.55, cy + ry * 0.35),
            (cx - rx * 0.97, cy + ry * 0.25),
            (cx - rx * 0.85, cy - ry * 0.05),
            (cx - rx * 0.92, cy - ry * 0.45),
            (cx - rx * 0.55, cy - ry * 0.85),
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
            # placas blindadas angulares en V (como un peto de armadura,
            # no pliegues organicos "suaves") mas una costura vertical por
            # cada anclaje de tentaculo, marcando su base.
            for factor, ancho in ((0.94, 1.6), (0.68, 1.3), (0.40, 1.0)):
                pts = [
                    (cx - rx * factor, cy - ry * 0.05 * factor),
                    (cx, cy - ry * 1.05 * factor),
                    (cx + rx * factor, cy - ry * 0.05 * factor),
                ]
                d.line(_sc(pts), fill=255, width=int(SS * ancho))
            for i in range(7):
                t = i / 6.0
                x = cx + rx * (1.0 - 2.0 * t)
                y = cy + ry * (1.22 if i % 2 == 0 else 0.45)
                d.line(_sc([(x, y), (x, cy + ry * 0.1)]), fill=255, width=SS)
        return _dibujar
    if kind == "anomaly":
        def _dibujar(d):
            # grietas irregulares que parten del centro (entre los ojos)
            # hacia las puntas de la calavera, quebradas a mitad de camino
            # (no lineas rectas: se ve como un hueso realmente fracturado,
            # no una calavera "prolija").
            rnd = random.Random(77)
            puntas = [
                (0, -1.0), (0.55, -0.85), (0.92, -0.45), (0.85, -0.05),
                (0.97, 0.25), (0.35, 0.75), (0, 1.0), (-0.35, 0.75),
                (-0.97, 0.25), (-0.85, -0.05), (-0.92, -0.45), (-0.55, -0.85),
            ]
            for gx, gy in puntas:
                x1, y1 = cx + gx * rx, cy + gy * ry
                frac = rnd.uniform(0.4, 0.62)
                mx = cx + gx * rx * frac + rnd.uniform(-rx * 0.08, rx * 0.08)
                my = cy + gy * ry * frac + rnd.uniform(-ry * 0.2, ry * 0.2)
                d.line(_sc([(cx, cy), (mx, my)]), fill=255, width=SS)
                d.line(_sc([(mx, my), (x1, y1)]), fill=255, width=SS)
        return _dibujar

    def _dibujar(d):
        # tres anillos concentricos mas pequeños, como lineas de blindaje,
        # mas costuras radiales cortas entre anillos (paneles individuales
        # en vez de un disco liso con solo circulos).
        for nivel in (1, 2, 3):
            factor = 1.0 - 0.24 * nivel
            caja = _caja_elipse(rx * factor, ry * factor, cx, cy)
            d.ellipse(_sc(_puntos_de_caja(caja)), outline=255, width=SS)
        n_costuras = 12
        for i in range(n_costuras):
            ang = 2 * math.pi * i / n_costuras
            x0 = cx + math.cos(ang) * rx * 0.28
            y0 = cy + math.sin(ang) * ry * 0.28
            x1 = cx + math.cos(ang) * rx * 0.94
            y1 = cy + math.sin(ang) * ry * 0.94
            d.line(_sc([(x0, y0), (x1, y1)]), fill=255, width=max(1, SS // 2))
    return _dibujar


def _remaches_casco(kind, cx, cy, rx, ry):
    if kind == "anomaly":
        # sin remaches mecanicos (es hueso fracturado, no chapa blindada):
        # la textura la dan las grietas de _paneles_casco y las cuencas/
        # esquirlas de _detalle_extra_casco.
        return lambda d: None
    n, radio_factor, radio_remache = (18, 0.85, 3.2) if kind == "titan" else (10, 0.8, 2.2)

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
    if kind == "saucer":
        # Centinela Corrupto: platillo militar cubierto de rejillas de
        # ventilacion, una franja de peligro amarillo/negro y unas
        # "grietas" de corrupcion digital -pequeños desgarros con franja
        # cromatica cyan/magenta, no huesos rotos como Anomaly- para que
        # se note que es un sentinel fallando, no solo un platillo liso.
        for signo in (-1, 1):
            vx, vy = cx + signo * rx * 0.52, cy + ry * 0.30
            rejilla = [vx - 11, vy - 7, vx + 11, vy + 7]
            dibujo_detalle.rounded_rectangle(rejilla, radius=2, fill=(30, 31, 36, 255), outline=(12, 12, 16, 255), width=1)
            for i in range(-2, 3):
                ly = vy + i * 2.6
                dibujo_detalle.line([(vx - 9, ly), (vx + 9, ly)], fill=(10, 10, 13, 255), width=1)

        rnd = random.Random(kind)
        n_franja = 9
        ang0 = math.radians(35)
        for i in range(n_franja):
            if i % 2:
                continue
            ang = ang0 + (i / n_franja) * math.radians(70)
            fx = cx + math.cos(ang) * rx * 0.97
            fy = cy + math.sin(ang) * ry * 0.97
            nx, ny = math.cos(ang), math.sin(ang)
            tx, ty = -ny, nx
            largo = 9
            dibujo_detalle.polygon([
                (fx - tx * largo, fy - ty * largo), (fx + tx * largo, fy + ty * largo),
                (fx + tx * largo + nx * 6, fy + ty * largo + ny * 6),
                (fx - tx * largo + nx * 6, fy - ty * largo + ny * 6),
            ], fill=(230, 190, 40, 235))

        for seed_extra in (11, 47):
            rr = random.Random(seed_extra)
            ang = rr.uniform(0, 2 * math.pi)
            gx = cx + math.cos(ang) * rx * rr.uniform(0.3, 0.7)
            gy = cy + math.sin(ang) * ry * rr.uniform(0.3, 0.7)
            largo_g = rr.uniform(10, 16)
            ang_g = rr.uniform(0, math.pi)
            gx1 = gx + math.cos(ang_g) * largo_g
            gy1 = gy + math.sin(ang_g) * largo_g * 0.4
            dibujo_detalle.line([(gx - 2, gy), (gx1 - 2, gy1)], fill=(70, 230, 220, 220), width=2)
            dibujo_detalle.line([(gx + 2, gy), (gx1 + 2, gy1)], fill=(230, 60, 200, 200), width=2)
            dibujo_detalle.line([(gx, gy), (gx1, gy1)], fill=(15, 14, 18, 255), width=2)
    elif kind == "dragon":
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
        # Ojo-camara mecanico grande y centrado: aro/iris con "cuchillas"
        # de apertura fijas (como el diafragma de una lente), sin pupila
        # horneada -la pupila es 100% dinamica, la dibuja titan_boss.py
        # cada frame siguiendo a la nave (ver TITAN_OJO_* mas arriba). Nada
        # de rojo brillante "amistoso": base oscura y metal envejecido,
        # para que se sienta amenazante y no un dibujo animado.
        ojo_x, ojo_y = cx, cy - ry * 0.22
        r = TITAN_OJO_R
        # sombra de ceja marcada arriba del ojo: le da un gesto serio/hostil
        dibujo_detalle.polygon([
            (ojo_x - r * 1.7, ojo_y - r * 0.55), (ojo_x, ojo_y - r * 1.5), (ojo_x + r * 1.7, ojo_y - r * 0.55),
            (ojo_x + r * 1.3, ojo_y - r * 0.75), (ojo_x, ojo_y - r * 1.05), (ojo_x - r * 1.3, ojo_y - r * 0.75),
        ], fill=(25, 24, 30, 235))
        detalle.alpha_composite(soft_glow(BOSS_W, BOSS_H, ojo_x, ojo_y, r * 1.3, (150, 30, 30), 140))
        # aro exterior grueso, envejecido, con remaches propios
        dibujo_detalle.ellipse([ojo_x - r, ojo_y - r, ojo_x + r, ojo_y + r], fill=(46, 44, 52, 255))
        dibujo_detalle.ellipse([ojo_x - r, ojo_y - r, ojo_x + r, ojo_y + r], outline=(20, 19, 24, 255), width=3)
        for angulo_grados in range(0, 360, 30):
            ang = math.radians(angulo_grados)
            mx = ojo_x + math.cos(ang) * (r - 4)
            my = ojo_y + math.sin(ang) * (r - 4)
            dibujo_detalle.ellipse([mx - 2, my - 2, mx + 2, my + 2], fill=(90, 88, 96, 255))
        # cuchillas de apertura (diafragma), fijas, apuntando al centro
        r_iris = r * 0.74
        n_cuchillas = 8
        for i in range(n_cuchillas):
            ang0 = 2 * math.pi * i / n_cuchillas
            ang1 = ang0 + 2 * math.pi / n_cuchillas * 0.86
            p0 = (ojo_x + math.cos(ang0) * r_iris, ojo_y + math.sin(ang0) * r_iris)
            p1 = (ojo_x + math.cos(ang1) * r_iris, ojo_y + math.sin(ang1) * r_iris)
            pc = (ojo_x + math.cos((ang0 + ang1) / 2) * r_iris * 0.35, ojo_y + math.sin((ang0 + ang1) / 2) * r_iris * 0.35)
            dibujo_detalle.polygon([p0, pc, p1], fill=(70, 20, 20, 255), outline=(30, 10, 10, 255))
        # zocalo oscuro donde se apoya la pupila dinamica (sin pupila fija)
        dibujo_detalle.ellipse(
            [ojo_x - r * 0.42, ojo_y - r * 0.42, ojo_x + r * 0.42, ojo_y + r * 0.42],
            fill=(12, 8, 10, 255),
        )
    elif kind == "anomaly":
        # Calavera glicheada: dos cuencas oscuras y vacias (la pupila es
        # 100% dinamica, ver ANOMALY_OJO_*/boss.py _dibujar_ojos) mas
        # cavidad nasal, marcas de dientes en la quijada y esquirlas de
        # cristal brillantes en las puntas mas afiladas del craneo - nada
        # de nucleo unico y central como antes, la amenaza ahora esta en
        # la mirada, no en un brillo en el pecho.
        for signo in (-1, 1):
            ox = cx + signo * ANOMALY_OJO_DX
            oy = ANOMALY_OJO_CY
            r = ANOMALY_OJO_R
            detalle.alpha_composite(soft_glow(BOSS_W, BOSS_H, ox, oy, r * 1.4, (150, 40, 220), 150))
            dibujo_detalle.ellipse([ox - r, oy - r * 1.15, ox + r, oy + r * 1.15], fill=(15, 4, 22, 255))
            dibujo_detalle.ellipse([ox - r, oy - r * 1.15, ox + r, oy + r * 1.15],
                                    outline=(200, 130, 255, 220), width=2)

        # cavidad nasal: pequeño rombo oscuro entre los ojos
        nx0, ny0 = cx, cy + ry * 0.32
        dibujo_detalle.polygon([
            (nx0, ny0 - ry * 0.14), (nx0 + rx * 0.09, ny0 + ry * 0.1),
            (nx0, ny0 + ry * 0.22), (nx0 - rx * 0.09, ny0 + ry * 0.1),
        ], fill=(20, 6, 28, 255), outline=(150, 60, 200, 200))

        # marcas de dientes a lo largo de la quijada
        for i in range(-3, 4):
            tx = cx + i * rx * 0.11
            ty = cy + ry * (0.86 + 0.03 * (i % 2))
            dibujo_detalle.line([(tx, ty), (tx, ty + ry * 0.14)], fill=(20, 6, 28, 230), width=2)

        puntas = [
            (0.55, -0.85), (0.92, -0.45), (0.97, 0.25),
            (-0.92, -0.45), (-0.97, 0.25), (-0.55, -0.85),
        ]
        for px_f, py_f in puntas:
            px, py = cx + px_f * rx, cy + py_f * ry
            nx, ny = -py_f, px_f
            norm = math.hypot(nx, ny) or 1.0
            nx, ny = nx / norm * 5.5, ny / norm * 5.5
            dibujo_detalle.polygon(
                [(px, py), (px - px_f * 9 + nx, py - py_f * 9 + ny), (px - px_f * 9 - nx, py - py_f * 9 - ny)],
                fill=(220, 195, 255, 220), outline=(120, 55, 180, 255),
            )


def build_boss(kind="saucer"):
    """Nave nodriza extraterrestre: anillo exterior + casco central +
    plataforma de la cupula. La cupula de cristal, el piloto y las luces
    parpadeantes siguen dibujandose en tiempo real (boss.py /
    boss_system.py) porque cambian de color segun la fase de la pelea; el
    sprite aporta el volumen, la silueta y el detalle fijo.

    kind: "saucer" (platillo clasico, jefe Centinela Corrupto), "dragon"
    (casco alargado y colmillos, jefe Dragon Espacial), "titan" (casco
    hexagonal blindado, jefe Titan del Vacio) o "anomaly" (casco fracturado
    con nucleo de vacio, La Anomalia Final).
    """
    w, h = BOSS_W, BOSS_H
    cx, cy = BOSS_CENTRO_X, BOSS_CENTRO_Y

    # ---- anillo exterior (tintable con el color secundario -> "wing")
    # Identico en saucer/dragon/anomaly: aqui es donde el juego dibuja el
    # anillo de luces parpadeantes de esos tres. "titan" (pulpo mecanico,
    # ver _silueta_casco) no lleva anillo de nave nodriza -sus tentaculos
    # cumplen ese rol visual, dibujados en tiempo real en titan_boss.py- asi
    # que su mascara queda en blanco (el "wing" no aporta nada al sprite
    # final; boss_system.py y titan_boss.py deciden por separado si dibujan
    # o no las luces parpadeantes segun el tipo de jefe).
    mascara_anillo = _blank_mask(w, h)
    dibujo_anillo = ImageDraw.Draw(mascara_anillo)
    if kind not in ("titan", "anomaly"):
        dibujo_anillo.ellipse(_sc(_puntos_de_caja(_caja_elipse(BOSS_ANILLO_EXT_RX, BOSS_ANILLO_EXT_RY))), fill=255)
        dibujo_anillo.ellipse(_sc(_puntos_de_caja(_caja_elipse(BOSS_ANILLO_INT_RX, BOSS_ANILLO_INT_RY))), fill=0)
        for i in range(BOSS_NUM_NODOS):
            angulo = 2 * math.pi * i / BOSS_NUM_NODOS
            nodo_x = cx + math.cos(angulo) * BOSS_NODO_RX
            nodo_y = cy + math.sin(angulo) * BOSS_NODO_RY
            dibujo_anillo.ellipse(_sc(_puntos_de_caja((nodo_x - 8, nodo_y - 8, nodo_x + 8, nodo_y + 8))), fill=255)

    valor_anillo = shading_field(w, h, light=(0.30, 0.14), body_falloff=60, bottom_dark=95, spec=55)
    valor_anillo = valor_anillo + grain_noise(w, h, _seed_de(f"anillo-{kind}"), octaves=((14, 6), (34, 3)))

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
    # Titan usa una caja mas grande (TITAN_CASCO_RX/RY): no comparte
    # anillo/cupula con los demas, asi que puede inflarse sin invadir esa
    # geometria (ver comentario de TITAN_RX_SCALE mas arriba).
    rx_casco, ry_casco = {
        "titan": (TITAN_CASCO_RX, TITAN_CASCO_RY),
        "anomaly": (ANOMALY_CASCO_RX, ANOMALY_CASCO_RY),
    }.get(kind, (BOSS_CASCO_RX, BOSS_CASCO_RY))
    silueta = _silueta_casco(kind, rx_casco, ry_casco)
    if silueta is not None:
        mascara_casco = mask_from_shapes(w, h, polys=[silueta])
    else:
        mascara_casco = mask_from_shapes(w, h, ellipses=[_caja_elipse(rx_casco, ry_casco)])

    luz_por_tipo = {
        "dragon": (0.30, 0.20),
        "titan": (0.36, 0.18),
        "anomaly": (0.5, 0.5),
    }.get(kind, (0.34, 0.16))
    valor_casco = shading_field(w, h, light=luz_por_tipo, body_falloff=88, bottom_dark=100, spec=62)
    valor_casco = valor_casco + grain_noise(w, h, _seed_de(f"casco-{kind}"), octaves=((14, 6), (34, 3)))
    valor_casco = stamp(valor_casco, w, h, _paneles_casco(kind, cx, cy, rx_casco, ry_casco), -28)
    valor_casco = stamp(valor_casco, w, h, _remaches_casco(kind, cx, cy, rx_casco, ry_casco), 45)
    casco_rgba = to_rgba_tintable(valor_casco, mascara_casco, w, h)

    # ---- detalle (sin tintar): contorno, remaches con brillo, plataforma
    detalle = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mascara_completa = Image.fromarray(
        np.maximum(np.asarray(mascara_casco, np.uint8), np.asarray(mascara_anillo, np.uint8)), mode="L"
    )
    detalle.alpha_composite(outline_layers(mascara_completa, w, h, dark_a=185, rim_a=95))

    dibujo_detalle = ImageDraw.Draw(detalle)
    if kind not in ("titan", "anomaly"):
        # Plataforma de la cupula (saucer/dragon/anomaly): base donde boss.py/
        # boss_system.py dibujan en tiempo real el vidrio y el piloto. Titan
        # (pulpo mecanico) no tiene cabina: su ojo ya es el foco visual (ver
        # _detalle_extra_casco), asi que no lleva esta plataforma.
        caja_plataforma = (
            cx - BOSS_PLATAFORMA_RX, BOSS_PLATAFORMA_CY - BOSS_PLATAFORMA_RY,
            cx + BOSS_PLATAFORMA_RX, BOSS_PLATAFORMA_CY + BOSS_PLATAFORMA_RY,
        )
        dibujo_detalle.ellipse(caja_plataforma, fill=(66, 66, 82, 255))
        dibujo_detalle.ellipse(caja_plataforma, outline=(18, 18, 28, 255), width=2)
        detalle.alpha_composite(
            soft_glow(w, h, cx, BOSS_PLATAFORMA_CY, BOSS_PLATAFORMA_RX * 1.3, (120, 220, 255), 90)
        )

    if kind not in ("titan", "anomaly"):
        for i in range(BOSS_NUM_NODOS):
            angulo = 2 * math.pi * i / BOSS_NUM_NODOS
            nodo_x = cx + math.cos(angulo) * BOSS_NODO_RX
            nodo_y = cy + math.sin(angulo) * BOSS_NODO_RY
            detalle.alpha_composite(soft_glow(w, h, nodo_x, nodo_y, 11, (255, 255, 255), 55))
            dibujo_detalle.ellipse([nodo_x - 3.4, nodo_y - 3.4, nodo_x + 3.4, nodo_y + 3.4], fill=(35, 35, 48, 255))
            dibujo_detalle.ellipse([nodo_x - 1.3, nodo_y - 1.3, nodo_x + 1.3, nodo_y + 1.3], fill=(210, 230, 255, 200))

    _detalle_extra_casco(kind, detalle, dibujo_detalle, cx, cy, rx_casco, ry_casco)

    return {"body": casco_rgba, "wing": anillo_rgba, "detail": detalle}


# ---------------------------------------------------- tentaculo de titan

# Segmento reutilizable de tentaculo: apunta a lo largo de +X (base ancha
# en x=0, garra afilada en el extremo derecho), para que titan_boss.py lo
# pueda rotar/escalar y encadenar varias copias siguiendo la curva de cada
# ataque en tiempo real (nada de esto puede ser un unico PNG fijo, porque
# el largo/curva cambian segun a donde ataca). Se generan aparte de
# build_boss(): no es un casco de nave, es una pieza que se repite.
TENTACULO_W, TENTACULO_H = 96, 40
TENTACULO_CY = TENTACULO_H / 2.0


def build_titan_tentaculo():
    w, h = TENTACULO_W, TENTACULO_H
    cy = TENTACULO_CY

    # cuerpo: tubo organico-mecanico que se afina de base (izquierda) a
    # punta (derecha), rematado en una garra curva afilada.
    cuerpo_pts = [
        (2, cy - 15), (18, cy - 16), (40, cy - 11), (60, cy - 7), (74, cy - 4),
        (74, cy + 4), (60, cy + 7), (40, cy + 11), (18, cy + 16), (2, cy + 15),
    ]
    garra_pts = [
        (70, cy - 5), (92, cy - 13), (86, cy - 2), (92, cy + 7), (70, cy + 5),
    ]
    mascara = mask_from_shapes(w, h, polys=[cuerpo_pts, garra_pts])

    valor = shading_field(w, h, light=(0.30, 0.30), body_falloff=75, bottom_dark=60, spec=50)
    valor = valor + grain_noise(w, h, _seed_de("tentaculo"), octaves=((10, 7), (24, 3.5)))

    def _anillos(d):
        for x0 in (16, 34, 52, 68):
            d.line(_sc([(x0, cy - 17), (x0, cy + 17)]), fill=255, width=SS)
    valor = stamp(valor, w, h, _anillos, -35)

    def _resalte(d):
        d.line(_sc([(4, cy - 4), (72, cy - 2)]), fill=255, width=int(SS * 1.4))
    valor = stamp(valor, w, h, _resalte, 30)

    cuerpo_rgba = to_rgba_tintable(valor, mascara, w, h)

    detalle = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    detalle.alpha_composite(outline_layers(mascara, w, h, dark_a=190, rim_a=90))
    dd = ImageDraw.Draw(detalle)

    # ventosas: dos hileras de circulos oscuros a lo largo del lado interno
    for x0 in range(10, 66, 11):
        dd.ellipse([x0 - 3.4, cy - 2 - 3.4, x0 + 3.4, cy - 2 + 3.4], fill=(35, 30, 40, 235))
        dd.ellipse([x0 - 1.6, cy - 2 - 1.6, x0 + 1.6, cy - 2 + 1.6], fill=(70, 60, 78, 200))

    # garra metalica en la punta, sin tintar (siempre gris acero oscuro)
    dd.polygon(garra_pts, fill=(72, 70, 80, 255), outline=(24, 22, 28, 255))
    dd.ellipse([84, cy - 3, 90, cy + 3], fill=(210, 200, 220, 200))

    return {"body": cuerpo_rgba, "detail": detalle}


# ------------------------------------------------------ dragon (oleada 20)

# El jefe de la oleada 20 (modules/entities/dragon_boss.py) es un DRAGON de
# verdad -craneo con cuernos y dos ojos, alas de murcielago bien abiertas
# a los costados, brazos con garras y una cola larga que se curva hacia un
# lado- mirando siempre de frente al jugador, no una nave ni un casco
# blindado. Los nombres DRAGON_ROBOT_*/build_dragon_robot() se mantienen
# por compatibilidad con dragon_boss.py y sprites.py (mismo criterio que
# BOSS_SPRITE_PREFIX guardando "saucer" como "mothership"): ya no hay nada
# de robotico en el diseño. La silueta no es un solo poligono con un lado
# espejado (como el resto de los jefes): son VARIOS poligonos simples
# (cabeza, cuerpo+patas, cola, cada ala, cada brazo) que `mask_from_shapes`
# une en una sola mascara -mucho mas facil de armar bien que un contorno
# gigante de 30 puntos sin que se cruce a si mismo.
#
# Dos ojos huecos en el sprite (pupila 100% dinamica, ver DRAGON_OJO_*/
# dragon_boss.py _dibujar_ojo, igual que ANOMALY_OJO_*). "apertura" (0.0 a
# 1.0) sigue sin ser un iris abriendose: es cuanto DAÑO/heridas tiene
# encima -mas grietas, mas heridas al rojo vivo, mas se le nota que esta
# perdiendo la pelea- y sube con cada cambio de fase (0.0 Explorador, 0.5
# Envite, 1.0 Furia). Se generan 11 cuadros (apertura 0.0, 0.1, ..., 1.0):
# los de las tres fases son sprites fijos, y los de en medio son el
# "flipbook" que dragon_boss.py reproduce en tiempo real durante la
# transformacion -se ve herirse de verdad cuadro a cuadro, no un simple
# destello de color.
#
# El PNG final es PIXEL ART de verdad, a pedido: toda la geometria de
# arriba se sigue dibujando a la escala grande de siempre (mas facil de
# armar a mano) y build_dragon_robot() la baja al final a una grilla
# nativa chica (DRAGON_PIXEL_W/H) con la luminancia posterizada en bandas
# planas (ver _dragon_pixelar) -asi la sombra se lee en escalones de color
# como en un sprite retro de verdad, con el contorno recalculado en esa
# misma grilla chica (no el antialiasing del hi-res, que se veria
# borroso). sprites.py la escala de vuelta arriba sin suavizar
# (`pixelado=True`) para que los "pixeles" se vean como bloques solidos.
DRAGON_ROBOT_W, DRAGON_ROBOT_H = 320, 300
DRAGON_ROBOT_CX, DRAGON_ROBOT_CY = DRAGON_ROBOT_W / 2.0, DRAGON_ROBOT_H / 2.0
DRAGON_ROBOT_FRAMES = 11  # apertura = indice / (DRAGON_ROBOT_FRAMES - 1)

# Resolucion NATIVA final (pixel-art de verdad, no una silueta suavizada
# escalada): toda la geometria de arriba se sigue autorando a la escala
# grande de siempre (DRAGON_ROBOT_W/H, mas facil de dibujar a mano), pero
# build_dragon_robot() la baja a esta grilla chica al final (BOX + una
# luminancia posterizada en bandas planas, ver _dragon_pixelar) y la
# guarda asi -sprites.py la escala de vuelta arriba con vecino-mas-cercano
# (sin suavizar), igual que las insignias de power-up, para que se vean
# los "cuadrados" de pixel de verdad en vez de un degrade continuo.
DRAGON_PIXEL_W, DRAGON_PIXEL_H = 80, 75

# Dos ojos (cuencas vacias horneadas, pupila dinamica en tiempo real).
DRAGON_OJO_DX = 26.0   # separacion desde el centro, cada ojo
DRAGON_OJO_CY = 60.0
DRAGON_OJO_R = 12.0

# Garganta: de aca sale telegrafiado el aliento de fuego (el resplandor en
# si es 100% en tiempo real, ver dragon_boss.py _dibujar_garganta) y punta
# del hocico, para ubicar la boca sin adivinar pixeles.
DRAGON_GARGANTA_X, DRAGON_GARGANTA_Y = DRAGON_ROBOT_CX, 102.0
DRAGON_HOCICO_Y = 130.0


def _espejar_x(puntos, cx=DRAGON_ROBOT_CX):
    return [(2 * cx - x, y) for x, y in puntos]


# Cabeza: hocico puntiagudo al frente (centro, abajo de la cabeza), dos
# cuernos curvos arriba. Sola alcanza para "leerse" como dragon sin
# necesitar el resto del cuerpo.
_DRAGON_CABEZA = [
    (DRAGON_ROBOT_CX, DRAGON_HOCICO_Y),
    (DRAGON_ROBOT_CX + 34, 108), (DRAGON_ROBOT_CX + 50, 80),
    (DRAGON_ROBOT_CX + 62, 46), (DRAGON_ROBOT_CX + 36, 18),
    (DRAGON_ROBOT_CX + 16, 2), (DRAGON_ROBOT_CX + 6, 32),
    (DRAGON_ROBOT_CX - 6, 32), (DRAGON_ROBOT_CX - 16, 2),
    (DRAGON_ROBOT_CX - 36, 18), (DRAGON_ROBOT_CX - 62, 46),
    (DRAGON_ROBOT_CX - 50, 80), (DRAGON_ROBOT_CX - 34, 108),
]

# Cuerpo: hombros -> torso -> caderas -> patas con garras.
_DRAGON_CUERPO = [
    (DRAGON_ROBOT_CX, 116),
    (DRAGON_ROBOT_CX + 42, 138), (DRAGON_ROBOT_CX + 36, 186),
    (DRAGON_ROBOT_CX + 46, 226), (DRAGON_ROBOT_CX + 36, 262),
    (DRAGON_ROBOT_CX + 44, 288), (DRAGON_ROBOT_CX + 20, 284),
    (DRAGON_ROBOT_CX + 10, 260), (DRAGON_ROBOT_CX, 292),
    (DRAGON_ROBOT_CX - 10, 260), (DRAGON_ROBOT_CX - 20, 284),
    (DRAGON_ROBOT_CX - 44, 288), (DRAGON_ROBOT_CX - 36, 262),
    (DRAGON_ROBOT_CX - 46, 226), (DRAGON_ROBOT_CX - 36, 186),
    (DRAGON_ROBOT_CX - 42, 138),
]

# Cola: se curva hacia la derecha (asimetrica a proposito, no es una nave
# ni un blindaje simetrico -un animal real no es perfectamente simetrico).
_DRAGON_COLA = [
    (DRAGON_ROBOT_CX + 38, 248), (DRAGON_ROBOT_CX + 72, 258),
    (DRAGON_ROBOT_CX + 108, 244), (DRAGON_ROBOT_CX + 136, 212),
    (DRAGON_ROBOT_CX + 150, 176), (DRAGON_ROBOT_CX + 138, 158),
    (DRAGON_ROBOT_CX + 116, 186), (DRAGON_ROBOT_CX + 94, 222),
    (DRAGON_ROBOT_CX + 64, 250), (DRAGON_ROBOT_CX + 42, 264),
]

# Ala derecha (membrana de murcielago con varias puntas); la izquierda es
# el espejo. Sale del hombro.
_DRAGON_ALA_DER = [
    (DRAGON_ROBOT_CX + 40, 142), (DRAGON_ROBOT_CX + 92, 116),
    (DRAGON_ROBOT_CX + 150, 84), (DRAGON_ROBOT_CX + 138, 124),
    (DRAGON_ROBOT_CX + 168, 132), (DRAGON_ROBOT_CX + 148, 168),
    (DRAGON_ROBOT_CX + 162, 192), (DRAGON_ROBOT_CX + 118, 198),
    (DRAGON_ROBOT_CX + 88, 182), (DRAGON_ROBOT_CX + 58, 158),
]
_DRAGON_ALA_IZQ = _espejar_x(_DRAGON_ALA_DER)

# Brazo derecho con garra; el izquierdo es el espejo. Se separa bien del
# torso (codo bien afuera, x hasta +86 contra los +46 del torso) para que
# se lea como una extremidad de verdad -brazo musculoso doblado con la
# garra al frente, como en la referencia- y no como un bulto pegado al
# cuerpo que solo se nota por la punta de la garra.
_DRAGON_BRAZO_DER = [
    (DRAGON_ROBOT_CX + 34, 148), (DRAGON_ROBOT_CX + 68, 160),
    (DRAGON_ROBOT_CX + 86, 188), (DRAGON_ROBOT_CX + 78, 214),
    (DRAGON_ROBOT_CX + 84, 234), (DRAGON_ROBOT_CX + 66, 238),
    (DRAGON_ROBOT_CX + 54, 220), (DRAGON_ROBOT_CX + 46, 196),
    (DRAGON_ROBOT_CX + 30, 172),
]
_DRAGON_BRAZO_IZQ = _espejar_x(_DRAGON_BRAZO_DER)


def _dragon_silueta():
    """Lista de poligonos (no uno solo): mask_from_shapes los une a todos
    en una sola mascara."""
    return [
        _DRAGON_CABEZA, _DRAGON_CUERPO, _DRAGON_COLA,
        _DRAGON_ALA_DER, _DRAGON_ALA_IZQ,
        _DRAGON_BRAZO_DER, _DRAGON_BRAZO_IZQ,
    ]


# Puntos de herida fijos (no simetricos a proposito) con el rango de
# "apertura" en el que pasan de intactas a heridas abiertas al rojo vivo
# (se dibujan en baja resolucion, ver el final de build_dragon_robot).
# Cada tupla es (x, y, radio_base, inicio, fin, seed) -seed nomas para
# variar el punto de la brasa, no hace falta mas en pixel art.
_DRAGON_DAÑOS = [
    (DRAGON_ROBOT_CX + 150, 84, 12, 0.08, 0.42, 1),   # punta del ala derecha
    (DRAGON_ROBOT_CX - 46, 226, 14, 0.18, 0.52, 2),   # cadera izquierda
    (DRAGON_ROBOT_CX, 186, 11, 0.32, 0.68, 3),        # pecho/torso central
    (DRAGON_ROBOT_CX - 150, 84, 13, 0.42, 0.78, 4),   # punta del ala izquierda
    (DRAGON_ROBOT_CX + 50, 80, 9, 0.62, 1.00, 5),     # mejilla derecha (solo fase 3 avanzada)
]


def _dragon_pixelar(cuerpo_rgba_hi, detalle_hi, mascara_hi, w_hi, h_hi, niveles=5):
    """Convierte el render suave (supersample+AA de siempre) en pixel art
    de verdad: lo baja a la grilla nativa chica con un filtro de area
    (`Image.BOX`, promedia bien en vez de solo tomar una muestra) y
    POSTERIZA la luminancia del cuerpo en `niveles` bandas planas -asi la
    sombra se lee en escalones de color como en un sprite pixel-art de
    verdad, no como un degrade continuo encogido. El contorno se
    RECALCULA en la propia grilla nativa (silueta binaria menos su
    erosion) en vez de reusar el contorno con antialiasing del hi-res,
    que se veria borroso a este tamaño."""
    pw, ph = DRAGON_PIXEL_W, DRAGON_PIXEL_H

    l_hi = cuerpo_rgba_hi.split()[0]
    l_low = l_hi.resize((pw, ph), Image.BOX)
    a_low = mascara_hi.resize((pw, ph), Image.BOX).point(lambda p: 255 if p > 100 else 0)

    l_arr = np.asarray(l_low, dtype=np.float32)
    paso = 255.0 / (niveles - 1)
    l_post = np.clip(np.round(l_arr / paso) * paso, 0, 255).astype(np.uint8)
    l_img = Image.fromarray(l_post, mode="L")
    cuerpo_low = Image.merge("RGBA", (l_img, l_img, l_img, a_low))

    detalle_low = detalle_hi.resize((pw, ph), Image.BOX)

    erosion = a_low.filter(ImageFilter.MinFilter(3))
    borde = np.clip(np.asarray(a_low, np.int16) - np.asarray(erosion, np.int16), 0, 255).astype(np.uint8)
    contorno = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    contorno.paste((8, 5, 12, 255), (0, 0), Image.fromarray(borde, mode="L"))
    detalle_low = Image.alpha_composite(detalle_low, contorno)

    return cuerpo_low, detalle_low


def build_dragon_robot(apertura):
    """Dragon del jefe de la oleada 20: craneo con cuernos y dos ojos,
    alas de murcielago, brazos con garras y cola curva -ver
    _dragon_silueta()-, mas un sistema de heridas que se agrava con
    `apertura` -mas grietas, mas heridas al rojo vivo, mas se le nota que
    esta perdiendo la pelea- reutilizado tanto para los 3 estados fijos de
    fase como para el flipbook de transformacion entre ellos."""
    w, h = DRAGON_ROBOT_W, DRAGON_ROBOT_H
    cx, cy = DRAGON_ROBOT_CX, DRAGON_ROBOT_CY

    poligonos = _dragon_silueta()
    mascara = mask_from_shapes(w, h, polys=poligonos)

    # mas contraste que el resto de los jefes (mas body_falloff/bottom_dark/
    # spec): es un dragon gigante, necesita leerse como un volumen solido
    # con musculo y escamas reales, no una silueta plana con un tinte
    # parejo encima.
    valor = shading_field(w, h, light=(0.40, 0.42), body_falloff=76, bottom_dark=30, spec=90)
    valor = valor + grain_noise(w, h, _seed_de("dragon-piel"), octaves=((11, 6), (26, 3)))

    def _escamas(d):
        # filas de arcos cortos en el pecho/torso: escamas, no placas
        # rectas de blindaje.
        y0 = 150.0
        fila = 0
        while y0 <= 280.0:
            offset = 10.0 if fila % 2 else 0.0
            x0 = cx - 44 + offset
            while x0 <= cx + 44:
                d.arc([(x0 - 9) * SS, (y0 - 7) * SS, (x0 + 9) * SS, (y0 + 9) * SS], start=200, end=340, fill=255, width=SS)
                x0 += 18.0
            y0 += 15.0
            fila += 1
    valor = stamp(valor, w, h, _escamas, -20)

    def _costuras(d):
        # separacion sutil donde el ala y el brazo se unen al cuerpo, y
        # una linea de cuernos a hocico marcando el perfil de la cara.
        for ala in (_DRAGON_ALA_DER, _DRAGON_ALA_IZQ):
            d.line(_sc([ala[0], ala[-1]]), fill=255, width=SS)
        for brazo in (_DRAGON_BRAZO_DER, _DRAGON_BRAZO_IZQ):
            d.line(_sc([brazo[0], brazo[-1]]), fill=255, width=SS)
        for punta_cuerno in (_DRAGON_CABEZA[4], _DRAGON_CABEZA[8]):
            d.line(_sc([(cx, DRAGON_HOCICO_Y - 10), punta_cuerno]), fill=255, width=SS)
    valor = stamp(valor, w, h, _costuras, -24)

    def _quilla(d):
        # resalte central del hocico al tope de la cabeza: una franja mas
        # clara marcando el eje de simetria de la cara, le da volumen real
        # al frente en vez de un tinte parejo.
        d.line(_sc([(cx, DRAGON_HOCICO_Y - 6), (cx, 20)]), fill=255, width=int(SS * 2.4))
    valor = stamp(valor, w, h, _quilla, 22)

    def _borde(d):
        for poly in poligonos:
            d.polygon(_sc(poly), outline=255, width=SS)
    valor = stamp(valor, w, h, _borde, -34)

    cuerpo_rgba = to_rgba_tintable(valor, mascara, w, h)

    detalle = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    detalle.alpha_composite(outline_layers(mascara, w, h, dark_a=195, rim_a=100))
    dd = ImageDraw.Draw(detalle)

    # dos ojos: cuencas vacias (sin pupila horneada) con un aro que se
    # ilumina mas cuanto mas herido esta el dragon -se pone mas intenso
    # cuanto mas cerca de morir.
    r_ojo = DRAGON_OJO_R
    intensidad = 110 + int(110 * apertura)
    for signo in (-1, 1):
        ox = cx + signo * DRAGON_OJO_DX
        oy = DRAGON_OJO_CY
        detalle.alpha_composite(soft_glow(w, h, ox, oy, r_ojo * 1.6, (255, 190, 60), intensidad))
        dd.ellipse([ox - r_ojo, oy - r_ojo, ox + r_ojo, oy + r_ojo], fill=(10, 3, 6, 255))
        dd.ellipse([ox - r_ojo, oy - r_ojo, ox + r_ojo, oy + r_ojo],
                   outline=(230, 170, 80, 230), width=3)

    # boca: cuenca ovalada y oscura con colmillos arriba Y abajo -un
    # dragon rugiendo con las fauces abiertas, no solo textura en la
    # quijada.
    boca_cx, boca_cy = cx, DRAGON_HOCICO_Y - 26
    boca_rx, boca_ry = 40, 20
    dd.ellipse([boca_cx - boca_rx, boca_cy - boca_ry, boca_cx + boca_rx, boca_cy + boca_ry],
               fill=(35, 6, 8, 255), outline=(90, 40, 30, 220), width=2)
    for i in range(-2, 3):
        dx_diente = i * 14
        if abs(dx_diente) >= boca_rx:
            continue
        frac = dx_diente / boca_rx
        alto_rim = boca_ry * math.sqrt(max(0.0, 1.0 - frac * frac))
        tx = boca_cx + dx_diente
        rim_arriba = boca_cy - alto_rim
        rim_abajo = boca_cy + alto_rim
        dd.polygon([(tx - 4, rim_arriba), (tx + 4, rim_arriba), (tx, rim_arriba + 14)],
                   fill=(230, 220, 200, 255), outline=(90, 80, 70, 255))
        dd.polygon([(tx - 4, rim_abajo), (tx + 4, rim_abajo), (tx, rim_abajo - 12)],
                   fill=(230, 220, 200, 255), outline=(90, 80, 70, 255))

    # venas de la membrana de cada ala: de la raiz a cada punta.
    for ala in (_DRAGON_ALA_DER, _DRAGON_ALA_IZQ):
        raiz = ala[0]
        for punta in (ala[2], ala[4], ala[6]):
            dd.line([raiz, punta], fill=(225, 210, 235, 110), width=2)

    # garras: una punta clara en la mano de cada brazo y en cada pata.
    for gx, gy in (
        _DRAGON_BRAZO_DER[4], _DRAGON_BRAZO_IZQ[4],
        (cx + 44, 288), (cx - 44, 288),
    ):
        dd.polygon([(gx - 5, gy - 4), (gx + 7, gy - 2), (gx - 1, gy + 9)],
                   fill=(235, 228, 210, 255), outline=(90, 80, 70, 255))

    # pixelado real (ver _dragon_pixelar): de aca en adelante todo se
    # dibuja en la grilla nativa chica, no en la resolucion "de autor"
    # de arriba -las heridas en particular NO se dibujan en hi-res: una
    # grieta fina de un par de pixeles de ancho se emborrona/desaparece
    # al bajar de escala, asi que se dibujan directo en baja resolucion,
    # como manchas solidas en vez de lineas.
    cuerpo_low, detalle_low = _dragon_pixelar(cuerpo_rgba, detalle, mascara, w, h)

    escala = DRAGON_PIXEL_W / w
    dd_low = ImageDraw.Draw(detalle_low)
    for x, y, r0, inicio, fin, seed in _DRAGON_DAÑOS:
        severidad = max(0.0, min(1.0, (apertura - inicio) / (fin - inicio)))
        if severidad <= 0:
            continue
        rng = random.Random(seed)
        px, py = x * escala, y * escala
        r_low = max(1.4, r0 * escala * (0.55 + 0.55 * severidad))
        dd_low.ellipse([px - r_low, py - r_low, px + r_low, py + r_low], fill=(28, 5, 6, 255))
        dd_low.ellipse([px - r_low, py - r_low, px + r_low, py + r_low],
                       outline=(255, 140, 60, min(255, int(160 + 80 * severidad))), width=1)
        if severidad > 0.5:
            ang = rng.uniform(0, 2 * math.pi)
            bx, by = px + math.cos(ang) * r_low * 0.6, py + math.sin(ang) * r_low * 0.6
            dd_low.point([(bx, by)], fill=(255, 210, 140, 255))

    return {"body": cuerpo_low, "detail": detalle_low}


# ------------------------------------------------------------- mega-jefe

# El mega-jefe de la oleada 50 (ver modules/entities/mega_boss.py) no
# reutiliza el molde "platillo + anillo de luces" de build_boss: tiene dos
# siluetas propias, una por fase, exportadas ya con sus colores finales (no
# son tintables como el resto: es un jefe unico, no una nave de skin
# variable). Estas fracciones las usa tambien modules/systems/sprites.py y
# deben coincidir con las de aca.
MEGA_W, MEGA_H = 380, 210
MEGA_SPHERE_RADIUS_FRAC = 0.457     # radio de la esfera / MEGA_H
MEGA_SPHERE_DISH_X_FRAC = 0.419     # centro del zocalo del laser / MEGA_W
MEGA_SPHERE_DISH_Y_FRAC = 0.335     # centro del zocalo del laser / MEGA_H
MEGA_SPHERE_DISH_R_FRAC = 0.076     # radio del zocalo del laser / MEGA_W

# Puntos fijos del crucero (fase 1) para que mega_boss.py pueda dibujar
# encima, en tiempo real, las luces de navegacion que parpadean y la
# animacion de largada de cazas desde el hangar, sin tener que adivinar
# coordenadas (mismo criterio que las fracciones de la esfera de arriba).
MEGA_CRUISER_PROA_X_FRAC = 0.968      # luz de proa (blanca)
MEGA_CRUISER_PROA_Y_FRAC = 0.580
MEGA_CRUISER_BABOR_X_FRAC = 0.047     # luz de babor, popa arriba (roja)
MEGA_CRUISER_BABOR_Y_FRAC = 0.523
MEGA_CRUISER_ESTRIBOR_X_FRAC = 0.047  # luz de estribor, popa abajo (verde)
MEGA_CRUISER_ESTRIBOR_Y_FRAC = 0.637
MEGA_CRUISER_BALIZA_X_FRAC = 0.463    # baliza ambar en la punta del radar
MEGA_CRUISER_BALIZA_Y_FRAC = 0.047
MEGA_CRUISER_HANGAR_X_FRAC = 0.447    # centro de la bahia de hangar
MEGA_CRUISER_HANGAR_Y_FRAC = 0.780


def build_mega_cruiser():
    """Fase 1 del mega-jefe: acorazado estelar de casco escalonado -hombros
    anchos a la mitad y popa partida en dos semi-cascos con motor propio
    cada uno, no una cuña lisa de bordes rectos- con espina dorsal
    elevada, torre de mando de dos niveles, hangar lateral y baterias de
    cañones de punto a lo largo de ambos flancos. Silueta original
    inspirada en el arquetipo clasico de "destructor estelar", no una
    copia de ningun diseño existente."""
    w, h = MEGA_W, MEGA_H
    # corrido hacia abajo (no exactamente centrado en el canvas): deja
    # margen arriba para la torre/radar sin recortarse contra el borde.
    cx, cy = w / 2.0, h * 0.58

    casco_pts = [
        (cx + 178, cy),
        (cx + 78, cy - 38),
        (cx + 22, cy - 44),
        (cx - 45, cy - 62),
        (cx - 100, cy - 68),
        (cx - 138, cy - 50),
        (cx - 158, cy - 30),
        (cx - 172, cy - 12),
        (cx - 172, cy + 12),
        (cx - 158, cy + 30),
        (cx - 138, cy + 50),
        (cx - 100, cy + 68),
        (cx - 45, cy + 62),
        (cx + 22, cy + 44),
        (cx + 78, cy + 38),
    ]
    mascara = mask_from_shapes(w, h, polys=[casco_pts])

    fondo = vertical_gradient_rgba(w * SS, h * SS, (168, 172, 182, 255), (60, 63, 74, 255))
    grande = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    grande.paste(fondo, (0, 0), mascara)
    dibujo = ImageDraw.Draw(grande)

    # espina dorsal: plataforma elevada mas clara que recorre el casco de
    # proa a popa, angostandose hacia la proa - le da capas/volumen real
    # en vez de una sola superficie lisa.
    espina_pts = [
        (cx + 150, cy - 6), (cx + 20, cy - 22), (cx - 90, cy - 26),
        (cx - 140, cy - 14), (cx - 140, cy + 14), (cx - 90, cy + 26),
        (cx + 20, cy + 22), (cx + 150, cy + 6),
    ]
    dibujo.polygon(_sc(espina_pts), fill=(196, 200, 210, 255))
    dibujo.line(_sc([(cx + 150, cy), (cx - 138, cy)]), fill=(40, 42, 52, 140), width=SS * 3)

    # paneles: lineas transversales densas de punta a punta, mas un par de
    # franjas de blindaje mas oscuras marcando secciones del casco.
    for i in range(-11, 12):
        x0 = cx + i * 16
        dibujo.line(_sc([(x0, cy - 74), (x0 - 9, cy + 74)]), fill=(28, 29, 38, 90), width=SS)
    for x0 in (cx + 60, cx - 20, cx - 95):
        dibujo.line(_sc([(x0, cy - 74), (x0 - 12, cy + 74)]), fill=(20, 21, 28, 140), width=int(SS * 2.2))

    # compuerta de hangar en el flanco inferior: un rectangulo subdividido,
    # como una bahia de lanzamiento, distinto de las lineas de panel finas.
    hangar = (cx - 55, cy + 30, cx + 15, cy + 54)
    dibujo.rectangle(_sc([(hangar[0], hangar[1]), (hangar[2], hangar[3])]),
                     fill=(30, 31, 40, 220), outline=(60, 63, 74, 255), width=SS)
    for i in range(1, 4):
        hx = hangar[0] + (hangar[2] - hangar[0]) * i / 4.0
        dibujo.line(_sc([(hx, hangar[1]), (hx, hangar[3])]), fill=(60, 63, 74, 200), width=SS)

    # las lineas de blindaje/espina se dibujaron con coordenadas rectas (no
    # siguen el contorno afilado de la proa ni la popa escalonada), asi que
    # se recortan contra la mascara del casco antes de agregar la torre
    # (que si debe sobresalir por encima del casco, sin recortarse).
    grande = Image.composite(grande, Image.new("RGBA", grande.size, (0, 0, 0, 0)), mascara)
    dibujo = ImageDraw.Draw(grande)

    # torre de mando de dos niveles, corrida hacia la popa, con puente de
    # observacion (ventanas) en cada nivel y un radar en la punta.
    base_torre = [(cx - 68, cy - 48), (cx - 24, cy - 82), (cx + 10, cy - 80), (cx + 22, cy - 46)]
    dibujo.polygon(_sc(base_torre), fill=(118, 122, 134, 255), outline=(34, 35, 44, 255))
    for i in range(5):
        wx = cx - 54 + i * 14
        dibujo.rectangle(_sc([(wx, cy - 74), (wx + 7, cy - 68)]), fill=(150, 225, 255, 230))
    torre_alta = [(cx - 46, cy - 80), (cx - 22, cy - 104), (cx - 2, cy - 102), (cx - 8, cy - 78)]
    dibujo.polygon(_sc(torre_alta), fill=(138, 142, 156, 255), outline=(34, 35, 44, 255))
    for i in range(3):
        wx = cx - 34 + i * 13
        dibujo.rectangle(_sc([(wx, cy - 98), (wx + 6, cy - 93)]), fill=(170, 230, 255, 220))
    dibujo.line(_sc([(cx - 14, cy - 100), (cx - 14, cy - 112)]), fill=(60, 63, 74, 255), width=SS)
    dibujo.ellipse(_sc([(cx - 20, cy - 118), (cx - 8, cy - 106)]), fill=(90, 94, 106, 255), outline=(34, 35, 44, 255), width=SS)

    # dos platos/antenas sensoras a los costados de la torre
    for signo in (-1, 1):
        px, py = cx - 34, cy - 64 + signo * 30
        dibujo.ellipse(_sc([(px - 9, py - 9), (px + 9, py + 9)]), fill=(72, 76, 88, 255), outline=(24, 25, 32, 255), width=2)
        dibujo.ellipse(_sc([(px - 4, py - 4), (px + 4, py + 4)]), fill=(42, 44, 54, 255))

    # dos torretas principales en los flancos, apuntando hacia la proa: le
    # dan una silueta secundaria al casco (no es solo una cuña lisa) y
    # hacen que se lea de entrada como un acorazado con poder de fuego
    # propio. Mas una hilera de canones de punto mas chicos a cada lado,
    # densidad tipica de un destructor estelar cubierto de armamento.
    torreta_ys = []
    for signo in (-1, 1):
        tx, ty = cx - 92, cy + signo * 58
        torreta_ys.append(ty)
        dibujo.rectangle(_sc([(tx - 12, ty - 8), (tx + 16, ty + 8)]), fill=(98, 102, 114, 255), outline=(28, 29, 38, 255), width=SS)
        dibujo.polygon(_sc([(tx + 16, ty - 6), (tx + 34, ty - 2.5), (tx + 34, ty + 2.5), (tx + 16, ty + 6)]),
                       fill=(58, 60, 70, 255), outline=(22, 23, 30, 255), width=SS)
        dibujo.ellipse(_sc([(tx - 12, ty - 8), (tx + 4, ty + 8)]), fill=(70, 74, 86, 255), outline=(28, 29, 38, 255), width=SS)

    canon_pts = []
    for signo in (-1, 1):
        for fx in (0.55, 0.2, -0.35, -0.75):
            gx = cx + fx * 150
            gy = cy + signo * (34 + 8 * abs(fx))
            canon_pts.append((gx, gy))
            dibujo.ellipse(_sc([(gx - 4, gy - 4), (gx + 4, gy + 4)]), fill=(64, 67, 78, 255), outline=(24, 25, 32, 255), width=SS)

    final = grande.resize((w, h), Image.LANCZOS)

    motor_ys = (cy - 24, cy - 6, cy + 6, cy + 24)
    for ey in motor_ys:
        ex = cx - 168
        final.alpha_composite(soft_glow(w, h, ex, ey, 14, (120, 205, 255), 220))
    for ty in torreta_ys:
        final.alpha_composite(soft_glow(w, h, cx - 92 + 34, ty, 8, (255, 150, 90), 200))
    dibujo_final = ImageDraw.Draw(final)
    for ey in motor_ys:
        ex = cx - 168
        dibujo_final.ellipse([ex - 4.5, ey - 4.5, ex + 4.5, ey + 4.5], fill=(215, 242, 255, 255))
        dibujo_final.ellipse([ex - 2, ey - 2, ex + 2, ey + 2], fill=(255, 255, 255, 255))
    for ty in torreta_ys:
        tx = cx - 92 + 34
        dibujo_final.ellipse([tx - 3.2, ty - 3.2, tx + 3.2, ty + 3.2], fill=(255, 210, 180, 255))
    for gx, gy in canon_pts:
        dibujo_final.ellipse([gx - 1.6, gy - 1.6, gx + 1.6, gy + 1.6], fill=(200, 210, 225, 220))

    final.alpha_composite(outline_layers(mascara, w, h, dark=(10, 10, 16), dark_a=200, rim=(210, 214, 224), rim_a=120))
    return final


def build_mega_sphere():
    """Fase 2 del mega-jefe: esfera de combate blindada con banda ecuatorial
    y el zocalo hundido del laser (el nucleo brillante que carga/dispara se
    dibuja en tiempo real en mega_boss.py; aca solo va el zocalo apagado)."""
    w, h = MEGA_W, MEGA_H
    cx, cy = w / 2.0, h / 2.0
    r = h * MEGA_SPHERE_RADIUS_FRAC

    mascara = mask_from_shapes(w, h, ellipses=[(cx - r, cy - r, cx + r, cy + r)])
    valor = shading_field(w, h, light=(0.34, 0.24), body_falloff=55, bottom_dark=95, spec=80)
    valor = valor + grain_noise(w, h, _seed_de("mega-sphere"), octaves=((14, 6), (34, 3)))

    # grilla de paneles tipo "gofre": la textura de superficie caracteristica
    # de una estacion de combate blindada, cubriendo toda la esfera
    def _grilla(d):
        paso = r * 0.15
        y0 = cy - r
        while y0 <= cy + r:
            d.line(_sc([(cx - r, y0), (cx + r, y0)]), fill=255, width=SS)
            y0 += paso
        x0 = cx - r
        while x0 <= cx + r:
            d.line(_sc([(x0, cy - r), (x0, cy + r)]), fill=255, width=SS)
            x0 += paso
    valor = stamp(valor, w, h, _grilla, -14)

    def _banda(d):
        d.rectangle(_sc([(cx - r * 1.02, cy - r * 0.2), (cx + r * 1.02, cy + r * 0.2)]), fill=255)
    valor = stamp(valor, w, h, _banda, -60)

    def _lineas_banda(d):
        for i in range(-6, 7):
            x0 = cx + i * (r * 0.14)
            d.line(_sc([(x0, cy - r * 0.2), (x0, cy + r * 0.2)]), fill=255, width=SS)
    valor = stamp(valor, w, h, _lineas_banda, -35)

    def _anillos(d):
        for nivel in (0.9, 0.7, 0.5):
            d.ellipse(_sc([(cx - r * nivel, cy - r * nivel), (cx + r * nivel, cy + r * nivel)]), outline=255, width=SS)
    valor = stamp(valor, w, h, _anillos, -16)

    gris_img = to_rgba_tintable(valor, mascara, w, h)
    gris = np.asarray(gris_img.convert("L"), dtype=np.float32) / 255.0
    tinte = np.array([150.0, 158.0, 176.0])
    rgb = (gris[..., None] * tinte[None, None, :]).astype(np.uint8)
    alpha = np.asarray(gris_img.split()[3])
    img = Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA")

    dibujo = ImageDraw.Draw(img)
    dish_x, dish_y = w * MEGA_SPHERE_DISH_X_FRAC, h * MEGA_SPHERE_DISH_Y_FRAC
    dish_r = w * MEGA_SPHERE_DISH_R_FRAC

    # plataforma hexagonal elevada alrededor del zocalo, como la estructura
    # de soporte de un cañon principal
    hex_pts = []
    for i in range(6):
        ang = math.pi / 6 + i * math.pi / 3
        hex_pts.append((dish_x + math.cos(ang) * dish_r * 1.6, dish_y + math.sin(ang) * dish_r * 1.6))
    dibujo.polygon(hex_pts, outline=(96, 100, 116, 255), width=2)
    dibujo.ellipse([dish_x - dish_r * 1.2, dish_y - dish_r * 1.2, dish_x + dish_r * 1.2, dish_y + dish_r * 1.2],
                   outline=(80, 84, 98, 255), width=2)
    dibujo.ellipse([dish_x - dish_r, dish_y - dish_r, dish_x + dish_r, dish_y + dish_r],
                   fill=(26, 26, 36, 255), outline=(96, 100, 118, 255), width=3)
    dibujo.ellipse([dish_x - dish_r * 0.55, dish_y - dish_r * 0.55, dish_x + dish_r * 0.55, dish_y + dish_r * 0.55],
                   fill=(64, 20, 22, 255))

    # cañones secundarios asomando en el borde de la esfera (lejos del
    # zocalo del laser principal): sin ellos la fase 2 es solo una bola
    # blindada; con ellos se lee como una estacion de combate armada.
    for angulo_grados in (20, 80, 160, 250):
        ang = math.radians(angulo_grados)
        bx, by = cx + math.cos(ang) * r * 0.92, cy + math.sin(ang) * r * 0.92
        nx, ny = math.cos(ang), math.sin(ang)
        base = [
            (bx - ny * 9, by + nx * 9),
            (bx + ny * 9, by - nx * 9),
            (bx + nx * 16 + ny * 5, by + ny * 16 - nx * 5),
            (bx + nx * 16 - ny * 5, by + ny * 16 + nx * 5),
        ]
        dibujo.polygon(base, fill=(70, 74, 88, 255), outline=(24, 25, 34, 255))
        tip_x, tip_y = bx + nx * 17, by + ny * 17
        dibujo.ellipse([tip_x - 3.4, tip_y - 3.4, tip_x + 3.4, tip_y + 3.4], fill=(255, 150, 90, 255))

    random.seed(11)
    for _ in range(16):
        ang = random.uniform(0, 2 * math.pi)
        rad = random.uniform(r * 0.35, r * 0.92)
        px, py = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad * 0.94
        if abs(py - cy) < r * 0.2 or math.hypot(px - dish_x, py - dish_y) < dish_r * 1.7:
            continue
        tam = random.uniform(1.8, 3.2)
        dibujo.ellipse([px - tam, py - tam, px + tam, py + tam], fill=(66, 70, 84, 255), outline=(28, 28, 38, 255))

    img.alpha_composite(outline_layers(mascara, w, h, dark=(8, 8, 16), dark_a=200, rim=(190, 210, 230), rim_a=100))
    return img


# --------------------------------------------------------------- power-ups

# Cada bonus se ve como una INSIGNIA pixel-art retro (marco biselado
# caqui/negro con un ICONO propio adentro -escudo, corazon, pistola,
# espada, iman, rayo...- al estilo "iconos de habilidad" de un RPG de 16
# bits) en vez de una letra generica sobre el mismo cuadrado repetido: el
# tipo de bonus se reconoce por la FORMA del icono de un vistazo, no solo
# por la letra. A proposito NO pasa por el pipeline de
# supersampling+LANCZOS del resto de sprites (mask_from_shapes/
# shading_field/to_rgba_tintable): se dibuja directo a resolucion nativa
# baja y sin antialiasing, y se escala en tiempo real con
# pygame.transform.scale (bloques, sin suavizado - ver
# sprites.get_powerup_surface), para que se vea genuinamente en pixeles
# grandes y no una ilustracion suave "pixelada de mentira".
POWERUP_BADGE_PX = 24
POWERUP_MARCO_ANCHO = 4  # grosor total del marco (negro+bisel+negro), debe
                          # coincidir en build_powerup_body/_detail

POWERUP_KINDS = (
    "extra_life", "fast_shoot", "triple_shot", "shield", "piercing", "attract",
    "damage_up", "speed_up", "max_life_up", "rapid_fire", "lightning_field",
)

_ICONO_NEGRO = (12, 10, 8, 255)
_ICONO_BLANCO = (245, 240, 225, 255)
_ICONO_DORADO = (255, 205, 90, 255)


def _icono_heart(d, dd, grande):
    d.ellipse([6, 5, 12, 11], fill=255)
    d.ellipse([12, 5, 18, 11], fill=255)
    d.polygon([(6, 9), (18, 9), (12, 18)], fill=255)
    dd.ellipse([6, 5, 12, 11], outline=_ICONO_NEGRO, width=1)
    dd.ellipse([12, 5, 18, 11], outline=_ICONO_NEGRO, width=1)
    dd.polygon([(6, 9), (18, 9), (12, 18)], outline=_ICONO_NEGRO, width=1)
    dd.ellipse([7, 6, 9, 8], fill=_ICONO_BLANCO)
    if grande:
        # cruz pequeña en el pecho: distingue "vida maxima +1" del
        # corazon simple de "+1 vida" sin tapar la silueta.
        dd.rectangle([10, 7, 14, 9], fill=_ICONO_NEGRO)
        dd.rectangle([11, 6, 13, 10], fill=_ICONO_NEGRO)
        dd.rectangle([10.5, 7.5, 13.5, 8.5], fill=_ICONO_BLANCO)
        dd.rectangle([11.5, 6.5, 12.5, 9.5], fill=_ICONO_BLANCO)


def _icono_shield(d, dd):
    puntos = [(6, 5), (18, 5), (18, 11), (12, 19), (6, 11)]
    d.polygon(puntos, fill=255)
    dd.polygon(puntos, outline=_ICONO_NEGRO, width=1)
    dd.line([(12, 6), (12, 17)], fill=_ICONO_BLANCO, width=1)
    dd.line([(7, 6), (17, 6)], fill=_ICONO_BLANCO, width=1)


def _icono_dardo_veloz(d, dd):
    # flecha/dardo apuntando arriba-derecha + estela: boost TEMPORAL de
    # cadencia (fast_shoot).
    punta = [(18, 5), (18, 11), (14, 8)]
    asta = [(18, 5), (11, 12), (14, 12), (14, 8)]
    d.polygon(punta, fill=255)
    d.polygon(asta, fill=255)
    dd.polygon(punta, outline=_ICONO_NEGRO, width=1)
    dd.polygon(asta, outline=_ICONO_NEGRO, width=1)
    dd.line([(5, 15), (10, 12)], fill=_ICONO_DORADO, width=2)
    dd.line([(5, 18), (12, 15)], fill=_ICONO_DORADO, width=2)


def _icono_pistola(d, dd):
    # rapid_fire: PERMANENTE - silueta de pistola de perfil mirando a la
    # derecha (cuerpo + cañon a la misma altura + culata hacia atras).
    cuerpo = [7, 7, 14, 12]
    cañon = [14, 8, 19, 10]
    culata = [(7, 12), (11, 12), (9, 19), (7, 18)]
    d.rectangle(cuerpo, fill=255)
    d.rectangle(cañon, fill=255)
    d.polygon(culata, fill=255)
    dd.rectangle(cuerpo, outline=_ICONO_NEGRO, width=1)
    dd.rectangle(cañon, outline=_ICONO_NEGRO, width=1)
    dd.polygon(culata, outline=_ICONO_NEGRO, width=1)
    dd.line([(8, 8), (13, 8)], fill=_ICONO_BLANCO, width=1)


def _icono_triple(d, dd):
    # tres disparos en abanico, uno por cada bala extra.
    for dx in (-4, 0, 4):
        cx = 12 + dx
        punta = [(cx, 5), (cx + 2, 10), (cx - 2, 10)]
        asta = [cx - 1, 10, cx + 1, 18]
        d.polygon(punta, fill=255)
        d.rectangle(asta, fill=255)
        dd.polygon(punta, outline=_ICONO_NEGRO, width=1)
        dd.rectangle(asta, outline=_ICONO_NEGRO, width=1)


def _icono_pierce(d, dd):
    # anillo/placa con una flecha grande atravesandola de lado a lado: el
    # proyectil no se detiene en el impacto.
    anillo = [6, 6, 18, 18]
    asta = [4, 11, 19, 13]
    punta = [(19, 8), (19, 16), (14, 12)]
    d.ellipse(anillo, outline=255, width=2)
    d.rectangle(asta, fill=255)
    d.polygon(punta, fill=255)
    dd.ellipse(anillo, outline=_ICONO_NEGRO, width=1)
    dd.rectangle(asta, outline=_ICONO_NEGRO, width=1)
    dd.polygon(punta, outline=_ICONO_NEGRO, width=1)
    dd.line([(4, 11.5), (13, 11.5)], fill=_ICONO_BLANCO, width=1)


def _icono_magnet(d, dd):
    # iman de herradura con las puntas de colores (rojo/azul), abierto
    # hacia abajo.
    arco = [5, 5, 19, 19]
    pata_izq = [5, 12, 9, 17]
    pata_der = [15, 12, 19, 17]
    d.pieslice(arco, start=180, end=360, fill=255)
    d.rectangle(pata_izq, fill=255)
    d.rectangle(pata_der, fill=255)
    dd.pieslice(arco, start=180, end=360, outline=_ICONO_NEGRO, width=1)
    dd.rectangle(pata_izq, outline=_ICONO_NEGRO, width=1)
    dd.rectangle(pata_der, outline=_ICONO_NEGRO, width=1)
    dd.rectangle([5, 14, 9, 17], fill=(210, 60, 60, 255))
    dd.rectangle([15, 14, 19, 17], fill=(70, 130, 220, 255))


def _icono_espada(d, dd):
    # espada diagonal (daño +): hoja + guarda + puño, icono clasico de
    # ataque, mas legible en pocos pixeles que una mano/puño.
    hoja = [(18, 4), (20, 6), (11, 15), (7, 16), (8, 12)]
    guarda = [6, 14, 11, 16]
    puño = [6, 16, 8, 19]
    d.polygon(hoja, fill=255)
    d.rectangle(guarda, fill=255)
    d.rectangle(puño, fill=255)
    dd.polygon(hoja, outline=_ICONO_NEGRO, width=1)
    dd.line([(17, 5), (11, 11)], fill=_ICONO_BLANCO, width=1)
    dd.rectangle(guarda, outline=_ICONO_NEGRO, width=1)
    dd.rectangle(puño, outline=_ICONO_NEGRO, width=1)


def _icono_chevrons(d, dd):
    # speed_up: PERMANENTE - doble flecha hacia arriba, estilo "subida de
    # rango".
    sup = [(12, 4), (19, 11), (15, 11), (12, 8), (9, 11), (5, 11)]
    inf = [(12, 11), (19, 18), (15, 18), (12, 15), (9, 18), (5, 18)]
    d.polygon(sup, fill=255)
    d.polygon(inf, fill=255)
    dd.polygon(sup, outline=_ICONO_NEGRO, width=1)
    dd.polygon(inf, outline=_ICONO_NEGRO, width=1)


def _icono_lightning(d, dd):
    rayo = [(14, 4), (7, 12), (11, 12), (9, 19), (18, 10), (13, 10)]
    d.polygon(rayo, fill=255)
    dd.polygon(rayo, outline=_ICONO_NEGRO, width=1)
    dd.line([(13, 6), (10, 11)], fill=_ICONO_BLANCO, width=1)


_POWERUP_ICONOS = {
    "extra_life": lambda d, dd: _icono_heart(d, dd, grande=False),
    "max_life_up": lambda d, dd: _icono_heart(d, dd, grande=True),
    "shield": _icono_shield,
    "fast_shoot": _icono_dardo_veloz,
    "rapid_fire": _icono_pistola,
    "triple_shot": _icono_triple,
    "piercing": _icono_pierce,
    "attract": _icono_magnet,
    "damage_up": _icono_espada,
    "speed_up": _icono_chevrons,
    "lightning_field": _icono_lightning,
}


def build_powerup_body(kind):
    """Cuerpo tintable de la insignia: la SILUETA del icono propio de
    `kind` (blanco solido -> se tinta al color del bonus en tiempo real,
    igual que el resto de sprites tintables), dibujada directo a
    resolucion nativa (sin supersampling) dentro del hueco que deja el
    marco -ver POWERUP_MARCO_ANCHO-. El marco biselado y el relieve del
    icono van sin tintar en build_powerup_detail."""
    s = POWERUP_BADGE_PX
    img = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(img)
    detalle_descartable = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dd_descartable = ImageDraw.Draw(detalle_descartable)
    dibujar_icono = _POWERUP_ICONOS.get(kind)
    if dibujar_icono is not None:
        dibujar_icono(d, dd_descartable)
    mascara = img.point(lambda p: 255 if p > 0 else 0)
    cuerpo_rgba = Image.merge("RGBA", (img, img, img, mascara))
    return cuerpo_rgba, mascara


def _dibujar_marco_pixel(d, s, b):
    """Marco biselado tipo boton de 16 bits: negro exterior, dos anillos
    caqui (claro arriba/izquierda, oscuro abajo/derecha - la luz "cae"
    desde arriba-izquierda) y negro interior separando del relleno
    tintado."""
    negro = (12, 10, 8, 255)
    caqui_claro = (230, 216, 178, 255)
    caqui_medio = (178, 164, 124, 255)
    caqui_oscuro = (104, 92, 64, 255)

    d.rectangle([0, 0, s - 1, s - 1], outline=negro, width=1)

    for i in range(1, b - 1):
        claro = caqui_claro if i == 1 else caqui_medio
        oscuro = caqui_oscuro if i == 1 else caqui_medio
        d.line([(i, i), (s - 1 - i, i)], fill=claro)
        d.line([(i, i), (i, s - 1 - i)], fill=claro)
        d.line([(i, s - 1 - i), (s - 1 - i, s - 1 - i)], fill=oscuro)
        d.line([(s - 1 - i, i), (s - 1 - i, s - 1 - i)], fill=oscuro)

    d.rectangle([b - 1, b - 1, s - b, s - b], outline=negro, width=1)


def build_powerup_detail(kind):
    """Capa sin tintar: marco biselado + relieve/acentos del icono propio
    de `kind` (contorno, brillos, y algun color fijo puntual como las
    puntas del iman), siempre encima del relleno tintado sin importar el
    color del bonus."""
    s = POWERUP_BADGE_PX
    detalle = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(detalle)
    _dibujar_marco_pixel(d, s, POWERUP_MARCO_ANCHO)
    descartable = Image.new("L", (s, s), 0)
    d_descartable = ImageDraw.Draw(descartable)
    dibujar_icono = _POWERUP_ICONOS.get(kind)
    if dibujar_icono is not None:
        dibujar_icono(d_descartable, d)
    return detalle


def build_powerup(kind):
    body_rgba, _mascara = build_powerup_body(kind)
    detail = build_powerup_detail(kind)
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

    # "saucer" se guarda como "mothership" por compatibilidad con el nombre
    # de archivo que ya usaba el jefe Centinela Corrupto (ver
    # BOSS_SPRITE_PREFIX en modules/systems/sprites.py). "anomaly" tiene su
    # propio archivo: ya no comparte silueta con "saucer".
    BOSS_FILE_PREFIX = {"saucer": "mothership", "dragon": "dragon", "titan": "titan", "anomaly": "anomaly"}
    for kind in BOSS_KINDS:
        boss_layers = build_boss(kind)
        prefix = BOSS_FILE_PREFIX[kind]
        for layer_name, img in boss_layers.items():
            written.append(save(img, "boss", f"{prefix}_{layer_name}.png"))

    written.append(save(build_mega_cruiser(), "boss", "mega_cruiser.png"))
    written.append(save(build_mega_sphere(), "boss", "mega_sphere.png"))

    tentaculo_layers = build_titan_tentaculo()
    for layer_name, img in tentaculo_layers.items():
        written.append(save(img, "boss", f"titan_tentaculo_{layer_name}.png"))

    for i in range(DRAGON_ROBOT_FRAMES):
        apertura = i / (DRAGON_ROBOT_FRAMES - 1)
        robot_layers = build_dragon_robot(apertura)
        for layer_name, img in robot_layers.items():
            written.append(save(img, "boss", f"dragon_robot_{i:02d}_{layer_name}.png"))

    for kind in POWERUP_KINDS:
        powerup_layers = build_powerup(kind)
        for layer_name, img in powerup_layers.items():
            written.append(save(img, "powerups", f"{kind}_{layer_name}.png"))

    if verbose:
        print(f"{len(written)} sprites generados en {OUT_DIR}")
    return written


if __name__ == "__main__":
    generate_all()
