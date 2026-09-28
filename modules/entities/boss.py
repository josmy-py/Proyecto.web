"""
El jefe final (oleada FINAL_BOSS_SPAWN_WAVE = 40, "La Anomalia Final"): una
calavera glicheada morada con dos ojos que siguen al jugador con la mirada.
No dispara balas comunes: sus ataques son su propia masa glicheada
disparada en forma de esquirlas/lanzas (ver AnomalyLanza). Ademas de la
rotacion SPREAD/AIMED/CIRCULAR/SPIRAL/RAIN tiene varios ataques propios
independientes: un tether que rastrea al jugador antes de descargar un
abanico de esas lanzas (_iniciar_tether), una embestida/carga directa
(_iniciar_embestida), una grieta que la teletransporta a otro angulo
(_iniciar_salto), una lluvia de esquirlas que marca una zona amplia antes
de hacerla estallar entera (_iniciar_lluvia) y, solo en fase 3, un grito
glicheado que expande un anillo con un hueco por donde escapar
(_iniciar_grito). Tether/embestida/salto son mutuamente excluyentes (un
solo ataque "de cuerpo" telegrafiado a la vez); lluvia/grito son
secundarios y pueden caer en paralelo. Se "rompe" visualmente cada tanto
(glitch, ver _dibujar_glitch) y esa misma rotura tambien se filtra al
campo de batalla a su alrededor en vez de quedarse solo en su propio
sprite (ver _dibujar_glitch_campo); cada rafaga de glitch (y cada cambio
de fase, al pasar los umbrales de 66%/33% de vida, ver take_damage)
tambien puede dejar 1-2 clones fantasma (_generar_clones) que se dibujan
con la misma corrupcion y disparan igual que la real, para que no se
distingan a simple vista. Sentinel/Dragon (oleadas 10/20) usan WaveBoss en
modules/core/boss_system.py, una clase hermana con la misma forma pero
definida por datos (BossDefinition) en vez de estar cableada como esta;
Titan (oleada 30) es otro jefe unico, ver modules/entities/titan_boss.py."""

import pygame
import random
import math
from modules.constants import ROSA, AMARILLO, MELON, WHITE, GAME_WIDTH, GAME_HEIGHT
from modules.systems.fonts import render_text
from modules.systems import sprites

# Tinte (color_casco, color_secundario) segun la fase: siempre dentro de la
# familia morada -es "una calavera morada", no cambia de paleta por fase-
# pero cada vez mas saturada/corrupta a medida que baja de vida.
TINTES_POR_FASE = {
    1: ((150, 130, 190), (110, 70, 170)),
    2: ((175, 90, 220), (140, 40, 200)),
    3: ((205, 60, 165), (175, 20, 125)),
}


