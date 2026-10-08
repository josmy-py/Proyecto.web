"""
Mascota de mitad de partida: el Zorrito Espacial.

Al llegar a MASCOTA_OLEADA (la mitad de las 50 oleadas) baja una capsula
de rescate con el zorrito adentro (CapsulaMascota); flota hasta que la nave
la toca y ahi el zorrito se une (ZorritoEspacial) por el resto de la
partida, bonus incluido. Ayuda de tres formas:

  - dispara bolitas de plasma al enemigo mas cercano (asteroides,
    alienigenas o jefes): son BalaZorro, con la misma interfaz que Bullet,
    asi main.py las trata como un disparo mas;
  - arrastra los power-ups cercanos hacia la nave;
  - cada BLOQUEO_CADA cuadros frena con la cola una bala enemiga que iba
    hacia la nave ("¡Yip!").

El arte es pixel art dibujado por codigo (contorno oscuro, dos tonos de
naranja, pecho y punta de la cola en crema, casco de vidrio y mochila
cohete), igual que el tripulante de modules/entities/tripulante.py."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE, AMARILLO
from modules.systems.fonts import get_font, render_text
from modules.systems import neon

MASCOTA_OLEADA = 25

CONTORNO = (48, 22, 18)
NARANJA = (245, 132, 42)
NARANJA_OSCURO = (192, 82, 28)
NARANJA_CLARO = (255, 176, 90)
CREMA = (255, 238, 214)
OREJA_INTERIOR = (255, 170, 150)
OJO = (30, 20, 40)
CASCO = (170, 230, 255)
METAL = (150, 160, 175)
METAL_OSCURO = (86, 94, 110)
LLAMA = (255, 200, 60)
LLAMA_ROJA = (255, 90, 40)
LUZ_ROJA = (255, 60, 80)


# ------------------------------------------------------------------ arte

def _formas_zorro(s, principal, cola_punta, pecho, cola_dy):
    """Formas planas del zorrito mirando a la derecha (se usan para la
    silueta del contorno y para el color)."""
    s.fill(principal, (4, 11, 4, 6))                                   # mochila cohete
    pygame.draw.ellipse(s, principal, (0, 7 + cola_dy, 11, 8))         # cola
    pygame.draw.ellipse(s, cola_punta, (0, 8 + cola_dy, 4, 5))         # punta de la cola
    pygame.draw.ellipse(s, principal, (7, 10, 10, 8))                  # cuerpo
    pygame.draw.ellipse(s, pecho, (12, 11, 4, 5))                      # pecho
    s.fill(principal, (9, 17, 2, 2))                                   # patitas
    s.fill(principal, (13, 17, 2, 2))
    pygame.draw.polygon(s, principal, [(10, 5), (11, 0), (13, 4)])     # oreja de atras
    pygame.draw.polygon(s, principal, [(15, 4), (17, 0), (18, 5)])     # oreja de adelante
    pygame.draw.ellipse(s, principal, (9, 3, 11, 9))                   # cabeza
    pygame.draw.ellipse(s, pecho, (15, 7, 7, 4))                       # hocico


def _arte_zorro(cuadro):
    s = pygame.Surface((24, 21), pygame.SRCALPHA)
    cola_dy = 0 if cuadro % 2 == 0 else 1

    silueta = pygame.Surface((24, 21), pygame.SRCALPHA)
    _formas_zorro(silueta, CONTORNO, CONTORNO, CONTORNO, cola_dy)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        s.blit(silueta, (dx, dy))
    _formas_zorro(s, NARANJA, CREMA, CREMA, cola_dy)

    # mochila metalica con remaches
    s.fill(METAL, (4, 11, 4, 6))
    s.fill(METAL_OSCURO, (4, 15, 4, 2))
    s.set_at((5, 12), WHITE)
    # sombra en la panza/cola y brillo en la cabeza
    for y in range(21):
        for x in range(24):
            if tuple(s.get_at((x, y)))[:3] == NARANJA and (y >= 15 or (x <= 9 and y >= 12 + cola_dy)):
                s.set_at((x, y), NARANJA_OSCURO)
    s.fill(NARANJA_CLARO, (12, 4, 3, 1))
    # interior de la oreja de adelante
    s.set_at((17, 2), OREJA_INTERIOR)
    s.set_at((17, 3), OREJA_INTERIOR)
    # ojo con brillo, nariz, patitas en crema
    s.fill(OJO, (15, 6, 2, 2))
    s.set_at((15, 6), WHITE)
    s.set_at((21, 8), OJO)
    s.set_at((9, 18), CREMA)
    s.set_at((13, 18), CREMA)
    # casco de vidrio: aro celeste + reflejo
    pygame.draw.circle(s, (*CASCO, 255), (15, 7), 8, 1)
    s.fill(WHITE, (11, 2, 2, 1))
    s.set_at((10, 3), WHITE)
    return s


def _arte_capsula(cuadro):
    s = pygame.Surface((22, 24), pygame.SRCALPHA)
    # antena con luz que parpadea
    s.fill(METAL_OSCURO, (10, 0, 2, 4))
    s.fill(LUZ_ROJA if cuadro % 2 == 0 else (110, 30, 40), (9, 0, 4, 2))
    pygame.draw.circle(s, CONTORNO, (11, 13), 10)
    pygame.draw.circle(s, METAL, (11, 13), 9)
    pygame.draw.circle(s, METAL_OSCURO, (11, 13), 9, 1)
    # ventanita con la cara del zorrito
    pygame.draw.circle(s, CONTORNO, (11, 12), 6)
    pygame.draw.circle(s, (60, 110, 160), (11, 12), 5)
    pygame.draw.polygon(s, NARANJA, [(7, 10), (8, 7), (10, 10)])
    pygame.draw.polygon(s, NARANJA, [(12, 10), (14, 7), (15, 10)])
    pygame.draw.ellipse(s, NARANJA, (7, 9, 9, 6))
    s.fill(CREMA, (10, 12, 4, 2))
    s.set_at((9, 11), OJO)
    s.set_at((13, 11), OJO)
    s.fill(WHITE, (8, 8, 2, 1))
    # remaches y patas de aterrizaje
    for rx in (3, 19):
        s.set_at((rx, 13), WHITE)
    s.fill(METAL_OSCURO, (4, 21, 3, 3))
    s.fill(METAL_OSCURO, (15, 21, 3, 3))
    return s


_CACHE = {}


def _sprite(nombre, cuadro, escala, voltear=False):
    clave = (nombre, cuadro, escala, voltear)
    surf = _CACHE.get(clave)
    if surf is None:
        arte = (_arte_zorro if nombre == "zorro" else _arte_capsula)(cuadro)
        surf = pygame.transform.scale(arte, (arte.get_width() * escala, arte.get_height() * escala))
        if voltear:
            surf = pygame.transform.flip(surf, True, False)
        _CACHE[clave] = surf
    return surf


def _globito(screen, texto, x, y):
    t = render_text(texto, 12, (40, 20, 20), outline=False)
    caja = pygame.Rect(0, 0, t.get_width() + 12, t.get_height() + 6)
    caja.midbottom = (int(x), int(y))
    screen.fill(CONTORNO, caja.inflate(4, 4))
    screen.fill((255, 250, 240), caja)
    screen.blit(t, (caja.x + 6, caja.y + 3))


# ------------------------------------------------------------------ capsula

class CapsulaMascota:
    """Capsula de rescate: baja despacio y flota en la mitad de abajo hasta
    que la nave la toca (recogida()). No se la puede romper a tiros."""

    ESCALA = 3

    def __init__(self):
        self.x = random.uniform(160, GAME_WIDTH - 160)
        self.y = -60.0
        self.t = 0
        self.destino_y = GAME_HEIGHT * 0.55

    def update(self):
        self.t += 1
        if self.y < self.destino_y:
            self.y += 1.6
        else:
            self.y = self.destino_y + math.sin(self.t * 0.05) * 10
        self.x += math.sin(self.t * 0.013) * 1.2
        self.x = max(60, min(GAME_WIDTH - 60, self.x))

    def recogida(self, ship):
        return math.hypot(ship.x - self.x, ship.y - self.y) < 50

    def draw(self, screen, offset_x=0, offset_y=0):
        spr = _sprite("capsula", (self.t // 15) % 2, self.ESCALA)
        # halo que late para que se note que es algo bueno
        radio = 44 + int(math.sin(self.t * 0.1) * 5)
        halo = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(halo, (255, 200, 120, 45), (radio, radio), radio)
        screen.blit(halo, (int(self.x) - radio + offset_x, int(self.y) - radio + offset_y))
        screen.blit(spr, (int(self.x) - spr.get_width() // 2 + offset_x, int(self.y) - spr.get_height() // 2 + offset_y))
        if (self.t // 20) % 2 == 0:
            _globito(screen, "¡Rescatame!", self.x + offset_x, self.y - spr.get_height() // 2 - 4 + offset_y)


# ------------------------------------------------------------------- zorrito

class BalaZorro:
    """Bolita de plasma del zorrito, apuntada. Interfaz de Bullet."""

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = 4
        self.piercing = False
        self.active = True
        self.t = 0

    def update(self):
        self.t += 1
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < GAME_WIDTH + 20 and -20 < self.y < GAME_HEIGHT + 20):
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        r = 5 + (self.t // 3) % 2
        screen.fill(NARANJA_OSCURO, (cx - r, cy - r, r * 2, r * 2))
        screen.fill(AMARILLO, (cx - r + 2, cy - r + 2, r * 2 - 4, r * 2 - 4))
        screen.fill(WHITE, (cx - 1, cy - 1, 2, 2))


class ZorritoEspacial:
    """Orbita alrededor de la nave. update() devuelve sus disparos nuevos;
    ademas modifica directamente power-ups (los acerca) y balas enemigas
    (bloquea una cada BLOQUEO_CADA cuadros)."""

    ESCALA = 3
    CADENCIA = 42
    ALCANCE = 460
    BLOQUEO_CADA = 8 * 60

    def __init__(self, ship):
        self.x = ship.x
        self.y = ship.y - 40
        self.t = 0
        self.angulo = 0.0
        self.mira_derecha = True
        self.timer_disparo = 30
        self.timer_bloqueo = 0
        self.destello_bloqueo = 0
        self.frase = ("¡Hola!", 120)
        self.llama = 0

    def _decir(self, texto, cuadros=70):
        self.frase = (texto, cuadros)

    def update(self, ship, objetivos, balas_enemigas):
        self.t += 1
        if self.frase is not None:
            texto, vida = self.frase
            self.frase = (texto, vida - 1) if vida > 1 else None
        if self.timer_bloqueo > 0:
            self.timer_bloqueo -= 1
        if self.destello_bloqueo > 0:
            self.destello_bloqueo -= 1

        # orbita elipsica por encima de la nave
        self.angulo += 0.035
        objetivo_x = ship.x + math.cos(self.angulo) * 62
        objetivo_y = ship.y - 34 + math.sin(self.angulo) * 22
        dx = (objetivo_x - self.x) * 0.14
        self.x += dx
        self.y += (objetivo_y - self.y) * 0.14
        if abs(dx) > 0.3:
            self.mira_derecha = dx > 0

        # bloqueo con la cola de una bala que viene a la nave
        if self.timer_bloqueo <= 0:
            for b in balas_enemigas:
                if not b.active or not getattr(b, "visible", True):
                    continue
                if math.hypot(b.x - self.x, b.y - self.y) < 48 or math.hypot(b.x - ship.x, b.y - ship.y) < 70:
                    b.active = False
                    self.timer_bloqueo = self.BLOQUEO_CADA
                    self.destello_bloqueo = 14
                    self._decir("¡Yip!", 45)
                    break

        # dispara al enemigo mas cercano
        self.timer_disparo -= 1
        if self.timer_disparo > 0:
            return []
        mejor, mejor_d = None, self.ALCANCE
        for o in objetivos:
            if not getattr(o, "active", True) or getattr(o, "entrando", False):
                continue
            d = math.hypot(o.x - self.x, o.y - self.y)
            if d < mejor_d:
                mejor, mejor_d = o, d
        if mejor is None:
            return []
        self.timer_disparo = self.CADENCIA
        self.mira_derecha = mejor.x >= self.x
        a = math.atan2(mejor.y - self.y, mejor.x - self.x)
        if random.random() < 0.04:
            self._decir(random.choice(("¡Toma!", "¡Yip yip!", "¡Vamos!")), 50)
        return [BalaZorro(self.x, self.y - 4, math.cos(a) * 8.5, math.sin(a) * 8.5)]

    def draw(self, screen, offset_x=0, offset_y=0):
        cuadro = (self.t // 10) % 2
        spr = _sprite("zorro", cuadro, self.ESCALA, voltear=not self.mira_derecha)
        x = int(self.x) - spr.get_width() // 2 + offset_x
        y = int(self.y) - spr.get_height() // 2 + offset_y

        # llama de la mochila cohete (atras y abajo)
        lado = -1 if self.mira_derecha else 1
        fx = int(self.x) + lado * 5 * self.ESCALA + offset_x
        fy = int(self.y) + 5 * self.ESCALA + offset_y
        largo = 6 + (self.t // 3) % 3 * 3
        screen.fill(LLAMA_ROJA, (fx - 4, fy, 8, largo + 4))
        screen.fill(LLAMA, (fx - 2, fy, 4, largo))

        screen.blit(spr, (x, y))

        if self.destello_bloqueo > 0:
            r = 30 + (14 - self.destello_bloqueo) * 3
            anillo = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(anillo, (255, 220, 150, 16 * self.destello_bloqueo), (r + 2, r + 2), r, 4)
            screen.blit(anillo, (int(self.x) - r - 2 + offset_x, int(self.y) - r - 2 + offset_y))
        if self.frase is not None:
            _globito(screen, self.frase[0], self.x + offset_x, y - 4)


def dibujar_aviso_mascota(surface, titulo, subtitulo, restante, t):
    """Cartel de arriba para la capsula/la llegada del zorrito (se usa en la
    partida normal, fuera del bonus)."""
    if restante <= 0:
        return
    alfa = min(1.0, restante / 30)
    caja = pygame.Rect(0, 0, 520, 74)
    caja.midtop = (GAME_WIDTH // 2, 70 - int((1 - alfa) * 20))
    # panel neon como las cartas de mejora (se arma aparte para el fundido)
    capa = pygame.Surface(caja.inflate(12, 12).size, pygame.SRCALPHA)
    neon.panel(capa, pygame.Rect(6, 6, caja.w, caja.h), NARANJA, t, halo=False)
    capa.set_alpha(int(255 * alfa))
    surface.blit(capa, (caja.x - 6, caja.y - 6))
    zorro = _sprite("zorro", (t // 10) % 2, 2)
    surface.blit(zorro, (caja.x + 14, caja.centery - zorro.get_height() // 2))
    ti = get_font(24, bold=True).render(titulo, True, NARANJA_CLARO)
    st = get_font(15).render(subtitulo, True, CREMA)
    ti.set_alpha(int(255 * alfa))
    st.set_alpha(int(255 * alfa))
    surface.blit(ti, (caja.x + 80, caja.y + 12))
    surface.blit(st, (caja.x + 80, caja.y + 44))
