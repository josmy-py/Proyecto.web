"""
Titan del Vacio (oleada 30): jefe unico como FinalBoss/MegaBoss, no un
WaveBoss generico armado solo con BossDefinition. Pulpo mecanico corpulento
(sprite "titan": cresta blindada angular con hombros/pauldrones redondeados
bien anchos a los costados y un ojo-camara mecanico central, ver
tools/generate_sprites.py) que se queda en la mitad superior de la
pantalla en vez de recorrerla entera como los demas jefes, para que se
sienta un depredador que domina el campo desde arriba, no una nave que
vuela por ahi.

No dispara ni un solo proyectil: pelea puramente cuerpo a cuerpo con sus
tentaculos, que son sprites articulados (varias copias de
titan_tentaculo_*.png encadenadas y rotadas en tiempo real, ver
_dibujar_tentaculo_sprite) en vez de lineas vectoriales. TODOS -los idle y
los de ataque/guardia- salen de anclajes fijos sobre el propio cuerpo
(hombros, flancos, vientre, cresta; ver _ANCLA_*/_ancla_mundo), nunca de
afuera de pantalla: se ve claramente que son parte del pulpo. Los ataques
son lentos y muy telegrafiados -mucho tiempo de aviso para leerlos y
reposicionarse, salvo la emboscada que es deliberadamente mas corta- y
golpean con una zona de impacto real en el lugar y el instante exactos en
que el tentaculo llega, en vez de lanzar nada a distancia:

  SISMO (desde la cresta, arriba): un tentaculo baja desde la cresta hasta
  el punto marcado (la posicion de la nave al arrancar el aviso), se toma
  ~1.8s en estirarse del todo, golpea, y se retira despacio.

  BRAZO (desde un flanco, a los costados): un tentaculo sale del hombro
  izquierdo o derecho del propio cuerpo (al azar) siguiendo la altura de
  la nave durante ~1.8s y despues lanza un golpe corto y decisivo mas alla
  de donde llego arrastrandose.

  EMBOSCADA (desde el vientre, abajo): una puñalada rapida con mucho menos
  aviso que las otras dos -otro ritmo, no se puede leer solo con la
  memoria del sismo- para que no todos los golpes vengan siempre del
  mismo punto del cuerpo ni con el mismo tiempo de reaccion.

  ENJAMBRE (los 6 anclajes idle a la vez, ver _iniciar_enjambre): el
  ataque "definitivo" -cada uno de los tentaculos que normalmente se mecen
  solos en reposo se estira al mismo tiempo hacia su propio blanco, en
  abanico parejo por casi todo el ancho de pantalla a la altura de la
  nave. Cooldown bien largo (no es un ataque mas, es un evento) y el
  aviso mas extendido de todos, para poder leer donde quedan los huecos
  entre un tentaculo y el siguiente antes de que golpeen juntos.

Ademas puede CRUZAR dos tentaculos -uno por hombro- en X delante del
cuerpo, como brazos cruzados bloqueando un golpe (ver
guardia_state/bloquea_disparo/_guardia_puntas): bloquea los disparos del
jugador que caigan cerca de donde se cruzan, la unica forma de dañarlo es
esquivar la guardia y darle al ojo. Ese ojo, aparte, sigue a la nave con
la mirada en tiempo real (pupila 100% dinamica sobre el zocalo ya horneado
en el sprite, ver _dibujar_ojo)."""

import random
import math

from modules.constants import (
    ROSA, AMARILLO, MELON, WHITE, GAME_WIDTH, GAME_HEIGHT,
)
from modules.systems.fonts import render_text
from modules.systems import sprites

import pygame

# Tinte (color_casco, color_secundario) segun la fase del jefe.
TINTES_POR_FASE = {
    1: ((140, 100, 220), (200, 160, 255)),
    2: ((190, 90, 150), (240, 150, 190)),
    3: ((230, 80, 70), (255, 150, 110)),
}

# Anclajes de los tentaculos sobre el propio cuerpo (fracciones del
# rectangulo del sprite ya escalado, ver TitanBoss._ancla_mundo): TODOS
# los tentaculos -idle, ataques y guardia- salen de puntos del cuerpo,
# nunca de afuera de pantalla, para que se vea claramente que son parte
# del pulpo y no algo que aparece de la nada.
_ANCLA_HOMBRO_IZQ = (0.10, 0.58)
_ANCLA_HOMBRO_DER = (0.90, 0.58)
_ANCLA_FLANCO_IZQ = (0.02, 0.80)
_ANCLA_FLANCO_DER = (0.98, 0.80)
_ANCLA_VIENTRE_IZQ = (0.32, 0.99)
_ANCLA_VIENTRE_DER = (0.68, 0.99)
_ANCLA_VIENTRE_CENTRO = (0.50, 0.99)
_ANCLA_CRESTA = (0.50, 0.03)

