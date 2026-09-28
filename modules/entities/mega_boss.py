"""
Mega-jefe unico de la oleada 50 (constants.MEGA_BOSS_SPAWN_WAVE): a
diferencia de los jefes de modules/core/boss_system.py y FinalBoss, no usa
el molde "platillo con anillo de luces" - tiene silueta y ataques propios
en dos fases:

  Fase 1 "cruiser": crucero de asalto alargado, con luces de navegacion
  que parpadean de verdad (ver _dibujar_luces_crucero) y banqueo/estela de
  motor ligados al movimiento real (ver _mover). Ataques de bala (ronda
  lateral tipo andanada, misiles dirigidos, abanico) y lanza cazas
  alienigenas de elite cada tanto, con su propia animacion de largada: la
  bahia de hangar destella (_dibujar_hangar) y los cazas nuevos aparecen
  ahi en vez de materializarse en el borde de la pantalla (ver
  _lanzar_cazas).

  Fase 2 "sphere" (a partir de MEGA_BOSS_PHASE2_HP_RATIO de vida): se
  transforma en una esfera de combate blindada. Suelta lluvia de
  meteoritos (Asteroid reciclado, con toda su colision ya existente),
  sigue lanzando cazas, y cada tanto carga y dispara un laser: una
  advertencia visual fija el corredor sobre la posicion de la nave y, tras
  esa ventana para esquivar, dispara una rafaga densa de proyectiles por
  ese corredor.

  La transformacion entre fases no es un simple destello de color: el
  crucero EXPLOTA en pedazos reales (recortes de su propio sprite, ver
  _iniciar_fragmentacion) que primero salen disparados hacia afuera y
  despues implosionan de vuelta al centro (_actualizar_fragmentos) -
  recien cuando termina de implosionar aparece la esfera, con un
  destello final (reform_flash).

update() no devuelve una lista plana de balas como WaveBoss/FinalBoss, sino
un dict {"bullets": [...], "asteroides": [...], "alien_ships": [...]}
porque tambien puede soltar meteoritos y naves; main.py lo distribuye a las
listas correspondientes (ver el manejo de MegaBoss ahi)."""

import random
import math
import pygame

from modules.constants import (
    GAME_WIDTH, GAME_HEIGHT, WHITE, ROSA, AMARILLO, MELON,
    BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_TRIPLE_SHOT, BUFF_TYPE_RAPID_FIRE,
    BUFF_DURATION_DAMAGE_UP, BUFF_DURATION_MAX_LIFE_UP, BUFF_DURATION_TRIPLE, BUFF_DURATION_RAPID_FIRE,
)
from modules.core.boss_system import BossReward, WaveBossBullet
from modules.entities.asteroid import Asteroid
from modules.entities.enemy import AlienShip
from modules.systems.fonts import render_text
from modules.systems import sprites

MEGA_BOSS_MAX_HP = 2800
MEGA_BOSS_PHASE2_HP_RATIO = 0.5

# Color de las naves de escolta que lanza el mega-jefe (ver _lanzar_cazas):
# gris metalico oscuro a tono con el crucero/esfera, en vez de un color
# vistoso de power-up, para que se lean como cazas imperiales propios en
# vez de una nave alienigena comun con otro tinte.
CAZA_ESCOLTA_COLOR = (98, 102, 114)


