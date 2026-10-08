"""
Dragon Espacial (oleada 20): un dragon en pixel art neon que baja de
frente hacia la nave, con las alas abiertas y fuego en las fauces (arte en
tools/generate_pixel_sprites.py, cuadros "dragon_a"/"dragon_b" del aleteo).

Pelea en tres modos que cambian al 66% y 33% de vida; cada cambio lo deja
mas lastimado (grietas al rojo vivo en el cuerpo) y de otro color:

  Acecho (fase 1): rafagas de dardos de fuego apuntados y zarpazos que
  salen de las garras en arco.
  Envite (fase 2): suma un cono de fuego con un hueco para pasar y el
  vendaval, plumas que caen en diagonal desde las puntas de las alas.
  Furia (fase 3): suma el aliento de fuego (una linea marca hacia donde va
  a escupir y se queda fija un momento antes del chorro) y un anillo de
  fuego giratorio.

Desde la fase 2 cada tanto hace una PICADA: sale por arriba, marca una
columna sobre la nave y baja en picada atravesando la pantalla.

Todo ataque se carga antes de salir (chispas que se juntan en la boca, las
garras o las alas), asi que siempre hay un momento para moverse. Al morir
tiembla rugiendo y estalla en pedazos de su propio sprite; mientras dura
esa secuencia sigue con active=True para que main.py no lo recompense
antes de tiempo."""

import math
import random


from modules.constants import AMARILLO, GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.core.boss_system import WaveBossBullet
from modules.systems import pixelfx, sprites
from modules.systems.fonts import render_text

# (cuerpo, alas) por fase
COLORES_FASE = {
    1: ((150, 90, 230), (110, 50, 170)),
    2: ((240, 140, 60), (170, 70, 40)),
    3: ((205, 55, 70), (120, 30, 60)),
}
NOMBRE_MODO = {1: "ACECHO", 2: "ENVITE", 3: "FURIA"}

FUEGO_ROJO = (255, 70, 50)
FUEGO_NARANJA = (255, 150, 50)
FUEGO_AMARILLO = (255, 220, 90)

# Grietas por fase, en celdas de la grilla del arte (sin PAD): se dibujan
# encima del sprite como lineas al rojo vivo que titilan.
_GRIETAS = {
    2: [[(30, 24), (32, 27), (31, 30), (33, 33)], [(41, 22), (39, 26), (41, 29)]],
    3: [[(30, 24), (32, 27), (31, 30), (33, 33)], [(41, 22), (39, 26), (41, 29)],
        [(16, 18), (20, 21), (19, 25)], [(55, 19), (52, 22), (53, 26)],
        [(34, 42), (36, 45), (35, 47)], [(37, 34), (39, 37), (38, 40)]],
}


class Embestida:
    """El cuerpo del dragon durante la picada: una "bala" grande que sigue
    al dragon, para que main.py lo choque con la nave sin cambios."""

    def __init__(self, jefe):
        self.jefe = jefe
        self.radius = 38
        self.active = True
        self.x, self.y = jefe.x, jefe.y

    def update(self):
        e = self.jefe.especial
        if e is None or e.get("fase") != "picada" or not self.jefe.active:
            self.active = False
            return
        self.x, self.y = self.jefe.x, self.jefe.y + 20

    def draw(self, screen, offset_x=0, offset_y=0):
        pass