# Los 6 anclajes que se mecen solos en reposo (ver _dibujar_tentaculos_idle)
# son tambien los que se suman TODOS a la vez en el Enjambre -el ataque
# "definitivo", ver _iniciar_enjambre-, cada uno con su angulo base propio
# para el balanceo idle.
_ANCLAS_IDLE = (
    (_ANCLA_HOMBRO_IZQ, -150), (_ANCLA_HOMBRO_DER, -30),
    (_ANCLA_FLANCO_IZQ, -172), (_ANCLA_FLANCO_DER, -8),
    (_ANCLA_VIENTRE_IZQ, -100), (_ANCLA_VIENTRE_DER, -80),
)


class TentaculoImpacto:
    """Zona de golpe de un tentaculo: no es un disparo, aparece ya en el
    lugar exacto donde el tentaculo llega en el instante en que llega, no
    viaja ni se lanza, y dura unos pocos frames nomas. Mismo "duck typing"
    que WaveBossBullet (x/y/radius/active/update/draw) para poder ir
    directo a la lista boss_bullets de main.py sin tocar nada ahi."""

    def __init__(self, x, y, radius=46, color=MELON, vida=16):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self._vida = vida
        self._vida_max = vida
        self.active = True

    def update(self):
        self._vida -= 1
        if self._vida <= 0:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        t = max(0.0, self._vida / self._vida_max)
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        r = int(self.radius * (0.55 + 0.45 * (1 - t)))
        surf = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
        centro = r + 6
        pygame.draw.circle(surf, (*self.color[:3], int(70 * t)), (centro, centro), r)
        pygame.draw.circle(surf, (*self.color[:3], int(200 * t)), (centro, centro), r, 4)
        pygame.draw.circle(surf, (255, 255, 255, int(160 * t)), (centro, centro), max(1, int(r * 0.35)))
        screen.blit(surf, (cx - centro, cy - centro))


