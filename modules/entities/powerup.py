"""
Bonus recogibles: insignias pixel-art (marco biselado caqui/negro + una
letra dorada por habilidad, ver tools/generate_sprites.py) que sueltan un
buff temporal o permanente al tocarlas. random_buff_type()/buff_duration()
los usan tambien main.py y modules/entities/ship.py para sortear y aplicar
el efecto."""

import pygame
import random
import math
from modules.constants import (
    ROSA, ROSA_CHICLE, AZUL, MENTA, LAVANDA, AMARILLO, WHITE, MELON, ELECTRICO,
    GAME_WIDTH, GAME_HEIGHT, BUFF_DURATION, BUFF_DURATION_FAST, BUFF_DURATION_TRIPLE,
    BUFF_TYPE_EXTRA_LIFE, BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT,
    BUFF_TYPE_SHIELD, BUFF_TYPE_PIERCING, BUFF_TYPE_ATTRACT,
    BUFF_DURATION_SHIELD, BUFF_DURATION_PIERCING, BUFF_DURATION_ATTRACT,
    BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_SPEED_UP, BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_RAPID_FIRE,
    BUFF_TYPE_LIGHTNING, BUFF_DURATION_LIGHTNING,
    SHADOW, GLASS_WHITE,
)
from modules.systems.fonts import render_text
from modules.systems import sprites


class PowerUp:
    """Capsula que cae lentamente y desaparece tras `lifetime` frames si no
    se recoge. buff_type es uno de los BUFF_TYPE_* de modules/constants.py;
    color/label/icono salen de ahi (ver _get_color/_get_label y el sprite
    en assets/sprites/powerups)."""

    def __init__(self, x, y, buff_type=None):
        self.x = x
        self.y = y
        self.speed = 1.5
        self.radius = 12
        self.active = True
        self.lifetime = 600
        self.buff_type = buff_type or random_buff_type()
        self.color = self._get_color()
        self.label = self._get_label()
        self.pulse = 0

    def _get_color(self):
        return {
            BUFF_TYPE_EXTRA_LIFE: ROSA,
            BUFF_TYPE_FAST_SHOOT: AZUL,
            BUFF_TYPE_TRIPLE_SHOT: LAVANDA,
            BUFF_TYPE_SHIELD: MENTA,
            BUFF_TYPE_PIERCING: MELON,
            BUFF_TYPE_ATTRACT: AMARILLO,
            BUFF_TYPE_DAMAGE_UP: (255, 80, 80),
            BUFF_TYPE_SPEED_UP: (80, 255, 80),
            BUFF_TYPE_MAX_LIFE_UP: (255, 200, 80),
            BUFF_TYPE_RAPID_FIRE: (255, 120, 255),
            BUFF_TYPE_LIGHTNING: ELECTRICO,
        }.get(self.buff_type, AMARILLO)

    def _get_label(self):
        return {
            BUFF_TYPE_EXTRA_LIFE: "+1",
            BUFF_TYPE_FAST_SHOOT: "FAST",
            BUFF_TYPE_TRIPLE_SHOT: "3X",
            BUFF_TYPE_SHIELD: "DEF",
            BUFF_TYPE_PIERCING: "PEN",
            BUFF_TYPE_ATTRACT: "MAG",
            BUFF_TYPE_DAMAGE_UP: "DMG+",
            BUFF_TYPE_SPEED_UP: "SPD+",
            BUFF_TYPE_MAX_LIFE_UP: "MAX+",
            BUFF_TYPE_RAPID_FIRE: "RAPID",
            BUFF_TYPE_LIGHTNING: "RAYO",
        }.get(self.buff_type, "?")

    def update(self):
        self.y += self.speed
        self.pulse += 0.08
        self.lifetime -= 1
        if self.y > GAME_HEIGHT + 20 or self.lifetime <= 0:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        r = self.radius + int(math.sin(self.pulse) * 2)

        shadow_surf = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, SHADOW, (r + 3, r + 3), r)
        screen.blit(shadow_surf, (cx - r - 3, cy - r - 3))

        glow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        for i in range(3):
            gr = r * (1 + i * 0.3)
            ga = int(30 / (i + 1))
            pygame.draw.circle(glow_surf, (*self.color[:3], ga), (r * 2, r * 2), int(gr))
        screen.blit(glow_surf, (cx - r * 2, cy - r * 2))

        # Insignia pixel-art (marco biselado + letra, ver
        # tools/generate_sprites.py). Sin PNG en assets/sprites/powerups
        # no se dibuja una de respaldo por codigo: solo queda la etiqueta
        # de texto (siempre visible, ver mas abajo). Nada de rotacion aca
        # a proposito: pygame.transform.rotate suaviza/difumina los bordes
        # al girar, y eso arruina el pixelado en bloque del estilo retro -
        # solo el pulso de tamaño (ya pixelado el mismo, ver
        # _scaled_pixelado) la hace sentir "viva".
        sprite = sprites.get_powerup_surface(self.buff_type, self.color, r * 2 + 6)
        if sprite is not None:
            rect = sprite.get_rect(center=(cx, cy))
            screen.blit(sprite, rect)

        # Etiqueta corta debajo del icono: el dibujo ya sugiere el efecto
        # (corazon, rayo, iman...) pero el texto deja clarisimo que hace
        # cada bonus de un vistazo.
        label_surf = render_text(self.label, 12, WHITE)
        label_x = cx - label_surf.get_width() // 2
        label_y = cy + r + 3
        chip_surf = pygame.Surface((label_surf.get_width() + 6, label_surf.get_height() + 2), pygame.SRCALPHA)
        pygame.draw.rect(chip_surf, (10, 10, 20, 170), chip_surf.get_rect(), border_radius=4)
        screen.blit(chip_surf, (label_x - 3, label_y - 1))
        screen.blit(label_surf, (label_x, label_y))


def random_buff_type():
    """Sortea un tipo de buff "de drop comun" (asteroides/alienigenas). Los
    permanentes de jefe (DAMAGE_UP, SPEED_UP, MAX_LIFE_UP, RAPID_FIRE) no
    entran aca: los reparte boss_system.py via BossDefinition.rewards."""
    return random.choice([
        BUFF_TYPE_EXTRA_LIFE,
        BUFF_TYPE_FAST_SHOOT,
        BUFF_TYPE_TRIPLE_SHOT,
        BUFF_TYPE_SHIELD,
        BUFF_TYPE_PIERCING,
        BUFF_TYPE_ATTRACT,
        BUFF_TYPE_LIGHTNING,
    ])


def buff_duration(buff_type):
    """Duracion en frames del buff (0 = instantaneo, como la vida extra)."""
    return {
        BUFF_TYPE_EXTRA_LIFE: 0,
        BUFF_TYPE_FAST_SHOOT: BUFF_DURATION_FAST,
        BUFF_TYPE_TRIPLE_SHOT: BUFF_DURATION_TRIPLE,
        BUFF_TYPE_SHIELD: BUFF_DURATION_SHIELD,
        BUFF_TYPE_PIERCING: BUFF_DURATION_PIERCING,
        BUFF_TYPE_ATTRACT: BUFF_DURATION_ATTRACT,
        BUFF_TYPE_LIGHTNING: BUFF_DURATION_LIGHTNING,
    }.get(buff_type, 0)