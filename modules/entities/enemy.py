"""
Naves alienigenas comunes (no jefes): aparecen desde la oleada 2, entran por
un costado o por arriba y disparan balas hacia la nave del jugador. Los
jefes de oleada viven en modules/core/boss_system.py y modules/entities/boss.py,
no en este archivo.
"""

import pygame
import random
import math
from modules.constants import (
    LAVANDA, ROSA_CHICLE, MENTA, MELON, WHITE, AZUL, ROSA, AMARILLO,
    GAME_WIDTH, GAME_HEIGHT, SHIP_WIDTH,
)
from modules.systems import sprites
from modules.systems.fonts import render_text


# Variantes de nave enemiga (sprites en assets/sprites/enemies)
ENEMY_VARIANTS = {
    "fighter": {"size": 18, "speed": (1.2, 2.6), "rate": (55, 150)},
    "drone": {"size": 20, "speed": (0.8, 1.7), "rate": (70, 180)},
    "gunner": {"size": 19, "speed": (0.9, 1.9), "rate": (45, 120)},
}


class AlienShip:
    """Nave enemiga comun. Entra por 'left', 'right' o 'top', avanza hacia
    el lado opuesto y dispara AlienBullet a intervalos aleatorios segun su
    variante (fighter/drone/gunner, ver ENEMY_VARIANTS)."""

    def __init__(self, side="left", variant=None):
        self.side = side
        self.variant = variant or random.choice(list(ENEMY_VARIANTS.keys()))
        cfg = ENEMY_VARIANTS[self.variant]
        self.size = cfg["size"]
        self.x = random.randint(40, GAME_WIDTH - 40)
        self.y = random.randint(-80, -20) if side == "top" else (0 if side == "left" else GAME_WIDTH)
        self.speed = random.uniform(*cfg["speed"])
        self.vertical_speed = random.uniform(0.8, 1.8)
        self.active = True
        self.color = random.choice([LAVANDA, ROSA_CHICLE, AZUL, MENTA])
        self.wing_color = tuple(int(c * 0.62) for c in self.color[:3])
        self.vertices = self._generate_shape()
        self.shoot_timer = random.randint(30, 120)
        self.shoot_rate = random.randint(*cfg["rate"])
        self.wave = 0
        # balanceo suave en vez de girar sobre si misma
        self.bank_phase = random.uniform(0, math.pi * 2)
        self.rotation = 0.0
        self.rot_speed = 0.0
        self._sprite_key = ("enemy", self.variant, self.color, self.size)

    def _generate_shape(self):
        """Solo se usa como respaldo si faltan los PNG."""
        vertices = []
        num_pts = random.randint(5, 8)
        for i in range(num_pts):
            angle = 2 * math.pi * i / num_pts
            r = self.size * random.uniform(0.7, 1.2)
            vertices.append((r * math.cos(angle), r * math.sin(angle)))
        return vertices

    def update(self):
        """Avanza segun el lado de entrada, actualiza el balanceo visual y
        dispara cuando el temporizador llega a cero. Devuelve el AlienBullet
        creado o None. Se marca inactiva al salir del area de juego."""
        if self.side == "left":
            self.x += self.speed
            self.y += self.vertical_speed * 0.5
        elif self.side == "right":
            self.x -= self.speed
            self.y += self.vertical_speed * 0.5
        else:
            self.y += self.vertical_speed

        self.bank_phase += 0.05
        base_tilt = 12.0 if self.side == "right" else (-12.0 if self.side == "left" else 0.0)
        self.rotation = base_tilt + math.sin(self.bank_phase) * 7.0
        self.wave += 1

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_rate
            return self._create_bullet()

        if self.y > GAME_HEIGHT + 30 or self.x < -40 or self.x > GAME_WIDTH + 40:
            self.active = False

        return None

    def _create_bullet(self):
        return AlienBullet(self.x, self.y + self.size, self.side, color=self.color)

    def draw(self, screen, offset_x=0, offset_y=0):
        """Dibuja el sprite tintado de la variante (o el poligono de
        respaldo si faltan los PNG de assets/sprites/enemies)."""
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        sprite = sprites.get_enemy_surface(self.variant, self.color, self.wing_color, self.size)
        if sprite is not None:
            rotated = sprites.get_rotated(sprite, self.rotation, self._sprite_key)
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
            pygame.draw.polygon(screen, self.color, rotated_pts)
            pygame.draw.polygon(screen, WHITE, rotated_pts, 1)
        pygame.draw.circle(screen, MELON, (cx, cy), max(2, int(self.size * 0.3)))


class AlienBullet:
    """Bala disparada por un AlienShip. Viaja en linea recta segun el lado
    de origen (horizontal si vino de un costado, vertical si vino de arriba)."""

    def __init__(self, x, y, side, color=None):
        self.x = x
        self.y = y
        self.radius = 3
        self.color = tuple(color[:3]) if color else MELON
        self.speed = 4.0 if side == "left" else -4.0 if side == "right" else 4.0
        self.side = side
        self.active = True

    def update(self):
        if self.side == "left":
            self.x += self.speed
        elif self.side == "right":
            self.x += self.speed
        else:
            self.y += self.speed
        if self.y > GAME_HEIGHT + 10 or self.y < -10 or self.x < -10 or self.x > GAME_WIDTH + 10:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        glow = pygame.Surface((self.radius * 6, self.radius * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 70), (self.radius * 3, self.radius * 3), self.radius * 3)
        screen.blit(glow, (cx - self.radius * 3, cy - self.radius * 3))
        pygame.draw.circle(screen, self.color, (cx, cy), self.radius)
        pygame.draw.circle(screen, WHITE, (cx, cy), max(1, self.radius - 1))