class TitanBoss:
    """Jefe de la oleada 30. take_damage() sube de fase (1->2->3) al pasar
    los umbrales de 66%/33% de vida, igual que FinalBoss. Usa el sprite
    "titan" (cresta de pulpo mecanico con ojo central) de assets/sprites/boss
    si esta disponible, escalado mas grande que los demas jefes (ver
    sprites.TITAN_DISPLAY_SCALE)."""

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH // 2
        self.y = 130
        self.target_x = self.x
        self.target_y = self.y
        self.active = True
        # La dificultad elegida en el menu tambien lo escala (igual que
        # WaveBoss/FinalBoss/MegaBoss), aunque ya no tenga cadencia de
        # disparo propia: acelera el ritmo de sus ataques de tentaculo.
        self.max_hp = max(1, int(550 * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.rotation = 0
        self.rot_speed = 0.18
        self.speed = 0.5 * dificultad
        self._dificultad = dificultad
        self.phase = 1
        self.damaged_timer = 0
        self.particles = []
        self.move_timer = 0
        self.move_cooldown = 130
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.phase_transition = False
        self.phase_timer = 0
        self.name = "TITÁN DEL VACÍO"
        self.rewarded = False
        self._ship_x, self._ship_y = self.x, self.y + 400

        # Sismo: aviso (se estira) -> golpe (impacto, una vez) -> retiro
        # (se repliega). Todo lento: se puede leer y reposicionarse.
        dur = 1.0 / dificultad
        self._sismo_dur_aviso = 110
        self._sismo_dur_golpe = 18
        self._sismo_dur_retiro = 55
        self.sismo_cooldown = random.randint(220, 280) * dur
        self.sismo_state = None
        self.sismo_timer = 0
        self.sismo_x = self.x
        self.sismo_y = self.y + 400

        # Brazo lateral: mismo esquema de 3 fases, saliendo de un flanco
        # del propio cuerpo (izquierdo o derecho, al azar).
        self._brazo_dur_aviso = 110
        self._brazo_dur_golpe = 16
        self._brazo_dur_retiro = 55
        self.brazo_cooldown = random.randint(260, 330) * dur
        self.brazo_state = None
        self.brazo_timer = 0
        self.brazo_lado = "left"
        self.brazo_target_y = self.y + 400
        self.brazo_golpe_x = self.x

        # Emboscada: puñalada rapida desde el vientre (parte baja del
        # cuerpo, en vez de la cresta de arriba que usa el sismo) con
        # mucho menos aviso -otro ritmo, no se puede leer solo con la
        # memoria del sismo- para que los ataques no salgan siempre del
        # mismo punto del cuerpo ni con el mismo tiempo de reaccion.
        self._emboscada_dur_aviso = 46
        self._emboscada_dur_golpe = 10
        self._emboscada_dur_retiro = 30
        self.emboscada_cooldown = random.randint(200, 260) * dur
        self.emboscada_state = None
        self.emboscada_timer = 0
        self.emboscada_x = self.x
        self.emboscada_y = self.y + 400

        # Guardia: levanta un tentaculo por delante del cuerpo que bloquea
        # los disparos del jugador que le peguen a el (ver
        # bloquea_disparo). Apunta hacia donde estaba la nave al alzarse y
        # se queda fijo ahi mientras dura - hay que salir de esa linea para
        # poder pegarle al ojo.
        self._guardia_dur_subida = 22
        self._guardia_dur_activa = 130
        self._guardia_dur_bajada = 22
        self.guardia_cooldown = random.randint(240, 300) * dur
        self.guardia_state = None
        self.guardia_timer = 0
        self.guardia_x = self.x
        self.guardia_y = self.y + 160
        self._guardia_radio = 34

        # Enjambre: el ataque "definitivo" -los mismos 6 anclajes del idle
        # (_ANCLAS_IDLE) golpean TODOS a la vez, en abanico por casi todo
        # el ancho de pantalla. Mucho mas telegrafiado que los demas (es
        # el mas peligroso) y con un cooldown bien largo: no es un ataque
        # mas, es un evento que obliga a repensar toda la posicion.
        self._enjambre_dur_aviso = 130
        self._enjambre_dur_golpe = 18
        self._enjambre_dur_retiro = 50
        self.enjambre_cooldown = random.randint(360, 440) * dur
        self.enjambre_state = None
        self.enjambre_timer = 0
        self.enjambre_targets = []

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
        elif self.hp < self.max_hp * 0.33 and self.phase == 2:
            self.phase = 3
            self.phase_transition = True
            self.phase_timer = 60

    def bloquea_disparo(self, x, y):
        """True si el punto (x, y) -tipicamente la bala del jugador- cae
        dentro de alguno de los dos tentaculos de guardia ya cruzados en
        X delante del cuerpo (ver _guardia_puntas): main.py la descarta
        ahi (parry) en vez de dejarla llegar al cuerpo/ojo."""
        if self.guardia_state != "activa":
            return False
        for cx_, cy_ in self._guardia_zonas_bloqueo():
            dx, dy = x - cx_, y - cy_
            if (dx * dx + dy * dy) < self._guardia_radio ** 2:
                return True
        return False

    def _guardia_zonas_bloqueo(self):
        return (
            (self.guardia_x - 22, self.guardia_y),
            (self.guardia_x + 22, self.guardia_y),
        )

    def update(self, ship=None):
        bullets = []
        self._ship_x = ship.x if ship is not None else self.x
        self._ship_y = ship.y if ship is not None else self.y + 400

        if self.phase_transition:
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase_transition = False

        self._update_movement()
        self.rotation += self.rot_speed
        self.damaged_timer = max(0, self.damaged_timer - 1)

        if not self.phase_transition:
            if self.sismo_state is not None:
                bullets.extend(self._actualizar_sismo())
            else:
                self.sismo_cooldown -= 1
                if self.sismo_cooldown <= 0:
                    self._iniciar_sismo()

            if self.brazo_state is not None:
                bullets.extend(self._actualizar_brazo())
            else:
                self.brazo_cooldown -= 1
                if self.brazo_cooldown <= 0:
                    self._iniciar_brazo()

            if self.emboscada_state is not None:
                bullets.extend(self._actualizar_emboscada())
            else:
                self.emboscada_cooldown -= 1
                if self.emboscada_cooldown <= 0:
                    self._iniciar_emboscada()

            if self.guardia_state is not None:
                self._actualizar_guardia()
            else:
                self.guardia_cooldown -= 1
                if self.guardia_cooldown <= 0:
                    self._iniciar_guardia()

            if self.enjambre_state is not None:
                bullets.extend(self._actualizar_enjambre())
            else:
                self.enjambre_cooldown -= 1
                if self.enjambre_cooldown <= 0:
                    self._iniciar_enjambre()

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

        return bullets

    def _update_movement(self):
        """A diferencia de los demas jefes, Titan se queda en la mitad
        superior de la pantalla (target_y acotado bien arriba): domina el
        campo desde ahi en vez de recorrerlo entero."""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 10:
            self.move_timer += 1
            if self.move_timer >= self.move_cooldown:
                self.move_timer = 0
                padding = 130
                self.target_x = random.randint(padding, GAME_WIDTH - padding)
                self.target_y = random.randint(90, 160)
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
        self.x = max(110, min(GAME_WIDTH - 110, self.x))
        self.y = max(80, min(170, self.y))

    def _ancla_mundo(self, frac_x, frac_y):
        """Punto del propio cuerpo en coordenadas de mundo (sin offset de
        pantalla) segun una fraccion (frac_x, frac_y) del rectangulo del
        sprite ya escalado -mismo calculo que hace draw() para ubicar
        rect_sprite, pero disponible tambien fuera de draw() para que
        update()/_iniciar_* puedan anclar ahi el origen de un tentaculo."""
        ancho = sprites.BOSS_DISPLAY_W * sprites.TITAN_DISPLAY_SCALE
        alto = sprites.BOSS_DISPLAY_H * sprites.TITAN_DISPLAY_SCALE
        left = self.x - ancho / 2.0
        top = (self.y + 15) - alto / 2.0
        return left + ancho * frac_x, top + alto * frac_y

    # ------------------------------------------------------------ sismo

    def _iniciar_sismo(self):
        self.sismo_state = "aviso"
        self.sismo_timer = self._sismo_dur_aviso
        self.sismo_x = self._ship_x
        self.sismo_y = min(GAME_HEIGHT - 40, self._ship_y)
        self.sismo_cooldown = random.randint(220, 300) / self._dificultad

    def _actualizar_sismo(self):
        self.sismo_timer -= 1
        if self.sismo_state == "aviso":
            if self.sismo_timer <= 0:
                self.sismo_state = "golpe"
                self.sismo_timer = self._sismo_dur_golpe
                return [TentaculoImpacto(self.sismo_x, self.sismo_y, radius=52, color=MELON, vida=16)]
            return []
        if self.sismo_state == "golpe":
            if self.sismo_timer <= 0:
                self.sismo_state = "retiro"
                self.sismo_timer = self._sismo_dur_retiro
            return []
        # "retiro"
        if self.sismo_timer <= 0:
            self.sismo_state = None
        return []

    def _sismo_extension(self):
        """0..1: cuanto tentaculo hay afuera ahora mismo, para el dibujo."""
        if self.sismo_state == "aviso":
            return 1.0 - max(0.0, self.sismo_timer / self._sismo_dur_aviso)
        if self.sismo_state == "golpe":
            return 1.0
        if self.sismo_state == "retiro":
            return max(0.0, self.sismo_timer / self._sismo_dur_retiro)
        return 0.0

    # ------------------------------------------------------------ brazo

    def _iniciar_brazo(self):
        self.brazo_state = "aviso"
        self.brazo_timer = self._brazo_dur_aviso
        self.brazo_lado = random.choice(["left", "right"])
        self.brazo_target_y = self._ship_y
        self.brazo_cooldown = random.randint(280, 360) / self._dificultad

    def _actualizar_brazo(self):
        self.brazo_timer -= 1
        if self.brazo_state == "aviso":
            # suavizado (no 1:1 instantaneo): deja un margen real para que
            # moverse rapido saque el blanco de la altura marcada.
            self.brazo_target_y += (self._ship_y - self.brazo_target_y) * 0.05
            if self.brazo_timer <= 0:
                self.brazo_state = "golpe"
                self.brazo_timer = self._brazo_dur_golpe
                largo = GAME_WIDTH * 0.86
                self.brazo_golpe_x = largo if self.brazo_lado == "left" else GAME_WIDTH - largo
                return [TentaculoImpacto(self.brazo_golpe_x, self.brazo_target_y, radius=44, color=ROSA, vida=14)]
            return []
        if self.brazo_state == "golpe":
            if self.brazo_timer <= 0:
                self.brazo_state = "retiro"
                self.brazo_timer = self._brazo_dur_retiro
            return []
        if self.brazo_timer <= 0:
            self.brazo_state = None
        return []

    def _brazo_extremos(self):
        """(x0, y0, x1_actual, y1_actual) del tentaculo lateral ahora
        mismo, para el dibujo: sale del flanco del propio cuerpo (x0, y0 -
        ver _ANCLA_FLANCO_IZQ/DER) y llega hasta (x1, y1), nunca desde
        afuera de pantalla."""
        frac = _ANCLA_FLANCO_IZQ if self.brazo_lado == "left" else _ANCLA_FLANCO_DER
        x0, y0 = self._ancla_mundo(*frac)
        alcance_aviso = GAME_WIDTH * 0.62
        x_aviso = alcance_aviso if self.brazo_lado == "left" else GAME_WIDTH - alcance_aviso
        if self.brazo_state == "aviso":
            t = 1.0 - max(0.0, self.brazo_timer / self._brazo_dur_aviso)
            return x0, y0, x0 + (x_aviso - x0) * t, y0 + (self.brazo_target_y - y0) * t
        if self.brazo_state == "golpe":
            # sigue desde donde llego el aviso (x_aviso, brazo_target_y),
            # no desde el flanco: el golpe es la lunge final, no un
            # segundo estirón completo.
            t = 1.0 - max(0.0, self.brazo_timer / self._brazo_dur_golpe)
            return x0, y0, x_aviso + (self.brazo_golpe_x - x_aviso) * t, self.brazo_target_y
        if self.brazo_state == "retiro":
            t = max(0.0, self.brazo_timer / self._brazo_dur_retiro)
            return x0, y0, x0 + (self.brazo_golpe_x - x0) * t, y0 + (self.brazo_target_y - y0) * t
        return x0, y0, x0, y0

    # -------------------------------------------------------- emboscada

    def _iniciar_emboscada(self):
        self.emboscada_state = "aviso"
        self.emboscada_timer = self._emboscada_dur_aviso
        self.emboscada_x = self._ship_x
        self.emboscada_y = min(GAME_HEIGHT - 40, self._ship_y)
        self.emboscada_cooldown = random.randint(200, 280) / self._dificultad

    def _actualizar_emboscada(self):
        self.emboscada_timer -= 1
        if self.emboscada_state == "aviso":
            if self.emboscada_timer <= 0:
                self.emboscada_state = "golpe"
                self.emboscada_timer = self._emboscada_dur_golpe
                return [TentaculoImpacto(self.emboscada_x, self.emboscada_y, radius=40, color=AMARILLO, vida=14)]
            return []
        if self.emboscada_state == "golpe":
            if self.emboscada_timer <= 0:
                self.emboscada_state = "retiro"
                self.emboscada_timer = self._emboscada_dur_retiro
            return []
        # "retiro"
        if self.emboscada_timer <= 0:
            self.emboscada_state = None
        return []

    def _emboscada_extension(self):
        if self.emboscada_state == "aviso":
            return 1.0 - max(0.0, self.emboscada_timer / self._emboscada_dur_aviso)
        if self.emboscada_state == "golpe":
            return 1.0
        if self.emboscada_state == "retiro":
            return max(0.0, self.emboscada_timer / self._emboscada_dur_retiro)
        return 0.0

    # -------------------------------------------------------- enjambre

    def _iniciar_enjambre(self):
        """Reparte un blanco por cada uno de los 6 anclajes idle
        (_ANCLAS_IDLE), en abanico parejo por casi todo el ancho de
        pantalla a la altura actual de la nave: cuando golpeen todos
        juntos (ver _actualizar_enjambre) van a cubrir casi toda la
        cancha, asi que el aviso tiene que ser bien largo para poder leer
        donde quedan los huecos entre un tentaculo y el siguiente."""
        self.enjambre_state = "aviso"
        self.enjambre_timer = self._enjambre_dur_aviso
        n = len(_ANCLAS_IDLE)
        margen = 90
        paso = (GAME_WIDTH - margen * 2) / (n - 1)
        y_objetivo = min(GAME_HEIGHT - 50, self._ship_y)
        self.enjambre_targets = [(margen + i * paso, y_objetivo) for i in range(n)]
        self.enjambre_cooldown = random.randint(360, 440) / self._dificultad

    def _actualizar_enjambre(self):
        self.enjambre_timer -= 1
        if self.enjambre_state == "aviso":
            if self.enjambre_timer <= 0:
                self.enjambre_state = "golpe"
                self.enjambre_timer = self._enjambre_dur_golpe
                return [TentaculoImpacto(tx, ty, radius=42, color=AMARILLO, vida=16)
                        for tx, ty in self.enjambre_targets]
            return []
        if self.enjambre_state == "golpe":
            if self.enjambre_timer <= 0:
                self.enjambre_state = "retiro"
                self.enjambre_timer = self._enjambre_dur_retiro
            return []
        # "retiro"
        if self.enjambre_timer <= 0:
            self.enjambre_state = None
        return []

    def _enjambre_extension(self):
        if self.enjambre_state == "aviso":
            return 1.0 - max(0.0, self.enjambre_timer / self._enjambre_dur_aviso)
        if self.enjambre_state == "golpe":
            return 1.0
        if self.enjambre_state == "retiro":
            return max(0.0, self.enjambre_timer / self._enjambre_dur_retiro)
        return 0.0

    # ---------------------------------------------------------- guardia

    def _iniciar_guardia(self):
        self.guardia_state = "subida"
        self.guardia_timer = self._guardia_dur_subida
        self.guardia_x = max(200, min(GAME_WIDTH - 200, self._ship_x))
        self.guardia_y = self.y + 150

    def _actualizar_guardia(self):
        self.guardia_timer -= 1
        if self.guardia_timer <= 0:
            if self.guardia_state == "subida":
                self.guardia_state = "activa"
                self.guardia_timer = self._guardia_dur_activa
            elif self.guardia_state == "activa":
                self.guardia_state = "bajada"
                self.guardia_timer = self._guardia_dur_bajada
            else:
                self.guardia_state = None
                self.guardia_cooldown = random.randint(260, 340) / self._dificultad

    def _guardia_extension(self):
        if self.guardia_state == "subida":
            return 1.0 - max(0.0, self.guardia_timer / self._guardia_dur_subida)
        if self.guardia_state == "activa":
            return 1.0
        if self.guardia_state == "bajada":
            return max(0.0, self.guardia_timer / self._guardia_dur_bajada)
        return 0.0

    def _guardia_puntas(self):
        """Los dos tentaculos de guardia salen cada uno de un hombro y
        terminan del lado CONTRARIO al que salieron -se cruzan en X
        delante del cuerpo, como brazos cruzados bloqueando un golpe, en
        vez de un unico tentaculo alzado- convergiendo en (guardia_x,
        guardia_y)."""
        ancla_izq = self._ancla_mundo(*_ANCLA_HOMBRO_IZQ)
        ancla_der = self._ancla_mundo(*_ANCLA_HOMBRO_DER)
        punta_izq = (self.guardia_x + 22, self.guardia_y)
        punta_der = (self.guardia_x - 22, self.guardia_y)
        return ancla_izq, punta_izq, ancla_der, punta_der

    # ---------------------------------------------------------------- draw

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        sombra_surf = pygame.Surface((220, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra_surf, (0, 0, 0, 55), (0, 0, 220, 40))
        screen.blit(sombra_surf, (cx - 110, cy + 78))

        color_casco, color_secundario = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        ancho_sprite = int(sprites.BOSS_DISPLAY_W * sprites.TITAN_DISPLAY_SCALE)
        alto_sprite = int(sprites.BOSS_DISPLAY_H * sprites.TITAN_DISPLAY_SCALE)
        sprite = sprites.get_boss_surface(color_casco, color_secundario, ancho_sprite, alto_sprite, kind="titan")

        if sprite is not None:
            rect_sprite = sprite.get_rect(center=(cx, cy + 15))
            screen.blit(sprite, rect_sprite)
            manto_cx = rect_sprite.centerx
            manto_top = rect_sprite.top
            ojo_x = rect_sprite.left + ancho_sprite * sprites.TITAN_OJO_CX_FRAC
            ojo_y = rect_sprite.top + alto_sprite * sprites.TITAN_OJO_CY_FRAC
            ojo_r = ancho_sprite * sprites.TITAN_OJO_R_FRAC
        else:
            # Sin PNG en assets/sprites/boss no se dibuja un casco de
            # respaldo por codigo: se mantienen coordenadas relativas
            # razonables para que la barra de vida/tentaculos/ojo sigan en
            # su lugar.
            manto_cx = cx
            manto_top = cy - 60
            ojo_x, ojo_y, ojo_r = cx, cy - 10, 22

        self._dibujar_tentaculos_idle(screen, offset_x, offset_y)
        self._dibujar_ojo(screen, ojo_x, ojo_y, ojo_r)

        if self.sismo_state is not None:
            self._dibujar_sismo(screen, offset_x, offset_y)
        if self.brazo_state is not None:
            self._dibujar_brazo(screen, offset_x, offset_y)
        if self.emboscada_state is not None:
            self._dibujar_emboscada(screen, offset_x, offset_y)
        if self.enjambre_state is not None:
            self._dibujar_enjambre(screen, offset_x, offset_y)
        if self.guardia_state is not None:
            self._dibujar_guardia(screen, offset_x, offset_y)

        barra_w = 160
        barra_h = 14
        barra_x = manto_cx - barra_w // 2
        barra_y = manto_top - 26
        proporcion_vida = max(0, self.hp / self.max_hp)
        proporcion_mostrada = self.health_deplete_anim

        temblor_x = temblor_y = 0
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

        pygame.draw.rect(screen, WHITE, fondo_barra_rect, width=1, border_radius=barra_h // 2)

        porcentaje = f"{int(proporcion_vida * 100)}%"
        porcentaje_surf = render_text(porcentaje, 10, WHITE)
        screen.blit(porcentaje_surf, (cx - porcentaje_surf.get_width() // 2, barra_dibujo_y - 14))

        if self.phase_transition:
            destello_w, destello_h = ancho_sprite, alto_sprite
            alfa_transicion = int(150 * (0.5 + 0.5 * math.sin(self.phase_timer * 0.5)))
            transicion_surf = pygame.Surface((destello_w + 40, destello_h + 40), pygame.SRCALPHA)
            pygame.draw.rect(transicion_surf, (255, 255, 255, alfa_transicion), (20, 20, destello_w, destello_h), border_radius=10)
            screen.blit(transicion_surf, (manto_cx - destello_w // 2 - 20, manto_top - 20))

        if self.damaged_timer > 0:
            alfa_impacto = int(140 * (self.damaged_timer / 10))
            impacto_surf = pygame.Surface((90, 90), pygame.SRCALPHA)
            pygame.draw.circle(impacto_surf, (255, 130, 150, alfa_impacto), (45, 45), 45)
            screen.blit(impacto_surf, (cx - 45, cy - 20))

        for p in self.particles:
            alpha = p['life'] / p['max_life']
            size = max(1, int(p['radius'] * alpha))
            c = (int(230 * alpha), int(180 * alpha), int(255 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)

    def _dibujar_ojo(self, screen, ojo_x, ojo_y, ojo_r):
        """La pupila es 100% dinamica (el aro/iris ya viene horneado en el
        sprite, ver _detalle_extra_casco en tools/generate_sprites.py):
        se desplaza cada frame hacia la nave, clampeada dentro del zocalo,
        para que el ojo la siga con la mirada en tiempo real."""
        zocalo_r = ojo_r * 0.42
        dx, dy = self._ship_x - ojo_x, self._ship_y - ojo_y
        dist = math.hypot(dx, dy) or 1.0
        alcance = zocalo_r * 0.55
        despl_x = dx / dist * min(alcance, dist * 0.06)
        despl_y = dy / dist * min(alcance, dist * 0.06)
        px, py = ojo_x + despl_x, ojo_y + despl_y
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
        glow_color = (255, 60, 50) if self.phase < 3 else (255, 90, 40)
        glow = pygame.Surface((int(zocalo_r * 3), int(zocalo_r * 3)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*glow_color, int(70 + 40 * pulse)), (glow.get_width() // 2, glow.get_height() // 2), int(zocalo_r * 1.3))
        screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))
        pygame.draw.circle(screen, (18, 6, 8), (int(px), int(py)), int(zocalo_r * 0.85))
        pygame.draw.circle(screen, glow_color, (int(px), int(py)), max(2, int(zocalo_r * 0.4)))
        pygame.draw.circle(screen, WHITE, (int(px - zocalo_r * 0.22), int(py - zocalo_r * 0.22)), max(1, int(zocalo_r * 0.16)))

    # ------------------------------------------------------ tentaculos (sprites)

    def _dibujar_tentaculo_sprite(self, screen, x0, y0, x1, y1, t, color, offset_x=0, offset_y=0,
                                  grosor=1.0, ondulado=True, n_segmentos=7):
        """Encadena copias rotadas/escaladas de titan_tentaculo_*.png entre
        (x0,y0) y una fraccion t (0..1) del camino a (x1,y1): con t
        creciendo en el tiempo se ve al tentaculo estirarse de verdad en
        vez de una linea vectorial. Reutilizado por el sismo, el brazo, la
        guardia y los tentaculos idle - son sprites, no dibujo a mano."""
        if t <= 0.001:
            return
        dx, dy = x1 - x0, y1 - y0
        largo_total = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / largo_total, dx / largo_total
        fase = pygame.time.get_ticks() * 0.004
        puntos = []
        for i in range(n_segmentos + 1):
            frac = (i / n_segmentos) * t
            px = x0 + dx * frac
            py = y0 + dy * frac
            if ondulado:
                onda = math.sin(fase + i * 0.9) * 5 * frac
                px += nx * onda
                py += ny * onda
            puntos.append((px + offset_x, py + offset_y))

        for i in range(len(puntos) - 1):
            ax, ay = puntos[i]
            bx, by = puntos[i + 1]
            seg_dx, seg_dy = bx - ax, by - ay
            seg_len = math.hypot(seg_dx, seg_dy)
            if seg_len < 1:
                continue
            angulo = math.degrees(math.atan2(seg_dy, seg_dx))
            factor = grosor * (1.0 - (i / n_segmentos) * 0.55)
            ancho_spr = max(12, (int(seg_len * 1.3) // 4) * 4)
            alto_spr = max(8, int(sprites.TITAN_TENTACULO_H * (ancho_spr / sprites.TITAN_TENTACULO_W) * factor))
            spr = sprites.get_titan_tentaculo_surface(color, ancho_spr, alto_spr)
            if spr is None:
                continue
            rotado = pygame.transform.rotate(spr, -angulo)
            rect = rotado.get_rect(center=(int(ax + seg_dx * 0.5), int(ay + seg_dy * 0.5)))
            screen.blit(rotado, rect)

    def _dibujar_tentaculos_idle(self, screen, offset_x, offset_y):
        """Tentaculos grandes y gruesos que salen de TODO el cuerpo -de
        los hombros, los flancos y el vientre, no solo en fila desde
        abajo del manto- y se mecen solos, cada uno con su propio angulo
        base, cuando no esta atacando: la firma visual de "pulpo vivo",
        intimidante incluso en reposo."""
        color_casco, _ = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        color = tuple(max(0, c - 30) for c in color_casco)
        for i, (frac, ang_base_grados) in enumerate(_ANCLAS_IDLE):
            x0, y0 = self._ancla_mundo(*frac)
            fase = self.rotation * 4 + i * 1.3
            balanceo_grados = math.sin(fase) * 14
            # largos y pocos segmentos (no muchos chicos): asi se leen
            # como miembros gruesos de verdad, no una fila de puntitos.
            largo = 100 + 18 * math.sin(self.rotation * 1.4 + i * 0.7)
            ang = math.radians(ang_base_grados + balanceo_grados)
            x1 = x0 + math.cos(ang) * largo
            y1 = y0 + math.sin(ang) * largo
            self._dibujar_tentaculo_sprite(screen, x0, y0, x1, y1, 1.0, color, offset_x, offset_y,
                                           grosor=2.1, n_segmentos=3)

    def _dibujar_sismo(self, screen, offset_x, offset_y):
        t = self._sismo_extension()
        color_casco, _ = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        x0, y0 = self._ancla_mundo(*_ANCLA_CRESTA)
        self._dibujar_tentaculo_sprite(
            screen, x0, y0, self.sismo_x, self.sismo_y, t, color_casco, offset_x, offset_y,
            grosor=1.6, n_segmentos=8,
        )
        if self.sismo_state == "aviso":
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.02)
            radio = 14 + 10 * pulse
            ax, ay = (x0 + (self.sismo_x - x0) * t) + offset_x, (y0 + (self.sismo_y - y0) * t) + offset_y
            pygame.draw.circle(screen, (255, 220, 120), (int(ax), int(ay)), int(radio), 3)

    def _dibujar_brazo(self, screen, offset_x, offset_y):
        # _brazo_extremos() ya resuelve el x1/y1 actual (la interpolacion
        # segun el estado/timer vive ahi), asi que aca siempre se dibuja
        # el segmento entero x0->x1 (t=1.0), no una segunda interpolacion.
        x0, y0, x1, y1 = self._brazo_extremos()
        color_casco, _ = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        self._dibujar_tentaculo_sprite(
            screen, x0, y0, x1, y1, 1.0, color_casco, offset_x, offset_y,
            grosor=1.6, n_segmentos=8, ondulado=self.brazo_state != "golpe",
        )
        if self.brazo_state == "aviso":
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.02)
            pygame.draw.circle(screen, (255, 150, 190), (int(x1) + offset_x, int(y1) + offset_y), int(10 + 6 * pulse), 3)

    def _dibujar_emboscada(self, screen, offset_x, offset_y):
        t = self._emboscada_extension()
        color_casco, _ = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        x0, y0 = self._ancla_mundo(*_ANCLA_VIENTRE_CENTRO)
        self._dibujar_tentaculo_sprite(
            screen, x0, y0, self.emboscada_x, self.emboscada_y, t, color_casco, offset_x, offset_y,
            grosor=1.3, n_segmentos=6, ondulado=self.emboscada_state != "golpe",
        )
        if self.emboscada_state == "aviso":
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.03)
            ax = (x0 + (self.emboscada_x - x0) * t) + offset_x
            ay = (y0 + (self.emboscada_y - y0) * t) + offset_y
            pygame.draw.circle(screen, (255, 200, 140), (int(ax), int(ay)), int(9 + 5 * pulse), 2)

    def _dibujar_enjambre(self, screen, offset_x, offset_y):
        """Los 6 anclajes idle (_ANCLAS_IDLE) estirandose TODOS a la vez
        hacia su propio blanco (_iniciar_enjambre): el ataque mas grande
        del Titan, cubre casi todo el ancho de pantalla de un saque."""
        t = self._enjambre_extension()
        color_casco, _ = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        for i, (frac, _ang) in enumerate(_ANCLAS_IDLE):
            if i >= len(self.enjambre_targets):
                break
            x0, y0 = self._ancla_mundo(*frac)
            tx, ty = self.enjambre_targets[i]
            self._dibujar_tentaculo_sprite(
                screen, x0, y0, tx, ty, t, color_casco, offset_x, offset_y,
                grosor=1.8, n_segmentos=7, ondulado=self.enjambre_state != "golpe",
            )
        if self.enjambre_state == "aviso":
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.02)
            for tx, ty in self.enjambre_targets:
                ax, ay = tx + offset_x, ty + offset_y
                pygame.draw.circle(screen, (255, 220, 120), (int(ax), int(ay)), int(14 + 8 * pulse), 3)

    def _dibujar_guardia(self, screen, offset_x, offset_y):
        """Dos tentaculos -uno por hombro- que se cruzan en X delante del
        cuerpo, como brazos cruzados bloqueando un golpe (ver
        _guardia_puntas/bloquea_disparo), en vez de un unico tentaculo
        alzado."""
        ancla_izq, punta_izq, ancla_der, punta_der = self._guardia_puntas()
        t = self._guardia_extension()
        color_casco, _ = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        color_guardia = tuple(min(255, c + 35) for c in color_casco)
        self._dibujar_tentaculo_sprite(
            screen, ancla_izq[0], ancla_izq[1], punta_izq[0], punta_izq[1], t, color_guardia,
            offset_x, offset_y, grosor=1.7, n_segmentos=6, ondulado=False,
        )
        self._dibujar_tentaculo_sprite(
            screen, ancla_der[0], ancla_der[1], punta_der[0], punta_der[1], t, color_guardia,
            offset_x, offset_y, grosor=1.7, n_segmentos=6, ondulado=False,
        )
        if self.guardia_state == "activa":
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.015)
            gx, gy = self.guardia_x + offset_x, self.guardia_y + offset_y
            glow = pygame.Surface((self._guardia_radio * 5, self._guardia_radio * 3), pygame.SRCALPHA)
            gw, gh = glow.get_width() // 2, glow.get_height() // 2
            pygame.draw.ellipse(glow, (*color_guardia[:3], int(50 + 30 * pulse)),
                                 (0, 0, glow.get_width(), glow.get_height()))
            screen.blit(glow, (gx - gw, gy - gh))