class FinalBoss:
    """Jefe de la oleada 40. take_damage() sube de fase (1->2->3) al pasar
    los umbrales de 66%/33% de vida, y cada fase agrega patrones de ataque
    nuevos (ver _choose_pattern). Usa su propio sprite "anomaly" (calavera
    glicheada) de assets/sprites/boss si esta disponible."""

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH // 2
        self.y = 80
        self.target_x = self.x
        self.target_y = self.y
        self.active = True
        # La dificultad elegida en el menu tambien la escala a ella (antes
        # solo afectaba asteroides/alienigenas comunes).
        self.max_hp = max(1, int(800 * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.speed = 1.0 * dificultad
        self.shoot_timer = 20
        self.shoot_rate = max(6, int(20 / dificultad))
        self._dificultad = dificultad
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

        # posicion del jugador, guardada cada update() para que las dos
        # pupilas la sigan con la mirada en tiempo real dentro de draw()
        # (que no recibe la nave), igual que TitanBoss._dibujar_ojo.
        self._ship_x, self._ship_y = self.x, self.y + 400

        # Tether de vacio: un hilo de energia que sigue al jugador durante
        # un rato (se ve venir, telegrafiado) y despues se congela y
        # dispara un abanico de lanzas por esa posicion. Es un ataque
        # independiente de la rotacion SPREAD/AIMED/CIRCULAR/SPIRAL/RAIN de
        # mas abajo, corre en paralelo (ver _actualizar_tether).
        self.tether_cooldown = random.randint(170, 220)
        self.tether_state = None
        self.tether_timer = 0
        self.tether_target_x = self.x
        self.tether_target_y = self.y

        # Embestida: aviso in situ (telegrafiado, fija el rumbo hacia donde
        # estaba el jugador en ese instante) y despues una carga directa en
        # linea recta a gran velocidad; el propio cuerpo de la Anomalia es
        # el arma (ver AnomalyEmbestidaImpacto). Mutuamente excluyente con
        # el tether (no se disparan los dos telegrafiados a la vez).
        self.embestida_state = None
        self.embestida_timer = 0
        self.embestida_cooldown = random.randint(260, 340)
        self.embestida_origen_x, self.embestida_origen_y = self.x, self.y
        self.embestida_destino_x, self.embestida_destino_y = self.x, self.y
        self.embestida_trail = []

        # Salto (grieta que teletransporta): tambien parte del mismo turno
        # "primario" que tether/embestida (mutuamente excluyente con ellos
        # -no se telegrafian dos ataques de cuerpo a la vez). Abre una
        # grieta glicheada en el destino ANTES de saltar (rompe el patron
        # de que siempre ataca desde donde ya estaba) y dispara apenas
        # reaparece.
        self.salto_state = None
        self.salto_timer = 0
        self.salto_destino_x, self.salto_destino_y = self.x, self.y
        self.salto_cooldown = random.randint(300, 380)

        # Clones fantasma: "tartamudeo" del glitch. Se generan solos cada
        # vez que arranca una rafaga de glitch (ver _generar_clones) y no
        # necesitan estado propio de ataque: son puramente un efecto
        # secundario del glitch existente.
        self.clones = []

        # Lluvia de esquirlas dirigida: ataque secundario de area (no
        # mueve el cuerpo ni compite por el turno primario, puede caer en
        # paralelo a tether/embestida/salto). Marca una zona amplia
        # alrededor de donde estaba el jugador y la hace estallar entera
        # de golpe -hay que salir caminando de la zona, no esquivar
        # proyectil por proyectil.
        self.lluvia_state = None
        self.lluvia_timer = 0
        self.lluvia_cx, self.lluvia_cy = self.x, self.y
        self.lluvia_radio = 95
        self.lluvia_cooldown = random.randint(280, 360)

        # Grito glicheado: pulso de panico, solo en fase 3 (poca vida). Un
        # anillo lento se expande cubriendo toda la pantalla pero con un
        # hueco angular fijo -marcado durante el aviso- por donde si se
        # puede escapar.
        self.grito_state = None
        self.grito_timer = 0
        self.grito_gap_angle = 0.0
        self.grito_cooldown = random.randint(260, 340)

        # Glitch visual: rafagas cortas de corrupcion digital (franjas
        # desplazadas + aberracion cromatica, ver _dibujar_glitch) que
        # aparecen solas cada tanto, ademas de forzarse en cada cambio de
        # fase, y que ademas se filtran al campo de batalla de alrededor
        # (ver _dibujar_glitch_campo) y no solo al propio sprite. Se
        # vuelven mas frecuentes y evidentes en fases avanzadas -la nave se
        # "rompe" mas cuanto mas dañada esta.
        self.glitch_timer = 0
        self.glitch_cooldown = random.randint(120, 180)

    def _glitch_cooldown_base(self):
        return {1: (120, 180), 2: (75, 120), 3: (35, 65)}.get(self.phase, (120, 180))

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
            self.glitch_timer = 40
            self._generar_clones()
        elif self.hp < self.max_hp * 0.33 and self.phase == 2:
            self.phase = 3
            self.phase_transition = True
            self.phase_timer = 60
            self.pattern_duration = 100
            self.shoot_rate = max(6, int(14 / self._dificultad))
            self.glitch_timer = 50
            self._generar_clones()

    def update(self, ship=None):
        bullets = []

        if ship is not None:
            self._ship_x, self._ship_y = ship.x, ship.y

        if self.phase_transition:
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase_transition = False

        if self.embestida_state in ("aviso", "cargando") or self.salto_state == "grieta":
            pass  # el movimiento normal se pausa: lo controla _actualizar_embestida/_actualizar_salto
        else:
            self._update_movement()
        self.damaged_timer = max(0, self.damaged_timer - 1)

        if self.glitch_timer > 0:
            self.glitch_timer -= 1
        else:
            self.glitch_cooldown -= 1
            if self.glitch_cooldown <= 0:
                self.glitch_timer = random.randint(16, 28)
                lo, hi = self._glitch_cooldown_base()
                self.glitch_cooldown = random.randint(lo, hi)
                self._generar_clones()

        # clones fantasma: viven mientras dure el "tartamudeo" que los
        # genero y de vez en cuando disparan una lanza como la real, para
        # que no se distingan a simple vista mas alla de su posicion.
        clones_vivos = []
        for clon in self.clones:
            clon['vida'] -= 1
            clon['fase_disparo'] -= 1
            if clon['fase_disparo'] <= 0 and ship is not None:
                clon['fase_disparo'] = random.randint(22, 36)
                angle = math.atan2(ship.y - clon['y'], ship.x - clon['x'])
                bullets.append(AnomalyLanza(clon['x'], clon['y'], math.cos(angle) * 4.5, math.sin(angle) * 4.5))
            if clon['vida'] > 0:
                clones_vivos.append(clon)
        self.clones = clones_vivos

        # turno "primario" (compromete el cuerpo del jefe): tether, la
        # embestida y el salto se telegrafian y ejecutan de a uno por vez.
        primario_libre = self.tether_state is None and self.embestida_state is None and self.salto_state is None

        if not self.phase_transition:
            self.shoot_timer -= 1
            self.pattern_timer += 1
            self.special_attack_timer += 1

            if self.pattern_timer >= self.pattern_duration:
                self.pattern_timer = 0
                self._choose_pattern()

            if primario_libre and self.shoot_timer <= 0:
                self.shoot_timer = self.shoot_rate
                bullets.extend(self._create_attack(ship))

            if self.tether_state is not None:
                bullets.extend(self._actualizar_tether(ship))
            elif primario_libre:
                self.tether_cooldown -= 1
                if self.tether_cooldown <= 0:
                    self._iniciar_tether(ship)

            if self.embestida_state is not None:
                bullets.extend(self._actualizar_embestida())
            elif primario_libre:
                self.embestida_cooldown -= 1
                if self.embestida_cooldown <= 0:
                    self._iniciar_embestida(ship)

            if self.salto_state is not None:
                bullets.extend(self._actualizar_salto(ship))
            elif primario_libre:
                self.salto_cooldown -= 1
                if self.salto_cooldown <= 0:
                    self._iniciar_salto(ship)

            # ataques secundarios: no compiten por el turno primario (no
            # mueven el cuerpo, solo marcan/disparan), pueden caer en
            # paralelo a cualquiera de los de arriba.
            if self.lluvia_state is not None:
                bullets.extend(self._actualizar_lluvia())
            else:
                self.lluvia_cooldown -= 1
                if self.lluvia_cooldown <= 0:
                    self._iniciar_lluvia(ship)

            if self.phase == 3:
                if self.grito_state is not None:
                    bullets.extend(self._actualizar_grito())
                else:
                    self.grito_cooldown -= 1
                    if self.grito_cooldown <= 0:
                        self._iniciar_grito()

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
                'color': (255, 120, 40),
            })

        # motas de "alma" ambientales: a diferencia de las chispas de daño
        # de arriba, no dependen de recibir un golpe, solo del aura morada
        # de la calavera en reposo.
        if random.random() < 0.05:
            self.particles.append({
                'x': self.x + random.uniform(-30, 30),
                'y': self.y - random.uniform(10, 45),
                'vx': random.uniform(-0.3, 0.3),
                'vy': random.uniform(-0.7, -0.2),
                'life': random.randint(25, 45),
                'max_life': 45,
                'radius': random.randint(1, 3),
                'color': (190, 110, 235),
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

        return bullets

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
            bullets.append(AnomalyLanza(self.x + i * 25, self.y + 20, 0, 5))
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
            bullets.append(AnomalyLanza(self.x, self.y + 20, vx, vy))
        return bullets

    def _create_circular(self):
        bullets = []
        count = 12
        for i in range(count):
            angle = (2 * math.pi * i) / count
            speed = 3.5
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            bullets.append(AnomalyLanza(self.x, self.y, vx, vy))
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
            bullets.append(AnomalyLanza(self.x, self.y, vx, vy))
        return bullets

    def _create_rain(self):
        bullets = []
        for _ in range(5):
            x = random.randint(40, GAME_WIDTH - 40)
            bullets.append(AnomalyLanza(x, -10, 0, 4))
        return bullets

    def _iniciar_tether(self, ship):
        """Arranca el rastreo: el hilo de energia sigue la posicion del
        jugador durante _actualizar_tether antes de congelarse y disparar,
        asi que el jugador ve venir el ataque y puede moverse para que la
        descarga final caiga en otro lado."""
        self.tether_state = "tracking"
        self.tether_timer = 46
        self.tether_target_x = ship.x if ship is not None else self.x
        self.tether_target_y = ship.y if ship is not None else self.y + 300
        self.tether_cooldown = random.randint(230, 300)

    def _actualizar_tether(self, ship):
        self.tether_timer -= 1
        if self.tether_state == "tracking":
            if ship is not None:
                # suavizado (no 1:1 instantaneo): sigue al jugador pero no
                # se pega perfecto, deja un margen real para esquivar.
                self.tether_target_x += (ship.x - self.tether_target_x) * 0.15
                self.tether_target_y += (ship.y - self.tether_target_y) * 0.15
            if self.tether_timer <= 0:
                self.tether_state = "firing"
                self.tether_timer = 1
            return []
        # "firing": descarga de lanzas en abanico apuntando al punto ya
        # congelado (no al jugador en tiempo real).
        bullets = []
        angle_base = math.atan2(self.tether_target_y - self.y, self.tether_target_x - self.x)
        for i in range(-2, 3):
            angle = angle_base + i * 0.12
            speed = 6.5
            bullets.append(AnomalyLanza(self.x, self.y, math.cos(angle) * speed, math.sin(angle) * speed))
        self.tether_state = None
        return bullets

    def _iniciar_embestida(self, ship):
        """Embestida: primero tiembla/brilla in situ (aviso, telegrafiado)
        fijando el rumbo hacia donde estaba el jugador en ESE instante -no
        persigue durante la carga, el rumbo ya quedo fijo, deja una ventana
        real para esquivar a un lado- y despues se lanza en linea recta a
        gran velocidad, pasandose de largo del punto fijado en vez de
        frenarse encima."""
        self.embestida_state = "aviso"
        self.embestida_timer = 38
        self.embestida_trail = []
        self.embestida_origen_x, self.embestida_origen_y = self.x, self.y
        objetivo_x = ship.x if ship is not None else self.x
        objetivo_y = ship.y if ship is not None else self.y + 200
        dist = math.hypot(objetivo_x - self.x, objetivo_y - self.y) or 1.0
        alcance = dist + 260
        dx, dy = (objetivo_x - self.x) / dist, (objetivo_y - self.y) / dist
        self.embestida_destino_x = self.x + dx * alcance
        self.embestida_destino_y = self.y + dy * alcance

    def _actualizar_embestida(self):
        self.embestida_timer -= 1
        if self.embestida_state == "aviso":
            if self.embestida_timer <= 0:
                self.embestida_state = "cargando"
                self.embestida_timer = 20
                return [AnomalyEmbestidaImpacto(self, radius=48)]
            return []
        if self.embestida_state == "cargando":
            t = 1.0 - max(0.0, self.embestida_timer / 20.0)
            avance = t * t  # aceleracion de golpe: se siente una embestida real, no un desplazamiento parejo
            self.x = self.embestida_origen_x + (self.embestida_destino_x - self.embestida_origen_x) * avance
            self.y = self.embestida_origen_y + (self.embestida_destino_y - self.embestida_origen_y) * avance
            self.x = max(40, min(GAME_WIDTH - 40, self.x))
            self.y = max(20, min(GAME_HEIGHT - 60, self.y))
            self.embestida_trail.append((self.x, self.y))
            if len(self.embestida_trail) > 6:
                self.embestida_trail.pop(0)
            if self.embestida_timer <= 0:
                self.embestida_state = "retiro"
                self.embestida_timer = 34
                self.target_x = self.x
                self.target_y = min(self.y, GAME_HEIGHT // 2 - 10)
                self.embestida_cooldown = random.randint(340, 440)
            return []
        # "retiro": el movimiento normal ya se reanudo en update(), solo se
        # espera un respiro antes de poder rastrear/cargar de nuevo.
        if self.embestida_timer <= 0:
            self.embestida_state = None
            self.embestida_trail = []
        return []

    def _generar_clones(self):
        """'Tartamudeo' de glitch: al arrancar una rafaga (o al cambiar de
        fase) deja 1-2 copias translucidas de si misma cerca, que tambien
        disparan mientras dura la rafaga -el jugador no sabe cual es la
        real hasta que le pega- y se dibujan con exactamente la misma
        corrupcion que el original (ver draw()), asi que no hay ninguna
        diferencia visual fija que las delate."""
        self.clones = []
        n = random.randint(1, 2)
        for _ in range(n):
            angulo = random.uniform(0, 2 * math.pi)
            distancia = random.uniform(70, 130)
            self.clones.append({
                'x': self.x + math.cos(angulo) * distancia,
                'y': max(30, min(GAME_HEIGHT // 2 - 10, self.y + math.sin(angulo) * distancia)),
                'vida': max(self.glitch_timer, 20) + random.randint(0, 10),
                'fase_disparo': random.randint(10, 20),
            })

    def _iniciar_salto(self, ship):
        """Grieta que teletransporta: abre una grieta glicheada en el
        destino ANTES de saltar (rompe el patron de que siempre ataca
        desde donde ya estaba) y al cerrarse reaparece ahi de un salto,
        disparando de inmediato desde el nuevo angulo."""
        self.salto_state = "grieta"
        self.salto_timer = 46
        padding = 90
        self.salto_destino_x = random.randint(padding, GAME_WIDTH - padding)
        self.salto_destino_y = random.randint(40, GAME_HEIGHT // 2 - 20)
        self.salto_cooldown = random.randint(320, 420)

    def _actualizar_salto(self, ship):
        self.salto_timer -= 1
        if self.salto_timer > 0:
            return []
        self.x, self.y = self.salto_destino_x, self.salto_destino_y
        self.target_x, self.target_y = self.x, self.y
        self.glitch_timer = max(self.glitch_timer, 20)
        self._generar_clones()
        self.salto_state = None
        if ship is None:
            return []
        angle = math.atan2(ship.y - self.y, ship.x - self.x)
        lanzas = []
        for i in range(-1, 2):
            a = angle + i * 0.15
            lanzas.append(AnomalyLanza(self.x, self.y, math.cos(a) * 6.0, math.sin(a) * 6.0))
        return lanzas

    def _iniciar_lluvia(self, ship):
        """Lluvia de esquirlas dirigida: se le fractura un pedazo del
        propio casco (particulas) y telegrafia una zona amplia alrededor
        de donde estaba el jugador; en vez de esquivar proyectiles
        individuales, hay que salir caminando de la zona marcada antes de
        que estalle entera de golpe."""
        self.lluvia_state = "aviso"
        self.lluvia_timer = 50
        self.lluvia_cx = ship.x if ship is not None else self.x
        self.lluvia_cy = ship.y if ship is not None else self.y + 300
        self.lluvia_radio = 95
        self.lluvia_cooldown = random.randint(340, 440)
        for _ in range(14):
            self.particles.append({
                'x': self.x + random.uniform(-20, 20),
                'y': self.y + random.uniform(-15, 15),
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'life': random.randint(20, 40),
                'max_life': 40,
                'radius': random.randint(2, 4),
                'color': (190, 110, 235),
            })

    def _actualizar_lluvia(self):
        self.lluvia_timer -= 1
        if self.lluvia_timer <= 0:
            self.lluvia_state = None
            return self._crear_esquirlas_lluvia()
        return []

    def _crear_esquirlas_lluvia(self):
        esquirlas = []
        for _ in range(11):
            angulo = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, self.lluvia_radio)
            x = self.lluvia_cx + math.cos(angulo) * r
            y = self.lluvia_cy + math.sin(angulo) * r
            esquirlas.append(AnomalyEsquirlaSuelo(x, y))
        return esquirlas

    def _iniciar_grito(self):
        """Grito glicheado: solo en fase 3 (poca vida). Un pulso de
        energia se expande lento cubriendo todo el ancho de pantalla, pero
        con un hueco angular fijo -marcado durante el aviso- por donde si
        se puede escapar."""
        self.grito_state = "aviso"
        self.grito_timer = 46
        self.grito_gap_angle = random.uniform(0, 2 * math.pi)
        self.grito_cooldown = random.randint(340, 460)

    def _actualizar_grito(self):
        self.grito_timer -= 1
        if self.grito_timer <= 0:
            self.grito_state = None
            return self._crear_grito()
        return []

    def _crear_grito(self):
        bullets = []
        count = 22
        gap = math.radians(55)
        for i in range(count):
            angle = (2 * math.pi * i) / count
            diff = (angle - self.grito_gap_angle + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) < gap / 2:
                continue
            speed = 2.2
            bullets.append(AnomalyLanza(self.x, self.y, math.cos(angle) * speed, math.sin(angle) * speed, largo=34, ancho=10))
        return bullets

    def draw(self, screen, offset_x=0, offset_y=0):
        temblor_cuerpo_x = temblor_cuerpo_y = 0
        if self.embestida_state == "aviso":
            temblor_cuerpo_x = random.randint(-3, 3)
            temblor_cuerpo_y = random.randint(-3, 3)

        cx = int(self.x) + offset_x + temblor_cuerpo_x
        cy = int(self.y) + offset_y + temblor_cuerpo_y

        sombra_surf = pygame.Surface((176, 34), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra_surf, (0, 0, 0, 50), (0, 0, 176, 34))
        screen.blit(sombra_surf, (cx - 88, cy + 60))

        for i, (tx, ty) in enumerate(self.embestida_trail):
            alpha = int(90 * ((i + 1) / max(1, len(self.embestida_trail))))
            r = 40
            fantasma = pygame.Surface((r * 2, int(r * 1.2)), pygame.SRCALPHA)
            pygame.draw.ellipse(fantasma, (170, 90, 220, alpha), fantasma.get_rect())
            screen.blit(fantasma, (int(tx) + offset_x - r, int(ty) + offset_y - int(r * 0.6)))

        color_casco, color_secundario = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        ancho_sprite = int(sprites.BOSS_DISPLAY_W * sprites.ANOMALY_DISPLAY_SCALE)
        alto_sprite = int(sprites.BOSS_DISPLAY_H * sprites.ANOMALY_DISPLAY_SCALE)
        sprite = sprites.get_boss_surface(color_casco, color_secundario, ancho_sprite, alto_sprite, kind="anomaly")

        if sprite is not None:
            rect_sprite = sprite.get_rect(center=(cx, cy + 10))
            if self.glitch_timer > 0:
                self._dibujar_glitch_campo(screen, rect_sprite)
                self._dibujar_glitch(screen, sprite, rect_sprite)
            else:
                screen.blit(sprite, rect_sprite)
            for clon in self.clones:
                rect_clon = sprite.get_rect(center=(int(clon['x']) + offset_x, int(clon['y']) + offset_y + 10))
                self._dibujar_glitch(screen, sprite, rect_clon)
            manto_top = rect_sprite.top
            manto_cx = rect_sprite.centerx
            ojo_izq_x = rect_sprite.left + ancho_sprite * (0.5 - sprites.ANOMALY_OJO_DX_FRAC)
            ojo_der_x = rect_sprite.left + ancho_sprite * (0.5 + sprites.ANOMALY_OJO_DX_FRAC)
            ojo_y = rect_sprite.top + alto_sprite * sprites.ANOMALY_OJO_CY_FRAC
            ojo_r = ancho_sprite * sprites.ANOMALY_OJO_R_FRAC
        else:
            # Sin PNG en assets/sprites/boss no se dibuja un casco de
            # respaldo por codigo: se mantienen coordenadas relativas
            # razonables para que ojos/barra de vida sigan en su lugar.
            manto_top = cy - 60
            manto_cx = cx
            ojo_izq_x, ojo_der_x, ojo_y, ojo_r = cx - 26, cx + 26, cy - 5, 16

        self._dibujar_ojo(screen, ojo_izq_x, ojo_y, ojo_r)
        self._dibujar_ojo(screen, ojo_der_x, ojo_y, ojo_r)

        self._dibujar_embestida_aviso(screen, cx, cy, offset_x, offset_y)
        self._dibujar_salto_aviso(screen, offset_x, offset_y)
        self._dibujar_lluvia_aviso(screen, offset_x, offset_y)
        self._dibujar_grito_aviso(screen, cx, cy, offset_x, offset_y)

        barra_w = 150
        barra_h = 13
        barra_x = manto_cx - barra_w // 2
        barra_y = manto_top - 24
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
            alfa_transicion = int(150 * (0.5 + 0.5 * math.sin(self.phase_timer * 0.5)))
            transicion_surf = pygame.Surface((ancho_sprite + 40, alto_sprite + 40), pygame.SRCALPHA)
            pygame.draw.rect(transicion_surf, (255, 255, 255, alfa_transicion), (20, 20, ancho_sprite, alto_sprite), border_radius=10)
            screen.blit(transicion_surf, (manto_cx - ancho_sprite // 2 - 20, manto_top - 20))

        if self.damaged_timer > 0:
            alfa_impacto = int(140 * (self.damaged_timer / 10))
            impacto_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(impacto_surf, (255, 130, 150, alfa_impacto), (40, 40), 40)
            screen.blit(impacto_surf, (cx - 40, cy - 20))

        if self.tether_state == "tracking":
            self._dibujar_tether(screen, cx, cy, offset_x, offset_y)

        for p in self.particles:
            alpha = p['life'] / p['max_life']
            size = max(1, int(p['radius'] * alpha))
            base = p.get('color', (255, 120, 40))
            c = (int(base[0] * alpha), int(base[1] * alpha), int(base[2] * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)

    def _dibujar_ojo(self, screen, ojo_x, ojo_y, ojo_r):
        """La pupila es 100% dinamica (la cuenca vacia ya viene horneada en
        el sprite, ver _detalle_extra_casco en tools/generate_sprites.py):
        se desplaza cada frame hacia la nave, clampeada dentro de la
        cuenca, para que ambos ojos la sigan con la mirada en tiempo real
        (mismo truco que TitanBoss._dibujar_ojo, pero duplicado)."""
        zocalo_r = ojo_r * 0.72
        dx, dy = self._ship_x - ojo_x, self._ship_y - ojo_y
        dist = math.hypot(dx, dy) or 1.0
        alcance = zocalo_r * 0.5
        despl_x = dx / dist * min(alcance, dist * 0.06)
        despl_y = dy / dist * min(alcance, dist * 0.06)
        px, py = ojo_x + despl_x, ojo_y + despl_y
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
        glow_color = (200, 90, 235) if self.phase < 3 else (230, 60, 160)
        glow = pygame.Surface((int(zocalo_r * 3), int(zocalo_r * 3)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*glow_color, int(70 + 40 * pulse)), (glow.get_width() // 2, glow.get_height() // 2), int(zocalo_r * 1.3))
        screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))
        pygame.draw.circle(screen, glow_color, (int(px), int(py)), max(2, int(zocalo_r * 0.62)))
        pygame.draw.circle(screen, (250, 230, 255), (int(px), int(py)), max(2, int(zocalo_r * 0.28)))
        pygame.draw.circle(screen, WHITE, (int(px - zocalo_r * 0.14), int(py - zocalo_r * 0.14)), max(1, int(zocalo_r * 0.14)))

    def _dibujar_embestida_aviso(self, screen, cx, cy, offset_x, offset_y):
        """Telegrafiado de la embestida: una linea punteada pulsante que
        marca el rumbo exacto que va a seguir la carga, para que el
        jugador pueda leer con anticipacion hacia donde tiene que
        apartarse."""
        if self.embestida_state != "aviso":
            return
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.05)
        dx_tot = int(self.embestida_destino_x) + offset_x - cx
        dy_tot = int(self.embestida_destino_y) + offset_y - cy
        pasos = 16
        for i in range(pasos):
            if i % 2 == 0:
                continue
            f0 = i / pasos
            f1 = (i + 0.6) / pasos
            p0 = (cx + dx_tot * f0, cy + dy_tot * f0)
            p1 = (cx + dx_tot * f1, cy + dy_tot * f1)
            alpha = int(90 + 90 * pulse)
            self._dibujar_linea_alpha(screen, p0[0], p0[1], p1[0], p1[1], (200, 90, 235), alpha, ancho=3)
        aviso_r = 30 + int(14 * pulse)
        aviso_surf = pygame.Surface((aviso_r * 2, aviso_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(aviso_surf, (200, 90, 235, 90), (aviso_r, aviso_r), aviso_r, 4)
        screen.blit(aviso_surf, (cx - aviso_r, cy - aviso_r))

    def _dibujar_linea_alpha(self, screen, x0, y0, x1, y1, color, alpha, ancho=3):
        """Linea con alpha real entre dos puntos cualquiera (con blit
        sobre una superficie SRCALPHA chica): pygame.draw.line ignora el
        alpha del color si se dibuja directo sobre `screen`. El ancla de
        cada punto se calcula relativa al min(x0,x1)/min(y0,y1) -no un
        (4,4) fijo- para que funcione sin importar en que cuadrante caiga
        el segundo punto respecto del primero (ver _dibujar_tether, que
        resuelve el mismo problema por eje en vez de con una formula)."""
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        w = max(2, int(max_x - min_x) + 8)
        h = max(2, int(max_y - min_y) + 8)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        p0 = (x0 - min_x + 4, y0 - min_y + 4)
        p1 = (x1 - min_x + 4, y1 - min_y + 4)
        pygame.draw.line(surf, (*color, alpha), p0, p1, ancho)
        screen.blit(surf, (min_x - 4, min_y - 4))

    def _dibujar_salto_aviso(self, screen, offset_x, offset_y):
        """Telegrafiado de la grieta: una fractura glicheada pulsante en
        el punto exacto de destino, para que el jugador sepa desde donde
        va a venir el proximo ataque antes de que la Anomalia reaparezca
        ahi de un salto."""
        if self.salto_state != "grieta":
            return
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.06)
        zx = int(self.salto_destino_x) + offset_x
        zy = int(self.salto_destino_y) + offset_y
        r = 34
        surf = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
        c = surf.get_width() // 2
        alpha = int(120 + 100 * pulse)
        pygame.draw.circle(surf, (20, 4, 30, alpha), (c, c), r)
        pygame.draw.circle(surf, (200, 90, 235, alpha), (c, c), r, 3)
        for i in range(7):
            ang = i * (2 * math.pi / 7) + pulse
            ex, ey = c + math.cos(ang) * r * 1.4, c + math.sin(ang) * r * 1.4
            pygame.draw.line(surf, (230, 190, 255, alpha), (c, c), (ex, ey), 2)
        screen.blit(surf, (zx - c, zy - c))

    def _dibujar_lluvia_aviso(self, screen, offset_x, offset_y):
        """Telegrafiado de la lluvia de esquirlas: marca la zona entera
        que va a estallar (hay que salir caminando de ahi, no esquivar
        proyectil por proyectil)."""
        if self.lluvia_state != "aviso":
            return
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.05)
        r = int(self.lluvia_radio)
        zx, zy = int(self.lluvia_cx) + offset_x, int(self.lluvia_cy) + offset_y
        zona = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        c = r + 4
        alpha = int(70 + 60 * pulse)
        pygame.draw.circle(zona, (200, 90, 235, alpha // 2), (c, c), r)
        pygame.draw.circle(zona, (200, 90, 235, alpha), (c, c), r, 3)
        screen.blit(zona, (zx - c, zy - c))

    def _dibujar_grito_aviso(self, screen, cx, cy, offset_x, offset_y):
        """Telegrafiado del grito: marca con dos lineas el hueco angular
        fijo por donde va a poder escapar el anillo que esta por
        expandirse."""
        if self.grito_state != "aviso":
            return
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.06)
        largo = 700
        gap = math.radians(55)
        alpha = int(140 + 100 * pulse)
        for signo in (-1, 1):
            ang = self.grito_gap_angle + signo * gap / 2
            ex = cx + math.cos(ang) * largo
            ey = cy + math.sin(ang) * largo
            self._dibujar_linea_alpha(screen, cx, cy, ex, ey, (230, 90, 200), alpha, ancho=3)

    def _dibujar_glitch(self, screen, sprite, rect):
        """Corrupcion digital del propio sprite, en vez del blit normal: la
        calavera se "rompe" tambien visualmente cada tanto (y siempre en
        cada cambio de fase). Tres efectos superpuestos, tipico de glitch
        art: franjas horizontales cortadas y desplazadas en X al azar (como
        un datamosh, ahora con mas alcance y alguna franja invertida),
        aberracion cromatica (fantasmas rojo/cian del mismo sprite,
        corridos a los costados con mezcla aditiva) y ruido. Todo se
        recalcula frame a frame mientras dura glitch_timer, para que
        tiemble/titile en vez de quedarse en un unico corte fijo."""
        w, h = sprite.get_size()

        franja_h = max(3, h // random.randint(5, 9))
        y = 0
        while y < h:
            alto = min(franja_h, h - y)
            franja = sprite.subsurface((0, y, w, alto))
            if random.random() < 0.12:
                franja = pygame.transform.flip(franja, True, False)
            dx = random.randint(-26, 26) if random.random() < 0.65 else 0
            screen.blit(franja, (rect.x + dx, rect.y + y))
            y += alto

        despl = random.randint(5, 12)
        fantasma_rojo = sprites.tint(sprite, (255, 60, 70))
        fantasma_cian = sprites.tint(sprite, (60, 220, 255))
        screen.blit(fantasma_rojo, (rect.x - despl, rect.y), special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(fantasma_cian, (rect.x + despl, rect.y), special_flags=pygame.BLEND_RGBA_ADD)

        if random.random() < 0.4:
            ruido = pygame.Surface((w, max(2, h // 10)), pygame.SRCALPHA)
            ruido.fill((*WHITE[:3], random.randint(60, 140)))
            ruido_y = rect.y + random.randint(0, h - ruido.get_height())
            screen.blit(ruido, (rect.x, ruido_y))

    def _dibujar_glitch_campo(self, screen, rect_sprite):
        """Ademas de romper su propio sprite (_dibujar_glitch), la Anomalia
        tambien distorsiona el campo de batalla a su alrededor mientras
        dura la rafaga: se recorta una region del fondo YA dibujado
        (estrellas, balas, la nave...) y se le aplica el mismo datamosh +
        aberracion cromatica antes de que el casco se dibuje encima, como
        si el glitch se filtrara fuera de la propia nave en vez de quedarse
        contenido en su silueta."""
        sw, sh = screen.get_size()
        pad = 70
        x0 = max(0, rect_sprite.left - pad)
        y0 = max(0, rect_sprite.top - pad)
        x1 = min(sw, rect_sprite.right + pad)
        y1 = min(sh, rect_sprite.bottom + pad)
        w, h = x1 - x0, y1 - y0
        if w <= 4 or h <= 4:
            return
        campo = screen.subsurface((x0, y0, w, h)).copy()

        franja_h = max(4, h // random.randint(5, 9))
        y = 0
        while y < h:
            alto = min(franja_h, h - y)
            franja = campo.subsurface((0, y, w, alto)).copy()
            dx = random.randint(-22, 22) if random.random() < 0.5 else 0
            screen.blit(franja, (x0 + dx, y0 + y))
            y += alto

        despl = random.randint(4, 9)
        fantasma_rojo = sprites.tint(campo, (255, 60, 70))
        fantasma_cian = sprites.tint(campo, (60, 220, 255))
        screen.blit(fantasma_rojo, (x0 - despl, y0), special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(fantasma_cian, (x0 + despl, y0), special_flags=pygame.BLEND_RGBA_ADD)

    def _dibujar_tether(self, screen, cx, cy, offset_x, offset_y):
        """Hilo de energia violeta que conecta el nucleo con el punto que
        esta rastreando: la animacion en si misma es el aviso (se ve que
        sigue al jugador en tiempo real), asi que cuando se corta y
        dispara ya no sorprende."""
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.05)
        tx = int(self.tether_target_x) + offset_x
        ty = int(self.tether_target_y) + offset_y
        color = (200, 110, 255)
        ancho = int((tx - cx) or 1)
        alto = int((ty - cy) or 1)
        line_surf = pygame.Surface((abs(ancho) + 12, abs(alto) + 12), pygame.SRCALPHA)
        x0 = 6 if tx >= cx else line_surf.get_width() - 6
        y0 = 6 if ty >= cy else line_surf.get_height() - 6
        x1 = line_surf.get_width() - 6 if tx >= cx else 6
        y1 = line_surf.get_height() - 6 if ty >= cy else 6
        alpha = int(120 + 90 * pulse)
        # fleco cromatico del hilo (mismo truco que el casco y las lanzas):
        # dos copias rojo/cian corridas en X detras de la linea violeta.
        pygame.draw.line(line_surf, (255, 60, 70, alpha // 2), (x0 - 2, y0), (x1 - 2, y1), 2)
        pygame.draw.line(line_surf, (60, 220, 255, alpha // 2), (x0 + 2, y0), (x1 + 2, y1), 2)
        pygame.draw.line(line_surf, (*color, alpha), (x0, y0), (x1, y1), 3)
        screen.blit(line_surf, (min(cx, tx) - 6, min(cy, ty) - 6))
        marca_r = 7 + int(3 * pulse)
        pygame.draw.circle(screen, (255, 60, 70), (tx - 2, ty), marca_r, 2)
        pygame.draw.circle(screen, (60, 220, 255), (tx + 2, ty), marca_r, 2)
        pygame.draw.circle(screen, color, (tx, ty), marca_r, 2)
        nucleo_r = 5 + int(3 * pulse)
        pygame.draw.circle(screen, color, (cx, cy), nucleo_r)


class AnomalyLanza:
    """Ataque propio de la Anomalia: en vez de una bala/circulo comun,
    dispara su propia masa glicheada en forma de esquirla/lanza alargada,
    orientada segun su velocidad (vx, vy). Mismo aire cromatico/corrupto
    que el casco (fleco rojo/cian permanente + parpadeo de corrupcion
    ocasional, ver draw())."""

    def __init__(self, x, y, vx=0.0, vy=5.0, largo=30, ancho=9):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.largo = largo
        self.ancho = ancho
        self.radius = 5  # hitbox de colision, independiente del tamaño visual
        self.active = True
        self.trail = []
        self._glitch_fase = random.uniform(0, 10)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        if self.y > GAME_HEIGHT + 20 or self.y < -20 or self.x < -20 or self.x > GAME_WIDTH + 20:
            self.active = False

    def _puntas(self, cx, cy):
        vx, vy = self.vx, self.vy
        norm = math.hypot(vx, vy) or 1.0
        dx, dy = vx / norm, vy / norm
        nx, ny = -dy, dx
        punta = (cx + dx * self.largo * 0.6, cy + dy * self.largo * 0.6)
        cola_izq = (cx - dx * self.largo * 0.4 + nx * self.ancho * 0.5, cy - dy * self.largo * 0.4 + ny * self.ancho * 0.5)
        cola_der = (cx - dx * self.largo * 0.4 - nx * self.ancho * 0.5, cy - dy * self.largo * 0.4 - ny * self.ancho * 0.5)
        return punta, cola_izq, cola_der

    def draw(self, screen, offset_x=0, offset_y=0):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(80 * (i / max(1, len(self.trail))))
            r = max(1, int(self.ancho * 0.4 * (i / max(1, len(self.trail)))))
            trail_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (180, 100, 230, alpha), (r, r), r)
            screen.blit(trail_surf, (int(tx) + offset_x - r, int(ty) + offset_y - r))

        cx = self.x + offset_x
        cy = self.y + offset_y
        glow_surf = pygame.Surface((self.largo * 2, self.largo * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (190, 90, 235, 60), (self.largo, self.largo), int(self.largo * 0.7))
        screen.blit(glow_surf, (cx - self.largo, cy - self.largo))

        # fleco cromatico: fantasmas rojo/cian corridos a los costados,
        # como en el casco (_dibujar_glitch) pero permanente y mas sutil.
        despl = 2 + int(1.5 * math.sin(pygame.time.get_ticks() * 0.02 + self._glitch_fase))
        punta_r, izq_r, der_r = self._puntas(cx - despl, cy)
        punta_c, izq_c, der_c = self._puntas(cx + despl, cy)
        pygame.draw.polygon(screen, (255, 60, 90), [punta_r, izq_r, der_r])
        pygame.draw.polygon(screen, (60, 220, 255), [punta_c, izq_c, der_c])

        punta, izq, der = self._puntas(cx, cy)
        if random.random() < 0.06:
            # parpadeo de corrupcion: un frame invertido/estatico en vez de
            # la lanza normal.
            pygame.draw.polygon(screen, WHITE, [punta, izq, der])
        else:
            pygame.draw.polygon(screen, (195, 110, 235), [punta, izq, der])
            pygame.draw.polygon(screen, (235, 195, 255), [punta, izq, der], 1)


class AnomalyEmbestidaImpacto:
    """Zona de contacto de la embestida (ver FinalBoss._actualizar_embestida):
    en vez de reposicionarla a mano cuadro a cuadro desde afuera, guarda
    una referencia al propio jefe y sigue su posicion sola mientras dure la
    carga; duck-typed igual que las lanzas normales (x, y, radius, active,
    update(), draw()) para poder sumarse a boss_bullets sin tocar main.py.
    Se autodesactiva sola en cuanto el jefe deja el estado "cargando"."""

    def __init__(self, boss, radius=48, vida_max=40):
        self._boss = boss
        self.x = boss.x
        self.y = boss.y
        self.radius = radius
        self._vida_max = vida_max
        self._vida = vida_max
        self.active = True

    def update(self):
        self.x, self.y = self._boss.x, self._boss.y
        self._vida -= 1
        if self._vida <= 0 or self._boss.embestida_state != "cargando":
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.07)
        glow = pygame.Surface((self.radius * 3, self.radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (200, 90, 235, int(70 + 50 * pulse)),
                            (glow.get_width() // 2, glow.get_height() // 2), int(self.radius * 1.3))
        screen.blit(glow, (cx - glow.get_width() // 2, cy - glow.get_height() // 2))


class AnomalyEsquirlaSuelo:
    """Fragmento de casco fracturado de la lluvia de esquirlas dirigida
    (ver FinalBoss._iniciar_lluvia/_crear_esquirlas_lluvia): a diferencia
    de las lanzas normales no viaja, aparece de golpe ya dentro de la zona
    marcada durante el aviso (la zona entera "estalla" a la vez, no cae
    esquirla por esquirla) y se queda un instante clavada antes de
    desvanecerse; duck-typed igual que las lanzas (x, y, radius, active,
    update(), draw())."""

    def __init__(self, x, y, radius=14, vida=40):
        self.x = x
        self.y = y
        self.radius = radius
        self._vida_max = vida
        self._vida = vida
        self.active = True

    def update(self):
        self._vida -= 1
        if self._vida <= 0:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        alpha = max(0, min(255, int(255 * (self._vida / self._vida_max))))
        r = self.radius
        surf = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
        c = surf.get_width() // 2
        pygame.draw.circle(surf, (190, 90, 235, min(90, alpha // 2)), (c, c), int(r * 1.3))
        despl = 2
        pygame.draw.circle(surf, (255, 60, 90, alpha), (c - despl, c), r)
        pygame.draw.circle(surf, (60, 220, 255, alpha), (c + despl, c), r)
        pygame.draw.circle(surf, (195, 110, 235, alpha), (c, c), r)
        pygame.draw.circle(surf, (235, 195, 255, alpha), (c, c), r, 1)
        screen.blit(surf, (cx - c, cy - c))
