"""
Jefes de oleada: uno cada 10 oleadas si o si (10, 20, 30, 40) y el
mega-jefe final en la oleada 50 (constants.MEGA_BOSS_SPAWN_WAVE, ver
modules/entities/mega_boss.py). BossDefinition describe cada jefe por
datos (vida, velocidad, patrones, colores, recompensas) y WaveBoss es la
instancia jugable que lee esos datos, asi que agregar un jefe nuevo es
sumar una BossDefinition a BOSS_DEFINITIONS sin tocar la logica de WaveBoss."""

import pygame
import random
import math
from modules.constants import (
    ROSA, AMARILLO, AZUL, AZUL_CIELO, MELON, LAVANDA, ROSA_CHICLE, MENTA,
    WHITE, DARK_BG, GAME_WIDTH, GAME_HEIGHT, SHIP_WIDTH, SHIP_HEIGHT,
    BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_SPEED_UP, BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_RAPID_FIRE,
    BUFF_DURATION_DAMAGE_UP, BUFF_DURATION_SPEED_UP, BUFF_DURATION_MAX_LIFE_UP, BUFF_DURATION_RAPID_FIRE,
    BUFF_TYPE_EXTRA_LIFE, BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT, BUFF_TYPE_SHIELD, BUFF_TYPE_PIERCING, BUFF_TYPE_ATTRACT,
    BUFF_DURATION, BUFF_DURATION_FAST, BUFF_DURATION_TRIPLE, BUFF_DURATION_SHIELD, BUFF_DURATION_PIERCING, BUFF_DURATION_ATTRACT,
    FINAL_BOSS_SPAWN_WAVE,
)
from modules.systems.fonts import render_text
from modules.systems import sprites


class BossDefinition:
    """Datos fijos de un jefe de oleada: cuando aparece, cuanta vida y
    velocidad tiene, que patrones de ataque puede usar, sus colores (para
    tintar el sprite) y las BossReward que suelta al morir."""

    def __init__(self, boss_id, name, spawn_wave, max_hp, speed, shoot_rate,
                 attack_patterns, primary_color, secondary_color, glow_color,
                 rewards, body_type="saucer"):
        self.boss_id = boss_id
        self.name = name
        self.spawn_wave = spawn_wave
        self.max_hp = max_hp
        self.speed = speed
        self.shoot_rate = shoot_rate
        self.attack_patterns = attack_patterns
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.glow_color = glow_color
        self.rewards = rewards
        self.body_type = body_type


class BossReward:
    """Un buff que un jefe reparte al ser derrotado (se muestra en el panel
    de "Jefe Derrotado" y se entrega como PowerUp; ver draw_boss_rewards en
    modules/systems/ui.py y su uso en main.py)."""

    def __init__(self, buff_type, label, description, duration=0):
        self.buff_type = buff_type
        self.label = label
        self.description = description
        self.duration = duration


