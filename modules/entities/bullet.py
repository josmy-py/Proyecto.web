"""Bala disparada por la nave del jugador (ver Ship.shoot() en ship.py)."""

import pygame
from modules.constants import AMARILLO, WHITE, AZUL, MELON


class Bullet:
    """Viaja en linea recta hacia arriba con una estela que se desvanece.
    piercing=True (buff o clase bombardero) hace que no se desactive al
    primer impacto, asi puede atravesar varios objetivos en el mismo tiro."""

    def __init__(self, x, y, piercing=False, color=None):
        self.x = x
        self.y = y
        self.radius = 3
        self.speed = 9
        self.active = True
        self.trail = []
        self.piercing = piercing
        # color heredado del skin de la nave (None = color por defecto)
        self.color = tuple(color[:3]) if color else None

    def update(self):
        self.y -= self.speed
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
        if self.y < -10:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        base_color = self.color or AZUL
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(100 * (i / len(self.trail)))
            size = max(1, int(self.radius * (i / len(self.trail))))
            trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*base_color, alpha), (size, size), size)
            screen.blit(trail_surf, (int(tx) + offset_x - size, int(ty) + offset_y - size))

        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        glow_color = MELON if self.piercing else base_color
        pygame.draw.circle(glow_surf, (*glow_color[:3], 60), (self.radius * 2, self.radius * 2), self.radius * 2)
        screen.blit(glow_surf, (int(self.x) + offset_x - self.radius * 2, int(self.y) + offset_y - self.radius * 2))

        bullet_color = MELON if self.piercing else (
            tuple(min(255, c + 60) for c in base_color) if self.color else AMARILLO
        )
        pygame.draw.circle(screen, bullet_color, (int(self.x) + offset_x, int(self.y) + offset_y), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x) + offset_x, int(self.y) + offset_y), self.radius - 1)