"""
HUD y pantallas de estado del juego en si (no del menu, ver
modules/systems/menu.py para eso): la cuenta regresiva inicial, el HUD de
vida/puntaje/oleada, los chips de buffs activos, la vista previa de camara
y las pantallas de fin de partida (game over / victoria) con sus
estadisticas."""

import pygame
import math
import random
from modules.constants import (
    WHITE, ROSA, MENTA, AMARILLO, AZUL, AZUL_CIELO, MELON, LAVANDA, ROSA_CHICLE, ELECTRICO,
    DARK_BG, DARKER_BG, GAME_WIDTH, GAME_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT,
    GLASS_WHITE, GLASS_BLACK, SHADOW,
    BUFF_TYPE_EXTRA_LIFE, BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT,
    BUFF_TYPE_SHIELD, BUFF_TYPE_PIERCING, BUFF_TYPE_ATTRACT,
    BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_SPEED_UP, BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_RAPID_FIRE,
    BUFF_TYPE_LIGHTNING,
    BUFF_DURATION_FAST, BUFF_DURATION_TRIPLE, BUFF_DURATION_SHIELD, BUFF_DURATION_PIERCING, BUFF_DURATION_ATTRACT,
    BOSS_SPAWN_WAVE, FINAL_BOSS_SPAWN_WAVE,
)
from modules.systems.fonts import get_font, render_text, render_texto_pixelado


def _texto_ajustado(texto, fuente, color, ancho_maximo):
    """Renderiza texto pixelado y lo reduce (si hace falta) para que quepa
    en ancho_maximo, sin importar que fuente termine cargando el sistema en
    la maquina donde corra el juego."""
    return render_texto_pixelado(fuente, texto, color, ancho_maximo=ancho_maximo)


