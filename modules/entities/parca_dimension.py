"""
El desafio de la Parca: si te derrotan dos veces seguidas (reintentando),
en el GAME OVER aparece una calavera en "Intentar de Nuevo" y, si lo
eliges, en vez de una partida nueva viene esto (ver _reintentar en main.py):

  - CinematicaParcaLlega: la guadaña corta la pantalla de GAME OVER en dos,
    la Parca sale de la oscuridad, abre un portal que se traga la nave y
    te desafia en su dimension ("¡DUELO A MUERTE!").
  - ParcaDimension: el duelo, en FondoDimension (cielo rojo con un remolino
    y calaveras que flotan), con la nave cargada de todas las mejoras.
  - CinematicaParcaConquista: si te derrota, conquista la galaxia planeta
    por planeta antes del GAME OVER.
  - CinematicaParcaVencida: si la vences, su dimension se rompe y escapas.

Mismo estilo que halloween.py (arte pixel por codigo, textos nitidos)."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.systems import neon
from modules.entities.nyan_boss import PIXEL_BONUS, pixelar, _blit_centrado
from modules.entities.halloween import (
    ParcaBoss, sprite_halloween, NARANJA, VIOLETA, VIOLETA_CLARO, VERDE_TOXICO,
)

ROJO_SANGRE = (150, 10, 30)
ROJO_VIVO = (255, 50, 70)
NEGRO = (0, 0, 0)
FONDO_DIMENSION = ((20, 0, 6), (34, 2, 12), (52, 4, 20), (70, 8, 26))


def _velo(surface, color, alfa):
    neon.velo(surface, color, alfa)


def _globo(surface, texto, x, y):
    neon.globo(surface, texto, x, y, ROJO_VIVO, cola_derecha=False, tam=22)


class FondoDimension:
    """La dimension de la Parca: cielo rojo oscuro en bandas, un remolino
    de bloques que gira lento detras de todo, un ojo rojo gigante en el
    horizonte y calaveras que suben flotando. Interfaz de FondoPixel."""

    def __init__(self):
        self.t = 0
        self.calaveras = [self._calavera(random.uniform(0, GAME_HEIGHT)) for _ in range(9)]

    @staticmethod
    def _calavera(y):
        return {'x': random.uniform(20, GAME_WIDTH - 20), 'y': y, 'v': random.uniform(0.4, 1.0),
                'fase': random.uniform(0, 6.3), 'escala': random.choice((2, 3))}

    def update(self):
        self.t += 1
        for i, c in enumerate(self.calaveras):
            c['y'] -= c['v']
            c['x'] += math.sin(self.t * 0.02 + c['fase']) * 0.4
            if c['y'] < -30:
                self.calaveras[i] = self._calavera(GAME_HEIGHT + 30)

    def draw(self, surface):
        for i, color in enumerate(FONDO_DIMENSION):
            surface.fill(color, (0, i * GAME_HEIGHT // 4, GAME_WIDTH, GAME_HEIGHT // 4 + 1))
        cx, cy = GAME_WIDTH // 2, GAME_HEIGHT // 2 - 40
        p = PIXEL_BONUS * 2
        for brazo in range(4):
            for k in range(46):
                r = 14 + k * 9
                a = self.t * 0.004 + brazo * math.pi / 2 + k * 0.16
                x = cx + math.cos(a) * r
                y = cy + math.sin(a) * r * 0.6
                tono = max(0, 120 - k * 2)
                surface.fill((tono, 10, tono // 3 + 20), (int(x) // p * p, int(y) // p * p, p, p))
        # ojo gigante en el horizonte que parpadea de vez en cuando
        ojo_y = GAME_HEIGHT - 60
        abierto = (self.t % 400) > 12
        pygame.draw.ellipse(surface, (40, 0, 10), (cx - 170, ojo_y - 40, 340, 80))
        if abierto:
            pygame.draw.ellipse(surface, (110, 10, 30), (cx - 150, ojo_y - 30, 300, 60))
            mira = math.sin(self.t * 0.01) * 50
            pygame.draw.ellipse(surface, ROJO_VIVO, (cx - 26 + mira, ojo_y - 26, 52, 52))
            pygame.draw.ellipse(surface, NEGRO, (cx - 8 + mira, ojo_y - 20, 16, 40))
        else:
            surface.fill((110, 10, 30), (cx - 150, ojo_y - 2, 300, 4))
        for c in self.calaveras:
            spr = sprite_halloween("calavera", 1 if (self.t // 20) % 3 == 0 else 0, c['escala'])
            _blit_centrado(surface, spr, c['x'], c['y'])


class ParcaDimension(ParcaBoss):
    """La Parca en su propia dimension: menos vida que en la ruta de
    Halloween (la nave llega sin haber jugado una partida) pero mas rapida
    y enfurecida antes."""

    nombre = "LA PARCA"
    hp_base = 700
    UMBRAL_FURIA = 0.55

    def __init__(self, dificultad=1.0):
        super().__init__(dificultad * 1.1)
        self.name = "LA PARCA - SU DIMENSION"


class CinematicaParcaLlega:
    """GAME OVER -> la guadaña corta la pantalla en diagonal y las dos
    mitades se separan; la Parca sube desde la oscuridad ("¿Otra vez tu?",
    "Tu alma me pertenece."), abre un portal y la nave cae girando adentro.
    Destello y su dimension: "Bienvenido a mi dimension." / "Derrotame y
    seras libre." / "Pierde... y la galaxia sera mia." y "¡DUELO A MUERTE!".

    eventos: "corte", "risa", "portal", "llegada", "duelo" (sonidos en
    main.py); temblor como las otras cinematicas."""

    FUNDIDO = 30
    T_CORTE = 50
    T_SUBE = 90
    T_PORTAL = 250
    T_DIMENSION = 360
    T_DUELO = 600
    DURACION = 690

    def __init__(self, captura, sprite_nave):
        self.captura = captura
        self.sprite_nave = sprite_nave
        self.t = 0
        self.fin = self.DURACION
        self.eventos = []
        self.temblor = 0
        self.fondo = FondoDimension()
        # las dos mitades de la pantalla cortada (triangulos por la diagonal)
        self.mitades = []
        for puntos, direccion in ((((0, 0), (GAME_WIDTH, 0), (0, GAME_HEIGHT)), (-1, -1)),
                                  (((GAME_WIDTH, 0), (GAME_WIDTH, GAME_HEIGHT), (0, GAME_HEIGHT)), (1, 1))):
            pieza = captura.copy().convert_alpha()
            mascara = pygame.Surface(pieza.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(mascara, (255, 255, 255, 255), puntos)
            pieza.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.mitades.append((pieza, direccion))

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 40:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        if self.t >= self.T_DIMENSION:
            self.fondo.update()
        marcas = {self.T_CORTE: ("corte", 18), self.T_SUBE + 40: ("risa", 6), self.T_PORTAL: ("portal", 10),
                  self.T_DIMENSION: ("llegada", 20), self.T_DUELO: ("duelo", 22)}
        if self.t in marcas:
            evento, temblor = marcas[self.t]
            self.eventos.append(evento)
            self.temblor = temblor

    # ------------------------------------------------------------ dibujo
    def _vacio(self, surface):
        surface.fill((10, 0, 4))
        for i in range(40):
            a = i * 0.7 + self.t * 0.01
            r = (i * 37 + self.t * 2) % 600
            x = GAME_WIDTH // 2 + math.cos(a) * r
            y = GAME_HEIGHT // 2 + math.sin(a) * r * 0.6
            surface.fill((90, 0, 20), (int(x), int(y), 4, 4))

    def _portal(self, surface, cx, cy, k):
        for anillo in range(7):
            r = int((30 + anillo * 26) * k)
            if r <= 0:
                continue
            color = (VIOLETA, ROJO_VIVO, VIOLETA_CLARO)[anillo % 3]
            n = 18 + anillo * 4
            for i in range(n):
                a = 2 * math.pi * i / n + self.t * (0.05 + anillo * 0.01) * (1 if anillo % 2 else -1)
                neon.cuadro_pixel(surface, color, cx + math.cos(a) * r, cy + math.sin(a) * r * 0.55, 8)
        pygame.draw.ellipse(surface, NEGRO, (cx - 26 * k, cy - 16 * k, 52 * k, 32 * k))

    def draw(self, surface):
        t = self.t
        if t < self.T_DIMENSION:
            self._vacio(surface)
            if t < self.T_CORTE:
                surface.blit(self.captura, (0, 0))
                # la calavera del boton late cada vez mas
                _velo(surface, ROJO_SANGRE, 40 + t * 2)
                calavera = sprite_halloween("calavera", 1, 8 + t // 12)
                _blit_centrado(surface, calavera, GAME_WIDTH // 2, GAME_HEIGHT // 2)
            else:
                # la guadaña corto la pantalla: las mitades se separan y caen
                d = t - self.T_CORTE
                for pieza, (dx, dy) in self.mitades:
                    ox = dx * (d * 6 + d * d * 0.05)
                    oy = dy * (d * 4 + d * d * 0.08)
                    surface.blit(pieza, (int(ox), int(oy)))
                if d < 12:
                    pygame.draw.line(surface, WHITE, (GAME_WIDTH, -10), (-10, GAME_HEIGHT), 10 - d // 2)
            if t >= self.T_SUBE:
                # la Parca sube desde abajo y se queda flotando
                k = min(1.0, (t - self.T_SUBE) / 60)
                k = 1 - (1 - k) ** 3
                y = GAME_HEIGHT + 200 - k * (GAME_HEIGHT // 2 + 220) + math.sin(t * 0.05) * 10
                cuadro = 2 if (t // 8) % 3 == 0 else 0
                parca = sprite_halloween("parca", cuadro, 8)
                if t >= self.T_PORTAL:
                    # se corre a un costado para dejar ver el portal
                    p = min(1.0, (t - self.T_PORTAL) / 30)
                    _blit_centrado(surface, parca, GAME_WIDTH // 2 - 300 * p, y)
                else:
                    _blit_centrado(surface, parca, GAME_WIDTH // 2, y)
                if self.T_SUBE + 60 < t < self.T_SUBE + 120:
                    _globo(surface, "¿Otra vez tu?", GAME_WIDTH // 2 + 120, y - 150)
                elif self.T_SUBE + 120 <= t < self.T_PORTAL:
                    _globo(surface, "Tu alma me pertenece.", GAME_WIDTH // 2 + 120, y - 150)
            if t >= self.T_PORTAL:
                cx, cy = GAME_WIDTH // 2 + 180, GAME_HEIGHT // 2
                k = min(1.0, (t - self.T_PORTAL) / 40)
                self._portal(surface, cx, cy, k)
                if self.sprite_nave is not None:
                    # la nave entra en espiral, achicandose y girando
                    p = min(1.0, (t - self.T_PORTAL - 20) / 80) if t > self.T_PORTAL + 20 else 0.0
                    r = 260 * (1 - p)
                    a = p * 6 * math.pi
                    escala = max(0.05, 2 * (1 - p))
                    nave = pygame.transform.rotozoom(self.sprite_nave, math.degrees(a), escala)
                    _blit_centrado(surface, nave, cx + math.cos(a) * r, cy + 200 * (1 - p) + math.sin(a) * r * 0.3)
            restante = self.T_DIMENSION - t
            if restante < 16:
                _velo(surface, WHITE, 255 * (1 - restante / 16))
        else:
            mundo = pygame.Surface(surface.get_size())
            self.fondo.draw(mundo)
            parca = sprite_halloween("parca", 2 if (t // 10) % 2 else 0, 4)
            _blit_centrado(mundo, parca, GAME_WIDTH // 2, 170 + math.sin(t * 0.05) * 10)
            if self.sprite_nave is not None:
                nave = pygame.transform.scale(self.sprite_nave, (self.sprite_nave.get_width() * 2,
                                                                 self.sprite_nave.get_height() * 2))
                _blit_centrado(mundo, nave, GAME_WIDTH // 2, GAME_HEIGHT - 150)
            surface.blit(pixelar(mundo, PIXEL_BONUS), (0, 0))
            neon.franjas_cine(surface, (t - self.T_DIMENSION) / 30, ROJO_VIVO, alto=48)
            d = t - self.T_DIMENSION
            if d < 16:
                _velo(surface, WHITE, 255 * (1 - d / 16))
            if 20 < d < 90:
                neon.cinta(surface, "DIMENSION DE LA PARCA", ROJO_VIVO, (GAME_WIDTH // 2, 80), tam=20)
            frases = ((95, 145, "Bienvenido a mi dimension."), (145, 195, "Derrotame y seras libre."),
                      (195, 240, "Pierde... y la galaxia sera mia."))
            for ini, fin, frase in frases:
                if ini <= d < fin:
                    _globo(surface, frase, GAME_WIDTH // 2 + 60, 110)
            if t >= self.T_DUELO and (t // 5) % 4 != 0:
                tam = 80 + int(10 * math.sin(t * 0.3))
                neon.titulo(surface, "¡DUELO A MUERTE!", tam, ROJO_VIVO, GAME_WIDTH // 2, GAME_HEIGHT // 2)
        neon.scanlines(surface)
        restante = self.fin - t
        if restante < self.FUNDIDO:
            _velo(surface, NEGRO, 255 * (1 - max(0, restante) / self.FUNDIDO))


class CinematicaParcaConquista:
    """Perdiste el duelo: la galaxia vista de lejos con siete planetas en
    orbita; la Parca gigante se alza en el centro y, uno por uno, un tajo de su
    guadaña los vuelve violeta oscuro con una calavera encima. Al final
    "LA PARCA CONQUISTO LA GALAXIA" y "FIN... ¿O NO?".
    eventos: "risa" al empezar y "planeta" por cada tajo."""

    FUNDIDO = 40
    T_PRIMERO = 150
    PASO = 45
    COLORES = ((90, 170, 255), (255, 170, 80), (120, 230, 140), (240, 110, 160),
               (200, 200, 120), (130, 220, 230), (255, 120, 90))

    def __init__(self):
        self.t = 0
        rng = random.Random(9)
        self.estrellas = [(rng.randrange(GAME_WIDTH), rng.randrange(GAME_HEIGHT), rng.randrange(40)) for _ in range(120)]
        self.planetas = []
        for i, color in enumerate(self.COLORES):
            a = -math.pi / 2 + 2 * math.pi * i / len(self.COLORES)
            self.planetas.append({'x': GAME_WIDTH / 2 + math.cos(a) * 400, 'y': GAME_HEIGHT * 0.55 + math.sin(a) * 200,
                                  'r': 26 + (i * 7) % 14, 'color': color})
        self.fin_tajos = self.T_PRIMERO + self.PASO * len(self.planetas)
        self.fin = self.fin_tajos + 260
        self.eventos = []
        self.temblor = 0

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 60:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def _conquistados(self):
        return max(0, min(len(self.planetas), (self.t - self.T_PRIMERO) // self.PASO + 1))

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        if self.t == 30:
            self.eventos.append("risa")
        d = self.t - self.T_PRIMERO
        if 0 <= d and d % self.PASO == 0 and d // self.PASO < len(self.planetas):
            self.eventos.append("planeta")
            self.temblor = 10

    def draw(self, surface):
        mundo = pygame.Surface(surface.get_size())
        mundo.fill((6, 2, 14))
        for x, y, fase in self.estrellas:
            if ((self.t + fase) // 20) % 3:
                mundo.fill((200, 190, 230), (x, y, 2, 2))
        # la Parca gigante se alza en el centro de la galaxia
        k = min(1.0, self.t / 120)
        k = 1 - (1 - k) ** 3
        parca = sprite_halloween("parca", 2 if (self.t // 12) % 3 else 0, 8).copy()
        parca.set_alpha(int(110 + 145 * k))
        _blit_centrado(mundo, parca, GAME_WIDTH // 2, GAME_HEIGHT + 200 - k * (GAME_HEIGHT * 0.45 + 200)
                       + math.sin(self.t * 0.05) * 8)
        conquistados = self._conquistados()
        for i, pl in enumerate(self.planetas):
            tomado = i < conquistados
            color = (60, 20, 80) if tomado else pl['color']
            pygame.draw.circle(mundo, (10, 4, 20), (int(pl['x']), int(pl['y'])), pl['r'] + 4)
            pygame.draw.circle(mundo, color, (int(pl['x']), int(pl['y'])), pl['r'])
            pygame.draw.circle(mundo, tuple(min(255, c + 50) for c in color),
                               (int(pl['x'] - pl['r'] * 0.35), int(pl['y'] - pl['r'] * 0.35)), pl['r'] // 3)
            if tomado:
                _blit_centrado(mundo, sprite_halloween("calavera", 1, 3), pl['x'], pl['y'])
        surface.blit(pixelar(mundo, PIXEL_BONUS), (0, 0))
        # el tajo de la guadaña sobre el planeta que cae ahora
        d = self.t - self.T_PRIMERO
        if 0 <= d < self.PASO * len(self.planetas) and d % self.PASO < 10:
            pl = self.planetas[d // self.PASO]
            k = (d % self.PASO) / 10
            largo = 90
            pygame.draw.line(surface, WHITE, (pl['x'] - largo, pl['y'] - largo * (1 - 2 * k)),
                             (pl['x'] + largo, pl['y'] + largo * (1 - 2 * k)), 6)
            _velo(surface, ROJO_SANGRE, 60 * (1 - k))
        neon.franjas_cine(surface, self.t / 30, VIOLETA, alto=48)
        if self.t > 40:
            neon.cinta(surface, f"PLANETAS CONQUISTADOS: {conquistados}/{len(self.planetas)}", VIOLETA_CLARO,
                       (GAME_WIDTH // 2, 80), tam=16)
        if self.t >= self.fin_tajos:
            _velo(surface, NEGRO, min(150, (self.t - self.fin_tajos) * 6))
            neon.titulo(surface, "LA PARCA CONQUISTO LA GALAXIA", 46, ROJO_VIVO, GAME_WIDTH // 2, GAME_HEIGHT // 2 - 20)
        if self.t >= self.fin_tajos + 90 and (self.t // 15) % 2 == 0:
            neon.cinta(surface, "FIN... ¿O NO?", NARANJA, (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 50), tam=22)
        neon.scanlines(surface)
        restante = self.fin - self.t
        if restante < self.FUNDIDO:
            _velo(surface, NEGRO, 255 * (1 - max(0, restante) / self.FUNDIDO))


class CinematicaParcaVencida:
    """Ganaste el duelo: la dimension se agrieta con luz blanca que entra
    por las grietas, la tunica de la Parca se desarma hacia abajo y
    "¡ESCAPASTE DE SU DIMENSION!" antes de un destello blanco.
    eventos: "grieta" (varias) y "libre" al final."""

    FUNDIDO = 30
    DURACION = 360

    def __init__(self, sprite_nave):
        self.sprite_nave = sprite_nave
        self.t = 0
        self.fin = self.DURACION
        self.fondo = FondoDimension()
        self.grietas = []
        self.eventos = []
        self.temblor = 0

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 40:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        self.fondo.update()
        if self.t % 30 == 0 and self.t < 240:
            x, y = random.uniform(80, GAME_WIDTH - 80), random.uniform(80, GAME_HEIGHT - 80)
            puntos = [(x, y)]
            a = random.uniform(0, 2 * math.pi)
            for _ in range(6):
                a += random.uniform(-0.6, 0.6)
                x += math.cos(a) * 60
                y += math.sin(a) * 60
                puntos.append((x, y))
            self.grietas.append(puntos)
            self.eventos.append("grieta")
            self.temblor = 8
        if self.t == 260:
            self.eventos.append("libre")

    def draw(self, surface):
        mundo = pygame.Surface(surface.get_size())
        self.fondo.draw(mundo)
        # la Parca se desarma: baja, se apaga y tiembla
        k = min(1.0, self.t / 200)
        parca = sprite_halloween("parca", 2, 4).copy()
        parca.set_alpha(int(255 * (1 - k)))
        _blit_centrado(mundo, parca, GAME_WIDTH // 2 + random.randint(-3, 3), 170 + k * 120)
        if self.sprite_nave is not None:
            nave = pygame.transform.scale(self.sprite_nave, (self.sprite_nave.get_width() * 2,
                                                             self.sprite_nave.get_height() * 2))
            _blit_centrado(mundo, nave, GAME_WIDTH // 2, GAME_HEIGHT - 150 - max(0, self.t - 240) * 4)
        surface.blit(pixelar(mundo, PIXEL_BONUS), (0, 0))
        for puntos in self.grietas:
            pygame.draw.lines(surface, (255, 240, 220), False, puntos, 8)
            pygame.draw.lines(surface, WHITE, False, puntos, 3)
        neon.franjas_cine(surface, self.t / 30, VERDE_TOXICO, alto=44)
        if self.t > 120 and (self.t // 8) % 4 != 0:
            neon.titulo(surface, "¡ESCAPASTE DE SU DIMENSION!", 44, VERDE_TOXICO, GAME_WIDTH // 2, GAME_HEIGHT // 2)
        neon.scanlines(surface)
        if self.t > 240:
            _velo(surface, WHITE, min(255, (self.t - 240) * 4))
        restante = self.fin - self.t
        if restante < self.FUNDIDO:
            _velo(surface, WHITE, 255)


def icono_calavera():
    """Icono del panel de victoria tras vencer a la Parca en su dimension."""
    return sprite_halloween("calavera", 1, 9)
