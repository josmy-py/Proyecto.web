"""
Nave del jugador: movimiento hacia la posicion de la mano, disparo,
sistema de vidas/invencibilidad temporal y todos los buffs recogibles
(disparo rapido, rafaga triple, escudo, perforante, iman, campo electrico,
y los permanentes que sueltan los jefes)."""

import pygame
import random
import math
from modules.constants import (
    AZUL, WHITE, AZUL_CIELO, DARK_BG, GAME_WIDTH, GAME_HEIGHT, SHIP_WIDTH, SHIP_HEIGHT,
    BUFF_TYPE_EXTRA_LIFE, BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT, LAVANDA,
    BUFF_DURATION, BUFF_DURATION_FAST, BUFF_DURATION_TRIPLE, ROSA, AMARILLO,
    GLASS_WHITE, GLASS_BLACK, SHADOW,
    BUFF_TYPE_SHIELD, BUFF_TYPE_PIERCING, BUFF_TYPE_ATTRACT,
    BUFF_DURATION_SHIELD, BUFF_DURATION_PIERCING, BUFF_DURATION_ATTRACT, MENTA, MELON,
    ROSA_CHICLE, ELECTRICO,
    BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_SPEED_UP, BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_RAPID_FIRE,
    BUFF_DURATION_DAMAGE_UP, BUFF_DURATION_SPEED_UP, BUFF_DURATION_MAX_LIFE_UP, BUFF_DURATION_RAPID_FIRE,
    BUFF_TYPE_LIGHTNING, BUFF_DURATION_LIGHTNING, LIGHTNING_ZAP_INTERVAL, LIGHTNING_RADIUS,
)
from modules.entities.bullet import Bullet
from modules.skins import apply_skin_to_ship
from modules.systems import sprites


