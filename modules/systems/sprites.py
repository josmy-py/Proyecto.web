"""
Carga, tintado y cacheo de los sprites PNG de assets/sprites.

Los PNG de cuerpo y alas estan en escala de grises: al multiplicarlos por un
color (BLEND_RGBA_MULT) se obtiene esa pieza pintada de ese color conservando
el sombreado. Gracias a eso el aspecto (skin) de cada nave, jefe o power-up
se pinta sin necesidad de tener un PNG por cada combinacion de color posible.

Si falta la carpeta assets/sprites el juego no se cae: todas las funciones
devuelven None y las entidades simplemente no dibujan su cuerpo (las
naves/rocas/jefes ya no generan una silueta de respaldo por codigo, ver
sus draw()); los "detalles" en tiempo real (cupula, luces, barra de vida,
particulas...) siguen animandose igual.

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
# en assets/sprites/boss/. "saucer" (Centinela) se guarda como "mothership"
# por compatibilidad de nombre; "dragon", "titan" y "anomaly" (La Anomalia
# Final, casco fracturado con nucleo de vacio) tienen cada uno su propia
# silueta generada por tools/generate_sprites.py.
BOSS_SPRITE_PREFIX = {
    "saucer": "mothership",
    "anomaly": "anomaly",
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

# Titan (pulpo mecanico) no usa el anillo/cupula de arriba: es mas grande
# (ver TITAN_DISPLAY_SCALE, aplicado sobre BOSS_DISPLAY_W/H solo para el) y
# titan_boss.py dibuja la pupila -que sigue a la nave- centrada en
# TITAN_OJO_*_FRAC, encima del aro/iris ya horneado en el sprite (debe
# coincidir con TITAN_OJO_* en tools/generate_sprites.py). Una unica
# fraccion de radio alcanza para x e y porque el sprite se escala siempre
# de forma uniforme (mismo factor en ambos ejes).
TITAN_DISPLAY_SCALE = 1.55
TITAN_OJO_CX_FRAC = 0.5
TITAN_OJO_CY_FRAC = 0.4437
TITAN_OJO_R_FRAC = 0.08125

# Segmento de tentaculo de Titan (ver TENTACULO_* en
# tools/generate_sprites.py): aspecto nativo 96x40, apunta a lo largo de
# +X con la base ancha en x=0 y la garra en el extremo derecho.
TITAN_TENTACULO_W, TITAN_TENTACULO_H = 96, 40

# La Anomalia (calavera glicheada) se dibuja "un poco" mas grande que el
# resto de jefes normales, y boss.py dibuja DOS pupilas dinamicas (una por
# cuenca) centradas en +-ANOMALY_OJO_DX_FRAC/ANOMALY_OJO_CY_FRAC, encima de
# las cuencas vacias ya horneadas en el sprite (debe coincidir con
# ANOMALY_OJO_* en tools/generate_sprites.py).
ANOMALY_DISPLAY_SCALE = 1.18
ANOMALY_OJO_DX_FRAC = 0.1144
ANOMALY_OJO_CY_FRAC = 0.4824
ANOMALY_OJO_R_FRAC = 0.06

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
    smoothscale): usado solo por las insignias de power-up, que se
    generan a proposito a resolucion nativa baja y sin antialiasing (ver
    build_powerup_body/_detail en tools/generate_sprites.py) para que se
    vean en pixeles grandes de verdad. Con smoothscale se perderia el
    borde en bloque del estilo pixel-art."""
    width = max(1, int(width))
    height = max(1, int(height))
    if surface.get_width() == width and surface.get_height() == height:
        return surface
    return pygame.transform.scale(surface, (width, height))


def _compose_layers(folder, kind, body_color, wing_color, width, height, con_ala=True, pixelado=False):
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
    if pixelado:
        # sin suavizar (pygame.transform.scale, no smoothscale): el PNG
        # YA es la grilla nativa chica de un sprite pixel-art (ver
        # build_dragon_robot en tools/generate_sprites.py) -con
        # smoothscale se perderia el borde en bloque de los "pixeles"
        # grandes, mismo criterio que las insignias de power-up.
        return _scaled_pixelado(canvas, width, height)
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


def _compose_pixel(folder, kind, body_color, wing_color, width, height, tono):
    canvas = _compose_layers(folder, kind, body_color, wing_color,
                             width, height, pixelado=True)
    if canvas is None:
        return None
    neon = load_raw(folder, f"{kind}_neon.png")
    glow = load_raw(folder, f"{kind}_glow.png")
    out = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
    if glow is not None:
        out.blit(tint(_scaled(glow, width, height), tono), (0, 0))
    out.blit(canvas, (0, 0))
    if neon is not None:
        out.blit(_scaled_pixelado(tint(neon, tono), width, height), (0, 0))
        # la capa de detalle (contorno, cabina) va siempre arriba del neon
        detail = load_raw(folder, f"{kind}_detail.png")
        if detail is not None:
            out.blit(_scaled_pixelado(detail, width, height), (0, 0))
    return out


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