class MegaBoss:
    """Ver docstring del modulo. take_damage() dispara la transformacion a
    fase 2 al cruzar MEGA_BOSS_PHASE2_HP_RATIO; update(ship) hay que
    llamarlo una vez por frame."""

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH // 2
        self.y = -160
        self.target_x = self.x
        self.target_y = 150
        self.active = True
        # La dificultad elegida en el menu tambien lo escala a el (antes solo
        # afectaba asteroides/alienigenas comunes): en dificil aguanta mas,
        # pega mas rapido y se mueve mas rapido; en facil, menos.
        self._dificultad = dificultad
        self.max_hp = max(1, int(MEGA_BOSS_MAX_HP * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.health_deplete_anim = 1.0
        self.health_shake = 0
        # Banqueo/empuje de motor: ligados al movimiento REAL cuadro a
        # cuadro (ver _mover), no una animacion decorativa aparte - el
        # casco se inclina hacia el lado que se desplaza y el resplandor
        # de motor se estira segun la velocidad real, como haria una nave
        # de verdad al maniobrar.
        self.bank_angle = 0.0
        self.motor_intensidad = 0.0
        self.name = "COLOSO ESTELAR"
        self.rewarded = False
        self.damaged_timer = 0
        self.particles = []

        self.phase = 1
        self.phase_name = "cruiser"
        # Mas grande que cualquier jefe de oleada (solo afecta la sombra y
        # la separacion de los cañones de la andanada; el sprite en si ya
        # tiene su tamaño fijo en sprites.MEGA_BOSS_DISPLAY_W) y con mas
        # empuje/particulas al recibir un golpe, para que se sienta pesado
        # de verdad y no solo "otro jefe con mas vida".
        self.width = 300
        self.phase_transition = False
        self.phase_timer = 0

        # Transformacion fase 1 -> fase 2: en vez de un simple destello de
        # color, el crucero explota en pedazos (ver _iniciar_fragmentacion)
        # y esos mismos pedazos implosionan hacia el centro, formando la
        # esfera - toda la secuencia se dibuja con sprites reales (los
        # fragmentos son recortes del propio sprite del crucero), ver
        # _actualizar_fragmentos/_dibujar_fragmentos.
        self.frag_pieces = []
        self.frag_stage = None
        self.frag_timer = 0
        self.frag_dur_explota = 42
        self.frag_dur_implota = 46
        self.reform_flash = 0

        # Aviso visual de largada de cazas (ver _lanzar_cazas): la bahia de
        # hangar del crucero destella cuando salen naves nuevas.
        self.hangar_flash = 0

        self.enter_timer = 100
        self.enter_done = False

        self.move_timer = 0
        self.move_cooldown = 130
        self.speed = 1.05 * dificultad

        self.shoot_timer = 40
        self.shoot_rate = max(10, int(40 / dificultad))
        self.attack_pattern = "BROADSIDE"
        self.pattern_timer = 0
        self.pattern_duration = 190

        self.fighter_timer = 220

        # Fase 2: meteoritos y laser (ver _actualizar_meteoros/_actualizar_laser)
        self.meteor_timer = 260
        self.laser_cooldown = 420
        self.laser_state = None
        self.laser_timer = 0
        self.laser_target_x = self.x

        # Cañon railgun (fase 1, ver _actualizar_railgun): apunta con una
        # linea de mira que se ve durante la carga y despues dispara un
        # unico proyectil pesado y muy rapido - un ataque mas, con su
        # propia animacion de aviso, para que la fase 1 se sienta mas
        # agresiva que cualquier jefe de oleada.
        self.railgun_cooldown = random.randint(260, 320)
        self.railgun_state = None
        self.railgun_timer = 0
        self.railgun_target_x = self.x
        self.railgun_target_y = self.y

        self.rewards = [
            BossReward(BUFF_TYPE_DAMAGE_UP, "DMG+", "Daño aumentado permanente", BUFF_DURATION_DAMAGE_UP),
            BossReward(BUFF_TYPE_RAPID_FIRE, "RAPID", "Disparo rapido permanente", BUFF_DURATION_RAPID_FIRE),
            BossReward(BUFF_TYPE_MAX_LIFE_UP, "MAX+", "Vida maxima +1", BUFF_DURATION_MAX_LIFE_UP),
            BossReward(BUFF_TYPE_TRIPLE_SHOT, "3X", "Rafaga triple permanente", BUFF_DURATION_TRIPLE),
        ]

    # ------------------------------------------------------------- estado

    def take_damage(self, amount=1):
        if self.enter_timer > 0:
            return
        prev_hp = self.hp
        self.hp = max(0, self.hp - amount)
        if prev_hp > self.hp:
            self.health_deplete_anim = prev_hp / self.max_hp
        self.damaged_timer = 10
        self.health_shake = 14
        if self.hp <= 0:
            self.active = False
        if self.phase == 1 and self.hp <= self.max_hp * MEGA_BOSS_PHASE2_HP_RATIO:
            self._iniciar_fase_2()

    def _iniciar_fase_2(self):
        self.phase = 2
        # OJO: phase_name se queda en "cruiser" hasta que termine la
        # implosion (ver _actualizar_fragmentos) - la transformacion en si
        # es la animacion, no un salto instantaneo de sprite.
        self.phase_transition = True
        self.width = 230
        self.attack_pattern = "SPREAD"
        self.pattern_timer = 0
        self.pattern_duration = 230
        self.shoot_rate = max(10, int(55 / self._dificultad))
        self.laser_state = None
        self.laser_cooldown = 300
        self.railgun_state = None
        self._iniciar_fragmentacion()

    # -------------------------------------------------------------- update

    def update(self, ship=None):
        resultado = {"bullets": [], "asteroides": [], "alien_ships": []}

        if self.enter_timer > 0:
            self.enter_timer -= 1
            self.y += (self.target_y - self.y) * 0.04
            if self.enter_timer <= 0:
                self.enter_done = True
            return resultado

        if self.phase_transition:
            if self.frag_stage is not None:
                self._actualizar_fragmentos()
            else:
                self.phase_timer -= 1
                if self.phase_timer <= 0:
                    self.phase_transition = False

        self._mover()
        self.damaged_timer = max(0, self.damaged_timer - 1)
        self.hangar_flash = max(0, self.hangar_flash - 1)
        self.reform_flash = max(0, self.reform_flash - 1)
        self.pattern_timer += 1
        self.fighter_timer -= 1

        if self.pattern_timer >= self.pattern_duration and not self.phase_transition:
            self.pattern_timer = 0
            self._elegir_patron()

        if not self.phase_transition:
            if self.phase == 1:
                if self.railgun_state is not None:
                    self._actualizar_railgun(ship, resultado)
                else:
                    self.railgun_cooldown -= 1
                    if self.railgun_cooldown <= 0:
                        self._iniciar_carga_railgun(ship)

            if self.phase == 2:
                self.meteor_timer -= 1
                if self.meteor_timer <= 0:
                    self.meteor_timer = random.randint(230, 300)
                    resultado["asteroides"].extend(self._crear_meteoros())

                if self.laser_state is not None:
                    self._actualizar_laser(ship, resultado)
                else:
                    self.laser_cooldown -= 1
                    if self.laser_cooldown <= 0:
                        self._iniciar_carga_laser(ship)

            if self.laser_state is None:
                self.shoot_timer -= 1
                if self.shoot_timer <= 0:
                    self.shoot_timer = self.shoot_rate
                    resultado["bullets"].extend(self._crear_ataque(ship))

            if self.fighter_timer <= 0:
                self.fighter_timer = random.randint(300, 420)
                resultado["alien_ships"].extend(self._lanzar_cazas())

        if self.damaged_timer > 0 and random.random() < 0.4:
            self.particles.append({
                'x': self.x + random.uniform(-self.width * 0.3, self.width * 0.3),
                'y': self.y + random.uniform(-20, 20),
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
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.02)

        return resultado

    def _mover(self):
        prev_x, prev_y = self.x, self.y
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 10:
            self.move_timer += 1
            if self.move_timer >= self.move_cooldown:
                self.move_timer = 0
                padding = 130
                self.target_x = random.randint(padding, GAME_WIDTH - padding)
                self.target_y = random.randint(140, GAME_HEIGHT // 2 - 20)
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
        self.x = max(90, min(GAME_WIDTH - 90, self.x))
        self.y = max(140, min(GAME_HEIGHT // 2, self.y))

        # banqueo y empuje de motor ligados al desplazamiento REAL de este
        # frame (no a un timer aparte): si frena en un borde o gira, se
        # nota al toque en vez de seguir "planeando" a velocidad constante.
        vx, vy = self.x - prev_x, self.y - prev_y
        velocidad_actual = math.hypot(vx, vy)
        objetivo_banqueo = max(-11.0, min(11.0, -vx * 3.4))
        self.bank_angle += (objetivo_banqueo - self.bank_angle) * 0.08
        objetivo_motor = min(1.0, velocidad_actual / max(0.001, self.speed))
        self.motor_intensidad += (objetivo_motor - self.motor_intensidad) * 0.15

    # ------------------------------------------------------------ ataques

    def _elegir_patron(self):
        opciones = ["BROADSIDE", "MISSILES", "SPREAD"] if self.phase == 1 else ["SPREAD", "CIRCULAR", "MINEFIELD"]
        if len(opciones) > 1 and self.attack_pattern in opciones:
            opciones.remove(self.attack_pattern)
        self.attack_pattern = random.choice(opciones)

    def _crear_ataque(self, ship=None):
        if self.attack_pattern == "BROADSIDE":
            return self._crear_andanada()
        if self.attack_pattern == "MISSILES":
            return self._crear_misiles(ship)
        if self.attack_pattern == "CIRCULAR":
            return self._crear_circular()
        if self.attack_pattern == "MINEFIELD":
            return self._crear_minas()
        return self._crear_abanico()

    def _crear_andanada(self):
        """Fase 1: 'canones' a lo largo de todo el casco disparando a la vez,
        como la andanada de un buque de guerra."""
        bullets = []
        for i in range(-4, 5):
            x = self.x + i * (self.width * 0.11)
            bullets.append(WaveBossBullet(x, self.y + 22, random.uniform(-0.4, 0.4), 5.0, AMARILLO))
        return bullets

    def _crear_misiles(self, ship):
        bullets = []
        if ship is None:
            return bullets
        for i in range(3):
            angle = math.atan2(ship.y - self.y, ship.x - self.x) + random.uniform(-0.15, 0.15)
            speed = 4.0 + i * 0.3
            vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
            bullets.append(WaveBossBullet(self.x + (i - 1) * 40, self.y + 20, vx, vy, MELON, 6))
        return bullets

    def _crear_abanico(self):
        bullets = []
        for i in range(-3, 4):
            angle = math.pi / 2 + i * 0.18
            speed = 4.2
            vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
            bullets.append(WaveBossBullet(self.x, self.y + 15, vx, vy, ROSA))
        return bullets

    def _crear_circular(self):
        bullets = []
        count = 14
        for i in range(count):
            angle = (2 * math.pi * i) / count
            speed = 3.2
            vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
            bullets.append(WaveBossBullet(self.x, self.y, vx, vy, (150, 158, 176)))
        return bullets

    def _crear_minas(self):
        """Fase 2: campo de minas estaticas (WaveBossBullet con velocidad
        cero, mismo truco que usa el Titan en modules/core/boss_system.py)
        repartidas por el area de juego para que el jugador tenga que
        esquivarlas en vez de solo el fuego directo."""
        minas = []
        for _ in range(4):
            x = random.randint(60, GAME_WIDTH - 60)
            y = random.randint(60, GAME_HEIGHT * 2 // 3)
            minas.append(WaveBossBullet(x, y, 0, 0, (230, 90, 110), 9))
        return minas

    def _iniciar_carga_railgun(self, ship):
        """Fase 1: aviso previo (linea de mira roja fija sobre el objetivo)
        antes de disparar un unico proyectil pesado y muy rapido - un
        ataque nuevo de riesgo/recompensa: se ve venir, pero perfora fuerte
        si no se esquiva a tiempo."""
        self.railgun_state = "charging"
        self.railgun_timer = 50
        self.railgun_target_x = ship.x if ship is not None else self.x
        self.railgun_target_y = ship.y if ship is not None else self.y + 300
        self.railgun_cooldown = random.randint(320, 420)

    def _actualizar_railgun(self, ship, resultado):
        self.railgun_timer -= 1
        if self.railgun_state == "charging":
            if self.railgun_timer <= 0:
                self.railgun_state = "firing"
                self.railgun_timer = 1
            return
        # "firing": un unico disparo pesado (radio grande, velocidad alta)
        # a lo largo de la linea de mira que se vio durante la carga.
        angle = math.atan2(self.railgun_target_y - self.y, self.railgun_target_x - self.x)
        speed = 11.0
        vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
        resultado["bullets"].append(WaveBossBullet(self.x, self.y, vx, vy, (255, 90, 70), 10))
        self.railgun_state = None

    def _crear_meteoros(self):
        """Fase 2: la esfera suelta meteoritos (Asteroid reciclado, con toda
        su colision/puntaje ya existente en main.py) en vez de un patron de
        balas."""
        meteoros = []
        for _ in range(5):
            x = random.randint(30, GAME_WIDTH - 30)
            size = random.randint(20, 36)
            meteoro = Asteroid(x, -size - 10, size)
            meteoro.speed *= 1.6
            meteoros.append(meteoro)
        return meteoros

    def _lanzar_cazas(self):
        """Naves de escolta de elite: mismo AlienShip de siempre (con toda
        su IA/colision/sprite ya existente, variante "fighter" — la mas
        chica y rapida, como un caza de asalto), pero retintadas gris
        metalico (CAZA_ESCOLTA_COLOR) para que se lean como cazas propios
        del mega-jefe en vez de una nave alienigena comun de otro color.
        En fase 1 salen del hangar del crucero (ver _dibujar_hangar): se
        les reubica x/y ahi apenas se crean, en vez de dejarlas aparecer
        en el borde de la pantalla como a un enemigo comun."""
        naves = []
        if self.phase == 1:
            display_w = sprites.MEGA_BOSS_DISPLAY_W
            display_h = round(display_w * sprites.MEGA_SPRITE_H / sprites.MEGA_SPRITE_W)
            hangar_x = self.x + (sprites.MEGA_CRUISER_HANGAR_X_FRAC - 0.5) * display_w
            hangar_y = self.y + (sprites.MEGA_CRUISER_HANGAR_Y_FRAC - 0.5) * display_h
            self.hangar_flash = 30
        for _ in range(2):
            lado = random.choice(["left", "right"])
            nave = AlienShip(lado, variant="fighter")
            nave.color = CAZA_ESCOLTA_COLOR
            nave.wing_color = tuple(int(c * 0.62) for c in CAZA_ESCOLTA_COLOR)
            nave.speed *= 1.25
            if self.phase == 1:
                nave.x, nave.y = hangar_x, hangar_y
            naves.append(nave)
        return naves

    # ------------------------------------------------ transformacion (fase 2)

    def _iniciar_fragmentacion(self):
        """Arranca la secuencia explosion -> implosion que reemplaza al
        simple destello de color: recorta el sprite ACTUAL del crucero en
        una grilla de pedazos (sprites reales, no formas vectoriales) y
        les da una direccion de salida propia; _actualizar_fragmentos los
        hace estallar hacia afuera y despues implosionar de vuelta al
        centro, momento en el que recien aparece el sprite de la esfera."""
        display_w = sprites.MEGA_BOSS_DISPLAY_W
        display_h = round(display_w * sprites.MEGA_SPRITE_H / sprites.MEGA_SPRITE_W)
        sprite_actual = sprites.get_mega_boss_surface("cruiser", display_w, display_h)
        self.frag_pieces = []
        if sprite_actual is not None:
            cols, rows = 6, 4
            pw, ph = display_w / cols, display_h / rows
            for row in range(rows):
                for col in range(cols):
                    rx0, ry0 = int(col * pw), int(row * ph)
                    rx1 = display_w if col == cols - 1 else int((col + 1) * pw)
                    ry1 = display_h if row == rows - 1 else int((row + 1) * ph)
                    rect = pygame.Rect(rx0, ry0, max(1, rx1 - rx0), max(1, ry1 - ry0))
                    pieza = sprite_actual.subsurface(rect).copy()
                    base_x = rect.centerx - display_w / 2.0
                    base_y = rect.centery - display_h / 2.0
                    dist = math.hypot(base_x, base_y) or 1.0
                    self.frag_pieces.append({
                        'surf': pieza,
                        'base_x': base_x, 'base_y': base_y,
                        'dir_x': base_x / dist, 'dir_y': base_y / dist,
                        'off': 0.0,
                        'ang': 0.0, 'ang_vel': random.uniform(-8, 8),
                    })
        self.frag_stage = "explota"
        self.frag_timer = self.frag_dur_explota
        self.phase_timer = self.frag_dur_explota + self.frag_dur_implota + 10
        for _ in range(36):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2, 6)
            self.particles.append({
                'x': self.x, 'y': self.y,
                'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
                'life': random.randint(30, 55), 'max_life': 55,
                'radius': random.randint(2, 5),
            })

    def _actualizar_fragmentos(self):
        if self.frag_stage == "explota":
            t = 1.0 - max(0.0, self.frag_timer / self.frag_dur_explota)
            for p in self.frag_pieces:
                p['off'] = 95 * (t * t)
                p['ang'] += p['ang_vel']
            self.frag_timer -= 1
            if self.frag_timer <= 0:
                self.frag_stage = "implota"
                self.frag_timer = self.frag_dur_implota
                for _ in range(30):
                    ang = random.uniform(0, 2 * math.pi)
                    rad = random.uniform(40, 95)
                    spd = random.uniform(2, 5)
                    self.particles.append({
                        'x': self.x + math.cos(ang) * rad, 'y': self.y + math.sin(ang) * rad,
                        'vx': -math.cos(ang) * spd, 'vy': -math.sin(ang) * spd,
                        'life': random.randint(25, 40), 'max_life': 40,
                        'radius': random.randint(2, 4),
                    })
            return
        # "implota"
        t = max(0.0, self.frag_timer / self.frag_dur_implota)
        for p in self.frag_pieces:
            p['off'] = 95 * (t * t)
            p['ang'] += p['ang_vel'] * 1.8
        self.frag_timer -= 1
        if self.frag_timer <= 0:
            self.frag_pieces = []
            self.frag_stage = None
            self.phase_name = "sphere"
            self.phase_transition = False
            self.reform_flash = 16
            for _ in range(26):
                ang = random.uniform(0, 2 * math.pi)
                spd = random.uniform(3, 7)
                self.particles.append({
                    'x': self.x, 'y': self.y,
                    'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
                    'life': random.randint(20, 35), 'max_life': 35,
                    'radius': random.randint(2, 4),
                })

    def _dibujar_fragmentos(self, screen, cx, cy):
        for p in self.frag_pieces:
            dx = p['base_x'] + p['dir_x'] * p['off']
            dy = p['base_y'] + p['dir_y'] * p['off']
            rotada = pygame.transform.rotate(p['surf'], p['ang'])
            rect = rotada.get_rect(center=(int(cx + dx), int(cy + dy)))
            screen.blit(rotada, rect)

    def _dibujar_luces_crucero(self, screen, cx, cy, display_w, display_h):
        """Luces de navegacion que parpadean de verdad (no horneadas en el
        PNG): blanca fija en la proa, rojo/verde titilando en la popa y
        una baliza ambar pulsante en la punta del radar - mas detalle
        "vivo" en el crucero ademas de la estela de motor."""
        def pos(fx, fy):
            return (cx - display_w / 2 + fx * display_w, cy - display_h / 2 + fy * display_h)

        t = pygame.time.get_ticks()
        px, py = pos(sprites.MEGA_CRUISER_PROA_X_FRAC, sprites.MEGA_CRUISER_PROA_Y_FRAC)
        pygame.draw.circle(screen, (235, 245, 255), (int(px), int(py)), 2)

        if (t // 350) % 2 == 0:
            bx, by = pos(sprites.MEGA_CRUISER_BABOR_X_FRAC, sprites.MEGA_CRUISER_BABOR_Y_FRAC)
            pygame.draw.circle(screen, (255, 60, 60), (int(bx), int(by)), 3)
            ex, ey = pos(sprites.MEGA_CRUISER_ESTRIBOR_X_FRAC, sprites.MEGA_CRUISER_ESTRIBOR_Y_FRAC)
            pygame.draw.circle(screen, (70, 255, 110), (int(ex), int(ey)), 3)

        zx, zy = pos(sprites.MEGA_CRUISER_BALIZA_X_FRAC, sprites.MEGA_CRUISER_BALIZA_Y_FRAC)
        pulso = 0.5 + 0.5 * math.sin(t * 0.006)
        alpha = int(130 + 120 * pulso)
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 180, 60, alpha), (8, 8), 5)
        screen.blit(surf, (int(zx - 8), int(zy - 8)))

    def _dibujar_hangar(self, screen, cx, cy, display_w, display_h):
        """Destello en la bahia de hangar mientras larga cazas nuevos (ver
        _lanzar_cazas): sin esto los cazas simplemente aparecian solos en
        el borde de la pantalla, sin ninguna señal de que salieron de
        algun lado de la nave."""
        if self.hangar_flash <= 0:
            return
        t = self.hangar_flash / 30.0
        hx = cx - display_w / 2 + sprites.MEGA_CRUISER_HANGAR_X_FRAC * display_w
        hy = cy - display_h / 2 + sprites.MEGA_CRUISER_HANGAR_Y_FRAC * display_h
        r = 18
        surf = pygame.Surface((int(r * 3), int(r * 1.6)), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (210, 235, 255, int(210 * t)), (0, 0, int(r * 3), int(r * 1.6)))
        screen.blit(surf, (int(hx - r * 1.5), int(hy - r * 0.8)))

    def _iniciar_carga_laser(self, ship):
        self.laser_state = "charging"
        self.laser_timer = 75
        self.laser_target_x = ship.x if ship is not None else self.x
        self.laser_cooldown = random.randint(480, 600)

    def _actualizar_laser(self, ship, resultado):
        self.laser_timer -= 1
        if self.laser_state == "charging":
            if self.laser_timer <= 0:
                self.laser_state = "firing"
                self.laser_timer = 30
            return
        # "firing"
        for dx in (-6, 0, 6):
            resultado["bullets"].append(
                WaveBossBullet(self.laser_target_x + dx, self.y + 10, 0, 15.0, WHITE, 7)
            )
        if self.laser_timer <= 0:
            self.laser_state = None

    # ---------------------------------------------------------------- draw

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        if self.enter_timer > 0:
            alpha = int(255 * (1 - self.enter_timer / 100))
            ghost = pygame.Surface((160, 70), pygame.SRCALPHA)
            pygame.draw.ellipse(ghost, (110, 120, 150, alpha), (0, 0, 160, 70))
            screen.blit(ghost, (cx - 80, cy - 35))
            return

        # Aura de amenaza permanente detras del casco: un pulso oscuro que
        # ningun otro jefe tiene, para que este se sienta distinto/superior
        # de un vistazo apenas aparece (no es un "detalle" de un ataque en
        # particular, es su firma visual constante de jefe final).
        aura_pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.0025)
        aura_r = int(self.width * 0.62 + aura_pulse * 14)
        aura = pygame.Surface((aura_r * 2, int(aura_r * 1.1)), pygame.SRCALPHA)
        aura_color = (140, 40, 60) if self.phase == 2 else (60, 70, 140)
        pygame.draw.ellipse(aura, (*aura_color, int(50 + 25 * aura_pulse)), (0, 0, aura_r * 2, int(aura_r * 1.1)))
        screen.blit(aura, (cx - aura_r, cy - int(aura_r * 0.55)))

        shadow = pygame.Surface((self.width + 40, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), (0, 0, self.width + 40, 40))
        screen.blit(shadow, (cx - (self.width + 40) // 2, cy + 60))

        display_w = sprites.MEGA_BOSS_DISPLAY_W if self.phase == 1 else int(sprites.MEGA_BOSS_DISPLAY_W * 0.72)
        display_h = round(display_w * sprites.MEGA_SPRITE_H / sprites.MEGA_SPRITE_W)
        # mientras dura la fragmentacion no hace falta componer el sprite
        # normal (se dibujan los pedazos en su lugar, ver mas abajo).
        sprite = None if self.frag_stage is not None else sprites.get_mega_boss_surface(self.phase_name, display_w, display_h)

        self._dibujar_estela_motor(screen, cx, cy, display_w, display_h)

        if self.frag_stage is not None:
            # Transformacion en curso: en vez del sprite entero se ven sus
            # propios pedazos explotando/implosionando (ver
            # _actualizar_fragmentos) - nada de sprite normal ni del
            # destello generico mientras dura.
            self._dibujar_fragmentos(screen, cx, cy)
        elif sprite is not None:
            # banqueo ligado al movimiento real (ver _mover): rota el
            # sprite ya compuesto en vez de tener un cuadro aparte por
            # angulo, el giro es chico (+-11°) asi que no hace falta cache.
            dibujado = sprite if abs(self.bank_angle) < 0.3 else pygame.transform.rotate(sprite, self.bank_angle)
            rect = dibujado.get_rect(center=(cx, cy))
            screen.blit(dibujado, rect)
        # Sin PNG en assets/sprites/boss no se dibuja un casco de respaldo
        # por codigo: solo quedan los "detalles" (aura, barra de vida,
        # particulas, ataques) hasta que se regeneren los sprites.

        if self.phase == 1 and self.frag_stage is None:
            self._dibujar_railgun(screen, cx, cy, offset_x, offset_y)
            self._dibujar_luces_crucero(screen, cx, cy, display_w, display_h)
            self._dibujar_hangar(screen, cx, cy, display_w, display_h)
        if self.phase == 2:
            self._dibujar_laser(screen, cx, cy, offset_x, offset_y)

        # bar/etiqueta ubicadas relativas al borde superior REAL del sprite
        # de esta fase (no un numero fijo), porque cambia de tamaño entre
        # fase 1 y fase 2; con un offset fijo quedaban pegadas o metidas
        # adentro del casco segun la fase.
        top_y = cy - display_h // 2
        bar_y = top_y - 26
        self._dibujar_barra_vida(screen, cx, bar_y)

        fase_label = "FASE 1: CRUCERO DE ASALTO" if self.phase == 1 else "FASE 2: ESFERA DE COMBATE"
        label_surf = render_text(f"{self.name} · {fase_label}", 12, WHITE if self.phase == 1 else ROSA)
        screen.blit(label_surf, (cx - label_surf.get_width() // 2, bar_y - 20))

        if self.phase_transition and self.frag_stage is None:
            trans_alpha = int(150 * (0.5 + 0.5 * math.sin(self.phase_timer * 0.5)))
            trans = pygame.Surface((self.width + 60, 140), pygame.SRCALPHA)
            pygame.draw.ellipse(trans, (255, 255, 255, trans_alpha), (0, 0, self.width + 60, 140))
            screen.blit(trans, (cx - (self.width + 60) // 2, cy - 70))

        if self.reform_flash > 0:
            t = self.reform_flash / 16.0
            r = int(60 + 90 * (1 - t))
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 255, int(220 * t)), (r, r), r)
            screen.blit(surf, (cx - r, cy - r))

        if self.damaged_timer > 0:
            flash_alpha = int(140 * (self.damaged_timer / 10))
            flash = pygame.Surface((90, 90), pygame.SRCALPHA)
            pygame.draw.circle(flash, (255, 130, 150, flash_alpha), (45, 45), 45)
            screen.blit(flash, (cx - 45, cy - 30))

        for p in self.particles:
            alpha = p['life'] / p['max_life']
            size = max(1, int(p['radius'] * alpha))
            c = (int(255 * alpha), int(150 * alpha), int(60 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)

    def _dibujar_estela_motor(self, screen, cx, cy, display_w, display_h):
        """Estela de motor que se estira/atenua segun la velocidad REAL de
        este frame (self.motor_intensidad, ver _mover): quieto no se ve
        nada, a toda marcha se estira una cadena de destellos larga. En
        fase 1 (crucero) sale de las 4 toberas de popa; en fase 2 (esfera,
        sin toberas a la vista) es un resplandor generico detras."""
        intensidad = self.motor_intensidad
        if intensidad <= 0.05:
            return
        if self.phase == 1:
            ex = cx - display_w * 0.46
            for frac in (-0.24, -0.08, 0.08, 0.24):
                ey = cy + frac * display_h * 0.55
                largo = 16 + 42 * intensidad
                pasos = 6
                for i in range(pasos):
                    t = i / pasos
                    px = ex - largo * t
                    r = max(1, int((7 - 4 * t) * (0.5 + 0.5 * intensidad)))
                    alpha = int(150 * intensidad * (1 - t))
                    surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (140, 205, 255, alpha), (r, r), r)
                    screen.blit(surf, (int(px - r), int(ey - r)))
        else:
            glow_r = 18 + 24 * intensidad
            surf = pygame.Surface((int(glow_r * 2), int(glow_r * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (150, 170, 255, int(90 * intensidad)), (int(glow_r), int(glow_r)), int(glow_r))
            screen.blit(surf, (int(cx - glow_r), int(cy - glow_r)))

    def _dibujar_laser(self, screen, cx, cy, offset_x, offset_y):
        """Zocalo animado del laser: pulso naranja mientras carga (aviso
        para esquivar) y columna brillante de punta a punta mientras
        dispara."""
        display_w = int(sprites.MEGA_BOSS_DISPLAY_W * 0.72)
        dish_x = cx - display_w // 2 + display_w * sprites.MEGA_SPHERE_DISH_X_FRAC
        dish_y = cy - int(display_w * sprites.MEGA_SPRITE_H / sprites.MEGA_SPRITE_W) // 2 + \
            int(display_w * sprites.MEGA_SPRITE_H / sprites.MEGA_SPRITE_W) * sprites.MEGA_SPHERE_DISH_Y_FRAC
        dish_r = display_w * sprites.MEGA_SPHERE_DISH_R_FRAC

        if self.laser_state == "charging":
            t = 1.0 - max(0.0, self.laser_timer / 75.0)
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.03)
            glow_r = dish_r * (0.6 + 0.5 * t + 0.15 * pulse)
            glow = pygame.Surface((int(glow_r * 2), int(glow_r * 2)), pygame.SRCALPHA)
            alpha = int(120 + 100 * t)
            pygame.draw.circle(glow, (255, 120, 60, alpha), (int(glow_r), int(glow_r)), int(glow_r))
            screen.blit(glow, (dish_x - glow_r, dish_y - glow_r))
            warn_x = int(self.laser_target_x) + offset_x
            warn_alpha = int(90 * (0.4 + 0.6 * pulse))
            warn = pygame.Surface((10, GAME_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(warn, (255, 120, 60, warn_alpha), (0, 0, 10, GAME_HEIGHT))
            screen.blit(warn, (warn_x - 5, offset_y))
        elif self.laser_state == "firing":
            beam_x = int(self.laser_target_x) + offset_x
            beam = pygame.Surface((34, GAME_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(beam, (255, 220, 180, 90), (2, 0, 30, GAME_HEIGHT))
            pygame.draw.rect(beam, (255, 255, 255, 200), (12, 0, 10, GAME_HEIGHT))
            screen.blit(beam, (beam_x - 17, offset_y))
            glow = pygame.Surface((int(dish_r * 3), int(dish_r * 3)), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 240, 220, 220), (int(dish_r * 1.5), int(dish_r * 1.5)), int(dish_r * 1.5))
            screen.blit(glow, (dish_x - dish_r * 1.5, dish_y - dish_r * 1.5))

    def _dibujar_railgun(self, screen, cx, cy, offset_x, offset_y):
        """Aviso del cañon railgun (fase 1): linea de mira roja intermitente
        que marca la trayectoria exacta del disparo durante la carga, para
        que se pueda esquivar a tiempo el proyectil pesado que sigue."""
        if self.railgun_state != "charging":
            return
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.04)
        t = 1.0 - max(0.0, self.railgun_timer / 50.0)
        tx = int(self.railgun_target_x) + offset_x
        ty = int(self.railgun_target_y) + offset_y
        alpha = int(90 + 120 * t * (0.5 + 0.5 * pulse))
        line = pygame.Surface((abs(tx - cx) + 8, abs(ty - cy) + 8), pygame.SRCALPHA)
        x0 = 4 if tx >= cx else line.get_width() - 4
        y0 = 4 if ty >= cy else line.get_height() - 4
        x1 = line.get_width() - 4 if tx >= cx else 4
        y1 = line.get_height() - 4 if ty >= cy else 4
        pygame.draw.line(line, (255, 70, 60, alpha), (x0, y0), (x1, y1), 2)
        screen.blit(line, (min(cx, tx) - 4, min(cy, ty) - 4))
        reticle_r = 6 + int(4 * pulse)
        pygame.draw.circle(screen, (255, 90, 80, 220), (tx, ty), reticle_r, 2)

    def _dibujar_barra_vida(self, screen, cx, bar_y):
        bar_w, bar_h = 190, 14
        bar_x = cx - bar_w // 2
        hp_ratio = max(0, self.hp / self.max_hp)
        display_ratio = self.health_deplete_anim

        shake_x = shake_y = 0
        if self.health_shake > 0:
            shake_x = random.randint(-self.health_shake, self.health_shake)
            shake_y = random.randint(-self.health_shake, self.health_shake)
            self.health_shake -= 1

        draw_x, draw_y = bar_x + shake_x, bar_y + shake_y
        shadow = pygame.Surface((bar_w + 6, bar_h + 6), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 70), (3, 3, bar_w, bar_h), border_radius=bar_h // 2)
        screen.blit(shadow, (draw_x - 3, draw_y - 3))

        bg_rect = (draw_x, draw_y, bar_w, bar_h)
        pygame.draw.rect(screen, (20, 20, 35), bg_rect, border_radius=bar_h // 2)

        fill_w = int((bar_w - 2) * display_ratio)
        if fill_w > 0:
            color = ROSA if hp_ratio > 0.5 else (AMARILLO if hp_ratio > 0.25 else MELON)
            pygame.draw.rect(screen, color, (draw_x + 1, draw_y + 1, fill_w, bar_h - 2), border_radius=bar_h // 2)
        pygame.draw.rect(screen, WHITE, bg_rect, width=1, border_radius=bar_h // 2)
