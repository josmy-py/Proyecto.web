"""Bala disparada por la nave del jugador (ver Ship.shoot() en ship.py)."""

import pygame
from modules.constants import AZUL, MELON
from modules.systems import pixelfx


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
        # fraccion del daño que hace a los jefes (las balas laterales del
        # TRIPLE CAÑON pegan menos, ver Ship.shoot)
        self.dano_jefe = 1.0

    def update(self):
        self.y -= self.speed
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
        if self.y < -10:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        base_color = MELON if self.piercing else (self.color or AZUL)
        # estela: bloques de pixel que se apagan
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail[:-1]):
            f = (i + 1) / n
            c = tuple(int(v * f * 0.8) for v in base_color[:3])
            lado = pixelfx.PIXEL
            screen.fill(c, (int(tx) + offset_x - lado // 2, int(ty) + offset_y + 6, lado, self.speed),
                        special_flags=pygame.BLEND_RGB_ADD)
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        pixelfx.dibujar_halo(screen, base_color, cx, cy, 10 if self.piercing else 7)
        sprite = pixelfx.bala_jugador(base_color, self.piercing)
        screen.blit(sprite, (cx - sprite.get_width() // 2, cy - sprite.get_height() // 2))