class Ship:
    """La nave del jugador. `ship_type` (scout/tank/interceptor/bomber) fija
    las estadisticas base y el buff de clase; `skin_id` fija los colores
    (ver modules/skins.py). target_x/target_y son la posicion de la mano
    detectada por MediaPipe; update() interpola la nave hacia ahi."""

    def __init__(self, x, y, ship_type="scout", skin_id="default"):
        self.ship_type = ship_type
        self.skin_id = skin_id
        self.skin_name = ""
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y
        self.width = SHIP_WIDTH
        self.height = SHIP_HEIGHT
        self.shoot_cooldown = 0
        self.base_shoot_delay = 20
        self.alive = True
        self.max_lives = 3
        self.lives = self.max_lives
        self.invincible_timer = 0
        self.thrust_particles = []
        self.buffs = {}
        self.class_buffs = set()
        self.triple_shot_active = False
        self.engine_flame_phase = 0
        self.glow_phase = 0
        self.trail_particles = []
        self.shield_hits = 0
        self.piercing_active = False
        self.attract_active = False
        self.lightning_active = False
        self.lightning_zap_cooldown = 0
        self.lightning_radius = LIGHTNING_RADIUS
        self.lightning_phase = 0
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.body_color = AZUL
        self.wing_color = AZUL_CIELO
        self.glow_color = (140, 210, 255)
        self.flame_color = AZUL
        self.name = "Scout"
        self.description = "Nave equilibrada con buena maniobrabilidad"
        self.damage_multiplier = 1.0
        self.permanent_speed_bonus = 0.0
        self.permanent_rapid_fire = False
        self._sprite = None
        self._sprite_key = None
        self.bank_angle = 0.0
        self._apply_type_stats()
        apply_skin_to_ship(self, skin_id)

    def _apply_type_stats(self):
        stats = {
            "scout": {
                "speed": 0.18,
                "shoot_delay": 20,
                "max_lives": 3,
                "body_color": AZUL,
                "wing_color": AZUL_CIELO,
                "glow_color": (140, 210, 255),
                "flame_color": AZUL,
                "name": "Scout",
                "description": "Nave equilibrada con buena maniobrabilidad",
            },
            "tank": {
                "speed": 0.13,
                "shoot_delay": 24,
                "max_lives": 3,
                "body_color": MELON,
                "wing_color": (200, 140, 100),
                "glow_color": (255, 190, 140),
                "flame_color": MELON,
                "name": "Tanque",
                "description": "Lenta pero resistente, con escudo adicional",
            },
            "interceptor": {
                "speed": 0.24,
                "shoot_delay": 16,
                "max_lives": 3,
                "body_color": LAVANDA,
                "wing_color": ROSA_CHICLE,
                "glow_color": (200, 150, 255),
                "flame_color": LAVANDA,
                "name": "Interceptor",
                "description": "Rapida y letal, pero muy fragil",
            },
            "bomber": {
                "speed": 0.11,
                "shoot_delay": 30,
                "max_lives": 3,
                "body_color": ROSA,
                "wing_color": (200, 100, 120),
                "glow_color": (255, 130, 150),
                "flame_color": ROSA,
                "name": "Bombardero",
                "description": "Lenta pero con gran potencia de fuego",
            },
        }
        data = stats.get(self.ship_type, stats["scout"])
        self.speed = data["speed"]
        self.base_shoot_delay = data["shoot_delay"]
        self.shoot_delay = self.base_shoot_delay
        self.max_lives = data["max_lives"]
        self.lives = self.max_lives
        self.body_color = data["body_color"]
        self.wing_color = data["wing_color"]
        self.glow_color = data["glow_color"]
        self.flame_color = data["flame_color"]
        self.name = data["name"]
        self.description = data["description"]

        self.class_buffs.clear()
        if self.ship_type == "tank":
            self.shield_hits = 3
            self.class_buffs.add(BUFF_TYPE_SHIELD)
        elif self.ship_type == "interceptor":
            self.shoot_delay = max(5, int(self.base_shoot_delay * 0.4))
            self.class_buffs.add(BUFF_TYPE_FAST_SHOOT)
        elif self.ship_type == "bomber":
            self.piercing_active = True
            self.class_buffs.add(BUFF_TYPE_PIERCING)

    def invalidate_sprite(self):
        """Fuerza a recomponer el sprite (se llama al cambiar de skin/color)."""
        self._sprite = None
        self._sprite_key = None

    def _get_sprite(self):
        """Sprite tintado con los colores del skin actual (None si no hay PNG)."""
        sw, sh = sprites.get_ship_size(self.ship_type, self.width, self.height)
        key = (self.ship_type, tuple(self.body_color[:3]), tuple(self.wing_color[:3]), sw, sh)
        if self._sprite is None or self._sprite_key != key:
            self._sprite = sprites.get_ship_surface(
                self.ship_type, self.body_color, self.wing_color, sw, sh
            )
            self._sprite_key = key
        return self._sprite

    def update(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        speed = (self.speed + self.permanent_speed_bonus) * 1.25
        if dist > 1.2:
            smooth = 0.16 + 0.04 * min(1.0, dist / 100)
            self.x += dx * speed * smooth
            self.y += dy * speed * smooth

        # inclinacion segun el desplazamiento horizontal
        target_bank = max(-14.0, min(14.0, -dx * 0.30))
        self.bank_angle += (target_bank - self.bank_angle) * 0.22
        self.x = max(self.width // 2, min(GAME_WIDTH - self.width // 2, self.x))
        self.y = max(self.height // 2, min(GAME_HEIGHT - self.height // 2, self.y))
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.lightning_active:
            self.lightning_phase += 0.3
            if self.lightning_zap_cooldown > 0:
                self.lightning_zap_cooldown -= 1
        if len(self.thrust_particles) > 40:
            self.thrust_particles.pop(0)
        expired = []
        for buff_type, data in self.buffs.items():
            data["timer"] -= 1
            if data["timer"] <= 0 and buff_type not in self.class_buffs and not data.get("permanent", False):
                expired.append(buff_type)
        for buff_type in expired:
            del self.buffs[buff_type]
            if buff_type == BUFF_TYPE_FAST_SHOOT:
                if not self.permanent_rapid_fire:
                    self.shoot_delay = self.base_shoot_delay
            if buff_type == BUFF_TYPE_TRIPLE_SHOT:
                self.triple_shot_active = False
            if buff_type == BUFF_TYPE_SHIELD:
                self.shield_hits = 0
            if buff_type == BUFF_TYPE_PIERCING:
                self.piercing_active = False
            if buff_type == BUFF_TYPE_ATTRACT:
                self.attract_active = False
            if buff_type == BUFF_TYPE_LIGHTNING:
                self.lightning_active = False
        self.engine_flame_phase += 0.8
        self.glow_phase += 0.12

        if len(self.trail_particles) > 25:
            self.trail_particles.pop(0)
        if random.random() < 0.6:
            self.trail_particles.append({
                'x': self.x + random.uniform(-3, 3),
                'y': self.y + self.height // 2 + random.uniform(0, 4),
                'vx': random.uniform(-0.3, 0.3),
                'vy': random.uniform(0.5, 1.5),
                'life': random.randint(20, 40),
                'max_life': 40,
                'size': random.uniform(1.5, 3.5),
            })

        alive_trail = []
        for p in self.trail_particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] > 0:
                alive_trail.append(p)
        self.trail_particles = alive_trail

    def draw(self, screen, offset_x=0, offset_y=0):
        if self.invincible_timer > 0 and self.invincible_timer % 3 < 2:
            return
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        w = self.width
        h = self.height

        for p in self.trail_particles:
            life_ratio = p['life'] / p['max_life']
            alpha = int(180 * life_ratio)
            size = max(1, int(p['size'] * life_ratio))
            c = (int(self.glow_color[0] * life_ratio), int(self.glow_color[1] * life_ratio), int(self.glow_color[2] * life_ratio))
            trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*c, alpha), (size, size), size)
            screen.blit(trail_surf, (int(p['x']) + offset_x - size, int(p['y']) + offset_y - size))

        glow_r = h * 0.95
        glow_surf = pygame.Surface((int(glow_r * 2), int(glow_r * 2)), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(self.glow_phase)
        for gi in range(3):
            gr = glow_r - gi * 9
            ga = int(14 * pulse * (1 - gi * 0.3))
            gc = (*self.glow_color[:3], max(0, ga))
            pygame.draw.circle(glow_surf, gc, (int(glow_r), int(glow_r)), max(1, int(gr)), 0)
        screen.blit(glow_surf, (cx - int(glow_r), cy - int(glow_r * 0.5)))

        sprite = self._get_sprite()

        if sprite is not None:
            sw, sh = sprite.get_size()

            shadow_surf = pygame.Surface((sw, int(sh * 0.35)), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, SHADOW, (0, 0, sw, int(sh * 0.35)))
            screen.blit(shadow_surf, (cx - sw // 2 + 3, cy + sh // 4))

            drawn = sprites.get_rotated(sprite, self.bank_angle, self._sprite_key)
            sprites.blit_centered(screen, drawn, cx, cy)
            flame_anchor = cy + sh // 2 - 6
        else:
            # respaldo vectorial si faltan los PNG de assets/sprites
            shadow_surf = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, SHADOW, (4, 4, w, h))
            screen.blit(shadow_surf, (cx - w // 2 - 4, cy - h // 2 - 4))

            body_points = [
                (cx, cy - h // 2),
                (cx - w // 2 + 6, cy + h // 3),
                (cx - w // 5, cy + h // 4),
                (cx, cy + h // 3),
                (cx + w // 5, cy + h // 4),
                (cx + w // 2 - 6, cy + h // 3),
            ]
            pygame.draw.polygon(screen, self.body_color, body_points)
            wing_l = [(cx - w // 2 + 6, cy + h // 3), (cx - w // 3, cy + h // 4 + 5), (cx - w // 4, cy + h // 3)]
            wing_r = [(cx + w // 2 - 6, cy + h // 3), (cx + w // 3, cy + h // 4 + 5), (cx + w // 4, cy + h // 3)]
            pygame.draw.polygon(screen, self.wing_color, wing_l)
            pygame.draw.polygon(screen, self.wing_color, wing_r)
            pygame.draw.circle(
                screen,
                (min(255, self.body_color[0] + 90), min(255, self.body_color[1] + 90), min(255, self.body_color[2] + 90)),
                (cx, cy - h // 4 + 2),
                3,
            )
            flame_anchor = cy + h // 3

        flame_phase = self.engine_flame_phase
        for fi in range(4):
            fy = flame_anchor + fi * 3
            fw = max(1, 6 - fi * 1 + int(math.sin(flame_phase + fi) * 1.5))
            fh = max(1, 10 - fi * 2 + int(math.sin(flame_phase * 1.3 + fi) * 2.5))
            alpha = 255 - fi * 50
            color_f = (min(255, self.flame_color[0]), max(0, self.flame_color[1] - fi * 40), max(0, self.flame_color[2] - fi * 30))
            flame_surf = pygame.Surface((fw * 2, fh), pygame.SRCALPHA)
            for row in range(fh):
                t = row / fh
                a = int(alpha * (1 - t))
                pygame.draw.line(flame_surf, (*color_f, max(0, a)), (0, row), (fw * 2 - 1, row))
            screen.blit(flame_surf, (cx - fw, fy - fh // 2))

        for tp in self.thrust_particles:
            alpha = max(0, tp[2])
            c = (int(255 * alpha), int(200 * alpha), int(50 * alpha))
            pygame.draw.circle(screen, c, (int(tp[0]) + offset_x, int(tp[1]) + offset_y), max(1, int(3 * alpha)))

        if BUFF_TYPE_SHIELD in self.buffs or BUFF_TYPE_SHIELD in self.class_buffs:
            shield_radius = w * 0.9
            shield_surf = pygame.Surface((shield_radius * 2, shield_radius * 2), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(self.glow_phase * 2)
            alpha = int(40 + 20 * pulse)
            pygame.draw.circle(shield_surf, (*MENTA[:3], alpha), (shield_radius, shield_radius), shield_radius)
            pygame.draw.circle(shield_surf, (*MENTA[:3], int(alpha * 1.5)), (shield_radius, shield_radius), shield_radius, 2)
            screen.blit(shield_surf, (cx - shield_radius, cy - shield_radius))

        if BUFF_TYPE_PIERCING in self.buffs or BUFF_TYPE_PIERCING in self.class_buffs:
            pierce_radius = w * 0.7
            pierce_surf = pygame.Surface((pierce_radius * 2, pierce_radius * 2), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(self.glow_phase * 3)
            alpha = int(50 + 25 * pulse)
            for i in range(3):
                offset = i * 4
                pygame.draw.circle(pierce_surf, (*MELON[:3], max(0, alpha - i * 15)), (pierce_radius, pierce_radius), pierce_radius - offset)
            screen.blit(pierce_surf, (cx - pierce_radius, cy - pierce_radius))

        if BUFF_TYPE_ATTRACT in self.buffs:
            attract_radius = w * 1.4
            attract_surf = pygame.Surface((attract_radius * 2, attract_radius * 2), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(self.glow_phase * 1.5)
            alpha = int(30 + 15 * pulse)
            for i in range(4):
                r = max(1, int(attract_radius * (0.3 + i * 0.2)))
                pygame.draw.circle(attract_surf, (*AMARILLO[:3], max(0, alpha - i * 8)), (attract_radius, attract_radius), r, 1)
            screen.blit(attract_surf, (cx - attract_radius, cy - attract_radius))

        if self.lightning_active:
            glow_r = w * 1.3
            glow_surf = pygame.Surface((int(glow_r * 2), int(glow_r * 2)), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(self.lightning_phase * 2)
            pygame.draw.circle(glow_surf, (*ELECTRICO[:3], int(25 + 15 * pulse)),
                               (int(glow_r), int(glow_r)), int(glow_r))
            screen.blit(glow_surf, (cx - glow_r, cy - glow_r))

            num_arcos = 6
            aura_r = w * 1.05
            for i in range(num_arcos):
                ang = (2 * math.pi * i) / num_arcos + self.lightning_phase
                mx = cx + math.cos(ang) * (aura_r * 0.5)
                my = cy + math.sin(ang) * (aura_r * 0.5) * 0.6
                jitter = random.uniform(-6, 6)
                ax = cx + math.cos(ang) * (aura_r + jitter)
                ay = cy + math.sin(ang) * (aura_r + jitter) * 0.6
                color = ELECTRICO if random.random() < 0.7 else WHITE
                pygame.draw.line(screen, color, (int(cx), int(cy)), (int(mx), int(my)), 1)
                pygame.draw.line(screen, color, (int(mx), int(my)), (int(ax), int(ay)), 1)

        self._draw_health_bar(screen, cx, cy)

        buff_icon_y = cy - h // 2 - 10
        visible_buffs = dict(self.buffs)
        for bt in self.class_buffs:
            if bt not in visible_buffs:
                visible_buffs[bt] = {"timer": 99999}
        for i, buff_type in enumerate(visible_buffs):
            color = {
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
            }.get(buff_type, AMARILLO)
            bx = cx - 8 + i * 10
            pygame.draw.circle(screen, color, (bx, buff_icon_y), 3)

    def _draw_health_bar(self, surface, cx, cy):
        bar_w = 40
        bar_h = 5
        bar_x = cx - bar_w // 2
        bar_y = cy - self.height // 2 - 14

        shake_x = 0
        shake_y = 0
        if self.health_shake > 0:
            shake_x = random.randint(-self.health_shake, self.health_shake)
            shake_y = random.randint(-self.health_shake, self.health_shake)
            self.health_shake -= 1

        draw_x = bar_x + shake_x
        draw_y = bar_y + shake_y

        shadow_surf = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 50), (2, 2, bar_w, bar_h), border_radius=2)
        surface.blit(shadow_surf, (draw_x - 2, draw_y - 2))

        pygame.draw.rect(surface, (20, 20, 30), (draw_x, draw_y, bar_w, bar_h), border_radius=2)

        ratio = self.lives / self.max_lives if self.max_lives > 0 else 0
        display_ratio = self.health_deplete_anim
        if self.health_deplete_anim > ratio:
            self.health_deplete_anim = max(ratio, self.health_deplete_anim - 0.03)

        fill_w = int((bar_w - 2) * display_ratio)
        if fill_w > 0:
            color = ROSA if ratio > 0.5 else AMARILLO if ratio > 0.25 else MELON
            pygame.draw.rect(surface, color, (draw_x + 1, draw_y + 1, fill_w, bar_h - 2), border_radius=1)

        pygame.draw.rect(surface, WHITE, (draw_x, draw_y, bar_w, bar_h), width=1, border_radius=2)

    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = self.shoot_delay
            shot_color = self.glow_color
            if self.triple_shot_active:
                return [
                    Bullet(self.x, self.y - self.height // 2, piercing=self.piercing_active, color=shot_color),
                    Bullet(self.x - 8, self.y - self.height // 2 + 2, piercing=self.piercing_active, color=shot_color),
                    Bullet(self.x + 8, self.y - self.height // 2 + 2, piercing=self.piercing_active, color=shot_color),
                ]
            bullet = Bullet(self.x, self.y - self.height // 2, piercing=self.piercing_active, color=shot_color)
            if self.ship_type == "bomber":
                bullet.speed = 12
                bullet.radius = 5
            return [bullet]
        return []

    def apply_buff(self, buff_type):
        if buff_type == BUFF_TYPE_EXTRA_LIFE:
            self.lives = min(self.lives + 1, self.max_lives)
            return "+1 vida"
        elif buff_type == BUFF_TYPE_FAST_SHOOT:
            if buff_type in self.class_buffs:
                self.buffs[buff_type] = {"timer": BUFF_DURATION_FAST}
                return "Disparo rapido"
            self.shoot_delay = max(5, int(self.base_shoot_delay * 0.4))
            self.buffs[buff_type] = {"timer": BUFF_DURATION_FAST}
            return "Disparo rapido"
        elif buff_type == BUFF_TYPE_TRIPLE_SHOT:
            self.triple_shot_active = True
            self.buffs[buff_type] = {"timer": BUFF_DURATION_TRIPLE}
            return "Rafaga triple"
        elif buff_type == BUFF_TYPE_SHIELD:
            if buff_type in self.class_buffs:
                self.shield_hits = 3
                self.buffs[buff_type] = {"timer": BUFF_DURATION_SHIELD}
                return "Escudo activo"
            self.shield_hits = 3
            self.buffs[buff_type] = {"timer": BUFF_DURATION_SHIELD}
            return "Escudo activo"
        elif buff_type == BUFF_TYPE_PIERCING:
            if buff_type in self.class_buffs:
                self.piercing_active = True
                self.buffs[buff_type] = {"timer": BUFF_DURATION_PIERCING}
                return "Penetracion"
            self.piercing_active = True
            self.buffs[buff_type] = {"timer": BUFF_DURATION_PIERCING}
            return "Penetracion"
        elif buff_type == BUFF_TYPE_ATTRACT:
            self.attract_active = True
            self.buffs[buff_type] = {"timer": BUFF_DURATION_ATTRACT}
            return "Imantado"
        elif buff_type == BUFF_TYPE_DAMAGE_UP:
            self.damage_multiplier += 0.25
            self.buffs[buff_type] = {"timer": BUFF_DURATION_DAMAGE_UP, "permanent": True}
            return "Daño +25%"
        elif buff_type == BUFF_TYPE_SPEED_UP:
            self.permanent_speed_bonus += 0.04
            self.buffs[buff_type] = {"timer": BUFF_DURATION_SPEED_UP, "permanent": True}
            return "Velocidad +"
        elif buff_type == BUFF_TYPE_MAX_LIFE_UP:
            self.max_lives += 1
            self.lives = min(self.lives + 1, self.max_lives)
            self.buffs[buff_type] = {"timer": BUFF_DURATION_MAX_LIFE_UP, "permanent": True}
            return "Vida Max +1"
        elif buff_type == BUFF_TYPE_RAPID_FIRE:
            self.permanent_rapid_fire = True
            self.shoot_delay = max(5, int(self.shoot_delay * 0.6))
            self.buffs[buff_type] = {"timer": BUFF_DURATION_RAPID_FIRE, "permanent": True}
            return "Fuego Rápido"
        elif buff_type == BUFF_TYPE_LIGHTNING:
            self.lightning_active = True
            self.lightning_zap_cooldown = 0
            self.buffs[buff_type] = {"timer": BUFF_DURATION_LIGHTNING}
            return "Campo electrico"
        return ""

    def puede_descargar_rayo(self):
        """True cuando el campo electrico esta activo y ya se puede
        disparar otra descarga (ver LIGHTNING_ZAP_INTERVAL)."""
        return self.lightning_active and self.lightning_zap_cooldown <= 0

    def reiniciar_descarga_rayo(self):
        self.lightning_zap_cooldown = LIGHTNING_ZAP_INTERVAL

    def take_damage(self):
        if self.invincible_timer <= 0:
            has_shield = BUFF_TYPE_SHIELD in self.buffs or BUFF_TYPE_SHIELD in self.class_buffs
            if has_shield and self.shield_hits > 0:
                self.shield_hits -= 1
                if self.shield_hits <= 0 and BUFF_TYPE_SHIELD in self.buffs:
                    del self.buffs[BUFF_TYPE_SHIELD]
                return False
            prev_lives = self.lives
            self.lives -= 1
            if prev_lives > self.lives:
                self.health_deplete_anim = prev_lives / self.max_lives
            self.health_shake = 6
            self.invincible_timer = 300
            if self.lives <= 0:
                self.alive = False
            return True
        return False

    def apply_skin(self, skin_id):
        apply_skin_to_ship(self, skin_id)