BOSS_DEFINITIONS = [
    BossDefinition(
        boss_id="sentinel",
        name="Centinela Corrupto",
        spawn_wave=10,
        max_hp=160,
        speed=1.2,
        shoot_rate=28,
        attack_patterns=["SPREAD", "AIMED", "CIRCULAR"],
        primary_color=(170, 170, 180),
        secondary_color=(80, 200, 160),
        glow_color=(100, 200, 255, 60),
        rewards=[
            BossReward(BUFF_TYPE_SHIELD, "DEF", "Escudo +1 golpe", BUFF_DURATION_SHIELD),
            BossReward(BUFF_TYPE_EXTRA_LIFE, "+1", "Vida extra", 0),
        ],
        body_type="saucer",
    ),
    BossDefinition(
        boss_id="dragon",
        name="Dragon Espacial",
        spawn_wave=20,
        max_hp=420,  # informativo: DragonBoss trae su propio max_hp, ver dragon_boss.py
        speed=1.6,
        shoot_rate=22,
        attack_patterns=["SPREAD", "AIMED", "CIRCULAR", "SPIRAL"],
        primary_color=(220, 100, 80),
        secondary_color=(255, 160, 60),
        glow_color=(255, 120, 60, 70),
        rewards=[
            BossReward(BUFF_TYPE_RAPID_FIRE, "RAPID", "Disparo rapido permanente", BUFF_DURATION_RAPID_FIRE),
            BossReward(BUFF_TYPE_FAST_SHOOT, "FAST", "Cadencia mejorada", BUFF_DURATION_FAST),
        ],
        body_type="dragon",
    ),
    BossDefinition(
        boss_id="titan",
        name="Titan del Vacío",
        spawn_wave=30,
        max_hp=550,  # informativo: TitanBoss trae su propio max_hp, ver titan_boss.py
        speed=1.0,
        shoot_rate=18,
        attack_patterns=["SPREAD", "AIMED", "CIRCULAR", "SPIRAL", "RAIN", "LASER"],
        primary_color=(140, 100, 220),
        secondary_color=(200, 160, 255),
        glow_color=(180, 140, 255, 80),
        rewards=[
            BossReward(BUFF_TYPE_DAMAGE_UP, "DMG+", "Daño aumentado permanente", BUFF_DURATION_DAMAGE_UP),
            BossReward(BUFF_TYPE_PIERCING, "PEN", "Balas penetrantes", BUFF_DURATION_PIERCING),
        ],
        body_type="titan",
    ),
    BossDefinition(
        boss_id="anomalia",
        name="La Anomalía Final",
        spawn_wave=FINAL_BOSS_SPAWN_WAVE,
        max_hp=800,  # informativo: FinalBoss trae su propio max_hp, ver boss.py
        speed=1.4,
        shoot_rate=14,
        attack_patterns=["SPREAD", "AIMED", "CIRCULAR", "SPIRAL", "RAIN", "LASER", "MINE"],
        primary_color=(255, 130, 150),
        secondary_color=(100, 220, 180),
        glow_color=(255, 80, 120, 90),
        rewards=[
            BossReward(BUFF_TYPE_MAX_LIFE_UP, "MAX+", "Vida maxima +1", BUFF_DURATION_MAX_LIFE_UP),
            BossReward(BUFF_TYPE_SPEED_UP, "SPD+", "Velocidad permanente", BUFF_DURATION_SPEED_UP),
            BossReward(BUFF_TYPE_TRIPLE_SHOT, "3X", "Rafaga triple permanente", BUFF_DURATION_TRIPLE),
        ],
        body_type="anomaly",
    ),
]


def get_boss_for_wave(wave):
    """BossDefinition que arranca en esta oleada, o None si no hay ninguno."""
    for definition in BOSS_DEFINITIONS:
        if wave == definition.spawn_wave:
            return definition
    return None


class WaveBossBullet:
    """Bala de un WaveBoss; color/radius variables para poder diferenciar
    el patron LASER y las minas del resto de los disparos."""

    def __init__(self, x, y, vx=0, vy=5.0, color=ROSA, radius=4):
        self.x = x
        self.y = y
        self.radius = radius
        self.vx = vx
        self.vy = vy
        self.speed = math.sqrt(vx * vx + vy * vy)
        self.active = True
        self.trail = []
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        if self.y > GAME_HEIGHT + 10 or self.y < -10 or self.x < -10 or self.x > GAME_WIDTH + 10:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(80 * (i / len(self.trail)))
            size = max(1, int(self.radius * (i / len(self.trail))))
            trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*self.color[:3], alpha), (size, size), size)
            screen.blit(trail_surf, (int(tx) + offset_x - size, int(ty) + offset_y - size))
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color[:3], 70), (self.radius * 2, self.radius * 2), self.radius * 2)
        screen.blit(glow_surf, (cx - self.radius * 2, cy - self.radius * 2))
        pygame.draw.circle(screen, self.color, (cx, cy), self.radius)
        pygame.draw.circle(screen, AMARILLO, (cx, cy), self.radius - 1)
        pygame.draw.circle(screen, WHITE, (cx, cy), max(1, self.radius - 2))


