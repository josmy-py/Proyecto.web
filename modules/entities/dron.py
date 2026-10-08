"""
Dron escolta: ayudante que da la mejora "DRON ESCOLTA" (ver
modules/systems/mejoras.py). Vuela pegado a un costado de la nave y
apunta al enemigo mas cercano que tenga por delante (arriba). Sus balas son
Bullet con un poco de desvio lateral, asi que main.py las trata como un
disparo mas."""

import math

import pygame

from modules.constants import WHITE, GAME_WIDTH
from modules.entities.bullet import Bullet
from modules.systems import pixelfx

CONTORNO = pixelfx.CONTORNO
METAL = (150, 160, 190)
METAL_OSCURO = (78, 84, 120)
OJO = (120, 255, 200)
HELICE = (200, 230, 255)

_ARTE = [
    "oooo.....oooo",
    "hhhh.....hhhh",
    "..o.......o..",
    "..ooooooooo..",
    ".ommmmmmmmmo.",
    "ommmeewweemmo",
    "ommmeewweemmo",
    ".oddmmmmmddo.",
    "..odddddddo..",
    "...o.o.o.o...",
]
_ARTE_GIRO = [
    ".oooo...oooo.",
    "..hh.....hh..",
    "..o.......o..",
    "..ooooooooo..",
    ".ommmmmmmmmo.",
    "ommmeewweemmo",
    "ommmeewweemmo",
    ".oddmmmmmddo.",
    "..odddddddo..",
    "...o.o.o.o...",
]

ESCALA = 3
_cache = {}


class BalaDron(Bullet):
    """Bullet que ademas se corre de costado (vx) para ir al blanco."""

    def __init__(self, x, y, vx, piercing, color):
        super().__init__(x, y, piercing=piercing, color=color)
        self.vx = vx

    def update(self):
        self.x += self.vx
        super().update()
        if not -10 < self.x < GAME_WIDTH + 10:
            self.active = False


def _sprite(cuadro):
    surf = _cache.get(cuadro)
    if surf is None:
        filas = _ARTE if cuadro == 0 else _ARTE_GIRO
        colores = {"o": CONTORNO, "m": METAL, "d": METAL_OSCURO, "e": OJO, "w": WHITE, "h": HELICE}
        surf = pygame.Surface((len(filas[0]) * ESCALA, len(filas) * ESCALA), pygame.SRCALPHA)
        for y, fila in enumerate(filas):
            for x, ch in enumerate(fila):
                c = colores.get(ch)
                if c is not None:
                    surf.fill(c, (x * ESCALA, y * ESCALA, ESCALA, ESCALA))
        _cache[cuadro] = surf
    return surf


class DronEscolta:
    CADENCIA = 28
    DISTANCIA = 60

    def __init__(self, ship, lado):
        self.lado = lado
        self.x = ship.x + lado * self.DISTANCIA
        self.y = ship.y + 6
        self.t = 0
        self.timer = 20 + (10 if lado > 0 else 0)
        self.fogonazo = 0

    def update(self, ship, objetivos):
        self.t += 1
        if self.fogonazo > 0:
            self.fogonazo -= 1
        destino_x = ship.x + self.lado * self.DISTANCIA
        destino_y = ship.y + 8 + math.sin(self.t * 0.07 + self.lado) * 5
        self.x += (destino_x - self.x) * 0.2
        self.y += (destino_y - self.y) * 0.2

        self.timer -= 1
        if self.timer > 0:
            return []
        # el blanco mas cercano dentro de un cono hacia arriba
        mejor, mejor_d = None, 1e9
        for o in objetivos:
            if not getattr(o, "active", True) or getattr(o, "entrando", False):
                continue
            dy = self.y - o.y
            if dy < 30 or abs(o.x - self.x) > dy * 0.7 + 40:
                continue
            d = math.hypot(o.x - self.x, dy)
            if d < mejor_d:
                mejor, mejor_d = o, d
        if mejor is None:
            return []
        self.timer = self.CADENCIA
        self.fogonazo = 5
        # la bala sube a 9 px por cuadro: el desvio lateral la lleva al blanco
        cuadros = max(1.0, (self.y - mejor.y) / 9)
        vx = max(-5.0, min(5.0, (mejor.x - self.x) / cuadros))
        return [BalaDron(self.x, self.y - 14, vx, ship.piercing_active, OJO)]

    def draw(self, screen, offset_x=0, offset_y=0):
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        # propulsor abajo
        largo = 4 + (self.t // 3) % 3 * 2
        screen.fill((40, 140, 120), (cx - 4, cy + 14, 8, largo + 3))
        screen.fill(OJO, (cx - 2, cy + 14, 4, largo))
        pixelfx.dibujar_halo(screen, OJO, cx, cy, 26 if self.fogonazo else 18)
        spr = _sprite((self.t // 3) % 2)
        screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() // 2))
        if self.fogonazo:
            screen.fill(WHITE, (cx - 2, cy - 20, 4, 6))
            screen.fill(OJO, (cx - 4, cy - 18, 8, 2))
