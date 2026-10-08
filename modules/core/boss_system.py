"""
Jefes de oleada: uno cada 10 oleadas si o si (10, 20, 30, 40) y el
mega-jefe final en la oleada 50 (constants.MEGA_BOSS_SPAWN_WAVE, ver
modules/entities/mega_boss.py). BossDefinition describe cada jefe por
datos (vida, velocidad, patrones, colores) y WaveBoss es la
instancia jugable que lee esos datos, asi que agregar un jefe nuevo es
sumar una BossDefinition a BOSS_DEFINITIONS sin tocar la logica de WaveBoss."""

import pygame
import random
import math
from modules.constants import (
    ROSA, AMARILLO, ROSA_CHICLE, MENTA,
    GAME_WIDTH, GAME_HEIGHT, FINAL_BOSS_SPAWN_WAVE,
)
from modules.systems import pixelfx, sprites


class BossDefinition:
    """Datos fijos de un jefe de oleada: cuando aparece, cuanta vida y
    velocidad tiene, que patrones de ataque puede usar, sus colores (para
    tintar el sprite)."""

    def __init__(self, boss_id, name, spawn_wave, max_hp, speed, shoot_rate,
                 attack_patterns, primary_color, secondary_color, glow_color,
                 body_type="saucer"):
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
        self.body_type = body_type


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
    """Bala de jefe: orbe pixel art con contorno y estela corta. color y
    radius cambian segun el ataque (las minas y los disparos pesados son
    mas grandes)."""

    def __init__(self, x, y, vx=0, vy=5.0, color=ROSA, radius=4):
        self.x = x
        self.y = y
        self.radius = radius
        self.vx = vx
        self.vy = vy
        self.speed = math.sqrt(vx * vx + vy * vy)
        self.active = True
        self.trail = []
        self.color = tuple(color[:3])
        self._fase = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.speed > 0:
            self.trail.append((self.x, self.y))
            if len(self.trail) > 4:
                self.trail.pop(0)
        if self.y > GAME_HEIGHT + 10 or self.y < -10 or self.x < -10 or self.x > GAME_WIDTH + 10:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        for i, (tx, ty) in enumerate(self.trail[:-1]):
            k = (i + 1) / len(self.trail)
            lado = max(2, int(self.radius * k)) // 2 * 2
            c = tuple(int(v * 0.5 * k) for v in self.color)
            screen.fill(c, (int(tx) + offset_x - lado // 2, int(ty) + offset_y - lado // 2, lado, lado),
                        special_flags=pygame.BLEND_RGB_ADD)
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        pixelfx.dibujar_halo(screen, self.color, cx, cy, self.radius * 2.5 + 5)
        self._fase += 1
        sprite = pixelfx.bala_enemiga(self.color, self.radius, (self._fase // 6) % 2)
        screen.blit(sprite, (cx - sprite.get_width() // 2, cy - sprite.get_height() // 2))


class RayoTractor:
    """Rayo vertical del Centinela. Se comporta como una bala mas (x, y,
    radius, active) para que main.py lo choque con la nave sin cambios:
    cada cuadro se ubica en el punto del rayo mas cercano a la nave, asi
    que solo pega si la nave esta dentro de la franja."""

    def __init__(self, jefe, ship, ancho=56, vida=48):
        self.jefe = jefe
        self.ship = ship
        self.ancho = ancho
        # main.py suma medio ancho de nave: se descuenta un poco para que el
        # roce del borde no cuente
        self.radius = ancho // 2 - 8
        self.vida = vida
        self.vida_max = vida
        self.active = True
        self.x = jefe.x
        self.y = jefe.y
        self.t = 0

    def update(self):
        self.t += 1
        self.vida -= 1
        if self.vida <= 0 or not self.jefe.active:
            self.active = False
            return
        x0 = self.jefe.x
        y0 = self.jefe.y + WaveBoss.EMISOR[1]
        sy = self.ship.y if self.ship is not None else GAME_HEIGHT
        self.x = x0
        self.y = max(y0, sy)

    def draw(self, screen, offset_x=0, offset_y=0):
        x = int(self.jefe.x) + offset_x
        y0 = int(self.jefe.y + WaveBoss.EMISOR[1]) + offset_y
        k = min(1.0, self.vida / 8, (self.vida_max - self.vida + 1) / 6)
        ancho = int(self.ancho * k) // 4 * 4
        if ancho <= 0:
            return
        color = self.jefe.secondary_color
        alto = screen.get_height() - y0
        brillo = pygame.Surface((ancho + 24, alto))
        brillo.fill(tuple(int(c * 0.25) for c in color))
        brillo.fill(tuple(int(c * 0.6) for c in color), (12, 0, ancho, alto))
        screen.blit(brillo, (x - ancho // 2 - 12, y0), special_flags=pygame.BLEND_RGB_ADD)
        nucleo = max(4, ancho // 3) // 2 * 2
        screen.fill(pixelfx.aclarar(color, 0.75), (x - nucleo // 2, y0, nucleo, alto))
        # anillos que bajan por el rayo
        for yy in range(y0 + (self.t * 6) % 32, y0 + alto, 32):
            screen.fill(pixelfx.aclarar(color, 0.4), (x - ancho // 2, yy, ancho, 4))



class WaveBoss:
    """Jefe de oleada generico armado desde una BossDefinition. Hoy lo usa
    el Centinela (body_type "saucer"); los demas jefes tienen clase propia.
    Sube de fase al 66% y 33% de vida.

    Todo ataque se avisa antes de salir: el punto de disparo se carga
    (chispas que se juntan y un nucleo que crece) durante `carga` cuadros,
    asi siempre hay tiempo de moverse. Desde la fase 2 suma ataques
    especiales: el rayo tractor (franja marcada en el piso que despues se
    enciende) y, en fase 3, una cortina de balas que barre desde el anillo."""

    # Puntos de salida respecto del centro, en px de pantalla (salen de la
    # grilla de tools/generate_pixel_sprites.py, escala ESCALA)
    ESCALA = 3
    EMISOR = (0, 40)
    TORRETAS = ((-46, 34), (46, 34))
    LUCES_Y = 10
    LUCES_X = tuple(int((round(38.5 + k * 7.6) + 3.5) * 3 - 126) for k in range(-4, 5))
    OJOS = ((-9, -36), (3, -36))

    def __init__(self, definition, dificultad=1.0):
        self.definition = definition
        self.dificultad = dificultad
        self.x = GAME_WIDTH // 2
        self.y = -90.0
        self.target_x = self.x
        self.target_y = 110
        self.active = True
        self.max_hp = max(1, int(definition.max_hp * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.size = 64
        self.speed = definition.speed * dificultad
        self.shoot_rate = max(24, int(definition.shoot_rate * 1.6 / dificultad))
        self.shoot_timer = 60
        self.phase = 1
        self.attack_pattern = definition.attack_patterns[0]
        self.accion = None          # ataque que se esta cargando
        self.carga = 0
        self.carga_total = 1
        self.especial = None
        self.timer_especial = 360
        self.damaged_timer = 0
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.phase_transition = False
        self.phase_timer = 0
        self.enter_timer = 80
        self.enter_done = False
        self.body_color = definition.primary_color
        self.secondary_color = tuple(definition.secondary_color[:3])
        self.glow_color = definition.glow_color
        self.particles = []
        self.rewarded = False
        self.t = 0
        self.move_timer = 0

    # ------------------------------------------------------------ estado

    def take_damage(self, amount=1):
        if self.enter_timer > 0:
            return
        prev_hp = self.hp
        self.hp = max(0, self.hp - amount)
        if prev_hp > self.hp:
            self.health_deplete_anim = max(self.health_deplete_anim, prev_hp / self.max_hp)
        self.damaged_timer = 6
        self.health_shake = 4
        if self.hp <= 0:
            self.active = False
        hp_ratio = self.hp / self.max_hp
        if (hp_ratio < 0.66 and self.phase == 1) or (hp_ratio < 0.33 and self.phase == 2):
            self.phase += 1
            self.phase_transition = True
            self.phase_timer = 50
            self.timer_especial = 90
            self.accion = None

    def _tiempo_carga(self):
        return {1: 30, 2: 24, 3: 20}[self.phase]

    def update(self, ship=None):
        self.t += 1
        self.damaged_timer = max(0, self.damaged_timer - 1)
        if self.health_deplete_anim > self.hp / self.max_hp:
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.01)
        self._actualizar_particulas()

        if self.enter_timer > 0:
            self.enter_timer -= 1
            self.y += (110 - self.y) * 0.06
            if self.enter_timer <= 0:
                self.enter_done = True
            return None

        if self.phase_transition:
            self.phase_timer -= 1
            if self.phase_timer % 6 == 0:
                self._chispas(self.x, self.y, 6)
            if self.phase_timer <= 0:
                self.phase_transition = False
            return None

        if self.especial is not None:
            return self._actualizar_especial(ship)

        self._update_movement()

        if self.phase >= 2:
            self.timer_especial -= 1
            if self.timer_especial <= 0 and self.accion is None:
                self._iniciar_especial(ship)
                return None

        if self.accion is not None:
            self.carga -= 1
            if self.carga <= 0:
                patron, self.accion = self.accion, None
                self.shoot_timer = self.shoot_rate
                return self._create_attack(patron, ship)
            return None

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self._choose_pattern()
            self.accion = self.attack_pattern
            self.carga = self.carga_total = self._tiempo_carga()
        return None

    def _update_movement(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        lento = 0.35 if self.accion is not None else 1.0
        if dist < 6:
            self.move_timer += 1
            if self.move_timer >= 70:
                self.move_timer = 0
                self.target_x = random.randint(150, GAME_WIDTH - 150)
                self.target_y = random.randint(80, 170)
        else:
            paso = min(dist, self.speed * lento)
            self.x += dx / dist * paso
            self.y += dy / dist * paso
        # leve vaiven para que se sienta vivo
        self.y += math.sin(self.t * 0.05) * 0.3

    def _choose_pattern(self):
        available = list(self.definition.attack_patterns)
        if len(available) > 1 and self.attack_pattern in available:
            available.remove(self.attack_pattern)
        self.attack_pattern = random.choice(available)

    # ------------------------------------------------------------ ataques

    def _bala(self, x, y, angulo, velocidad, radio=4, color=None):
        return WaveBossBullet(x, y, math.cos(angulo) * velocidad, math.sin(angulo) * velocidad,
                              color or self.secondary_color, radio)

    def _create_attack(self, patron, ship=None):
        if patron == "SPREAD":
            return self._create_spread()
        if patron == "AIMED":
            return self._create_aimed(ship)
        if patron == "CIRCULAR":
            return self._create_circular()
        if patron == "SPIRAL":
            return self._create_spiral()
        if patron == "RAIN":
            return self._create_rain()
        if patron == "MINE":
            return self._create_mine()
        return []

    def _create_spread(self):
        """Abanico desde el emisor; en fase 3 un segundo abanico intercalado."""
        ex, ey = self.x + self.EMISOR[0], self.y + self.EMISOR[1]
        n = 7 if self.phase < 3 else 9
        balas = []
        for i in range(n):
            a = math.radians(90 + (i - (n - 1) / 2) * 14)
            balas.append(self._bala(ex, ey, a, 3.8, 4))
        if self.phase == 3:
            for i in range(n - 1):
                a = math.radians(90 + (i - (n - 2) / 2) * 14)
                balas.append(self._bala(ex, ey, a, 2.8, 3))
        return balas

    def _create_aimed(self, ship):
        """Cada torreta dispara una fila de balas hacia donde ESTA la nave:
        moverse de costado alcanza para esquivarla."""
        if ship is None:
            return []
        balas = []
        for tx, ty in self.TORRETAS:
            x, y = self.x + tx, self.y + ty
            a = math.atan2(ship.y - y, ship.x - x)
            for k in range(2 + (self.phase >= 2)):
                balas.append(self._bala(x, y, a, 4.2 + k * 0.7, 3, AMARILLO))
        return balas

    def _create_circular(self):
        """Anillo desde el centro (doble y girado en fase 3)."""
        n = 14
        desfase = random.uniform(0, math.pi)
        balas = [self._bala(self.x, self.y + 20, desfase + 2 * math.pi * i / n, 3.0, 4) for i in range(n)]
        if self.phase == 3:
            balas += [self._bala(self.x, self.y + 20, desfase + math.pi * (2 * i + 1) / n, 2.2, 3)
                      for i in range(n)]
        return balas

    def _create_spiral(self):
        base = self.t * 0.2
        return [self._bala(self.x, self.y, base + 2 * math.pi * i / 8, 3.0) for i in range(8)]

    def _create_rain(self):
        return [WaveBossBullet(random.randint(40, GAME_WIDTH - 40), -10, 0, 4, self.secondary_color)
                for _ in range(5)]

    def _create_mine(self):
        return [WaveBossBullet(random.randint(60, GAME_WIDTH - 60), random.randint(40, 200), 0, 0, ROSA_CHICLE, 8)
                for _ in range(3)]

    # ------------------------------------------------------------ especiales

    def _iniciar_especial(self, ship):
        tipo = "rayo" if self.phase == 2 or random.random() < 0.5 else "cortina"
        if tipo == "rayo":
            self.especial = {"tipo": "rayo", "fase": "apunta", "t": 50, "ship": ship}
        else:
            self.especial = {"tipo": "cortina", "fase": "carga", "t": 40, "paso": 0,
                             "sentido": random.choice((-1, 1))}
        self.timer_especial = 420 if self.phase == 2 else 330

    def _actualizar_especial(self, ship):
        e = self.especial
        e["t"] -= 1
        if e["tipo"] == "rayo":
            if e["fase"] == "apunta":
                # se acomoda encima de la nave
                if ship is not None:
                    self.x += max(-4.0, min(4.0, (ship.x - self.x) * 0.08))
                    self.x = max(140, min(GAME_WIDTH - 140, self.x))
                self.y += (100 - self.y) * 0.08
                if e["t"] <= 0:
                    e["fase"], e["t"] = "aviso", 55
            elif e["fase"] == "aviso":
                if e["t"] <= 0:
                    e["fase"], e["t"] = "fuego", 48
                    return [RayoTractor(self, e["ship"] or ship)]
            elif e["fase"] == "fuego":
                if e["t"] % 16 == 0:
                    # chispas de los costados: castigan quedarse pegado al rayo
                    ex, ey = self.x, self.y + self.EMISOR[1]
                    return [self._bala(ex, ey, math.radians(a), 3.0, 3) for a in (35, 145)]
                if e["t"] <= 0:
                    self.especial = None
                    self.shoot_timer = 50
            return None
        # cortina: las luces del anillo sueltan balas una tras otra
        if e["fase"] == "carga":
            if e["t"] <= 0:
                e["fase"], e["t"] = "barre", 0
            return None
        if e["t"] <= 0:
            luces = self.LUCES_X if e["sentido"] > 0 else self.LUCES_X[::-1]
            i = e["paso"]
            if i >= len(luces) * 2:
                self.especial = None
                self.shoot_timer = 60
                return None
            e["paso"] += 1
            e["t"] = 7
            vuelta = i >= len(luces)
            lx = luces[i % len(luces)] if not vuelta else luces[::-1][i % len(luces)]
            return [WaveBossBullet(self.x + lx, self.y + self.LUCES_Y + 6, 0, 3.4 if not vuelta else 2.6,
                                   self.secondary_color, 4)]
        return None

    # ------------------------------------------------------------ efectos

    def _chispas(self, x, y, n):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(1.0, 3.5)
            self.particles.append({'x': x + random.uniform(-60, 60), 'y': y + random.uniform(-20, 30),
                                   'vx': math.cos(a) * v, 'vy': math.sin(a) * v,
                                   'life': random.randint(12, 26), 'max_life': 26})

    def _actualizar_particulas(self):
        if self.damaged_timer > 0 and random.random() < 0.5:
            self._chispas(self.x, self.y, 1)
        vivas = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.05
            p['life'] -= 1
            if p['life'] > 0:
                vivas.append(p)
        self.particles = vivas

    # ------------------------------------------------------------ dibujo

    def _sprite(self):
        w, h = sprites.tamano_pixel("boss", sprites.BOSS_SPRITE_PREFIX["saucer"], self.ESCALA) \
            if sprites.es_pixel("boss", sprites.BOSS_SPRITE_PREFIX["saucer"]) else \
            (sprites.BOSS_DISPLAY_W, sprites.BOSS_DISPLAY_H)
        return sprites.get_boss_surface(self.body_color, self.secondary_color, w, h,
                                        kind=self.definition.body_type)

    def _dibujar_luces(self, screen, cx, cy):
        n = len(self.LUCES_X)
        e = self.especial
        for i, lx in enumerate(self.LUCES_X):
            if e is not None and e["tipo"] == "cortina":
                encendida = e["fase"] == "carga" and (self.t // 4) % 2 == 0
                color = (255, 80, 110)
            else:
                encendida = (i - self.t // 6) % n in (0, 1, n // 2, n // 2 + 1)
                color = self.secondary_color if self.phase < 3 else (255, 80, 110)
            x, y = cx + lx, cy + self.LUCES_Y
            if encendida:
                pixelfx.dibujar_halo(screen, color, x, y, 12)
                screen.fill(pixelfx.aclarar(color, 0.6), (x - 3, y - 3, 6, 6))
            else:
                screen.fill(tuple(int(c * 0.35) for c in color), (x - 3, y - 3, 6, 6))

    def _dibujar_aviso(self, screen, cx, cy):
        if self.accion is None:
            return
        prog = 1 - self.carga / self.carga_total
        if self.accion == "AIMED":
            for tx, ty in self.TORRETAS:
                pixelfx.carga(screen, AMARILLO, cx + tx, cy + ty, prog, self.t, 12)
        else:
            dy = self.EMISOR[1] if self.accion == "SPREAD" else 20
            pixelfx.carga(screen, self.secondary_color, cx, cy + dy, prog, self.t, 18)

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        sprite = self._sprite()
        e = self.especial

        if e is not None and e["tipo"] == "rayo" and e["fase"] == "aviso":
            pixelfx.columna_aviso(screen, cx, 64, (255, 80, 110), self.t, cy + self.EMISOR[1])
            pixelfx.carga(screen, self.secondary_color, cx, cy + self.EMISOR[1], 1 - e["t"] / 55, self.t, 22)

        if sprite is not None:
            rect = sprite.get_rect(center=(cx, cy))
            if self.enter_timer > 0:
                copia = sprite.copy()
                copia.set_alpha(int(255 * (1 - self.enter_timer / 80)))
                screen.blit(copia, rect)
            else:
                screen.blit(sprite, rect)
                if self.damaged_timer > 3 or (self.phase_transition and (self.phase_timer // 4) % 2 == 0):
                    blanco = pixelfx.silueta_blanca(sprite)
                    blanco.set_alpha(170)
                    screen.blit(blanco, rect)
            if (self.t // 90) % 4 == 0 and (self.t % 90) < 6:
                # el piloto parpadea
                for ox, oy in self.OJOS:
                    screen.fill((120, 240, 130), (cx + ox, cy + oy, 6, 6))

        if self.enter_timer <= 0:
            self._dibujar_luces(screen, cx, cy)
            self._dibujar_aviso(screen, cx, cy)

        for p in self.particles:
            k = p['life'] / p['max_life']
            c = (255, int(160 + 90 * k), int(80 * k))
            lado = 4 if k > 0.5 else 2
            screen.fill(c, (int(p['x']) + offset_x, int(p['y']) + offset_y, lado, lado))

        if self.enter_timer <= 0:
            temblor = (0, 0)
            if self.health_shake > 0:
                temblor = (random.randint(-self.health_shake, self.health_shake), 0)
                self.health_shake -= 1
            alto = sprite.get_height() if sprite is not None else 120
            ratio = max(0.0, self.hp / self.max_hp)
            color = MENTA if ratio > 0.66 else AMARILLO if ratio > 0.33 else (255, 80, 110)
            pixelfx.barra_jefe(screen, cx, cy - alto // 2 - 4, 150, ratio, self.health_deplete_anim, color, temblor)