class WaveBoss:
    """Instancia jugable de un jefe de oleada, construida a partir de una
    BossDefinition. Como FinalBoss, sube de fase al pasar 66%/33% de vida y
    usa el sprite que corresponda a definition.body_type (saucer/dragon/
    titan) si esta disponible en assets/sprites/boss."""

    def __init__(self, definition, dificultad=1.0):
        self.definition = definition
        self.x = GAME_WIDTH // 2
        self.y = 80
        self.target_x = self.x
        self.target_y = self.y
        self.active = True
        # La dificultad elegida en el menu escala tambien a los jefes (antes
        # solo afectaba asteroides/alienigenas comunes): en dificil pegan
        # mas rapido y aguantan mas; en facil, menos.
        self.max_hp = max(1, int(definition.max_hp * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.rotation = 0
        self.rot_speed = 0.5
        self.speed = definition.speed * dificultad
        self.shoot_timer = 20
        self.shoot_rate = max(6, int(definition.shoot_rate / dificultad))
        self.phase = 1
        self.damaged_timer = 0
        self.particles = []
        self.attack_pattern = definition.attack_patterns[0]
        self.pattern_timer = 0
        self.pattern_duration = 180
        self.move_timer = 0
        self.move_cooldown = 90
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.phase_transition = False
        self.phase_timer = 0
        self.special_attack_timer = 0
        self.enter_timer = 60
        self.enter_done = False
        self.body_color = definition.primary_color
        self.secondary_color = definition.secondary_color
        self.glow_color = definition.glow_color
        self.rewarded = False

    def take_damage(self, amount=1):
        if self.enter_timer > 0:
            return
        prev_hp = self.hp
        self.hp = max(0, self.hp - amount)
        if prev_hp > self.hp:
            self.health_deplete_anim = prev_hp / self.max_hp
        self.damaged_timer = 10
        self.health_shake = 10
        if self.hp <= 0:
            self.active = False
        hp_ratio = self.hp / self.max_hp
        if hp_ratio < 0.66 and self.phase == 1:
            self.phase = 2
            self.phase_transition = True
            self.phase_timer = 60
            self.pattern_duration = 140
        elif hp_ratio < 0.33 and self.phase == 2:
            self.phase = 3
            self.phase_transition = True
            self.phase_timer = 60
            self.pattern_duration = 100
            self.shoot_rate = max(10, self.shoot_rate - 4)

    def update(self, ship=None):
        if self.enter_timer > 0:
            self.enter_timer -= 1
            self.y += (80 - self.y) * 0.05
            if self.enter_timer <= 0:
                self.enter_done = True
            self.rotation += self.rot_speed
            return None

        if self.phase_transition:
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase_transition = False

        self._update_movement()
        self.rotation += self.rot_speed
        self.shoot_timer -= 1
        self.damaged_timer = max(0, self.damaged_timer - 1)
        self.pattern_timer += 1
        self.special_attack_timer += 1

        if self.pattern_timer >= self.pattern_duration:
            self.pattern_timer = 0
            self._choose_pattern()

        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_rate
            return self._create_attack(ship)

        if self.hp <= 0:
            self.active = False

        if self.damaged_timer > 0 and random.random() < 0.4:
            self.particles.append({
                'x': self.x + random.uniform(-15, 15),
                'y': self.y + random.uniform(-10, 10),
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-2, 2),
                'life': random.randint(15, 35),
                'max_life': 35,
                'radius': random.randint(2, 5),
            })

        alive_particles = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] > 0:
                alive_particles.append(p)
        self.particles = alive_particles

        if self.health_deplete_anim > self.hp / self.max_hp:
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.025)

        return None

    def _update_movement(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 10:
            self.move_timer += 1
            if self.move_timer >= self.move_cooldown:
                self.move_timer = 0
                padding = 80
                self.target_x = random.randint(padding, GAME_WIDTH - padding)
                self.target_y = random.randint(40, GAME_HEIGHT // 2 - 30)
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
        self.x = max(60, min(GAME_WIDTH - 60, self.x))
        self.y = max(30, min(GAME_HEIGHT // 2 - 10, self.y))

    def _choose_pattern(self):
        available = list(self.definition.attack_patterns)
        if len(available) > 1:
            available.remove(self.attack_pattern)
        self.attack_pattern = random.choice(available)

    def _create_attack(self, ship=None):
        if self.attack_pattern == "SPREAD":
            return self._create_spread()
        elif self.attack_pattern == "AIMED":
            return self._create_aimed(ship)
        elif self.attack_pattern == "CIRCULAR":
            return self._create_circular()
        elif self.attack_pattern == "SPIRAL":
            return self._create_spiral()
        elif self.attack_pattern == "RAIN":
            return self._create_rain()
        elif self.attack_pattern == "LASER":
            return self._create_laser(ship)
        elif self.attack_pattern == "MINE":
            return self._create_mine()
        return []

    def _create_spread(self):
        bullets = []
        for i in range(-2, 3):
            bullets.append(WaveBossBullet(self.x + i * 25, self.y + 20, 0, 5, self.secondary_color))
        return bullets

    def _create_aimed(self, ship):
        bullets = []
        if ship is None:
            return bullets
        for i in range(3):
            angle = math.atan2(ship.y - self.y, ship.x - self.x)
            angle += random.uniform(-0.2, 0.2)
            speed = 4.5 + i * 0.4
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            bullets.append(WaveBossBullet(self.x, self.y + 20, vx, vy, self.secondary_color))
        return bullets

    def _create_circular(self):
        bullets = []
        count = 12
        for i in range(count):
            angle = (2 * math.pi * i) / count
            speed = 3.5
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            bullets.append(WaveBossBullet(self.x, self.y, vx, vy, self.secondary_color))
        return bullets

    def _create_spiral(self):
        bullets = []
        count = 8
        base_angle = self.pattern_timer * 0.2
        for i in range(count):
            angle = base_angle + (2 * math.pi * i) / count
            speed = 3.0
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            bullets.append(WaveBossBullet(self.x, self.y, vx, vy, self.secondary_color))
        return bullets

    def _create_rain(self):
        bullets = []
        for _ in range(5):
            x = random.randint(40, GAME_WIDTH - 40)
            bullets.append(WaveBossBullet(x, -10, 0, 4, self.secondary_color))
        return bullets

    def _create_laser(self, ship=None):
        bullets = []
        if ship is None:
            return bullets
        angle = math.atan2(ship.y - self.y, ship.x - self.x)
        for i in range(5):
            spread = random.uniform(-0.3, 0.3)
            speed = 6.0
            vx = math.cos(angle + spread) * speed
            vy = math.sin(angle + spread) * speed
            bullets.append(WaveBossBullet(self.x, self.y + 20, vx, vy, self.glow_color, 6))
        return bullets

    def _create_mine(self):
        bullets = []
        for _ in range(3):
            x = random.randint(60, GAME_WIDTH - 60)
            bullets.append(WaveBossBullet(x, random.randint(40, 200), 0, 0, ROSA_CHICLE, 8))
        return bullets

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        if self.enter_timer > 0:
            alpha = int(255 * (1 - self.enter_timer / 60))
            ghost_surf = pygame.Surface((120, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(ghost_surf, (*self.body_color[:3], alpha), (0, 0, 120, 60))
            screen.blit(ghost_surf, (cx - 60, cy - 30))
            return

        shadow_surf = pygame.Surface((176, 34), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 50), (0, 0, 176, 34))
        screen.blit(shadow_surf, (cx - 88, cy + 48))

        ancho_sprite, alto_sprite = sprites.BOSS_DISPLAY_W, sprites.BOSS_DISPLAY_H
        sprite = sprites.get_boss_surface(self.body_color, self.secondary_color, ancho_sprite, alto_sprite,
                                          kind=self.definition.body_type)

        if sprite is not None:
            # ---- con sprite: el casco y el anillo ya vienen dibujados ----
            rect_sprite = sprite.get_rect(center=(cx, cy + 15))
            screen.blit(sprite, rect_sprite)
            body_y = rect_sprite.centery
            dome_cx = rect_sprite.centerx
            plataforma_cy = rect_sprite.top + alto_sprite * sprites.BOSS_PLATFORM_CY_FRAC
            ring_cx, ring_cy = rect_sprite.centerx, body_y
            ring_rx = ancho_sprite * sprites.BOSS_RING_RX_FRAC
            ring_ry = alto_sprite * sprites.BOSS_RING_RY_FRAC
            dome_w = int(ancho_sprite * sprites.BOSS_PLATFORM_RX_FRAC * 1.5)
            dome_h = int(alto_sprite * sprites.BOSS_PLATFORM_RY_FRAC * 2.6)
            dome_y = int(plataforma_cy - dome_h * 0.62)
        else:
            # Sin PNG en assets/sprites/boss no se dibuja un casco de
            # respaldo por codigo: se mantienen las mismas coordenadas
            # relativas para que la cupula/anillo de luces/piloto y el
            # destello de cambio de fase (los "detalles" animados de mas
            # abajo) sigan ubicados en su lugar aunque no haya casco visible.
            body_w = 140
            body_h = 30
            body_y = cy + 15
            dome_cx = cx
            ring_cx, ring_cy = cx, body_y
            ring_rx, ring_ry = body_w // 2 - 12, body_h // 2 - 4
            dome_w, dome_h = 80, 32
            dome_y = body_y - body_h // 2 - dome_h + 8

        dome_surf = pygame.Surface((dome_w, dome_h), pygame.SRCALPHA)
        dome_color = (*self.secondary_color[:3], 160) if not self.phase_transition else (
            max(0, min(255, int(self.secondary_color[0] + 40 * math.sin(self.rotation * 5)))),
            self.secondary_color[1], self.secondary_color[2], 200
        )
        pygame.draw.ellipse(dome_surf, dome_color, (0, 0, dome_w, dome_h))
        pygame.draw.ellipse(dome_surf, (*self.secondary_color[:3], 120), (0, 0, dome_w, dome_h), 1)
        screen.blit(dome_surf, (dome_cx - dome_w // 2, dome_y))

        num_lights = 12
        for i in range(num_lights):
            angle = (2 * math.pi * i) / num_lights + self.rotation * 0.03
            lx = ring_cx + math.cos(angle) * ring_rx
            ly = ring_cy + math.sin(angle) * ring_ry
            color = [ROSA, AMARILLO, AZUL, MENTA, LAVANDA, MELON][i % 6]
            blink = 0.6 + 0.4 * math.sin(self.rotation * 0.8 + i * 0.5)
            c = (int(color[0] * blink), int(color[1] * blink), int(color[2] * blink))
            pygame.draw.circle(screen, c, (int(lx), int(ly)), 5)

        pilot_x = dome_cx
        pilot_y = dome_y + 10
        pygame.draw.circle(screen, MENTA, (pilot_x, pilot_y), 9)
        pygame.draw.circle(screen, (80, 200, 160), (pilot_x, pilot_y), 9, 1)
        pygame.draw.circle(screen, WHITE, (pilot_x - 5, pilot_y - 3), 4)
        pygame.draw.circle(screen, WHITE, (pilot_x + 5, pilot_y - 3), 4)
        pygame.draw.circle(screen, (0, 0, 0), (pilot_x - 5, pilot_y - 3), 2)
        pygame.draw.circle(screen, (0, 0, 0), (pilot_x + 5, pilot_y - 3), 2)
        pygame.draw.line(screen, (180, 180, 180), (pilot_x, pilot_y - 9), (pilot_x, pilot_y - 20), 2)
        antenna_glow = max(0, min(255, int(180 + 120 * math.sin(self.rotation * 2.5))))
        _glow = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(_glow, (255, 130, 150, antenna_glow), (4, 4), 3)
        screen.blit(_glow, (pilot_x - 4, pilot_y - 21))

        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(20, 35)
            px = dome_cx + math.cos(angle) * dist
            py = dome_y + 10 + math.sin(angle) * dist
            _p = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(_p, (100, 255, 200, 60), (3, 3), 2)
            screen.blit(_p, (int(px) - 3, int(py) - 3))

        glow_r = 28
        glow_surf = pygame.Surface((glow_r * 2, glow_r), pygame.SRCALPHA)
        glow_color = self.glow_color if len(self.glow_color) == 4 else (*self.glow_color[:3], 70)
        if self.phase == 2:
            glow_color = (200, 100, 255, 80)
        elif self.phase == 3:
            glow_color = (255, 80, 120, 90)
        pygame.draw.ellipse(glow_surf, glow_color, (0, 0, glow_r * 2, glow_r))
        screen.blit(glow_surf, (dome_cx - glow_r, body_y + 8))

        bar_w = 130
        bar_h = 12
        bar_x = dome_cx - bar_w // 2
        bar_y = dome_y - 32
        hp_ratio = max(0, self.hp / self.max_hp)
        display_ratio = self.health_deplete_anim

        shake_x = 0
        shake_y = 0
        if self.health_shake > 0:
            shake_x = random.randint(-self.health_shake, self.health_shake)
            shake_y = random.randint(-self.health_shake, self.health_shake)
            self.health_shake -= 1

        draw_bar_x = bar_x + shake_x
        draw_bar_y = bar_y + shake_y

        shadow_surf = pygame.Surface((bar_w + 6, bar_h + 6), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60), (3, 3, bar_w, bar_h), border_radius=bar_h // 2)
        screen.blit(shadow_surf, (draw_bar_x - 3, draw_bar_y - 3))

        bg_rect = (draw_bar_x, draw_bar_y, bar_w, bar_h)
        pygame.draw.rect(screen, (20, 20, 35), bg_rect, border_radius=bar_h // 2)

        fill_w = int((bar_w - 2) * display_ratio)
        if fill_w > 0:
            if hp_ratio > 0.66:
                hp_color = ROSA
            elif hp_ratio > 0.33:
                hp_color = AMARILLO
            else:
                hp_color = MELON
            pygame.draw.rect(screen, hp_color, (draw_bar_x + 1, draw_bar_y + 1, fill_w, bar_h - 2), border_radius=bar_h // 2)

            hl_h = max(1, bar_h // 3)
            hl_surf = pygame.Surface((fill_w, hl_h), pygame.SRCALPHA)
            for row in range(hl_h):
                a = int(70 * (1 - row / hl_h))
                pygame.draw.line(hl_surf, (255, 255, 255, a), (0, row), (fill_w - 1, row))
            screen.blit(hl_surf, (draw_bar_x + 1, draw_bar_y + 1))

        pygame.draw.rect(screen, WHITE, bg_rect, width=1, border_radius=bar_h // 2)

        pct = f"{int(hp_ratio * 100)}%"
        pct_surf = render_text(pct, 10, WHITE)
        screen.blit(pct_surf, (cx - pct_surf.get_width() // 2, draw_bar_y - 14))

        if self.phase_transition:
            if sprite is not None:
                trans_w, trans_h, trans_top = ancho_sprite, alto_sprite, rect_sprite.top
            else:
                trans_w, trans_h, trans_top = body_w, body_h + dome_h, body_y - body_h // 2 - dome_h
            trans_alpha = int(150 * (0.5 + 0.5 * math.sin(self.phase_timer * 0.5)))
            trans_surf = pygame.Surface((trans_w + 40, trans_h + 40), pygame.SRCALPHA)
            pygame.draw.rect(trans_surf, (255, 255, 255, trans_alpha), (20, 20, trans_w, trans_h), border_radius=10)
            screen.blit(trans_surf, (dome_cx - trans_w // 2 - 20, trans_top - 20))

        if self.damaged_timer > 0:
            flash_alpha = int(140 * (self.damaged_timer / 10))
            flash_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 130, 150, flash_alpha), (40, 40), 40)
            screen.blit(flash_surf, (cx - 40, cy - 20))

        for p in self.particles:
            alpha = p['life'] / p['max_life']
            size = max(1, int(p['radius'] * alpha))
            c = (int(255 * alpha), int(120 * alpha), int(40 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)
