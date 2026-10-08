"""
Nave del jugador: movimiento hacia la posicion de la mano, disparo,
sistema de vidas/invencibilidad temporal y todos los buffs recogibles
(disparo rapido, rafaga triple, escudo, perforante, iman, campo electrico,
y los permanentes que sueltan los jefes)."""

import pygame
import random
import math
from modules.constants import (
    AZUL, WHITE, AZUL_CIELO, GAME_WIDTH, GAME_HEIGHT, SHIP_WIDTH, SHIP_HEIGHT, BUFF_TYPE_EXTRA_LIFE,
    BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT, LAVANDA, BUFF_DURATION_FAST,
    BUFF_DURATION_TRIPLE, TRIPLE_SHOT_CADENCIA_PENALIDAD, ROSA, AMARILLO, SHADOW, BUFF_TYPE_SHIELD,
    BUFF_TYPE_PIERCING, BUFF_TYPE_ATTRACT, BUFF_DURATION_SHIELD,
    BUFF_DURATION_PIERCING, BUFF_DURATION_ATTRACT, MENTA,
    MELON, ELECTRICO, BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_SPEED_UP, BUFF_TYPE_MAX_LIFE_UP,
    BUFF_TYPE_RAPID_FIRE,
    BUFF_DURATION_DAMAGE_UP, BUFF_DURATION_SPEED_UP, BUFF_DURATION_MAX_LIFE_UP, BUFF_DURATION_RAPID_FIRE,
    BUFF_TYPE_LIGHTNING, BUFF_DURATION_LIGHTNING, LIGHTNING_ZAP_INTERVAL, LIGHTNING_RADIUS,
    BUFF_STACK_BONUS, FIST_BURST_SHOTS, FIST_CONFIRM_FRAMES,
)
from modules.entities.bullet import Bullet
from modules.skins import apply_skin_to_ship, get_skin_colors
from modules.systems import sprites


# Naves que se pueden elegir en el menu (MenuScene, estado "nave"). Los
# colores del jugador son siempre los del Explorador, asi no se confunde con
# las naves bonus enemigas que reciclan los mismos cascos.
TIPOS_NAVE = {
    "scout": {
        "nombre": "EXPLORADOR", "speed": 0.18, "shoot_delay": 20, "max_lives": 5,
        "rasgo": "Pareja en todo, sin puntos flojos",
    },
    "interceptor": {
        "nombre": "INTERCEPTOR", "speed": 0.24, "shoot_delay": 15, "max_lives": 4,
        "rasgo": "La mas veloz y la que mas dispara",
    },
    "tank": {
        "nombre": "ACORAZADO", "speed": 0.14, "shoot_delay": 24, "max_lives": 7,
        "rasgo": "Escudo que se recarga solo",
    },
    "bomber": {
        "nombre": "BOMBARDERO", "speed": 0.16, "shoot_delay": 26, "max_lives": 5,
        "rasgo": "Balas perforantes siempre",
    },
}
ORDEN_NAVES = ("scout", "interceptor", "tank", "bomber")
# cuadros entre recargas del escudo del Acorazado / de la mejora de escudo
ESCUDO_RECARGA = 1200