def get_titan_tentaculo_surface(color, width, height):
    """Segmento de tentaculo de Titan ya tintado y escalado (sin "wing":
    con_ala=False, mismo truco que los power-ups). titan_boss.py encadena
    varias copias rotadas y escaladas para armar cada tentaculo curvo en
    tiempo real -no puede ser un unico PNG fijo porque el largo/curva
    cambian segun a donde ataca."""
    key = ("titan_tentaculo", _quantize(color), int(width), int(height))
    if key in _composed_cache:
        return _composed_cache[key]

    surface = _compose_layers("boss", "titan_tentaculo", color, color, width, height, con_ala=False)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


# Geometria del mega-jefe (oleada 50, ver modules/entities/mega_boss.py).
# A diferencia de los demas jefes no es tintable (colores finales ya
# horneados en el PNG por tools/generate_sprites.py): es un jefe unico, no
# una nave de skin variable. Estas fracciones deben coincidir con las
# MEGA_* de ese script.
MEGA_SPRITE_W, MEGA_SPRITE_H = 380, 210
MEGA_BOSS_DISPLAY_W = 300
MEGA_BOSS_DISPLAY_H = round(MEGA_BOSS_DISPLAY_W * MEGA_SPRITE_H / MEGA_SPRITE_W)
MEGA_SPHERE_DISH_X_FRAC = 0.419
MEGA_SPHERE_DISH_Y_FRAC = 0.335
MEGA_SPHERE_DISH_R_FRAC = 0.076

# Puntos fijos del crucero (fase 1): luces de navegacion que parpadean y
# centro de la bahia de hangar, para la animacion de largada de cazas (ver
# mega_boss.py). Deben coincidir con las MEGA_CRUISER_* de
# tools/generate_sprites.py.
MEGA_CRUISER_PROA_X_FRAC = 0.968
MEGA_CRUISER_PROA_Y_FRAC = 0.580
MEGA_CRUISER_BABOR_X_FRAC = 0.047
MEGA_CRUISER_BABOR_Y_FRAC = 0.523
MEGA_CRUISER_ESTRIBOR_X_FRAC = 0.047
MEGA_CRUISER_ESTRIBOR_Y_FRAC = 0.637
MEGA_CRUISER_BALIZA_X_FRAC = 0.463
MEGA_CRUISER_BALIZA_Y_FRAC = 0.047
MEGA_CRUISER_HANGAR_X_FRAC = 0.447
MEGA_CRUISER_HANGAR_Y_FRAC = 0.780

_MEGA_BOSS_FILE = {"cruiser": "mega_cruiser.png", "sphere": "mega_sphere.png"}


def get_mega_boss_surface(phase, width=MEGA_BOSS_DISPLAY_W, height=MEGA_BOSS_DISPLAY_H):
    """Sprite del mega-jefe para la fase pedida ("cruiser" o "sphere"), ya
    escalado. A diferencia de get_boss_surface no tiñe nada: son colores
    finales horneados en el PNG. None si falta el archivo (dibujo
    vectorial de respaldo en mega_boss.py)."""
    filename = _MEGA_BOSS_FILE.get(phase)
    if filename is None:
        return None
    key = ("mega_boss", phase, int(width), int(height))
    if key in _composed_cache:
        return _composed_cache[key]

    raw = load_raw("boss", filename)
    surface = _scaled(raw, width, height) if raw is not None else None
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


# Dragon del jefe de la oleada 20 (ver modules/entities/dragon_boss.py y
# build_dragon_robot()/DRAGON_ROBOT_* en tools/generate_sprites.py): los
# nombres DRAGON_ROBOT_*/get_dragon_robot_surface se mantienen por
# compatibilidad con el resto del codigo, aunque ya no hay nada robotico
# en el diseño (mismo criterio que BOSS_SPRITE_PREFIX guardando "saucer"
# como "mothership"). Tintable pero con 11 cuadros fijos (apertura 0.0 a
# 1.0) en vez de una unica silueta - "intacto a hecho pedazos":
# dragon_boss.py elige el cuadro mas cercano a su "apertura" (= daño)
# actual, tanto para sus 3 formas fijas por fase como para reproducir el
# deterioro cuadro a cuadro durante la transformacion entre fases.
#
# El PNG en si es pixel art de verdad -una grilla nativa CHICA (ver
# DRAGON_PIXEL_W/H en tools/generate_sprites.py), no una silueta suave
# reducida- asi que se escala siempre sin suavizar (ver
# get_dragon_robot_surface, pixelado=True) para que los "pixeles" grandes
# se vean como bloques solidos y no como un degrade continuo encogido.
DRAGON_ROBOT_SPRITE_W, DRAGON_ROBOT_SPRITE_H = 80, 75
DRAGON_ROBOT_FRAMES = 11
DRAGON_ROBOT_DISPLAY_W = 250
DRAGON_ROBOT_DISPLAY_H = round(DRAGON_ROBOT_DISPLAY_W * DRAGON_ROBOT_SPRITE_H / DRAGON_ROBOT_SPRITE_W)

