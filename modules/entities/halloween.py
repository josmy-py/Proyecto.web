"""
Ruta secreta de Halloween del jefe bonus. Al caer el mega-jefe, la
cinematica de la VICTORIA falsa a veces se tuerce (ver
_cinematica_victoria_falsa en main.py): un brazo de zombi rompe la pantalla
desde abajo, el glitch se vuelve naranja/violeta y en vez de Nyan Cat
llegan tres jefes de Halloween, uno tras otro:

  1. REY CALABAZA: calabaza gigante con corona; salta, tira semillas y
     calabazas bomba que estallan al caer.
  2. BRUJA NEON: vuela en su escoba; murcielagos que te persiguen, pociones
     que dejan charcos toxicos y clones del aquelarre. A mitad de la vida
     se toma una pocion y pelea gigante, con pociones y circulos magicos.
  3. LA PARCA: se teletransporta, dispara calaveras y almas y barre una
     fila entera con su guadaña (avisada antes).

Al caer la Parca, CinematicaFinHalloween y la victoria de verdad. Mismo
estilo que nyan_boss.py: arte pixel dibujado por codigo a resolucion de
"pixel de arte", agrandado sin filtrado, y la misma interfaz de jefe
(JefeGatoBase), asi main.py los trata igual que a los gatos."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.systems import neon, pixelfx
from modules.systems.fonts import get_font
from modules.entities.nyan_boss import (
    PIXEL_BONUS, BalaPixel, JefeGatoBase, CinematicaVictoriaFalsa,
    _anillo, _apuntada, _blit_centrado, _lanzar_en_arco, _px, pixelar,
)


NEGRO = (0, 0, 0)
CONTORNO = (20, 8, 24)
NARANJA = (255, 128, 24)
NARANJA_OSCURO = (196, 72, 14)
NARANJA_CLARO = (255, 184, 70)
LUZ_CARA = (255, 236, 110)
LUZ_FURIA = (255, 70, 40)
TALLO = (70, 140, 50)
TALLO_OSCURO = (36, 84, 32)
ORO = (255, 206, 60)
ORO_OSCURO = (176, 120, 20)
VIOLETA = (150, 60, 220)
VIOLETA_OSCURO = (78, 26, 128)
VIOLETA_CLARO = (205, 130, 255)
VERDE_BRUJA = (120, 220, 90)
VERDE_BRUJA_OSCURO = (60, 140, 60)
VERDE_TOXICO = (150, 255, 60)
PELO = (40, 20, 60)
MADERA = (130, 80, 40)
MADERA_OSCURA = (82, 46, 22)
PAJA = (230, 190, 90)
HUESO = (236, 230, 210)
HUESO_SOMBRA = (160, 150, 140)
OJO_PARCA = (255, 40, 70)
ACERO_OSCURO = (80, 92, 116)
HUMO_PARCA = (110, 40, 36)
# la Parca: tunica rojiza, mango de madera retorcida, cadenas y reloj de arena
TUNICA_PARCA = (90, 34, 28)
TUNICA_PARCA_LUZ = (138, 62, 44)
TUNICA_PARCA_SOMBRA = (42, 16, 18)
MADERA_PARCA = (70, 44, 30)
MADERA_PARCA_LUZ = (112, 74, 48)
CADENA = (96, 96, 108)
CADENA_LUZ = (168, 168, 182)
VIDRIO_PARCA = (150, 170, 190)
ARENA = (240, 190, 90)
FILO = (200, 230, 255)
ACERO = (140, 160, 185)
PIEL_ZOMBI = (124, 176, 96)
PIEL_ZOMBI_LUZ = (168, 214, 128)
PIEL_ZOMBI_OSCURA = (70, 116, 62)
HERIDA = (170, 20, 40)
FONDO_NOCHE = ((18, 8, 34), (26, 10, 46), (36, 14, 58), (48, 18, 68))

PALABRAS_HALLOWEEN = (
    "DULCE O TRUCO", "BOO!", "HALLOWEEN.EXE", "NO ESCAPE", "MUAHAHA", "R.I.P.",
    "NOCHE DE BRUJAS", "TRICK OR TREAT", "PUMPKIN.EXE", "THE END?", "GHOST IN THE MACHINE",
    "TE ENCONTRE", "NEW BOSS READY", "CORRUPTED", "SCREAM", "NO ES EL FINAL", "13", "UNDEAD",
)
COLORES_HALLOWEEN = (NARANJA, VIOLETA_CLARO, VERDE_TOXICO, (255, 60, 60), LUZ_CARA, WHITE)


# ------------------------------------------------------------------ arte

def _contornear(forma, color_contorno, tam):
    """Silueta de `forma` corrida un pixel a cada lado (contorno grueso)."""
    s = pygame.Surface(tam, pygame.SRCALPHA)
    silueta = pygame.mask.from_surface(forma).to_surface(setcolor=(*color_contorno, 255), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        s.blit(silueta, (dx, dy))
    s.blit(forma, (0, 0))
    return s


def _arte_calabaza(cuadro):
    """Rey Calabaza (34x34): calabaza de gajos con corona dorada y cara
    tallada que titila. cuadro: 0/1 brillo de la cara, 2 = furioso (rojo),
    3 = boca abierta (escupe)."""
    s = pygame.Surface((34, 34), pygame.SRCALPHA)
    # gajos: cinco elipses que se superponen
    for x, w in ((2, 14), (18, 14), (6, 12), (16, 12), (11, 12)):
        pygame.draw.ellipse(s, NARANJA, (x, 9, w, 23))
    for x in (8, 15, 22):
        _px(s, NARANJA_OSCURO, x, 12, 1, 17)
    pygame.draw.ellipse(s, NARANJA_CLARO, (5, 12, 4, 8))
    _px(s, NARANJA_OSCURO, 4, 26, 26, 3)
    # tallo y corona
    _px(s, TALLO_OSCURO, 16, 6, 3, 4)
    _px(s, TALLO, 16, 6, 2, 3)
    _px(s, ORO, 9, 4, 16, 3)
    for cx in (9, 15, 21):
        _px(s, ORO, cx, 0, 4, 4)
        _px(s, ORO_OSCURO, cx + 1, 2, 2, 2)
    _px(s, (255, 60, 90), 16, 4, 2, 2)
    _px(s, (90, 200, 255), 11, 4, 2, 2)
    _px(s, (90, 200, 255), 21, 4, 2, 2)
    _px(s, ORO_OSCURO, 9, 6, 16, 1)
    # cara tallada
    luz = LUZ_FURIA if cuadro == 2 else LUZ_CARA if cuadro != 1 else NARANJA_CLARO
    for ox in (8, 20):
        pygame.draw.polygon(s, CONTORNO, ((ox, 19), (ox + 6, 19), (ox + 3, 14)))
        pygame.draw.polygon(s, luz, ((ox + 1, 18), (ox + 5, 18), (ox + 3, 15)))
    _px(s, CONTORNO, 16, 20, 2, 2)
    boca_alto = 6 if cuadro == 3 else 4
    _px(s, CONTORNO, 8, 23, 18, boca_alto)
    _px(s, luz, 9, 24, 16, boca_alto - 2)
    for dx in (11, 16, 21):
        _px(s, NARANJA, dx, 24, 2, 1)
        _px(s, NARANJA, dx - 2, 23 + boca_alto - 2, 2, 1)
    return _contornear(s, CONTORNO, (34, 34))


# Bruja Neon: mujer adulta de anime (pelo violeta largo, ojos violeta,
# labios rojos, aro de oro, vestido de cuello alto con ribete neon y medias
# negras) sentada de costado en su escoba, mirando a la derecha.
_PALETA_BRUJA = {
    # sombrero azul noche, pelo largo gris azulado, piel palida, ojos
    # blancos que brillan, vestido azul marino y constelaciones celestes
    'K': CONTORNO, 'H': (26, 32, 74), 'h': (62, 80, 140), 'B': (40, 50, 104), 'G': (170, 236, 255),
    'P': (84, 106, 146), 'p': (50, 64, 100), 'L': (146, 172, 212),
    'S': (238, 232, 242), 's': (196, 190, 216), 'W': WHITE, 'E': (228, 250, 255), 'e': (120, 210, 255),
    'R': (186, 64, 96), 'O': (150, 220, 255), 'D': (24, 28, 60), 'd': (56, 64, 112), 'b': (226, 180, 200),
    'M': MADERA, 'm': MADERA_OSCURA, 'Y': PAJA, 'y': (190, 140, 60), 'N': (24, 24, 46), 'n': (66, 70, 110),
}
_ARTE_BRUJA = (
    "..............KKK...........................",
    ".............KHHK...........................",
    "..............KHHK..........................",
    "...............KHHK.........................",
    "...............KHHHK........................",
    "..............KHHHHHK.......................",
    "..............KHhHHHHK......................",
    ".............KHHhHHHHHK.....................",
    ".............KHHHhHHHHHK....................",
    "............KBBBBBBBGBBBBK..................",
    "............KHHHHHHHHHHHHHK.................",
    ".......KKKKKHHHHHHHHHHHHHHHKKKKKK...........",
    "......KhhhhHHHHHHHHHhhHHHHHHHHHHHK..........",
    ".......KKKKPPPPPPPPPPPPPPPPKKKKKK...........",
    ".........KPPPLPPPPPPPPPPPPPPPK..............",
    "........KPPPLPPPPPPPPPPPPPPPSPK.............",
    "........KPPLPPPPPPPPPPPPPPPSSSPK............",
    ".......KPPLPPPPPPPPPPPPPPPKKKSSSK...........",
    ".......KPPPPPPPPPPPPPPPPPKWEEKSSK...........",
    ".......KPPPPPPPPPPPPPPPPPSWEeKSSSK..........",
    "......KPPPPpPPPPPPPPPPPPPSSSSbbSSK..........",
    "......KPPPPpPPPPPPPPPPPOPsSSSSSSSK..........",
    "......KPPPPPpPPPPPPPPPPPPsSSSSRRK...........",
    ".....KPPPPPPpPPPPPPPPPPPPPsSSSSK............",
    ".....KPPPPPPPpPPPPPPPPPPPPKsSSK.............",
    ".....KPPPPPPPpPPPPPPPPPKKKDGGGK.............",
    "....KPPPPPPPPPpPPPPPPKDDDDGDDDDK............",
    "....KPPPPPPPPPpPPPPPKDDdDDDDDDDDK...........",
    "....KPPPPPPPPPPpPPPKDDdDDDDDDDDDDK..........",
    "...KPPPPPPPPPPPpPPKDDdDDDDDdddddddKK........",
    "...KPPPPPPPPPPPPpPKDDdDDDDDDDDDDDDdSSK......",
    "...KPPPPPPPPPPPPpPKDDdDDDDKKKKKKKKKKSSK.....",
    "YyYKPPPPPPPPPPPPpPKDDGGGGGGDDDK....KSSK.....",
    "KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKMSSMKKKK.",
    "YYyYYYYKMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMK",
    "YyYYyYYKmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmK",
    "yYYyYYYKKKKKKKKKKDDdDDDDDDDDDDKKKKKKKKKKKKK.",
    "yYYyKPPPPPPPPPKDDdDDDDDDDDDDDDDK............",
    "...KPPPPPPPPPKDDdDDDDDDDDDDDDDDDDK..........",
    "....KPPPPPPPKDDdDDDDDDDDDDDGDDDDDDK.........",
    ".....KPPPPPKDDDDDDDDDDDDDGGGKNNNK...........",
    "......KPPPKGGGGGGGGGGGGGGGKKNnNNK...........",
    ".......KKK...............K.KNnNK............",
    "...........................KNnNK............",
    "...........................KNnNNK...........",
    "...........................KNNNNNNK.........",
    "............................KKKKKKK.........",
)


def _desde_texto(filas, paleta):
    s = pygame.Surface((len(filas[0]), len(filas)), pygame.SRCALPHA)
    for y, fila in enumerate(filas):
        for x, c in enumerate(fila):
            color = paleta.get(c)
            if color is not None:
                s.set_at((x, y), color)
    return s


def _arte_bruja(cuadro):
    """Bruja Neon (44x47). cuadro 0/1: la paja de la escoba y las puntas
    del pelo se mueven con el viento."""
    filas = list(_ARTE_BRUJA)
    if cuadro:
        for y in range(32, 38):
            filas[y] = filas[y][1:7] + filas[y][0] + filas[y][7:]
        for y in range(36, 42):
            fila = filas[y]
            k = fila.find("K")
            if k > 0:
                filas[y] = fila[1:k + 1] + fila[k] + fila[k + 1:]
    return _desde_texto(filas, _PALETA_BRUJA)


def _arte_bruja_gigante(cuadro):
    """La Bruja Neon gigante de frente, de la cintura para arriba (120x92),
    estilo anime: sombrero enorme con cinta y hebilla de estrella, pelo
    largo gris azulado con reflejos, ojos grandes blancos que brillan con
    pestañas largas, rubor, labios rosados, gargantilla con gema, vestido
    azul marino de escote corazon con ribete plateado y cordones, mangas
    transparentes y constelaciones en los hombros. La mano izquierda queda
    abierta para los circulos magicos y la derecha levantada para las
    pociones (las dos se dibujan en el arte: ya no atacan con los brazos).
    cuadro: 0 normal, 1 parpadeo, 2 risa (ojos cerrados), 3 furia (los
    ojos y las constelaciones brillan mas)."""
    pal = _PALETA_BRUJA
    sf = pygame.Surface((120, 92), pygame.SRCALPHA)
    S, s, P, p, L = pal['S'], pal['s'], pal['P'], pal['p'], pal['L']
    D, d, H, h = pal['D'], pal['d'], pal['H'], pal['h']
    brillo = (240, 252, 255) if cuadro == 3 else pal['G']
    PLATA = (190, 200, 228)
    RUBOR = (240, 150, 182)
    LABIO = (226, 96, 130)
    UNA = (120, 90, 230)
    PELO_OSCURO = (36, 46, 76)

    # ---- pelo de atras: cae largo y ondulado hasta abajo
    pygame.draw.polygon(sf, p, [(44, 26), (38, 38), (35, 52), (30, 66), (24, 80), (20, 92), (100, 92), (96, 80),
                                (90, 66), (85, 52), (82, 38), (76, 26)])
    # mechones: lineas que se abren hacia abajo, con brillo y sombra
    for i, x0 in enumerate(range(37, 84, 3)):
        abre = (x0 - 60) / 23
        x1 = 60 + abre * 40
        c = (L, P, PELO_OSCURO, P)[i % 4]
        pygame.draw.lines(sf, c, False, ((x0, 30), (x0 + abre * 6, 52), (x1 + math.sin(i) * 2, 90)))
    # brillo de anillo sobre la cabeza (el reflejo tipico del pelo de anime)
    for x in range(44, 78, 4):
        _px(sf, L, x, 27, 2, 1)
    # ondas en las puntas
    for y in range(70, 92, 4):
        _px(sf, PELO_OSCURO, 20 + (y - 70) // 6, y, 2, 1)
        _px(sf, PELO_OSCURO, 98 - (y - 70) // 6, y, 2, 1)

    # ---- brazos (detras del cuerpo): el izquierdo levantado con la palma
    # abierta para los circulos magicos, el derecho sostiene la pocion
    for (hx, hy), (cx, cy), (mx, my) in (((40, 74), (24, 82), (14, 64)), ((80, 74), (96, 82), (106, 62))):
        lado = -1 if cx < 60 else 1
        pygame.draw.line(sf, S, (hx, hy), (cx, cy), 7)
        pygame.draw.circle(sf, S, (cx, cy), 3)
        pygame.draw.line(sf, S, (cx, cy), (mx, my), 5)
        pygame.draw.line(sf, s, (cx + lado * 2, cy + 1), (mx + lado * 2, my + 1))
        _px(sf, PLATA, mx + (cx - mx) // 4 - 2, my + (cy - my) // 4 - 1, 5, 2)   # pulsera
        # manga transparente acampanada que cae desde el hombro
        manga = [(hx - lado * 2, hy - 4), (cx + lado * 2, cy - 5), (cx + lado * 9, cy + 6),
                 (cx + lado * 4, cy + 10), (hx, hy + 8)]
        pygame.draw.polygon(sf, (205, 218, 250, 55), manga)
        pygame.draw.lines(sf, (230, 238, 255, 200), False, manga[1:4])
        for k in (0.35, 0.7):
            px = manga[0][0] + (manga[2][0] - manga[0][0]) * k
            py = manga[0][1] + (manga[2][1] - manga[0][1]) * k
            _px(sf, (225, 232, 250, 150), px, py)
    # mano izquierda abierta (palma hacia afuera, dedos finos y uñas violeta)
    pygame.draw.ellipse(sf, S, (9, 57, 9, 9))
    for fx, fy in ((8, 51), (11, 49), (14, 49), (17, 51)):
        pygame.draw.line(sf, S, (fx + 1, fy + 7), (fx, fy), 2)
        _px(sf, UNA, fx, fy, 2, 1)
    pygame.draw.line(sf, S, (18, 62), (21, 58), 2)   # pulgar
    _px(sf, s, 11, 63, 6, 1)
    # mano derecha levantada, curva para sostener la pocion
    pygame.draw.ellipse(sf, S, (102, 55, 9, 10))
    for k in range(3):
        _px(sf, s, 103 + k * 3, 56, 1, 3)
    _px(sf, UNA, 102, 58, 1, 2)
    _px(sf, UNA, 110, 58, 1, 2)

    # ---- hombros, cuello y pecho
    pygame.draw.polygon(sf, S, [(30, 92), (32, 80), (40, 70), (52, 66), (68, 66), (80, 70), (88, 80), (90, 92)])
    pygame.draw.polygon(sf, s, [(30, 92), (32, 80), (40, 70), (44, 69), (36, 80), (34, 92)])
    pygame.draw.polygon(sf, s, [(90, 92), (88, 80), (80, 70), (76, 69), (84, 80), (86, 92)])
    _px(sf, S, 55, 54, 10, 14)
    _px(sf, s, 55, 56, 10, 3)                  # sombra del menton
    pygame.draw.line(sf, s, (45, 72), (56, 74))   # claviculas
    pygame.draw.line(sf, s, (64, 74), (75, 72))
    # gargantilla con gema
    _px(sf, CONTORNO, 55, 61, 10, 2)
    _px(sf, PLATA, 55, 61, 10, 1)
    _px(sf, PLATA, 60, 63, 1, 1)
    pygame.draw.polygon(sf, brillo, ((60, 64), (62, 66), (60, 68), (58, 66)))   # gema en rombo
    _px(sf, WHITE, 60, 65, 1, 1)
    # vestido: escote corazon, ribete plateado, cordones cruzados
    pygame.draw.polygon(sf, D, [(34, 92), (35, 80), (46, 76), (54, 78), (60, 82), (66, 78), (74, 76), (85, 80),
                                (86, 92)])
    pygame.draw.lines(sf, PLATA, False, ((35, 80), (46, 76), (54, 78), (60, 82), (66, 78), (74, 76), (85, 80)))
    pygame.draw.lines(sf, d, False, ((38, 84), (46, 80), (53, 82)))
    pygame.draw.lines(sf, d, False, ((67, 82), (74, 80), (82, 84)))
    # moño en el escote con un broche de cristal
    pygame.draw.polygon(sf, pal['B'], ((60, 83), (55, 80), (55, 86)))
    pygame.draw.polygon(sf, pal['B'], ((60, 83), (65, 80), (65, 86)))
    _px(sf, brillo, 59, 82, 2, 2)
    _px(sf, WHITE, 59, 82, 1, 1)
    for x0, x1 in ((40, 44), (76, 80)):
        pygame.draw.line(sf, d, (x0, 84), (x1 - 2, 92))
    for y in range(87, 92, 3):
        pygame.draw.line(sf, PLATA, (57, y), (63, y + 2))
        pygame.draw.line(sf, PLATA, (63, y), (57, y + 2))
    # constelaciones que brillan sobre los hombros
    for linea in (((34, 82), (38, 76), (44, 77), (47, 72)), ((73, 72), (76, 77), (82, 76), (86, 82))):
        pygame.draw.lines(sf, brillo, False, linea)
        for x, y in linea:
            _px(sf, WHITE, x, y)

    # ---- mechones delanteros que enmarcan la cara y caen sobre los hombros
    for x0, inclina in ((38, -1), (76, 1)):
        pygame.draw.polygon(sf, P, [(x0, 28), (x0 + 6, 28), (x0 + 5 + inclina * 3, 60), (x0 + 3 + inclina * 6, 80),
                                    (x0 + inclina * 4, 70), (x0 + 1 + inclina, 50)])
        pygame.draw.line(sf, L, (x0 + 3, 32), (x0 + 3 + inclina * 3, 64))
        pygame.draw.line(sf, PELO_OSCURO, (x0 + 1, 40), (x0 + 1 + inclina * 2, 62))

    # ---- cara: ovalada con menton fino
    pygame.draw.ellipse(sf, S, (43, 26, 34, 30))
    pygame.draw.polygon(sf, S, [(44, 44), (76, 44), (66, 57), (60, 59), (54, 57)])
    _px(sf, s, 44, 44, 1, 6)
    _px(sf, s, 75, 44, 1, 6)
    pygame.draw.line(sf, s, (46, 50), (54, 57))
    pygame.draw.line(sf, s, (74, 50), (66, 57))

    # ojos grandes de anime: almendrados, blancos que brillan, pestañas largas
    for ex, afuera in ((47, -1), (64, 1)):
        ox = ex if afuera < 0 else ex + 8    # rabillo del ojo (lado de afuera)
        ix = ex + 8 if afuera < 0 else ex    # lagrimal (lado de adentro)
        if cuadro == 1:
            pygame.draw.lines(sf, CONTORNO, False, ((ex, 44), (ex + 4, 45), (ex + 8, 44)), 2)
            _px(sf, CONTORNO, ox + afuera, 43, 1, 1)
        elif cuadro == 2:
            # ojos cerrados de felicidad (arco hacia arriba)
            pygame.draw.lines(sf, CONTORNO, False, ((ex, 45), (ex + 2, 42), (ex + 6, 42), (ex + 8, 45)), 2)
            _px(sf, CONTORNO, ox + afuera, 43, 1, 1)
        else:
            # forma almendrada: el blanco del ojo con las esquinas recortadas
            pygame.draw.polygon(sf, pal['e'], ((ex, 41), (ex + 8, 41), (ex + 8, 45), (ex + 6, 47), (ex + 2, 47), (ex, 45)))
            # iris: degradado de celeste oscuro arriba a blanco abajo
            _px(sf, (100, 180, 240), ex + 2, 40, 5, 2)
            _px(sf, (170, 228, 255), ex + 2, 42, 5, 2)
            _px(sf, pal['E'], ex + 2, 44, 5, 2)
            _px(sf, WHITE, ex + 3, 45, 3, 1)
            _px(sf, (90, 160, 230), ex + 3, 42, 3, 2)           # pupila
            # reflejos grandes de anime
            _px(sf, WHITE, ex + 2 + (1 if afuera > 0 else 0), 41, 2, 2)
            _px(sf, WHITE, ex + 5 - (1 if afuera > 0 else 0), 44, 1, 1)
            # pestaña de arriba: arco grueso con dos puntas hacia afuera
            pygame.draw.lines(sf, CONTORNO, False, ((ix, 41), (ex + 4, 39), (ox, 40)), 2)
            pygame.draw.line(sf, CONTORNO, (ox, 40), (ox + afuera * 3, 37))
            pygame.draw.line(sf, CONTORNO, (ox, 41), (ox + afuera * 3, 40))
            _px(sf, CONTORNO, ox + afuera, 46, 1, 1)
            pygame.draw.line(sf, s, (ex + 1, 48), (ex + 7, 48))   # parpado de abajo
            if cuadro == 3:
                _px(sf, WHITE, ex + 1, 42, 7, 3)
                _px(sf, brillo, ox + afuera * 2, 42, 1, 3)        # el brillo se escapa
                _px(sf, brillo, ox + afuera * 3, 44, 1, 1)
        # cejas finas y arqueadas
        pygame.draw.lines(sf, PELO_OSCURO, False, ((ix, 36), (ex + 4, 35), (ox + afuera, 36)))
        # rubor
        for k in range(3):
            _px(sf, RUBOR, ex + 1 + k * 2, 50, 1, 1)
            _px(sf, RUBOR, ex + 2 + k * 2, 51, 1, 1)
    # nariz y boca
    _px(sf, s, 60, 50, 1, 2)
    _px(sf, (255, 250, 252), 59, 49, 1, 1)
    if cuadro == 2:
        pygame.draw.polygon(sf, (150, 30, 70), ((56, 53), (64, 53), (62, 56), (58, 56)))
        _px(sf, WHITE, 57, 53, 6, 1)
        _px(sf, (255, 120, 150), 59, 55, 3, 1)
    else:
        # sonrisa suave con labios rosados
        _px(sf, (180, 70, 100), 58, 54, 5, 1)
        _px(sf, (180, 70, 100), 57, 53, 1, 1)
        _px(sf, (180, 70, 100), 63, 53, 1, 1)
        _px(sf, LABIO, 59, 55, 3, 1)
        _px(sf, (255, 196, 214), 60, 55, 1, 1)

    # flequillo en puntas, con un mechon fino entre los ojos
    pygame.draw.polygon(sf, P, [(42, 26), (78, 26), (78, 36), (75, 40), (72, 33), (68, 38), (64, 31), (61, 37),
                                (58, 31), (54, 38), (50, 32), (46, 40), (42, 36)])
    for x0, x1 in ((48, 46), (56, 54), (66, 68), (73, 75)):
        pygame.draw.line(sf, L, (x0, 27), (x1, 33))
    pygame.draw.line(sf, P, (60, 32), (61, 46))
    pygame.draw.line(sf, L, (61, 33), (61, 41))
    # aros de cristal
    for x in (42, 77):
        _px(sf, pal['O'], x, 50, 1, 4)
        _px(sf, WHITE, x, 53, 1, 1)

    # ---- sombrero: ala enorme que cae a los costados, punta doblada
    pygame.draw.polygon(sf, H, [(2, 30), (10, 25), (26, 21), (46, 19), (74, 19), (94, 21), (110, 25), (118, 30),
                                (112, 31), (96, 27), (78, 25), (60, 25), (42, 25), (24, 27), (8, 31)])
    pygame.draw.line(sf, h, (10, 26), (40, 20))
    pygame.draw.line(sf, h, (80, 20), (110, 26))
    for x, y in ((5, 30), (16, 28), (102, 28), (114, 30)):
        _px(sf, (0, 0, 0, 0), x, y, 2, 1)   # ala rasgada
    pygame.draw.polygon(sf, H, [(42, 21), (78, 21), (73, 12), (70, 6), (78, 2), (90, 0), (80, 0), (66, 2), (54, 8)])
    pygame.draw.line(sf, h, (56, 9), (52, 19))
    pygame.draw.line(sf, h, (68, 4), (80, 1))
    pygame.draw.line(sf, (16, 20, 50), (70, 7), (73, 18))
    # cinta con hebilla de estrella y moño de costado
    _px(sf, pal['B'], 43, 17, 34, 4)
    _px(sf, brillo, 43, 17, 34, 1)
    pygame.draw.polygon(sf, (255, 214, 110), ((60, 16), (61, 18), (63, 18), (61.5, 19.5), (62, 21), (60, 20),
                                               (58, 21), (58.5, 19.5), (57, 18), (59, 18)))
    pygame.draw.polygon(sf, pal['B'], ((77, 18), (84, 14), (84, 22)))
    pygame.draw.polygon(sf, pal['B'], ((77, 19), (82, 24), (79, 26)))
    _px(sf, brillo, 82, 15, 1, 6)
    # dijes de cristal que cuelgan del ala
    for x, y in ((14, 28), (106, 28)):
        _px(sf, PLATA, x, y, 1, 3)
        _px(sf, pal['O'], x - 1, y + 3, 3, 2)
        _px(sf, WHITE, x, y + 3)
        _px(sf, pal['O'], x, y + 5)
    # estrellitas en el ala
    for x, y in ((30, 23), (88, 23), (20, 26)):
        _px(sf, brillo, x, y)
    return _contornear(sf, CONTORNO, (120, 92))


def _arte_parca(cuadro):
    """La Parca (46x58): alta, con tunica rojiza rasgada en jirones, la cara
    perdida en la sombra de la capucha (solo se ven dos ojos rojos),
    cadenas cruzadas sobre el pecho con una gema roja, guadaña de madera
    retorcida en una mano y un reloj de arena en la otra.
    cuadro 0/1: los jirones ondean y cae la arena; 2: ataca (ojos, gema y
    reloj encendidos)."""
    s = pygame.Surface((46, 58), pygame.SRCALPHA)
    ataca = cuadro == 2
    rojo = OJO_PARCA if ataca else (190, 24, 40)
    # guadaña: mango de madera retorcida con nudos (detras del cuerpo)
    for y in range(5, 58):
        x = 8 + round(math.sin(y * 0.35) * 0.8) - (y - 5) // 26
        _px(s, MADERA_PARCA, x, y, 2, 1)
        if y % 3 == 0:
            _px(s, MADERA_PARCA_LUZ, x, y, 1, 1)
    for y in (16, 31, 44):
        _px(s, MADERA_PARCA_LUZ, 7, y, 4, 2)    # nudos
    # hoja curva por encima de la capucha (el filo es la curva de abajo)
    pygame.draw.polygon(s, ACERO, ((8, 6), (12, 2), (20, 0), (29, 1), (36, 4), (40, 9),
                                   (35, 6), (28, 4), (20, 4), (13, 6), (10, 9)))
    pygame.draw.polygon(s, ACERO_OSCURO, ((12, 2), (20, 0), (29, 1), (36, 4), (28, 2), (20, 2)))
    pygame.draw.lines(s, FILO, False, ((10, 8), (13, 6), (20, 4), (28, 4), (35, 6), (39, 9)))
    _px(s, MADERA_PARCA, 6, 3, 5, 5)
    if ataca:
        _px(s, WHITE, 31, 4, 3, 1)
        _px(s, WHITE, 32, 3, 1, 3)
    # tunica larga que se abre hacia abajo
    pygame.draw.polygon(s, TUNICA_PARCA, ((18, 15), (30, 15), (35, 22), (37, 34), (40, 50), (8, 50), (11, 34), (13, 22)))
    pygame.draw.polygon(s, TUNICA_PARCA_SOMBRA, ((27, 17), (35, 22), (37, 34), (40, 50), (31, 50), (30, 34)))
    for x, y0 in ((15, 30), (20, 34), (26, 36), (33, 30)):
        _px(s, TUNICA_PARCA_LUZ, x, y0, 1, 50 - y0)   # pliegues
    # jirones largos del borde
    for i in range(9):
        x = 8 + i * 3.6
        largo = 3 + ((i * 5 + cuadro) % 4) * 2
        punta = x + 1.5 + (1 if (i + cuadro) % 2 else -1)
        pygame.draw.polygon(s, TUNICA_PARCA if i % 3 else TUNICA_PARCA_SOMBRA,
                            ((x, 49), (x + 3.6, 49), (punta, 49 + largo)))
    # cadenas: una cruza el pecho y otra cuelga de la cintura
    for k in range(14):
        cx, cy = 13 + k * 1.6, 20 + k * 1.3
        _px(s, CADENA_LUZ if k % 2 else CADENA, int(cx), int(cy), 2, 1)
    for k in range(16):
        cx = 12 + k * 1.5
        cy = 38 + math.sin(k * 0.4) * 2 + (k * k) * 0.02
        _px(s, CADENA_LUZ if k % 2 else CADENA, int(cx), int(cy), 2, 1)
    for k in range(4):   # el extremo que cuelga
        _px(s, CADENA if k % 2 else CADENA_LUZ, 32, 40 + k * 2, 1, 2)
    # gema roja con engarce de oro en el pecho
    pygame.draw.circle(s, (255, 40, 50, 110 if ataca else 60), (24, 24), 6)   # resplandor
    _px(s, ORO_OSCURO, 22, 22, 5, 5)
    _px(s, ORO, 24, 21, 1, 1)
    _px(s, rojo, 23, 23, 3, 3)
    _px(s, (255, 170, 170) if ataca else (255, 90, 100), 23, 23, 1, 1)
    # brazo izquierdo (de frente a la derecha del mango): manga y mano en el mango
    pygame.draw.polygon(s, TUNICA_PARCA, ((15, 18), (8, 22), (7, 27), (12, 28), (17, 24)))
    for k, x in enumerate((7, 9, 11)):
        _px(s, TUNICA_PARCA_SOMBRA, x, 28, 2, 3 + (k + cuadro) % 2 * 3)   # manga rasgada
    for y in (23, 25):   # dedos huesudos cerrados sobre el mango
        _px(s, HUESO, 7, y, 4, 1)
        _px(s, HUESO_SOMBRA, 7, y + 1, 4, 1)
    _px(s, HUESO, 11, 23, 1, 2)
    # brazo derecho: manga rasgada y la mano que sostiene el reloj de arena
    pygame.draw.polygon(s, TUNICA_PARCA, ((30, 17), (37, 21), (41, 27), (36, 29), (32, 24)))
    for k, x in enumerate((36, 38, 40)):
        _px(s, TUNICA_PARCA_SOMBRA, x, 29, 1, 4 + (k + cuadro) % 2 * 4)
    for x in (39, 41):   # dedos largos que cuelgan
        _px(s, HUESO, x, 26, 1, 4)
        _px(s, HUESO_SOMBRA, x, 30, 1, 1)
    _px(s, HUESO, 38, 26, 4, 1)
    # reloj de arena colgando de la mano
    _px(s, MADERA_PARCA, 40, 30, 1, 2)
    if ataca:
        pygame.draw.circle(s, (255, 140, 60, 90), (40, 38), 6)
    _px(s, ORO_OSCURO, 36, 32, 9, 1)
    _px(s, ORO_OSCURO, 36, 44, 9, 1)
    _px(s, MADERA_PARCA, 36, 33, 1, 11)
    _px(s, MADERA_PARCA, 44, 33, 1, 11)
    pygame.draw.polygon(s, VIDRIO_PARCA, ((37, 33), (43, 33), (41, 38), (43, 43), (37, 43), (39, 38)))
    _px(s, ARENA, 38, 34, 5, 2)          # arena de arriba
    _px(s, ARENA, 39, 36, 3, 1)
    pygame.draw.polygon(s, ARENA, ((37, 43), (43, 43), (40, 40)))   # monton de abajo
    _px(s, ARENA, 40, 37 + cuadro % 2, 1, 2)   # hilo de arena que cae
    # capucha alta en punta y la cara perdida en la sombra
    pygame.draw.polygon(s, TUNICA_PARCA, ((24, 2), (28, 6), (31, 12), (32, 19), (16, 19), (17, 12), (20, 6)))
    pygame.draw.polygon(s, TUNICA_PARCA_SOMBRA, ((26, 4), (31, 12), (32, 19), (28, 19), (29, 11)))
    _px(s, TUNICA_PARCA_LUZ, 19, 9, 1, 8)
    _px(s, TUNICA_PARCA_LUZ, 23, 3, 1, 3)
    pygame.draw.ellipse(s, NEGRO, (19, 8, 10, 12))
    _px(s, (30, 12, 14), 21, 16, 6, 3)   # apenas se adivina una mandibula
    _px(s, rojo, 21, 12, 2, 1)
    _px(s, rojo, 25, 12, 2, 1)
    if ataca:
        _px(s, (255, 180, 180), 21, 12, 1, 1)
        _px(s, (255, 180, 180), 26, 12, 1, 1)
        _px(s, (120, 10, 20), 20, 11, 8, 1)
    return _contornear(s, CONTORNO, (46, 58))


def _arte_mini_calabaza(cuadro):
    s = pygame.Surface((9, 9), pygame.SRCALPHA)
    pygame.draw.ellipse(s, NARANJA, (0, 2, 9, 7))
    _px(s, NARANJA_OSCURO, 4, 3, 1, 5)
    _px(s, TALLO, 4, 0, 2, 2)
    _px(s, LUZ_CARA if cuadro else NARANJA_CLARO, 2, 4, 1, 1)
    _px(s, LUZ_CARA if cuadro else NARANJA_CLARO, 6, 4, 1, 1)
    return _contornear(s, CONTORNO, (9, 9))


def _arte_murcielago(cuadro):
    s = pygame.Surface((13, 7), pygame.SRCALPHA)
    _px(s, PELO, 5, 2, 3, 4)
    _px(s, PELO, 5, 1, 1, 1)
    _px(s, PELO, 7, 1, 1, 1)
    _px(s, (255, 60, 90), 5, 3, 1, 1)
    _px(s, (255, 60, 90), 7, 3, 1, 1)
    if cuadro:
        for k in range(4):
            _px(s, VIOLETA_OSCURO, 4 - k, 1 + k // 2, 1, 2)
            _px(s, VIOLETA_OSCURO, 8 + k, 1 + k // 2, 1, 2)
    else:
        for k in range(4):
            _px(s, VIOLETA_OSCURO, 4 - k, 3 + k // 2, 1, 2)
            _px(s, VIOLETA_OSCURO, 8 + k, 3 + k // 2, 1, 2)
    return _contornear(s, CONTORNO, (13, 7))


def _arte_calavera(cuadro):
    s = pygame.Surface((9, 9), pygame.SRCALPHA)
    pygame.draw.ellipse(s, HUESO, (0, 0, 9, 7))
    _px(s, HUESO, 2, 6, 5, 2)
    _px(s, NEGRO, 1, 3, 3, 2)
    _px(s, NEGRO, 5, 3, 3, 2)
    if cuadro:
        _px(s, OJO_PARCA, 2, 3, 1, 1)
        _px(s, OJO_PARCA, 6, 3, 1, 1)
    _px(s, NEGRO, 4, 5, 1, 1)
    _px(s, HUESO_SOMBRA, 3, 7, 1, 1)
    _px(s, HUESO_SOMBRA, 5, 7, 1, 1)
    return _contornear(s, CONTORNO, (9, 9))


def _arte_alma(cuadro):
    s = pygame.Surface((8, 10), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (200, 240, 255), (0, 0, 8, 8))
    _px(s, (200, 240, 255), 0, 4, 8, 4)
    for i in range(3):
        _px(s, (200, 240, 255), i * 3 + (cuadro % 2), 8, 2, 2)
    _px(s, (40, 40, 90), 2, 3, 1, 2)
    _px(s, (40, 40, 90), 5, 3, 1, 2)
    return _contornear(s, (40, 60, 120), (8, 10))


def _arte_pocion(cuadro):
    s = pygame.Surface((7, 9), pygame.SRCALPHA)
    _px(s, MADERA, 2, 0, 3, 2)
    _px(s, (180, 210, 230), 2, 2, 3, 2)
    pygame.draw.ellipse(s, (180, 210, 230), (0, 3, 7, 6))
    pygame.draw.ellipse(s, VERDE_TOXICO, (1, 5, 5, 3))
    _px(s, WHITE, 1, 4, 1, 1)
    return _contornear(s, CONTORNO, (7, 9))


def _formas_brazo(s, color, cerrado):
    """Brazo de zombi apuntando hacia arriba (24x60): antebrazo, palma,
    cuatro dedos (abiertos o cerrados en puño) y el pulgar."""
    s.fill(color, (7, 22, 10, 40))                       # antebrazo
    pygame.draw.ellipse(s, color, (3, 11, 18, 15))       # palma
    for i, fx in enumerate((3, 8, 13, 17)):
        if cerrado:
            s.fill(color, (fx, 9, 4, 5))
        else:
            largo = (9, 11, 10, 8)[i]
            s.fill(color, (fx + int((i - 1.5) * 0.5), 12 - largo, 3, largo + 2))
    if cerrado:
        s.fill(color, (16, 14, 5, 4))
    else:
        s.fill(color, (19, 16, 3, 4))
        s.fill(color, (21, 12, 2, 5))


def _arte_brazo(cuadro):
    """Brazo de zombi verde con manga violeta rota. cuadro 0: mano abierta,
    1: puño cerrado (agarra la pantalla)."""
    cerrado = cuadro == 1
    forma = pygame.Surface((24, 60), pygame.SRCALPHA)
    _formas_brazo(forma, PIEL_ZOMBI, cerrado)
    s = _contornear(forma, CONTORNO, (24, 60))
    # sombra del lado derecho y luz del izquierdo
    for y in range(60):
        for x in range(24):
            if tuple(s.get_at((x, y)))[:3] != PIEL_ZOMBI:
                continue
            if x >= 14 and y > 20:
                s.set_at((x, y), PIEL_ZOMBI_OSCURA)
            elif x <= 8 and y > 22:
                s.set_at((x, y), PIEL_ZOMBI_LUZ)
    # uñas/huesos en las puntas de los dedos
    if not cerrado:
        for fx, largo in ((3, 9), (8, 11), (13, 10), (17, 8)):
            x = int(fx + 0.5)
            s.fill(HUESO, (x, 12 - largo + 1, 2, 2))
    else:
        for fx in (3, 8, 13, 17):
            s.fill(PIEL_ZOMBI_OSCURA, (fx, 13, 4, 1))
    # heridas y costuras
    s.fill(HERIDA, (10, 30, 3, 2))
    s.fill(HERIDA, (12, 31, 1, 2))
    for y in range(36, 42, 2):
        s.fill(CONTORNO, (8, y, 3, 1))
    # manga rota
    for x in range(6, 18):
        borde = 44 + (x * 7) % 5
        s.fill(VIOLETA_OSCURO, (x, borde, 1, 60 - borde))
        if x % 3 == 0:
            s.fill(VIOLETA, (x, borde, 1, 60 - borde))
    return s


def _arte_lapida(cuadro):
    s = pygame.Surface((14, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (70, 64, 96), (0, 0, 14, 10))
    s.fill((70, 64, 96), (0, 5, 14, 11))
    s.fill((46, 40, 70), (9, 2, 5, 14))
    s.fill((40, 34, 60), (4, 6, 6, 1))
    s.fill((40, 34, 60), (6, 4, 2, 6))
    return s


_ARTES = {
    "calabaza": _arte_calabaza, "bruja": _arte_bruja, "parca": _arte_parca,
    "bruja_gigante": _arte_bruja_gigante,
    "mini_calabaza": _arte_mini_calabaza, "murcielago": _arte_murcielago,
    "calavera": _arte_calavera, "alma": _arte_alma, "pocion": _arte_pocion,
    "brazo": _arte_brazo, "lapida": _arte_lapida,
}
_CACHE = {}


def sprite_halloween(nombre, cuadro, escala, voltear=False, blanco=False):
    """Como nyan_boss.sprite_pixel: arte agrandado sin filtrado (cacheado)."""
    clave = (nombre, cuadro, escala, voltear, blanco)
    surf = _CACHE.get(clave)
    if surf is None:
        arte = _ARTES[nombre](cuadro)
        surf = pygame.transform.scale(arte, (arte.get_width() * escala, arte.get_height() * escala))
        if voltear:
            surf = pygame.transform.flip(surf, True, False)
        if blanco:
            surf = surf.copy()
            surf.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
        _CACHE[clave] = surf
    return surf


# ------------------------------------------------------------- escenario

class FondoHalloween:
    """Noche de Halloween: cielo violeta en bandas, luna naranja, estrellas,
    lapidas en el horizonte y murcielagos que cruzan de vez en cuando.
    Misma interfaz que nyan_boss.FondoPixel (update/draw)."""

    def __init__(self):
        self.t = 0
        rng = random.Random(31)
        self.estrellas = [(rng.randrange(GAME_WIDTH), rng.randrange(int(GAME_HEIGHT * 0.7)), rng.randrange(60))
                          for _ in range(55)]
        self.lapidas = [(rng.randrange(20, GAME_WIDTH - 20), rng.choice((2, 3))) for _ in range(7)]
        self.hojas = [self._hoja(random.uniform(0, GAME_HEIGHT)) for _ in range(14)]
        self.murcielagos = []

    @staticmethod
    def _hoja(y):
        return {'x': random.uniform(0, GAME_WIDTH), 'y': y, 'v': random.uniform(0.8, 1.8),
                'fase': random.uniform(0, 6.3), 'color': random.choice((NARANJA, NARANJA_OSCURO, (190, 60, 40)))}

    def update(self):
        self.t += 1
        for i, h in enumerate(self.hojas):
            h['y'] += h['v']
            h['x'] += math.sin(self.t * 0.03 + h['fase']) * 0.8
            if h['y'] > GAME_HEIGHT + 10:
                self.hojas[i] = self._hoja(-10)
        if self.t % 260 == 0:
            lado = random.choice((-1, 1))
            self.murcielagos.append({'x': -30 if lado > 0 else GAME_WIDTH + 30, 'y': random.uniform(60, 220),
                                     'vx': lado * random.uniform(2.5, 3.5)})
        for m in self.murcielagos:
            m['x'] += m['vx']
        self.murcielagos = [m for m in self.murcielagos if -40 < m['x'] < GAME_WIDTH + 40]

    def draw(self, surface):
        for i, color in enumerate(FONDO_NOCHE):
            surface.fill(color, (0, i * GAME_HEIGHT // 4, GAME_WIDTH, GAME_HEIGHT // 4 + 1))
        p = PIXEL_BONUS
        for x, y, fase in self.estrellas:
            if ((self.t + fase) // 30) % 3:
                surface.fill((230, 210, 255), (x // p * p, y // p * p, p, p))
        # luna llena naranja con crateres
        lx, ly = GAME_WIDTH - 170, 110
        pygame.draw.circle(surface, (90, 40, 30), (lx, ly), 66)
        pygame.draw.circle(surface, (255, 190, 90), (lx, ly), 58)
        pygame.draw.circle(surface, (240, 160, 70), (lx - 18, ly - 10), 12)
        pygame.draw.circle(surface, (240, 160, 70), (lx + 20, ly + 18), 9)
        pygame.draw.circle(surface, (240, 160, 70), (lx + 6, ly - 28), 6)
        for m in self.murcielagos:
            spr = sprite_halloween("murcielago", (self.t // 6) % 2, 3)
            _blit_centrado(surface, spr, m['x'], m['y'] + math.sin(self.t * 0.2) * 6)
        # colinas y lapidas
        horizonte = GAME_HEIGHT - 70
        pygame.draw.ellipse(surface, (22, 10, 30), (-120, horizonte, GAME_WIDTH // 2 + 240, 160))
        pygame.draw.ellipse(surface, (22, 10, 30), (GAME_WIDTH // 2 - 120, horizonte + 14, GAME_WIDTH // 2 + 240, 160))
        for x, escala in self.lapidas:
            spr = sprite_halloween("lapida", 0, escala)
            surface.blit(spr, (x - spr.get_width() // 2, GAME_HEIGHT - 40 - spr.get_height()))
        for h in self.hojas:
            surface.fill(h['color'], (int(h['x']) // p * p, int(h['y']) // p * p, p * 2, p))


# ------------------------------------------------------------- proyectiles

class Murcielago(BalaPixel):
    """Murcielago que persigue un rato a la nave y despues sigue de largo."""

    def __init__(self, x, y, vx, vy, ship, persigue=70):
        super().__init__(x, y, vx, vy, forma="sprite", sprite=sprite_halloween("murcielago", 0, 3), radio=11)
        self.ship = ship
        self.persigue = persigue
        self.t = random.randrange(10)

    def update(self):
        self.t += 1
        if self.persigue > 0:
            self.persigue -= 1
            a = math.atan2(self.ship.y - self.y, self.ship.x - self.x)
            v = math.hypot(self.vx, self.vy)
            actual = math.atan2(self.vy, self.vx)
            dif = (a - actual + math.pi) % (2 * math.pi) - math.pi
            actual += max(-0.05, min(0.05, dif))
            self.vx, self.vy = math.cos(actual) * v, math.sin(actual) * v
        self.sprite = sprite_halloween("murcielago", (self.t // 5) % 2, 3)
        super().update()


def _semillas_en_abanico(x, y, ship, n, abertura, velocidad, color=LUZ_CARA):
    base = math.atan2(ship.y - y, ship.x - x)
    balas = []
    for i in range(n):
        a = base + (i - (n - 1) / 2) * abertura
        balas.append(BalaPixel(x, y, math.cos(a) * velocidad, math.sin(a) * velocidad, color=color, tam=10))
    return balas


def _hitbox(x, y, radio):
    """Golpe con el cuerpo: hitbox invisible que dura un cuadro."""
    return BalaPixel(x, y, 0, 0, vida=2, radio=radio, visible=False)


# ------------------------------------------------------------------ jefes

class JefeHalloweenBase(JefeGatoBase):
    """Base de los tres: aviso de fila (la franja roja donde va a pasar un
    ataque de lado a lado) y bombas en arco que estallan al caer."""

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.especial = None
        self.timer_especial = 300
        self.indice_especial = 0
        self.bombas = []

    def _lanzar_bomba(self, objetivo_x, objetivo_y, nombre, radio, al_estallar):
        bomba = _lanzar_en_arco(self.x, self.y, objetivo_x, objetivo_y, sprite_halloween(nombre, 1, 3), radio)
        self.bombas.append((bomba, objetivo_y, al_estallar))
        return bomba

    def _actualizar_bombas(self):
        balas = []
        quedan = []
        for bomba, piso, al_estallar in self.bombas:
            if bomba.vy > 0 and bomba.y >= piso or not bomba.active:
                if bomba.active:
                    bomba.active = False
                    balas += al_estallar(bomba.x, bomba.y)
            else:
                quedan.append((bomba, piso, al_estallar))
        self.bombas = quedan
        return balas

    def _dibujar_aviso_fila(self, screen, y, t, offset_x=0, offset_y=0):
        if (t // 5) % 2 == 0:
            capa = pygame.Surface((GAME_WIDTH, 56), pygame.SRCALPHA)
            capa.fill((255, 40, 60, 70))
            screen.blit(capa, (offset_x, int(y) - 28 + offset_y))
            for x in range(0, GAME_WIDTH, 48):
                screen.fill((255, 80, 90), (x + offset_x, int(y) - 30 + offset_y, 28, 4))
                screen.fill((255, 80, 90), (x + offset_x, int(y) + 26 + offset_y, 28, 4))


class ReyCalabazaBoss(JefeHalloweenBase):
    """Primer jefe de Halloween. Salta de lado a lado soltando semillas al
    aterrizar, dispara abanicos de semillas y tira calabazas bomba que
    estallan en un anillo al caer cerca de la nave. Especiales en rotacion:
      - RODADA: sale por arriba, marca la fila de la nave y la cruza rodando.
      - FUEGO FATUO: se planta y escupe una espiral de llamas verdes.
      - LLUVIA DE CALABAZAS: muchas bombas a la vez por toda la pantalla."""

    nombre = "REY CALABAZA"
    hp_base = 900
    ESCALA = 4

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = GAME_WIDTH / 2
        self.y = -140.0
        self.base_y = 170.0
        self.size = 62
        self.alto_sprite = 34 * self.ESCALA
        self.salto = None
        self.aplastado = 0
        self.timer_salto = 90
        self.timer_semillas = 70
        self.timer_bombas = 140
        self.angulo = 0.0
        self.escupe = 0

    def _estallido(self, x, y):
        n = 12 if self.furioso else 8
        return _anillo(x, y, n, 2.6 * math.sqrt(self._vel()), LUZ_CARA, 10, desfase=random.uniform(0, 1))

    def update(self, ship):
        self._tick_comun()
        balas = self._actualizar_bombas()
        v = self._vel()
        if self.aplastado > 0:
            self.aplastado -= 1
        if self.escupe > 0:
            self.escupe -= 1
        if self.entrando:
            self.y += 7
            if self.y >= self.base_y:
                self.y = self.base_y
                self.entrando = False
                self.aplastado = 12
            return balas
        if self.especial is not None:
            return balas + self._actualizar_especial(ship, v)
        if self.salto is not None:
            s = self.salto
            s['t'] += 1
            p = min(1.0, s['t'] / s['dur'])
            self.x = s['x0'] + (s['x1'] - s['x0']) * p
            self.y = self.base_y - math.sin(math.pi * p) * 110
            if p >= 1.0:
                self.salto = None
                self.y = self.base_y
                self.aplastado = 12
                balas += _anillo(self.x, self.y + 40, 14 if self.furioso else 10, 2.4 * math.sqrt(v),
                                 NARANJA_CLARO, 10, desfase=random.uniform(0, 1))
            return balas
        self.timer_especial -= 1
        self.timer_salto -= 1
        self.timer_semillas -= 1
        self.timer_bombas -= 1
        if self.timer_especial <= 0:
            self.timer_especial = max(260, int((480 if not self.furioso else 360) / v))
            self._iniciar_especial(ship)
        elif self.timer_salto <= 0:
            self.timer_salto = max(60, int((150 if not self.furioso else 100) / v))
            destino = max(120.0, min(GAME_WIDTH - 120.0, ship.x + random.uniform(-180, 180)))
            self.salto = {'x0': self.x, 'x1': destino, 't': 0, 'dur': max(36, int(60 / math.sqrt(v)))}
        elif self.timer_semillas <= 0:
            self.timer_semillas = max(40, int((95 if not self.furioso else 65) / v))
            self.escupe = 14
            balas += _semillas_en_abanico(self.x, self.y + 50, ship, 7 if self.furioso else 5, 0.22,
                                          3.4 * math.sqrt(v))
        elif self.timer_bombas <= 0:
            self.timer_bombas = max(70, int((170 if not self.furioso else 120) / v))
            for dx in ((-150, 150) if not self.furioso else (-200, 0, 200)):
                balas.append(self._lanzar_bomba(ship.x + dx, ship.y - 20, "mini_calabaza", 14, self._estallido))
        return balas

    def _iniciar_especial(self, ship):
        tipo = ("rodada", "fatuo", "lluvia")[self.indice_especial % 3]
        self.indice_especial += 1
        if tipo == "rodada":
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'sube', 'fila': ship.y, 'dir': 1}
            self._anunciar("¡RODADA DE CALABAZA!")
        elif tipo == "fatuo":
            self.especial = {'tipo': tipo, 't': 0}
            self._anunciar("¡FUEGO FATUO!")
        else:
            self.especial = {'tipo': tipo, 't': 0}
            self._anunciar("¡LLUVIA DE CALABAZAS!")

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "rodada":
            if e['fase'] == 'sube':
                self.y -= 12
                if self.y < -120:
                    e['fase'], e['t'] = 'aviso', 0
                    e['fila'] = max(GAME_HEIGHT * 0.45, min(GAME_HEIGHT - 60, ship.y))
                    e['dir'] = random.choice((-1, 1))
                    self.x = -120 if e['dir'] > 0 else GAME_WIDTH + 120
                    self.y = e['fila']
            elif e['fase'] == 'aviso':
                if e['t'] >= 60:
                    e['fase'], e['t'] = 'rueda', 0
            elif e['fase'] == 'rueda':
                self.x += e['dir'] * 13 * math.sqrt(v)
                self.angulo += e['dir'] * 0.4
                balas.append(_hitbox(self.x, self.y, 56))
                if e['t'] % 6 == 0:
                    balas.append(BalaPixel(self.x, self.y, 0, -random.uniform(2, 4), color=LUZ_CARA, tam=10,
                                           gravedad=0.08))
                if not -160 < self.x < GAME_WIDTH + 160:
                    e['fase'], e['t'] = 'vuelve', 0
                    self.x = GAME_WIDTH / 2
                    self.y = -140
                    self.angulo = 0.0
            else:
                self.y += 9
                if self.y >= self.base_y:
                    self.y = self.base_y
                    self.aplastado = 12
                    balas += self._estallido(self.x, self.y + 40)
                    self.especial = None
        elif e['tipo'] == "fatuo":
            self.escupe = 4
            if 20 <= e['t'] and e['t'] % 6 == 0:
                brazos = 4 if self.furioso else 3
                for k in range(brazos):
                    a = e['t'] * 0.05 + 2 * math.pi * k / brazos
                    balas.append(BalaPixel(self.x, self.y + 40, math.cos(a) * 2.6 * math.sqrt(v),
                                           math.sin(a) * 2.6 * math.sqrt(v), color=VERDE_TOXICO, tam=12,
                                           forma="estrella"))
            if e['t'] >= 170:
                self.especial = None
        else:
            if e['t'] % 14 == 0 and e['t'] <= 100:
                destino_x = random.uniform(60, GAME_WIDTH - 60)
                destino_y = random.uniform(GAME_HEIGHT * 0.45, GAME_HEIGHT - 60)
                balas.append(self._lanzar_bomba(destino_x, destino_y, "mini_calabaza", 14, self._estallido))
            if e['t'] >= 150:
                self.especial = None
        return balas

    def draw(self, screen, offset_x=0, offset_y=0):
        e = self.especial
        if e is not None and e['tipo'] == 'rodada' and e['fase'] == 'aviso':
            self._dibujar_aviso_fila(screen, e['fila'], e['t'], offset_x, offset_y)
        if self.furioso:
            cuadro = 2
        elif self.escupe > 0:
            cuadro = 3
        else:
            cuadro = (self.t // 10) % 2
        spr = sprite_halloween("calabaza", cuadro, self.ESCALA, blanco=self.flash % 2 == 1)
        if self.angulo:
            spr = pygame.transform.rotate(spr, -math.degrees(self.angulo))
        elif self.aplastado > 0:
            spr = pygame.transform.scale(spr, (int(spr.get_width() * 1.12), int(spr.get_height() * 0.86)))
        if self.salto is not None:
            sombra = pygame.Surface((130, 18), pygame.SRCALPHA)
            pygame.draw.ellipse(sombra, (0, 0, 0, 90), (0, 0, 130, 18))
            screen.blit(sombra, (int(self.x) - 65 + offset_x, int(self.base_y) + self.alto_sprite // 2 - 10 + offset_y))
        _blit_centrado(screen, spr, self.x + offset_x, self.y + offset_y)


class BrujaBoss(JefeHalloweenBase):
    """Segundo jefe de Halloween. Vuela de lado a lado en su escoba, larga
    murcielagos que persiguen a la nave un rato y pociones que dejan un
    charco toxico donde caen. Especiales en rotacion:
      - ESCOBA VELOZ: marca la fila de la nave y la cruza a toda velocidad.
      - CALDERO ESTELAR: se queda quieta girando una espiral de estrellas.
      - AQUELARRE: aparecen dos brujas fantasma que tambien disparan; solo
        la de verdad recibe daño.

    A la mitad de la vida (UMBRAL_GIGANTE) pide la cinematica en la que se
    toma una pocion y crece (pide_cinematica = "bruja_gigante", ver
    modules/entities/bruja_gigante.py y main.py); mientras tanto no recibe
    daño. Despues main.py llama a volverse_gigante() y la pelea cambia: la
    bruja ocupa la parte de arriba de la pantalla, de frente, y ataca con
    magia (ya no con los brazos). Especiales del modo gigante:
      - POCIONES: tandas de pociones desde la mano derecha.
      - CIRCULOS MAGICOS: aparecen circulos sobre la nave que se cargan y
        estallan en una columna de luz.
      - SELLO ESTELAR: un sello gigante gira en su mano izquierda y suelta
        espirales de estrellas."""

    nombre = "BRUJA NEON"
    hp_base = 1000
    ESCALA = 3
    UMBRAL_GIGANTE = 0.5
    ESCALA_GIGANTE = 4
    Y_GIGANTE = 170.0
    # manos en el arte gigante (120x92, centro 60,46), en pixeles de pantalla
    MANO_CIRCULO = ((13 - 60) * 4, (58 - 46) * 4)
    MANO_POCION = ((106 - 60) * 4, (52 - 46) * 4)

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = -150.0
        self.y = 150.0
        self.base_y = 150.0
        self.size = 60
        self.alto_sprite = 47 * self.ESCALA
        self.vx = 3.0
        self.mira_der = True
        self.timer_murcielagos = 80
        self.timer_pocion = 150
        self.clones = []
        self.charcos = []
        self.gigante = False
        self.transformando = False
        self.pide_cinematica = None
        self.circulos = []
        self.sin_pocion = 0

    def take_damage(self, amount=1):
        if self.transformando:
            return
        super().take_damage(amount)
        if not self.gigante and self.active and self.hp <= self.max_hp * self.UMBRAL_GIGANTE:
            # se guarda el resto del golpe para despues de crecer
            self.transformando = True
            self.pide_cinematica = "bruja_gigante"
            self.especial = None
            self.clones = []
            self.bombas = []

    def volverse_gigante(self):
        """Despues de la cinematica: la bruja gigante de frente, con una
        pocion en la mano derecha y la izquierda lista para la magia."""
        self.gigante = True
        self.transformando = False
        self.pide_cinematica = None
        self.entrando = False
        self.especial = None
        self.clones = []
        self.bombas = []
        self.name = "BRUJA NEON GIGANTE"
        self.x = GAME_WIDTH / 2
        self.y = self.Y_GIGANTE
        self.size = 140
        self.alto_sprite = 92 * self.ESCALA_GIGANTE
        self.timer_especial = 120
        self.indice_especial = 0
        self.timer_pocion = 70
        self.timer_murcielagos = 160
        self.risa = 0
        self.circulos = []
        self.sin_pocion = 0

    def _charco(self, x, y):
        balas = []
        for k in range(-2, 3):
            balas.append(BalaPixel(x + k * 20, y, 0, 0, color=VERDE_TOXICO, tam=16, vida=170))
        balas += _anillo(x, y, 6, 2.0, VERDE_TOXICO, 8)
        return balas

    def update(self, ship):
        self._tick_comun()
        if self.transformando:
            # espera la cinematica flotando hacia el centro
            self.x += (GAME_WIDTH / 2 - self.x) * 0.1
            self.y += (self.base_y - self.y) * 0.1
            return []
        balas = self._actualizar_bombas()
        v = self._vel()
        if self.gigante:
            return balas + self._actualizar_gigante(ship, v)
        if self.entrando:
            self.x += 6
            self.y = self.base_y + math.sin(self.t * 0.08) * 10
            if self.x >= GAME_WIDTH / 2:
                self.entrando = False
            return balas
        if self.especial is not None:
            return balas + self._actualizar_especial(ship, v)
        # vuelo normal: de lado a lado con ondulacion
        self.x += self.vx * v
        if self.x < 110 or self.x > GAME_WIDTH - 110:
            self.vx = -self.vx
            self.x = max(110, min(GAME_WIDTH - 110, self.x))
        self.mira_der = self.vx > 0
        self.y = self.base_y + math.sin(self.t * 0.05) * 30
        self.timer_especial -= 1
        self.timer_murcielagos -= 1
        self.timer_pocion -= 1
        if self.timer_especial <= 0:
            self.timer_especial = max(260, int((460 if not self.furioso else 340) / v))
            self._iniciar_especial(ship)
        elif self.timer_murcielagos <= 0:
            self.timer_murcielagos = max(50, int((120 if not self.furioso else 80) / v))
            for k in range(4 if self.furioso else 3):
                a = math.pi / 2 + (k - 1) * 0.6
                balas.append(Murcielago(self.x, self.y + 20, math.cos(a) * 3.2 * math.sqrt(v),
                                        math.sin(a) * 3.2 * math.sqrt(v), ship))
        elif self.timer_pocion <= 0:
            self.timer_pocion = max(80, int((190 if not self.furioso else 130) / v))
            balas.append(self._lanzar_bomba(ship.x, ship.y, "pocion", 10, self._charco))
        return balas

    def _iniciar_especial(self, ship):
        tipo = ("escoba", "caldero", "aquelarre")[self.indice_especial % 3]
        self.indice_especial += 1
        if tipo == "escoba":
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'sale', 'fila': ship.y, 'dir': 1, 'pasadas': 0}
            self._anunciar("¡ESCOBA VELOZ!")
        elif tipo == "caldero":
            self.especial = {'tipo': tipo, 't': 0}
            self._anunciar("¡CALDERO ESTELAR!")
        else:
            self.especial = {'tipo': tipo, 't': 0}
            self.clones = [{'x': self.x, 'y': self.y, 'dx': -260}, {'x': self.x, 'y': self.y, 'dx': 260}]
            self._anunciar("¡AQUELARRE!")

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "escoba":
            if e['fase'] == 'sale':
                self.y -= 10
                if self.y < -100:
                    e['fase'], e['t'] = 'aviso', 0
                    e['fila'] = max(GAME_HEIGHT * 0.45, min(GAME_HEIGHT - 60, ship.y))
                    e['dir'] = 1 if ship.x > GAME_WIDTH / 2 else -1
                    self.x = -140 if e['dir'] > 0 else GAME_WIDTH + 140
                    self.y = e['fila']
                    self.mira_der = e['dir'] > 0
            elif e['fase'] == 'aviso':
                if e['t'] >= 55:
                    e['fase'], e['t'] = 'cruza', 0
            elif e['fase'] == 'cruza':
                self.x += e['dir'] * 15 * math.sqrt(v)
                balas.append(_hitbox(self.x, self.y, 50))
                if e['t'] % 4 == 0:
                    balas.append(BalaPixel(self.x, self.y, random.uniform(-0.5, 0.5), random.uniform(1, 2.5),
                                           color=VIOLETA_CLARO, tam=10, forma="estrella", vida=80))
                if not -180 < self.x < GAME_WIDTH + 180:
                    e['pasadas'] += 1
                    if self.furioso and e['pasadas'] < 2:
                        e['fase'], e['t'] = 'aviso', 0
                        e['fila'] = max(GAME_HEIGHT * 0.45, min(GAME_HEIGHT - 60, ship.y))
                        e['dir'] = -e['dir']
                        self.y = e['fila']
                        self.mira_der = e['dir'] > 0
                    else:
                        e['fase'], e['t'] = 'vuelve', 0
                        self.x = -140.0
                        self.y = self.base_y
                        self.vx = abs(self.vx)
                        self.mira_der = True
            else:
                self.x += 6
                if self.x >= 140:
                    self.especial = None
        elif e['tipo'] == "caldero":
            self.y += (self.base_y - self.y) * 0.1
            if 20 <= e['t'] and e['t'] % 5 == 0:
                brazos = 3 if self.furioso else 2
                for k in range(brazos):
                    a = e['t'] * 0.07 + 2 * math.pi * k / brazos
                    for sentido in (1, -1):
                        aa = a * sentido
                        balas.append(BalaPixel(self.x, self.y + 10, math.cos(aa) * 2.4 * math.sqrt(v),
                                               math.sin(aa) * 2.4 * math.sqrt(v), color=VIOLETA_CLARO, tam=12,
                                               forma="estrella"))
            if e['t'] >= 160:
                self.especial = None
        else:
            p = min(1.0, e['t'] / 30)
            for c in self.clones:
                c['x'] = max(80.0, min(GAME_WIDTH - 80.0, self.x + c['dx'] * p))
                c['y'] = self.y + math.sin(self.t * 0.07 + c['dx']) * 14
            if e['t'] > 30 and e['t'] % 35 == 0:
                for cx, cy in [(self.x, self.y)] + [(c['x'], c['y']) for c in self.clones]:
                    balas.append(_apuntada(cx, cy + 10, ship, 4.2 * math.sqrt(v), color=VIOLETA_CLARO, tam=14,
                                           forma="estrella"))
            if e['t'] > 30 and e['t'] % 70 == 0:
                for c in self.clones:
                    balas.append(Murcielago(c['x'], c['y'] + 10, 0, 3.0, ship, persigue=50))
            if e['t'] >= 210:
                self.clones = []
                self.especial = None
        return balas

    # ------------------------------------------------------- modo gigante

    def _mano(self, cual):
        dx, dy = cual
        return self.x + dx, self.y + dy

    def _lanzar_desde(self, x0, y0, objetivo_x, objetivo_y):
        bomba = _lanzar_en_arco(x0, y0, objetivo_x, objetivo_y, sprite_halloween("pocion", 1, 4), 12,
                                vy0=-4.0, gravedad=0.2)
        self.bombas.append((bomba, objetivo_y, self._charco))
        self.sin_pocion = 22   # la mano queda vacia un ratito
        return bomba

    def _actualizar_gigante(self, ship, v):
        balas = []
        self.risa = max(0, self.risa - 1)
        self.sin_pocion = max(0, self.sin_pocion - 1)
        self.x = GAME_WIDTH / 2 + math.sin(self.t * 0.02) * 50
        self.y = self.Y_GIGANTE + math.sin(self.t * 0.04) * 8
        balas += self._actualizar_circulos(v)
        if self.especial is not None:
            balas += self._especial_gigante(ship, v)
            return balas
        self.timer_especial -= 1
        self.timer_pocion -= 1
        self.timer_murcielagos -= 1
        if self.timer_especial <= 0:
            self.timer_especial = max(150, int((300 if not self.furioso else 220) / v))
            tipo = ("pociones", "circulos", "sello")[self.indice_especial % 3]
            self.indice_especial += 1
            self.especial = {'tipo': tipo, 't': 0, 'tandas': 0, 'puestos': 0}
            self._anunciar({"pociones": "¡POCIONES!", "circulos": "¡CÍRCULOS MÁGICOS!",
                            "sello": "¡SELLO ESTELAR!"}[tipo])
        elif self.timer_pocion <= 0:
            # una pocion suelta desde la mano derecha
            self.timer_pocion = max(60, int((120 if not self.furioso else 80) / v))
            balas.append(self._lanzar_desde(*self._mano(self.MANO_POCION), ship.x, ship.y))
        elif self.timer_murcielagos <= 0:
            # murcielagos que salen del sombrero
            self.timer_murcielagos = max(110, int((200 if not self.furioso else 140) / v))
            for k in range(3 if self.furioso else 2):
                a = math.pi / 2 + (k - 0.5) * 0.9
                balas.append(Murcielago(self.x + (k - 0.5) * 300, self.y - 40, math.cos(a) * 3.0 * math.sqrt(v),
                                        abs(math.sin(a)) * 3.0 * math.sqrt(v), ship))
        return balas

    def _actualizar_circulos(self, v):
        """Circulos magicos en el piso: se cargan (CARGA_CIRCULO cuadros) y
        estallan en una columna de luz con un anillo de estrellas."""
        balas = []
        for c in self.circulos:
            c['t'] += 1
            if c['t'] == self.CARGA_CIRCULO:
                balas += _anillo(c['x'], c['y'], 10 if self.furioso else 8, 2.6 * math.sqrt(v), VIOLETA_CLARO, 12,
                                 forma="estrella", desfase=random.uniform(0, 1))
                self.risa = max(self.risa, 12)
            if self.CARGA_CIRCULO <= c['t'] < self.CARGA_CIRCULO + 10:
                balas.append(_hitbox(c['x'], c['y'], self.RADIO_CIRCULO))
        self.circulos = [c for c in self.circulos if c['t'] < self.CARGA_CIRCULO + 24]
        return balas

    CARGA_CIRCULO = 62
    RADIO_CIRCULO = 66

    def _especial_gigante(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "pociones":
            # tandas de pociones en abanico desde la mano derecha
            if e['t'] == 30:
                n = 5 if self.furioso else 3
                x0, y0 = self._mano(self.MANO_POCION)
                corrido = 55 if e['tandas'] % 2 else 0
                for k in range(n):
                    dx = (k - (n - 1) / 2) * 120 + corrido
                    tx = max(40, min(GAME_WIDTH - 40, ship.x + dx))
                    balas.append(self._lanzar_desde(x0, y0, tx, max(GAME_HEIGHT * 0.55, ship.y)))
                self.risa = 30
            elif e['t'] >= 60:
                e['tandas'] += 1
                if e['tandas'] >= (3 if self.furioso else 2):
                    self.especial = None
                else:
                    e['t'] = 0
        elif e['tipo'] == "circulos":
            # un circulo debajo de la nave cada tanto; termina cuando estallan todos
            total = 5 if self.furioso else 3
            if e['puestos'] < total and e['t'] % max(18, int(32 / v)) == 1:
                e['puestos'] += 1
                self.circulos.append({'x': max(60, min(GAME_WIDTH - 60, ship.x)),
                                      'y': max(GAME_HEIGHT * 0.55, min(GAME_HEIGHT - 50, ship.y)), 't': 0,
                                      'giro': random.uniform(0, 6)})
            elif e['puestos'] >= total and not self.circulos:
                self.especial = None
        else:
            # sello estelar: gira en la mano izquierda y suelta espirales
            x0, y0 = self._mano(self.MANO_CIRCULO)
            if 30 <= e['t'] < 170 and e['t'] % 6 == 0:
                brazos = 3 if self.furioso else 2
                for k in range(brazos):
                    a = e['t'] * 0.11 + 2 * math.pi * k / brazos
                    vel = 3.0 * math.sqrt(v)
                    balas.append(BalaPixel(x0, y0, math.cos(a) * vel, math.sin(a) * vel,
                                           color=(170, 236, 255) if k % 2 else VIOLETA_CLARO, tam=12,
                                           forma="estrella"))
            if e['t'] >= 190:
                self.especial = None
                self.risa = 30
        return balas

    @staticmethod
    def _circulo_magico(screen, x, y, r, giro, color, color2, k=1.0):
        """Circulo magico neon: dos anillos, runas que giran entre ellos y
        un hexagrama adentro. k (0..1) lo va dibujando mientras se carga."""
        x, y = int(x), int(y)
        r = max(6, int(r))
        pixelfx.dibujar_halo(screen, pixelfx.apagar(color, 0.35), x, y, r * 1.2)
        pygame.draw.circle(screen, color, (x, y), r, 4)
        pygame.draw.circle(screen, color2, (x, y), int(r * 0.8), 2)
        n = 12
        for i in range(int(n * k)):
            a = -giro * 0.7 + 2 * math.pi * i / n
            rx, ry = x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9
            screen.fill(color2 if i % 3 else WHITE, (int(rx) - 3, int(ry) - 3, 6, 6))
        if k > 0.4:
            for desfase in (0, math.pi / 3):
                puntos = [(x + math.cos(giro + desfase + 2 * math.pi * i / 3) * r * 0.78,
                           y + math.sin(giro + desfase + 2 * math.pi * i / 3) * r * 0.78) for i in range(3)]
                pygame.draw.polygon(screen, color, puntos, 2)
        pygame.draw.circle(screen, WHITE, (x, y), max(2, int(r * 0.12)))

    # constelaciones del aura de la bruja gigante (coordenadas del aura)
    _CONSTELACIONES = (
        ((40, 120), (90, 70), (130, 110), (170, 60)),
        ((320, 60), (360, 110), (410, 80), (440, 140)),
        ((30, 260), (70, 300), (60, 350)),
        ((410, 280), (450, 240), (440, 330)),
        ((200, 30), (240, 15), (280, 35)),
    )

    def _dibujar_gigante(self, screen, ox, oy):
        e = self.especial
        celeste, violeta = (170, 236, 255), VIOLETA_CLARO
        # circulos magicos en el piso (debajo de todo)
        for c in self.circulos:
            k = min(1.0, c['t'] / self.CARGA_CIRCULO)
            cx, cy = c['x'] + ox, c['y'] + oy
            if c['t'] < self.CARGA_CIRCULO:
                parpadea = k > 0.75 and (self.t // 3) % 2
                self._circulo_magico(screen, cx, cy, 20 + (self.RADIO_CIRCULO - 20) * k, c['giro'] + self.t * 0.08,
                                     WHITE if parpadea else celeste, violeta, k)
            else:
                # estalla: columna de luz hacia arriba
                d = c['t'] - self.CARGA_CIRCULO
                ancho = int(self.RADIO_CIRCULO * 1.6 * (1 - d / 24))
                if ancho > 0:
                    columna = pygame.Surface((ancho, int(cy)), pygame.SRCALPHA)
                    columna.fill((200, 245, 255, int(200 * (1 - d / 24))))
                    columna.fill((255, 255, 255, int(240 * (1 - d / 24))), (ancho // 4, 0, ancho // 2, int(cy)))
                    screen.blit(columna, (int(cx) - ancho // 2, 0))
                self._circulo_magico(screen, cx, cy, self.RADIO_CIRCULO + d * 2, c['giro'], WHITE, celeste)
        # aura que late detras
        aura = pygame.Surface((560, 420), pygame.SRCALPHA)
        alfa = 60 + int(30 * math.sin(self.t * 0.08))
        pygame.draw.ellipse(aura, (40, 90, 200, alfa), aura.get_rect())
        pygame.draw.ellipse(aura, (90, 160, 255, alfa // 2), aura.get_rect().inflate(-140, -110))
        for linea in self._CONSTELACIONES:
            linea = [(x * 1.15, y * 1.05) for x, y in linea]
            pygame.draw.lines(aura, (200, 240, 255, 150 + alfa // 2), False, linea, 2)
            for x, y in linea:
                aura.fill((255, 255, 255, 230), (int(x) - 3, int(y) - 3, 6, 6))
        _blit_centrado(screen, aura, self.x + ox, self.y + oy + 10)
        if self.risa > 0:
            cuadro = 2
        elif self.furioso:
            cuadro = 3
        elif self.t % 150 < 7:
            cuadro = 1
        else:
            cuadro = 0
        cuerpo = sprite_halloween("bruja_gigante", cuadro, self.ESCALA_GIGANTE, blanco=self.flash % 2 == 1)
        # alineado a la grilla del pixelado para que el arte no se deforme
        bx = int(self.x + ox) // 4 * 4
        by = int(self.y + oy) // 4 * 4
        _blit_centrado(screen, cuerpo, bx, by)
        # la pocion en la mano derecha
        px, py = self._mano(self.MANO_POCION)
        if self.sin_pocion == 0:
            pocion = sprite_halloween("pocion", 1, 4)
            _blit_centrado(screen, pocion, px + ox, py + oy - 22 + math.sin(self.t * 0.1) * 2)
        # la mano izquierda: un circulito siempre encendido, o el sello estelar
        cx, cy = self._mano(self.MANO_CIRCULO)
        if e is not None and e['tipo'] == 'sello':
            k = min(1.0, e['t'] / 30) * (1 if e['t'] < 170 else max(0.0, 1 - (e['t'] - 170) / 20))
            self._circulo_magico(screen, cx + ox, cy + oy - 30, 30 + 70 * k, self.t * 0.12, celeste, violeta, k)
        else:
            self._circulo_magico(screen, cx + ox, cy + oy - 30, 22 + 2 * math.sin(self.t * 0.1),
                                 self.t * 0.06, violeta, celeste, 1.0)

    def draw(self, screen, offset_x=0, offset_y=0):
        if self.gigante:
            self._dibujar_gigante(screen, offset_x, offset_y)
            return
        e = self.especial
        if e is not None and e['tipo'] == 'escoba' and e['fase'] == 'aviso':
            self._dibujar_aviso_fila(screen, e['fila'], e['t'], offset_x, offset_y)
        cuadro = (self.t // 8) % 2
        for c in self.clones:
            copia = sprite_halloween("bruja", cuadro, self.ESCALA, voltear=not self.mira_der).copy()
            copia.set_alpha(110)
            _blit_centrado(screen, copia, c['x'] + offset_x, c['y'] + offset_y)
        spr = sprite_halloween("bruja", cuadro, self.ESCALA, voltear=not self.mira_der, blanco=self.flash % 2 == 1)
        _blit_centrado(screen, spr, self.x + offset_x, self.y + offset_y)


class ParcaBoss(JefeHalloweenBase):
    """Ultimo jefe de Halloween. Flota y se teletransporta (mientras esta
    desvanecida no recibe daño), dispara calaveras y anillos de almas.
    Especiales en rotacion:
      - GUADAÑA: marca la fila de la nave y la barre de lado a lado
        (furiosa: dos barridas).
      - LLUVIA DE CALAVERAS: marca columnas y llueven calaveras en todas
        menos en un hueco.
      - DANZA MACABRA: gira en el lugar soltando una espiral de calaveras."""

    nombre = "LA PARCA"
    hp_base = 1500
    ESCALA = 4
    ANCHO_COLUMNA = 80

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = GAME_WIDTH / 2
        self.y = -160.0
        self.base_y = 160.0
        self.size = 70
        self.alto_sprite = 58 * self.ESCALA
        self.humo = []   # jirones de sombra que suben desde la tunica
        self.alfa = 1.0
        self.tele = None
        self.timer_tele = 200
        self.timer_calaveras = 70
        self.timer_almas = 160
        self.ataca = 0

    def take_damage(self, amount=1):
        if self.alfa < 0.5:
            return  # desvanecida: los disparos la atraviesan
        super().take_damage(amount)

    def _teletransportar(self, x, y, despues=None):
        self.tele = {'t': 0, 'x': x, 'y': y, 'despues': despues}

    def update(self, ship):
        self._tick_comun()
        balas = self._actualizar_bombas()
        v = self._vel()
        if self.ataca > 0:
            self.ataca -= 1
        if self.entrando:
            self.y += 5
            if self.y >= self.base_y:
                self.y = self.base_y
                self.entrando = False
            return balas
        if self.tele is not None:
            tl = self.tele
            tl['t'] += 1
            if tl['t'] <= 20:
                self.alfa = 1 - tl['t'] / 20
            elif tl['t'] == 21:
                self.x, self.y = tl['x'], tl['y']
            else:
                self.alfa = min(1.0, (tl['t'] - 21) / 20)
                if self.alfa >= 1.0:
                    self.tele = None
                    if tl['despues']:
                        tl['despues']()
            return balas
        if self.especial is not None:
            return balas + self._actualizar_especial(ship, v)
        self.y = self.base_y + math.sin(self.t * 0.04) * 16
        self.x += (ship.x - self.x) * 0.006 * v
        self.timer_especial -= 1
        self.timer_tele -= 1
        self.timer_calaveras -= 1
        self.timer_almas -= 1
        if self.timer_especial <= 0:
            self.timer_especial = max(260, int((470 if not self.furioso else 340) / v))
            self._iniciar_especial(ship)
        elif self.timer_tele <= 0:
            self.timer_tele = max(120, int((260 if not self.furioso else 170) / v))
            self._teletransportar(random.uniform(140, GAME_WIDTH - 140), random.uniform(110, 220))
        elif self.timer_calaveras <= 0:
            self.timer_calaveras = max(40, int((90 if not self.furioso else 60) / v))
            self.ataca = 16
            spr = sprite_halloween("calavera", 1, 3)
            abanico = 2 if self.furioso else 1   # furiosa: cinco calaveras
            for k in range(-abanico, abanico + 1):
                bala = _apuntada(self.x, self.y + 20, ship, 4.0 * math.sqrt(v), forma="sprite", sprite=spr, radio=12)
                a = math.atan2(bala.vy, bala.vx) + k * 0.25
                vel = math.hypot(bala.vx, bala.vy)
                bala.vx, bala.vy = math.cos(a) * vel, math.sin(a) * vel
                balas.append(bala)
        elif self.timer_almas <= 0:
            self.timer_almas = max(90, int((200 if not self.furioso else 140) / v))
            spr = sprite_halloween("alma", (self.t // 6) % 2, 3)
            n = 14 if self.furioso else 10
            for i in range(n):
                a = 2 * math.pi * i / n + self.t * 0.01
                balas.append(BalaPixel(self.x, self.y, math.cos(a) * 2.1 * math.sqrt(v), math.sin(a) * 2.1 * math.sqrt(v),
                                       forma="sprite", sprite=spr, radio=11))
        return balas

    def _iniciar_especial(self, ship):
        tipo = ("guadana", "lluvia", "danza")[self.indice_especial % 3]
        self.indice_especial += 1
        if tipo == "guadana":
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'aviso', 'pasadas': 0,
                             'fila': max(GAME_HEIGHT * 0.45, min(GAME_HEIGHT - 60, ship.y)),
                             'dir': 1 if ship.x > GAME_WIDTH / 2 else -1}
            self._anunciar("¡GUADAÑA!")
        elif tipo == "lluvia":
            columnas = GAME_WIDTH // self.ANCHO_COLUMNA
            self.especial = {'tipo': tipo, 't': 0, 'hueco': random.randint(1, columnas - 3)}
            self._anunciar("¡LLUVIA DE CALAVERAS!")
        else:
            self.especial = {'tipo': tipo, 't': 0}
            self._anunciar("¡DANZA MACABRA!")

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "guadana":
            if e['fase'] == 'aviso':
                # se va al costado mientras parpadea la fila
                lado_x = -60 if e['dir'] > 0 else GAME_WIDTH + 60
                self.x += (lado_x - self.x) * 0.12
                self.y += (e['fila'] - self.y) * 0.12
                if e['t'] >= 60:
                    e['fase'], e['t'] = 'barre', 0
                    self.x = lado_x
                    self.y = e['fila']
            elif e['fase'] == 'barre':
                self.ataca = 4
                self.x += e['dir'] * 16 * math.sqrt(v)
                # el filo de la guadaña: hitboxes a lo alto de la fila
                for dy in (-30, 0, 30):
                    balas.append(_hitbox(self.x + e['dir'] * 30, self.y + dy, 26))
                if not -120 < self.x < GAME_WIDTH + 120:
                    e['pasadas'] += 1
                    if self.furioso and e['pasadas'] < 2:
                        e['fase'], e['t'] = 'aviso', 0
                        e['fila'] = max(GAME_HEIGHT * 0.45, min(GAME_HEIGHT - 60, ship.y))
                        e['dir'] = -e['dir']
                    else:
                        self.especial = None
                        self.alfa = 0.0
                        self._teletransportar(GAME_WIDTH / 2, self.base_y)
                        self.tele['t'] = 20  # aparece en el centro sin desvanecerse antes
        elif e['tipo'] == "lluvia":
            columnas = GAME_WIDTH // self.ANCHO_COLUMNA
            if e['t'] in (60, 110):
                if e['t'] == 110:
                    e['hueco'] = max(0, min(columnas - 2, e['hueco'] + random.choice((-1, 1))))
                spr = sprite_halloween("calavera", 1, 3)
                for c in range(columnas):
                    if c in (e['hueco'], e['hueco'] + 1):
                        continue
                    cx = c * self.ANCHO_COLUMNA + self.ANCHO_COLUMNA // 2
                    balas.append(BalaPixel(cx, -30, 0, 5.2 * math.sqrt(v), forma="sprite", sprite=spr, radio=14))
            if e['t'] >= 170:
                self.especial = None
        else:
            self.ataca = 4
            if e['t'] % 6 == 0:
                spr = sprite_halloween("calavera", 1, 3)
                brazos = 5 if self.furioso else 4
                for k in range(brazos):
                    a = e['t'] * 0.045 + 2 * math.pi * k / brazos
                    balas.append(BalaPixel(self.x, self.y, math.cos(a) * 2.6 * math.sqrt(v), math.sin(a) * 2.6 * math.sqrt(v),
                                           forma="sprite", sprite=spr, radio=12))
            if e['t'] >= 180:
                self.especial = None
        return balas

    def draw(self, screen, offset_x=0, offset_y=0):
        e = self.especial
        if e is not None and e['tipo'] == 'guadana' and e['fase'] == 'aviso':
            self._dibujar_aviso_fila(screen, e['fila'], e['t'], offset_x, offset_y)
        if e is not None and e['tipo'] == 'lluvia' and e['t'] < 120:
            parpadeo = (self.t // 6) % 2 == 0
            for c in range(GAME_WIDTH // self.ANCHO_COLUMNA):
                cx = c * self.ANCHO_COLUMNA + self.ANCHO_COLUMNA // 2 + offset_x
                hueco = c in (e['hueco'], e['hueco'] + 1)
                if hueco or parpadeo:
                    color = VERDE_TOXICO if hueco else (255, 80, 80)
                    for k in range(3):
                        screen.fill(color, (cx - 12 + k * 4, 16 + k * 4 + offset_y, 24 - k * 8, 4))
        cuadro = 2 if self.ataca > 0 or self.furioso else (self.t // 10) % 2
        self._dibujar_aura(screen, self.x + offset_x, self.y + offset_y)
        spr = sprite_halloween("parca", cuadro, self.ESCALA, voltear=e is not None and e['tipo'] == 'guadana'
                               and e['dir'] < 0, blanco=self.flash % 2 == 1)
        if e is not None and e['tipo'] == 'danza':
            spr = pygame.transform.rotate(spr, math.sin(e['t'] * 0.3) * 20)
        if self.alfa < 1.0:
            spr = spr.copy()
            spr.set_alpha(int(255 * self.alfa))
        _blit_centrado(screen, spr, self.x + offset_x, self.y + offset_y)


    def _dibujar_aura(self, screen, x, y):
        """Sombra que la rodea: un halo oscuro (rojo cuando esta furiosa) y
        jirones de humo que se desprenden de la tunica y suben."""
        if self.alfa < 0.3:
            return
        latido = 0.5 + 0.5 * math.sin(self.t * 0.12)
        color = (200, 20, 30) if self.furioso else (130, 30, 30)
        pixelfx.dibujar_halo(screen, pixelfx.apagar(color, 0.5 + 0.3 * latido), x, y + 20, 95 + 10 * latido)
        if self.t % 4 == 0:
            self.humo.append([random.uniform(-70, 70), random.uniform(10, 90), 0])
        for h in self.humo:
            h[2] += 1
        self.humo = [h for h in self.humo if h[2] < 40]
        for hx, hy, edad in self.humo:
            k = edad / 40
            tam = int(10 * (1 - k)) + 2
            col = pixelfx.apagar((255, 120, 50) if edad % 7 == 0 else ((150, 20, 30) if self.furioso else HUMO_PARCA),
                                 1 - k * 0.8)   # humo y alguna brasa
            screen.fill(col, (int(x + hx + math.sin(edad * 0.2 + hx) * 6) - tam // 2,
                              int(y + hy - edad * 1.6) - tam // 2, tam, tam))


# ------------------------------------------------------------ cinematicas

class CinematicaVictoriaHalloween(CinematicaVictoriaFalsa):
    """La VICTORIA falsa de siempre, pero a mitad del glitch un brazo de
    zombi atraviesa la pantalla desde abajo: todo se tiñe de naranja y
    violeta, las palabras pasan a ser de Halloween ("DULCE O TRUCO",
    "BOO!", "HALLOWEEN.EXE"...) y al final el brazo agarra el cartel de
    "NEW BOSS READY". eventos agrega "brazo" (cuando sale) y "agarra"."""

    P_BRAZO = 0.3
    P_AGARRA = 0.8

    def __init__(self, captura):
        super().__init__(captura)
        self.brazo_afuera = False
        self.agarro = False

    def update(self):
        super().update()
        p = self._progreso()
        if self.t >= self.DURACION_NORMAL and p >= self.P_BRAZO and not self.brazo_afuera:
            self.brazo_afuera = True
            self.eventos.append("brazo")
            self.temblor = 16
            self.PALABRAS = PALABRAS_HALLOWEEN
            self.COLORES = COLORES_HALLOWEEN
            self.COLORES_PANEL = (NARANJA, VIOLETA, VERDE_TOXICO)
            self.TITULO_COLOR = NARANJA_CLARO
        if p >= self.P_AGARRA and not self.agarro:
            self.agarro = True
            self.eventos.append("agarra")
            self.temblor = 12

    def _dibujar_extra(self, surface, p):
        if not self.brazo_afuera:
            return
        # tinte naranja/violeta que late sobre el glitch
        tinte = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        tinte.fill((*(NARANJA if (self.t // 4) % 2 else VIOLETA), 60))
        surface.blit(tinte, (0, 0))
        # el brazo sube rapido desde abajo y se sacude
        k = min(1.0, (p - self.P_BRAZO) / 0.12)
        k = 1 - (1 - k) ** 3
        escala = 8
        brazo = sprite_halloween("brazo", 1 if self.agarro else 0, escala)
        alto = brazo.get_height()
        x = GAME_WIDTH // 2 - brazo.get_width() // 2 + random.randint(-4, 4)
        y_final = GAME_HEIGHT // 2 - 50 if self.agarro else GAME_HEIGHT // 2 - 10
        y = int(GAME_HEIGHT + 20 - k * (GAME_HEIGHT + 20 - y_final))
        # grietas del "vidrio" donde lo atraveso
        for i in range(8):
            a = i * math.pi / 8 + 0.2
            largo = 120 + (i * 37) % 90
            pygame.draw.line(surface, (255, 220, 200), (GAME_WIDTH // 2, GAME_HEIGHT - 10),
                             (GAME_WIDTH // 2 - math.cos(a) * largo, GAME_HEIGHT - 10 - math.sin(a) * largo), 3)
        surface.blit(brazo, (x, y))
        if y + alto < GAME_HEIGHT:
            surface.fill(PIEL_ZOMBI_OSCURA, (x + 7 * escala, y + alto, 10 * escala, GAME_HEIGHT - y - alto))
        if self.agarro:
            self._texto_glitch(surface, "HALLOWEEN.EXE", 40, VERDE_TOXICO, GAME_WIDTH // 2 + random.randint(-4, 4),
                               GAME_HEIGHT // 2 + 90, 4)


class CinematicaFinHalloween:
    """Final de la ruta de Halloween al caer la Parca: noche con luna, el
    Rey Calabaza convertido en farol con caramelos alrededor, murcielagos y
    "¡FELIZ HALLOWEEN!" con "Sobreviviste a la noche de brujas" escribiendose.
    Misma interfaz que CinematicaGatoDormido (update/draw/saltar/terminada)."""

    DURACION = 600
    FUNDIDO = 45
    MENSAJE = "Sobreviviste a la noche de brujas"

    def __init__(self):
        self.t = 0
        self.fin = self.DURACION
        self.fondo = FondoHalloween()
        rng = random.Random(5)
        self.caramelos = [(rng.uniform(-170, 170), rng.uniform(0, 30), rng.choice(
            ((255, 80, 160), (90, 220, 255), (255, 230, 80), (150, 255, 120)))) for _ in range(14)]

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 60:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def update(self):
        self.t += 1
        self.fondo.update()
        if self.t % 90 == 0:
            self.fondo.murcielagos.append({'x': -30, 'y': random.uniform(80, 260), 'vx': 3.0})

    def draw(self, surface):
        mundo = pygame.Surface(surface.get_size())
        self.fondo.draw(mundo)
        cx, cy = GAME_WIDTH // 2, int(GAME_HEIGHT * 0.66)
        brillo = pygame.Surface((420, 420), pygame.SRCALPHA)
        pygame.draw.circle(brillo, (255, 160, 40, 50 + int(20 * math.sin(self.t * 0.1))), (210, 210), 200)
        mundo.blit(brillo, (cx - 210, cy - 210))
        calabaza = sprite_halloween("calabaza", (self.t // 14) % 2, 5)
        _blit_centrado(mundo, calabaza, cx, cy)
        for dx, dy, color in self.caramelos:
            x, y = cx + dx, cy + 90 + dy
            mundo.fill(color, (int(x) - 6, int(y) - 4, 12, 8))
            mundo.fill(WHITE, (int(x) - 12, int(y) - 2, 6, 4))
            mundo.fill(WHITE, (int(x) + 6, int(y) - 2, 6, 4))
        surface.blit(pixelar(mundo, PIXEL_BONUS), (0, 0))

        neon.franjas_cine(surface, self.t / 40, NARANJA, alto=40)
        if self.t > 70:
            fuente = get_font(64, bold=True)
            for i, letra_color in enumerate((VIOLETA, NARANJA)):
                txt = fuente.render("¡FELIZ HALLOWEEN!", True, letra_color)
                dy = math.sin(self.t * 0.08) * 6
                surface.blit(txt, (GAME_WIDTH // 2 - txt.get_width() // 2 + (4 - i * 4), 70 + dy + (4 - i * 4)))
        if self.t > 120:
            fuente = get_font(28, bold=True)
            caja = pygame.Rect(0, 0, fuente.size(self.MENSAJE)[0] + 60, 64)
            caja.center = (GAME_WIDTH // 2, 186)
            neon.panel(surface, caja, NARANJA, self.t, halo=False)
            letras = min(len(self.MENSAJE), max(0, self.t - 130) // 3)
            texto = fuente.render(self.MENSAJE[:letras], True, WHITE)
            surface.blit(texto, (caja.x + 30, caja.centery - texto.get_height() // 2))
        if self.t > 260 and (self.t // 30) % 2 == 0:
            neon.cinta(surface, "ENTER para continuar", NARANJA, (GAME_WIDTH // 2, GAME_HEIGHT - 64), tam=14)
        neon.scanlines(surface)
        if self.t < self.FUNDIDO:
            neon.velo(surface, WHITE, 255 * (1 - self.t / self.FUNDIDO))
        restante = self.fin - self.t
        if restante < self.FUNDIDO:
            neon.velo(surface, NEGRO, 255 * (1 - max(0, restante) / self.FUNDIDO))


def icono_final():
    """Icono del panel de la victoria final de esta ruta."""
    return sprite_halloween("calabaza", 0, 3)
