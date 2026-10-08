"""
Efectos en pixel art neon compartidos por balas, enemigos y jefes.

Todo se arma en una grilla chica y se agranda sin suavizar (PIXEL pixeles
de pantalla por celda), igual que las naves de tools/generate_pixel_ships.py.
El brillo se suma con BLEND_RGB_ADD para que se vea como luz neon sobre el
fondo oscuro. Cada superficie se cachea por (forma, color, tamaño), asi que
dibujar cientos de balas por cuadro no vuelve a construir nada.
"""

import pygame

PIXEL = 2
CONTORNO = (12, 6, 34)

_cache = {}
_MAX_CACHE = 400


def _guardar(clave, surf):
    if len(_cache) > _MAX_CACHE:
        _cache.pop(next(iter(_cache)))
    _cache[clave] = surf
    return surf


def _q(color, paso=16):
    return tuple(min(255, int(c) // paso * paso) for c in color[:3])


def aclarar(color, f=0.5):
    """Mezcla el color con blanco (f=1 -> blanco)."""
    return tuple(min(255, int(c + (255 - c) * f)) for c in color[:3])


def _desde_mapa(filas, colores):
    """Superficie a partir de un mapa de caracteres (cada celda = PIXEL)."""
    alto = len(filas)
    ancho = max(len(f) for f in filas)
    surf = pygame.Surface((ancho * PIXEL, alto * PIXEL), pygame.SRCALPHA)
    for y, fila in enumerate(filas):
        for x, ch in enumerate(fila):
            c = colores.get(ch)
            if c is not None:
                surf.fill(c, (x * PIXEL, y * PIXEL, PIXEL, PIXEL))
    return surf


def halo(color, radio):
    """Circulo de luz suave para sumar con BLEND_RGB_ADD."""
    radio = max(2, int(radio))
    clave = ("halo", _q(color), radio)
    surf = _cache.get(clave)
    if surf is not None:
        return surf
    surf = pygame.Surface((radio * 2, radio * 2))
    surf.fill((0, 0, 0))
    pasos = 14
    for i in range(pasos):
        r = int(radio * (1 - i / pasos))
        k = 0.05 + 0.032 * i
        c = tuple(int(v * k) for v in color[:3])
        pygame.draw.circle(surf, c, (radio, radio), max(1, r))
    return _guardar(clave, surf)


def dibujar_halo(screen, color, cx, cy, radio):
    s = halo(color, radio)
    screen.blit(s, (int(cx) - s.get_width() // 2, int(cy) - s.get_height() // 2),
                special_flags=pygame.BLEND_RGB_ADD)


# ------------------------------------------------------------------ jugador

_BALA_JUGADOR = [
    ".n.",
    "nWn",
    "nWn",
    "nWn",
    "ncn",
    ".c.",
]
_BALA_PERFORANTE = [
    "..n..",
    ".nWn.",
    "nWWWn",
    "nWWWn",
    "nWWWn",
    ".nWn.",
    ".ncn.",
    "..c..",
]


def bala_jugador(color, perforante=False):
    clave = ("bj", _q(color), perforante)
    surf = _cache.get(clave)
    if surf is not None:
        return surf
    colores = {"W": (255, 255, 255), "n": aclarar(color, 0.35), "c": color[:3]}
    surf = _desde_mapa(_BALA_PERFORANTE if perforante else _BALA_JUGADOR, colores)
    return _guardar(clave, surf)


# ------------------------------------------------------------------ enemigos

# Las balas enemigas llevan contorno oscuro y centro blanco: se distinguen
# siempre de las del jugador y del fondo, que es lo que permite esquivarlas.
_ORBE = {
    1: [".o.",
        "oWo",
        ".o."],
    2: [".ooo.",
        "occco",
        "ocWco",
        "occco",
        ".ooo."],
    3: ["..ooo..",
        ".occco.",
        "occWcco",
        "ocWWWco",
        "occWcco",
        ".occco.",
        "..ooo.."],
    4: ["...ooo...",
        "..occco..",
        ".occccco.",
        "occcWccco",
        "occWWWcco",
        "occcWccco",
        ".occccco.",
        "..occco..",
        "...ooo..."],
}


def bala_enemiga(color, radio, fase=0):
    """Orbe pixel art con contorno; fase (0/1) alterna el brillo del centro."""
    nivel = 1 if radio <= 2 else 2 if radio <= 3 else 3 if radio <= 5 else 4
    clave = ("be", _q(color), nivel, fase)
    surf = _cache.get(clave)
    if surf is not None:
        return surf
    colores = {
        "o": CONTORNO,
        "c": color[:3],
        "W": (255, 255, 255) if fase == 0 else aclarar(color, 0.6),
    }
    if nivel == 1:
        colores["o"] = color[:3]
    surf = _desde_mapa(_ORBE[nivel], colores)
    return _guardar(clave, surf)
