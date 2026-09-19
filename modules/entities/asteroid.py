"""
Asteroides y los efectos visuales de particulas que usa todo el juego
(Particle/Explosion las reutilizan bosses, enemigos y power-ups, no solo
los asteroides)."""

import pygame
import random
import math
from modules.constants import (
    MELON, WHITE, DARK_BG, GAME_WIDTH, GAME_HEIGHT,
    DARKER_BG, ROSA, LAVANDA, AZUL,
)
from modules.systems import sprites


# Paleta de roca: pocos tonos para que el cache de sprites se reutilice
ROCK_TINTS = [
    (196, 172, 146),
    (168, 150, 138),
    (150, 132, 116),
    (186, 182, 178),
    (140, 152, 164),
]


class Asteroid:
    """Roca que cae desde arriba del area de juego. Usa uno de los 14
    sprites generados por tools/generate_sprites.py (tintado y rotado); si
    faltan los PNG cae al poligono aleatorio de _generate_shape()."""

    def __init__(self, x, y, size=25):
        self.x = x
        self.y = y
        self.size = size
        self.speed = random.uniform(2.0, 5.0)
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-2.2, 2.2)
        self.active = True
        self.variant = random.randrange(sprites.ASTEROID_VARIANTS)
        self.color = random.choice(ROCK_TINTS)
        self.dark_color = tuple(max(0, c - 35) for c in self.color)
        self.light_color = tuple(min(255, c + 35) for c in self.color)
        self.vertices = self._generate_shape()
        self.flash_timer = 0
        self.glow_phase = random.uniform(0, math.pi * 2)
        self._sprite_key = ("rock", self.variant, self.size, self.color)

    def _generate_shape(self):
        """Solo se usa como respaldo si faltan los PNG."""
        vertices = []
        num_pts = random.randint(7, 12)
        for i in range(num_pts):
            angle = 2 * math.pi * i / num_pts
            r = self.size * random.uniform(0.6, 1.3)
            vertices.append((r * math.cos(angle), r * math.sin(angle)))
        return vertices

    def update(self):
        self.y += self.speed
        self.rotation = (self.rotation + self.rot_speed) % 360
        self.glow_phase += 0.06
        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.y > GAME_HEIGHT + self.size + 20:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        hit = self.flash_timer > 0
        tint = (255, 255, 255) if hit else self.color
        sprite = sprites.get_asteroid_surface(self.variant, self.size, tint)

        if sprite is not None:
            key = self._sprite_key + (hit,)
            rotated = sprites.get_rotated(sprite, self.rotation, key)
            sprites.blit_centered(screen, rotated, cx, cy)
            return

        # ---- respaldo vectorial (sin assets/sprites)
        rad = math.radians(self.rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        rotated_pts = []
        for vx, vy in self.vertices:
            rotated_pts.append((cx + vx * cos_r - vy * sin_r, cy + vx * sin_r + vy * cos_r))
        if len(rotated_pts) >= 3:
            pygame.draw.polygon(screen, WHITE if hit else self.color, rotated_pts)
            pygame.draw.polygon(screen, self.dark_color, rotated_pts, 2)


class Particle:
    """Chispa individual con velocidad aleatoria y desvanecimiento por vida
    restante. Explosion agrupa varias para el efecto de destruccion."""

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = random.randint(15, 40)
        self.max_life = self.life
        self.radius = random.randint(1, 4)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, screen, offset_x=0, offset_y=0):
        if self.life <= 0:
            return
        alpha = self.life / self.max_life
        size = max(1, int(self.radius * alpha))
        c = tuple(int(ch * alpha) for ch in self.color)
        pygame.draw.circle(screen, c, (int(self.x) + offset_x, int(self.y) + offset_y), size)


class Explosion:
    """Grupo de Particle que se dispara al destruir algo. active pasa a
    False cuando ya ninguna particula tiene vida restante."""

    def __init__(self, x, y, color=MELON, count=20):
        self.particles = [Particle(x, y, color) for _ in range(count)]
        self.active = True
        self.glow_phase = 0

    def update(self):
        alive_any = False
        for p in self.particles:
            p.update()
            if p.life > 0:
                alive_any = True
        if not alive_any:
            self.active = False
        self.glow_phase += 0.1

    def draw(self, screen, offset_x=0, offset_y=0):
        for p in self.particles:
            p.draw(screen, offset_x, offset_y)