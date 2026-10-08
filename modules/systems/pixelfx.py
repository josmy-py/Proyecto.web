"""
Efectos en pixel art neon compartidos por balas, enemigos y jefes.

Todo se arma en una grilla chica y se agranda sin suavizar (PIXEL pixeles
de pantalla por celda), igual que las naves de tools/generate_pixel_ships.py.
El brillo se suma con BLEND_RGB_ADD para que se vea como luz neon sobre el
fondo oscuro. Cada superficie se cachea por (forma, color, tamaño), asi que
dibujar cientos de balas por cuadro no vuelve a construir nada.
"""

import math

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


# ------------------------------------------------------------------ jefes

def silueta_blanca(surf):
    """Silueta blanca del sprite (destello al recibir un golpe)."""
    clave = ("blanca", id(surf), surf.get_size())
    s = _cache.get(clave)
    if s is not None:
        return s
    s = pygame.mask.from_surface(surf).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    return _guardar(clave, s)


def barra_jefe(screen, cx, y, ancho, ratio, ratio_anim, color, temblor=(0, 0)):
    """Barra de vida en bloques: el tramo recien perdido queda en blanco un
    momento (ratio_anim) antes de vaciarse."""
    bloque = 6
    n = max(4, ancho // bloque)
    ancho = n * bloque
    x0 = int(cx - ancho // 2) + temblor[0]
    y0 = int(y) + temblor[1]
    alto = 8
    screen.fill(CONTORNO, (x0 - 3, y0 - 3, ancho + 4, alto + 6))
    screen.fill(aclarar(color, 0.2), (x0 - 2, y0 - 2, ancho + 2, 1))
    screen.fill(aclarar(color, 0.2), (x0 - 2, y0 + alto + 1, ancho + 2, 1))
    oscuro = tuple(int(c * 0.22) for c in color[:3])
    claro = aclarar(color, 0.55)
    for i in range(n):
        x = x0 + i * bloque
        f = (i + 1) / n
        if f <= ratio + 1e-6:
            screen.fill(color[:3], (x, y0, bloque - 2, alto))
            screen.fill(claro, (x, y0, bloque - 2, 2))
        elif f <= ratio_anim + 1e-6:
            screen.fill((255, 255, 255), (x, y0, bloque - 2, alto))
        else:
            screen.fill(oscuro, (x, y0, bloque - 2, alto))
    if ratio > 0:
        dibujar_halo(screen, color, x0 + ancho * ratio, y0 + alto // 2, 10)


def carga(screen, color, x, y, progreso, t, radio=16):
    """Aviso de disparo: un nucleo que crece y chispas que se juntan en el
    punto de salida. progreso va de 0 (recien empieza) a 1 (dispara)."""
    progreso = max(0.0, min(1.0, progreso))
    dibujar_halo(screen, color, x, y, radio * (0.6 + progreso * 1.4))
    lado = 2 + int(progreso * 4) * 2
    c = (255, 255, 255) if (t // 3) % 2 else aclarar(color, 0.5)
    screen.fill(c, (int(x) - lado // 2, int(y) - lado // 2, lado, lado))
    dist = radio * 2.2 * (1 - progreso) + 4
    for k in range(6):
        a = k * math.pi / 3 + t * 0.08
        px = int(x + math.cos(a) * dist)
        py = int(y + math.sin(a) * dist)
        screen.fill(aclarar(color, 0.4), (px - 1, py - 1, PIXEL + 1, PIXEL + 1))


def columna_aviso(screen, x, ancho, color, t, y0=0, y1=None):
    """Franja de peligro parpadeante (antes de un rayo): bordes punteados y
    chevrones bajando."""
    if y1 is None:
        y1 = screen.get_height()
    x0 = int(x - ancho / 2)
    vel = (t * 3) % 24
    luz = aclarar(color, 0.3) if (t // 5) % 2 else color[:3]
    for y in range(int(y0) - 24 + vel, int(y1), 24):
        screen.fill(luz, (x0, y, 4, 12))
        screen.fill(luz, (x0 + int(ancho) - 4, y, 4, 12))
        for k in range(3):
            screen.fill(color[:3], (int(x) - 8 + k * 2, y + 4 + k * 2, 16 - k * 4, 2))


_ESQUIRLA = [
    "..w..",
    ".wcw.",
    ".wcw.",
    "wcWcw",
    "wcWcw",
    ".wcw.",
    ".wcw.",
    "..w..",
    "..o..",
]


def esquirla(color, angulo):
    """Lanza de cristal en pixel art apuntando a `angulo` (radianes). Se
    gira en la grilla (pasos de 22.5 grados) y despues se agranda."""
    paso = round(math.degrees(angulo) / 22.5) % 16
    clave = ("esq", _q(color), paso)
    surf = _cache.get(clave)
    if surf is not None:
        return surf
    colores = {"w": aclarar(color, 0.55), "c": color[:3], "W": (255, 255, 255), "o": CONTORNO}
    alto, ancho = len(_ESQUIRLA), len(_ESQUIRLA[0])
    base = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    for y, fila in enumerate(_ESQUIRLA):
        for x, ch in enumerate(fila):
            if ch in colores:
                base.set_at((x, y), colores[ch])
    # el mapa apunta hacia arriba (-90 grados)
    girado = pygame.transform.rotate(base, -(paso * 22.5 + 90))
    surf = pygame.transform.scale(girado, (girado.get_width() * PIXEL, girado.get_height() * PIXEL))
    return _guardar(clave, surf)
