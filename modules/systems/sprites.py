"""
Carga, tintado y cacheo de los sprites PNG de assets/sprites.

Los PNG de cuerpo y alas estan en escala de grises: al multiplicarlos por un
color (BLEND_RGBA_MULT) se obtiene esa pieza pintada de ese color conservando
el sombreado. Gracias a eso el aspecto (skin) de cada nave, jefe o power-up
se pinta sin necesidad de tener un PNG por cada combinacion de color posible.

Si falta la carpeta assets/sprites el juego sigue funcionando: todas las
funciones devuelven None y las entidades dibujan su version vectorial de
respaldo.

Regenerar los PNG:  python tools/generate_sprites.py
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
ASTEROID_SCALE = 2.25
ENEMY_SCALE = 2.90

ASTEROID_VARIANTS = 14
ENEMY_KINDS = ("fighter", "drone", "gunner")

# body_type del jefe (ver modules/core/boss_system.py) -> prefijo de archivo
# en assets/sprites/boss/. "saucer" y "anomaly" comparten el sprite
# "mothership" (el platillo clasico); "dragon" y "titan" tienen su propia
# silueta generada por tools/generate_sprites.py.
BOSS_SPRITE_PREFIX = {
    "saucer": "mothership",
    "anomaly": "mothership",
    "dragon": "dragon",
    "titan": "titan",
}

# Geometria del sprite del jefe final (debe coincidir con BOSS_* en
# tools/generate_sprites.py). Se expresa en fracciones del ancho/alto ya
# escalados para que boss.py pueda ubicar encima la cupula animada, el
# piloto y el anillo de luces parpadeantes sin conocer los pixeles del PNG.
BOSS_SPRITE_W, BOSS_SPRITE_H = 320, 170
BOSS_DISPLAY_W = 230
BOSS_DISPLAY_H = round(BOSS_DISPLAY_W * BOSS_SPRITE_H / BOSS_SPRITE_W)
BOSS_PLATFORM_CY_FRAC = 0.2882   # centro vertical de la plataforma de la cupula
BOSS_PLATFORM_RX_FRAC = 0.1375
BOSS_PLATFORM_RY_FRAC = 0.0882
BOSS_RING_RX_FRAC = 0.3969       # radio del anillo de nodos (para las luces animadas)
BOSS_RING_RY_FRAC = 0.2147

_MAX_COMPOSED = 160
_MAX_ROTATIONS = 600
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
        print(f"[sprites] no encontrado: {path} (se usara el dibujo vectorial)")

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

    surface = _compose_layers("ships", ship_type, body_color, wing_color, width, height)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


def get_ship_size(ship_type, base_width, base_height):
    scale = SHIP_SCALE.get(ship_type, 1.45)
    return int(base_width * scale), int(base_height * scale)


def get_enemy_surface(kind, body_color, wing_color, size):
    """Nave enemiga tintada. size = radio logico usado en las colisiones."""
    px = max(8, int(size * ENEMY_SCALE))
    key = ("enemy", kind, _quantize(body_color), _quantize(wing_color), px)
    if key in _composed_cache:
        return _composed_cache[key]

    surface = _compose_layers("enemies", kind, body_color, wing_color, px, px)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


def get_asteroid_surface(variant, size, color):
    """Roca tintada. size = radio logico usado en las colisiones."""
    px = max(8, int(size * ASTEROID_SCALE))
    px = (px // 4) * 4  # cuantizado para reutilizar cache
    key = ("rock", int(variant) % ASTEROID_VARIANTS, _quantize(color, 16), px)
    if key in _composed_cache:
        return _composed_cache[key]

    raw = load_raw("asteroids", f"asteroid_{int(variant) % ASTEROID_VARIANTS}.png")
    surface = None
    if raw is not None:
        surface = _scaled(tint(raw, color), px, px)

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
    prefix = BOSS_SPRITE_PREFIX.get(kind, "mothership")
    key = ("boss", prefix, _quantize(body_color), _quantize(wing_color), int(width), int(height))
    if key in _composed_cache:
        return _composed_cache[key]

    surface = _compose_layers("boss", prefix, body_color, wing_color, width, height)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


POWERUP_KINDS = (
    "extra_life", "fast_shoot", "triple_shot", "shield", "piercing", "attract",
    "damage_up", "speed_up", "max_life_up", "rapid_fire", "lightning_field",
)


def get_powerup_surface(buff_type, color, size):
    """Capsula tipo 'caja de bonus' (estilo recreativa de los 90) tintada
    con el color del bonus y escalada a un cuadrado de "size" px. El icono
    grabado (corazon, rayo, iman...) cambia segun buff_type; ver
    tools/generate_sprites.py. None si faltan los PNG (el llamador cae al
    dibujo vectorial de circulo con etiqueta)."""
    key = ("powerup", buff_type, _quantize(color), int(size))
    if key in _composed_cache:
        return _composed_cache[key]

    surface = _compose_layers("powerups", buff_type, color, color, size, size, con_ala=False)
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


def clear_cache():
    _composed_cache.clear()
    _rotation_cache.clear()
