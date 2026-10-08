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
    GAME_WIDTH, GAME_HEIGHT, GLASS_WHITE, GLASS_BLACK, SHADOW, BUFF_TYPE_EXTRA_LIFE,
    BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT, BUFF_TYPE_SHIELD,
    BUFF_TYPE_PIERCING, BUFF_TYPE_ATTRACT, BUFF_TYPE_DAMAGE_UP,
    BUFF_TYPE_SPEED_UP, BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_RAPID_FIRE,
    BUFF_TYPE_LIGHTNING,
)
from modules.systems.fonts import get_font, render_text, render_texto_pixelado
from modules.systems import neon, pixelfx


def _texto_ajustado(texto, fuente, color, ancho_maximo):
    """Renderiza texto pixelado y lo reduce (si hace falta) para que quepa
    en ancho_maximo, sin importar que fuente termine cargando el sistema en
    la maquina donde corra el juego."""
    return render_texto_pixelado(fuente, texto, color, ancho_maximo=ancho_maximo)


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


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
                fill_surf = pygame.Surface((fill_w, inner_h), pygame.SRCALPHA)

                if ratio > 0.6:
                    base_color = ROSA
                elif ratio > 0.3:
                    base_color = AMARILLO
                else:
                    base_color = MELON

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
        self.objetivos = 0
        self.objetivos_meta = 1
        self.jefe_activo = False

    def update(self, score, wave, lives, buffs, hand_active, objetivos=0, objetivos_meta=1, jefe_activo=False):
        self.score_value.set(score)
        self.score_value.update()
        self.wave_value = wave
        self.lives = lives
        self.display_lives.set(lives)
        self.display_lives.update()
        self.health_bar.set_hp(lives)
        self.buffs = buffs
        self.hand_active = hand_active
        self.objetivos = objetivos
        self.objetivos_meta = max(1, objetivos_meta)
        self.jefe_activo = jefe_activo
        self.pulse_phase += 0.06
        self.health_bar.update()
        self.fade_in = min(1.0, self.fade_in + 0.05)
        if self.score_flash > 0:
            self.score_flash -= 1
        if self.lives_pulse > 0:
            self.lives_pulse -= 1

    def draw(self, surface):
        panel_w = 200
        panel_h = 116
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

        objetivos_y = panel_y + 82
        if self.jefe_activo:
            jefe_text = render_text("¡JEFE!", 13, ROSA)
            surface.blit(jefe_text, (panel_x + 16, objetivos_y))
        else:
            objetivos_text = render_text(f"{self.objetivos}/{self.objetivos_meta}", 13, (200, 200, 220))
            surface.blit(objetivos_text, (panel_x + 16, objetivos_y))
            bar_w, bar_h = 168, 6
            bar_x = panel_x + 16
            bar_y = objetivos_y + 16
            pygame.draw.rect(surface, (30, 30, 46), (bar_x, bar_y, bar_w, bar_h), border_radius=bar_h // 2)
            frac = max(0.0, min(1.0, self.objetivos / self.objetivos_meta))
            fill_w = int(bar_w * frac)
            if fill_w > 0:
                pygame.draw.rect(surface, MENTA, (bar_x, bar_y, fill_w, bar_h), border_radius=bar_h // 2)

        self.health_bar.x = panel_x + 16
        self.health_bar.y = panel_y + 108
        self.health_bar.draw(surface)


class BuffChip:
    """Panel vertical estilo consola de nave para un buff activo: insignia
    con el icono arriba y una barra de carga vertical que se vacia con el
    tiempo restante debajo. _get_style()/_get_label() traducen el
    BUFF_TYPE_* a color/icono/texto; agregar un buff nuevo implica sumarlo
    ahi. Los buffs "eternos" (permanentes o de clase, ver `everlasting`) se
    muestran siempre a full con un brillo lento en vez de vaciarse, porque
    en la practica nunca vencen (ver Ship.apply_buff)."""

    WIDTH = 72
    HEIGHT = 118

    def __init__(self, buff_type, timer, max_timer, everlasting=False):
        self.buff_type = buff_type
        self.timer = timer
        self.max_timer = max_timer
        self.everlasting = everlasting
        self.label_font = get_font(10, bold=True)
        self.pulse_phase = random.uniform(0, math.pi * 2)
        self.fade_in = 0.0
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
        self.pulse_phase += 0.05
        self.fade_in = min(1.0, self.fade_in + 0.08)

    def draw(self, surface, x, y):
        w, h = self.WIDTH, self.HEIGHT
        radius = 10
        pulse = 0.5 + 0.5 * math.sin(self.pulse_phase)

        panel = pygame.Surface((w, h), pygame.SRCALPHA)

        # marco metalico de la consola (mismo glass que el panel de score)
        pygame.draw.rect(panel, GLASS_BLACK, (0, 0, w, h), border_radius=radius)
        pygame.draw.rect(panel, GLASS_WHITE, (0, 0, w, h), border_radius=radius)
        pygame.draw.rect(panel, (*self.color[:3], 45), (2, 2, w - 4, h - 4), border_radius=radius - 1)
        borde_alpha = int(180 + 60 * pulse) if self.everlasting else 170
        pygame.draw.rect(panel, (*self.color[:3], min(255, borde_alpha)), (0, 0, w, h), width=2, border_radius=radius)

        # remaches en las esquinas: detalle de panel de nave
        for rx, ry in ((7, 7), (w - 7, 7), (7, h - 7), (w - 7, h - 7)):
            pygame.draw.circle(panel, (255, 255, 255, 60), (rx, ry), 1.6)

        # insignia con el icono del buff
        badge_r = 15
        badge_cx, badge_cy = w // 2, 20
        glow_r = int(badge_r * 2.6)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        glow_alpha = int(90 + 60 * pulse) if self.everlasting else 70
        pygame.draw.circle(glow, (*self.color[:3], glow_alpha), (glow_r, glow_r), int(glow_r * 0.85))
        panel.blit(glow, (badge_cx - glow_r, badge_cy - glow_r))
        pygame.draw.circle(panel, (16, 16, 26), (badge_cx, badge_cy), badge_r)
        pygame.draw.circle(panel, self.color, (badge_cx, badge_cy), badge_r, 2)
        self._draw_icon(panel, badge_cx, badge_cy)

        # barra vertical de carga: se vacia de arriba hacia abajo con el
        # tiempo restante (o se queda a full, con brillo, si es "eterno")
        bar_w, bar_h = 16, 54
        bar_x = w // 2 - bar_w // 2
        bar_y = badge_cy + badge_r + 10
        pygame.draw.rect(panel, (16, 16, 24), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        frac = 1.0 if self.everlasting else clamp(self.timer / self.max_timer, 0.0, 1.0) if self.max_timer else 0.0
        fill_h = int(bar_h * frac)
        if fill_h > 0:
            fill_color = self.color
            if self.everlasting:
                fill_color = tuple(min(255, int(c * (0.85 + 0.3 * pulse))) for c in self.color[:3])
            fill_rect = (bar_x, bar_y + (bar_h - fill_h), bar_w, fill_h)
            pygame.draw.rect(panel, fill_color, fill_rect, border_radius=4)
            hl_h = max(1, fill_h // 3)
            hl = pygame.Surface((bar_w - 4, hl_h), pygame.SRCALPHA)
            for row in range(hl_h):
                a = int(70 * (1 - row / hl_h))
                pygame.draw.line(hl, (255, 255, 255, a), (0, row), (bar_w - 5, row))
            panel.blit(hl, (bar_x + 2, bar_y + (bar_h - fill_h)))

        for marca in (0.25, 0.5, 0.75):
            my = bar_y + int(bar_h * (1 - marca))
            pygame.draw.line(panel, (0, 0, 0, 90), (bar_x, my), (bar_x + bar_w, my), 1)
        pygame.draw.rect(panel, WHITE, (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)

        label = self._get_label()
        label_surf = render_texto_pixelado(self.label_font, label, WHITE)
        panel.blit(label_surf, (w // 2 - label_surf.get_width() // 2, bar_y + bar_h + 8))

        panel.set_alpha(int(255 * ease_out_cubic(self.fade_in)))
        surface.blit(panel, (x, y))

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
    """Paneles de buff activos en los margenes laterales del area de juego
    (fuera del viewport), alternando izquierda/derecha para leerse como los
    paneles de instrumentos a los costados de la ventana principal de una
    nave. Crea/elimina paneles segun los buffs aparecen o vencen."""

    def __init__(self):
        self.chips = {}

    def update(self, buffs, class_buffs=None):
        class_buffs = class_buffs or set()
        for buff_type, data in buffs.items():
            everlasting = bool(data.get("permanent", False) or buff_type in class_buffs)
            if buff_type not in self.chips:
                self.chips[buff_type] = BuffChip(buff_type, data.get("timer", 0), data.get("max_timer", 1), everlasting)
            chip = self.chips[buff_type]
            chip.timer = data.get("timer", 0)
            chip.max_timer = data.get("max_timer", 1)
            chip.everlasting = everlasting
            chip.update()

        expired = [bt for bt in self.chips if bt not in buffs]
        for bt in expired:
            del self.chips[bt]

    def draw(self, surface, offset_x=0, offset_y=0):
        if not self.chips:
            return
        slot_w, slot_h, gap = BuffChip.WIDTH, BuffChip.HEIGHT, 16
        margin_w = offset_x
        left_x = max(4, (margin_w - slot_w) // 2)
        right_x = offset_x + GAME_WIDTH + max(4, (margin_w - slot_w) // 2)
        start_y = offset_y + 12

        for idx, chip in enumerate(self.chips.values()):
            columna_izq = idx % 2 == 0
            fila = idx // 2
            x = left_x if columna_izq else right_x
            y = start_y + fila * (slot_h + gap)
            chip.draw(surface, x, y)


def draw_hud(surface, score, wave, lives, buffs, font, small_font, hand_active=False, max_hp=3,
             objetivos=0, objetivos_meta=1, jefe_activo=False):
    if not hasattr(draw_hud, 'hud'):
        draw_hud.hud = ModernHUD(max_hp)
    hud = draw_hud.hud
    hud.health_bar.max_hp = max_hp
    hud.update(score, wave, lives, buffs, hand_active, objetivos, objetivos_meta, jefe_activo)
    hud.draw(surface)


def draw_buff_hud(surface, buffs, offset_x=0, offset_y=0, class_buffs=None):
    if not hasattr(draw_buff_hud, 'hud'):
        draw_buff_hud.hud = BuffHUD()
    hud = draw_buff_hud.hud
    hud.update(buffs, class_buffs)
    hud.draw(surface, offset_x, offset_y)


def draw_ship_status_bar(surface, lives, max_lives, offset_x, offset_y, ticks=0):
    """Consola de vida de la nave en el margen inferior (fuera del
    viewport): un segmento iluminado por vida restante, estilo panel de
    nave, en vez de una barra continua (mas legible con pocas vidas). Se
    dibuja aparte de la barrita chica del panel de score, mas visible."""
    max_lives = max(1, int(max_lives))
    cx = offset_x + GAME_WIDTH // 2
    bar_y = offset_y + GAME_HEIGHT + 12

    seg_w, seg_h, seg_gap = 34, 16, 6
    total_w = max_lives * seg_w + (max_lives - 1) * seg_gap
    start_x = cx - total_w // 2

    label = render_texto_pixelado(get_font(12, bold=True), "CASCO", (205, 215, 235))
    surface.blit(label, (start_x - label.get_width() - 12, bar_y + seg_h // 2 - label.get_height() // 2))

    ratio = lives / max_lives if max_lives else 0
    color = ROSA if ratio > 0.5 else (AMARILLO if ratio > 0.25 else MELON)
    pulse = 0.5 + 0.5 * math.sin(ticks * 0.008)

    for i in range(max_lives):
        seg_x = start_x + i * (seg_w + seg_gap)
        rect = (seg_x, bar_y, seg_w, seg_h)
        if i < lives:
            fill_color = color
            if lives == 1 and max_lives > 1:
                # ultima vida: parpadea como alarma de casco critico
                fill_color = tuple(min(255, int(c * (0.6 + 0.5 * pulse))) for c in color[:3])
            pygame.draw.rect(surface, fill_color, rect, border_radius=3)
            hl_h = max(1, seg_h // 3)
            hl = pygame.Surface((seg_w - 4, hl_h), pygame.SRCALPHA)
            for row in range(hl_h):
                a = int(80 * (1 - row / hl_h))
                pygame.draw.line(hl, (255, 255, 255, a), (0, row), (seg_w - 5, row))
            surface.blit(hl, (seg_x + 2, bar_y + 2))
        else:
            pygame.draw.rect(surface, (22, 22, 34), rect, border_radius=3)
        pygame.draw.rect(surface, (*AZUL_CIELO[:3], 190), rect, width=1, border_radius=3)

    ship_x = start_x + total_w + 18
    ship_y = bar_y + seg_h // 2
    pygame.draw.polygon(surface, AZUL_CIELO, [
        (ship_x, ship_y - 8), (ship_x - 7, ship_y + 7), (ship_x, ship_y + 3), (ship_x + 7, ship_y + 7),
    ])


def draw_viewport_frame(surface, x, y, w, h, timestamp):
    """Marco del area de juego con resplandor pulsante y acentos en las
    esquinas, para que el borde se sienta parte del espacio de fondo (donde
    ya se dibujaron estrellas) en vez de una linea plana y estatica."""
    pulse = 0.5 + 0.5 * math.sin(timestamp * 0.0015)

    glow_surf = pygame.Surface((w + 64, h + 64), pygame.SRCALPHA)
    base_alpha = 22 + int(14 * pulse)
    for i in range(5):
        expand = i * 6
        alpha = max(0, base_alpha - i * 4)
        pygame.draw.rect(
            glow_surf, (*AZUL_CIELO[:3], alpha),
            (30 - expand, 30 - expand, w + 4 + expand * 2, h + 4 + expand * 2),
            width=2, border_radius=8,
        )
    surface.blit(glow_surf, (x - 32, y - 32))

    pygame.draw.rect(surface, AZUL, (x - 2, y - 2, w + 4, h + 4), width=2, border_radius=4)

    corner = 18
    for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        pygame.draw.line(surface, WHITE, (cx, cy), (cx + dx * corner, cy), 2)
        pygame.draw.line(surface, WHITE, (cx, cy), (cx, cy + dy * corner), 2)


def draw_camera_preview(surface, preview_surf, preview_rect, timestamp):
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


def draw_countdown(surface, game_w, game_h, countdown_val, countdown_fraction, font, info_font, big_font, control_hint=""):
    """Pantalla de preparacion antes de que arranque la partida, en pixel
    art neon: un anillo de bloques que se van apagando con el tiempo
    restante y el numero grande en el centro, sobre el fondo de estrellas
    que ya dibujo el llamador. countdown_fraction va de 1.0 (recien
    empezo) a 0.0 (arranca la partida)."""
    t = pygame.time.get_ticks() // 16
    cx, cy = game_w // 2, game_h // 2 - 20
    radio = 84

    neon.titulo(surface, "NAVE VS ASTEROIDES", 22, (170, 190, 255), cx, cy - radio - 70, halo=False)

    frac = max(0.0, min(1.0, countdown_fraction))
    segmentos = 28
    encendidos = int(round(frac * segmentos))
    pixelfx.dibujar_halo(surface, neon.CIAN, cx, cy, radio + 40)
    for i in range(segmentos):
        a = -math.pi / 2 + 2 * math.pi * i / segmentos
        x, y = cx + math.cos(a) * radio, cy + math.sin(a) * radio
        if i < encendidos:
            color = neon.CIAN if i < encendidos - 1 or (t // 6) % 2 else WHITE
            neon.cuadro_pixel(surface, neon.CONTORNO, x, y, 14)
            neon.cuadro_pixel(surface, color, x, y, 10)
        else:
            neon.cuadro_pixel(surface, (40, 30, 80), x, y, 8)

    neon.titulo(surface, str(countdown_val), 86, WHITE, cx, cy + 4)
    neon.cinta(surface, "PREPARATE", neon.CIAN, (cx, cy + radio + 34), tam=16)

    if control_hint:
        hint = render_texto_pixelado(get_font(14), control_hint, (150, 160, 200))
        surface.blit(hint, (game_w // 2 - hint.get_width() // 2, cy + radio + 62))


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


def _pantalla_final(surface, game_w, game_h, color):
    """Velo oscuro + panel neon de las pantallas de fin de partida."""
    neon.velo(surface, (6, 2, 20), 175)
    caja = pygame.Rect(0, 0, 620, 268)
    caja.midtop = (game_w // 2, game_h // 2 - 178)
    neon.panel(surface, caja, color, pygame.time.get_ticks() // 16)
    return caja


def draw_game_over(surface, game_w, game_h, score, wave, font, big_font, buttons=None, selected=0, stats=None):
    caja = _pantalla_final(surface, game_w, game_h, neon.ROJO)
    neon.titulo(surface, "GAME OVER", 50, (255, 110, 140), game_w // 2, caja.y + 40)
    sc_text = render_texto_pixelado(font, f"Puntuacion Final: {score}", WHITE)
    wt_text = render_texto_pixelado(font, f"Oleada Alcanzada: {wave}", AZUL)
    surface.blit(sc_text, (game_w // 2 - sc_text.get_width() // 2, game_h // 2 - 98))
    surface.blit(wt_text, (game_w // 2 - wt_text.get_width() // 2, game_h // 2 - 72))

    _dibujar_stats_partida(surface, game_w, game_h // 2 - 40, stats)

    if buttons:
        btn_w = 150
        btn_h = 40
        spacing = 180
        base_x = game_w // 2 - btn_w // 2 - spacing // 2
        y = game_h // 2 + 30
        t = pygame.time.get_ticks() // 16
        for i, (label, color) in enumerate(buttons):
            neon.boton(surface, (base_x + i * spacing, y, btn_w, btn_h), label, color, i == selected, t)
    neon.scanlines(surface)


def draw_victory_screen(surface, game_w, game_h, score, wave, font, big_font, stats=None,
                        subtitulo="Has derrotado al Coloso"):
    caja = _pantalla_final(surface, game_w, game_h, neon.ORO)
    neon.titulo(surface, "VICTORIA", 54, AMARILLO, game_w // 2, caja.y + 42)
    sub = render_texto_pixelado(font, subtitulo, WHITE)
    sc_text = render_texto_pixelado(font, f"Puntuacion Final: {score}", WHITE)
    wt_text = render_texto_pixelado(font, f"Oleada Alcanzada: {wave}", AZUL)
    surface.blit(sub, (game_w // 2 - sub.get_width() // 2, game_h // 2 - 104))
    surface.blit(sc_text, (game_w // 2 - sc_text.get_width() // 2, game_h // 2 - 72))
    surface.blit(wt_text, (game_w // 2 - wt_text.get_width() // 2, game_h // 2 - 46))

    _dibujar_stats_partida(surface, game_w, game_h // 2 - 16, stats)

    neon.cinta(surface, "Presiona R para volver al menu", neon.ORO, (game_w // 2, game_h // 2 + 58), tam=15)
    neon.scanlines(surface)


def draw_boss_rewards(surface, boss_name, rewards, x, y):
    if not rewards:
        return
    title_surf = render_text(f"RECOMPENSAS: {boss_name}", 16, AMARILLO)
    surface.blit(title_surf, (x - title_surf.get_width() // 2, y))
    for i, reward in enumerate(rewards):
        color = ROSA if i % 2 == 0 else AZUL
        label_surf = render_text(f"{reward.label} - {reward.description}", 14, color)
        surface.blit(label_surf, (x - label_surf.get_width() // 2, y + 22 + i * 20))


# ------------------------------------------------ pantalla final (jefe bonus)

_ARCOIRIS_FINAL = [(255, 70, 70), (255, 160, 40), (255, 235, 60), (80, 230, 90), (60, 160, 255), (150, 90, 255)]


def dibujar_texto_arcoiris(surface, texto, fuente, cx, y, t, amplitud=6, contorno=True):
    """Texto centrado en cx con cada letra de un color del arcoiris que va
    rotando con el tiempo y saltando en ola (t en cuadros)."""
    letras = []
    ancho_total = 0
    for i, letra in enumerate(texto):
        color = pygame.Color(0)
        color.hsva = (((t * 3 + i * 28) % 360), 70, 100, 100)
        surf = fuente.render(letra, True, color)
        letras.append((surf, i))
        ancho_total += surf.get_width()
    x = cx - ancho_total // 2
    for surf, i in letras:
        dy = int(math.sin(t * 0.12 + i * 0.55) * amplitud)
        if contorno:
            sombra = fuente.render(texto[i], True, (20, 10, 40))
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (3, 3)):
                surface.blit(sombra, (x + ox, y + dy + oy))
        surface.blit(surf, (x, y + dy))
        x += surf.get_width()


def _confeti(surface, game_w, game_h, t, cantidad=70):
    """Confeti deterministico (depende solo de t): no necesita estado."""
    for i in range(cantidad):
        velocidad = 0.8 + (i * 37 % 100) / 60.0
        x = (i * 97 + int(math.sin(t * 0.02 + i) * 30)) % game_w
        y = int((t * velocidad + i * 53) % (game_h + 40)) - 20
        color = _ARCOIRIS_FINAL[i % len(_ARCOIRIS_FINAL)]
        giro = abs(math.sin(t * 0.08 + i))
        w = max(2, int(10 * giro)) // 2 * 2
        surface.fill(color, (x // 2 * 2 - w // 2, y // 2 * 2, w, 6))


def draw_victory_final(surface, game_w, game_h, score, wave, stats, texto_record, nuevo_record, t,
                       icono=None):
    """Pantalla de victoria de verdad (despues del Gato OIIA): mas festiva
    que draw_victory_screen -confeti, titulo arcoiris, franja estilo Nyan y
    las estadisticas en cartas neon como las de mejora-.
    icono: Surface opcional (el gatito durmiendo) para el panel."""
    # fondo: degrade violeta -> azul noche en bandas
    fondo = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
    for yy in range(0, game_h, 8):
        k = yy / game_h
        fondo.fill((int(40 - 26 * k), int(14 + 8 * k), int(70 + 20 * k), 220), (0, yy, game_w, 8))
    surface.blit(fondo, (0, 0))
    _confeti(surface, game_w, game_h, t)

    # franja arcoiris ondulada detras del titulo
    franja_y = 58
    for i, color in enumerate(_ARCOIRIS_FINAL):
        for sx in range(0, game_w, 16):
            ondula = 4 if ((sx // 16) + t // 8) % 2 else 0
            surface.fill(color, (sx, franja_y + i * 7 + ondula, 16, 7))

    dibujar_texto_arcoiris(surface, "¡VICTORIA TOTAL!", get_font(60, bold=True), game_w // 2, 40, t)
    sub = render_texto_pixelado(get_font(20), "Derrotaste a Nyan Cat y su pandilla... y el gatito ya duerme", WHITE)
    surface.blit(sub, (game_w // 2 - sub.get_width() // 2, 132))

    # panel central con el marco que cambia de color
    card = pygame.Rect(game_w // 2 - 330, 170, 660, 330)
    borde = pygame.Color(0)
    borde.hsva = ((t * 2) % 360, 60, 100, 100)
    neon.panel(surface, card, tuple(borde)[:3], t)

    stats = stats or {}
    disparos = stats.get("disparos", 0)
    precision = int(round(100 * stats.get("aciertos", 0) / disparos)) if disparos > 0 else 0
    chips = [
        ("PUNTUACION", f"{score}", AMARILLO),
        ("OLEADA", f"{wave}", AZUL),
        ("JEFES", f"{stats.get('jefes', 0)}", ROSA),
        ("PRECISION", f"{precision}%", MENTA),
        ("TIEMPO", formatear_tiempo(stats.get("tiempo", 0)), LAVANDA),
        ("ENEMIGOS", f"{stats.get('asteroides', 0) + stats.get('alienigenas', 0)}", MELON),
    ]
    chip_w, chip_h = 190, 78
    for i, (etiqueta, valor, color) in enumerate(chips):
        col, fila = i % 3, i // 3
        cx = card.x + 30 + col * (chip_w + 10)
        cy = card.y + 28 + fila * (chip_h + 12) + int(math.sin(t * 0.06 + i) * 2)
        chip = pygame.Rect(cx, cy, chip_w, chip_h)
        surface.fill(neon.CONTORNO, chip.inflate(6, 6))
        surface.fill((34, 20, 70), chip)
        neon.marco_pixel(surface, chip, color, 3)
        neon.cinta(surface, etiqueta, color, (chip.centerx, chip.y + 14), tam=11)
        va = render_texto_pixelado(get_font(30, bold=True), valor, WHITE)
        surface.blit(va, (chip.centerx - va.get_width() // 2, cy + 32))

    # gatito durmiendo + Zzz en la parte baja del panel
    base_y = card.y + 232
    if icono is not None:
        surface.blit(icono, (card.x + 40, base_y + 6))
        for k in range(3):
            fase = (t * 0.02 + k / 3) % 1.0
            z = render_text("z" if k < 2 else "Z", 14 + k * 5, (220, 220, 255))
            z.set_alpha(int(255 * (1 - fase)))
            surface.blit(z, (card.x + 40 + icono.get_width() - 8 + k * 12, base_y - int(fase * 30) + 4))

    pulso = 0.5 + 0.5 * math.sin(t * 0.15)
    color_record = AMARILLO if nuevo_record else WHITE
    if nuevo_record:
        color_record = (255, int(200 + 55 * pulso), int(90 + 100 * pulso))
    centro_x = card.x + 250 + (card.w - 250) // 2
    if nuevo_record:
        neon.cinta(surface, "¡NUEVO RÉCORD!", neon.ORO, (centro_x, base_y + 4), tam=13)
    rec = render_texto_pixelado(get_font(22, bold=True), texto_record, color_record)
    surface.blit(rec, (centro_x - rec.get_width() // 2, base_y + 20))
    gracias = render_texto_pixelado(get_font(15), "¡Gracias por jugar!", ROSA_CHICLE)
    surface.blit(gracias, (centro_x - gracias.get_width() // 2, base_y + 56))

    # boton de salida neon con el color que rota
    color_pill = pygame.Color(0)
    color_pill.hsva = ((t * 2 + 180) % 360, 45, 100, 100)
    neon.boton(surface, (game_w // 2 - 190, card.bottom + 26, 380, 40), "ENTER / R  -  volver al menu",
               tuple(color_pill)[:3], True, t)
    neon.scanlines(surface)
