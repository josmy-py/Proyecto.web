"""
Coloso Estelar, el jefe final de la oleada 50 (constants.MEGA_BOSS_SPAWN_WAVE),
en pixel art neon (artes "coloso_crucero" y "coloso_esfera" de
tools/generate_pixel_sprites.py). Pelea en dos fases y hace un solo ataque
grande a la vez, siempre avisado:

  FASE 1, CRUCERO DE ASALTO (acorazado con la proa hacia abajo):
    ANDANADA: las troneras de las alas se prenden de a una y despues
    disparan en el mismo orden, una ola que barre de un lado al otro.
    MISILES: los silos parpadean y salen misiles que giran despacio hacia
    la nave; un giro brusco los deja atras.
    CAÑON DE RIEL: una mira sigue a la nave, se pone roja y queda fija un
    momento antes del disparo pesado.

  A la mitad de la vida el crucero estalla en pedazos que implosionan y
  forman la ESFERA DE COMBATE:
    SUPERLASER: la esfera se acomoda encima de la nave marcando la
    columna, se frena y dispara un rayo de arriba abajo.
    TORRETAS: las cuatro torretas cargan y sueltan una espiral.
    MINAS: salen de la trinchera, se clavan, marcan su radio y estallan.
    METEOROS: columnas de aviso arriba y despues caen rocas por ahi.

  En las dos fases lanza cazas de escolta (AlienShip) desde el hangar,
  con la bahia destellando antes. En la esfera se abre una grieta de
  arcoiris que crece con el daño: un guiño al mundo del gato secreto.

update() devuelve {"bullets": [...], "asteroides": [...], "alien_ships": [...]}
y main.py reparte cada lista."""

import math
import random

import pygame

from modules.constants import (
    GAME_WIDTH, GAME_HEIGHT, WHITE, ROSA,
)
from modules.core.boss_system import WaveBossBullet
from modules.entities.asteroid import Asteroid
from modules.entities.enemy import AlienShip
from modules.entities.nyan_boss import ARCOIRIS
from modules.systems import pixelfx, sprites
from modules.systems.fonts import render_text

MEGA_BOSS_MAX_HP = 2800
MEGA_BOSS_PHASE2_HP_RATIO = 0.5

# cazas de escolta: gris metalico, se leen como naves propias del Coloso
CAZA_ESCOLTA_COLOR = (98, 102, 114)

NEON_1 = sprites.color_neon(sprites.MEGA_FASES["cruiser"][2])
NEON_2 = sprites.color_neon(sprites.MEGA_FASES["sphere"][2])
ROJO_AVISO = (255, 70, 90)
AMBAR = (255, 190, 80)

# puntos del crucero respecto del centro del sprite (grilla x3)
TRONERAS = tuple((x, 15) for x in (-123, -105, -87, -69, 69, 87, 105, 123))
CANON = (0, 74)
HANGARES = ((-42, 21), (42, 21))
TOBERAS = (-33, -18, 18, 33)
TOBERAS_Y = -76
SILOS = ((-27, -30), (27, -30))
# puntos de la esfera
PARABOLA = (0, 44)
TORRETAS = ((-90, -51), (90, -51), (-90, 51), (90, 51))
COMPUERTAS = ((-100, 0), (100, 0))