class Ship:
    """La nave del jugador. ship_type es una de TIPOS_NAVE (velocidad,
    cadencia, vidas y un rasgo propio); `skin_id` fija los colores (ver
    modules/skins.py). target_x/target_y son la posicion de la mano
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
        self.hand_was_fist = False
        self._fist_pending_state = False
        self._fist_pending_count = 0
        self.burst_shots_pending = 0
        self.alive = True
        self.max_lives = 5
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
        # escudo que se recarga solo (rasgo del Acorazado o mejora)
        self.escudo_max = 0
        self.escudo_timer = 0
        self._apply_type_stats()
        apply_skin_to_ship(self, skin_id)
        if ship_type != "scout" and skin_id == "default":
            # los cascos nuevos con los colores de siempre del jugador
            body, wing, glow, flame = get_skin_colors("scout", "default")
            self.body_color, self.wing_color, self.glow_color, self.flame_color = body, wing, glow, flame
            self.invalidate_sprite()

    def _apply_type_stats(self):
        if self.ship_type not in TIPOS_NAVE:
            self.ship_type = "scout"
        data = TIPOS_NAVE[self.ship_type]
        self.speed = data["speed"]
        self.base_shoot_delay = data["shoot_delay"]
        self.shoot_delay = self.base_shoot_delay
        self.max_lives = data["max_lives"]
        self.lives = self.max_lives
        self.body_color = AZUL
        self.wing_color = AZUL_CIELO
        self.glow_color = (140, 210, 255)
        self.flame_color = AZUL
        self.name = data["nombre"]
        self.description = data["rasgo"]
        self.class_buffs.clear()
        if self.ship_type == "tank":
            self.sumar_escudo_recargable()
        elif self.ship_type == "bomber":
            self.class_buffs.add(BUFF_TYPE_PIERCING)
            self.piercing_active = True

    def sumar_escudo_recargable(self):
        """Una carga mas de escudo que se recarga sola cada ESCUDO_RECARGA
        cuadros (rasgo del Acorazado y mejora "Escudo recargable")."""
        self.escudo_max += 1
        self.class_buffs.add(BUFF_TYPE_SHIELD)
        self.shield_hits = max(self.shield_hits, self.escudo_max)

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
        if self.escudo_max > 0 and self.shield_hits < self.escudo_max:
            self.escudo_timer += 1
            if self.escudo_timer >= ESCUDO_RECARGA:
                self.escudo_timer = 0
                self.shield_hits += 1
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
                self.shoot_delay = max(5, int(self.shoot_delay / TRIPLE_SHOT_CADENCIA_PENALIDAD))
            if buff_type == BUFF_TYPE_SHIELD:
                self.shield_hits = min(self.shield_hits, self.escudo_max)
            if buff_type == BUFF_TYPE_PIERCING and BUFF_TYPE_PIERCING not in self.class_buffs:
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
            # Sin PNG en assets/sprites no se dibuja un casco de respaldo por
            # codigo: la nave queda sin cuerpo visible (solo los "detalles"
            # de mas abajo, como la llama, siguen animandose con un ancla
            # por defecto) hasta que se regeneren los sprites.
            flame_anchor = cy + h // 3

        toberas = sprites.get_ship_nozzles(self.ship_type) if sprite is not None else []
        if toberas:
            self._draw_llamas_pixel(screen, cx, cy, toberas)
            toberas_ok = True
        else:
            toberas_ok = False

        flame_phase = self.engine_flame_phase
        for fi in range(0 if toberas_ok else 4):
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

        if (BUFF_TYPE_SHIELD in self.buffs or BUFF_TYPE_SHIELD in self.class_buffs) and self.shield_hits > 0:
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

    def _draw_llamas_pixel(self, screen, cx, cy, toberas):
        """Llamas en bloques de pixel debajo de cada tobera de la nave pixel
        art: punta blanca, despues el color neon del motor y una cola que se
        apaga. El largo late con engine_flame_phase."""
        p = sprites.SHIP_PIXEL
        neon = sprites.color_neon(self.flame_color)
        base = self.flame_color[:3]
        for i, (dx, dy) in enumerate(toberas):
            largo = 3 + int(2.4 * (0.5 + 0.5 * math.sin(self.engine_flame_phase + i * 1.7)))
            x = int(cx + dx - p / 2)
            for paso in range(largo):
                if paso == 0:
                    color = (255, 255, 255)
                elif paso == 1:
                    color = neon
                else:
                    f = max(0.15, 1.0 - (paso - 1) / largo)
                    color = (int(base[0] * f), int(base[1] * f), int(base[2] * f))
                pygame.draw.rect(screen, color, (x, int(cy + dy) + paso * p, p, p))

    def _draw_health_bar(self, surface, cx, cy):
        bar_w = 40
        bar_h = 5
        bar_x = cx - bar_w // 2
        # se ubica arriba del sprite (que trae margen para el halo) y deja
        # un hueco visible entre la barra y la punta de la nave
        sprite = self._get_sprite()
        alto = sprite.get_height() if sprite is not None else self.height + 28
        bar_y = cy - alto // 2 - bar_h - 4

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

    def queue_shot(self, count=None):
        """Encola disparos para que update_burst_fire() los vaya soltando a
        ritmo de shoot_cooldown. Usado tanto por el flanco de cierre de
        puño (camara) como por el boton de disparo del mando."""
        self.burst_shots_pending = FIST_BURST_SHOTS if count is None else count

    def trigger_fist_burst(self, fist_now):
        """Se llama una vez por frame con el estado crudo de is_fist().
        El landmark de MediaPipe tiembla un poco cuadro a cuadro, y justo en
        el instante de abrir/cerrar la mano la punta de un dedo puede
        quedar oscilando alrededor de su PIP; sin filtro eso se leeria como
        varios cierres sueltos en vez de uno solo. Por eso un cambio de
        estado (abierta<->cerrada) solo se confirma tras FIST_CONFIRM_FRAMES
        cuadros seguidos con el mismo valor, y solo ahi, si el estado
        confirmado pasa de abierta a cerrada, se dispara un unico tiro.
        Mientras el puño siga cerrado no se vuelve a disparar; hace falta
        que el estado confirmado pase por "abierta" antes del proximo
        "cerrada" para habilitar otro disparo."""
        if fist_now == self._fist_pending_state:
            self._fist_pending_count += 1
        else:
            self._fist_pending_state = fist_now
            self._fist_pending_count = 1

        if self._fist_pending_count < FIST_CONFIRM_FRAMES:
            return
        if self._fist_pending_state == self.hand_was_fist:
            return

        if self._fist_pending_state:
            self.queue_shot()
        self.hand_was_fist = self._fist_pending_state

    def reset_fist_tracking(self):
        """Cuando se pierde la deteccion de la mano no sabemos si se abrio o
        se sigue cerrada; se limpia todo el estado (confirmado y pendiente)
        para que la proxima deteccion de puño cuente como un cierre nuevo."""
        self.hand_was_fist = False
        self._fist_pending_state = False
        self._fist_pending_count = 0

    def update_burst_fire(self):
        """Dispara un disparo de la rafaga pendiente si el cooldown ya se
        cumplio. Debe llamarse una vez por frame para ir vaciando la rafaga
        a ritmo de shoot_delay. Devuelve las balas creadas (puede ser vacia)."""
        if self.burst_shots_pending <= 0 or self.shoot_cooldown > 0:
            return []
        bullets = self.shoot()
        if bullets:
            self.burst_shots_pending -= 1
        return bullets

    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = self.shoot_delay
            shot_color = self.glow_color
            if self.triple_shot_active:
                balas = [
                    Bullet(self.x, self.y - self.height // 2, piercing=self.piercing_active, color=shot_color),
                    Bullet(self.x - 8, self.y - self.height // 2 + 2, piercing=self.piercing_active, color=shot_color),
                    Bullet(self.x + 8, self.y - self.height // 2 + 2, piercing=self.piercing_active, color=shot_color),
                ]
                # contra un jefe las tres pegan juntas: las laterales hacen
                # un cuarto del daño, asi la rafaga es 1.5x y no 3x
                for lateral in balas[1:]:
                    lateral.dano_jefe = 0.25
                return balas
            bullet = Bullet(self.x, self.y - self.height // 2, piercing=self.piercing_active, color=shot_color)
            return [bullet]
        return []

    def _extender_buff(self, buff_type, duracion):
        """Curva de apilado al agarrar el mismo power-up mientras sigue
        activo: la 1ra vez dura `duracion` (20s); la 2da vez se DUPLICA lo
        que quedaba; de la 3ra en adelante cada agarrada solo suma
        BUFF_STACK_BONUS (10s) mas, para que no se dispare al infinito
        duplicando siempre. max_timer se guarda junto al timer para que el
        HUD pueda calcular que fraccion de tiempo queda con timer/max_timer
        sin conocer la duracion base ni el conteo de stacks."""
        actual = self.buffs.get(buff_type)
        if actual is None:
            total = duracion
            stacks = 1
        else:
            stacks = actual.get("stacks", 1) + 1
            if stacks == 2:
                total = actual["timer"] * 2
            else:
                total = actual["timer"] + BUFF_STACK_BONUS
        self.buffs[buff_type] = {"timer": total, "max_timer": total, "stacks": stacks}

    def apply_buff(self, buff_type):
        if buff_type == BUFF_TYPE_EXTRA_LIFE:
            self.lives = min(self.lives + 1, self.max_lives)
            return "+1 vida"
        elif buff_type == BUFF_TYPE_FAST_SHOOT:
            if buff_type not in self.class_buffs:
                self.shoot_delay = max(5, int(self.base_shoot_delay * 0.4))
            self._extender_buff(buff_type, BUFF_DURATION_FAST)
            return "Disparo rapido"
        elif buff_type == BUFF_TYPE_TRIPLE_SHOT:
            # tres balas por disparo ya es mucho mas daño por si solo (cada
            # bala pega igual que una sola); una pequeña penalidad de
            # cadencia (aplicada una unica vez, no cada vez que se vuelve a
            # agarrar el mismo bonus mientras sigue activo) lo deja fuerte
            # pero no roto contra jefes. Se revierte al expirar (ver el
            # bucle de expiracion mas abajo).
            if not self.triple_shot_active:
                self.shoot_delay = int(self.shoot_delay * TRIPLE_SHOT_CADENCIA_PENALIDAD)
            self.triple_shot_active = True
            self._extender_buff(buff_type, BUFF_DURATION_TRIPLE)
            return "Rafaga triple"
        elif buff_type == BUFF_TYPE_SHIELD:
            self.shield_hits = max(3, self.shield_hits)
            self._extender_buff(buff_type, BUFF_DURATION_SHIELD)
            return "Escudo activo"
        elif buff_type == BUFF_TYPE_PIERCING:
            self.piercing_active = True
            self._extender_buff(buff_type, BUFF_DURATION_PIERCING)
            return "Penetracion"
        elif buff_type == BUFF_TYPE_ATTRACT:
            self.attract_active = True
            self._extender_buff(buff_type, BUFF_DURATION_ATTRACT)
            return "Imantado"
        elif buff_type == BUFF_TYPE_DAMAGE_UP:
            self.damage_multiplier += 0.25
            self.buffs[buff_type] = {"timer": BUFF_DURATION_DAMAGE_UP, "max_timer": BUFF_DURATION_DAMAGE_UP, "permanent": True}
            return "Daño +25%"
        elif buff_type == BUFF_TYPE_SPEED_UP:
            self.permanent_speed_bonus += 0.04
            self.buffs[buff_type] = {"timer": BUFF_DURATION_SPEED_UP, "max_timer": BUFF_DURATION_SPEED_UP, "permanent": True}
            return "Velocidad +"
        elif buff_type == BUFF_TYPE_MAX_LIFE_UP:
            self.max_lives += 1
            self.lives = min(self.lives + 1, self.max_lives)
            self.buffs[buff_type] = {"timer": BUFF_DURATION_MAX_LIFE_UP, "max_timer": BUFF_DURATION_MAX_LIFE_UP, "permanent": True}
            return "Vida Max +1"
        elif buff_type == BUFF_TYPE_RAPID_FIRE:
            self.permanent_rapid_fire = True
            self.shoot_delay = max(5, int(self.shoot_delay * 0.6))
            self.buffs[buff_type] = {"timer": BUFF_DURATION_RAPID_FIRE, "max_timer": BUFF_DURATION_RAPID_FIRE, "permanent": True}
            return "Fuego Rápido"
        elif buff_type == BUFF_TYPE_LIGHTNING:
            self.lightning_active = True
            self.lightning_zap_cooldown = 0
            self._extender_buff(buff_type, BUFF_DURATION_LIGHTNING)
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
            if self.lives <= 0 and getattr(self, "fenix", 0) > 0:
                # carta FENIX: renace una vez con 2 vidas (ver habilidades.py)
                self.fenix -= 1
                self.lives = min(2, self.max_lives)
                self.health_deplete_anim = self.lives / self.max_lives
                self.fenix_evento = True
            if self.lives <= 0:
                self.alive = False
            return True
        return False