# Dos ojos (cuencas vacias horneadas, ver DRAGON_OJO_* en
# tools/generate_sprites.py): dragon_boss.py dibuja las dos pupilas -que
# siguen a la nave- centradas en estas fracciones, encima del aro ya
# horneado de cada una (mismo criterio que ANOMALY_OJO_*).
DRAGON_OJO_IZQ_X_FRAC = 0.41875
DRAGON_OJO_DER_X_FRAC = 0.58125
DRAGON_OJO_CY_FRAC = 0.2
DRAGON_OJO_R_FRAC = 0.0375

# Garganta: de aca sale telegrafiado el aliento de fuego (el resplandor en
# si es 100% en tiempo real, ver dragon_boss.py _dibujar_garganta).
DRAGON_GARGANTA_X_FRAC = 0.5
DRAGON_GARGANTA_Y_FRAC = 0.34

# Puntos de herida (fx, fy, inicio, fin) - deben coincidir con
# _DRAGON_DAÑOS en tools/generate_sprites.py: dragon_boss.py los usa para
# saber DONDE spawnear chispas/brasas animadas en tiempo real segun la
# severidad actual (`apertura`), ademas de la grieta ya horneada en el
# sprite.
DRAGON_DAÑOS_FRAC = [
    (0.96875, 0.28, 0.08, 0.42),
    (0.35625, 0.75333, 0.18, 0.52),
    (0.5, 0.62, 0.32, 0.68),
    (0.03125, 0.28, 0.42, 0.78),
    (0.65625, 0.26667, 0.62, 1.00),
]


def get_dragon_robot_surface(apertura, color, width=DRAGON_ROBOT_DISPLAY_W, height=DRAGON_ROBOT_DISPLAY_H):
    """Cuadro del flipbook de daño mas cercano a `apertura` (0.0=Modo
    Explorador casi intacto, 1.0=Modo Destructor hecho pedazos), tintado y
    escalado. None si faltan los PNG."""
    idx = max(0, min(DRAGON_ROBOT_FRAMES - 1, round(apertura * (DRAGON_ROBOT_FRAMES - 1))))
    prefix = f"dragon_robot_{idx:02d}"
    key = ("dragon_robot", idx, _quantize(color), int(width), int(height))
    if key in _composed_cache:
        return _composed_cache[key]

    surface = _compose_layers("boss", prefix, color, color, width, height, con_ala=False, pixelado=True)
    _composed_cache[key] = surface
    _cap(_composed_cache, _MAX_COMPOSED)
    return surface


POWERUP_KINDS = (
    "extra_life", "fast_shoot", "triple_shot", "shield", "piercing", "attract",
    "damage_up", "speed_up", "max_life_up", "rapid_fire", "lightning_field",
)


def get_powerup_surface(buff_type, color, size):
    """Insignia pixel-art (marco biselado caqui/negro + letra dorada,
    tinte propio del bonus solo en el relleno interior; ver
    tools/generate_sprites.py) escalada a un cuadrado de "size" px con
    pixelado real (_scaled_pixelado, sin suavizar) en vez del smoothscale
    que usa el resto de sprites - asi no se pierden los bordes en bloque
    del estilo retro. None si faltan los PNG (el llamador solo dibuja la
    etiqueta de texto, sin insignia de respaldo)."""
    key = ("powerup", buff_type, _quantize(color), int(size))
    if key in _composed_cache:
        return _composed_cache[key]

    body = load_raw("powerups", f"{buff_type}_body.png")
    detail = load_raw("powerups", f"{buff_type}_detail.png")
    surface = None
    if body is not None or detail is not None:
        ref = body if body is not None else detail
        canvas = pygame.Surface(ref.get_size(), pygame.SRCALPHA)
        if body is not None:
            canvas.blit(tint(body, color), (0, 0))
        if detail is not None:
            canvas.blit(detail, (0, 0))
        surface = _scaled_pixelado(canvas, size, size)
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


