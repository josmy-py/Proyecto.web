"""
El jefe final (oleada 20, "La Anomalia Final"): 3 fases con patrones de
ataque cada vez mas agresivos. Los otros 4 jefes de oleada (5/10/15) usan
WaveBoss en modules/core/boss_system.py, una clase hermana con la misma
forma pero definida por datos (BossDefinition) en vez de estar cableada
como esta."""

import pygame
import random
import math
from modules.constants import (
    ROSA, AMARILLO, AZUL, AZUL_CIELO, MELON, LAVANDA, ROSA_CHICLE, MENTA,
    WHITE, DARK_BG, GAME_WIDTH, GAME_HEIGHT, SHIP_WIDTH, SHIP_HEIGHT,
)
from modules.systems.fonts import render_text
from modules.systems import sprites

# Tinte (color_casco, color_anillo) segun la fase del jefe. Sin
# assets/sprites el jefe vuelve a dibujarse con las formas vectoriales de siempre.
TINTES_POR_FASE = {
    1: ((172, 176, 190), (92, 196, 156)),
    2: ((198, 150, 226), (150, 88, 206)),
    3: ((232, 118, 138), (206, 68, 108)),
}


class FinalBoss:
    """Jefe de la oleada 20. take_damage() sube de fase (1->2->3) al pasar
    los umbrales de 66%/33% de vida, y cada fase agrega patrones de ataque
    nuevos (ver _choose_pattern). Usa el sprite "anomaly" (mothership) de
    assets/sprites/boss si esta disponible."""

    def __init__(self):
        self.x = GAME_WIDTH // 2
        self.y = 80
        self.target_x = self.x
        self.target_y = self.y
        self.active = True
        self.max_hp = 600
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.rotation = 0
        self.rot_speed = 0.5
        self.shoot_timer = 20
        self.shoot_rate = 20
        self.phase = 1
        self.damaged_timer = 0
        self.particles = []
        self.attack_pattern = "SPREAD"
        self.pattern_timer = 0
        self.pattern_duration = 180
        self.move_timer = 0
        self.move_cooldown = 90
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.phase_transition = False
        self.phase_timer = 0
        self.special_attack_timer = 0
        self.name = "LA ANOMALÍA FINAL"
        self.rewarded = False

    def take_damage(self, amount=1):
        prev_hp = self.hp
        self.hp = max(0, self.hp - amount)
        if prev_hp > self.hp:
            self.health_deplete_anim = prev_hp / self.max_hp
        self.damaged_timer = 10
        self.health_shake = 10
        if self.hp <= 0:
            self.active = False
        if self.hp < self.max_hp * 0.66 and self.phase == 1:
            self.phase = 2
            self.phase_transition = True
            self.phase_timer = 60
            self.pattern_duration = 140
        elif self.hp < self.max_hp * 0.33 and self.phase == 2:
            self.phase = 3
            self.phase_transition = True
            self.phase_timer = 60
            self.pattern_duration = 100
            self.shoot_rate = 14

    def update(self, ship=None):
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
            self.x += (dx / dist) * 1.0
            self.y += (dy / dist) * 1.0
        self.x = max(60, min(GAME_WIDTH - 60, self.x))
        self.y = max(30, min(GAME_HEIGHT // 2 - 10, self.y))

    def _choose_pattern(self):
        if self.phase == 1:
            self.attack_pattern = random.choice(["SPREAD", "AIMED", "CIRCULAR"])
        elif self.phase == 2:
            self.attack_pattern = random.choice(["SPREAD", "AIMED", "CIRCULAR", "SPIRAL"])
        else:
            self.attack_pattern = random.choice(["SPREAD", "AIMED", "CIRCULAR", "SPIRAL", "RAIN"])

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
        return []

    def _create_spread(self):
        bullets = []
        for i in range(-2, 3):
            bullets.append(FinalBossBullet(self.x + i * 25, self.y + 20, 0, 5))
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
            bullets.append(FinalBossBullet(self.x, self.y + 20, vx, vy))
        return bullets

    def _create_circular(self):
        bullets = []
        count = 12
        for i in range(count):
            angle = (2 * math.pi * i) / count
            speed = 3.5
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            bullets.append(FinalBossBullet(self.x, self.y, vx, vy))
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
            bullets.append(FinalBossBullet(self.x, self.y, vx, vy))
        return bullets

    def _create_rain(self):
        bullets = []
        for _ in range(5):
            x = random.randint(40, GAME_WIDTH - 40)
            bullets.append(FinalBossBullet(x, -10, 0, 4))
        return bullets

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        sombra_surf = pygame.Surface((176, 34), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra_surf, (0, 0, 0, 50), (0, 0, 176, 34))
        screen.blit(sombra_surf, (cx - 88, cy + 48))

        color_casco, color_anillo = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        ancho_sprite, alto_sprite = sprites.BOSS_DISPLAY_W, sprites.BOSS_DISPLAY_H
        sprite = sprites.get_boss_surface(color_casco, color_anillo, ancho_sprite, alto_sprite, kind="anomaly")

        if sprite is not None:
            # ---- con sprite: el casco y el anillo ya vienen dibujados ----
            rect_sprite = sprite.get_rect(center=(cx, cy + 15))
            screen.blit(sprite, rect_sprite)
            centro_y = rect_sprite.centery
            cupula_cx = rect_sprite.centerx
            plataforma_cy = rect_sprite.top + alto_sprite * sprites.BOSS_PLATFORM_CY_FRAC
            anillo_cx, anillo_cy = rect_sprite.centerx, centro_y
            anillo_rx = ancho_sprite * sprites.BOSS_RING_RX_FRAC
            anillo_ry = alto_sprite * sprites.BOSS_RING_RY_FRAC
            cupula_w = int(ancho_sprite * sprites.BOSS_PLATFORM_RX_FRAC * 1.5)
            cupula_h = int(alto_sprite * sprites.BOSS_PLATFORM_RY_FRAC * 2.6)
            cupula_y = int(plataforma_cy - cupula_h * 0.62)
        else:
            # ---- respaldo vectorial (sin assets/sprites) ----
            casco_w = 140
            casco_h = 30
            centro_y = cy + 15
            casco_surf = pygame.Surface((casco_w, casco_h), pygame.SRCALPHA)
            pygame.draw.ellipse(casco_surf, (160, 160, 170), (0, 0, casco_w, casco_h))
            pygame.draw.ellipse(casco_surf, (130, 130, 140), (0, 0, casco_w, casco_h), 2)
            resalte_surf = pygame.Surface((casco_w, casco_h // 2), pygame.SRCALPHA)
            pygame.draw.ellipse(resalte_surf, (190, 190, 200, 100), (0, 0, casco_w, casco_h // 2))
            casco_surf.blit(resalte_surf, (0, 0))
            screen.blit(casco_surf, (cx - casco_w // 2, centro_y - casco_h // 2))
            cupula_cx = cx
            anillo_cx, anillo_cy = cx, centro_y
            anillo_rx, anillo_ry = casco_w // 2 - 12, casco_h // 2 - 4
            cupula_w, cupula_h = 80, 32
            cupula_y = centro_y - casco_h // 2 - cupula_h + 8

        cupula_surf = pygame.Surface((cupula_w, cupula_h), pygame.SRCALPHA)
        color_cupula = (60, 180, 140, 160) if not self.phase_transition else (int(60 + 40 * math.sin(self.rotation * 5)), 180, 140, 200)
        pygame.draw.ellipse(cupula_surf, color_cupula, (0, 0, cupula_w, cupula_h))
        pygame.draw.ellipse(cupula_surf, (100, 220, 180, 120), (0, 0, cupula_w, cupula_h), 1)
        screen.blit(cupula_surf, (cupula_cx - cupula_w // 2, cupula_y))

        num_luces = 12
        for i in range(num_luces):
            angulo = (2 * math.pi * i) / num_luces + self.rotation * 0.03
            luz_x = anillo_cx + math.cos(angulo) * anillo_rx
            luz_y = anillo_cy + math.sin(angulo) * anillo_ry
            color = [ROSA, AMARILLO, AZUL, MENTA, LAVANDA, MELON][i % 6]
            parpadeo = 0.6 + 0.4 * math.sin(self.rotation * 0.8 + i * 0.5)
            c = (int(color[0] * parpadeo), int(color[1] * parpadeo), int(color[2] * parpadeo))
            pygame.draw.circle(screen, c, (int(luz_x), int(luz_y)), 5)

        piloto_x = cupula_cx
        piloto_y = cupula_y + 10
        pygame.draw.circle(screen, MENTA, (piloto_x, piloto_y), 9)
        pygame.draw.circle(screen, (80, 200, 160), (piloto_x, piloto_y), 9, 1)
        pygame.draw.circle(screen, WHITE, (piloto_x - 5, piloto_y - 3), 4)
        pygame.draw.circle(screen, WHITE, (piloto_x + 5, piloto_y - 3), 4)
        pygame.draw.circle(screen, (0, 0, 0), (piloto_x - 5, piloto_y - 3), 2)
        pygame.draw.circle(screen, (0, 0, 0), (piloto_x + 5, piloto_y - 3), 2)
        pygame.draw.line(screen, (180, 180, 180), (piloto_x, piloto_y - 9), (piloto_x, piloto_y - 20), 2)
        brillo_antena = max(0, min(255, int(180 + 120 * math.sin(self.rotation * 2.5))))
        pygame.draw.circle(screen, (255, 130, 150, brillo_antena), (piloto_x, piloto_y - 21), 3)

        for _ in range(3):
            angulo = random.uniform(0, 2 * math.pi)
            distancia = random.uniform(20, 35)
            px = cupula_cx + math.cos(angulo) * distancia
            py = cupula_y + 10 + math.sin(angulo) * distancia
            pygame.draw.circle(screen, (100, 255, 200, 60), (int(px), int(py)), 2)

        radio_resplandor = 28
        resplandor_surf = pygame.Surface((radio_resplandor * 2, radio_resplandor), pygame.SRCALPHA)
        color_resplandor = (100, 200, 255, 70) if self.phase == 1 else (200, 100, 255, 80) if self.phase == 2 else (255, 80, 120, 90)
        pygame.draw.ellipse(resplandor_surf, color_resplandor, (0, 0, radio_resplandor * 2, radio_resplandor))
        screen.blit(resplandor_surf, (cupula_cx - radio_resplandor, centro_y + 8))

        barra_w = 130
        barra_h = 12
        barra_x = cupula_cx - barra_w // 2
        barra_y = cupula_y - 32
        proporcion_vida = max(0, self.hp / self.max_hp)
        proporcion_mostrada = self.health_deplete_anim

        temblor_x = 0
        temblor_y = 0
        if self.health_shake > 0:
            temblor_x = random.randint(-self.health_shake, self.health_shake)
            temblor_y = random.randint(-self.health_shake, self.health_shake)
            self.health_shake -= 1

        barra_dibujo_x = barra_x + temblor_x
        barra_dibujo_y = barra_y + temblor_y

        sombra_barra_surf = pygame.Surface((barra_w + 6, barra_h + 6), pygame.SRCALPHA)
        pygame.draw.rect(sombra_barra_surf, (0, 0, 0, 60), (3, 3, barra_w, barra_h), border_radius=barra_h // 2)
        screen.blit(sombra_barra_surf, (barra_dibujo_x - 3, barra_dibujo_y - 3))

        fondo_barra_rect = (barra_dibujo_x, barra_dibujo_y, barra_w, barra_h)
        pygame.draw.rect(screen, (20, 20, 35), fondo_barra_rect, border_radius=barra_h // 2)

        ancho_relleno = int((barra_w - 2) * proporcion_mostrada)
        if ancho_relleno > 0:
            if proporcion_vida > 0.66:
                color_vida = ROSA
            elif proporcion_vida > 0.33:
                color_vida = AMARILLO
            else:
                color_vida = MELON
            pygame.draw.rect(screen, color_vida, (barra_dibujo_x + 1, barra_dibujo_y + 1, ancho_relleno, barra_h - 2), border_radius=barra_h // 2)

            alto_brillo = max(1, barra_h // 3)
            brillo_barra_surf = pygame.Surface((ancho_relleno, alto_brillo), pygame.SRCALPHA)
            for fila in range(alto_brillo):
                alfa = int(70 * (1 - fila / alto_brillo))
                pygame.draw.line(brillo_barra_surf, (255, 255, 255, alfa), (0, fila), (ancho_relleno - 1, fila))
            screen.blit(brillo_barra_surf, (barra_dibujo_x + 1, barra_dibujo_y + 1))

        pygame.draw.rect(screen, WHITE, fondo_barra_rect, width=1, border_radius=barra_h // 2)

        porcentaje = f"{int(proporcion_vida * 100)}%"
        porcentaje_surf = render_text(porcentaje, 10, WHITE)
        screen.blit(porcentaje_surf, (cx - porcentaje_surf.get_width() // 2, barra_dibujo_y - 14))

        if self.phase_transition:
            if sprite is not None:
                destello_w, destello_h, destello_top = ancho_sprite, alto_sprite, rect_sprite.top
            else:
                destello_w, destello_h, destello_top = casco_w, casco_h + cupula_h, centro_y - casco_h // 2 - cupula_h
            alfa_transicion = int(150 * (0.5 + 0.5 * math.sin(self.phase_timer * 0.5)))
            transicion_surf = pygame.Surface((destello_w + 40, destello_h + 40), pygame.SRCALPHA)
            pygame.draw.rect(transicion_surf, (255, 255, 255, alfa_transicion), (20, 20, destello_w, destello_h), border_radius=10)
            screen.blit(transicion_surf, (cupula_cx - destello_w // 2 - 20, destello_top - 20))

        if self.damaged_timer > 0:
            alfa_impacto = int(140 * (self.damaged_timer / 10))
            impacto_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(impacto_surf, (255, 130, 150, alfa_impacto), (40, 40), 40)
            screen.blit(impacto_surf, (cx - 40, cy - 20))

        for p in self.particles:
            alpha = p['life'] / p['max_life']
            size = max(1, int(p['radius'] * alpha))
            c = (int(255 * alpha), int(120 * alpha), int(40 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)


class FinalBossBullet:
    """Bala del jefe final, con velocidad libre (vx, vy) para soportar los
    patrones dirigidos/circulares/espiral, y una estela corta."""

    def __init__(self, x, y, vx=0, vy=5.0):
        self.x = x
        self.y = y
        self.radius = 5
        self.vx = vx
        self.vy = vy
        self.speed = math.sqrt(vx * vx + vy * vy)
        self.active = True
        self.trail = []

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
            pygame.draw.circle(trail_surf, (*ROSA[:3], alpha), (size, size), size)
            screen.blit(trail_surf, (int(tx) + offset_x - size, int(ty) + offset_y - size))

        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 130, 150, 70), (self.radius * 2, self.radius * 2), self.radius * 2)
        screen.blit(glow_surf, (cx - self.radius * 2, cy - self.radius * 2))
        pygame.draw.circle(screen, ROSA, (cx, cy), self.radius)
        pygame.draw.circle(screen, AMARILLO, (cx, cy), self.radius - 1)
        pygame.draw.circle(screen, WHITE, (cx, cy), max(1, self.radius - 2))
