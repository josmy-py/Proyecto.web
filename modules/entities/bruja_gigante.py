"""
Cinematica de la Bruja Neon a mitad de pelea (ver BrujaBoss.UMBRAL_GIGANTE
en halloween.py y _cinematica_bruja_gigante en main.py): se planta en el
centro, saca una pocion, se la toma ("*glu glu glu*"), brilla y crece hasta
llenar la pantalla. Despues aparece de frente, gigante, con una pocion en
una mano y un circulo magico en la otra para la segunda parte de la pelea.

Interfaz de las otras cinematicas: update(), draw(surface), terminada,
saltar(), temblor y eventos ("pocion", "trago", "crece", "flash", "risa")."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.systems import neon
from modules.entities.nyan_boss import PIXEL_BONUS, pixelar, _blit_centrado
from modules.entities.halloween import (
    BrujaBoss, FondoHalloween, sprite_halloween, VERDE_TOXICO,
)

NEGRO = (0, 0, 0)
# celeste de las constelaciones de la bruja (ver _PALETA_BRUJA)
CELESTE = (170, 236, 255)
AZUL_NOCHE = (60, 110, 230)


def _globo(surface, texto, x, y):
    neon.globo(surface, texto, x, y, CELESTE, cola_derecha=False, tam=22)


class CinematicaBrujaGigante:
    T_POCION = 80
    T_BEBE = 150
    T_CRECE = 220
    T_FLASH = 320
    T_GIGANTE = 340
    T_RISA = 385
    DURACION = 500
    FUNDIDO = 25
    ESCALA = 6

    def __init__(self):
        self.t = 0
        self.fin = self.DURACION
        self.eventos = []
        self.temblor = 0
        self.fondo = FondoHalloween()
        self.burbujas = []
        self.chispas = []
        # la bruja gigante se dibuja con el mismo codigo que la pelea
        self.gigante = BrujaBoss(1.0)
        self.gigante.volverse_gigante()

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 30:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        self.fondo.update()
        t = self.t
        if t == self.T_POCION:
            self.eventos.append("pocion")
        if t in (self.T_BEBE + 15, self.T_BEBE + 35, self.T_BEBE + 55):
            self.eventos.append("trago")
        if t == self.T_CRECE:
            self.eventos.append("crece")
        if t == self.T_FLASH:
            self.eventos.append("flash")
        if t == self.T_RISA:
            self.eventos.append("risa")
            self.temblor = 12
        if self.T_CRECE <= t < self.T_FLASH:
            self.temblor = max(self.temblor, 3 + (t - self.T_CRECE) // 25)
            if t % 3 == 0:
                a = random.uniform(0, 2 * math.pi)
                r = random.uniform(160, 300)
                self.chispas.append([GAME_WIDTH / 2 + math.cos(a) * r, 330 + math.sin(a) * r, a, 30])
        if self.T_BEBE <= t < self.T_CRECE and t % 4 == 0:
            self.burbujas.append([GAME_WIDTH / 2 + 40 + random.uniform(-14, 14), 320.0, random.uniform(5, 10), 40])
        for b in self.burbujas:
            b[1] -= 1.6
            b[3] -= 1
        self.burbujas = [b for b in self.burbujas if b[3] > 0]
        for c in self.chispas:
            # las chispas vuelan hacia la bruja (la magia la llena)
            c[0] += (GAME_WIDTH / 2 - c[0]) * 0.08
            c[1] += (330 - c[1]) * 0.08
            c[3] -= 1
        self.chispas = [c for c in self.chispas if c[3] > 0]
        g = self.gigante
        if t >= self.T_GIGANTE:
            g.t = t
            k = min(1.0, (t - self.T_GIGANTE) / 45)
            k = 1 - (1 - k) ** 3
            g.x = GAME_WIDTH / 2
            g.y = GAME_HEIGHT + 220 - k * (GAME_HEIGHT + 220 - g.Y_GIGANTE)
            g.risa = 999 if t >= self.T_RISA else 0

    # ------------------------------------------------------------- dibujo

    def _bruja_chica(self, mundo):
        t = self.t
        escala = self.ESCALA
        y = 330 + math.sin(t * 0.06) * 8
        if t >= self.T_CRECE:
            k = min(1.0, (t - self.T_CRECE) / (self.T_FLASH - self.T_CRECE))
            escala = self.ESCALA + int(k * k * 9)
            y = 330 - k * 40
        spr = sprite_halloween("bruja", (t // 8) % 2, escala, blanco=t >= self.T_CRECE and (t // 3) % 5 == 0)
        _blit_centrado(mundo, spr, GAME_WIDTH / 2, y)
        # la pocion: aparece en la mano, sube a la boca y se vacia
        if self.T_POCION <= t < self.T_CRECE:
            mano = (GAME_WIDTH / 2 + 84, y + 42)
            boca = (GAME_WIDTH / 2 + 54, y - 16)
            if t < self.T_BEBE:
                px, py = mano
                py += math.sin(t * 0.2) * 3
            else:
                k = min(1.0, (t - self.T_BEBE) / 14)
                px = mano[0] + (boca[0] - mano[0]) * k
                py = mano[1] + (boca[1] - mano[1]) * k
            pocion = sprite_halloween("pocion", 1, 6)
            if t >= self.T_BEBE + 14:
                pocion = pygame.transform.rotate(pocion, 120)
            halo = pygame.Surface((90, 90), pygame.SRCALPHA)
            pygame.draw.circle(halo, (150, 255, 60, 60 + int(40 * math.sin(t * 0.3))), (45, 45), 45)
            _blit_centrado(mundo, halo, px, py)
            _blit_centrado(mundo, pocion, px, py)

    def draw(self, surface):
        t = self.t
        mundo = pygame.Surface(surface.get_size())
        self.fondo.draw(mundo)
        if t < self.T_GIGANTE:
            self._bruja_chica(mundo)
            for x, y, r, vida in self.burbujas:
                pygame.draw.circle(mundo, VERDE_TOXICO, (int(x), int(y)), int(r), 2)
            for x, y, a, vida in self.chispas:
                mundo.fill(CELESTE if int(a * 10) % 2 else VERDE_TOXICO, (int(x) - 3, int(y) - 3, 6, 6))
        else:
            self.gigante.draw(mundo)
        surface.blit(pixelar(mundo, PIXEL_BONUS), (0, 0))

        # destellos violeta / verde mientras crece
        if self.T_CRECE <= t < self.T_FLASH and (t // 6) % 2 == 0:
            neon.velo(surface, AZUL_NOCHE if (t // 12) % 2 else VERDE_TOXICO, 70)
        neon.franjas_cine(surface, t / 30, CELESTE, alto=48)

        # textos (nitidos, encima del pixelado)
        if 15 <= t < 75:
            _globo(surface, "Vaya, vaya... me estas haciendo enojar.", GAME_WIDTH / 2 + 60, 210)
        elif self.T_POCION + 10 <= t < self.T_BEBE:
            _globo(surface, "Hora de ponerme seria, cariño.", GAME_WIDTH / 2 + 60, 210)
        elif self.T_BEBE + 14 <= t < self.T_CRECE:
            dy = int(math.sin(t * 0.4) * 4)
            neon.cinta(surface, "*glu glu glu*", VERDE_TOXICO, (GAME_WIDTH / 2 + 150, 230 + dy), tam=20)
        elif self.T_CRECE + 10 <= t < self.T_FLASH and (t // 8) % 2 == 0:
            neon.titulo(surface, "¡¿QUE ME PASA?!", 44, VERDE_TOXICO, GAME_WIDTH / 2, 110)
        if t >= self.T_RISA:
            tam = 58 + int(4 * math.sin(t * 0.2))
            neon.titulo(surface, "¡BRUJA NEON GIGANTE!", tam, CELESTE, GAME_WIDTH / 2, GAME_HEIGHT - 130)
            if t >= self.T_RISA + 20:
                _globo(surface, "¡Ahora juguemos en serio!", GAME_WIDTH / 2 + 190, 120)

        # destello blanco del cambio de tamaño
        if self.T_FLASH <= t < self.T_GIGANTE + 20:
            if t < self.T_GIGANTE:
                alfa = 255 * (t - self.T_FLASH) / (self.T_GIGANTE - self.T_FLASH)
            else:
                alfa = 255 * (1 - (t - self.T_GIGANTE) / 20)
            neon.velo(surface, WHITE, int(alfa))
        neon.scanlines(surface)
        if t < 16:
            neon.velo(surface, NEGRO, int(255 * (1 - t / 16)))
        restante = self.fin - t
        if restante < self.FUNDIDO:
            neon.velo(surface, NEGRO, int(255 * (1 - max(0, restante) / self.FUNDIDO)))