def draw_rounded_rect(surface, rect, color, radius=4, border=0):
    x, y, w, h = rect
    r = min(radius, w // 2, h // 2)
    pygame.draw.rect(surface, color, (x + r, y, w - 2 * r, h))
    pygame.draw.rect(surface, color, (x, y + r, w, h - 2 * r))
    pygame.draw.circle(surface, color, (x + r, y + r), r)
    pygame.draw.circle(surface, color, (x + w - r, y + r), r)
    pygame.draw.circle(surface, color, (x + r, y + h - r), r)
    pygame.draw.circle(surface, color, (x + w - r, y + h - r), r)
    if border > 0:
        pygame.draw.rect(surface, WHITE, rect, border)


def draw_glow_circle(surface, pos, radius, color, intensity=0.5):
    x, y = pos
    for i in range(3):
        r = radius + i * 6
        alpha = int(intensity * (1 - i * 0.3) * 255)
        glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        c = (*color[:3], alpha)
        pygame.draw.circle(glow_surf, c, (r, r), r)
        surface.blit(glow_surf, (int(x - r), int(y - r)))


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    p = 0.3
    s = p / 4
    return math.pow(2, -10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(val, min_val, max_val):
    return max(min_val, min(max_val, val))


class AnimatedValue:
    """Numero que persigue a `target` con resorte amortiguado en vez de
    saltar de golpe (usado por el puntaje y las vidas del HUD)."""

    def __init__(self, value, speed=0.15):
        self.current = float(value)
        self.target = float(value)
        self.speed = speed
        self.velocity = 0.0

    def set(self, value):
        self.target = float(value)

    def update(self):
        diff = self.target - self.current
        self.velocity += diff * self.speed
        self.velocity *= 0.85
        self.current += self.velocity
        if abs(diff) < 0.01 and abs(self.velocity) < 0.01:
            self.current = self.target
            self.velocity = 0.0

    def get(self):
        return self.current


class HealthBar:
    """Barra de vidas del HUD (no confundir con la de los jefes, que vive
    en boss.py/boss_system.py). set_hp() dispara particulas de impacto y
    sacudida cuando la vida baja."""

    def __init__(self, x, y, width, height, max_hp):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.display_hp = float(max_hp)
        self.animated_hp = AnimatedValue(max_hp, speed=0.12)
        self.particles = []
        self.shake_timer = 0
        self.shake_intensity = 0
        self.glow_phase = 0
        self.fill_phase = 0
        self.last_hp = max_hp

    def set_hp(self, hp):
        if hp < self.last_hp:
            damage = self.last_hp - hp
            for _ in range(int(damage * 0.5)):
                self.particles.append({
                    'x': random.uniform(self.x, self.x + self.width),
                    'y': self.y + self.height // 2,
                    'vx': random.uniform(-2, 2),
                    'vy': random.uniform(-1.5, -0.5),
                    'life': random.randint(15, 30),
                    'max_life': 30,
                    'size': random.randint(2, 4),
                    'color': (255, random.randint(150, 220), random.randint(150, 200)),
                })
            self.shake_timer = 12
            self.shake_intensity = 4
        self.current_hp = max(0, min(self.max_hp, hp))
        self.last_hp = self.current_hp

    def update(self):
        self.animated_hp.set(self.current_hp)
        self.animated_hp.update()
        self.display_hp = self.animated_hp.get()
        self.glow_phase += 0.08
        self.fill_phase += 0.05

        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_intensity *= 0.85

        alive_particles = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.05
            p['life'] -= 1
            if p['life'] > 0:
                alive_particles.append(p)
        self.particles = alive_particles

    def get_hp_ratio(self):
        return self.display_hp / self.max_hp if self.max_hp > 0 else 0

    def draw(self, surface):
        ratio = clamp(self.get_hp_ratio(), 0.0, 1.0)
        shake_x = 0
        shake_y = 0
        if self.shake_timer > 0:
            shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)

        draw_x = self.x + shake_x
        draw_y = self.y + shake_y

        shadow_rect = (draw_x + 3, draw_y + 3, self.width, self.height)
        shadow_surf = pygame.Surface((self.width + 6, self.height + 6), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, SHADOW, (3, 3, self.width, self.height), border_radius=self.height // 2)
        surface.blit(shadow_surf, (draw_x, draw_y))

        bg_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        bg_color = (35, 35, 55)
        pygame.draw.rect(bg_surf, bg_color, (0, 0, self.width, self.height), border_radius=self.height // 2)
        surface.blit(bg_surf, (draw_x, draw_y))

        inner_margin = 3
        inner_x = draw_x + inner_margin
        inner_y = draw_y + inner_margin
        inner_w = self.width - inner_margin * 2
        inner_h = self.height - inner_margin * 2

        if ratio > 0.001:
            fill_w = int(inner_w * ratio)
            if fill_w > 0:
                fill_rect = (inner_x, inner_y, fill_w, inner_h)
                fill_surf = pygame.Surface((fill_w, inner_h), pygame.SRCALPHA)

                if ratio > 0.6:
                    base_color = ROSA
                    glow_color = (255, 150, 180, 40)
                elif ratio > 0.3:
                    base_color = AMARILLO
                    glow_color = (255, 235, 160, 40)
                else:
                    base_color = MELON
                    glow_color = (255, 120, 120, 50)

                for row in range(inner_h):
                    t = row / inner_h
                    alpha = 255
                    brightness = 1.0 - t * 0.3
                    r = int(base_color[0] * brightness)
                    g = int(base_color[1] * brightness)
                    b = int(base_color[2] * brightness)
                    pygame.draw.line(fill_surf, (r, g, b, alpha), (0, row), (fill_w - 1, row))

                pygame.draw.rect(fill_surf, GLASS_WHITE, (0, 0, fill_w, inner_h), border_radius=inner_h // 2)
                surface.blit(fill_surf, (inner_x, inner_y))

                highlight_h = max(1, inner_h // 3)
                hl_surf = pygame.Surface((fill_w, highlight_h), pygame.SRCALPHA)
                for row in range(highlight_h):
                    a = int(50 * (1 - row / highlight_h))
                    pygame.draw.line(hl_surf, (255, 255, 255, a), (0, row), (fill_w - 1, row))
                surface.blit(hl_surf, (inner_x, inner_y + 1))

                wave_offset = int(self.fill_phase * 2) % 6 - 3
                wave_surf = pygame.Surface((fill_w, 3), pygame.SRCALPHA)
                for col in range(fill_w):
                    wave_t = math.sin((col + self.fill_phase * 3) * 0.1) * 0.5 + 0.5
                    a = int(30 * wave_t)
                    pygame.draw.line(wave_surf, (255, 255, 255, a), (col, 0), (col, 2))
                surface.blit(wave_surf, (inner_x, inner_y + inner_h - 5 + wave_offset))

        border_rect = (draw_x, draw_y, self.width, self.height)
        pygame.draw.rect(surface, WHITE, border_rect, width=1, border_radius=self.height // 2)

        if ratio > 0.001:
            cx = draw_x + self.width // 2
            cy = draw_y + self.height // 2
            pct_text = f"{int(ratio * 100)}%"
            text_surf = render_text(pct_text, max(8, self.height - 2), WHITE)
            surface.blit(text_surf, (cx - text_surf.get_width() // 2, cy - text_surf.get_height() // 2))

        for p in self.particles:
            life_ratio = p['life'] / p['max_life']
            alpha = int(255 * life_ratio)
            size = max(1, int(p['size'] * life_ratio))
            c = (p['color'][0], p['color'][1], p['color'][2])
            pygame.draw.circle(surface, c, (int(p['x']), int(p['y'])), size)


class ModernHUD:
    """Panel superior izquierdo con puntaje, oleada y la HealthBar. Se crea
    una sola vez por partida (ver draw_hud, que la guarda como atributo de
    si misma para no recrearla cada frame)."""

    def __init__(self, max_hp):
        self.max_hp = max_hp
        self.health_bar = HealthBar(12, 12, 180, 18, max_hp)
        self.score_value = AnimatedValue(0, speed=0.2)
        self.wave_value = 1
        self.lives = 3
        self.display_lives = AnimatedValue(3, speed=0.3)
        self.buffs = {}
        self.hand_active = False
        self.pulse_phase = 0
        self.fade_in = 0.0
        self.score_flash = 0
        self.lives_pulse = 0

    def update(self, score, wave, lives, buffs, hand_active):
        self.score_value.set(score)
        self.score_value.update()
        self.wave_value = wave
        self.lives = lives
        self.display_lives.set(lives)
        self.display_lives.update()
        self.health_bar.set_hp(lives)
        self.buffs = buffs
        self.hand_active = hand_active
        self.pulse_phase += 0.06
        self.health_bar.update()
        self.fade_in = min(1.0, self.fade_in + 0.05)
        if self.score_flash > 0:
            self.score_flash -= 1
        if self.lives_pulse > 0:
            self.lives_pulse -= 1

    def draw(self, surface):
        alpha = int(255 * ease_out_cubic(self.fade_in))
        panel_w = 200
        panel_h = 90
        panel_x = 8
        panel_y = 8

        panel_surf = pygame.Surface((panel_w + 20, panel_h + 20), pygame.SRCALPHA)
        shadow_surf = pygame.Surface((panel_w + 26, panel_h + 26), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, SHADOW, (5, 5, panel_w + 20, panel_h + 20), border_radius=16)
        surface.blit(shadow_surf, (panel_x - 3, panel_y - 3))

        bg_rect = (0, 0, panel_w + 20, panel_h + 20)
        pygame.draw.rect(panel_surf, GLASS_BLACK, bg_rect, border_radius=16)
        bg2 = pygame.Surface((panel_w + 20, panel_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(bg2, GLASS_WHITE, bg_rect, border_radius=16)
        panel_surf.blit(bg2, (0, 0))
        pygame.draw.rect(panel_surf, (255, 255, 255, 30), (1, 1, panel_w + 18, panel_h + 18), width=1, border_radius=16)
        surface.blit(panel_surf, (panel_x, panel_y))

        score = int(self.score_value.get())
        score_text = render_text("SCORE", 22, (180, 180, 200))
        score_val = render_text(f"{score}", 22, WHITE)
        surface.blit(score_text, (panel_x + 16, panel_y + 16))
        surface.blit(score_val, (panel_x + 16, panel_y + 36))

        wave_color = AZUL
        wave_text = render_text(f"WAVE {self.wave_value}", 16, wave_color)
        surface.blit(wave_text, (panel_x + 16, panel_y + 60))

        self.health_bar.x = panel_x + 16
        self.health_bar.y = panel_y + 82
        self.health_bar.draw(surface)


class BuffChip:
    """Tarjeta con icono, etiqueta y barra de tiempo restante para un buff
    activo de la nave. _get_style()/_get_label() traducen el BUFF_TYPE_* a
    color/icono/texto; agregar un buff nuevo implica sumarlo ahi."""

    def __init__(self, buff_type, timer, max_timer, font):
        self.buff_type = buff_type
        self.timer = timer
        self.max_timer = max_timer
        self.font = font
        self.label_font = get_font(9)
        self.width = 62
        self.height = 24
        self.pulse_phase = random.uniform(0, math.pi * 2)
        self.color, self.icon = self._get_style()

    def _get_style(self):
        mapping = {
            BUFF_TYPE_EXTRA_LIFE: (ROSA, "heart"),
            BUFF_TYPE_FAST_SHOOT: (AZUL, "bolt"),
            BUFF_TYPE_TRIPLE_SHOT: (LAVANDA, "triple"),
            BUFF_TYPE_SHIELD: (MENTA, "hexagon"),
            BUFF_TYPE_PIERCING: (MELON, "arrow"),
            BUFF_TYPE_ATTRACT: (AMARILLO, "magnet"),
            BUFF_TYPE_DAMAGE_UP: ((255, 80, 80), "sword"),
            BUFF_TYPE_SPEED_UP: ((80, 255, 80), "speed"),
            BUFF_TYPE_MAX_LIFE_UP: ((255, 200, 80), "heart_plus"),
            BUFF_TYPE_RAPID_FIRE: ((255, 120, 255), "rapid"),
            BUFF_TYPE_LIGHTNING: (ELECTRICO, "lightning_field"),
        }
        return mapping.get(self.buff_type, (AMARILLO, "circle"))

    def update(self):
        self.pulse_phase += 0.06

    def draw(self, surface, x, y):
        w, h = self.width, self.height
        radius = 8
        chip_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(chip_surf, GLASS_BLACK, (0, 0, w, h), border_radius=radius)
        pygame.draw.rect(chip_surf, GLASS_WHITE, (0, 0, w, h), border_radius=radius)
        pygame.draw.rect(chip_surf, (*self.color[:3], 80), (2, 2, w - 4, h - 4), border_radius=radius)

        icon_x = 10
        icon_y = h // 2
        self._draw_icon(chip_surf, icon_x, icon_y)

        label = self._get_label()
        label_surf = render_texto_pixelado(self.label_font, label, WHITE)
        chip_surf.blit(label_surf, (22, h // 2 - label_surf.get_height() // 2))

        timer_ratio = clamp(self.timer / self.max_timer, 0.0, 1.0)
        bar_w = w - 8
        bar_h = 3
        bar_x = 4
        bar_y = h - 6
        pygame.draw.rect(chip_surf, (20, 20, 30), (bar_x, bar_y, bar_w, bar_h), border_radius=1)
        fill_w = int(bar_w * timer_ratio)
        if fill_w > 0:
            pygame.draw.rect(chip_surf, self.color, (bar_x, bar_y, fill_w, bar_h), border_radius=1)

        pulse = 0.5 + 0.5 * math.sin(self.pulse_phase)
        glow_alpha = int(15 + 10 * pulse)
        glow_surf = pygame.Surface((w + 10, h + 10), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*self.color[:3], glow_alpha), (5, 5, w, h), border_radius=radius)
        surface.blit(glow_surf, (x - 5, y - 5))

        surface.blit(chip_surf, (x, y))

    def _draw_icon(self, surface, x, y):
        if self.icon == "heart":
            pygame.draw.circle(surface, self.color, (x - 2, y - 2), 3)
            pygame.draw.circle(surface, self.color, (x + 2, y - 2), 3)
            pygame.draw.polygon(surface, self.color, [(x - 5, y - 1), (x + 5, y - 5), (x + 5, y + 3), (x - 5, y + 1)])
        elif self.icon == "bolt":
            pygame.draw.polygon(surface, self.color, [(x, y - 5), (x + 2, y - 1), (x + 5, y - 1), (x + 1, y + 2), (x + 3, y + 5), (x, y + 2), (x - 3, y + 2), (x, y - 5)])
        elif self.icon == "triple":
            pygame.draw.circle(surface, self.color, (x, y - 3), 2)
            pygame.draw.circle(surface, self.color, (x - 4, y + 3), 2)
            pygame.draw.circle(surface, self.color, (x + 4, y + 3), 2)
        elif self.icon == "hexagon":
            points = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                points.append((x + 4 * math.cos(angle), y + 4 * math.sin(angle)))
            pygame.draw.polygon(surface, self.color, points)
        elif self.icon == "arrow":
            pygame.draw.polygon(surface, self.color, [(x, y - 5), (x + 5, y + 2), (x + 2, y + 2), (x + 2, y + 5), (x - 2, y + 5), (x - 2, y + 2), (x - 5, y + 2)])
        elif self.icon == "magnet":
            pygame.draw.arc(surface, self.color, (x - 5, y - 4, 10, 8), math.pi, 0, 2)
            pygame.draw.line(surface, self.color, (x - 5, y), (x - 5, y + 4), 2)
            pygame.draw.line(surface, self.color, (x + 5, y), (x + 5, y + 4), 2)
            pygame.draw.line(surface, self.color, (x - 2, y + 2), (x - 4, y + 5), 2)
            pygame.draw.line(surface, self.color, (x + 2, y + 2), (x + 4, y + 5), 2)
        elif self.icon == "sword":
            pygame.draw.line(surface, self.color, (x, y - 5), (x, y + 5), 2)
            pygame.draw.line(surface, self.color, (x - 2, y - 3), (x + 2, y - 3), 2)
        elif self.icon == "speed":
            pygame.draw.polygon(surface, self.color, [(x - 3, y - 4), (x + 3, y), (x - 3, y + 4)])
        elif self.icon == "heart_plus":
            pygame.draw.circle(surface, self.color, (x - 2, y - 2), 3)
            pygame.draw.circle(surface, self.color, (x + 2, y - 2), 3)
            pygame.draw.polygon(surface, self.color, [(x - 5, y - 1), (x + 5, y - 5), (x + 5, y + 3), (x - 5, y + 1)])
            pygame.draw.line(surface, self.color, (x + 2, y - 4), (x + 5, y - 7), 2)
            pygame.draw.line(surface, self.color, (x, y - 5), (x, y - 8), 2)
        elif self.icon == "rapid":
            pygame.draw.polygon(surface, self.color, [(x, y - 5), (x + 3, y - 1), (x + 6, y - 1), (x + 1, y + 2), (x + 3, y + 5), (x, y + 2), (x - 3, y + 2), (x, y - 5)])
        elif self.icon == "lightning_field":
            pygame.draw.circle(surface, self.color, (x, y), 5, 1)
            pygame.draw.polygon(surface, self.color, [(x, y - 4), (x + 2, y - 1), (x, y - 1), (x + 1, y + 4), (x - 2, y + 1), (x, y + 1), (x, y - 4)])
        else:
            pygame.draw.circle(surface, self.color, (x, y), 4)

    def _get_label(self):
        labels = {
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
        }
        return labels.get(self.buff_type, "?")


class BuffHUD:
    """Columna de BuffChip a la derecha del area de juego, uno por buff
    activo en ship.buffs. Crea/elimina chips segun aparecen o vencen."""

    def __init__(self):
        self.chips = {}
        self.fade_in = 0.0

    def update(self, buffs):
        self.fade_in = min(1.0, self.fade_in + 0.05)
        for buff_type, data in buffs.items():
            if buff_type not in self.chips:
                self.chips[buff_type] = BuffChip(buff_type, data.get("timer", 0), data.get("max_timer", 1), get_font(9))
            self.chips[buff_type].timer = data.get("timer", 0)
            self.chips[buff_type].max_timer = data.get("max_timer", 1)
            self.chips[buff_type].update()

        expired = [bt for bt in self.chips if bt not in buffs]
        for bt in expired:
            del self.chips[bt]

    def draw(self, surface, offset_x=0, offset_y=0):
        if not self.chips:
            return
        alpha = int(255 * ease_out_cubic(self.fade_in))
        chip_w = 62
        chip_h = 24
        gap = 6
        start_x = offset_x + GAME_WIDTH + 10
        start_y = offset_y + 10

        for idx, chip in enumerate(self.chips.values()):
            chip.draw(surface, start_x, start_y + idx * (chip_h + gap))


def draw_hud(surface, score, wave, lives, buffs, font, small_font, hand_active=False, max_hp=3):
    if not hasattr(draw_hud, 'hud'):
        draw_hud.hud = ModernHUD(max_hp)
    hud = draw_hud.hud
    hud.health_bar.max_hp = max_hp
    hud.update(score, wave, lives, buffs, hand_active)
    hud.draw(surface)


def draw_buff_hud(surface, buffs, offset_x=0, offset_y=0):
    if not hasattr(draw_buff_hud, 'hud'):
        draw_buff_hud.hud = BuffHUD()
    hud = draw_buff_hud.hud
    hud.update(buffs)
    hud.draw(surface, offset_x, offset_y)


def draw_camera_preview(surface, preview_surf, preview_rect, timestamp):
    shadow_rect = pygame.Rect(preview_rect.x - 2, preview_rect.y - 2, preview_rect.width + 4, preview_rect.height + 4)
    shadow_surf = pygame.Surface((preview_rect.width + 4, preview_rect.height + 4), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, SHADOW, (2, 2, preview_rect.width, preview_rect.height), border_radius=8)
    surface.blit(shadow_surf, (preview_rect.x - 2, preview_rect.y - 2))

    border_surf = pygame.Surface((preview_rect.width + 4, preview_rect.height + 4), pygame.SRCALPHA)
    pulse = abs(math.sin(timestamp * 0.004))
    border_color = (int(AZUL[0] * (0.7 + 0.3 * pulse)), int(AZUL[1] * (0.7 + 0.3 * pulse)), int(AZUL[2] * (0.7 + 0.3 * pulse)), 200)
    pygame.draw.rect(border_surf, border_color, (2, 2, preview_rect.width, preview_rect.height), width=1, border_radius=8)
    surface.blit(border_surf, (preview_rect.x - 2, preview_rect.y - 2))

    surface.blit(preview_surf, preview_rect)

    label_surf = render_text("CAM", 11, WHITE)
    surface.blit(label_surf, (preview_rect.x + 4, preview_rect.y + preview_rect.height + 3))


def draw_countdown(surface, game_w, game_h, countdown_val, font, info_font, big_font):
    for i in range(3):
        y_off = (pygame.time.get_ticks() // (30 + i * 10)) % (game_h + 20) - 10
        alpha = 40 + i * 10
        pygame.draw.line(surface, (alpha, alpha, alpha), (0, y_off), (game_w, y_off), 1)

    title = render_texto_pixelado(big_font, "Nave vs Asteroides", WHITE)
    surface.blit(title, (game_w // 2 - title.get_width() // 2, game_h // 2 - 180))

    cd_text = render_texto_pixelado(font, f"Comienza en: {countdown_val}", WHITE)
    surface.blit(cd_text, (game_w // 2 - cd_text.get_width() // 2, game_h // 2 - 50))

    instructions = [
        "Mueve tu mano para controlar la nave",
        "Cierra el puno para disparar (rafaga de 3)",
        "Destruye objetos para recibir power-ups",
        f"Oleada {BOSS_SPAWN_WAVE}: JEFE",
        f"Oleada {FINAL_BOSS_SPAWN_WAVE}: JEFE FINAL",
        "ESC para salir | R para reiniciar",
    ]
    colors = [WHITE, WHITE, WHITE, ROSA, AZUL, AMARILLO]

    for i, (text, color) in enumerate(zip(instructions, colors)):
        inst = render_texto_pixelado(info_font, text, color)
        surface.blit(inst, (game_w // 2 - inst.get_width() // 2, game_h // 2 + 30 + i * 25))


def formatear_tiempo(segundos):
    segundos = max(0, int(segundos))
    return f"{segundos // 60}:{segundos % 60:02d}"


def _dibujar_stats_partida(surface, game_w, y, stats):
    """Dos lineas compactas con precision/tiempo y el desglose de enemigos
    destruidos. stats es un dict (ver terminar_partida() en main.py); si es
    None no se dibuja nada (compatibilidad con llamadas viejas)."""
    if not stats:
        return y
    disparos = stats.get("disparos", 0)
    aciertos = stats.get("aciertos", 0)
    precision = int(round(100 * aciertos / disparos)) if disparos > 0 else 0
    tiempo = formatear_tiempo(stats.get("tiempo", 0))

    linea1 = render_texto_pixelado(get_font(15), f"Precision: {precision}%   Tiempo: {tiempo}", MENTA)
    surface.blit(linea1, (game_w // 2 - linea1.get_width() // 2, y))

    linea2 = render_texto_pixelado(
        get_font(15),
        f"Asteroides: {stats.get('asteroides', 0)}   "
        f"Alienigenas: {stats.get('alienigenas', 0)}   "
        f"Jefes: {stats.get('jefes', 0)}",
        (200, 200, 220),
    )
    surface.blit(linea2, (game_w // 2 - linea2.get_width() // 2, y + 22))
    return y + 22 + linea2.get_height()


def draw_game_over(surface, game_w, game_h, score, wave, font, big_font, buttons=None, selected=0, stats=None):
    overlay = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    go_text = render_texto_pixelado(big_font, "GAME OVER", ROSA)
    sc_text = render_texto_pixelado(font, f"Puntuacion Final: {score}", WHITE)
    wt_text = render_texto_pixelado(font, f"Oleada Alcanzada: {wave}", AZUL)

    surface.blit(go_text, (game_w // 2 - go_text.get_width() // 2, game_h // 2 - 130))
    surface.blit(sc_text, (game_w // 2 - sc_text.get_width() // 2, game_h // 2 - 85))
    surface.blit(wt_text, (game_w // 2 - wt_text.get_width() // 2, game_h // 2 - 58))

    _dibujar_stats_partida(surface, game_w, game_h // 2 - 26, stats)

    if buttons:
        btn_w = 150
        btn_h = 40
        spacing = 180
        base_x = game_w // 2 - btn_w // 2 - spacing // 2
        y = game_h // 2 + 30
        padding_texto = 16
        for i, (label, color) in enumerate(buttons):
            is_sel = i == selected
            btn_color = (*color[:3], 255) if is_sel else (*color[:3], 120)
            bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            pygame.draw.rect(bg, btn_color, (0, 0, btn_w, btn_h), border_radius=8)
            if is_sel:
                pygame.draw.rect(bg, WHITE, (0, 0, btn_w, btn_h), width=2, border_radius=8)
            surface.blit(bg, (base_x + i * spacing, y))
            txt = _texto_ajustado(label, font, WHITE, btn_w - padding_texto)
            surface.blit(txt, (base_x + i * spacing + btn_w // 2 - txt.get_width() // 2, y + btn_h // 2 - txt.get_height() // 2))


def draw_victory_screen(surface, game_w, game_h, score, wave, font, big_font, stats=None):
    overlay = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    title = render_texto_pixelado(big_font, "VICTORIA", AMARILLO)
    sub = render_texto_pixelado(font, "Has derrotado a La Anomalia Final", WHITE)
    sc_text = render_texto_pixelado(font, f"Puntuacion Final: {score}", WHITE)
    wt_text = render_texto_pixelado(font, f"Oleada Alcanzada: {wave}", AZUL)
    restart_text = render_texto_pixelado(font, "Presiona R para volver al menu", AMARILLO)

    surface.blit(title, (game_w // 2 - title.get_width() // 2, game_h // 2 - 140))
    surface.blit(sub, (game_w // 2 - sub.get_width() // 2, game_h // 2 - 100))
    surface.blit(sc_text, (game_w // 2 - sc_text.get_width() // 2, game_h // 2 - 62))
    surface.blit(wt_text, (game_w // 2 - wt_text.get_width() // 2, game_h // 2 - 36))

    _dibujar_stats_partida(surface, game_w, game_h // 2 - 4, stats)

    surface.blit(restart_text, (game_w // 2 - restart_text.get_width() // 2, game_h // 2 + 48))


def draw_boss_rewards(surface, boss_name, rewards, x, y):
    if not rewards:
        return
    title_surf = render_text(f"RECOMPENSAS: {boss_name}", 16, AMARILLO)
    surface.blit(title_surf, (x - title_surf.get_width() // 2, y))
    for i, reward in enumerate(rewards):
        color = ROSA if i % 2 == 0 else AZUL
        label_surf = render_text(f"{reward.label} - {reward.description}", 14, color)
        surface.blit(label_surf, (x - label_surf.get_width() // 2, y + 22 + i * 20))
