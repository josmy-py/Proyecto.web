"""
Carga, tintado y cacheo de los sprites PNG de assets/sprites.

Los PNG de cuerpo y alas estan en escala de grises: al multiplicarlos por un
color (BLEND_RGBA_MULT) se obtiene esa pieza pintada de ese color conservando
el sombreado. Gracias a eso el aspecto (skin) de cada nave o jefe
se pinta sin necesidad de tener un PNG por cada combinacion de color posible.

Si falta la carpeta assets/sprites el juego no se cae: todas las funciones
devuelven None y las entidades simplemente no dibujan su cuerpo (las
naves/rocas/jefes ya no generan una silueta de respaldo por codigo, ver
sus draw()); los "detalles" en tiempo real (cupula, luces, barra de vida,
particulas...) siguen animandose igual.

Regenerar los PNG:  python tools/generate_pixel_sprites.py
(los asteroides se dibujan por codigo, ver modules/entities/asteroid.py)
"""

import os

import pygame

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")

SHIP_SCALE = {
    "scout": 1.58,
    "tank": 1.72,
    "interceptor": 1.62,
    "bomber": 1.76,
}
ENEMY_SCALE = 2.90

ENEMY_KINDS = ("fighter", "drone", "gunner")

# body_type del jefe (ver modules/core/boss_system.py) -> prefijo de archivo
# en assets/sprites/boss/ (pixel art de tools/generate_pixel_sprites.py,
# con capa _neon). Un kind que no figura aca se usa tal cual
# como prefijo (dragon_a, titan_px, ...).
BOSS_SPRITE_PREFIX = {
    "saucer": "centinela",
}

# Tamano por defecto de un jefe normal en pantalla (lo usan las barras y
# los radios de colision de main.py y boss_system.py).
BOSS_SPRITE_W, BOSS_SPRITE_H = 320, 170
BOSS_DISPLAY_W = 230
BOSS_DISPLAY_H = round(BOSS_DISPLAY_W * BOSS_SPRITE_H / BOSS_SPRITE_W)

_MAX_COMPOSED = 160
_MAX_ROTATIONS = 1200
_ROT_STEP = 6

_raw_cache = {}
_composed_cache = {}
_rotation_cache = {}
_missing_reported = set()


def _cap(cache, limit):
    while len(cache) > limit:
        cache.pop(next(iter(cache)))


