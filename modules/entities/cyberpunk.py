"""
Ruta secreta cyberpunk del jefe bonus. Al caer el mega-jefe, la
cinematica de la VICTORIA falsa a veces es hackeada (ver
_cinematica_victoria_falsa en main.py): llueve codigo, el glitch se vuelve
cian/magenta/amarillo y "ACCESO CONCEDIDO". Despues, en una ciudad de neon
bajo la lluvia, llegan tres jefes (cada uno con su cinematica de entrada,
ver cyberpunk_cine.py):

  1. NETRUNNER FANTASMA: hacker encapuchado; se teletransporta en glitch,
     tira daemons que persiguen, muros de firewall con un hueco, lluvia
     de codigo por columnas y un quickhack que fija la mira en la nave.
  2. TARANTULA-9: araña mecanica; camina por arriba, dispara con sus dos
     cañones, lanza minas, misiles teledirigidos, barre con un laser y
     salta encima de la nave.
  3. KAISER CROMADO: cyborg de cromo; overclock (embestidas con estela),
     cañon de riel en una columna y puños cohete.

Al caer el Kaiser, la cinematica de la Luna (cyberpunk_cine.CinematicaLuna)
y la victoria de verdad al costado. Mismo estilo e interfaz de jefe que
halloween.py (JefeHalloweenBase), asi main.py los trata igual."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.entities.nyan_boss import BalaPixel, PIXEL_BONUS, _anillo, _apuntada, _blit_centrado, _lanzar_en_arco
from modules.entities.halloween import JefeHalloweenBase, _contornear, _desde_texto, _hitbox


NEGRO = (0, 0, 0)
CONTORNO = (10, 8, 22)
CIAN = (0, 240, 255)
CIAN_OSCURO = (0, 130, 170)
MAGENTA = (255, 40, 170)
MAGENTA_OSCURO = (150, 20, 100)
AMARILLO = (252, 238, 10)
AMARILLO_OSCURO = (180, 150, 0)
ROJO = (255, 50, 70)
ROJO_OSCURO = (150, 14, 40)
VERDE_CODIGO = (80, 255, 150)
CROMO = (210, 220, 240)
CROMO_MEDIO = (140, 150, 182)
CROMO_OSCURO = (70, 76, 112)

PALABRAS_CYBER = (
    "BREACH PROTOCOL", "ACCESO CONCEDIDO", "ICE ROTO", "DAEMON INSTALADO", "NETRUN.EXE",
    "JACK IN", "> sudo spawn boss", "CHROME", "OVERCLOCK", "NEO CIUDAD", "SIN SEÑAL",
    "0xC0FFEE", "FIREWALL DOWN", "CYBER", "RUN.EXE", "TRACE: 99%", "WAKE UP",
    "SISTEMA COMPROMETIDO", "LUNA.DAT", "UPLOAD", "ROOT", "KERNEL PANIC",
)
COLORES_CYBER = (CIAN, MAGENTA, AMARILLO, VERDE_CODIGO, WHITE)


# ------------------------------------------------------------------ arte

def _espejar(mitades):
    """Filas escritas solo por la mitad izquierda: las completa en espejo."""
    return tuple(m + m[::-1] for m in mitades)


_PALETA_NETRUNNER = {
    'K': CONTORNO, 'H': (44, 32, 76), 'h': (86, 66, 138), 'S': (232, 196, 178), 's': (196, 150, 140),
    'V': CIAN, 'v': CIAN_OSCURO, 'W': WHITE, 'J': (28, 24, 48), 'j': (64, 56, 104),
    'Y': AMARILLO, 'C': MAGENTA,
}
_NETRUNNER = _espejar((
    "..........KKKK",
    "........KKHHHH",
    ".......KHHHhhh",
    "......KHHhhHHH",
    ".....KHHhHHKKK",
    ".....KHhHHKSSS",
    "....KHHhHKSSSS",
    "....KHhHKVVVVV",
    "....KHhHKVVVVV",
    "....KHhHKvvvvv",
    "....KHhHKSSSSS",
    "....KHHhHKSSsK",
    ".....KHhHHKsSS",
    ".....KHHhHHKKK",
    "....KJJHHhHHYY",
    "...KJjJJHHHHYK",
    "..KJjJJJJJJJJY",
    "..KJjJJJJCJJJJ",
    ".KJjJJJJJCJJJJ",
    ".KJjJKJJJJCJJY",
    ".KJjK.KJJJJCJY",
    ".KSSK.KJJJJJCC",
    ".KSSK.KJJJJJJJ",
    "..KK..KJjJJJJJ",
    "......KJjJJJJJ",
    "......KJjJJJYY",
    ".......KJjJJJJ",
    ".......KJJjJJJ",
    "........KJJjJJ",
    "........KJJJjJ",
    ".........KJJJJ",
    ".........KJJJJ",
    "..........KJJK",
    "..........KJK.",
    "...........K..",
))


def _arte_netrunner(cuadro):
    """Netrunner Fantasma (28x35): capucha, visor cian y abrigo con cables
    magenta. cuadro 0/1: el brillo del visor barre de lado a lado;
    2: furioso (visor rojo)."""
    paleta = dict(_PALETA_NETRUNNER)
    if cuadro == 2:
        paleta['V'], paleta['v'] = ROJO, ROJO_OSCURO
    s = _desde_texto(_NETRUNNER, paleta)
    brillo = 10 if cuadro != 1 else 16
    s.set_at((brillo, 7), WHITE)
    s.set_at((brillo + 1, 7), WHITE)
    return s


_MITAD_ARACNIDO = (
    "......KKKKKK",
    "....KKMMMMMM",
    "...KMMmmmmMM",
    "..KMMmYYYYmM",
    "..KMmMMMMMMM",
    ".KMMmMMKKKKK",
    ".KMmMMKGGGGG",
    ".KMmMKGRGGRG",
    ".KMmMKGGRGGG",
    ".KMMmMKGGGGG",
    "..KMMmMKKKKK",
    "..KMMMmmmmmm",
    "...KMMMCCMMM",
    "....KKMMMMMM",
    "......KKKMMM",
    ".........KKK",
)


def _arte_tarantula(cuadro):
    """Tarantula-9 (72x44): abdomen con franjas de peligro, cabeza blindada
    con seis ojos rojos y ocho patas articuladas. cuadro = paso (0..3)
    + 4 si esta furiosa (los ojos brillan blancos/rojos)."""
    paso, furiosa = cuadro % 4, cuadro >= 4
    s = pygame.Surface((72, 44), pygame.SRCALPHA)
    metal, metal_oscuro, articulacion = (96, 100, 132), (52, 54, 78), AMARILLO
    # patas: cuatro por lado, cadera -> rodilla (arriba) -> pie (abajo)
    for lado in (-1, 1):
        for i in range(4):
            fase = paso * math.pi / 2 + i * math.pi / 2 + (0 if lado < 0 else math.pi)
            levanta = max(0.0, math.sin(fase)) * 3
            cadera = (36 + lado * 9, 17 + i * 3)
            rodilla = (36 + lado * (17 + i * 3), 6 + i * 3 - levanta)
            pie = (36 + lado * (24 + i * 4) + math.cos(fase) * 1.5, 40 - i * 2 - levanta)
            pygame.draw.line(s, metal_oscuro, cadera, rodilla, 3)
            pygame.draw.line(s, metal_oscuro, rodilla, pie, 3)
            pygame.draw.line(s, metal, cadera, rodilla, 1)
            pygame.draw.line(s, metal, rodilla, pie, 1)
            s.fill(articulacion, (int(rodilla[0]) - 1, int(rodilla[1]) - 1, 2, 2))
            s.fill(CROMO, (int(pie[0]) - 1, int(pie[1]), 3, 2))
    # abdomen detras de la cabeza
    pygame.draw.ellipse(s, (40, 38, 60), (22, 0, 28, 20))
    for k in range(3):
        pygame.draw.line(s, AMARILLO if k % 2 == 0 else NEGRO, (27 + k * 2, 3 + k * 2), (45 - k * 2, 3 + k * 2), 2)
    pygame.draw.ellipse(s, (80, 82, 110), (25, 1, 22, 6))
    paleta = {'K': CONTORNO, 'M': (120, 124, 160), 'm': (70, 72, 104), 'Y': AMARILLO, 'G': (22, 12, 30),
              'R': WHITE if furiosa and paso % 2 else ROJO, 'C': CIAN}
    cabeza = _desde_texto(_espejar(_MITAD_ARACNIDO), paleta)
    s.blit(cabeza, (24, 12))
    # cañones a los costados de la cabeza
    for lado in (-1, 1):
        x = 36 + lado * 13 - (3 if lado < 0 else 0)
        s.fill(CONTORNO, (x - 1, 22, 5, 11))
        s.fill((60, 62, 90), (x, 22, 3, 10))
        s.fill(MAGENTA if furiosa else CIAN, (x, 31, 3, 2))
    return _contornear(s, CONTORNO, s.get_size())


def _arte_kaiser(cuadro):
    """Kaiser Cromado (48x52): cyborg de cromo con cresta magenta, visor
    amarillo, nucleo rojo en el pecho y el brazo derecho hecho cañon.
    cuadro: bit 0 = visor encendido a pleno, bit 1 = sin puños (los
    lanzo), bit 2 = al rojo vivo (furioso)."""
    visor, sin_punos, caliente = cuadro & 1, cuadro & 2, cuadro & 4
    claro, medio, oscuro = CROMO, CROMO_MEDIO, CROMO_OSCURO
    if caliente:
        claro, medio, oscuro = (255, 196, 170), (220, 110, 96), (130, 40, 54)
    s = pygame.Surface((48, 52), pygame.SRCALPHA)
    # piernas
    for x0 in (14, 27):
        s.fill(medio, (x0, 32, 7, 10))
        s.fill(claro, (x0 + 1, 32, 2, 10))
        s.fill(oscuro, (x0 - 1, 41, 9, 3))
        s.fill(medio, (x0, 44, 7, 6))
        s.fill(oscuro, (x0 - 1, 49, 9, 3))
    # cadera y cinturon
    s.fill(oscuro, (14, 28, 20, 5))
    for x in range(16, 33, 4):
        s.fill(CIAN, (x, 30, 2, 1))
    # torso en trapecio
    pygame.draw.polygon(s, medio, ((7, 13), (40, 13), (34, 29), (13, 29)))
    pygame.draw.polygon(s, claro, ((9, 14), (23, 14), (22, 27), (15, 27)))
    pygame.draw.line(s, oscuro, (24, 14), (24, 28))
    for y in (20, 24):
        pygame.draw.line(s, oscuro, (14, y), (34, y))
    pygame.draw.circle(s, ROJO, (24, 20), 3)
    s.set_at((24, 20), WHITE)
    s.set_at((23, 19), WHITE)
    # hombreras
    for x0 in (2, 34):
        pygame.draw.ellipse(s, medio, (x0, 10, 12, 10))
        pygame.draw.ellipse(s, claro, (x0 + 2, 11, 7, 4))
        s.fill(AMARILLO, (x0 + 1, 17, 10, 1))
    # brazo izquierdo y puño
    s.fill(medio, (5, 20, 6, 12))
    s.fill(claro, (6, 20, 2, 12))
    if not sin_punos:
        s.fill(claro, (3, 32, 10, 7))
        s.fill(oscuro, (3, 35, 10, 1))
        s.fill(medio, (11, 32, 2, 7))
    else:
        s.fill(MAGENTA, (5, 32, 6, 2))
    # brazo derecho: cañon
    s.fill(oscuro, (36, 20, 9, 18))
    s.fill(medio, (37, 20, 3, 18))
    s.fill(CONTORNO, (37, 37, 7, 2))
    s.fill(CIAN, (38, 38, 5, 2))
    if not sin_punos:
        s.fill(claro, (35, 25, 3, 5))  # puño montado al costado del cañon
    # cabeza, visor, rejilla y cresta
    s.fill(oscuro, (21, 11, 7, 3))
    s.fill(medio, (19, 3, 11, 9))
    s.fill(claro, (20, 3, 4, 8))
    s.fill(AMARILLO if visor else AMARILLO_OSCURO, (19, 6, 11, 2))
    if visor:
        s.fill(WHITE, (26, 6, 2, 1))
    for x in range(21, 28, 2):
        s.fill(oscuro, (x, 9, 1, 3))
    pygame.draw.polygon(s, MAGENTA, ((23, 3), (25, 3), (25, 0), (23, 1)))
    s.fill(MAGENTA_OSCURO, (24, 0, 1, 3))
    return _contornear(s, CONTORNO, s.get_size())


_LUCY_PALETA = {
    'K': (14, 10, 24), 'H': (238, 238, 252), 'h': (186, 194, 232), 'T': (130, 224, 255), 't': (255, 150, 226),
    'S': (252, 222, 206), 's': (226, 180, 172), 'E': (226, 40, 86), 'B': (26, 24, 38), 'b': (64, 58, 86),
    'W': (242, 242, 250), 'w': (184, 190, 212), 'R': (232, 44, 76), 'G': (70, 70, 92),
}
_LUCY_LADO = (
    "....KKKKKK........",
    "...KHHHHHHK.......",
    "..KHHHHHHHHK......",
    "..KHHHHHHHHHK.....",
    ".KHHhHHHHHHHK.....",
    ".KHHhHHHSSSSK.....",
    ".KHhHHHSESSSK.....",
    ".KHhHHHSSSSsK.....",
    ".KThHHHKSSSK......",
    ".KTtHTKKSsK.......",
    "..KtTtKSSK........",
    "...KKKWWWK........",
    "...KWWWWWWWK......",
    "..KWWWWWWWWK......",
    "..KWwWWWWBBK......",
    "..KWwWWWBBBK......",
    "..KWwWWKBBBK......",
    "..KWwWWKBBBK......",
    "..KWWWKSKBBK......",
    "...KKKKSKBBK......",
    "....KBBBBBBK......",
    "....KBBRRBBK......",
    "....KBBBBBBK......",
)
_LUCY_PIERNAS = (
    (   # paso largo
        "....KBBBKBBK......",
        "....KBBK.KBBK.....",
        "...KBBK..KBBK.....",
        "...KBBK...KBBK....",
        "..KGGK....KGGK....",
        "..KGGK.....KGGK...",
        ".KGGGK.....KGGGK..",
        ".KKKKK.....KKKKK..",
    ),
    (   # piernas juntas
        "....KBBBBBK.......",
        "....KBBKBBK.......",
        "....KBBKBBK.......",
        "....KBBKBBK.......",
        "....KGGKGGK.......",
        "....KGGKGGK.......",
        "....KGGKGGGK......",
        "....KKKKKKKK......",
    ),
)
_LUCY_ESPALDA = (
    "....KKKKKKKK......",
    "...KHHHHHHHHK.....",
    "..KHHHHHHHHHHK....",
    "..KHHhHHHHhHHK....",
    "..KHHhHHHHhHHK....",
    "..KHhHHHHHHhHK....",
    "..KHhHHHHHHhHK....",
    "..KHhHHHHHHhHK....",
    "..KThHHHHHHhTK....",
    "..KTtTHHHHTtTK....",
    "...KtTtKKtTtK.....",
    "....KKKSSKKK......",
    "..KKWWWWWWWWKK....",
    ".KWWWWWWWWWWWWK...",
    ".KWwWWWWWWWWwWK...",
    ".KWwWWWWWWWWwWK...",
    ".KWwWWWWWWWWwWK...",
    ".KSKWWWWWWWWKSK...",
    ".KSKKWWWWWWKKSK...",
    "..K.KBBBBBBK.K....",
    "....KBBBBBBK......",
    "....KBRRRRBK......",
    "....KBBBBBBK......",
    "....KBBKKBBK......",
    "....KBBKKBBK......",
    "....KBBKKBBK......",
    "....KBBKKBBK......",
    "....KGGKKGGK......",
    "....KGGKKGGK......",
    "...KGGGKKGGGK.....",
    "...KKKKKKKKKK.....",
)


def _arte_lucy(cuadro):
    """Lucy (fan art, 18x31): pelo blanco en bob con puntas cian y rosa,
    delineado rojo, traje negro y chaqueta blanca. cuadro 0/1: caminando
    de perfil (mirando a la derecha); 2: de espaldas, mirando la Tierra."""
    if cuadro == 2:
        filas = _LUCY_ESPALDA
    else:
        filas = _LUCY_LADO + _LUCY_PIERNAS[cuadro]
    return _desde_texto(filas, _LUCY_PALETA)


def _arte_daemon(cuadro):
    """Daemon (9x9): rombo de ICE con un ojo que parpadea."""
    s = pygame.Surface((9, 9), pygame.SRCALPHA)
    pygame.draw.polygon(s, MAGENTA, ((4, 0), (8, 4), (4, 8), (0, 4)))
    pygame.draw.polygon(s, MAGENTA_OSCURO, ((4, 2), (6, 4), (4, 6), (2, 4)))
    s.fill(WHITE if cuadro else AMARILLO, (3, 3, 3, 3))
    return s


def _arte_misil(cuadro):
    """Misil (5x12) apuntando hacia arriba, con llama que titila."""
    s = pygame.Surface((5, 12), pygame.SRCALPHA)
    s.fill(CROMO, (1, 1, 3, 7))
    s.fill(ROJO, (2, 0, 1, 2))
    s.fill(AMARILLO, (0, 6, 1, 3))
    s.fill(AMARILLO, (4, 6, 1, 3))
    s.fill((255, 160, 40), (1, 8, 3, 2 + cuadro))
    s.fill(WHITE, (2, 8, 1, 1))
    return s


def _arte_mina(cuadro):
    s = pygame.Surface((9, 9), pygame.SRCALPHA)
    pygame.draw.circle(s, (70, 72, 100), (4, 4), 4)
    for x, y in ((4, 0), (0, 4), (8, 4), (4, 8)):
        s.set_at((x, y), AMARILLO)
    s.fill(ROJO if cuadro else (120, 20, 30), (3, 3, 3, 3))
    return s


def _arte_puno(cuadro):
    """Puño cohete del Kaiser (12x16), cerrado y con la llama atras (abajo
    del sprite: el puño "mira" hacia arriba y se rota hacia donde va)."""
    s = pygame.Surface((12, 16), pygame.SRCALPHA)
    s.fill(CROMO, (1, 0, 10, 8))
    s.fill(CROMO_OSCURO, (1, 3, 10, 1))
    s.fill(CROMO_MEDIO, (9, 0, 2, 8))
    s.fill(CROMO_OSCURO, (2, 8, 8, 2))
    s.fill((255, 170, 40), (3, 10, 6, 3 + cuadro))
    s.fill(AMARILLO, (4, 10, 4, 2))
    return _contornear(s, CONTORNO, s.get_size())


def _arte_bit(cuadro):
    """Un "1" o un "0" (3x5) de la lluvia de codigo."""
    s = pygame.Surface((3, 5), pygame.SRCALPHA)
    if cuadro:
        s.fill(VERDE_CODIGO, (1, 0, 1, 5))
        s.set_at((0, 1), VERDE_CODIGO)
    else:
        s.fill(VERDE_CODIGO, (0, 0, 3, 5))
        s.fill((0, 0, 0, 0), (1, 1, 1, 3))
    return s


_ARTES = {
    "netrunner": _arte_netrunner, "tarantula": _arte_tarantula, "kaiser": _arte_kaiser,
    "lucy": _arte_lucy, "daemon": _arte_daemon, "misil": _arte_misil, "mina": _arte_mina,
    "puno": _arte_puno, "bit": _arte_bit,
}
_CACHE = {}


def sprite_cyber(nombre, cuadro, escala, voltear=False, blanco=False, angulo=0):
    """Como halloween.sprite_halloween (arte agrandado sin filtrado,
    cacheado); angulo (grados, de a 15) lo rota despues de agrandar."""
    angulo = int(round(angulo / 15.0)) * 15 % 360
    clave = (nombre, cuadro, escala, voltear, blanco, angulo)
    surf = _CACHE.get(clave)
    if surf is None:
        arte = _ARTES[nombre](cuadro)
        surf = pygame.transform.scale(arte, (arte.get_width() * escala, arte.get_height() * escala))
        if voltear:
            surf = pygame.transform.flip(surf, True, False)
        if blanco:
            surf = surf.copy()
            surf.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
        if angulo:
            surf = pygame.transform.rotate(surf, angulo)
        _CACHE[clave] = surf
    return surf


# ------------------------------------------------------------- escenario

class FondoCyber:
    """Ciudad de neon de noche bajo la lluvia: cielo violeta que se vuelve
    magenta en el horizonte, una luna enorme y palida (la del final),
    rascacielos con ventanas que titilan y carteles, autos voladores y
    lluvia en diagonal. Misma interfaz que nyan_boss.FondoPixel."""

    def __init__(self):
        self.t = 0
        rng = random.Random(77)
        self.estrellas = [(rng.randrange(GAME_WIDTH), rng.randrange(int(GAME_HEIGHT * 0.45))) for _ in range(30)]
        self.ciudad = self._ciudad(rng)
        self.ventanas = []
        for capa, (x0, ancho, alto) in self._edificios_cerca:
            for wy in range(GAME_HEIGHT - alto + 8, GAME_HEIGHT - 6, 12):
                for wx in range(x0 + 6, x0 + ancho - 6, 10):
                    if rng.random() < 0.45:
                        self.ventanas.append((wx, wy, rng.choice((CIAN, AMARILLO, MAGENTA, (255, 200, 140))),
                                              rng.randrange(400)))
        self.gotas = [[random.uniform(0, GAME_WIDTH), random.uniform(0, GAME_HEIGHT), random.uniform(9, 14)]
                      for _ in range(45)]
        self.autos = []

    def _ciudad(self, rng):
        """Silueta fija (cielo, luna, edificios lejanos y cercanos)."""
        s = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        bandas = ((14, 6, 34), (22, 8, 48), (34, 10, 62), (52, 12, 76), (78, 16, 92), (110, 22, 104))
        alto_banda = GAME_HEIGHT // len(bandas)
        for i, color in enumerate(bandas):
            s.fill(color, (0, i * alto_banda, GAME_WIDTH, alto_banda + 1))
        # luna grande y palida detras de los edificios
        lx, ly = 210, 150
        pygame.draw.circle(s, (70, 40, 110), (lx, ly), 92)
        pygame.draw.circle(s, (226, 220, 246), (lx, ly), 84)
        for dx, dy, r in ((-26, -18, 16), (30, 22, 12), (8, -40, 8), (-34, 34, 9), (40, -14, 6)):
            pygame.draw.circle(s, (196, 190, 224), (lx + dx, ly + dy), r)
        # rascacielos lejanos
        x = -20
        while x < GAME_WIDTH:
            ancho = rng.randint(40, 90)
            alto = rng.randint(140, 300)
            s.fill((30, 12, 54), (x, GAME_HEIGHT - alto, ancho, alto))
            if rng.random() < 0.4:
                s.fill((30, 12, 54), (x + ancho // 2 - 2, GAME_HEIGHT - alto - 30, 4, 30))  # antena
                s.fill(ROJO, (x + ancho // 2 - 2, GAME_HEIGHT - alto - 32, 4, 4))
            for wy in range(GAME_HEIGHT - alto + 10, GAME_HEIGHT, 16):
                for wx in range(x + 6, x + ancho - 6, 12):
                    if rng.random() < 0.25:
                        s.fill((90, 60, 140), (wx, wy, 4, 4))
            x += ancho + rng.randint(4, 20)
        # rascacielos cercanos (las ventanas que titilan se dibujan aparte)
        self._edificios_cerca = []
        x = -10
        while x < GAME_WIDTH:
            ancho = rng.randint(70, 130)
            alto = rng.randint(90, 200)
            s.fill((12, 6, 24), (x, GAME_HEIGHT - alto, ancho, alto))
            s.fill((60, 24, 90), (x, GAME_HEIGHT - alto, ancho, 3))
            self._edificios_cerca.append((0, (x, ancho, alto)))
            x += ancho + rng.randint(10, 40)
        # carteles de neon verticales
        self.carteles = []
        for x0, ancho, alto in [e for _, e in self._edificios_cerca][1::2]:
            self.carteles.append((x0 + ancho - 14, GAME_HEIGHT - alto + 14, rng.choice((CIAN, MAGENTA, AMARILLO)),
                                  rng.randrange(200)))
        return s

    def update(self):
        self.t += 1
        for g in self.gotas:
            g[0] -= g[2] * 0.3
            g[1] += g[2]
            if g[1] > GAME_HEIGHT:
                g[0], g[1] = random.uniform(0, GAME_WIDTH + 100), random.uniform(-40, 0)
        if self.t % 150 == 0:
            lado = random.choice((-1, 1))
            self.autos.append({'x': -40 if lado > 0 else GAME_WIDTH + 40, 'y': random.uniform(300, 430),
                               'vx': lado * random.uniform(3, 5), 'color': random.choice((CIAN, MAGENTA, AMARILLO))})
        for a in self.autos:
            a['x'] += a['vx']
        self.autos = [a for a in self.autos if -60 < a['x'] < GAME_WIDTH + 60]

    def draw(self, surface):
        surface.blit(self.ciudad, (0, 0))
        p = PIXEL_BONUS
        for i, (x, y) in enumerate(self.estrellas):
            if ((self.t // 20) + i) % 4:
                surface.fill((200, 190, 255), (x // p * p, y // p * p, p, p))
        for a in self.autos:
            x, y = int(a['x']), int(a['y'])
            surface.fill((40, 40, 70), (x - 14, y - 4, 28, 8))
            surface.fill(a['color'], (x - 14, y + 4, 28, 2))
            frente = 1 if a['vx'] > 0 else -1
            surface.fill(WHITE, (x + frente * 14 - 2, y - 2, 4, 4))
            surface.fill(ROJO, (x - frente * 14 - 2, y - 2, 4, 4))
        for wx, wy, color, fase in self.ventanas:
            if ((self.t + fase) // 90) % 5:
                surface.fill(color, (wx, wy, 4, 4))
        for x, y, color, fase in self.carteles:
            if ((self.t + fase) // 12) % 9:
                surface.fill(color, (x, y, 6, 50))
                surface.fill(WHITE, (x + 2, y + 4, 2, 42))
        for x, y, v in self.gotas:
            surface.fill((120, 150, 220), (int(x) // 4 * 4, int(y), 4, int(v)))


# ------------------------------------------------------------- proyectiles

class Daemon(BalaPixel):
    """Rombo de ICE que persigue un rato a la nave y despues sigue de largo."""

    def __init__(self, x, y, vx, vy, ship, persigue=80):
        super().__init__(x, y, vx, vy, forma="sprite", sprite=sprite_cyber("daemon", 0, 3), radio=11)
        self.ship = ship
        self.persigue = persigue
        self.t = random.randrange(10)

    def update(self):
        self.t += 1
        if self.persigue > 0:
            self.persigue -= 1
            _girar_hacia(self, self.ship.x, self.ship.y, 0.05)
        self.sprite = sprite_cyber("daemon", (self.t // 6) % 2, 3)
        super().update()


class Misil(BalaPixel):
    """Misil teledirigido: sale hacia donde se lo lanza, gira hacia la nave
    durante `persigue` cuadros y despues sigue derecho."""

    def __init__(self, x, y, vx, vy, ship, persigue=90):
        super().__init__(x, y, vx, vy, forma="sprite", sprite=sprite_cyber("misil", 0, 3), radio=9)
        self.ship = ship
        self.persigue = persigue
        self.t = 0

    def update(self):
        self.t += 1
        if self.persigue > 0 and self.t > 12:
            self.persigue -= 1
            _girar_hacia(self, self.ship.x, self.ship.y, 0.06)
        angulo = -math.degrees(math.atan2(self.vy, self.vx)) - 90
        self.sprite = sprite_cyber("misil", (self.t // 4) % 2, 3, angulo=angulo)
        super().update()


class PunoCohete(BalaPixel):
    """Puño del Kaiser: sale disparado hacia donde estaba la nave."""

    def __init__(self, x, y, objetivo_x, objetivo_y, velocidad):
        a = math.atan2(objetivo_y - y, objetivo_x - x)
        super().__init__(x, y, math.cos(a) * velocidad, math.sin(a) * velocidad, forma="sprite",
                         sprite=sprite_cyber("puno", 0, 4), radio=20)
        self.t = 0

    def update(self):
        self.t += 1
        angulo = -math.degrees(math.atan2(self.vy, self.vx)) - 90
        self.sprite = sprite_cyber("puno", (self.t // 3) % 2, 4, angulo=angulo)
        super().update()


def _girar_hacia(bala, x, y, maximo):
    a = math.atan2(y - bala.y, x - bala.x)
    v = math.hypot(bala.vx, bala.vy)
    actual = math.atan2(bala.vy, bala.vx)
    dif = (a - actual + math.pi) % (2 * math.pi) - math.pi
    actual += max(-maximo, min(maximo, dif))
    bala.vx, bala.vy = math.cos(actual) * v, math.sin(actual) * v


def _bit(x, y, vy):
    return BalaPixel(x, y, 0, vy, forma="sprite", sprite=sprite_cyber("bit", random.randrange(2), 4), radio=9)


def _dibujar_mira(screen, x, y, radio, color, t, offset_x=0, offset_y=0):
    """Mira de quickhack: esquinas que giran y un punto en el centro."""
    x, y = int(x) + offset_x, int(y) + offset_y
    for k in range(4):
        a = t * 0.06 + k * math.pi / 2
        cx, cy = x + math.cos(a) * radio, y + math.sin(a) * radio
        for d in range(3):
            screen.fill(color, (int(cx + math.cos(a + 1.57) * d * 5) - 3, int(cy + math.sin(a + 1.57) * d * 5) - 3, 6, 6))
    screen.fill(color, (x - 3, y - 3, 6, 6))
    pygame.draw.circle(screen, color, (x, y), radio - 10, 2)


def _dibujar_glitch(screen, spr, x, y, intensidad, alfa=255):
    """El sprite cortado en franjas corridas al azar (aparece/desaparece)."""
    w, h = spr.get_size()
    alto = max(4, h // 8)
    x0, y0 = int(x) - w // 2, int(y) - h // 2
    for fy in range(0, h, alto):
        franja = spr.subsurface((0, fy, w, min(alto, h - fy))).copy()
        if alfa < 255:
            franja.set_alpha(alfa)
        dx = random.randint(-int(intensidad), int(intensidad)) if intensidad else 0
        screen.blit(franja, (x0 + dx, y0 + fy))


# ------------------------------------------------------------------ jefes

class NetrunnerBoss(JefeHalloweenBase):
    """Primer jefe cyberpunk. Flota encapuchado con pantallas holograficas
    en las manos; dispara rafagas de datos, suelta daemons que persiguen y
    se teletransporta en glitch (mientras esta cortado no recibe daño).
    Especiales en rotacion:
      - FIREWALL: muros de punta a punta que bajan con un solo hueco.
      - LLUVIA DE CODIGO: marca columnas y por ellas llueven unos y ceros.
      - QUICKHACK: una mira persigue a la nave, se fija y detona."""

    nombre = "NETRUNNER FANTASMA"
    hp_base = 950
    ESCALA = 4
    ANCHO_COLUMNA = 70

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = GAME_WIDTH / 2
        self.y = -160.0
        self.base_y = 160.0
        self.size = 56
        self.alto_sprite = 35 * self.ESCALA
        self.alfa = 1.0
        self.tele = None
        self.timer_tele = 220
        self.timer_datos = 60
        self.timer_daemons = 150
        self.hackea = 0

    def take_damage(self, amount=1):
        if self.alfa < 0.5:
            return  # en glitch: los disparos lo atraviesan
        super().take_damage(amount)

    def _teletransportar(self, x, y):
        self.tele = {'t': 0, 'x': x, 'y': y}

    def update(self, ship):
        self._tick_comun()
        v = self._vel()
        if self.hackea > 0:
            self.hackea -= 1
        if self.entrando:
            self.y += 6
            if self.y >= self.base_y:
                self.y = self.base_y
                self.entrando = False
            return []
        if self.tele is not None:
            tl = self.tele
            tl['t'] += 1
            if tl['t'] <= 16:
                self.alfa = 1 - tl['t'] / 16
            elif tl['t'] == 17:
                self.x, self.y = tl['x'], tl['y']
            else:
                self.alfa = min(1.0, (tl['t'] - 17) / 16)
                if self.alfa >= 1.0:
                    self.tele = None
            return []
        if self.especial is not None:
            return self._actualizar_especial(ship, v)
        self.y = self.base_y + math.sin(self.t * 0.05) * 14
        self.x += (ship.x - self.x) * 0.005 * v
        balas = []
        self.timer_especial -= 1
        self.timer_tele -= 1
        self.timer_datos -= 1
        self.timer_daemons -= 1
        if self.timer_especial <= 0:
            self.timer_especial = max(260, int((470 if not self.furioso else 350) / v))
            self._iniciar_especial(ship)
        elif self.timer_tele <= 0:
            self.timer_tele = max(120, int((250 if not self.furioso else 160) / v))
            self._teletransportar(random.uniform(140, GAME_WIDTH - 140), random.uniform(110, 220))
        elif self.timer_datos <= 0:
            self.timer_datos = max(36, int((80 if not self.furioso else 55) / v))
            self.hackea = 14
            n = 7 if self.furioso else 5
            for k in range(n):
                bala = _apuntada(self.x, self.y + 30, ship, 4.2 * math.sqrt(v), color=CIAN, tam=10)
                a = math.atan2(bala.vy, bala.vx) + (k - (n - 1) / 2) * 0.16
                vel = math.hypot(bala.vx, bala.vy)
                bala.vx, bala.vy = math.cos(a) * vel, math.sin(a) * vel
                balas.append(bala)
        elif self.timer_daemons <= 0:
            self.timer_daemons = max(90, int((200 if not self.furioso else 140) / v))
            self.hackea = 20
            for k in range(4 if self.furioso else 3):
                a = math.pi / 2 + (k - 1) * 0.7
                balas.append(Daemon(self.x, self.y + 20, math.cos(a) * 2.6 * math.sqrt(v),
                                    math.sin(a) * 2.6 * math.sqrt(v), ship))
        return balas

    def _iniciar_especial(self, ship):
        tipo = ("firewall", "codigo", "quickhack")[self.indice_especial % 3]
        self.indice_especial += 1
        if tipo == "firewall":
            self.especial = {'tipo': tipo, 't': 0, 'muros': 0}
            self._anunciar("¡FIREWALL!")
        elif tipo == "codigo":
            columnas = GAME_WIDTH // self.ANCHO_COLUMNA
            cerca = int(ship.x // self.ANCHO_COLUMNA)
            elegidas = {max(0, min(columnas - 1, cerca))}
            while len(elegidas) < (7 if self.furioso else 5):
                elegidas.add(random.randrange(columnas))
            self.especial = {'tipo': tipo, 't': 0, 'columnas': sorted(elegidas)}
            self._anunciar("¡LLUVIA DE CODIGO!")
        else:
            self.especial = {'tipo': tipo, 't': 0, 'mira': [ship.x, ship.y], 'veces': 0}
            self._anunciar("¡QUICKHACK!")

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        self.hackea = 4
        if e['tipo'] == "firewall":
            # cada muro: una fila de bloques de punta a punta con un hueco
            # de 4 bloques (3 furioso) cerca de la nave
            espera = max(50, int(75 / math.sqrt(v)))
            total = 4 if self.furioso else 3
            if e['t'] % espera == 1 and e['muros'] < total:
                e['muros'] += 1
                paso = 40
                bloques = GAME_WIDTH // paso + 1
                ancho_hueco = 3 if self.furioso else 4
                centro = int(ship.x // paso) + random.randint(-3, 3)
                inicio = max(0, min(bloques - ancho_hueco, centro - ancho_hueco // 2))
                for b in range(bloques):
                    if inicio <= b < inicio + ancho_hueco:
                        continue
                    balas.append(BalaPixel(b * paso + paso // 2, -20, 0, 3.0 * math.sqrt(v), color=MAGENTA,
                                           tam=16, radio=13))
            if e['muros'] >= total and e['t'] > total * espera + 30:
                self.especial = None
        elif e['tipo'] == "codigo":
            if 50 <= e['t'] < 120 and e['t'] % 5 == 0:
                for c in e['columnas']:
                    cx = c * self.ANCHO_COLUMNA + self.ANCHO_COLUMNA // 2 + random.randint(-14, 14)
                    balas.append(_bit(cx, -16, 6.0 * math.sqrt(v)))
            if e['t'] >= 150:
                self.especial = None
        else:
            # la mira sigue a la nave, se fija (parpadea) y detona
            fija = 80
            if e['t'] < fija:
                k = 0.07 * v
                e['mira'][0] += (ship.x - e['mira'][0]) * k
                e['mira'][1] += (ship.y - e['mira'][1]) * k
            elif e['t'] == fija + 30:
                mx, my = e['mira']
                balas.append(BalaPixel(mx, my, 0, 0, vida=10, radio=70, visible=False))
                balas += _anillo(mx, my, 12, 3.2 * math.sqrt(v), MAGENTA, 10, desfase=random.uniform(0, 1))
                e['estallido'] = 18
            elif e['t'] > fija + 50:
                e['veces'] += 1
                if self.furioso and e['veces'] < 2:
                    e['t'] = 0
                else:
                    self.especial = None
            if e.get('estallido'):
                e['estallido'] -= 1
        return balas

    def draw(self, screen, offset_x=0, offset_y=0):
        e = self.especial
        if e is not None and e['tipo'] == 'codigo' and e['t'] < 60 and (self.t // 5) % 2 == 0:
            for c in e['columnas']:
                capa = pygame.Surface((self.ANCHO_COLUMNA - 10, GAME_HEIGHT), pygame.SRCALPHA)
                capa.fill((80, 255, 150, 50))
                screen.blit(capa, (c * self.ANCHO_COLUMNA + 5 + offset_x, offset_y))
                for k in range(3):
                    cx = c * self.ANCHO_COLUMNA + self.ANCHO_COLUMNA // 2 + offset_x
                    screen.fill(VERDE_CODIGO, (cx - 12 + k * 4, 16 + k * 4 + offset_y, 24 - k * 8, 4))
        if e is not None and e['tipo'] == 'quickhack':
            mx, my = e['mira']
            if e['t'] < 80:
                _dibujar_mira(screen, mx, my, 46, CIAN, self.t, offset_x, offset_y)
            elif e['t'] < 110:
                if (self.t // 3) % 2 == 0:
                    _dibujar_mira(screen, mx, my, 40, ROJO, self.t * 3, offset_x, offset_y)
            elif e.get('estallido'):
                r = 80 - e['estallido'] * 2
                pygame.draw.circle(screen, MAGENTA, (int(mx) + offset_x, int(my) + offset_y), r, 8)
                pygame.draw.circle(screen, WHITE, (int(mx) + offset_x, int(my) + offset_y), max(4, r - 20), 4)
        cuadro = 2 if self.furioso else (self.t // 24) % 2
        spr = sprite_cyber("netrunner", cuadro, self.ESCALA, blanco=self.flash % 2 == 1)
        x, y = self.x + offset_x, self.y + offset_y
        # cables que cuelgan de la capucha y se mecen
        for lado in (-1, 1):
            for k in range(7):
                cx = x + lado * (44 + k * 2) + math.sin(self.t * 0.08 + k * 0.6) * k * 1.5
                cy = y - 30 + k * 12
                screen.fill(MAGENTA if k % 2 else MAGENTA_OSCURO, (int(cx) - 2, int(cy), 4, 12))
        # pantallas holograficas en las manos
        if self.hackea > 0 or self.furioso:
            for lado in (-1, 1):
                hx, hy = int(x + lado * 66) - 22, int(y + 20)
                capa = pygame.Surface((44, 30), pygame.SRCALPHA)
                capa.fill((0, 240, 255, 70))
                for ly in range(4, 28, 6):
                    capa.fill((0, 240, 255, 180), (4, ly, random.randint(10, 36), 2))
                screen.blit(capa, (hx, hy))
        if self.alfa < 1.0:
            _dibujar_glitch(screen, spr, x, y, 30 * (1 - self.alfa), int(255 * max(0.2, self.alfa)))
        else:
            _blit_centrado(screen, spr, x, y)


class TarantulaBoss(JefeHalloweenBase):
    """Segundo jefe cyberpunk: araña mecanica que camina por arriba
    disparando con sus dos cañones y tirando minas que estallan al caer.
    Especiales en rotacion:
      - ENJAMBRE DE MISILES: misiles que suben y despues persiguen.
      - LASER: carga un rayo desde los ojos y barre la pantalla.
      - SALTO: marca el lugar de la nave y cae encima (onda al aterrizar)."""

    nombre = "TARANTULA-9"
    hp_base = 1100
    ESCALA = 3

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = GAME_WIDTH / 2
        self.y = -150.0
        self.base_y = 140.0
        self.size = 80
        self.alto_sprite = 44 * self.ESCALA
        self.destino_x = self.x
        self.paso = 0.0
        self.timer_canon = 60
        self.timer_minas = 130
        self.timer_camina = 40
        self.dispara = 0

    def update(self, ship):
        self._tick_comun()
        balas = self._actualizar_bombas()
        v = self._vel()
        if self.dispara > 0:
            self.dispara -= 1
        if self.entrando:
            self.y += 6
            self.paso += 0.15
            if self.y >= self.base_y:
                self.y = self.base_y
                self.entrando = False
            return balas
        if self.especial is not None:
            return balas + self._actualizar_especial(ship, v)
        dx = self.destino_x - self.x
        if abs(dx) > 3:
            self.x += max(-2.4 * v, min(2.4 * v, dx))
            self.paso += 0.18 * v
        self.y = self.base_y + abs(math.sin(self.paso * math.pi / 2)) * 3
        self.timer_especial -= 1
        self.timer_canon -= 1
        self.timer_minas -= 1
        self.timer_camina -= 1
        if self.timer_camina <= 0:
            self.timer_camina = random.randint(70, 130)
            self.destino_x = max(140.0, min(GAME_WIDTH - 140.0, ship.x + random.uniform(-260, 260)))
        if self.timer_especial <= 0:
            self.timer_especial = max(260, int((460 if not self.furioso else 340) / v))
            self._iniciar_especial(ship)
        elif self.timer_canon <= 0:
            self.timer_canon = max(34, int((72 if not self.furioso else 48) / v))
            self.dispara = 10
            for lado in (-1, 1):
                for k in range(3):
                    bala = _apuntada(self.x + lado * 39, self.y + 50, ship, (4.0 + k * 0.6) * math.sqrt(v),
                                     color=AMARILLO, tam=10)
                    balas.append(bala)
        elif self.timer_minas <= 0:
            self.timer_minas = max(80, int((170 if not self.furioso else 120) / v))
            for dx in ((-140, 140) if not self.furioso else (-200, 0, 200)):
                balas.append(self._lanzar_bomba_cyber(ship.x + dx, ship.y - 20))
        return balas

    def _lanzar_bomba_cyber(self, objetivo_x, objetivo_y):
        bomba = _lanzar_en_arco(self.x, self.y + 30, objetivo_x, objetivo_y, sprite_cyber("mina", 1, 3), 13)
        self.bombas.append((bomba, objetivo_y, self._estallido))
        return bomba

    def _estallido(self, x, y):
        n = 12 if self.furioso else 9
        return _anillo(x, y, n, 2.6 * math.sqrt(self._vel()), AMARILLO, 10, desfase=random.uniform(0, 1))

    def _iniciar_especial(self, ship):
        tipo = ("misiles", "laser", "salto")[self.indice_especial % 3]
        self.indice_especial += 1
        if tipo == "misiles":
            self.especial = {'tipo': tipo, 't': 0}
            self._anunciar("¡ENJAMBRE DE MISILES!")
        elif tipo == "laser":
            izquierda = ship.x < self.x
            self.especial = {'tipo': tipo, 't': 0, 'pasadas': 0,
                             'a0': math.radians(150 if izquierda else 30), 'a1': math.radians(30 if izquierda else 150)}
            self._anunciar("¡LASER!")
        else:
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'aviso', 'objetivo': [ship.x, ship.y],
                             'origen': (self.x, self.y)}
            self._anunciar("¡SALTO MORTAL!")

    def _ojos(self):
        return self.x, self.y + 10

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "misiles":
            total = 8 if self.furioso else 6
            if e['t'] % 10 == 0 and e['t'] // 10 <= total:
                k = e['t'] // 10
                lado = -1 if k % 2 else 1
                balas.append(Misil(self.x + lado * 20, self.y - 20, lado * 2.2, -4.0 * math.sqrt(v), ship))
            if e['t'] >= total * 10 + 50:
                self.especial = None
        elif e['tipo'] == "laser":
            carga, barre = 55, max(60, int(100 / math.sqrt(v)))
            if e['t'] > carga:
                p = min(1.0, (e['t'] - carga) / barre)
                a = e['a0'] + (e['a1'] - e['a0']) * p
                ox, oy = self._ojos()
                d = 70
                while d < 900:
                    balas.append(_hitbox(ox + math.cos(a) * d, oy + math.sin(a) * d, 16))
                    d += 32
                e['angulo'] = a
                if p >= 1.0:
                    e['pasadas'] += 1
                    if self.furioso and e['pasadas'] < 2:
                        e['t'] = carga
                        e['a0'], e['a1'] = e['a1'], e['a0']
                    else:
                        self.especial = None
            else:
                e['angulo'] = e['a0']
        else:
            if e['fase'] == 'aviso':
                k = 0.05 * v
                e['objetivo'][0] += (ship.x - e['objetivo'][0]) * k
                e['objetivo'][1] += (max(GAME_HEIGHT * 0.5, ship.y) - e['objetivo'][1]) * k
                self.paso += 0.05
                if e['t'] >= 60:
                    e['fase'], e['t'] = 'salta', 0
                    e['origen'] = (self.x, self.y)
            elif e['fase'] == 'salta':
                dur = 40
                p = min(1.0, e['t'] / dur)
                ox, oy = e['origen']
                tx, ty = e['objetivo']
                self.x = ox + (tx - ox) * p
                self.y = oy + (ty - oy) * p - math.sin(math.pi * p) * 200
                if p >= 1.0:
                    e['fase'], e['t'] = 'aterriza', 0
                    balas.append(BalaPixel(self.x, self.y, 0, 0, vida=6, radio=75, visible=False))
                    balas += _anillo(self.x, self.y + 20, 16 if self.furioso else 12, 3.0 * math.sqrt(v), AMARILLO, 10,
                                     desfase=random.uniform(0, 1))
            elif e['fase'] == 'aterriza':
                if e['t'] >= 40:
                    e['fase'], e['t'] = 'vuelve', 0
            else:
                self.y += (self.base_y - self.y) * 0.08
                self.paso += 0.2
                if abs(self.y - self.base_y) < 4:
                    self.y = self.base_y
                    self.destino_x = self.x
                    self.especial = None
        return balas

    def draw(self, screen, offset_x=0, offset_y=0):
        e = self.especial
        if e is not None and e['tipo'] == 'salto' and e['fase'] in ('aviso', 'salta'):
            tx, ty = e['objetivo']
            if e['fase'] == 'salta' or (self.t // 5) % 2 == 0:
                capa = pygame.Surface((180, 180), pygame.SRCALPHA)
                pygame.draw.circle(capa, (255, 50, 70, 70), (90, 90), 80)
                pygame.draw.circle(capa, (255, 80, 90, 200), (90, 90), 80, 4)
                screen.blit(capa, (int(tx) - 90 + offset_x, int(ty) - 90 + offset_y))
        if e is not None and e['tipo'] == 'laser':
            ox, oy = self._ojos()
            a = e.get('angulo', e['a0'])
            fin = (ox + math.cos(a) * 1100 + offset_x, oy + math.sin(a) * 1100 + offset_y)
            inicio = (ox + offset_x, oy + offset_y)
            if e['t'] <= 55:
                if (self.t // 4) % 2 == 0:
                    pygame.draw.line(screen, ROJO, inicio, fin, 2)
            else:
                pygame.draw.line(screen, MAGENTA, inicio, fin, 26)
                pygame.draw.line(screen, ROJO, inicio, fin, 16)
                pygame.draw.line(screen, WHITE, inicio, fin, 6)
        paso = int(self.paso * 2) % 4
        spr = sprite_cyber("tarantula", paso + (4 if self.furioso else 0), self.ESCALA, blanco=self.flash % 2 == 1)
        _blit_centrado(screen, spr, self.x + offset_x, self.y + offset_y)
        if self.dispara > 0:
            for lado in (-1, 1):
                screen.fill(AMARILLO, (int(self.x + lado * 39) - 6 + offset_x, int(self.y + 46) + offset_y, 12, 12))


class KaiserBoss(JefeHalloweenBase):
    """Ultimo jefe cyberpunk: cyborg de cromo que flota con propulsores.
    Rafagas del cañon del brazo y anillos de los hombros. Especiales:
      - OVERCLOCK: marca un punto, embiste en linea recta dejando estelas
        (tres veces, cinco furioso) y vuelve.
      - CAÑON DE RIEL: se pone encima de la nave, carga y dispara un rayo
        que ocupa toda la columna.
      - PUÑOS COHETE: lanza los dos puños hacia la nave (furioso: dos tandas).
    Al bajar del 40% de vida se pone al rojo vivo."""

    nombre = "KAISER CROMADO"
    hp_base = 1500
    ESCALA = 4
    ANCHO_RIEL = 90

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad)
        self.x = GAME_WIDTH / 2
        self.y = -200.0
        self.base_y = 170.0
        self.size = 70
        self.alto_sprite = 52 * self.ESCALA
        self.timer_rafaga = 60
        self.timer_hombros = 140
        self.estelas = []
        self.sin_punos = 0
        self.dispara = 0

    def update(self, ship):
        self._tick_comun()
        v = self._vel()
        if self.dispara > 0:
            self.dispara -= 1
        if self.sin_punos > 0:
            self.sin_punos -= 1
        for est in self.estelas:
            est[2] -= 1
        self.estelas = [est for est in self.estelas if est[2] > 0]
        if self.entrando:
            self.y += 5
            if self.y >= self.base_y:
                self.y = self.base_y
                self.entrando = False
            return []
        if self.especial is not None:
            return self._actualizar_especial(ship, v)
        self.y = self.base_y + math.sin(self.t * 0.05) * 10
        self.x += (ship.x - self.x) * 0.008 * v
        balas = []
        self.timer_especial -= 1
        self.timer_rafaga -= 1
        self.timer_hombros -= 1
        if self.timer_especial <= 0:
            self.timer_especial = max(240, int((440 if not self.furioso else 320) / v))
            self._iniciar_especial(ship)
        elif self.timer_rafaga <= 0:
            self.timer_rafaga = max(30, int((70 if not self.furioso else 46) / v))
            self.dispara = 12
            cx, cy = self._boca_canon()
            for k in (-1, 0, 1):
                bala = _apuntada(cx, cy, ship, 5.0 * math.sqrt(v), color=AMARILLO, tam=12)
                a = math.atan2(bala.vy, bala.vx) + k * 0.12
                vel = math.hypot(bala.vx, bala.vy)
                bala.vx, bala.vy = math.cos(a) * vel, math.sin(a) * vel
                balas.append(bala)
        elif self.timer_hombros <= 0:
            self.timer_hombros = max(90, int((190 if not self.furioso else 130) / v))
            for lado in (-1, 1):
                balas += _anillo(self.x + lado * 72, self.y - 40, 10 if self.furioso else 7, 2.4 * math.sqrt(v),
                                 CIAN, 10, desfase=random.uniform(0, 1))
        return balas

    def _boca_canon(self):
        return self.x + 64, self.y + 50

    def _iniciar_especial(self, ship):
        tipo = ("overclock", "riel", "punos")[self.indice_especial % 3]
        self.indice_especial += 1
        if tipo == "overclock":
            self.especial = {'tipo': tipo, 't': 0, 'fase': 'apunta', 'embestidas': 0,
                             'destino': [ship.x, ship.y], 'origen': (self.x, self.y)}
            self._anunciar("¡OVERCLOCK!")
        elif tipo == "riel":
            self.especial = {'tipo': tipo, 't': 0, 'columna': ship.x}
            self._anunciar("¡CAÑON DE RIEL!")
        else:
            self.especial = {'tipo': tipo, 't': 0, 'tandas': 0}
            self._anunciar("¡PUÑOS COHETE!")

    def _actualizar_especial(self, ship, v):
        e = self.especial
        e['t'] += 1
        balas = []
        if e['tipo'] == "overclock":
            total = 5 if self.furioso else 3
            if e['fase'] == 'apunta':
                e['destino'][0] += (ship.x - e['destino'][0]) * 0.1
                e['destino'][1] += (ship.y - e['destino'][1]) * 0.1
                if e['t'] >= max(24, int(36 / math.sqrt(v))):
                    e['fase'], e['t'] = 'embiste', 0
                    e['origen'] = (self.x, self.y)
            elif e['fase'] == 'embiste':
                dur = 12
                p = min(1.0, e['t'] / dur)
                ox, oy = e['origen']
                dx, dy = e['destino']
                self.x = ox + (dx - ox) * p
                self.y = oy + (dy - oy) * p
                self.estelas.append([self.x, self.y, 18, random.choice((CIAN, MAGENTA))])
                balas.append(_hitbox(self.x, self.y, 60))
                if p >= 1.0:
                    e['embestidas'] += 1
                    balas += _anillo(self.x, self.y, 8, 2.6 * math.sqrt(v), MAGENTA, 10, desfase=random.uniform(0, 1))
                    if e['embestidas'] < total:
                        e['fase'], e['t'] = 'apunta', 0
                        # el siguiente destino arranca de la nave, sin seguirla del todo
                        e['destino'] = [ship.x + random.uniform(-60, 60), ship.y + random.uniform(-40, 20)]
                    else:
                        e['fase'], e['t'] = 'vuelve', 0
            else:
                self.x += (GAME_WIDTH / 2 - self.x) * 0.1
                self.y += (self.base_y - self.y) * 0.1
                if abs(self.y - self.base_y) < 4 and abs(self.x - GAME_WIDTH / 2) < 6:
                    self.especial = None
        elif e['tipo'] == "riel":
            carga = max(50, int(80 / math.sqrt(v)))
            if e['t'] < carga - 20:
                e['columna'] += (ship.x - e['columna']) * 0.08
            self.x += (e['columna'] - 64 - self.x) * 0.15
            self.dispara = 4
            if carga <= e['t'] < carga + 34:
                cx = e['columna']
                for y in range(int(self.y + 60), GAME_HEIGHT + 40, 40):
                    balas.append(_hitbox(cx, y, self.ANCHO_RIEL // 2 - 6))
            if e['t'] >= carga + 50:
                self.especial = None
        else:
            if e['t'] == 20:
                self.sin_punos = 90
                vel = 7.5 * math.sqrt(v)
                balas.append(PunoCohete(self.x - 72, self.y + 20, ship.x - 30, ship.y, vel))
                balas.append(PunoCohete(self.x + 60, self.y + 10, ship.x + 30, ship.y, vel))
            if e['t'] >= 70:
                e['tandas'] += 1
                if self.furioso and e['tandas'] < 2:
                    e['t'] = 0
                else:
                    self.especial = None
        return balas

    def draw(self, screen, offset_x=0, offset_y=0):
        e = self.especial
        if e is not None and e['tipo'] == 'overclock':
            # velo azul de "tiempo lento" y la linea punteada de la embestida
            capa = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            capa.fill((0, 60, 120, 40))
            screen.blit(capa, (0, 0))
            if e['fase'] == 'apunta':
                dx, dy = e['destino']
                pasos = 14
                for k in range(pasos):
                    if (k + self.t // 3) % 2:
                        px = self.x + (dx - self.x) * k / pasos + offset_x
                        py = self.y + (dy - self.y) * k / pasos + offset_y
                        screen.fill(MAGENTA, (int(px) - 4, int(py) - 4, 8, 8))
                _dibujar_mira(screen, dx, dy, 36, MAGENTA, self.t * 2, offset_x, offset_y)
        if e is not None and e['tipo'] == 'riel':
            cx = int(e['columna']) + offset_x
            carga = max(50, int(80 / math.sqrt(self._vel())))
            if e['t'] < carga:
                if (self.t // 4) % 2 == 0:
                    capa = pygame.Surface((self.ANCHO_RIEL, GAME_HEIGHT), pygame.SRCALPHA)
                    capa.fill((252, 238, 10, 60))
                    screen.blit(capa, (cx - self.ANCHO_RIEL // 2, offset_y))
                    screen.fill(AMARILLO, (cx - self.ANCHO_RIEL // 2, offset_y, 4, GAME_HEIGHT))
                    screen.fill(AMARILLO, (cx + self.ANCHO_RIEL // 2 - 4, offset_y, 4, GAME_HEIGHT))
            elif e['t'] < carga + 34:
                y0 = int(self.y + 50) + offset_y
                ancho = self.ANCHO_RIEL + random.randint(-8, 8)
                screen.fill(AMARILLO, (cx - ancho // 2, y0, ancho, GAME_HEIGHT))
                screen.fill(WHITE, (cx - ancho // 4, y0, ancho // 2, GAME_HEIGHT))
        caliente = 4 if self.furioso else 0
        sin_punos = 2 if self.sin_punos > 0 else 0
        visor = 1 if (self.t // 30) % 4 or self.dispara > 0 else 0
        spr = sprite_cyber("kaiser", visor | sin_punos | caliente, self.ESCALA, blanco=self.flash % 2 == 1)
        # estelas del overclock: copias del sprite tenidas que se apagan
        for ex, ey, vida, color in self.estelas:
            fantasma = sprite_cyber("kaiser", sin_punos | caliente, self.ESCALA, blanco=True).copy()
            fantasma.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MIN)
            fantasma.set_alpha(int(150 * vida / 18))
            _blit_centrado(screen, fantasma, ex + offset_x, ey + offset_y)
        # llamas de los propulsores de los pies
        x, y = self.x + offset_x, self.y + offset_y
        for lado in (-1, 1):
            largo = 18 + (self.t % 4) * 4
            fx = int(x + lado * 26)
            fy = int(y + self.alto_sprite // 2 - 4)
            screen.fill((255, 140, 40), (fx - 8, fy, 16, largo))
            screen.fill(AMARILLO, (fx - 4, fy, 8, largo - 6))
        _blit_centrado(screen, spr, x, y)
        if self.dispara > 0:
            cx, cy = self._boca_canon()
            screen.fill(AMARILLO, (int(cx) - 8 + offset_x, int(cy) - 4 + offset_y, 16, 16))
            screen.fill(WHITE, (int(cx) - 4 + offset_x, int(cy) + offset_y, 8, 8))


def icono_final():
    """Icono del panel de la victoria final de esta ruta (Lucy de espaldas)."""
    return sprite_cyber("lucy", 2, 2)
