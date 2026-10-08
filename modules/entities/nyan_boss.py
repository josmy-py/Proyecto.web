"""
Jefe bonus secreto que aparece despues de la (falsa) victoria contra el
mega-jefe: un combate en un entorno pixel art contra Nyan Cat, que usa
como ataques a los otros dos gatos -el Gato Pan (el "loaf cat" que se
lanza como proyectil) y el Gato Alien en su plato volador (mini-ovnis que
bajan a disparar)- y que, al caer, deja paso a esos dos como jefes
propios, uno tras otro: primero el Gato Alien y al final el Gato Pan, que
gira sin parar como el gato "OIIA OIIA" (ver bonus_estado en main.py).

Todo el arte se dibuja por codigo a resolucion de "pixel de arte" (una
superficie diminuta pintada con fill/ellipse) y se agranda con escala
nearest, asi no hacen falta PNG nuevos en assets/sprites (aunque Nyan Cat
y el Gato Pan pueden usar frames propios, ver frames_personalizados). main.py ademas
pixela el cuadro completo (ver pixelar) mientras dura el bonus, para que
la nave del jugador, las balas y las explosiones compartan la misma
estetica que los gatos.

Los jefes siguen la misma interfaz que el resto (x, y, active, rewarded,
hp/max_hp, size, take_damage, update(ship) -> lista de balas, draw); lo
unico extra es draw_ui, que main.py llama DESPUES de pixelar el cuadro
para que la barra de vida y el nombre se lean nitidos."""

import glob
import math
import os
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE, AMARILLO, MENTA
from modules.systems.fonts import render_text, get_font
from modules.systems.ui import dibujar_texto_arcoiris
from modules.systems import neon

# Tamaño (en px de juego) de cada "pixel" del entorno bonus: main.py
# reduce el cuadro a 1/PIXEL_BONUS y lo vuelve a agrandar sin filtrado.
PIXEL_BONUS = 4

NEGRO = (0, 0, 0)
FONDO_NYAN = (14, 38, 92)
ARCOIRIS = [(255, 0, 0), (255, 153, 0), (255, 255, 0), (51, 255, 0), (0, 153, 255), (102, 51, 255)]
MASA = (255, 204, 153)
GLASEADO = (255, 153, 255)
CHISPA = (255, 51, 153)
GRIS = (153, 153, 153)
MEJILLA = (255, 153, 153)

PAN_CONTORNO = (22, 22, 12)
PAN_OSCURO = (48, 46, 26)
PAN_MEDIO = (92, 88, 48)
PAN_CLARO = (138, 128, 78)
MIGA = (235, 200, 120)

OVNI_CONTORNO = (45, 18, 70)
OVNI_CASCO = (236, 60, 200)
OVNI_BORDE = (150, 70, 190)
OVNI_CUPULA = (205, 195, 255)
OVNI_LUZ = (150, 240, 140)
OVNI_LUZ_APAGADA = (70, 140, 70)
ALIEN_VERDE = (70, 205, 105)
ALIEN_OSCURO = (35, 130, 70)
ALIEN_OJO = (30, 20, 60)
ESTRELLA_VERDE = (190, 255, 200)
ALMOHADON = (255, 160, 210)
ALMOHADON_BORDE = (190, 80, 150)

# Gato OIIA: gato negro con casco espartano dorado (penacho rojo), sentado
# derecho, ojos amarillos entrecerrados y la boca abierta cantando
GATO_CONTORNO = (10, 8, 16)
GATO_NEGRO = (38, 34, 46)
GATO_NEGRO_LUZ = (70, 64, 86)
GATO_OREJA = (110, 56, 80)
GATO_OJO = (255, 214, 70)
GATO_BLANCO = (238, 236, 232)
GATO_ROSA = (240, 140, 160)
GATO_BOCA = (90, 24, 44)
CASCO = (206, 150, 48)
CASCO_SOMBRA = (140, 92, 28)
CASCO_LUZ = (246, 206, 104)
CASCO_FILO = (255, 240, 180)
PENACHO = (196, 36, 48)
PENACHO_OSCURO = (120, 18, 34)


# ------------------------------------------------------------------ arte

def _px(s, color, x, y, w=1, h=1):
    s.fill(color, (x, y, w, h))


def _borrar(s, x, y):
    s.fill((0, 0, 0, 0), (x, y, 1, 1))


def _arte_nyan(cuadro):
    """Nyan Cat mirando a la derecha: tostada con glaseado, cabeza gris,
    cola y patas. Dos cuadros (cola/patas/tostada alternan)."""
    s = pygame.Surface((36, 22), pygame.SRCALPHA)
    arriba = cuadro % 2 == 0

    cy = 8 if arriba else 10
    _px(s, NEGRO, 0, cy, 7, 4)
    _px(s, GRIS, 1, cy + 1, 5, 2)

    for i, lx in enumerate((6, 10, 19, 23)):
        dx = 1 if (i % 2 == 0) == arriba else 0
        _px(s, NEGRO, lx + dx, 16, 4, 5)
        _px(s, GRIS, lx + dx + 1, 16, 2, 4)

    ty = 0 if arriba else 1
    _px(s, NEGRO, 5, ty, 21, 18)
    _px(s, MASA, 6, ty + 1, 19, 16)
    _px(s, GLASEADO, 8, ty + 3, 15, 12)
    for sx, sy in ((10, 5), (14, 4), (19, 6), (11, 9), (16, 8), (20, 11), (9, 12), (13, 13), (18, 13), (15, 11)):
        _px(s, CHISPA, sx, ty + sy)
    for qx, qy in ((5, ty), (25, ty), (5, ty + 17), (25, ty + 17)):
        _borrar(s, qx, qy)

    hx = 21 if arriba else 22
    hy = 6 if arriba else 7
    _px(s, NEGRO, hx, hy, 4, 4)
    _px(s, GRIS, hx + 1, hy + 1, 2, 3)
    _px(s, NEGRO, hx + 10, hy, 4, 4)
    _px(s, GRIS, hx + 11, hy + 1, 2, 3)
    _px(s, NEGRO, hx + 3, hy + 2, 8, 1)
    _px(s, NEGRO, hx, hy + 3, 14, 11)
    _px(s, GRIS, hx + 1, hy + 3, 12, 10)
    _borrar(s, hx, hy + 13)
    _borrar(s, hx + 13, hy + 13)
    for ox in (3, 9):
        _px(s, NEGRO, hx + ox, hy + 6, 2, 2)
        _px(s, WHITE, hx + ox, hy + 6)
    _px(s, NEGRO, hx + 7, hy + 7)
    for mx in (4, 7, 10):
        _px(s, NEGRO, hx + mx, hy + 9)
    for mx in (5, 6, 8, 9):
        _px(s, NEGRO, hx + mx, hy + 10)
    _px(s, MEJILLA, hx + 1, hy + 8, 2, 2)
    _px(s, MEJILLA, hx + 11, hy + 8, 2, 2)
    return s


def _arte_pan(cuadro):
    """Gato Pan: el gato echado en forma de pan, un bulto oscuro con la
    cabeza asomando a la derecha y manchas de camuflaje."""
    s = pygame.Surface((22, 13), pygame.SRCALPHA)
    aplasta = cuadro % 2
    pygame.draw.ellipse(s, PAN_CONTORNO, (0, 3 + aplasta, 22, 10 - aplasta))
    pygame.draw.ellipse(s, PAN_MEDIO, (1, 4 + aplasta, 20, 8 - aplasta))
    pygame.draw.ellipse(s, PAN_CONTORNO, (13, aplasta, 9, 8))
    pygame.draw.ellipse(s, PAN_MEDIO, (14, 1 + aplasta, 7, 6))
    _px(s, PAN_CONTORNO, 14, aplasta, 2, 2)
    _px(s, PAN_CONTORNO, 19, aplasta, 2, 2)

    rng = random.Random(7)
    for _ in range(26):
        mx, my = rng.randrange(1, 21), rng.randrange(2, 12)
        if tuple(s.get_at((mx, my)))[:3] == PAN_MEDIO:
            _px(s, rng.choice((PAN_OSCURO, PAN_OSCURO, PAN_CLARO)), mx, my)
    _px(s, PAN_CONTORNO, 16, 3 + aplasta)
    _px(s, PAN_CONTORNO, 19, 3 + aplasta)
    return s


def _arte_ovni(cuadro):
    """Gato Alien: gatito verde con antenas dentro de la cupula de un
    plato volador fucsia con luces verdes que parpadean."""
    s = pygame.Surface((32, 26), pygame.SRCALPHA)
    pygame.draw.circle(s, OVNI_CONTORNO, (16, 11), 10)
    pygame.draw.circle(s, OVNI_CUPULA, (16, 11), 9)
    _px(s, WHITE, 11, 5, 2, 1)
    _px(s, WHITE, 10, 6, 1, 2)

    _px(s, ALIEN_OSCURO, 13, 3, 1, 3)
    _px(s, ALIEN_OSCURO, 19, 3, 1, 3)
    _px(s, ALIEN_VERDE, 12, 2, 2, 2)
    _px(s, ALIEN_VERDE, 19, 2, 2, 2)
    _px(s, ALIEN_VERDE, 10, 5, 2, 3)
    _px(s, ALIEN_VERDE, 20, 5, 2, 3)
    pygame.draw.ellipse(s, ALIEN_VERDE, (10, 6, 12, 10))
    _px(s, ESTRELLA_VERDE, 16, 7)
    for ox in (12, 17):
        _px(s, ALIEN_OJO, ox, 10, 3, 3)
        _px(s, WHITE, ox, 10)
    _px(s, ALIEN_OSCURO, 15, 14, 2, 1)

    pygame.draw.ellipse(s, OVNI_CONTORNO, (0, 14, 32, 12))
    pygame.draw.ellipse(s, OVNI_CASCO, (1, 15, 30, 10))
    pygame.draw.ellipse(s, OVNI_BORDE, (8, 15, 16, 4))
    _px(s, ALIEN_VERDE, 13, 15, 6, 2)
    for i, (lx, ly) in enumerate(((4, 19), (14, 21), (25, 19))):
        _px(s, OVNI_LUZ if (i + cuadro) % 2 == 0 else OVNI_LUZ_APAGADA, lx, ly, 3, 2)
    return s


def _arte_gato_durmiendo(cuadro):
    """El gato negro del final (el OIIA) hecho bolita sobre su almohadon,
    ojos cerrados y la cola enroscada por delante; su casco espartano
    dorado descansa al lado. cuadro 0/1 = inhala/exhala (el lomo sube un
    pixel)."""
    s = pygame.Surface((60, 26), pygame.SRCALPHA)
    # almohadon
    pygame.draw.ellipse(s, ALMOHADON_BORDE, (0, 15, 42, 11))
    pygame.draw.ellipse(s, ALMOHADON, (1, 15, 40, 9))
    _px(s, (255, 200, 230), 6, 16, 10, 1)

    sube = cuadro % 2
    # lomo
    pygame.draw.ellipse(s, GATO_CONTORNO, (9, 6 - sube, 29, 14 + sube))
    pygame.draw.ellipse(s, GATO_NEGRO, (10, 7 - sube, 27, 12 + sube))
    _px(s, GATO_NEGRO_LUZ, 16, 8 - sube, 12, 1)
    _px(s, GATO_NEGRO_LUZ, 14, 9 - sube, 2, 1)
    _px(s, GATO_NEGRO_LUZ, 28, 9 - sube, 4, 1)
    _px(s, GATO_NEGRO_LUZ, 32, 10 - sube, 2, 2)

    # cabeza apoyada a la izquierda
    for pts, relleno, adentro in (([(2, 12), (4, 2), (10, 9)], [(3, 11), (4, 4), (9, 9)], [(5, 9), (5, 6), (7, 9)]),
                                  ([(9, 10), (13, 1), (17, 11)], [(10, 10), (13, 3), (16, 10)], [(12, 9), (13, 5), (14, 9)])):
        pygame.draw.polygon(s, GATO_CONTORNO, pts)
        pygame.draw.polygon(s, GATO_NEGRO, relleno)
        pygame.draw.polygon(s, GATO_OREJA, adentro)
    pygame.draw.ellipse(s, GATO_CONTORNO, (2, 8, 16, 12))
    pygame.draw.ellipse(s, GATO_NEGRO, (3, 9, 14, 10))
    _px(s, GATO_NEGRO_LUZ, 6, 9, 5, 1)
    # ojos cerrados (arcos claros) y nariz rosa
    for ox in (5, 11):
        _px(s, (176, 166, 200), ox, 13, 1, 1)
        _px(s, (176, 166, 200), ox + 1, 14, 1, 1)
        _px(s, (176, 166, 200), ox + 2, 13, 1, 1)
    _px(s, GATO_ROSA, 9, 15, 2, 1)
    _px(s, GATO_BOCA, 9, 16, 2, 1)
    # bigotes
    _px(s, GATO_BLANCO, 0, 15, 4, 1)
    _px(s, GATO_BLANCO, 0, 17, 4, 1)
    _px(s, GATO_BLANCO, 15, 16, 4, 1)
    # patita debajo del cachete
    pygame.draw.ellipse(s, GATO_CONTORNO, (12, 16, 7, 5))
    pygame.draw.ellipse(s, GATO_NEGRO, (13, 17, 5, 3))

    # cola enroscada por delante del cuerpo
    _px(s, GATO_CONTORNO, 16, 19, 22, 3)
    _px(s, GATO_NEGRO, 17, 20, 20, 1)
    _px(s, GATO_CONTORNO, 36, 16, 3, 5)
    _px(s, GATO_NEGRO, 37, 17, 1, 3)

    # ------------------------------------------------ casco al lado (perfil)
    x0 = 43
    # cresta roja de crin de adelante para atras, con sus mechones
    pygame.draw.ellipse(s, GATO_CONTORNO, (x0 - 1, 0, 19, 11))
    pygame.draw.ellipse(s, PENACHO, (x0, 1, 17, 9))
    for mx in range(x0 + 2, x0 + 16, 3):
        _px(s, PENACHO_OSCURO, mx, 3, 1, 5)
    _px(s, (240, 90, 96), x0 + 3, 2, 9, 1)
    # cupula
    pygame.draw.ellipse(s, GATO_CONTORNO, (x0, 7, 16, 13))
    pygame.draw.ellipse(s, CASCO, (x0 + 1, 8, 14, 11))
    # protector de la mejilla (adelante, mirando al gato) y cubrenuca
    pygame.draw.polygon(s, GATO_CONTORNO, [(x0, 12), (x0, 23), (x0 + 6, 24), (x0 + 7, 16)])
    pygame.draw.polygon(s, CASCO, [(x0 + 1, 13), (x0 + 1, 22), (x0 + 5, 23), (x0 + 6, 16)])
    pygame.draw.polygon(s, GATO_CONTORNO, [(x0 + 12, 14), (x0 + 17, 22), (x0 + 11, 23)])
    pygame.draw.polygon(s, CASCO_SOMBRA, [(x0 + 12, 16), (x0 + 15, 21), (x0 + 12, 22)])
    _px(s, CASCO_SOMBRA, x0 + 6, 18, 6, 4)
    _px(s, GATO_CONTORNO, x0 + 5, 22, 8, 2)
    # ranura del ojo y filo
    _px(s, GATO_CONTORNO, x0 + 1, 13, 5, 2)
    _px(s, CASCO_FILO, x0 + 6, 13, 1, 3)
    # brillos
    _px(s, CASCO_LUZ, x0 + 4, 9, 6, 1)
    _px(s, CASCO_FILO, x0 + 5, 9, 2, 1)
    _px(s, CASCO_LUZ, x0 + 2, 11, 1, 2)
    _px(s, CASCO_LUZ, x0 + 2, 16, 1, 5)
    _px(s, CASCO_SOMBRA, x0 + 11, 10, 3, 1)
    return s


