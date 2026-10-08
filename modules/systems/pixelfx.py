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


# ------------------------------------------------------ explosiones y misiles

def disco(color, radio):
    """Circulo lleno en pixeles grandes (nucleo del destello de explosion)."""
    celdas = max(1, int(radio) // PIXEL)
    clave = ("disco", _q(color), celdas)
    surf = _cache.get(clave)
    if surf is not None:
        return surf
    chico = pygame.Surface((celdas * 2 + 1, celdas * 2 + 1), pygame.SRCALPHA)
    pygame.draw.circle(chico, color[:3], (celdas, celdas), celdas)
    surf = pygame.transform.scale(chico, (chico.get_width() * PIXEL, chico.get_height() * PIXEL))
    return _guardar(clave, surf)


def apagar(color, k):
    """Color de una chispa segun la vida que le queda (k de 1 a 0): blanca
    al nacer, del color propio en el medio y oscura al final."""
    if k > 0.7:
        return aclarar(color, (k - 0.7) / 0.3 * 0.8)
    f = 0.35 + 0.65 * k / 0.7
    return tuple(int(c * f) for c in color[:3])


def misil(screen, x, y, angulo, t, cuerpo=(200, 206, 224), punta=(255, 70, 90), fuego=(255, 190, 80),
          largo=6):
    """Cohete pixel: cuerpo de cuadraditos con contorno, aletas, punta que
    parpadea y tobera encendida con halo."""
    dx, dy = math.cos(angulo), math.sin(angulo)
    nx, ny = -dy, dx
    for k in range(largo):
        px, py = int(x - dx * k * 3), int(y - dy * k * 3)
        screen.fill(CONTORNO, (px - 4, py - 4, 8, 8))
    for k in range(largo):
        px, py = int(x - dx * k * 3), int(y - dy * k * 3)
        screen.fill(cuerpo, (px - 3, py - 3, 6, 6))
    cola = (largo - 1) * 3
    oscuro = tuple(int(c * 0.6) for c in cuerpo)
    for s in (-1, 1):
        screen.fill(oscuro, (int(x - dx * cola + nx * s * 6) - 2, int(y - dy * cola + ny * s * 6) - 2, 5, 5))
    color = punta if (t // 4) % 2 else (255, 255, 255)
    screen.fill(color, (int(x + dx * 3) - 3, int(y + dy * 3) - 3, 6, 6))
    fx, fy = x - dx * (cola + 6), y - dy * (cola + 6)
    dibujar_halo(screen, fuego, fx, fy, 10)
    screen.fill(fuego, (int(fx) - 3, int(fy) - 3, 6, 6))
    screen.fill((255, 255, 255), (int(fx) - 1, int(fy) - 1, 3, 3))