def _quantize(color, step=8):
    r, g, b = color[0], color[1], color[2]
    q = lambda v: min(255, max(0, int(v) // step * step))
    return (q(r), q(g), q(b))


def load_raw(*path_parts):
    """Carga un PNG (con cache). Devuelve None si no existe o falla."""
    key = path_parts
    if key in _raw_cache:
        return _raw_cache[key]

    path = os.path.join(SPRITES_DIR, *path_parts)
    surface = None
    if os.path.isfile(path):
        try:
            surface = pygame.image.load(path)
            if pygame.display.get_init() and pygame.display.get_surface() is not None:
                surface = surface.convert_alpha()
        except pygame.error:
            surface = None
    elif path not in _missing_reported:
        _missing_reported.add(path)
        print(f"[sprites] no encontrado: {path} (no se dibujara esa pieza)")

    _raw_cache[key] = surface
    return surface


def available():
    return os.path.isdir(SPRITES_DIR)


def tint(surface, color):
    """Copia el sprite multiplicado por color (conserva el canal alfa)."""
    out = surface.copy()
    out.fill((int(color[0]), int(color[1]), int(color[2]), 255),
             special_flags=pygame.BLEND_RGBA_MULT)
    return out


def _scaled(surface, width, height):
    width = max(1, int(width))
    height = max(1, int(height))
    if surface.get_width() == width and surface.get_height() == height:
        return surface
    try:
        return pygame.transform.smoothscale(surface, (width, height))
    except (ValueError, pygame.error):
        return pygame.transform.scale(surface, (width, height))


def _scaled_pixelado(surface, width, height):
    """Como _scaled() pero SIN suavizar (pygame.transform.scale, no
    smoothscale): para el pixel art, que se dibuja a resolucion nativa
    baja y sin antialiasing. Con smoothscale se perderia el borde en
    bloque del estilo pixel-art."""
    width = max(1, int(width))
    height = max(1, int(height))
    if surface.get_width() == width and surface.get_height() == height:
        return surface
    return pygame.transform.scale(surface, (width, height))


def _compose_layers(folder, kind, body_color, wing_color, width, height, con_ala=True):
    body = load_raw(folder, f"{kind}_body.png")
    wing = load_raw(folder, f"{kind}_wing.png") if con_ala else None
    detail = load_raw(folder, f"{kind}_detail.png")
    if body is None and wing is None:
        return None

    ref = body if body is not None else wing
    canvas = pygame.Surface(ref.get_size(), pygame.SRCALPHA)
    if wing is not None:
        canvas.blit(tint(wing, wing_color), (0, 0))
    if body is not None:
        canvas.blit(tint(body, body_color), (0, 0))
    if detail is not None:
        canvas.blit(detail, (0, 0))
    return _scaled(canvas, width, height)


def get_ship_surface(ship_type, body_color, wing_color, width, height):
    """Nave del jugador ya tintada y escalada a (width, height)."""
    key = ("ship", ship_type, _quantize(body_color), _quantize(wing_color),
           int(width), int(height))
    if key in _composed_cache:
        return _composed_cache[key]

    if es_nave_pixel(ship_type):
        surface = _compose_pixel("ships", ship_type, body_color, wing_color,
                                 width, height, color_neon(wing_color))
    else:
        surface = _compose_layers("ships", ship_type, body_color, wing_color, width, height)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


def get_ship_size(ship_type, base_width, base_height):
    if es_nave_pixel(ship_type):
        return tamano_pixel("ships", ship_type)
    scale = SHIP_SCALE.get(ship_type, 1.45)
    return int(base_width * scale), int(base_height * scale)


# ---------------------------------------------------------------- naves pixel art
# Las naves y enemigos de tools/generate_pixel_sprites.py traen una capa "_neon" (lineas
# que brillan) y una "_glow" (halo suave a 4x). body/wing/neon/detail vienen
# a la resolucion de la grilla y se agrandan sin suavizar; el halo si se
# suaviza. Si una clase no tiene "_neon" se usa el camino viejo de arriba.

SHIP_PIXEL = 2          # cada celda de la grilla = SHIP_PIXEL x SHIP_PIXEL en pantalla
_COLOR_TOBERA = (200, 252, 255)

_nave_pixel_cache = {}
_toberas_cache = {}


def es_pixel(folder, kind):
    clave = (folder, kind)
    if clave not in _nave_pixel_cache:
        _nave_pixel_cache[clave] = os.path.isfile(
            os.path.join(SPRITES_DIR, folder, f"{kind}_neon.png"))
    return _nave_pixel_cache[clave]


def es_nave_pixel(ship_type):
    return es_pixel("ships", ship_type)


def tamano_pixel(folder, kind, escala=SHIP_PIXEL):
    """Tamaño en pantalla de un sprite pixel art agrandado escala veces."""
    grilla = load_raw(folder, f"{kind}_body.png")
    return grilla.get_width() * escala, grilla.get_height() * escala


def color_neon(color):
    """Color de alas aclarado hacia el blanco: lo que usan las lineas neon."""
    return tuple(min(255, int(c * 0.45 + 140)) for c in color[:3])


def _compose_pixel(folder, kind, body_color, wing_color, width, height, tono, angulo=0):
    """Arma el sprite a la resolucion de la grilla, lo gira ahi (si angulo)
    y recien despues lo agranda sin suavizar: asi el giro tambien queda en
    pixeles grandes y parejos. El halo se gira y se escala suavizado."""
    body = load_raw(folder, f"{kind}_body.png")
    wing = load_raw(folder, f"{kind}_wing.png")
    if body is None and wing is None:
        return None
    ref = body if body is not None else wing
    canvas = pygame.Surface(ref.get_size(), pygame.SRCALPHA)
    if wing is not None:
        canvas.blit(tint(wing, wing_color), (0, 0))
    if body is not None:
        canvas.blit(tint(body, body_color), (0, 0))
    neon = load_raw(folder, f"{kind}_neon.png")
    if neon is not None:
        canvas.blit(tint(neon, tono), (0, 0))
    detail = load_raw(folder, f"{kind}_detail.png")
    if detail is not None:
        canvas.blit(detail, (0, 0))

    factor = max(1, round(width / ref.get_width()))
    if angulo:
        canvas = pygame.transform.rotate(canvas, angulo)
    final = (canvas.get_width() * factor, canvas.get_height() * factor)
    if not angulo:
        final = (int(width), int(height))

    out = pygame.Surface(final, pygame.SRCALPHA)
    glow = load_raw(folder, f"{kind}_glow.png")
    if glow is not None:
        if angulo:
            glow = pygame.transform.rotozoom(glow, angulo, 1.0)
        out.blit(tint(_scaled(glow, *final), tono), (0, 0))
    out.blit(_scaled_pixelado(canvas, *final), (0, 0))
    return out


def get_enemy_surface_girado(kind, body_color, wing_color, size, angulo):
    """Como get_enemy_surface() pero girado en la grilla (pasos de _ROT_STEP
    grados): para los platillos, que giran sin parar."""
    bucket = int(round(angulo / _ROT_STEP)) * _ROT_STEP % 360
    if not es_pixel("enemies", kind) or bucket == 0:
        return get_enemy_surface(kind, body_color, wing_color, size)
    escala = max(1, round(size * ENEMY_SCALE / 28))
    w, h = tamano_pixel("enemies", kind, escala)
    key = ("enemy_giro", kind, _quantize(body_color), _quantize(wing_color), w, bucket)
    surf = _rotation_cache.get(key)
    if surf is None:
        surf = _compose_pixel("enemies", kind, body_color, wing_color, w, h,
                              color_neon(body_color), bucket)
        _rotation_cache[key] = surf
        _cap(_rotation_cache, _MAX_ROTATIONS)
    return surf


def get_ship_nozzles(ship_type):
    """Puntos de salida de las toberas de una nave pixel art, en pixeles de
    pantalla relativos al centro del sprite: [(dx, dy), ...]. Se obtienen
    buscando en la capa de detalle las celdas encendidas que no tienen otra
    celda encendida debajo (la punta de cada tobera)."""
    if ship_type in _toberas_cache:
        return _toberas_cache[ship_type]
    puntos = []
    detail = load_raw("ships", f"{ship_type}_detail.png") if es_nave_pixel(ship_type) else None
    if detail is not None:
        w, h = detail.get_size()

        def encendida(x, y):
            return y < h and tuple(detail.get_at((x, y)))[:3] == _COLOR_TOBERA

        for x in range(w):
            for y in range(h):
                if encendida(x, y) and not encendida(x, y + 1):
                    puntos.append(((x + 0.5 - w / 2) * SHIP_PIXEL, (y + 1 - h / 2) * SHIP_PIXEL))
    _toberas_cache[ship_type] = puntos
    return puntos


def get_enemy_surface(kind, body_color, wing_color, size):
    """Nave enemiga tintada. size = radio logico usado en las colisiones."""
    if es_pixel("enemies", kind):
        escala = max(1, round(size * ENEMY_SCALE / 28))
        w, h = tamano_pixel("enemies", kind, escala)
        key = ("enemy", kind, _quantize(body_color), _quantize(wing_color), w)
        if key not in _composed_cache:
            _composed_cache[key] = _compose_pixel(
                "enemies", kind, body_color, wing_color, w, h, color_neon(body_color))
            _cap(_composed_cache, _MAX_COMPOSED)
        return _composed_cache[key]

    px = max(8, int(size * ENEMY_SCALE))
    key = ("enemy", kind, _quantize(body_color), _quantize(wing_color), px)
    if key in _composed_cache:
        return _composed_cache[key]

    surface = _compose_layers("enemies", kind, body_color, wing_color, px, px)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


def get_boss_surface(body_color, wing_color, width=BOSS_DISPLAY_W, height=BOSS_DISPLAY_H, kind="saucer"):
    """Nave nodriza de un jefe ya tintada y escalada a (width, height).

    Como con las naves, "body" tiñe el casco central y "wing" tiñe el
    anillo exterior de nodos (se llama igual por compartir _compose_layers,
    aunque aqui no sea literalmente un ala). kind es el body_type del jefe
    (ver BossDefinition en modules/core/boss_system.py): decide que silueta
    de assets/sprites/boss/ se usa (BOSS_SPRITE_PREFIX).
    """
    prefix = BOSS_SPRITE_PREFIX.get(kind, kind)
    key = ("boss", prefix, _quantize(body_color), _quantize(wing_color), int(width), int(height))
    if key in _composed_cache:
        return _composed_cache[key]

    if es_pixel("boss", prefix):
        surface = _compose_pixel("boss", prefix, body_color, wing_color, width, height, color_neon(wing_color))
    else:
        surface = _compose_layers("boss", prefix, body_color, wing_color, width, height)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


# Coloso Estelar (oleada 50, ver modules/entities/mega_boss.py): pixel art
# de tools/generate_pixel_sprites.py con colores fijos por fase.
MEGA_FASES = {
    "cruiser": ("coloso_crucero", (140, 150, 175), (70, 110, 170)),
    "sphere": ("coloso_esfera", (150, 140, 165), (170, 50, 90)),
}
MEGA_ESCALA = 3


def get_mega_boss_surface(phase):
    """Sprite del Coloso para la fase pedida ("cruiser" o "sphere") a su
    tamaño de juego. None si faltan los PNG."""
    datos = MEGA_FASES.get(phase)
    if datos is None:
        return None
    kind, casco, alas = datos
    key = ("mega_boss", phase)
    if key in _composed_cache:
        return _composed_cache[key]
    surface = None
    if es_pixel("boss", kind):
        w, h = tamano_pixel("boss", kind, MEGA_ESCALA)
        surface = _compose_pixel("boss", kind, casco, alas, w, h, color_neon(alas))
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


def get_rotated(surface, angle, key):
    """Rotacion cacheada en pasos de 6 grados (key identifica al sprite base)."""
    if surface is None:
        return None
    bucket = int(round(angle / _ROT_STEP)) * _ROT_STEP % 360
    if bucket == 0:
        return surface

    cache_key = (key, bucket)
    cached = _rotation_cache.get(cache_key)
    if cached is not None:
        return cached

    rotated = pygame.transform.rotate(surface, bucket)
    _rotation_cache[cache_key] = rotated
    _cap(_rotation_cache, _MAX_ROTATIONS)
    return rotated


def blit_centered(target, surface, cx, cy, offset_x=0, offset_y=0):
    """Dibuja el sprite centrado en (cx, cy). Devuelve False si no habia sprite."""
    if surface is None:
        return False
    rect = surface.get_rect(center=(int(cx) + offset_x, int(cy) + offset_y))
    target.blit(surface, rect)
    return True