def _arte_oiia(cuadro):
    """Gato OIIA de frente, como el recorte del meme. cuadro 0: boca chica
    ("O"), 1: abierta ("I"), 2: bien abierta con la cabeza para atras ("A")."""
    s = pygame.Surface((26, 38), pygame.SRCALPHA)
    alza = 1 if cuadro == 2 else 0       # en la "A" levanta la cabeza
    # cola enroscada al costado
    cola = [(19, 36), (23, 34), (24, 30), (23, 26)]
    pygame.draw.lines(s, GATO_CONTORNO, False, cola, 4)
    pygame.draw.lines(s, GATO_NEGRO, False, cola, 2)
    _px(s, GATO_NEGRO_LUZ, 23, 27, 1, 3)
    # cuerpo sentado
    pygame.draw.ellipse(s, GATO_CONTORNO, (4, 18, 18, 20))
    pygame.draw.ellipse(s, GATO_NEGRO, (5, 19, 16, 18))
    _px(s, GATO_NEGRO_LUZ, 7, 22, 1, 6)
    _px(s, GATO_NEGRO_LUZ, 8, 21, 2, 1)
    # patas delanteras derechas y juntas
    for x in (9, 14):
        _px(s, GATO_CONTORNO, x - 1, 28, 5, 10)
        _px(s, GATO_NEGRO, x, 28, 3, 9)
        _px(s, GATO_NEGRO_LUZ, x, 29, 1, 6)
    _px(s, GATO_CONTORNO, 12, 30, 2, 8)
    # cabeza (debajo del casco solo asoman las orejas)
    oy = -alza
    for pts, adentro in (([(2, 12), (3, 2), (9, 8)], [(4, 9), (4, 5), (7, 8)]),
                         ([(23, 12), (22, 2), (16, 8)], [(21, 9), (21, 5), (18, 8)])):
        pygame.draw.polygon(s, GATO_CONTORNO, [(x, y + oy) for x, y in pts])
        pygame.draw.polygon(s, GATO_OREJA, [(x, y + oy) for x, y in adentro])
    # penacho de adelante para atras
    pygame.draw.ellipse(s, GATO_CONTORNO, (9, 0 + oy, 8, 12))
    pygame.draw.ellipse(s, PENACHO, (10, 1 + oy, 6, 10))
    _px(s, PENACHO_OSCURO, 14, 3 + oy, 1, 6)
    _px(s, (240, 90, 96), 11, 3 + oy, 1, 4)
    # casco: cupula y protectores de las mejillas
    pygame.draw.ellipse(s, GATO_CONTORNO, (1, 6 + oy, 24, 17))
    pygame.draw.polygon(s, GATO_CONTORNO, [(2, 13 + oy), (2, 22 + oy), (7, 26 + oy), (19, 26 + oy), (24, 22 + oy), (24, 13 + oy)])
    pygame.draw.ellipse(s, CASCO, (2, 7 + oy, 22, 15))
    pygame.draw.polygon(s, CASCO, [(3, 13 + oy), (3, 22 + oy), (7, 25 + oy), (19, 25 + oy), (23, 22 + oy), (23, 13 + oy)])
    _px(s, CASCO_SOMBRA, 5, 23 + oy, 16, 2)
    _px(s, CASCO_SOMBRA, 21, 15 + oy, 2, 8)
    _px(s, CASCO_SOMBRA, 17, 8 + oy, 5, 1)
    # brillo del metal
    _px(s, CASCO_LUZ, 5, 9 + oy, 4, 1)
    _px(s, CASCO_LUZ, 4, 10 + oy, 1, 2)
    _px(s, CASCO_FILO, 6, 8 + oy, 2, 1)
    _px(s, CASCO_LUZ, 4, 16 + oy, 1, 5)
    _px(s, CASCO_LUZ, 3, 12 + oy, 20, 1)
    # abertura en T: ranura de los ojos y de la boca, se ve el gato negro
    _px(s, GATO_CONTORNO, 4, 13 + oy, 18, 4)
    _px(s, GATO_NEGRO, 5, 14 + oy, 16, 2)
    _px(s, GATO_CONTORNO, 9, 16 + oy, 8, 10)
    _px(s, GATO_NEGRO, 10, 16 + oy, 6, 9)
    _px(s, CASCO_FILO, 8, 17 + oy, 1, 7)
    _px(s, CASCO_FILO, 17, 17 + oy, 1, 7)
    _px(s, CASCO_FILO, 4, 17 + oy, 4, 1)
    _px(s, CASCO_FILO, 18, 17 + oy, 4, 1)
    # ojos amarillos entrecerrados
    for ex in (6, 16):
        _px(s, GATO_OJO, ex, 14 + oy, 4, 1)
        _px(s, GATO_OJO, ex + 1, 15 + oy, 2, 1)
    # nariz
    _px(s, GATO_ROSA, 12, 16 + oy, 2, 1)
    # boca abierta
    ancho, alto = ((2, 2), (4, 3), (6, 5))[cuadro]
    bx, by = 13 - ancho // 2, 18 + oy
    _px(s, GATO_CONTORNO, bx - (1 if ancho < 6 else 0), by, ancho + (2 if ancho < 6 else 0), alto + 1)
    _px(s, GATO_BOCA, bx, by, ancho, alto)
    if alto >= 3:
        _px(s, GATO_ROSA, bx + 1, by + alto - 1, ancho - 2, 1)
    # bigotes que salen por la ranura
    for y in (18, 20):
        _px(s, GATO_BLANCO, 0, y + oy, 9, 1)
        _px(s, GATO_BLANCO, 17, y + oy, 9, 1)
    return s


_ARTES = {"nyan": _arte_nyan, "pan": _arte_pan, "ovni": _arte_ovni, "durmiendo": _arte_gato_durmiendo,
          "oiia": _arte_oiia}

# Animaciones propias (opcionales): PNG con transparencia en
# assets/sprites/bonus/<jefe>/ en orden alfabetico (frame_00.png, ...),
# generados desde un video/GIF con tools/extraer_nyan_video.py --jefe <jefe>.
#   "nyan": Nyan Cat volando (se reproducen a TICKS_POR_FRAME)
#   "pan":  el gato que gira (OIIA): los frames se recorren segun el angulo
#           de giro, asi que conviene extraer UNA vuelta completa
# Sin frames se usa el arte dibujado por codigo (_arte_nyan / _arte_oiia).
CARPETA_BONUS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "sprites", "bonus",
)
_FRAMES_PROPIOS = {}
_CACHE_FRAMES_PROPIOS = {}


def frames_personalizados(jefe):
    """Surfaces originales de assets/sprites/bonus/<jefe>/ (vacia si no hay)."""
    frames = _FRAMES_PROPIOS.get(jefe)
    if frames is None:
        frames = []
        for ruta in sorted(glob.glob(os.path.join(CARPETA_BONUS, jefe, "*.png"))):
            try:
                frames.append(pygame.image.load(ruta).convert_alpha())
            except pygame.error:
                pass
        _FRAMES_PROPIOS[jefe] = frames
    return frames


def frame_personalizado(jefe, indice, alto, voltear=False, blanco=False):
    """Frame `indice` de la animacion propia de `jefe` escalado a `alto` px."""
    frames = frames_personalizados(jefe)
    indice %= len(frames)
    clave = (jefe, indice, alto, voltear, blanco)
    surf = _CACHE_FRAMES_PROPIOS.get(clave)
    if surf is None:
        original = frames[indice]
        ancho = max(1, round(original.get_width() * alto / original.get_height()))
        surf = pygame.transform.scale(original, (ancho, alto))
        if voltear:
            surf = pygame.transform.flip(surf, True, False)
        if blanco:
            surf = surf.copy()
            surf.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
        _CACHE_FRAMES_PROPIOS[clave] = surf
    return surf


_CACHE_SPRITES = {}


def sprite_pixel(nombre, cuadro, escala, voltear=False, blanco=False):
    """Sprite `nombre` agrandado `escala` veces sin filtrado (cacheado).
    blanco=True devuelve la silueta blanca para el destello de impacto."""
    clave = (nombre, cuadro, escala, voltear, blanco)
    surf = _CACHE_SPRITES.get(clave)
    if surf is None:
        arte = _ARTES[nombre](cuadro)
        w, h = arte.get_size()
        surf = pygame.transform.scale(arte, (w * escala, h * escala))
        if voltear:
            surf = pygame.transform.flip(surf, True, False)
        if blanco:
            surf = surf.copy()
            surf.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
        _CACHE_SPRITES[clave] = surf
    return surf