class DragonBoss:
    ESCALA = 3
    # puntos del arte en px de pantalla respecto del centro
    BOCA = (0, 72)
    GARRAS = ((-44, 46), (43, 46))
    PUNTAS_ALA = ((-104, -60), (104, -60))
    OJOS = ((-17, 55), (16, 55))

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH / 2
        self.y = -120.0
        self.target_x = self.x
        self.target_y = 120.0
        self.active = True
        self._dificultad = dificultad
        self.max_hp = max(1, int(420 * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.size = 70
        self.name = "DRAGON ESPACIAL"
        self.phase = 1
        self.rewarded = False
        self.t = 0
        self.enter_timer = 90
        self.move_timer = 0
        self.damaged_timer = 0
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.phase_transition = False
        self.phase_timer = 0
        self.particles = []
        self.cola = []              # balas de una rafaga: (demora, bala)
        self.accion = None
        self.carga = 0
        self.carga_total = 1
        self.shoot_timer = 50
        self.ultimo = None
        self.especial = None
        self.timer_picada = 420
        self._ship = None

    # ------------------------------------------------------------ estado

    @property
    def speed(self):
        return (1.6 - 0.2 * (self.phase - 1)) * self._dificultad

    def take_damage(self, amount=1):
        if self.enter_timer > 0:
            return
        prev = self.hp
        self.hp = max(0, self.hp - amount)
        if prev > self.hp:
            self.health_deplete_anim = max(self.health_deplete_anim, prev / self.max_hp)
        self.damaged_timer = 6
        self.health_shake = 4
        if self.hp <= 0:
            # sin rugido ni explosion aca: cae en su cinematica (cine_jefes)
            self.active = False
            return
        ratio = self.hp / self.max_hp
        if (ratio < 0.66 and self.phase == 1) or (ratio < 0.33 and self.phase == 2):
            self.phase += 1
            self.phase_transition = True
            self.phase_timer = 80
            self.accion = None
            self.cola = []
            if self.especial is not None and self.especial["fase"] in ("sube", "marca"):
                # estaba fuera de pantalla: vuelve y recien ahi se transforma
                self.especial = {"tipo": "picada", "fase": "vuelve", "t": 0}
                self.y = min(self.y, -160)
            self._chispas(self.x, self.y, 30, 4.0)

    def update(self, ship=None):
        self.t += 1
        self._ship = ship
        self.damaged_timer = max(0, self.damaged_timer - 1)
        if self.health_deplete_anim > self.hp / self.max_hp:
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.01)
        self._avanzar_particulas()

        if self.enter_timer > 0:
            self.enter_timer -= 1
            self.y += (self.target_y - self.y) * 0.05
            return []

        if self.phase_transition and self.especial is None:
            self.phase_timer -= 1
            if self.phase_timer % 8 == 0:
                self._chispas(self.x, self.y, 6, 3.0)
            if self.phase_timer <= 0:
                self.phase_transition = False
                self.shoot_timer = 30
            return []

        balas = self._soltar_cola()

        if self.especial is not None:
            return balas + self._actualizar_especial(ship)

        self._mover()

        if self.phase >= 2 and self.accion is None and not self.cola:
            self.timer_picada -= 1
            if self.timer_picada <= 0:
                self.especial = {"tipo": "picada", "fase": "sube", "t": 0}
                self.timer_picada = random.randint(480, 600)
                return balas

        if self.accion is not None:
            self.carga -= 1
            if self.accion == "aliento":
                self._apuntar_aliento()
            if self.carga <= 0:
                accion, self.accion = self.accion, None
                self.shoot_timer = max(30, int(70 / self._dificultad) - 10 * self.phase)
                balas += self._atacar(accion, ship)
            return balas

        if not self.cola:
            self.shoot_timer -= 1
            if self.shoot_timer <= 0:
                self._elegir_ataque(ship)
        return balas

    def _mover(self):
        dx, dy = self.target_x - self.x, self.target_y - self.y
        dist = math.hypot(dx, dy)
        lento = 0.3 if self.accion is not None else 1.0
        if dist < 6:
            self.move_timer += 1
            if self.move_timer > 50:
                self.move_timer = 0
                self.target_x = random.randint(160, GAME_WIDTH - 160)
                self.target_y = random.randint(100, 180)
        else:
            paso = min(dist, self.speed * lento)
            self.x += dx / dist * paso
            self.y += dy / dist * paso
        self.y += math.sin(self.t * 0.06) * 0.4

    # ------------------------------------------------------------ ataques

    def _elegir_ataque(self, ship):
        opciones = {1: ["dardos", "garras"],
                    2: ["dardos", "garras", "cono", "vendaval"],
                    3: ["cono", "vendaval", "aliento", "anillo", "garras"]}[self.phase]
        if self.ultimo in opciones and len(opciones) > 1:
            opciones.remove(self.ultimo)
        self.accion = self.ultimo = random.choice(opciones)
        self.carga = self.carga_total = {"aliento": 70, "cono": 34, "vendaval": 34}.get(self.accion, 28)
        if self.accion == "aliento":
            self.angulo_aliento = self._angulo_a_nave(*self.BOCA)

    def _angulo_a_nave(self, ox, oy):
        s = self._ship
        if s is None:
            return math.pi / 2
        return math.atan2(s.y - (self.y + oy), s.x - (self.x + ox))

    def _apuntar_aliento(self):
        # sigue a la nave mientras carga y se queda fijo los ultimos cuadros
        if self.carga > 16:
            objetivo = self._angulo_a_nave(*self.BOCA)
            diff = (objetivo - self.angulo_aliento + math.pi) % (2 * math.pi) - math.pi
            self.angulo_aliento += diff * 0.07

    def _bala(self, x, y, ang, vel, color, radio=4):
        return WaveBossBullet(x, y, math.cos(ang) * vel, math.sin(ang) * vel, color, radio)

    def _soltar_cola(self):
        salen = []
        quedan = []
        for demora, fabrica in self.cola:
            if demora <= 0:
                salen.append(fabrica())
            else:
                quedan.append((demora - 1, fabrica))
        self.cola = quedan
        return salen

    def _atacar(self, accion, ship):
        bx, by = self.x + self.BOCA[0], self.y + self.BOCA[1]
        balas = []
        if accion == "dardos":
            # rafaga de 3 (5 en fase 2+) dardos que apuntan a la nave al salir
            for k in range(3 if self.phase == 1 else 5):
                self.cola.append((k * 7, lambda: self._bala(
                    self.x + self.BOCA[0], self.y + self.BOCA[1],
                    self._angulo_a_nave(*self.BOCA), 5.2, FUEGO_NARANJA, 3)))
        elif accion == "garras":
            for (gx, gy), lado in zip(self.GARRAS, (-1, 1)):
                for k in range(5):
                    a = math.radians(90 + lado * (20 + k * 14))
                    balas.append(self._bala(self.x + gx, self.y + gy, a, 2.6 + k * 0.25, FUEGO_AMARILLO, 3))
        elif accion == "cono":
            # abanico con un hueco de dos balas por donde pasar
            n = 11
            hueco = random.randint(2, n - 4)
            for i in range(n):
                if hueco <= i <= hueco + 1:
                    continue
                a = math.radians(90 + (i - (n - 1) / 2) * 9)
                balas.append(self._bala(bx, by, a, 3.6, FUEGO_NARANJA, 4))
        elif accion == "vendaval":
            for (px, py), lado in zip(self.PUNTAS_ALA, (-1, 1)):
                for k in range(6):
                    self.cola.append((k * 6, lambda px=px, py=py, lado=lado: WaveBossBullet(
                        self.x + px, self.y + py, -lado * 1.6, 3.0, self._color_alas(), 3)))
        elif accion == "aliento":
            for k in range(26):
                self.cola.append((k * 2, lambda k=k: self._bala(
                    self.x + self.BOCA[0], self.y + self.BOCA[1],
                    self.angulo_aliento + math.sin(k * 0.9) * 0.06, 8.0,
                    FUEGO_AMARILLO if k % 3 == 0 else FUEGO_ROJO, 5)))
        elif accion == "anillo":
            n = 16
            base = self.t * 0.05
            balas = [self._bala(self.x, self.y + 20, base + 2 * math.pi * i / n, 3.0, FUEGO_ROJO, 4)
                     for i in range(n)]
        return balas

    def _actualizar_especial(self, ship):
        e = self.especial
        e["t"] += 1
        if e["fase"] == "sube":
            self.y -= 7
            if self.y < -160:
                e["fase"], e["t"] = "marca", 0
                e["x"] = ship.x if ship is not None else GAME_WIDTH / 2
                self.x = e["x"]
            return []
        if e["fase"] == "marca":
            if e["t"] < 40 and ship is not None:
                # sigue a la nave un rato y despues se queda fija
                e["x"] += max(-3.0, min(3.0, (ship.x - e["x"]) * 0.1))
                self.x = e["x"]
            if e["t"] >= 64:
                e["fase"], e["t"] = "picada", 0
                return [Embestida(self)]
            return []
        if e["fase"] == "picada":
            self.y += 13
            if e["t"] % 5 == 0:
                self._chispas(self.x, self.y - 60, 3, 1.5)
            if self.y > GAME_HEIGHT + 200:
                e["fase"] = "vuelve"
                self.y = -200
            return []
        # vuelve a su lugar desde arriba
        self.y += (120 - self.y) * 0.07
        if abs(self.y - 120) < 4:
            self.especial = None
            self.shoot_timer = 40
        return []

    # ------------------------------------------------------------ efectos

    def _chispas(self, x, y, n, vel):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.5, vel)
            self.particles.append({'x': x + random.uniform(-50, 50), 'y': y + random.uniform(-40, 40),
                                   'vx': math.cos(a) * v, 'vy': math.sin(a) * v - 0.5,
                                   'life': random.randint(16, 34), 'max_life': 34})

    def _avanzar_particulas(self):
        if self.damaged_timer > 0 and random.random() < 0.5:
            self._chispas(self.x, self.y, 1, 2.0)
        if self.phase == 3 and random.random() < 0.3:
            # brasas que se escapan de las grietas
            gx, gy = random.choice(random.choice(_GRIETAS[3]))
            x, y = self._celda(gx, gy)
            self.particles.append({'x': x, 'y': y, 'vx': random.uniform(-0.5, 0.5), 'vy': random.uniform(-1.6, -0.4),
                                   'life': 20, 'max_life': 20})
        vivas = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] > 0:
                vivas.append(p)
        self.particles = vivas

    # ------------------------------------------------------------ dibujo

    def _color_alas(self):
        return COLORES_FASE[self.phase][1]

    def _sprite(self, cuadro):
        cuerpo, alas = COLORES_FASE[self.phase]
        kind = ("dragon_a", "dragon_b")[cuadro]
        w, h = sprites.tamano_pixel("boss", kind, self.ESCALA)
        return sprites.get_boss_surface(cuerpo, alas, w, h, kind=kind)

    def _celda(self, gx, gy):
        """Centro en pantalla de una celda de la grilla del arte."""
        w, h = sprites.tamano_pixel("boss", "dragon_a", self.ESCALA)
        return (self.x + (gx + 3.5) * self.ESCALA - w / 2, self.y + (gy + 3.5) * self.ESCALA - h / 2)

    def _dibujar_grietas(self, screen, ox, oy):
        grietas = _GRIETAS.get(self.phase, [])
        brillo = FUEGO_AMARILLO if (self.t // 4) % 3 else FUEGO_ROJO
        for linea in grietas:
            for (x0, y0), (x1, y1) in zip(linea, linea[1:]):
                pasos = max(abs(x1 - x0), abs(y1 - y0))
                for k in range(pasos + 1):
                    gx = round(x0 + (x1 - x0) * k / max(1, pasos))
                    gy = round(y0 + (y1 - y0) * k / max(1, pasos))
                    x, y = self._celda(gx, gy)
                    screen.fill(brillo, (int(x) - 1 + ox, int(y) - 1 + oy, self.ESCALA, self.ESCALA))
            x, y = self._celda(*linea[len(linea) // 2])
            pixelfx.dibujar_halo(screen, FUEGO_NARANJA, x + ox, y + oy, 7)

    def _dibujar_aviso(self, screen, cx, cy):
        if self.accion is None:
            return
        prog = 1 - self.carga / self.carga_total
        if self.accion in ("dardos", "cono", "aliento"):
            pixelfx.carga(screen, FUEGO_NARANJA, cx + self.BOCA[0], cy + self.BOCA[1], prog, self.t, 16)
        elif self.accion == "garras":
            for gx, gy in self.GARRAS:
                pixelfx.carga(screen, FUEGO_AMARILLO, cx + gx, cy + gy, prog, self.t, 12)
        elif self.accion == "vendaval":
            for px, py in self.PUNTAS_ALA:
                pixelfx.carga(screen, pixelfx.aclarar(self._color_alas(), 0.4), cx + px, cy + py, prog, self.t, 14)
        elif self.accion == "anillo":
            pixelfx.carga(screen, FUEGO_ROJO, cx, cy + 20, prog, self.t, 24)
        if self.accion == "aliento":
            # linea punteada hacia donde va a escupir (fija = roja)
            fijo = self.carga <= 16
            color = (255, 70, 90) if fijo else FUEGO_AMARILLO
            bx, by = cx + self.BOCA[0], cy + self.BOCA[1]
            for k in range(4, 70):
                if (k + self.t // 2) % 4 < 2:
                    continue
                x = bx + math.cos(self.angulo_aliento) * k * 10
                y = by + math.sin(self.angulo_aliento) * k * 10
                if not (0 <= x < screen.get_width() and 0 <= y < screen.get_height()):
                    break
                screen.fill(color, (int(x) - 2, int(y) - 2, 4, 4))

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        e = self.especial
        if e is not None and e["fase"] == "marca":
            pixelfx.columna_aviso(screen, int(e["x"]) + offset_x, 90, (255, 70, 90), self.t)

        ritmo = 7 if self.phase == 3 else 10
        sprite = self._sprite((self.t // ritmo) % 2)
        rect = sprite.get_rect(center=(cx, cy))
        if self.enter_timer > 0:
            copia = sprite.copy()
            copia.set_alpha(int(255 * (1 - self.enter_timer / 90)))
            screen.blit(copia, rect)
        else:
            screen.blit(sprite, rect)
            self._dibujar_grietas(screen, cx - int(self.x), cy - int(self.y))
            destello = self.damaged_timer > 3 or (self.phase_transition and (self.phase_timer // 4) % 2 == 0)
            if destello:
                blanco = pixelfx.silueta_blanca(sprite)
                blanco.set_alpha(170)
                screen.blit(blanco, rect)
            # ojos encendidos
            ojo = (255, 90, 110)
            for ox, oy in self.OJOS:
                pixelfx.dibujar_halo(screen, ojo, cx + ox, cy + oy, 6)
            # brasa en la boca
            pixelfx.dibujar_halo(screen, FUEGO_NARANJA, cx + self.BOCA[0], cy + self.BOCA[1], 7 + (self.t // 5) % 3 * 2)
            self._dibujar_aviso(screen, cx, cy)

        for p in self.particles:
            k = p['life'] / p['max_life']
            c = (255, int(120 + 120 * k), int(60 * k))
            lado = 4 if k > 0.5 else 2
            screen.fill(c, (int(p['x']) + offset_x, int(p['y']) + offset_y, lado, lado))

        if self.enter_timer <= 0 and (e is None or e["fase"] == "vuelve"):
            temblor = (0, 0)
            if self.health_shake > 0:
                temblor = (random.randint(-self.health_shake, self.health_shake), 0)
                self.health_shake -= 1
            ratio = max(0.0, self.hp / self.max_hp)
            color = COLORES_FASE[self.phase][0]
            y_barra = max(14, cy - 100)
            pixelfx.barra_jefe(screen, cx, y_barra, 156, ratio, self.health_deplete_anim, color, temblor)
            etiqueta = render_text(f"{self.name}  {NOMBRE_MODO[self.phase]}", 11, WHITE if self.phase < 3 else AMARILLO)
            screen.blit(etiqueta, (cx - etiqueta.get_width() // 2, y_barra - 18))