class ColosoMisil:
    """Misil que sale hacia arriba y gira despacio hacia la nave. Deja de
    seguirla al rato, asi que un desvio a tiempo lo pasa de largo."""

    def __init__(self, x, y, lado, ship):
        self.x, self.y = float(x), float(y)
        self.ang = -math.pi / 2 + lado * 0.6
        self.vel = 2.0
        self.ship = ship
        self.radius = 6
        self.active = True
        self.t = 0
        self.humo = []

    def update(self):
        self.t += 1
        if self.ship is not None and 12 < self.t < 100:
            deseado = math.atan2(self.ship.y - self.y, self.ship.x - self.x)
            giro = (deseado - self.ang + math.pi) % (2 * math.pi) - math.pi
            self.ang += max(-0.05, min(0.05, giro))
        self.vel = min(5.2, self.vel + 0.08)
        self.x += math.cos(self.ang) * self.vel
        self.y += math.sin(self.ang) * self.vel
        if self.t % 3 == 0:
            self.humo.append([self.x, self.y, 14])
        for h in self.humo:
            h[2] -= 1
        self.humo = [h for h in self.humo if h[2] > 0]
        if not (-60 < self.x < GAME_WIDTH + 60 and -80 < self.y < GAME_HEIGHT + 60):
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        for hx, hy, vida in self.humo:
            lado = 4 if vida > 7 else 2
            gris = 60 + vida * 6
            screen.fill((gris, gris, gris + 20), (int(hx) + offset_x - lado // 2, int(hy) + offset_y - lado // 2, lado, lado))
        pixelfx.misil(screen, self.x + offset_x, self.y + offset_y, self.ang, self.t)


class ColosoLaser:
    """Superlaser de la esfera. Como el rayo del Centinela, se porta como
    una bala (x, y, radius, active): cada cuadro se pone en el punto de la
    columna mas cercano a la nave."""

    def __init__(self, jefe, ship, ancho=64, vida=42):
        self.jefe = jefe
        self.ship = ship
        self.ancho = ancho
        self.radius = ancho // 2 - 8
        self.vida = vida
        self.vida_max = vida
        self.active = True
        self.t = 0
        self.x = jefe.x
        self.y = jefe.y + PARABOLA[1]

    def update(self):
        self.t += 1
        self.vida -= 1
        if self.vida <= 0 or not self.jefe.active or self.jefe.frag_stage is not None:
            self.active = False
            return
        y0 = self.jefe.y + PARABOLA[1]
        self.x = self.jefe.x
        self.y = max(y0, self.ship.y if self.ship is not None else GAME_HEIGHT)

    def draw(self, screen, offset_x=0, offset_y=0):
        x = int(self.jefe.x) + offset_x
        y0 = int(self.jefe.y + PARABOLA[1]) + offset_y
        k = min(1.0, self.vida / 8, (self.vida_max - self.vida + 1) / 5)
        ancho = int(self.ancho * k) // 4 * 4
        if ancho <= 0:
            return
        alto = screen.get_height() - y0
        brillo = pygame.Surface((ancho + 28, alto))
        brillo.fill(tuple(int(c * 0.25) for c in NEON_2))
        brillo.fill(tuple(int(c * 0.65) for c in NEON_2), (14, 0, ancho, alto))
        screen.blit(brillo, (x - ancho // 2 - 14, y0), special_flags=pygame.BLEND_RGB_ADD)
        nucleo = max(4, ancho // 3) // 2 * 2
        screen.fill(pixelfx.aclarar(NEON_2, 0.8), (x - nucleo // 2, y0, nucleo, alto))
        for yy in range(y0 + (self.t * 8) % 36, y0 + alto, 36):
            screen.fill(pixelfx.aclarar(NEON_2, 0.4), (x - ancho // 2, yy, ancho, 4))
        pixelfx.dibujar_halo(screen, NEON_2, x, y0, 30)


class ColosoMina:
    """Mina de la esfera: sale despedida hasta su lugar, se clava, marca su
    radio y el jefe la hace estallar (ver MegaBoss._actualizar_minas)."""

    ARMADO = 75

    def __init__(self, jefe, destino):
        self.jefe = jefe
        self.x, self.y = float(jefe.x), float(jefe.y)
        self.destino = destino
        self.radius = 9
        self.active = True
        self.t = 0
        self.armada = 0

    def update(self):
        self.t += 1
        if not self.jefe.active or self.jefe.frag_stage is not None:
            self.active = False
            return
        if self.armada == 0:
            dx, dy = self.destino[0] - self.x, self.destino[1] - self.y
            if math.hypot(dx, dy) < 3:
                self.armada = 1
            else:
                self.x += dx * 0.09
                self.y += dy * 0.09
        else:
            self.armada += 1

    def draw(self, screen, offset_x=0, offset_y=0):
        x, y = int(self.x) + offset_x, int(self.y) + offset_y
        if self.armada:
            prog = self.armada / self.ARMADO
            color = ROJO_AVISO if (self.t // max(2, int(8 - prog * 6))) % 2 else NEON_2
            n = 16
            for i in range(n):
                if (i + self.t // 3) % 2:
                    continue
                a = 2 * math.pi * i / n
                screen.fill(color, (int(x + math.cos(a) * 58) - 2, int(y + math.sin(a) * 58) - 2, 4, 4))
        else:
            color = NEON_2
        screen.fill(pixelfx.CONTORNO, (x - 7, y - 7, 14, 14))
        screen.fill((90, 80, 100), (x - 6, y - 6, 12, 12))
        for dx, dy in ((-9, 0), (6, 0), (0, -9), (0, 6)):
            screen.fill((90, 80, 100), (x + dx, y + dy, 3, 3))
        screen.fill(color, (x - 3, y - 3, 6, 6))
        pixelfx.dibujar_halo(screen, color, x, y, 10)


class MegaBoss:
    """Ver docstring del modulo. take_damage() lanza la transformacion al
    cruzar MEGA_BOSS_PHASE2_HP_RATIO; update(ship) va una vez por cuadro."""

    ESCALA = sprites.MEGA_ESCALA

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH // 2
        self.y = -120.0
        self.target_x = self.x
        self.target_y = 130
        self.active = True
        self._dificultad = dificultad
        self.max_hp = max(1, int(MEGA_BOSS_MAX_HP * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.health_deplete_anim = 1.0
        self.health_shake = 0
        self.name = "COLOSO ESTELAR"
        self.rewarded = False
        self.damaged_timer = 0
        self.particles = []
        self.t = 0

        self.phase = 1
        self.phase_name = "cruiser"
        # main.py usa width // 2 como radio de impacto
        self.width = 240
        self.phase_transition = False
        self.speed = 1.1 * dificultad

        self.enter_timer = 110
        self.enter_done = False
        self.move_timer = 0

        self.accion = None
        self.ultimo = None
        self.timer_accion = 70
        self.cola = []               # disparos programados: [cuadro, funcion]
        self.cazas = None            # aviso del hangar antes de largar cazas
        self.timer_cazas = 360
        self.minas = []

        self.frag_pieces = []
        self.frag_stage = None
        self.frag_timer = 0
        self.reform_flash = 0
        self.grieta = []

        self._ship_x, self._ship_y = GAME_WIDTH / 2, GAME_HEIGHT - 80
        self._ship = None

    # ------------------------------------------------------------- estado

    def take_damage(self, amount=1):
        if self.enter_timer > 0 or self.frag_stage is not None:
            return
        prev = self.hp
        self.hp = max(0, self.hp - amount)
        if prev > self.hp:
            self.health_deplete_anim = max(self.health_deplete_anim, prev / self.max_hp)
        self.damaged_timer = 8
        self.health_shake = 6
        if self.hp <= 0:
            self.active = False
        elif self.phase == 1 and self.hp <= self.max_hp * MEGA_BOSS_PHASE2_HP_RATIO:
            self._iniciar_fase_2()

    def _iniciar_fase_2(self):
        self.phase = 2
        self.phase_transition = True
        self.accion = None
        self.cola = []
        self.cazas = None
        self._iniciar_fragmentacion()

    def _ritmo(self):
        return {1: 1.0, 2: 0.85}[self.phase] / self._dificultad

    # -------------------------------------------------------------- update

    def update(self, ship=None):
        resultado = {"bullets": [], "asteroides": [], "alien_ships": []}
        self.t += 1
        if ship is not None:
            self._ship = ship
            self._ship_x, self._ship_y = ship.x, ship.y
        self.damaged_timer = max(0, self.damaged_timer - 1)
        self.reform_flash = max(0, self.reform_flash - 1)
        if self.health_deplete_anim > self.hp / self.max_hp:
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.01)
        self._avanzar_particulas()

        if self.enter_timer > 0:
            self.enter_timer -= 1
            self.y += (self.target_y - self.y) * 0.035
            if self.enter_timer <= 0:
                self.enter_done = True
            return resultado

        if self.frag_stage is not None:
            self._actualizar_fragmentos()
            return resultado

        resultado["bullets"] += self._soltar_cola()
        resultado["bullets"] += self._actualizar_minas()
        if self.accion is None:
            self._mover()
            self.timer_accion -= 1
            if self.timer_accion <= 0 and not self.cola:
                self._elegir_accion()
        else:
            self._actualizar_accion(resultado)
        resultado["alien_ships"] += self._actualizar_cazas()
        return resultado

    def _mover(self, vel=None):
        dx, dy = self.target_x - self.x, self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 6:
            self.move_timer += 1
            if self.move_timer > 50:
                self.move_timer = 0
                margen = 170 if self.phase == 1 else 130
                self.target_x = random.randint(margen, GAME_WIDTH - margen)
                self.target_y = random.randint(110, 160)
        else:
            paso = min(dist, vel or self.speed)
            self.x += dx / dist * paso
            self.y += dy / dist * paso

    def _soltar_cola(self):
        balas = []
        quedan = []
        for item in self.cola:
            item[0] -= 1
            if item[0] <= 0:
                balas += item[1]()
            else:
                quedan.append(item)
        self.cola = quedan
        return balas

    # ------------------------------------------------------------ acciones

    def _elegir_accion(self):
        if self.phase == 1:
            opciones = ["andanada", "misiles", "riel"]
        else:
            opciones = ["superlaser", "torretas", "minas", "meteoros"]
        if self.ultimo in opciones:
            opciones.remove(self.ultimo)
        tipo = self.ultimo = random.choice(opciones)
        dur = {"andanada": 40, "misiles": 34, "riel": 56, "superlaser": 80,
               "torretas": 34, "minas": 30, "meteoros": 50}[tipo]
        a = {"tipo": tipo, "fase": "aviso", "t": 0, "dur": dur}
        if tipo == "andanada":
            a["orden"] = list(range(8)) if random.random() < 0.5 else list(range(7, -1, -1))
        elif tipo == "riel":
            a["mira"] = [self._ship_x, self._ship_y]
        elif tipo == "superlaser":
            a["disparos"] = 2 if self.hp < self.max_hp * 0.25 else 1
        elif tipo == "meteoros":
            xs = [self._ship_x] + [random.randint(40, GAME_WIDTH - 40) for _ in range(4)]
            a["columnas"] = [(max(40, min(GAME_WIDTH - 40, x)), random.randint(22, 34)) for x in xs]
        elif tipo == "minas":
            a["destinos"] = [(random.randint(80, GAME_WIDTH - 80), random.randint(260, GAME_HEIGHT - 120))
                             for _ in range(3 if self.hp > self.max_hp * 0.25 else 4)]
        self.accion = a

    def _actualizar_accion(self, resultado):
        a = self.accion
        a["t"] += 1
        tipo = a["tipo"]
        if tipo == "superlaser":
            self._actualizar_superlaser(a, resultado)
            return
        if tipo == "riel":
            if a["t"] < a["dur"] - 16:
                a["mira"][0] += (self._ship_x - a["mira"][0]) * 0.1
                a["mira"][1] += (self._ship_y - a["mira"][1]) * 0.1
            if a["t"] >= a["dur"]:
                ox, oy = self.x + CANON[0], self.y + CANON[1]
                ang = math.atan2(a["mira"][1] - oy, a["mira"][0] - ox)
                resultado["bullets"].append(WaveBossBullet(ox, oy, math.cos(ang) * 12, math.sin(ang) * 12,
                                                           (255, 120, 110), 9))
                self._chispas(ox, oy, ROJO_AVISO, 10)
                self._fin_accion()
            return
        if tipo in ("andanada", "misiles", "meteoros"):
            # se sigue moviendo despacio mientras avisa
            self._mover(self.speed * 0.5)
        if a["t"] < a["dur"]:
            return
        if tipo == "andanada":
            # la ola va y vuelve
            for k, i in enumerate(a["orden"] + a["orden"][::-1][1:]):
                self.cola.append([1 + k * 5, lambda i=i: self._tronera(i)])
        elif tipo == "misiles":
            for k in range(4):
                lado = -1 if k % 2 == 0 else 1
                self.cola.append([1 + k * 9, lambda lado=lado: self._misil(lado)])
        elif tipo == "torretas":
            for k in range(14):
                self.cola.append([1 + k * 5, lambda k=k: self._espiral(k)])
        elif tipo == "minas":
            for k, destino in enumerate(a["destinos"]):
                self.cola.append([1 + k * 8, lambda destino=destino: self._mina(destino)])
        elif tipo == "meteoros":
            for x, tam in a["columnas"]:
                meteoro = Asteroid(x, -tam - 10, tam)
                meteoro.speed = random.uniform(4.0, 5.5)
                resultado["asteroides"].append(meteoro)
        self._fin_accion()

    def _fin_accion(self):
        self.accion = None
        self.timer_accion = int(random.randint(45, 75) * self._ritmo())

    def _tronera(self, i):
        x, y = self.x + TRONERAS[i][0], self.y + TRONERAS[i][1]
        self._chispas(x, y, AMBAR, 3)
        return [WaveBossBullet(x, y + 4, vx, 4.4, AMBAR, 5) for vx in (-1.1, 0.0, 1.1)]

    def _misil(self, lado):
        x, y = self.x + SILOS[0 if lado < 0 else 1][0], self.y + SILOS[0][1]
        self._chispas(x, y, AMBAR, 5)
        return [ColosoMisil(x, y, lado, self._ship)]

    def _espiral(self, k):
        balas = []
        giro = k * 0.21
        for i, (tx, ty) in enumerate(TORRETAS):
            base = math.atan2(ty, tx)
            for extra in (0.0, math.pi / 2):
                ang = base + giro * (1 if i % 2 == 0 else -1) + extra
                balas.append(WaveBossBullet(self.x + tx, self.y + ty, math.cos(ang) * 3.3, math.sin(ang) * 3.3,
                                            NEON_2, 5))
        return balas

    def _mina(self, destino):
        mina = ColosoMina(self, destino)
        self.minas.append(mina)
        return [mina]

    def _actualizar_minas(self):
        balas = []
        vivas = []
        for m in self.minas:
            if not m.active:
                continue
            if m.armada >= ColosoMina.ARMADO:
                m.active = False
                self._chispas(m.x, m.y, NEON_2, 10)
                for i in range(8):
                    ang = i * math.pi / 4 + math.pi / 8
                    balas.append(WaveBossBullet(m.x, m.y, math.cos(ang) * 3.6, math.sin(ang) * 3.6, NEON_2, 5))
            else:
                vivas.append(m)
        self.minas = vivas
        return balas

    def _actualizar_superlaser(self, a, resultado):
        if a["fase"] == "aviso":
            # se acomoda encima de la nave y se frena al final del aviso
            if a["t"] < a["dur"] - 22:
                dx = self._ship_x - self.x
                self.x += max(-3.2, min(3.2, dx * 0.08))
                self.x = max(110, min(GAME_WIDTH - 110, self.x))
            if a["t"] >= a["dur"]:
                a["fase"], a["t"] = "fuego", 0
                resultado["bullets"].append(ColosoLaser(self, self._ship))
            return
        if a["fase"] == "fuego":
            if a["t"] >= 46:
                a["disparos"] -= 1
                if a["disparos"] > 0:
                    a["fase"], a["t"], a["dur"] = "aviso", 0, 56
                else:
                    self.target_x, self.target_y = self.x, self.y
                    self._fin_accion()

    def _actualizar_cazas(self):
        if self.cazas is None:
            self.timer_cazas -= 1
            if self.timer_cazas <= 0 and self.accion is None:
                self.cazas = 40
            return []
        self.cazas -= 1
        if self.cazas > 0:
            return []
        self.cazas = None
        self.timer_cazas = int(random.randint(420, 540) * self._ritmo())
        bocas = HANGARES if self.phase == 1 else COMPUERTAS
        naves = []
        for bx, by in bocas:
            nave = AlienShip("left" if bx < 0 else "right", variant="fighter")
            nave.color = CAZA_ESCOLTA_COLOR
            nave.wing_color = tuple(int(c * 0.62) for c in CAZA_ESCOLTA_COLOR)
            nave.speed *= 1.25
            nave.x, nave.y = self.x + bx, self.y + by
            naves.append(nave)
            self._chispas(self.x + bx, self.y + by, WHITE, 6)
        return naves

    # ------------------------------------------------ transformacion (fase 2)

    def _iniciar_fragmentacion(self):
        """El crucero se parte en pedazos de su propio sprite que salen
        volando y despues implosionan; recien ahi aparece la esfera."""
        sprite = sprites.get_mega_boss_surface("cruiser")
        self.frag_pieces = []
        if sprite is not None:
            w, h = sprite.get_size()
            cols, filas = 8, 4
            pw, ph = w // cols, h // filas
            for fila in range(filas):
                for col in range(cols):
                    rect = pygame.Rect(col * pw, fila * ph, pw if col < cols - 1 else w - col * pw,
                                       ph if fila < filas - 1 else h - fila * ph)
                    pieza = sprite.subsurface(rect).copy()
                    if pygame.mask.from_surface(pieza).count() < 20:
                        continue
                    bx, by = rect.centerx - w / 2, rect.centery - h / 2
                    dist = math.hypot(bx, by) or 1.0
                    self.frag_pieces.append({'surf': pieza, 'bx': bx, 'by': by,
                                             'dx': bx / dist, 'dy': by / dist,
                                             'lejos': random.uniform(70, 130), 'off': 0.0})
        self.frag_stage = "explota"
        self.frag_timer = 0
        self._chispas(self.x, self.y, AMBAR, 40, vel=6)

    def _actualizar_fragmentos(self):
        self.frag_timer += 1
        if self.frag_stage == "explota":
            t = min(1.0, self.frag_timer / 40)
            for p in self.frag_pieces:
                p['off'] = p['lejos'] * (1 - (1 - t) ** 2)
            if self.frag_timer % 6 == 0 and self.frag_pieces:
                p = random.choice(self.frag_pieces)
                self._chispas(self.x + p['bx'] + p['dx'] * p['off'], self.y + p['by'] + p['dy'] * p['off'], AMBAR, 6)
            if self.frag_timer >= 56:
                self.frag_stage, self.frag_timer = "implota", 0
            return
        t = min(1.0, self.frag_timer / 44)
        for p in self.frag_pieces:
            p['off'] = p['lejos'] * (1 - t * t)
        if self.frag_timer % 3 == 0:
            a = random.uniform(0, 2 * math.pi)
            self.particles.append({'x': self.x + math.cos(a) * 140, 'y': self.y + math.sin(a) * 140,
                                   'vx': -math.cos(a) * 5, 'vy': -math.sin(a) * 5,
                                   'life': 26, 'max_life': 26, 'color': NEON_2})
        if self.frag_timer >= 44:
            self.frag_pieces = []
            self.frag_stage = None
            self.phase_name = "sphere"
            self.phase_transition = False
            self.width = 210
            self.reform_flash = 18
            self.timer_accion = 60
            self.timer_cazas = 300
            self._chispas(self.x, self.y, NEON_2, 30, vel=7)
            self._generar_grieta()

    def _generar_grieta(self):
        """Camino de la grieta de arcoiris sobre la esfera (en pixeles de la
        grilla x3, relativo al centro)."""
        x, y = -30, -78
        self.grieta = []
        while y < 70:
            self.grieta.append((x, y))
            y += 3
            x += random.choice((-3, 0, 0, 3, 3))
            x = max(-60, min(40, x))

    # ------------------------------------------------------------ efectos

    def _chispas(self, x, y, color, n, vel=4):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(1, vel)
            self.particles.append({'x': x, 'y': y, 'vx': math.cos(a) * v, 'vy': math.sin(a) * v,
                                   'life': random.randint(12, 26), 'max_life': 26, 'color': color})

    def _avanzar_particulas(self):
        if self.damaged_timer > 4 and random.random() < 0.5:
            w = 220 if self.phase == 1 else 140
            self._chispas(self.x + random.uniform(-w / 2, w / 2), self.y + random.uniform(-30, 30), AMBAR, 2)
        vivas = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vx'] *= 0.94
            p['vy'] *= 0.94
            p['life'] -= 1
            if p['life'] > 0:
                vivas.append(p)
        self.particles = vivas[-260:]

    # ---------------------------------------------------------------- draw

    def _sprite(self):
        return sprites.get_mega_boss_surface(self.phase_name)

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        ox, oy = offset_x, offset_y
        sprite = self._sprite()

        if self.frag_stage is not None:
            for p in self.frag_pieces:
                x = cx + p['bx'] + p['dx'] * p['off']
                y = cy + p['by'] + p['dy'] * p['off']
                screen.blit(p['surf'], p['surf'].get_rect(center=(int(x), int(y))))
        elif sprite is not None:
            self._dibujar_motores(screen, cx, cy)
            self._dibujar_avisos(screen, cx, cy, ox, oy)
            rect = sprite.get_rect(center=(cx, cy))
            screen.blit(sprite, rect)
            if self.phase == 1:
                self._dibujar_crucero(screen, cx, cy)
            else:
                self._dibujar_esfera(screen, cx, cy)
            if self.damaged_timer > 3:
                blanco = pixelfx.silueta_blanca(sprite)
                blanco.set_alpha(150)
                screen.blit(blanco, rect)
            if self.reform_flash > 0:
                blanco = pixelfx.silueta_blanca(sprite)
                blanco.set_alpha(int(255 * self.reform_flash / 18))
                screen.blit(blanco, rect)

        for p in self.particles:
            k = p['life'] / p['max_life']
            lado = 4 if k > 0.5 else 2
            screen.fill(pixelfx.aclarar(p['color'], 0.5 * k), (int(p['x']) + ox, int(p['y']) + oy, lado, lado))

        if self.enter_timer <= 0 and sprite is not None:
            self._dibujar_barra(screen, cx, cy - sprite.get_height() // 2 - 16)

    def _dibujar_motores(self, screen, cx, cy):
        """Toberas del crucero (arriba, porque la proa mira a la nave) o el
        brillo de la esfera."""
        if self.phase == 2:
            return
        largo = 8 + (self.t // 3) % 3 * 3 + (12 if self.enter_timer > 0 else 0)
        for tx in TOBERAS:
            x, y = cx + tx, cy + TOBERAS_Y
            pixelfx.dibujar_halo(screen, NEON_1, x, y - largo // 2, 10)
            for k in range(0, largo, 3):
                f = k / largo
                lado = 6 if f < 0.4 else 4 if f < 0.75 else 2
                color = pixelfx.aclarar(NEON_1, 0.6) if f < 0.3 else tuple(int(c * (1 - f * 0.6)) for c in NEON_1)
                screen.fill(color, (x - lado // 2, y - k - 3, lado, 3))

    def _dibujar_crucero(self, screen, cx, cy):
        a = self.accion
        # troneras: se prenden en el orden en que van a disparar
        prendidas = set()
        if a is not None and a["tipo"] == "andanada":
            n = int(len(a["orden"]) * min(1.0, a["t"] / (a["dur"] * 0.8))) + 1
            prendidas = set(a["orden"][:n])
        for i, (tx, ty) in enumerate(TRONERAS):
            x, y = cx + tx, cy + ty
            if i in prendidas:
                color = AMBAR if (self.t // 3) % 2 else WHITE
                pixelfx.dibujar_halo(screen, AMBAR, x, y, 12)
                screen.fill(color, (x - 3, y - 3, 6, 6))
        # silos de misiles
        if a is not None and a["tipo"] == "misiles" and (self.t // 4) % 2:
            for sx, sy in SILOS:
                pixelfx.dibujar_halo(screen, ROJO_AVISO, cx + sx, cy + sy, 14)
                screen.fill(ROJO_AVISO, (cx + sx - 5, cy + sy - 5, 10, 10))
        # bahias del hangar antes de largar cazas
        if self.cazas is not None:
            for hx, hy in HANGARES:
                prog = 1 - self.cazas / 40
                pixelfx.dibujar_halo(screen, WHITE, cx + hx, cy + hy, 8 + 14 * prog)
                if (self.t // 3) % 2:
                    screen.fill(WHITE, (cx + hx - 5, cy + hy - 8, 10, 16))
        # luces de punta de ala
        if (self.t // 20) % 2:
            for s, color in ((-1, (90, 255, 170)), (1, ROJO_AVISO)):
                pixelfx.dibujar_halo(screen, color, cx + s * 141, cy + 33, 10)

    def _dibujar_esfera(self, screen, cx, cy):
        # luces de la trinchera que corren
        for k in range(8):
            if (k + self.t // 4) % 4:
                continue
            for s in (-1, 1):
                x = cx + s * (93 - k * 12)
                pixelfx.dibujar_halo(screen, NEON_2, x, cy, 8)
                screen.fill(WHITE, (x - 2, cy - 2, 4, 4))
        # compuertas de cazas
        if self.cazas is not None:
            prog = 1 - self.cazas / 40
            for hx, hy in COMPUERTAS:
                pixelfx.dibujar_halo(screen, WHITE, cx + hx, cy + hy, 8 + 14 * prog)
        # grieta de arcoiris, crece con el daño
        herida = 1 - self.hp / (self.max_hp * MEGA_BOSS_PHASE2_HP_RATIO)
        n = int(len(self.grieta) * max(0.0, min(1.0, herida + 0.08)))
        for gx, gy in self.grieta[:n]:
            screen.fill(pixelfx.CONTORNO, (cx + gx - 2, cy + gy - 1, 9, 5))
        for i, (gx, gy) in enumerate(self.grieta[:n]):
            color = ARCOIRIS[(i + self.t // 3) % len(ARCOIRIS)]
            screen.fill(color, (cx + gx, cy + gy, 5, 3))
        if n:
            gx, gy = self.grieta[n - 1]
            pixelfx.dibujar_halo(screen, ARCOIRIS[(self.t // 3) % len(ARCOIRIS)], cx + gx, cy + gy, 10)

    def _dibujar_avisos(self, screen, cx, cy, ox, oy):
        a = self.accion
        if a is None:
            return
        tipo = a["tipo"]
        prog = a["t"] / a["dur"] if a["fase"] == "aviso" else 1.0
        if tipo == "riel":
            fijo = a["t"] >= a["dur"] - 16
            color = ROJO_AVISO if fijo else AMBAR
            x0, y0 = cx + CANON[0], cy + CANON[1]
            mx, my = a["mira"][0] + ox, a["mira"][1] + oy
            largo = math.hypot(mx - x0, my - y0)
            n = int(largo / 8)
            for k in range(n):
                if (k + self.t // 2) % 3 == 0:
                    continue
                f = k / max(1, n)
                screen.fill(color, (int(x0 + (mx - x0) * f) - 2, int(y0 + (my - y0) * f) - 2, 4, 4))
            r = int(22 - 12 * prog)
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                screen.fill(color, (int(mx + dx * r) - 3, int(my + dy * r) - 1, 6, 3))
                screen.fill(color, (int(mx + dx * r) - 1, int(my + dy * r) - 3, 3, 6))
            pixelfx.carga(screen, color, x0, y0, prog, self.t, 12)
        elif tipo == "superlaser" and a["fase"] == "aviso":
            pixelfx.columna_aviso(screen, cx, 64, ROJO_AVISO if prog > 0.7 else NEON_2, self.t,
                                  cy + PARABOLA[1] + 20)
            pixelfx.carga(screen, NEON_2, cx + PARABOLA[0], cy + PARABOLA[1], prog, self.t, 20)
        elif tipo == "torretas":
            for tx, ty in TORRETAS:
                pixelfx.carga(screen, NEON_2, cx + tx, cy + ty, prog, self.t, 12)
        elif tipo == "minas":
            pixelfx.carga(screen, NEON_2, cx, cy, prog, self.t, 16)
            for x, y in a["destinos"]:
                if (self.t // 4) % 2:
                    screen.fill(ROJO_AVISO, (int(x) + ox - 6, int(y) + oy - 1, 12, 3))
                    screen.fill(ROJO_AVISO, (int(x) + ox - 1, int(y) + oy - 6, 3, 12))
        elif tipo == "meteoros":
            for x, tam in a["columnas"]:
                pixelfx.columna_aviso(screen, x + ox, tam * 2, AMBAR, self.t, 0, GAME_HEIGHT * prog)

    def _dibujar_barra(self, screen, cx, y):
        temblor = (0, 0)
        if self.health_shake > 0:
            self.health_shake -= 1
            temblor = (random.randint(-2, 2), random.randint(-2, 2))
        color = NEON_1 if self.phase_name == "cruiser" else NEON_2
        pixelfx.barra_jefe(screen, cx, y, 200, max(0.0, self.hp / self.max_hp), self.health_deplete_anim,
                           color, temblor)
        crucero = self.phase_name == "cruiser"
        fase = "CRUCERO DE ASALTO" if crucero else "ESFERA DE COMBATE"
        etiqueta = render_text(f"{self.name} · {fase}", 11, WHITE if crucero else ROSA)
        screen.blit(etiqueta, (cx - etiqueta.get_width() // 2, y - 18))
