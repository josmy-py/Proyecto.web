"""
Generador de los asteroides del juego (assets/sprites/asteroids/*.png).

Los asteroides se dibujan de forma procedural con Pillow (rocas en escala
de grises que el juego tinta en runtime). Las naves, enemigos y jefes son
pixel art y salen de tools/generate_pixel_sprites.py, que este script
tambien ejecuta. El juego SOLO necesita pygame para cargarlos; Pillow
unicamente hace falta para volver a generarlos:

    pip install pillow numpy
    python tools/generate_sprites.py
"""

import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4  # supersampling: se dibuja x4 y se reduce con LANCZOS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "sprites")

ROCK_SIZE = 128


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _blank_mask(w, h):
    return Image.new("L", (w * SS, h * SS), 0)


def _sc(points):
    return [(x * SS, y * SS) for x, y in points]


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


def save(img, *parts):
    path = os.path.join(OUT_DIR, *parts)
    _ensure_dir(os.path.dirname(path))
    img.save(path)
    return path


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

# ----------------------------------------------------------------- ejecucion

ASTEROID_VARIANTS = 14


def generate_all(verbose=True):
    _ensure_dir(OUT_DIR)
    written = []

    # naves, enemigos y jefes: pixel art neon
    import generate_pixel_sprites
    generate_pixel_sprites.main()

    for i in range(ASTEROID_VARIANTS):
        written.append(save(build_asteroid(1000 + i), "asteroids", f"asteroid_{i}.png"))

    if verbose:
        print(f"{len(written)} sprites generados en {OUT_DIR}")
    return written


if __name__ == "__main__":
    generate_all()