def _blit_centrado(screen, surf, x, y):
    screen.blit(surf, (int(x) - surf.get_width() // 2, int(y) - surf.get_height() // 2))


# ------------------------------------------------------- entorno y efectos

def pixelar(surface, factor):
    """Devuelve `surface` reducida a 1/factor y agrandada de nuevo sin
    filtrado: todo lo dibujado queda en bloques de factor x factor."""
    if factor <= 1:
        return surface
    w, h = surface.get_size()
    chica = pygame.transform.scale(surface, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.scale(chica, (w, h))


_SCANLINES = {}


def dibujar_scanlines(surface):
    """Lineas oscuras cada PIXEL_BONUS filas, como un monitor CRT viejo."""
    w, h = surface.get_size()
    capa = _SCANLINES.get((w, h))
    if capa is None:
        capa = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(PIXEL_BONUS - 1, h, PIXEL_BONUS):
            capa.fill((0, 0, 0, 38), (0, y, w, 1))
        _SCANLINES[(w, h)] = capa
    surface.blit(capa, (0, 0))


def aplicar_glitch(surface, intensidad):
    """Franjas horizontales desplazadas y bloques de color al azar sobre
    una copia de `surface` (intensidad 0..1): la pantalla de victoria
    "se rompe" antes de revelar el jefe bonus."""
    w, h = surface.get_size()
    out = surface.copy()
    desplazamiento_max = int(10 + 70 * intensidad)
    for _ in range(int(4 + 16 * intensidad)):
        y = random.randrange(0, h)
        alto = min(random.randint(3, 10 + int(30 * intensidad)), h - y)
        if alto <= 0:
            continue
        franja = surface.subsurface((0, y, w, alto)).copy()
        out.blit(franja, (random.randint(-desplazamiento_max, desplazamiento_max), y))
    for _ in range(int(10 * intensidad)):
        color = random.choice(ARCOIRIS + [NEGRO, WHITE])
        out.fill(color, (random.randrange(0, w), random.randrange(0, h),
                         random.randint(8, 70), random.randint(4, 16)))
    return out


class FondoPixel:
    """Cielo azul marino de Nyan Cat con destellos pixelados que bajan
    (el mundo "corre" hacia atras mientras la nave avanza)."""

    def __init__(self):
        self.t = 0
        self.estrellas = [self._nueva(random.uniform(0, GAME_HEIGHT)) for _ in range(38)]

    @staticmethod
    def _nueva(y):
        return {'x': random.uniform(0, GAME_WIDTH), 'y': y,
                'v': random.uniform(1.2, 3.2), 'fase': random.randrange(40)}

    def update(self):
        self.t += 1
        for i, e in enumerate(self.estrellas):
            e['y'] += e['v']
            if e['y'] > GAME_HEIGHT + 12:
                self.estrellas[i] = self._nueva(-12)

    def draw(self, surface):
        surface.fill(FONDO_NYAN)
        p = PIXEL_BONUS
        for e in self.estrellas:
            x = int(e['x']) // p * p
            y = int(e['y']) // p * p
            cuadro = ((self.t + e['fase']) // 10) % 4
            if cuadro == 0:
                surface.fill(WHITE, (x, y, p, p))
            elif cuadro == 1:
                for dx, dy in ((0, 0), (-p, 0), (p, 0), (0, -p), (0, p)):
                    surface.fill(WHITE, (x + dx, y + dy, p, p))
            elif cuadro == 2:
                for d in (2 * p, 3 * p):
                    for dx, dy in ((-d, 0), (d, 0), (0, -d), (0, d)):
                        surface.fill(WHITE, (x + dx, y + dy, p, p))
            else:
                for dx, dy in ((-2 * p, -2 * p), (2 * p, -2 * p), (-2 * p, 2 * p), (2 * p, 2 * p)):
                    surface.fill(WHITE, (x + dx, y + dy, p, p))


# ------------------------------------------------------------------ balas

class BalaPixel:
    """Proyectil de los gatos. forma: "cuadro" (chispa), "estrella"
    (destello en cruz), "arcoiris" (bloque de la estela de la carrera) o
    "sprite" (un gato arrojado). vida=None dura hasta salir de pantalla;
    visible=False sirve para hitboxes que dibuja el propio jefe (el rayo
    tractor del Gato Alien)."""

    def __init__(self, x, y, vx=0.0, vy=4.0, color=CHISPA, tam=8, vida=None,
                 gravedad=0.0, forma="cuadro", sprite=None, radio=None, visible=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.tam = tam
        self.vida = vida
        self.gravedad = gravedad
        self.forma = forma
        self.sprite = sprite
        self.radius = radio if radio is not None else max(3, tam // 2)
        self.visible = visible
        self.active = True

    def update(self):
        self.vy += self.gravedad
        self.x += self.vx
        self.y += self.vy
        if self.vida is not None:
            self.vida -= 1
            if self.vida <= 0:
                self.active = False
        margen = 70
        if self.x < -margen or self.x > GAME_WIDTH + margen or self.y > GAME_HEIGHT + margen or self.y < -margen * 3:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        if not self.visible:
            return
        if self.vida is not None and self.vida < 18 and self.vida % 4 < 2:
            return
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        if self.forma == "sprite" and self.sprite is not None:
            _blit_centrado(screen, self.sprite, cx, cy)
        elif self.forma == "estrella":
            b = max(2, self.tam // 4)
            r = self.tam // 2
            screen.fill(self.color, (cx - r, cy - b // 2, r * 2, b))
            screen.fill(self.color, (cx - b // 2, cy - r, b, r * 2))
            screen.fill(WHITE, (cx - b // 2, cy - b // 2, b, b))
        elif self.forma == "arcoiris":
            franja = self.tam // 6
            alto = franja * 6
            for i, color in enumerate(ARCOIRIS):
                screen.fill(color, (cx - self.tam // 2, cy - alto // 2 + i * franja, self.tam, franja))
        else:
            # bloque de color con nucleo blanco: tras pixelar sigue leyendose
            # sobre el azul del fondo (con borde negro quedaba como una mota)
            m = self.tam // 2
            screen.fill(self.color, (cx - m, cy - m, self.tam, self.tam))
            screen.fill(WHITE, (cx - 2, cy - 2, 4, 4))


def _lanzar_en_arco(x0, y0, objetivo_x, objetivo_y, sprite, radio, vy0=-2.6, gravedad=0.16):
    """Gato arrojado en parabola que cae cerca de (objetivo_x, objetivo_y)."""
    dy = max(40.0, objetivo_y - y0)
    t = (-vy0 + math.sqrt(vy0 * vy0 + 2 * gravedad * dy)) / gravedad
    vx = (objetivo_x - x0) / max(1.0, t)
    return BalaPixel(x0, y0, vx, vy0, gravedad=gravedad, forma="sprite", sprite=sprite, radio=radio)


def _anillo(x, y, n, velocidad, color, tam, forma="cuadro", desfase=0.0):
    balas = []
    for i in range(n):
        a = desfase + 2 * math.pi * i / n
        balas.append(BalaPixel(x, y, math.cos(a) * velocidad, math.sin(a) * velocidad,
                               color=color, tam=tam, forma=forma))
    return balas


def _apuntada(x, y, ship, velocidad, **kw):
    a = math.atan2(ship.y - y, ship.x - x)
    return BalaPixel(x, y, math.cos(a) * velocidad, math.sin(a) * velocidad, **kw)


# ------------------------------------------------------------------ jefes

class JefeGatoBase:
    """Vida, destello de impacto, entrada invulnerable, "furia" (al bajar de
    UMBRAL_FURIA de vida: mas rapido y con ataques extra) y la barra de
    vida pixelada."""

    UMBRAL_FURIA = 0.4

    nombre = "GATO"
    hp_base = 300

    def __init__(self, dificultad=1.0):
        self.dificultad = dificultad
        self.max_hp = max(1, int(self.hp_base * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.active = True
        self.rewarded = False
        self.flash = 0
        self.t = 0
        self.entrando = True
        self.furioso = False
        self.name = self.nombre
        self.alto_sprite = 80
        # nombre del ataque especial en curso, se muestra bajo el jefe
        self.cartel = None

    def take_damage(self, amount=1):
        if self.entrando or not self.active:
            return
        self.hp = max(0, self.hp - amount)
        self.flash = 5
        if self.hp <= 0:
            self.active = False
        elif not self.furioso and self.hp < self.max_hp * self.UMBRAL_FURIA:
            self.enfurecer()

    def enfurecer(self):
        self.furioso = True

    def _vel(self):
        return self.dificultad * (1.35 if self.furioso else 1.0)

    def _anunciar(self, texto, cuadros=80):
        self.cartel = [texto, cuadros]

    def _tick_comun(self):
        self.t += 1
        if self.cartel is not None:
            self.cartel[1] -= 1
            if self.cartel[1] <= 0:
                self.cartel = None
        if self.flash > 0:
            self.flash -= 1
        if self.display_hp > self.hp:
            self.display_hp = max(self.hp, self.display_hp - self.max_hp * 0.01)

    def draw_ui(self, surface):
        ancho, alto = 150, 12
        x = int(self.x) - ancho // 2
        x = max(8, min(GAME_WIDTH - ancho - 8, x))
        y = max(40, int(self.y - self.alto_sprite / 2) - 26)
        titulo = self.name + (" (FURIOSO)" if self.furioso else "")
        nombre = render_text(titulo, 12, CHISPA if self.furioso else AMARILLO)
        surface.blit(nombre, (x + ancho // 2 - nombre.get_width() // 2, y - 16))

        surface.fill(NEGRO, (x - 2, y - 2, ancho + 4, alto + 4))
        surface.fill(WHITE, (x - 2, y - 2, ancho + 4, 2))
        surface.fill(WHITE, (x - 2, y + alto, ancho + 4, 2))
        surface.fill(WHITE, (x - 2, y - 2, 2, alto + 4))
        surface.fill(WHITE, (x + ancho, y - 2, 2, alto + 4))

        ratio = self.hp / self.max_hp
        color = MENTA if ratio > 0.6 else AMARILLO if ratio > 0.3 else CHISPA
        segmento = 6
        mostrado = int(ancho * (self.display_hp / self.max_hp))
        real = int(ancho * ratio)
        for sx in range(0, ancho, segmento):
            if sx < real:
                surface.fill(color, (x + sx + 1, y + 2, segmento - 2, alto - 4))
            elif sx < mostrado:
                surface.fill(WHITE, (x + sx + 1, y + 2, segmento - 2, alto - 4))
        self._dibujar_cartel(surface)

    def _dibujar_cartel(self, surface):
        if self.cartel is None or (self.cartel[1] < 20 and self.cartel[1] % 4 < 2):
            return
        texto = render_text(self.cartel[0], 22, AMARILLO)
        cx = max(texto.get_width() // 2 + 8, min(GAME_WIDTH - texto.get_width() // 2 - 8, int(self.x)))
        cy = max(60, min(GAME_HEIGHT - 60, int(self.y) + self.alto_sprite // 2 + 12))
        surface.blit(texto, (cx - texto.get_width() // 2, cy))


class _ClonNyan:
    """Copia de Nyan Cat para los ataques dobles: solo posicion/aspecto (no
    recibe daño; sus golpes son hitboxes como las del original)."""

    def __init__(self, x, y, mirando_der):
        self.x = x
        self.y = y
        self.mirando_der = mirando_der
        self.desvanece = 0  # >0: se esta yendo (cuadros que le quedan)


class NyanBoss(JefeGatoBase):
    """Jefe bonus principal. Ataques a distancia:
      fase 1: abanico de chispas de glaseado + Gatos Pan arrojados en arco.
      fase 2 (<60%): ademas baja un par de mini Gatos Alien que disparan
                     destellos apuntados y se van.
      fase 3 (<30%): ademas "carrera arcoiris": avisa una fila a la altura
                     de la nave, cruza la pantalla por ahi a toda velocidad
                     y deja una pared de arcoiris que tarda en apagarse.
    Ataques fisicos (pega con el cuerpo: hitbox que lo sigue), en rotacion:
      - EMBESTIDA: tiembla, fija la posicion de la nave y la atraviesa a
        toda velocidad hasta salir de pantalla; vuelve por arriba.
      - PICADA ARCOIRIS: dos picadas en U de un lado al otro que bajan hasta
        la altura de la nave, soltando chispas hacia abajo.
      - PISOTON: sale por arriba, marca el lugar de la nave y cae como un
        meteorito; al impactar suelta un anillo de chispas.
    "¡DOBLE NYAN!": de la nada (destello) se duplica y la copia hace el
    mismo ataque en espejo -embestidas en X, picadas que se cruzan, dos
    pisotones-; mas probable en cada fase. La copia se desvanece al
    terminar y solo el original recibe daño."""

    nombre = "NYAN CAT"
    hp_base = 650
    ESCALA = 4
    LARGO_ESTELA = 240
    RADIO_CUERPO = 44
    # velocidad de la animacion propia (frames de assets/sprites/bonus/nyan):
    # 5 ticks a 60 FPS = 12 cuadros por segundo, como un GIF tipico
    TICKS_POR_FRAME = 5
    NOMBRES_FISICOS = {"embestida": "¡EMBESTIDA!", "picada": "¡PICADA ARCOIRIS!", "pisoton": "¡PISOTON!"}

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = -170.0
        self.y = 150.0
        self.size = 62
        self.alto_sprite = 22 * self.ESCALA
        self.base_y = 140
        self.fase = 1
        self.mirando_der = True
        self.recorrido = 0.0
        self.ovnis = []
        self.carrera = None
        self.timer_chispas = 80
        self.timer_panes = 150
        self.timer_ovnis = 200
        self.timer_carrera = 300
        self.fisico = None
        self.timer_fisico = 180
        self.indice_fisico = 0
        self.clon = None
        self.destello_dup = 0

    def update(self, ship):
        self._tick_comun()
        balas = []
        prev_x = self.x
        ratio = self.hp / self.max_hp
        self.fase = 1 if ratio > 0.6 else 2 if ratio > 0.3 else 3
        if self.destello_dup > 0:
            self.destello_dup -= 1

        if self.entrando:
            self.x = min(GAME_WIDTH / 2, self.x + 5.5)
            self.y = self.base_y + math.sin(self.t * 0.08) * 8
            if self.x >= GAME_WIDTH / 2:
                self.entrando = False
        elif self.fisico is not None:
            balas += self._actualizar_fisico(ship)
        elif self.carrera is not None:
            balas += self._actualizar_carrera(ship)
        else:
            self.recorrido += 0.011 * self._vel()
            tx = GAME_WIDTH / 2 + math.sin(self.recorrido) * (GAME_WIDTH / 2 - 130)
            ty = self.base_y + math.sin(self.recorrido * 2) * 45
            self.x += (tx - self.x) * 0.08
            self.y += (ty - self.y) * 0.08
            balas += self._ataques(ship)
            self.timer_fisico -= 1
            if self.timer_fisico <= 0 and self.carrera is None:
                self._iniciar_fisico()

        balas += self._actualizar_ovnis(ship)

        if self.clon is not None and self.clon.desvanece > 0:
            self.clon.desvanece -= 1
            if self.clon.desvanece <= 0:
                self.clon = None

        dx = self.x - prev_x
        if abs(dx) > 0.4:
            self.mirando_der = dx > 0
        return balas

    # ------------------------------------------------- ataques fisicos
    def _cuerpos(self):
        """El original y (si hay un ataque doble en curso) su copia."""
        if self.clon is not None and self.clon.desvanece == 0:
            return [self, self.clon]
        return [self]

    def _golpe(self, cuerpo):
        """Hitbox del cuerpo para este cuadro (invisible, dura 2 cuadros)."""
        return BalaPixel(cuerpo.x, cuerpo.y, 0, 0, vida=2, radio=self.RADIO_CUERPO, visible=False)

    @staticmethod
    def _espejo(x, referencia):
        """Posicion espejada de x; si queda muy cerca de la referencia se
        corre para que la copia no se superponga con el original."""
        espejo = GAME_WIDTH - x
        if abs(espejo - referencia) < 200:
            espejo = referencia + (240 if referencia < GAME_WIDTH / 2 else -240)
        return max(90.0, min(GAME_WIDTH - 90.0, espejo))

    def _iniciar_fisico(self):
        tipo = ("embestida", "picada", "pisoton")[self.indice_fisico % 3]
        self.indice_fisico += 1
        doble = random.random() < (0.3, 0.5, 0.75)[self.fase - 1]
        self.fisico = {'tipo': tipo, 't': 0, 'fase': 'duplica' if doble else 'inicio', 'datos': [{}, {}]}
        if doble:
            self.clon = _ClonNyan(self.x, self.y, not self.mirando_der)
            self.destello_dup = 14
            self._anunciar("¡DOBLE NYAN!", 50)
        else:
            self._anunciar(self.NOMBRES_FISICOS[tipo])

    def _terminar_fisico(self):
        self.fisico = None
        self.recorrido = math.asin(max(-1.0, min(1.0, (self.x - GAME_WIDTH / 2) / (GAME_WIDTH / 2 - 130))))
        if self.clon is not None:
            self.clon.desvanece = 20
        self.timer_fisico = max(170, int((300 if self.fase == 1 else 240) / self._vel()))

    def _actualizar_fisico(self, ship):
        e = self.fisico
        e['t'] += 1
        v = math.sqrt(self._vel())
        balas = []
        cuerpos = self._cuerpos()

        if e['fase'] == 'duplica':
            # la copia sale del original hacia su lado espejado
            destino = self._espejo(self.x, self.x)
            self.clon.x += (destino - self.clon.x) * 0.2
            self.clon.y = self.y
            if e['t'] >= 24:
                e['fase'], e['t'] = 'inicio', 0
                self._anunciar(self.NOMBRES_FISICOS[e['tipo']])
            return balas

        if e['tipo'] == "embestida":
            if e['fase'] == 'inicio':
                for i, c in enumerate(cuerpos):
                    e['datos'][i] = {'base': (c.x, c.y), 'objetivo': (ship.x, ship.y)}
                e['fase'], e['t'] = 'aviso', 0
            elif e['fase'] == 'aviso':
                for i, c in enumerate(cuerpos):
                    d = e['datos'][i]
                    if e['t'] < 26:
                        d['objetivo'] = (ship.x, ship.y)
                    c.x = d['base'][0] + random.uniform(-4, 4)
                    c.y = d['base'][1] + random.uniform(-3, 3)
                    c.mirando_der = d['objetivo'][0] >= c.x
                if e['t'] >= 42:
                    rapidez = min(22.0, 17 * v)
                    for i, c in enumerate(cuerpos):
                        d = e['datos'][i]
                        a = math.atan2(d['objetivo'][1] - c.y, d['objetivo'][0] - c.x)
                        d['vx'], d['vy'] = math.cos(a) * rapidez, math.sin(a) * rapidez
                    e['fase'], e['t'] = 'embiste', 0
            elif e['fase'] == 'embiste':
                afuera = True
                for i, c in enumerate(cuerpos):
                    d = e['datos'][i]
                    c.x += d['vx']
                    c.y += d['vy']
                    c.mirando_der = d['vx'] > 0
                    balas.append(self._golpe(c))
                    if -160 < c.x < GAME_WIDTH + 160 and -160 < c.y < GAME_HEIGHT + 120:
                        afuera = False
                if afuera or e['t'] > 150:
                    self.x, self.y = GAME_WIDTH / 2, -90.0
                    self._terminar_fisico()

        elif e['tipo'] == "picada":
            if e['fase'] == 'inicio':
                fondo = max(260.0, min(GAME_HEIGHT - 80.0, ship.y - 10))
                for i, c in enumerate(cuerpos):
                    x1 = GAME_WIDTH - c.x
                    if abs(x1 - c.x) < 200:
                        x1 = GAME_WIDTH - 120 if c.x < GAME_WIDTH / 2 else 120.0
                    e['datos'][i] = {'x0': c.x, 'x1': x1, 'y0': c.y}
                e['fondo'] = fondo
                e['dur'] = int(75 / v)
                e['vueltas'] = 0
                e['fase'], e['t'] = 'baja', 0
            else:
                p = min(1.0, e['t'] / e['dur'])
                for i, c in enumerate(cuerpos):
                    d = e['datos'][i]
                    c.x = d['x0'] + (d['x1'] - d['x0']) * p
                    c.y = d['y0'] + math.sin(math.pi * p) * (e['fondo'] - d['y0'])
                    c.mirando_der = d['x1'] > d['x0']
                    balas.append(self._golpe(c))
                    if e['t'] % 7 == 0:
                        balas.append(BalaPixel(c.x, c.y + 20, 0, 3.2 * v, color=random.choice((CHISPA, GLASEADO)), tam=12))
                if p >= 1:
                    e['vueltas'] += 1
                    if e['vueltas'] >= 2:
                        self._terminar_fisico()
                    else:
                        e['fondo'] = max(260.0, min(GAME_HEIGHT - 80.0, ship.y - 10))
                        for i in range(len(cuerpos)):
                            d = e['datos'][i]
                            d['x0'], d['x1'] = d['x1'], d['x0']
                        e['t'] = 0

        else:  # pisoton
            if e['fase'] == 'inicio':
                e['fase'], e['t'] = 'sube', 0
            elif e['fase'] == 'sube':
                for c in cuerpos:
                    c.y -= 14
                if all(c.y < -90 for c in cuerpos):
                    e['fase'], e['t'] = 'marca', 0
            elif e['fase'] == 'marca':
                if e['t'] < 30:
                    e['my'] = max(300.0, min(GAME_HEIGHT - 50.0, ship.y))
                    e['datos'][0]['mx'] = max(80.0, min(GAME_WIDTH - 80.0, ship.x))
                    if len(cuerpos) > 1:
                        e['datos'][1]['mx'] = self._espejo(ship.x, e['datos'][0]['mx'])
                for i, c in enumerate(cuerpos):
                    c.x = e['datos'][i]['mx']
                    c.y = -90.0
                if e['t'] >= 50:
                    e['fase'], e['t'] = 'cae', 0
            elif e['fase'] == 'cae':
                llego = True
                for c in cuerpos:
                    if c.y < e['my']:
                        c.y = min(e['my'], c.y + 24 * v)
                        llego = False
                    balas.append(self._golpe(c))
                if llego:
                    for c in cuerpos:
                        balas += _anillo(c.x, c.y, 12, 3.0 * v, CHISPA, 12, desfase=random.uniform(0, math.pi))
                    e['fase'], e['t'] = 'impacto', 0
            elif e['fase'] == 'impacto':
                if e['t'] < 6:
                    balas += [self._golpe(c) for c in cuerpos]
                if e['t'] >= 22:
                    e['fase'], e['t'] = 'vuelve', 0
            else:
                for c in cuerpos:
                    c.y += (self.base_y - c.y) * 0.08
                if abs(self.y - self.base_y) < 6:
                    self._terminar_fisico()
        return balas

    # --------------------------------------------- ataques a distancia
    def _ataques(self, ship):
        balas = []
        v = self._vel()

        self.timer_chispas -= 1
        if self.timer_chispas <= 0:
            self.timer_chispas = max(24, int((60 if self.fase == 1 else 46) / v))
            n = 5 if self.fase == 1 else 7
            base = math.atan2(ship.y - self.y, ship.x - self.x)
            abanico = 1.0
            velocidad = (3.3 + 0.3 * self.fase) * math.sqrt(v)
            for i in range(n):
                a = base - abanico / 2 + abanico * i / (n - 1)
                balas.append(BalaPixel(self.x, self.y + 10, math.cos(a) * velocidad, math.sin(a) * velocidad,
                                       color=random.choice((CHISPA, GLASEADO, ARCOIRIS[2], MASA)), tam=12))

        self.timer_panes -= 1
        if self.timer_panes <= 0:
            self.timer_panes = max(60, int((170 if self.fase == 1 else 130) / v))
            sprite = sprite_pixel("pan", 0, 2)
            for _ in range(self.fase):
                balas.append(_lanzar_en_arco(self.x, self.y, ship.x + random.uniform(-90, 90), ship.y,
                                             sprite, radio=14))

        if self.fase >= 2:
            self.timer_ovnis -= 1
            if self.timer_ovnis <= 0 and not self.ovnis:
                self.timer_ovnis = max(160, int(330 / v))
                for lado in (-1, 1):
                    self.ovnis.append({'x': GAME_WIDTH / 2 + lado * random.uniform(170, 330), 'y': -50.0,
                                       'dest_y': random.uniform(170, 230), 'estado': 'baja',
                                       'timer': 0, 'disparos': 0})

        if self.fase >= 3:
            self.timer_carrera -= 1
            if self.timer_carrera <= 0 and self.timer_fisico > 60:
                self.timer_carrera = max(260, int(480 / v))
                direccion = 1 if self.x < GAME_WIDTH / 2 else -1
                self.carrera = {'estado': 'sale', 'timer': 0, 'dir': direccion,
                                'fila': self._fila_para(ship)}
        return balas

    @staticmethod
    def _fila_para(ship):
        return max(280.0, min(GAME_HEIGHT - 70.0, ship.y))

    def _actualizar_carrera(self, ship):
        c = self.carrera
        c['timer'] += 1
        x_inicio = -170 if c['dir'] == 1 else GAME_WIDTH + 170
        balas = []
        if c['estado'] == 'sale':
            c['fila'] = self._fila_para(ship)
            self.x += (x_inicio - self.x) * 0.09
            self.y += (c['fila'] - self.y) * 0.09
            if c['timer'] >= 45:
                c['estado'], c['timer'] = 'aviso', 0
                self.x, self.y = x_inicio, c['fila']
        elif c['estado'] == 'aviso':
            if c['timer'] >= 55:
                c['estado'], c['timer'] = 'corre', 0
        elif c['estado'] == 'corre':
            self.x += c['dir'] * 15 * min(1.4, self._vel())
            balas.append(BalaPixel(self.x - c['dir'] * 50, c['fila'], 0, 0, tam=18, vida=75,
                                   forma="arcoiris", radio=13))
            if (c['dir'] == 1 and self.x > GAME_WIDTH + 170) or (c['dir'] == -1 and self.x < -170):
                # vuelve a entrar por arriba y retoma su recorrido normal
                self.carrera = None
                self.x, self.y = GAME_WIDTH / 2, -90.0
                self.recorrido = 0.0
        return balas

    def _actualizar_ovnis(self, ship):
        balas = []
        disparos_max = 4 if self.fase >= 3 else 3
        for o in self.ovnis:
            o['timer'] += 1
            if o['estado'] == 'baja':
                o['y'] += (o['dest_y'] - o['y']) * 0.07
                if abs(o['dest_y'] - o['y']) < 3:
                    o['estado'], o['timer'] = 'dispara', 0
            elif o['estado'] == 'dispara':
                o['x'] += math.sin(o['timer'] * 0.05) * 1.2
                if o['timer'] % 34 == 20:
                    balas.append(_apuntada(o['x'], o['y'] + 16, ship, 4.2 * math.sqrt(self._vel()),
                                           color=OVNI_LUZ, tam=16, forma="estrella"))
                    o['disparos'] += 1
                    if o['disparos'] >= disparos_max:
                        o['estado'] = 'sube'
            else:
                o['y'] -= 6
        self.ovnis = [o for o in self.ovnis if not (o['estado'] == 'sube' and o['y'] < -70)]
        return balas

    def draw(self, screen, offset_x=0, offset_y=0):
        e = self.fisico
        # marcas de los ataques fisicos (debajo de todo)
        color_mira = (255, 70, 90) if (self.t // 4) % 2 == 0 else (255, 235, 80)
        if e is not None and e['tipo'] == 'embestida' and e['fase'] == 'aviso':
            for d in e['datos']:
                if 'objetivo' in d:
                    self._dibujar_mira(screen, d['objetivo'][0] + offset_x, d['objetivo'][1] + offset_y, 30, color_mira)
        if e is not None and e['tipo'] == 'pisoton' and e['fase'] in ('marca', 'cae'):
            for d in e['datos']:
                if 'mx' in d:
                    sombra = pygame.Surface((140, 36), pygame.SRCALPHA)
                    pygame.draw.ellipse(sombra, (0, 0, 0, 110), (0, 0, 140, 36))
                    screen.blit(sombra, (int(d['mx']) - 70 + offset_x, int(e['my']) + 30 + offset_y))
                    self._dibujar_mira(screen, d['mx'] + offset_x, e['my'] + offset_y, 46, color_mira)

        if self.carrera is not None and self.carrera['estado'] in ('sale', 'aviso'):
            self._dibujar_aviso(screen, self.carrera['fila'] + offset_y)
        for o in self.ovnis:
            _blit_centrado(screen, sprite_pixel("ovni", (self.t // 10) % 2, 2), o['x'] + offset_x, o['y'] + offset_y)

        # la copia (si hay): un poco transparente y titilando, como un glitch
        if self.clon is not None:
            alfa = 200 if self.clon.desvanece == 0 else int(200 * self.clon.desvanece / 20)
            if (self.t // 3) % 7 != 0:
                self._dibujar_estela(screen, self.clon, offset_x, offset_y, alfa)
                copia = self._sprite_actual(self.clon.mirando_der, blanco=False).copy()
                copia.set_alpha(alfa)
                _blit_centrado(screen, copia, self.clon.x + offset_x + random.randint(-2, 2), self.clon.y + offset_y)

        self._dibujar_estela(screen, self, offset_x, offset_y)
        _blit_centrado(screen, self._sprite_actual(), self.x + offset_x, self.y + offset_y)

        if self.destello_dup > 0:
            r = 40 + (14 - self.destello_dup) * 10
            anillo = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(anillo, (255, 255, 255, 18 * self.destello_dup), (r + 4, r + 4), r)
            pygame.draw.circle(anillo, (*ARCOIRIS[self.t % 6], 255), (r + 4, r + 4), r, 6)
            _blit_centrado(screen, anillo, self.x + offset_x, self.y + offset_y)

    @staticmethod
    def _dibujar_mira(screen, x, y, r, color):
        x, y = int(x), int(y)
        pygame.draw.circle(screen, color, (x, y), r, 4)
        screen.fill(color, (x - r - 10, y - 2, 20, 4))
        screen.fill(color, (x + r - 10, y - 2, 20, 4))
        screen.fill(color, (x - 2, y - r - 10, 4, 20))
        screen.fill(color, (x - 2, y + r - 10, 4, 20))

    def _sprite_actual(self, mirando_der=None, blanco=None):
        voltear = not (self.mirando_der if mirando_der is None else mirando_der)
        blanco = self.flash % 2 == 1 if blanco is None else blanco
        if frames_personalizados("nyan"):
            return frame_personalizado("nyan", self.t // self.TICKS_POR_FRAME, self.alto_sprite, voltear, blanco)
        return sprite_pixel("nyan", (self.t // 7) % 2, self.ESCALA, voltear=voltear, blanco=blanco)

    def _dibujar_estela(self, screen, cuerpo, offset_x, offset_y, alfa=255):
        """Estela arcoiris recta detras de la tostada, en tramos que suben
        y bajan un pixel alternados (como el Nyan Cat original). cuerpo:
        el propio Nyan o su copia."""
        if self.carrera is not None and self.carrera['estado'] == 'aviso':
            return
        franja = 2 * PIXEL_BONUS
        tramo = 4 * PIXEL_BONUS
        lado = 1 if cuerpo.mirando_der else -1
        # la estela sale del borde trasero del sprite (sea el dibujado por
        # codigo o la animacion propia, que puede tener otro ancho)
        medio_ancho = self._sprite_actual().get_width() // 2
        inicio = int(cuerpo.x) - lado * (medio_ancho - 20)
        top_base = int(cuerpo.y) - 3 * franja - 4
        n = self.LARGO_ESTELA // tramo
        capa = pygame.Surface((self.LARGO_ESTELA + tramo, 6 * franja + PIXEL_BONUS), pygame.SRCALPHA)
        for i in range(n):
            ondula = PIXEL_BONUS if (i + self.t // 8) % 2 else 0
            x = (n - 1 - i) * tramo if lado == 1 else i * tramo
            for k, color in enumerate(ARCOIRIS):
                capa.fill(color, (x, ondula + k * franja, tramo, franja))
        if alfa < 255:
            capa.set_alpha(alfa)
        x_capa = inicio - n * tramo if lado == 1 else inicio
        screen.blit(capa, (x_capa + offset_x, top_base + offset_y))

    def _dibujar_aviso(self, screen, fila):
        if (self.t // 6) % 2:
            return
        banda = pygame.Surface((GAME_WIDTH, 40), pygame.SRCALPHA)
        banda.fill((255, 60, 60, 70))
        screen.blit(banda, (0, int(fila) - 20))
        for x in range(0, GAME_WIDTH, 48):
            screen.fill((255, 235, 80), (x + 20, int(fila) - 12, 8, 16))
            screen.fill((255, 235, 80), (x + 20, int(fila) + 8, 8, 6))


class GatoPanBoss(JefeGatoBase):
    """Ultimo jefe bonus: el gato del meme "OIIA OIIA", que gira sin parar
    sobre su eje vertical con aceleracion y frenado suaves.
      - normal: gira lento, salta de lado a lado soltando un anillo de migas
        al aterrizar y arroja mini Gatos Pan en arco.
      - "OIIA": se planta, acelera el giro al maximo y escupe una espiral de
        migas que sigue su propio angulo; al frenar suelta un anillo final.
      - furioso (<40%): espirales de mas brazos y mas seguidas.
    Ataques especiales propios, en rotacion (ver _iniciar_especial):
      - RUEDA OIIA: gira a toda velocidad y rebota por media pantalla como
        un logo de DVD, dejando un rastro de migas que tarda en apagarse.
      - LLUVIA DE PANES: salta fuera de pantalla, marca las columnas y
        llueven panes en todas menos en un hueco (dos oleadas con el hueco
        corrido); cae encima de la nave con un anillo de migas.
      - CLONES OIIA: se parte en tres (dos copias fantasma) y los tres
        giran escupiendo espirales; solo el del medio recibe daño."""

    nombre = "GATO OIIA"
    hp_base = 1000
    ANCHO_COLUMNA = 80
    # 4 = un pixel del arte por cada pixel del entorno bonus (PIXEL_BONUS)
    ESCALA = 4
    GIRO_LENTO = 0.07
    GIRO_OIIA = 0.42
    DURACION_OIIA = 170

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = GAME_WIDTH / 2
        self.y = -120.0
        self.base_y = 160.0
        self.size = 58
        self.alto_sprite = 38 * self.ESCALA
        self.salto = None
        self.aplastado = 0
        self.timer_salto = 80
        self.timer_panes = 120
        self.timer_oiia = 200
        self.oiia = 0
        self.angulo = 0.0
        self.vel_giro = self.GIRO_LENTO
        self.angulo_espiral = 0.0
        self.especial = None
        self.timer_especial = 280
        self.indice_especial = 0
        self.clones = []

    def _girando_rapido(self):
        return self.oiia > 0 or (self.especial is not None and self.especial['tipo'] in ('rodante', 'clones'))

    def update(self, ship):
        self._tick_comun()
        balas = []
        v = self._vel()
        if self.aplastado > 0:
            self.aplastado -= 1

        # el giro nunca salta de velocidad: siempre se acerca de a poco al
        # objetivo (acelera al entrar en "OIIA", frena despacio al salir)
        objetivo = self.GIRO_OIIA * min(1.3, v) if self._girando_rapido() else self.GIRO_LENTO
        self.vel_giro += (objetivo - self.vel_giro) * 0.05
        self.angulo = (self.angulo + self.vel_giro) % (2 * math.pi)

        if self.entrando:
            self.y += 7
            if self.y >= self.base_y:
                self.y = self.base_y
                self.entrando = False
                self.aplastado = 10
        elif self.especial is not None:
            balas += self._actualizar_especial(ship, v)
        elif self.oiia > 0:
            balas += self._actualizar_oiia(v)
        elif self.salto is not None:
            s = self.salto
            s['t'] += 1
            p = min(1.0, s['t'] / s['dur'])
            self.x = s['x0'] + (s['x1'] - s['x0']) * p
            self.y = self.base_y - math.sin(math.pi * p) * s['altura']
            if p >= 1.0:
                self.salto = None
                self.y = self.base_y
                self.aplastado = 10
                n = 18 if self.furioso else 12
                balas += _anillo(self.x, self.y + 20, n, 2.7 * math.sqrt(v),
                                 MIGA, 12, desfase=random.uniform(0, math.pi))
        else:
            self.timer_especial -= 1
            self.timer_oiia -= 1
            self.timer_salto -= 1
            self.timer_panes -= 1
            if self.timer_especial <= 0:
                self.timer_especial = max(240, int((420 if not self.furioso else 320) / v))
                self._iniciar_especial()
            elif self.timer_oiia <= 0:
                self.timer_oiia = max(150, int((330 if not self.furioso else 240) / v))
                self.oiia = self.DURACION_OIIA
            elif self.timer_salto <= 0:
                self.timer_salto = max(45, int((110 if not self.furioso else 75) / v))
                destino = max(110.0, min(GAME_WIDTH - 110.0, ship.x + random.uniform(-140, 140)))
                self.salto = {'x0': self.x, 'x1': destino, 't': 0,
                              'dur': max(34, int(55 / math.sqrt(v))), 'altura': 90}
            elif self.timer_panes <= 0:
                self.timer_panes = max(55, int((130 if not self.furioso else 90) / v))
                sprite = sprite_pixel("pan", 0, 2)
                for dx in (-110, 0, 110):
                    balas.append(_lanzar_en_arco(self.x, self.y - 10, ship.x + dx, ship.y, sprite, radio=14))
        return balas

    # ------------------------------------------------ ataques especiales
    def _iniciar_especial(self):
        tipo = ("rodante", "lluvia", "clones")[self.indice_especial % 3]
        self.indice_especial += 1
        v = math.sqrt(self._vel())
        if tipo == "rodante":
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'rueda',
                             'vx': random.choice((-1, 1)) * 5.5 * v, 'vy': 4.2 * v}
            self._anunciar("¡RUEDA OIIA!")
        elif tipo == "lluvia":
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'sube', 'hueco': 0}
            self._anunciar("¡LLUVIA DE PANES!")
        else:
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'separa'}
            self.clones = [{'x': self.x, 'y': self.y, 'dx': -230}, {'x': self.x, 'y': self.y, 'dx': 230}]
            self._anunciar("¡CLONES OIIA!")

    def _terminar_especial(self):
        self.especial = None
        self.clones = []
        self.timer_salto = 60

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "rodante":
            if e['fase'] == 'rueda':
                self.x += e['vx']
                self.y += e['vy']
                if not 80 <= self.x <= GAME_WIDTH - 80:
                    e['vx'] = -e['vx']
                    self.x = max(80, min(GAME_WIDTH - 80, self.x))
                if not 120 <= self.y <= GAME_HEIGHT * 0.62:
                    e['vy'] = -e['vy']
                    self.y = max(120, min(GAME_HEIGHT * 0.62, self.y))
                if e['t'] % 4 == 0:
                    balas.append(BalaPixel(self.x, self.y + 10, 0, 0, color=MIGA, tam=12, vida=100))
                if e['t'] >= 220:
                    e['fase'] = 'vuelve'
            else:
                self.x += (GAME_WIDTH / 2 - self.x) * 0.06
                self.y += (self.base_y - self.y) * 0.08
                if abs(self.y - self.base_y) < 6:
                    self.y = self.base_y
                    balas += _anillo(self.x, self.y + 10, 14, 2.4 * math.sqrt(v), MIGA, 12)
                    self._terminar_especial()

        elif e['tipo'] == "lluvia":
            columnas = GAME_WIDTH // self.ANCHO_COLUMNA
            if e['fase'] == 'sube':
                self.y -= 12
                if self.y < -110:
                    e['fase'], e['t'] = 'aviso', 0
                    e['hueco'] = random.randint(1, columnas - 3)
            elif e['fase'] == 'aviso':
                if e['t'] >= 55:
                    e['fase'], e['t'] = 'cae', 0
            elif e['fase'] == 'cae':
                if e['t'] in (1, 45):
                    if e['t'] == 45:
                        # segunda oleada: el hueco se corre una columna
                        e['hueco'] = max(0, min(columnas - 2, e['hueco'] + random.choice((-1, 1))))
                    sprite = sprite_pixel("pan", 0, 2)
                    for c in range(columnas):
                        if c in (e['hueco'], e['hueco'] + 1):
                            continue
                        cx = c * self.ANCHO_COLUMNA + self.ANCHO_COLUMNA // 2
                        balas.append(BalaPixel(cx, -30, 0, 5.5 * math.sqrt(v), forma="sprite", sprite=sprite, radio=16))
                if e['t'] >= 110:
                    e['fase'] = 'aterriza'
                    self.x = max(110.0, min(GAME_WIDTH - 110.0, ship.x))
                    self.y = -120.0
            else:
                self.y += 14
                if self.y >= self.base_y:
                    self.y = self.base_y
                    self.aplastado = 12
                    balas += _anillo(self.x, self.y + 20, 20, 2.8 * math.sqrt(v), MIGA, 12,
                                     desfase=random.uniform(0, math.pi))
                    self._terminar_especial()

        else:  # clones
            if e['fase'] == 'separa':
                p = min(1.0, e['t'] / 30)
                for c in self.clones:
                    c['x'] = max(60.0, min(GAME_WIDTH - 60.0, self.x + c['dx'] * p))
                    c['y'] = self.y
                if p >= 1:
                    e['fase'], e['t'] = 'dispara', 0
            elif e['fase'] == 'dispara':
                if e['t'] % 9 == 0:
                    self.angulo_espiral += 0.28
                    velocidad = 2.4 * math.sqrt(v)
                    for i, (cx, cy) in enumerate([(self.x, self.y)] + [(c['x'], c['y']) for c in self.clones]):
                        for k in range(2):
                            a = self.angulo_espiral * (1 if i != 1 else -1) + math.pi * k + i
                            balas.append(BalaPixel(cx, cy + 10, math.cos(a) * velocidad, math.sin(a) * velocidad,
                                                   color=MIGA if i == 0 else PAN_CLARO, tam=12))
                if e['t'] >= 200:
                    e['fase'], e['t'] = 'junta', 0
            else:
                for c in self.clones:
                    c['x'] += (self.x - c['x']) * 0.15
                if e['t'] >= 25:
                    self._terminar_especial()
        return balas

    def _actualizar_oiia(self, v):
        """Espiral de migas mientras gira a toda velocidad."""
        balas = []
        self.oiia -= 1
        transcurrido = self.DURACION_OIIA - self.oiia
        # los primeros cuadros solo acelera (aviso visual), despues dispara
        if 30 <= transcurrido and self.oiia > 20 and transcurrido % 5 == 0:
            brazos = 3 if self.furioso else 2
            self.angulo_espiral += 0.23 * (1 if not self.furioso else 1.25)
            velocidad = 2.8 * math.sqrt(v)
            for k in range(brazos):
                a = self.angulo_espiral + 2 * math.pi * k / brazos
                balas.append(BalaPixel(self.x, self.y + 10, math.cos(a) * velocidad, math.sin(a) * velocidad,
                                       color=MIGA if k % 2 == 0 else PAN_CLARO, tam=12))
        if self.oiia == 0:
            balas += _anillo(self.x, self.y + 10, 16, 2.2 * math.sqrt(v), MIGA, 12,
                             desfase=self.angulo_espiral)
        return balas

    def _sprite_girando(self):
        """Sprite segun el angulo de giro. Con frames propios (un video del
        gato girando) elige el frame que corresponde al angulo; sin ellos
        hace lo mismo que el meme: el recorte de frente gira como un cartel,
        angostandose con |cos(angulo)| y dado vuelta cuando mira atras."""
        blanco = self.flash % 2 == 1
        if frames_personalizados("pan"):
            n = len(frames_personalizados("pan"))
            indice = int(self.angulo / (2 * math.pi) * n) % n
            return frame_personalizado("pan", indice, self.alto_sprite, blanco=blanco)
        coseno = math.cos(self.angulo)
        # "O" tranquilo, "I" mientras gira rapido, "A" al frenar o aterrizar
        if self.aplastado > 0 or 0 < self.oiia < 30:
            boca = 2
        elif self._girando_rapido():
            boca = 1
        else:
            boca = (self.t // 12) % 2
        base = sprite_pixel("oiia", boca, self.ESCALA, voltear=coseno < 0, blanco=blanco)
        factor = abs(coseno)
        ancho, alto = base.get_size()
        if self.aplastado > 0:
            # al aterrizar se aplasta un poco, como un resorte
            factor *= 1.12
            alto = int(alto * 0.86)
        return pygame.transform.scale(base, (max(PIXEL_BONUS, int(ancho * factor)), alto))

    def draw(self, screen, offset_x=0, offset_y=0):
        e = self.especial
        if e is not None and e['tipo'] == 'lluvia' and e['fase'] in ('aviso', 'cae'):
            # columnas marcadas: flechas rojas donde caen panes, verdes en el hueco
            parpadeo = (self.t // 6) % 2 == 0
            for c in range(GAME_WIDTH // self.ANCHO_COLUMNA):
                cx = c * self.ANCHO_COLUMNA + self.ANCHO_COLUMNA // 2 + offset_x
                hueco = c in (e['hueco'], e['hueco'] + 1)
                if e['fase'] == 'cae' and not hueco:
                    continue
                color = MENTA if hueco else (255, 80, 80)
                if hueco or parpadeo:
                    for k in range(3):
                        screen.fill(color, (cx - 12 + k * 4, 16 + k * 4 + offset_y, 24 - k * 8, 4))
        for c in self.clones:
            copia = self._sprite_girando().copy()
            copia.set_alpha(120)
            _blit_centrado(screen, copia, c['x'] + offset_x, c['y'] + offset_y)
        if self.salto is not None or self.entrando:
            sombra = pygame.Surface((120, 18), pygame.SRCALPHA)
            pygame.draw.ellipse(sombra, (0, 0, 0, 80), (0, 0, 120, 18))
            screen.blit(sombra, (int(self.x) - 60 + offset_x, int(self.base_y) + self.alto_sprite // 2 - 8 + offset_y))
        if self._girando_rapido():
            # remolino de lineas alrededor mientras gira rapido
            for i in range(6):
                a = self.angulo * 2 + i * math.pi / 3
                r = 80
                px = int(self.x + math.cos(a) * r) + offset_x
                py = int(self.y + math.sin(a) * r * 0.45) + offset_y
                screen.fill(MIGA, (px - 4, py - 2, 8, 4))
        _blit_centrado(screen, self._sprite_girando(), self.x + offset_x, self.y + offset_y)

    def draw_ui(self, surface):
        super().draw_ui(surface)
        if self.oiia > 0 and (self.t // 8) % 2 == 0:
            texto = render_text("OIIA OIIA", 22, MIGA)
            surface.blit(texto, (int(self.x) - texto.get_width() // 2, int(self.y) + self.alto_sprite // 2 + 14))


class GatoAlienBoss(JefeGatoBase):
    """Segundo jefe bonus (despues de Nyan Cat): el Gato Alien flota en su
    plato volador soltando anillos de destellos verdes y, cada tanto, se
    para encima de la nave, avisa y baja un rayo tractor vertical que hay
    que esquivar hacia un costado. Furioso (<40%): persigue a la nave y
    suma disparos apuntados.

    invencible=True (asi entra en la cadena del bonus): no recibe daño,
    persigue a la nave con ataques cada vez mas rapidos y, si la nave
    aguanta ABDUCCION_TRAS cuadros, la abduce con un rayo que no se puede
    esquivar (pide_matar_nave=True, main.py la destruye). Esa derrota lleva
    a la cinematica del tripulante (modules/entities/tripulante.py), que
    llama a volverse_vulnerable().

    Ya vulnerable suma ataques especiales propios, en rotacion:
      - CONSTELACION: siembra minas-estrella por la pantalla (lejos de la
        nave) que parpadean cada vez mas rapido y estallan en anillos.
      - TELETRANSPORTE: se desvanece y reaparece del lado opuesto a la nave
        tres veces seguidas, disparando al reaparecer.
      - RAYOS EN PINZA: dos rayos tractores nacen en los bordes y se cierran
        sobre la nave hasta dejarle un pasillo angosto."""

    nombre = "GATO ALIEN"
    hp_base = 900
    ESCALA = 5
    ABDUCCION_TRAS = 35 * 60

    def __init__(self, dificultad=1.0, invencible=False):
        super().__init__(dificultad)
        self.invencible = invencible
        self.t_invencible = 0
        self.escudo = 0
        self.abduccion = None
        self.pide_matar_nave = False
        self.x = GAME_WIDTH / 2
        self.y = -140.0
        self.base_y = 150.0
        self.size = 62
        self.alto_sprite = 26 * self.ESCALA
        self.timer_estrellas = 90
        self.timer_rayo = 240
        self.timer_apuntado = 60
        self.rayo = None
        self.giro = 0.0
        self.especial = None
        self.timer_especial = 260
        self.indice_especial = 0
        self.minas = []
        self.alfa = 255

    def take_damage(self, amount=1):
        if self.invencible:
            if not self.entrando:
                self.escudo = 8  # el escudo destella: el disparo rebota
            return
        super().take_damage(amount)

    def volverse_vulnerable(self):
        """Despues de la cinematica del tripulante: el escudo cae y la pelea
        sigue normal (con la vida llena y sin el rayo de abduccion)."""
        self.invencible = False
        self.abduccion = None
        self.rayo = None
        self.pide_matar_nave = False
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.furioso = False
        self.timer_rayo = 200
        self.timer_especial = 240

    def _vel(self):
        if self.invencible:
            # se pone mas agresivo cuanto mas aguanta la nave
            return self.dificultad * (1.5 + min(0.9, self.t_invencible / 2000))
        return super()._vel()

    def update(self, ship):
        self._tick_comun()
        balas = []
        v = self._vel()
        if self.escudo > 0:
            self.escudo -= 1

        if self.entrando:
            self.y += (self.base_y - self.y) * 0.05 + 1
            if self.y >= self.base_y - 2:
                self.entrando = False
            return balas

        if self.invencible:
            self.t_invencible += 1
            if self.abduccion is None and self.rayo is None and self.t_invencible >= self.ABDUCCION_TRAS:
                self.abduccion = {'estado': 'fija', 'timer': 0}

        balas += self._actualizar_minas(v)

        if self.abduccion is not None:
            self._actualizar_abduccion(ship)
        elif self.especial is not None:
            balas += self._actualizar_especial(ship, v)
        elif self.rayo is not None:
            balas += self._actualizar_rayo(ship)
        else:
            if self.furioso or self.invencible:
                tx = ship.x
            else:
                tx = GAME_WIDTH / 2 + math.sin(self.t * 0.012) * 300
            tx = max(110.0, min(GAME_WIDTH - 110.0, tx))
            self.x += (tx - self.x) * 0.03
            self.y = self.base_y + math.sin(self.t * 0.05) * 12

            self.timer_estrellas -= 1
            if self.timer_estrellas <= 0:
                self.timer_estrellas = max(45, int(100 / v))
                self.giro += 0.3
                n = 14 if self.furioso else 10
                balas += _anillo(self.x, self.y + 20, n, 2.6 * math.sqrt(v), OVNI_LUZ, 16,
                                 forma="estrella", desfase=self.giro)

            if self.furioso or self.invencible:
                self.timer_apuntado -= 1
                if self.timer_apuntado <= 0:
                    self.timer_apuntado = max(22, int(50 / v))
                    base = _apuntada(self.x, self.y + 30, ship, 5.0, color=ESTRELLA_VERDE,
                                     tam=16, forma="estrella")
                    balas.append(base)
                    if self.invencible:
                        # abanico de tres: le cierra los costados a la nave
                        a = math.atan2(base.vy, base.vx)
                        for d in (-0.3, 0.3):
                            balas.append(BalaPixel(self.x, self.y + 30, math.cos(a + d) * 5.0, math.sin(a + d) * 5.0,
                                                   color=ESTRELLA_VERDE, tam=16, forma="estrella"))

            self.timer_rayo -= 1
            if not self.invencible:
                self.timer_especial -= 1
            if not self.invencible and self.timer_especial <= 0:
                self.timer_especial = max(280, int((500 if not self.furioso else 380) / v))
                self._iniciar_especial(ship)
            elif self.timer_rayo <= 0:
                self.timer_rayo = max(170, int(280 / v))
                self.rayo = {'estado': 'apunta', 'timer': 0}
        return balas

    # ------------------------------------------------ ataques especiales
    def _iniciar_especial(self, ship):
        tipo = ("constelacion", "teletransporte", "pinza")[self.indice_especial % 3]
        self.indice_especial += 1
        if tipo == "constelacion":
            self.especial = {'tipo': tipo, 't': 0}
            self._anunciar("¡CONSTELACION!")
        elif tipo == "teletransporte":
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'fuera', 'saltos': 0}
            self._anunciar("¡TELETRANSPORTE!")
        else:
            meta = max(140.0, min(GAME_WIDTH - 140.0, ship.x))
            self.especial = {'tipo': tipo, 't': 0, 'izq': 20.0, 'der': GAME_WIDTH - 20.0,
                             'meta_izq': meta - 95, 'meta_der': meta + 95}
            self._anunciar("¡RAYOS EN PINZA!")

    def _actualizar_minas(self, v):
        balas = []
        for m in self.minas:
            m['t'] += 1
            if m['t'] >= m['dura']:
                balas += _anillo(m['x'], m['y'], 8, 2.6 * math.sqrt(v), ESTRELLA_VERDE, 14,
                                 forma="estrella", desfase=random.uniform(0, math.pi))
        self.minas = [m for m in self.minas if m['t'] < m['dura']]
        return balas

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "constelacion":
            # se queda quieto "sembrando" y deja las minas por la pantalla
            if e['t'] == 20:
                cantidad = 7 if self.furioso else 5
                intentos = 0
                while cantidad > 0 and intentos < 60:
                    intentos += 1
                    mx = random.uniform(70, GAME_WIDTH - 70)
                    my = random.uniform(GAME_HEIGHT * 0.3, GAME_HEIGHT - 60)
                    if math.hypot(mx - ship.x, my - ship.y) < 130:
                        continue
                    self.minas.append({'x': mx, 'y': my, 't': 0, 'dura': 110 + cantidad * 12})
                    cantidad -= 1
            if e['t'] >= 45:
                self.especial = None

        elif e['tipo'] == "teletransporte":
            if e['fase'] == 'fuera':
                self.alfa = max(0, 255 - e['t'] * 12)
                if e['t'] >= 22:
                    # reaparece del lado contrario a la nave
                    self.x = max(110.0, min(GAME_WIDTH - 110.0, GAME_WIDTH - ship.x + random.uniform(-60, 60)))
                    self.y = self.base_y + random.uniform(-20, 50)
                    e['fase'], e['t'] = 'dentro', 0
            else:
                self.alfa = min(255, e['t'] * 12)
                if e['t'] >= 22:
                    self.alfa = 255
                    balas += _anillo(self.x, self.y + 20, 14, 2.8 * math.sqrt(v), OVNI_LUZ, 16,
                                     forma="estrella", desfase=random.uniform(0, math.pi))
                    base = _apuntada(self.x, self.y + 30, ship, 5.5, color=ESTRELLA_VERDE, tam=16, forma="estrella")
                    balas.append(base)
                    e['saltos'] += 1
                    if e['saltos'] >= 3:
                        self.especial = None
                    else:
                        e['fase'], e['t'] = 'fuera', 0

        else:  # pinza
            p = min(1.0, max(0.0, (e['t'] - 30) / 100))
            e['izq'] = 20 + (e['meta_izq'] - 20) * p
            e['der'] = (GAME_WIDTH - 20) + (e['meta_der'] - (GAME_WIDTH - 20)) * p
            if e['t'] > 30:
                # hitbox de los dos rayos, renovada cada cuadro
                for bx in (e['izq'], e['der']):
                    y = 60
                    while y < GAME_HEIGHT + 20:
                        balas.append(BalaPixel(bx, y, 0, 0, vida=2, radio=14, visible=False))
                        y += 18
            if e['t'] >= 170:
                self.especial = None
        return balas

    def _actualizar_abduccion(self, ship):
        """Rayo final del modo invencible: se clava sobre la nave y la sigue
        a donde vaya; al terminar pide a main.py que la destruya."""
        a = self.abduccion
        a['timer'] += 1
        seguir = 0.2 if a['estado'] == 'fija' else 0.5
        self.x += (max(60.0, min(GAME_WIDTH - 60.0, ship.x)) - self.x) * seguir
        self.y += (self.base_y - self.y) * 0.1
        if a['estado'] == 'fija' and a['timer'] >= 70:
            a['estado'], a['timer'] = 'atrapa', 0
        elif a['estado'] == 'atrapa' and a['timer'] >= 80:
            self.abduccion = None
            self.t_invencible = 0
            self.pide_matar_nave = True

    def _actualizar_rayo(self, ship):
        r = self.rayo
        r['timer'] += 1
        balas = []
        if r['estado'] == 'apunta':
            tx = max(110.0, min(GAME_WIDTH - 110.0, ship.x))
            self.x += (tx - self.x) * 0.08
            if r['timer'] >= 40:
                r['estado'], r['timer'] = 'aviso', 0
        elif r['estado'] == 'aviso':
            if r['timer'] >= 45:
                r['estado'], r['timer'] = 'dispara', 0
                y = self.y + 60
                while y < GAME_HEIGHT + 20:
                    balas.append(BalaPixel(self.x, y, 0, 0, vida=50, radio=12, visible=False))
                    y += 18
        elif r['timer'] >= 50:
            self.rayo = None
        return balas

    def draw(self, screen, offset_x=0, offset_y=0):
        for m in self.minas:
            # estrella que late cada vez mas rapido antes de estallar
            restante = m['dura'] - m['t']
            ritmo = 4 if restante < 40 else 10
            r = 10 if (m['t'] // ritmo) % 2 == 0 else 14
            mx, my = int(m['x']) + offset_x, int(m['y']) + offset_y
            color = (255, 90, 120) if restante < 40 else ESTRELLA_VERDE
            screen.fill(color, (mx - r, my - 3, r * 2, 6))
            screen.fill(color, (mx - 3, my - r, 6, r * 2))
            screen.fill(WHITE, (mx - 3, my - 3, 6, 6))
        e = self.especial
        if e is not None and e['tipo'] == 'pinza':
            for bx in (e['izq'], e['der']):
                x = int(bx) + offset_x
                if e['t'] <= 30:
                    if (self.t // 4) % 2 == 0:
                        screen.fill((255, 80, 120), (x - 2, 60 + offset_y, 4, GAME_HEIGHT - 60))
                else:
                    rayo = pygame.Surface((40, GAME_HEIGHT - 60), pygame.SRCALPHA)
                    rayo.fill((*OVNI_LUZ, 120))
                    rayo.fill((255, 255, 255, 190), (13, 0, 14, GAME_HEIGHT - 60))
                    screen.blit(rayo, (x - 20, 60 + offset_y))
        if self.abduccion is not None:
            x = int(self.x) + offset_x
            y0 = int(self.y) + 50 + offset_y
            alto = GAME_HEIGHT - y0 + offset_y
            if self.abduccion['estado'] == 'fija':
                if (self.t // 4) % 2 == 0:
                    screen.fill((255, 80, 120), (x - 3, y0, 6, alto))
            else:
                ancho = 90 + int(math.sin(self.t * 0.3) * 10)
                rayo = pygame.Surface((ancho, max(1, alto)), pygame.SRCALPHA)
                rayo.fill((*OVNI_LUZ, 130))
                rayo.fill((255, 255, 255, 200), (ancho // 2 - 14, 0, 28, max(1, alto)))
                screen.blit(rayo, (x - ancho // 2, y0))
                for i in range(0, alto, 20):
                    fy = y0 + alto - (i + self.t * 8) % max(1, alto)
                    screen.fill(ESTRELLA_VERDE, (x - ancho // 2 + (i * 13) % ancho, fy, 6, 6))
        if self.rayo is not None and self.rayo['estado'] in ('aviso', 'dispara'):
            x = int(self.x) + offset_x
            y0 = int(self.y) + 50 + offset_y
            alto = GAME_HEIGHT - y0 + offset_y
            if self.rayo['estado'] == 'aviso':
                if (self.t // 5) % 2 == 0:
                    screen.fill(OVNI_LUZ, (x - 2, y0, 4, alto))
            else:
                rayo = pygame.Surface((48, max(1, alto)), pygame.SRCALPHA)
                rayo.fill((*OVNI_LUZ, 110))
                rayo.fill((255, 255, 255, 190), (16, 0, 16, max(1, alto)))
                screen.blit(rayo, (x - 24, y0))
                for i in range(0, alto, 24):
                    fy = y0 + (i + self.t * 6) % max(1, alto)
                    screen.fill(ESTRELLA_VERDE, (x - 20 + (i * 7) % 36, fy, 4, 4))
        sprite = sprite_pixel("ovni", (self.t // 10) % 2, self.ESCALA, blanco=self.flash % 2 == 1)
        if self.alfa < 255:
            sprite = sprite.copy()
            sprite.set_alpha(self.alfa)
        _blit_centrado(screen, sprite, self.x + offset_x, self.y + offset_y)
        if self.invencible:
            # burbuja de escudo: tenue siempre, brillante al rebotar un tiro
            radio = self.alto_sprite // 2 + 22
            alfa = 170 if self.escudo > 0 else 60 + int(30 * math.sin(self.t * 0.1))
            burbuja = pygame.Surface((radio * 2 + 8, radio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(burbuja, (*ESTRELLA_VERDE, alfa // 3), (radio + 4, radio + 4), radio)
            pygame.draw.circle(burbuja, (*ESTRELLA_VERDE, alfa), (radio + 4, radio + 4), radio, 6)
            _blit_centrado(screen, burbuja, self.x + offset_x, self.y + offset_y)

    def draw_ui(self, surface):
        if not self.invencible:
            super().draw_ui(surface)
            return
        ancho, alto = 150, 12
        x = max(8, min(GAME_WIDTH - ancho - 8, int(self.x) - ancho // 2))
        y = max(40, int(self.y - self.alto_sprite / 2) - 26)
        nombre = render_text(self.name + " (INVENCIBLE)", 12, ESTRELLA_VERDE)
        surface.blit(nombre, (x + ancho // 2 - nombre.get_width() // 2, y - 16))
        surface.fill(NEGRO, (x - 2, y - 2, ancho + 4, alto + 4))
        pygame.draw.rect(surface, WHITE, (x - 2, y - 2, ancho + 4, alto + 4), 2)
        for sx in range(0, ancho, 6):
            brillo = 150 + int(80 * math.sin(self.t * 0.15 + sx * 0.1))
            surface.fill((brillo, brillo, brillo), (x + sx + 1, y + 2, 4, alto - 4))
        if self.abduccion is not None and (self.t // 8) % 2 == 0:
            aviso = render_text("¡ABDUCCION!", 22, (255, 90, 130))
            surface.blit(aviso, (int(self.x) - aviso.get_width() // 2, int(self.y) + self.alto_sprite // 2 + 10))


# ------------------------------------------------------------- cinematica

class CinematicaGatoDormido:
    """Cinematica final al derrotar al Gato Pan: noche estrellada con luna,
    el gatito dormido en su almohadon (respira y suelta "Zzz"), el texto
    "¡FELICIDADES!" en arcoiris y "Ayudaste a dormir a mi gato" escribiendose
    letra por letra. Se dibuja a resolucion de arte (1/PIXEL_BONUS) y se
    agranda sin filtrado, el texto va encima nitido.

    update() una vez por cuadro; saltar() adelanta el fundido de salida;
    terminada indica que ya se puede pasar a la pantalla de victoria."""

    DURACION = 600
    FUNDIDO = 45
    MENSAJE = "Ayudaste a dormir a mi gato"

    def __init__(self):
        self.t = 0
        self.fin = self.DURACION
        self.ancho = GAME_WIDTH // PIXEL_BONUS
        self.alto = GAME_HEIGHT // PIXEL_BONUS
        rng = random.Random(11)
        self.estrellas = [(rng.randrange(self.ancho), rng.randrange(int(self.alto * 0.62)), rng.randrange(60))
                          for _ in range(45)]
        self.zetas = []

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        """Enter/click: arranca el fundido de salida (si no empezo ya)."""
        if self.t > 60:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def update(self):
        self.t += 1
        if self.t % 55 == 0:
            self.zetas.append({'x': self.ancho / 2 - 30, 'y': self.alto * 0.56, 'vida': 0})
        for z in self.zetas:
            z['vida'] += 1
            z['y'] -= 0.22
            z['x'] += 0.12 + math.sin(z['vida'] * 0.08) * 0.25
        self.zetas = [z for z in self.zetas if z['vida'] < 150]

    def _dibujar_z(self, arte, x, y, escala, color):
        e = escala
        x, y = int(x), int(y)
        arte.fill(color, (x, y, 4 * e, e))
        for i in range(3):
            arte.fill(color, (x + (3 - i) * e - e // 2, y + (i + 1) * e, e, e))
        arte.fill(color, (x, y + 4 * e, 4 * e, e))

    def draw(self, surface):
        arte = pygame.Surface((self.ancho, self.alto))
        # cielo nocturno en bandas
        bandas = ((12, 14, 44), (16, 20, 58), (22, 26, 74), (28, 32, 88))
        for i, color in enumerate(bandas):
            arte.fill(color, (0, i * self.alto // 8, self.ancho, self.alto))
        for x, y, fase in self.estrellas:
            if ((self.t + fase) // 25) % 3:
                arte.fill(WHITE, (x, y, 1, 1))
        # luna creciente
        # (en la esquina, fuera del camino del titulo)
        pygame.draw.circle(arte, (255, 240, 180), (self.ancho - 20, 18), 11)
        pygame.draw.circle(arte, bandas[0], (self.ancho - 15, 14), 10)
        # colina/piso
        pygame.draw.ellipse(arte, (34, 30, 80), (-40, int(self.alto * 0.72), self.ancho + 80, self.alto))
        # gatito dormido (respira cada ~2 s)
        cuadro = 1 if math.sin(self.t * 0.05) > 0 else 0
        gato = sprite_pixel("durmiendo", cuadro, 2)
        arte.blit(gato, (self.ancho // 2 - gato.get_width() // 2, int(self.alto * 0.52)))
        for z in self.zetas:
            escala = 1 + z['vida'] // 50
            tono = max(90, 255 - z['vida'])
            self._dibujar_z(arte, z['x'], z['y'], escala, (tono, tono, 255))

        surface.blit(pygame.transform.scale(arte, surface.get_size()), (0, 0))

        # textos nitidos
        neon.franjas_cine(surface, self.t / 40, neon.MAGENTA, alto=40)
        if self.t > 70:
            dibujar_texto_arcoiris(surface, "¡FELICIDADES!", get_font(64, bold=True), GAME_WIDTH // 2, 70,
                                   self.t, amplitud=8)
        if self.t > 120:
            fuente = get_font(28, bold=True)
            caja = pygame.Rect(0, 0, fuente.size(self.MENSAJE)[0] + 60, 64)
            caja.center = (GAME_WIDTH // 2, 186)
            neon.panel(surface, caja, neon.MAGENTA, self.t, halo=False)
            letras = min(len(self.MENSAJE), max(0, self.t - 130) // 3)
            texto = fuente.render(self.MENSAJE[:letras], True, WHITE)
            surface.blit(texto, (caja.x + 30, caja.centery - texto.get_height() // 2))
            if letras < len(self.MENSAJE) and (self.t // 8) % 2 == 0:
                surface.fill(neon.MAGENTA, (caja.x + 32 + texto.get_width(), caja.centery - 12, 12, 24))
        if self.t > 260 and (self.t // 30) % 2 == 0:
            neon.cinta(surface, "ENTER para continuar", neon.MAGENTA, (GAME_WIDTH // 2, GAME_HEIGHT - 64), tam=14)
        neon.scanlines(surface)

        # fundido de entrada (desde blanco, la explosion) y de salida (a negro)
        if self.t < self.FUNDIDO:
            velo = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            velo.fill((255, 255, 255, int(255 * (1 - self.t / self.FUNDIDO))))
            surface.blit(velo, (0, 0))
        restante = self.fin - self.t
        if restante < self.FUNDIDO:
            velo = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            velo.fill((0, 0, 0, int(255 * (1 - max(0, restante) / self.FUNDIDO))))
            surface.blit(velo, (0, 0))


# --------------------------------------- cinematica del golpe del Gato Alien

_FILAS_CORAZON = (".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X...")
CORAZON_VIVO = (255, 70, 110)
CORAZON_LUZ = (255, 190, 210)
CORAZON_VACIO = (70, 40, 60)


def _dibujar_corazon(surface, x, y, tam, lleno, blanco=False):
    """Corazon pixel de 7x6 (cada pixel de `tam`), con contorno."""
    for fy, fila in enumerate(_FILAS_CORAZON):
        for fx, c in enumerate(fila):
            if c == "X":
                surface.fill(neon.CONTORNO, (x + fx * tam - 2, y + fy * tam - 2, tam + 4, tam + 4))
    for fy, fila in enumerate(_FILAS_CORAZON):
        for fx, c in enumerate(fila):
            if c != "X":
                continue
            if blanco:
                color = WHITE
            elif not lleno:
                color = CORAZON_VACIO
            elif (fx, fy) in ((1, 1), (2, 1), (1, 2)):
                color = CORAZON_LUZ
            else:
                color = CORAZON_VIVO
            surface.fill(color, (x + fx * tam, y + fy * tam, tam, tam))


class CinematicaGolpeAlien:
    """Antes de la pelea contra el Gato Alien: el plato baja, carga energia
    verde ("¡Miau! Esto te va a doler."), se tira en picada y le pega de
    lleno a la nave. Destello, temblor, la nave sale despedida y la barra
    de corazones se vacia uno por uno hasta dejar UNA sola vida
    ("¡GOLPE CRITICO!" / "1 VIDA RESTANTE"); el plato vuelve arriba riendose
    y arranca la pelea.

    nave_pos: donde esta la nave (para que la pelea siga desde ahi).
    eventos: "carga", "golpe" y "vida" (un corazon perdido) para los
    sonidos de main.py; temblor: pixeles de sacudida del cuadro."""

    FUNDIDO = 30
    BAJA_HASTA = 70
    CARGA_HASTA = 150
    T_GOLPE = 172
    DRENA_DESDE = 196
    PASO_VIDA = 16

    def __init__(self, sprite_nave, vidas, max_vidas, nave_pos):
        self.sprite_nave = sprite_nave
        self.vidas = max(1, vidas)
        self.max_vidas = max(self.vidas, max_vidas, 1)
        self.nave_pos = nave_pos
        self.t = 0
        self.eventos = []
        self.temblor = 0
        self.fondo = FondoPixel()
        self.chispas = []
        self.anillos = []
        # cuadro en que se apaga el ultimo corazon (vidas - 1 en total)
        self.fin_drenado = self.DRENA_DESDE + (self.vidas - 2) * self.PASO_VIDA
        self.duracion = self.fin_drenado + 170
        self.fin = self.duracion
        self.ovni_arriba = (GAME_WIDTH / 2, GAME_HEIGHT * 0.26)

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 30:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def vidas_mostradas(self):
        """Corazones llenos en la barra: todas hasta el golpe, despues se
        van apagando de a uno hasta quedar en 1."""
        if self.t < self.DRENA_DESDE:
            return self.vidas
        perdidas = (self.t - self.DRENA_DESDE) // self.PASO_VIDA + 1
        return max(1, self.vidas - perdidas)

    def _pos_ovni(self):
        ax, ay = self.ovni_arriba
        nx, ny = self.nave_pos
        t = self.t
        if t < self.BAJA_HASTA:
            p = 1 - (1 - t / self.BAJA_HASTA) ** 3
            return ax, -80 + (ay + 80) * p
        if t < self.CARGA_HASTA:
            # flota temblando mientras carga (cada vez mas)
            k = (t - self.BAJA_HASTA) / (self.CARGA_HASTA - self.BAJA_HASTA)
            return ax + random.uniform(-1, 1) * 6 * k, ay + math.sin(t * 0.12) * 6
        if t < self.T_GOLPE:
            # retrocede un poquito y se tira en picada
            p = (t - self.CARGA_HASTA) / (self.T_GOLPE - self.CARGA_HASTA)
            if p < 0.3:
                return ax, ay - 30 * (p / 0.3)
            q = ((p - 0.3) / 0.7) ** 2
            return ax + (nx - ax) * q, ay - 30 + (ny - 40 - ay + 30) * q
        # rebota y vuelve arriba
        p = min(1.0, (t - self.T_GOLPE) / 60)
        suave = 1 - (1 - p) ** 3
        return nx + (ax - nx) * suave, ny - 40 + (ay - ny + 40) * suave - math.sin(math.pi * p) * 60

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        self.fondo.update()
        ox, oy = self._pos_ovni()
        if self.t == self.BAJA_HASTA:
            self.eventos.append("carga")
        if self.BAJA_HASTA <= self.t < self.CARGA_HASTA and self.t % 9 == 0:
            self.anillos.append([ox, oy + 10, 120.0])
        for a in self.anillos:
            a[0], a[1] = ox, oy + 10
            a[2] -= 4
        self.anillos = [a for a in self.anillos if a[2] > 10]
        if self.T_GOLPE - 22 < self.t < self.T_GOLPE:
            # estela verde de la picada
            self.chispas.append([ox + random.uniform(-30, 30), oy + random.uniform(-10, 20), 0, -1, 18, ESTRELLA_VERDE])
        if self.t == self.T_GOLPE:
            self.eventos.append("golpe")
            self.temblor = 26
            nx, ny = self.nave_pos
            for _ in range(60):
                a = random.uniform(0, 2 * math.pi)
                v = random.uniform(2, 11)
                color = random.choice((WHITE, AMARILLO, ESTRELLA_VERDE, (255, 120, 60)))
                self.chispas.append([nx, ny, math.cos(a) * v, math.sin(a) * v, random.randint(20, 45), color])
        if self.DRENA_DESDE <= self.t <= self.fin_drenado and (self.t - self.DRENA_DESDE) % self.PASO_VIDA == 0:
            self.eventos.append("vida")
            self.temblor = max(self.temblor, 8)
        if self.T_GOLPE < self.t < self.fin_drenado + 60 and self.t % 5 == 0:
            # humo de la nave averiada
            nx, ny = self._pos_nave()
            self.chispas.append([nx + random.uniform(-12, 12), ny, random.uniform(-0.4, 0.4), -1.2,
                                 30, random.choice(((90, 90, 110), (60, 60, 80)))])
        for c in self.chispas:
            c[0] += c[2]
            c[1] += c[3]
            c[2] *= 0.94
            c[3] *= 0.94
            c[4] -= 1
        self.chispas = [c for c in self.chispas if c[4] > 0]

    def _pos_nave(self):
        nx, ny = self.nave_pos
        d = self.t - self.T_GOLPE
        if d < 0:
            return nx, ny + math.sin(self.t * 0.08) * 3
        # sale despedida para abajo y vuelve despacio a su lugar
        retroceso = 70 * math.exp(-d / 30) * min(1.0, d / 4)
        return nx + math.sin(d * 0.9) * 8 * math.exp(-d / 25), ny + retroceso

    def draw(self, surface):
        mundo = pygame.Surface(surface.get_size())
        self.fondo.draw(mundo)
        ox, oy = self._pos_ovni()
        d = self.t - self.T_GOLPE

        # carga: anillos verdes que se cierran sobre el plato
        for x, y, r in self.anillos:
            neon.anillo_pixel(mundo, ESTRELLA_VERDE, x, y, r, 8)
        if self.BAJA_HASTA <= self.t < self.T_GOLPE:
            k = min(1.0, (self.t - self.BAJA_HASTA) / (self.CARGA_HASTA - self.BAJA_HASTA))
            brillo = pygame.Surface((240, 240), pygame.SRCALPHA)
            pygame.draw.circle(brillo, (*OVNI_LUZ, int(40 + 90 * k)), (120, 120), int(40 + 60 * k))
            mundo.blit(brillo, (int(ox) - 120, int(oy) - 110))

        # la nave (en rojo y titilando despues del golpe)
        nx, ny = self._pos_nave()
        if self.sprite_nave is not None:
            nave = pygame.transform.scale(self.sprite_nave, (self.sprite_nave.get_width() * 2,
                                                             self.sprite_nave.get_height() * 2))
            if 0 <= d < 90 and (d // 4) % 2 == 0:
                nave = nave.copy()
                nave.fill((255, 60, 60, 0), special_flags=pygame.BLEND_RGBA_MAX)
            _blit_centrado(mundo, nave, nx, ny)

        ovni = sprite_pixel("ovni", (self.t // 8) % 2, 5, blanco=0 <= d < 6)
        _blit_centrado(mundo, ovni, ox, oy)
        for x, y, _, _, vida, color in self.chispas:
            neon.cuadro_pixel(mundo, color, x, y, 8 if vida > 15 else 4)

        surface.blit(pixelar(mundo, PIXEL_BONUS), (0, 0))

        # impacto: destello blanco y onda
        if 0 <= d < 14:
            neon.velo(surface, WHITE, 255 * (1 - d / 14))
        if 0 <= d < 30:
            neon.anillo_pixel(surface, WHITE, self.nave_pos[0], self.nave_pos[1], 20 + d * 12, 10)

        # textos nitidos
        neon.franjas_cine(surface, self.t / 30, neon.VERDE, alto=48)
        if 20 < self.t < self.BAJA_HASTA + 30 and (self.t // 6) % 4 != 0:
            neon.titulo(surface, "¡GATO ALIEN!", 52, neon.VERDE, GAME_WIDTH // 2, 110)
        if self.BAJA_HASTA + 10 < self.t < self.T_GOLPE - 8:
            neon.globo(surface, "¡Miau! Esto te va a doler.", ox + 40, oy - 60, neon.VERDE, cola_derecha=True, tam=20)
        if 0 <= d < 18:
            neon.titulo(surface, "¡PUM!", 80, AMARILLO, GAME_WIDTH // 2, GAME_HEIGHT // 2)
        if d >= 8:
            if self.t < self.fin_drenado + 50 and (d // 5) % 3 != 0:
                neon.titulo(surface, "¡GOLPE CRITICO!", 46, neon.ROJO, GAME_WIDTH // 2, GAME_HEIGHT // 2 - 60)
            if self.t >= self.fin_drenado + 20 and (self.t // 10) % 3 != 0:
                neon.cinta(surface, "1 VIDA RESTANTE", neon.ROJO, (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 80), tam=24)
            self._dibujar_vidas(surface)

        neon.scanlines(surface)
        restante = self.fin - self.t
        if restante < self.FUNDIDO:
            neon.velo(surface, (0, 0, 0), 255 * (1 - max(0, restante) / self.FUNDIDO))

    def _dibujar_vidas(self, surface):
        """Barra de corazones grande bajo el titulo; el que se apaga en este
        cuadro destella en blanco y sacude."""
        tam = 6 if self.max_vidas <= 10 else 4
        ancho = 7 * tam + 14
        total = self.max_vidas * ancho - 14
        x0 = GAME_WIDTH // 2 - total // 2
        y = GAME_HEIGHT // 2 - 6
        llenos = self.vidas_mostradas()
        caja = pygame.Rect(x0 - 24, y - 16, total + 48, 6 * tam + 32)
        neon.panel(surface, caja, neon.ROJO, self.t, halo=False)
        recien = (self.t - self.DRENA_DESDE) % self.PASO_VIDA < 6 and self.DRENA_DESDE <= self.t <= self.fin_drenado
        for i in range(self.max_vidas):
            x = x0 + i * ancho
            sacudida = random.randint(-3, 3) if recien and i == llenos else 0
            _dibujar_corazon(surface, x + sacudida, y + sacudida, tam, i < llenos and i < self.vidas,
                             blanco=recien and i == llenos)
        if llenos == 1 and self.t > self.fin_drenado and (self.t // 8) % 2 == 0:
            # el ultimo corazon late
            _dibujar_corazon(surface, x0, y, tam, True, blanco=True)


# ------------------------------------------- cinematica de la victoria falsa

PALABRAS_GLITCH = (
    "NEW BOSS READY", "WARNING", "ERROR", "SYSTEM OVERRIDE", "BOSS.EXE", "NO ESCAPE",
    "HACKED", "CRITICAL ERROR", "LOADING BONUS...", "NYAN.EXE", "GAME_END NOT FOUND",
    "RUN", "¿VICTORIA?", "FATAL", "BREACH", "0xDEADBEEF", "MEOW", "RESTART?",
    "INSERT COIN", "UNKNOWN ENTITY", "DANGER", "LEVEL ???", "PLAYER 2 HAS JOINED",
    "CORRUPTED", "NO ES EL FINAL", "BONUS STAGE", "SIGUIENTE JEFE", "404",
)
_COLORES_GLITCH = ((255, 60, 90), (60, 255, 240), (255, 70, 255), (255, 240, 80), (120, 255, 120), WHITE)


class CinematicaVictoriaFalsa:
    """La VICTORIA falsa despues del mega-jefe, como cinematica:

      NORMAL (DURACION_NORMAL): la pantalla de victoria de siempre, quieta,
        mientras suena el techno (musica_victoria_tecno).
      GLITCH (DURACION_GLITCH, lo mismo que dura musica_glitch_epica): la
        musica se vuelve epica y la pantalla se rompe: franjas corridas,
        bloques de color, pixelado creciente y cada vez mas palabras
        ("NEW BOSS READY", "WARNING", "BOSS.EXE"...) con los canales de
        color separados; al final "NEW BOSS READY" gigante y destello.

    captura: la pantalla de victoria ya dibujada (mundo + textos).
    eventos: "epica" al empezar el glitch y "chispazo" de vez en cuando
    (sonidos, ver main.py); temblor: pixeles de sacudida del cuadro."""

    DURACION_NORMAL = 360
    DURACION_GLITCH = 300
    # palabras, colores y paneles del glitch (la ruta de Halloween los
    # cambia a mitad de camino, ver halloween.CinematicaVictoriaHalloween)
    PALABRAS = PALABRAS_GLITCH
    COLORES = _COLORES_GLITCH
    COLORES_PANEL = (neon.MAGENTA, neon.CIAN, neon.ROJO)
    TITULO_COLOR = WHITE

    def __init__(self, captura):
        self.captura = captura
        self.t = 0
        self.palabras = []
        self.eventos = []
        self.temblor = 0

    @property
    def terminada(self):
        return self.t >= self.DURACION_NORMAL + self.DURACION_GLITCH

    def saltar(self):
        """Enter en la parte normal: pasa directo al glitch."""
        if self.t < self.DURACION_NORMAL:
            self.t = self.DURACION_NORMAL - 1

    def _progreso(self):
        return max(0.0, min(1.0, (self.t - self.DURACION_NORMAL) / self.DURACION_GLITCH))

    def update(self):
        self.t += 1
        if self.t == self.DURACION_NORMAL:
            self.eventos.append("epica")
        if self.t < self.DURACION_NORMAL:
            return
        p = self._progreso()
        self.temblor = int(2 + 10 * p) if random.random() < 0.3 + 0.5 * p else 0
        if random.random() < 0.02 + 0.05 * p:
            self.eventos.append("chispazo")

        # cada vez mas palabras por cuadro
        tasa = 0.15 + 2.2 * p
        nuevas = int(tasa) + (1 if random.random() < tasa - int(tasa) else 0)
        for _ in range(nuevas):
            self.palabras.append({
                'texto': random.choice(self.PALABRAS),
                'x': random.uniform(0, GAME_WIDTH), 'y': random.uniform(0, GAME_HEIGHT),
                'tam': random.choice((16, 20, 26, 34, 44)) + int(20 * p * random.random()),
                'color': random.choice(self.COLORES),
                'vida': random.randint(12, 40), 'vida_max': 40,
            })
        for w in self.palabras:
            w['vida'] -= 1
        self.palabras = [w for w in self.palabras if w['vida'] > 0]

    def _dibujar_extra(self, surface, p):
        """Encima del glitch, antes de las scanlines (lo usa la ruta de
        Halloween para el brazo)."""

    def _texto_glitch(self, surface, texto, tam, color, cx, cy, separacion):
        fuente = get_font(tam, bold=True)
        for dx, c in ((-separacion, (255, 0, 60)), (separacion, (0, 240, 255)), (0, color)):
            s = fuente.render(texto, True, c)
            surface.blit(s, (int(cx) - s.get_width() // 2 + dx, int(cy) - s.get_height() // 2))

    def draw(self, surface):
        surface.blit(self.captura, (0, 0))
        if self.t < self.DURACION_NORMAL:
            return
        p = self._progreso()

        # la pantalla se rompe y se va pixelando hacia el mundo del bonus
        roto = aplicar_glitch(surface, 0.25 + 0.75 * p)
        roto = pixelar(roto, 1 + int(p * (PIXEL_BONUS * 2 - 1)))
        surface.blit(roto, (0, 0))
        if random.random() < 0.15 + 0.3 * p:
            # un cuadro con los colores invertidos de vez en cuando (blanco - imagen)
            surface.fill((255, 255, 255))
            surface.blit(roto, (0, 0), special_flags=pygame.BLEND_RGB_SUB)

        for w in self.palabras:
            if w['vida'] % 5 == 0:
                continue  # parpadeo
            self._texto_glitch(surface, w['texto'], w['tam'], w['color'],
                               w['x'] + random.randint(-3, 3), w['y'] + random.randint(-2, 2), 2 + w['tam'] // 12)

        # "NEW BOSS READY" gigante: aparece a saltos y al final se queda
        if (p > 0.4 and (self.t // 5) % 3 == 0) or p > 0.82:
            caja = pygame.Rect(0, 0, 760, 120)
            caja.center = (GAME_WIDTH // 2 + random.randint(-4, 4), GAME_HEIGHT // 2)
            neon.panel(surface, caja, random.choice(self.COLORES_PANEL), self.t, halo=False)
            self._texto_glitch(surface, "NEW BOSS READY", 72, self.TITULO_COLOR,
                               GAME_WIDTH // 2 + random.randint(-6, 6), GAME_HEIGHT // 2 + random.randint(-4, 4),
                               4 + int(8 * p))
        self._dibujar_extra(surface, p)

        neon.scanlines(surface, 60 if p > 0 else 40)
        restante = self.DURACION_NORMAL + self.DURACION_GLITCH - self.t
        if restante < 18:
            destello = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            destello.fill((255, 255, 255, int(255 * (1 - restante / 18))))
            surface.blit(destello, (0, 0))
