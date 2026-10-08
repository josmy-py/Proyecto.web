"""
La Anomalia Final (oleada FINAL_BOSS_SPAWN_WAVE): una calavera de vacio en
pixel art neon (arte "anomalia_px" en tools/generate_pixel_sprites.py) que
se "rompe" en glitches, deja clones fantasma y dispara esquirlas de
cristal (AnomalyLanza).

Hace un solo ataque grande a la vez y todos se avisan antes:

  VOLEAS (desde la boca, con carga): abanico, rafaga apuntada y anillo;
  en fase 2 suma espiral y en fase 3 lluvia desde arriba.
  HILO: una linea punteada sigue a la nave, se pone roja y se queda fija
  un momento, y por ahi sale un abanico de esquirlas.
  EMBESTIDA: tiembla mirando a la nave, marca el rumbo con chevrones y
  se lanza en linea recta pasandose de largo.
  SALTO (fase 2+): abre una grieta en otro lugar, aparece ahi y dispara.

Ademas, en paralelo:
  ESTALLIDO: marca una zona circular alrededor de la nave que despues
  estalla entera; hay que salir caminando de la zona.
  GRITO (fase 3): un anillo lento con un hueco marcado en verde.

Los clones fantasma aparecen en cada glitch y en cada cambio de fase;
disparan como la real pero no reciben daño."""

import math
import random

import pygame

from modules.constants import GAME_HEIGHT, GAME_WIDTH, MENTA, WHITE
from modules.systems import pixelfx, sprites
from modules.systems.fonts import render_text

# (craneo, placas) por fase
COLORES_FASE = {
    1: ((150, 90, 220), (90, 60, 170)),
    2: ((200, 70, 170), (120, 50, 150)),
    3: ((240, 60, 90), (150, 40, 90)),
}
CRISTAL = (200, 120, 255)
ROJO_AVISO = (255, 70, 90)
CIAN = (60, 220, 255)


class AnomalyLanza:
    """Esquirla de cristal que viaja en linea recta."""

    def __init__(self, x, y, vx=0.0, vy=5.0, color=CRISTAL):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.radius = 5
        self.active = True
        self._ang = math.atan2(vy, vx)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y > GAME_HEIGHT + 20 or self.y < -20 or self.x < -20 or self.x > GAME_WIDTH + 20:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        pixelfx.dibujar_halo(screen, self.color, cx, cy, 14)
        s = pixelfx.esquirla(self.color, self._ang)
        screen.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2))


class AnomalyEmbestidaImpacto:
    """El cuerpo de la Anomalia mientras embiste: sigue al jefe y se apaga
    sola cuando termina la carga."""

    def __init__(self, boss, radius=48):
        self._boss = boss
        self.x, self.y = boss.x, boss.y
        self.radius = radius
        self.active = True

    def update(self):
        a = self._boss.accion
        if a is None or a["tipo"] != "embestida" or a["fase"] != "carga" or not self._boss.active:
            self.active = False
            return
        self.x, self.y = self._boss.x, self._boss.y

    def draw(self, screen, offset_x=0, offset_y=0):
        pass


class AnomalyEsquirlaSuelo:
    """Pedazo de la zona que estalla: aparece clavado y se apaga."""

    def __init__(self, x, y, radius=14, vida=36):
        self.x = x
        self.y = y
        self.radius = radius
        self._vida_max = vida
        self._vida = vida
        self.active = True
        self._ang = random.uniform(0, 2 * math.pi)

    def update(self):
        self._vida -= 1
        if self._vida <= 0:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        if self._vida < 10 and self._vida % 2:
            return
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        pixelfx.dibujar_halo(screen, CRISTAL, cx, cy, 22)
        s = pixelfx.esquirla(CRISTAL, self._ang)
        screen.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2))


class FinalBoss:
    ESCALA = 3
    OJOS = ((-31, -5), (31, -5))
    BOCA = (0, 46)
    NUCLEO = (0, -44)

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH / 2
        self.y = -140.0
        self.target_x = self.x
        self.target_y = 130.0
        self.active = True
        self._dificultad = dificultad
        self.max_hp = max(1, int(800 * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.size = 62
        self.speed = 1.2 * dificultad
        self.name = "LA ANOMALIA FINAL"
        self.phase = 1
        self.rewarded = False
        self.t = 0
        self.enter_timer = 100
        self.move_timer = 0
        self.damaged_timer = 0
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.phase_transition = False
        self.phase_timer = 0
        self.particles = []
        self._ship_x, self._ship_y = self.x, GAME_HEIGHT - 80
        self.accion = None
        self.timer_accion = 70
        self.ultimo = None
        self.cola = []
        self.zona = None
        self.timer_zona = 300
        self.grito = None
        self.timer_grito = 200
        self.clones = []
        self.glitch_timer = 0
        self.glitch_cooldown = 150
        self._franjas = []

    # ------------------------------------------------------------ estado

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
            self.active = False
            return
        ratio = self.hp / self.max_hp
        if (ratio < 0.66 and self.phase == 1) or (ratio < 0.33 and self.phase == 2):
            self.phase += 1
            self.phase_transition = True
            self.phase_timer = 70
            self.cola = []
            if self.accion is not None and self.accion["tipo"] != "embestida":
                self.accion = None
            self.glitch_timer = 40
            self._generar_clones()

    def update(self, ship=None):
        self.t += 1
        if ship is not None:
            self._ship_x, self._ship_y = ship.x, ship.y
        self.damaged_timer = max(0, self.damaged_timer - 1)
        if self.health_deplete_anim > self.hp / self.max_hp:
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.01)
        self._avanzar_particulas()
        self._actualizar_glitch()

        if self.enter_timer > 0:
            self.enter_timer -= 1
            self.y += (self.target_y - self.y) * 0.04
            return []

        balas = self._actualizar_clones()
        if self.phase_transition and (self.accion is None or self.accion["tipo"] != "embestida"):
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase_transition = False
            return balas

        balas += self._soltar_cola()
        if self.accion is None:
            self._mover()
            self.timer_accion -= 1
            if self.timer_accion <= 0 and not self.cola:
                self._elegir_accion()
        else:
            balas += self._actualizar_accion()
        balas += self._actualizar_zona()
        balas += self._actualizar_grito()
        return balas

    def _mover(self):
        dx, dy = self.target_x - self.x, self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 6:
            self.move_timer += 1
            if self.move_timer > 60:
                self.move_timer = 0
                self.target_x = random.randint(140, GAME_WIDTH - 140)
                self.target_y = random.randint(100, 190)
        else:
            paso = min(dist, self.speed)
            self.x += dx / dist * paso
            self.y += dy / dist * paso

    def _ritmo(self):
        return {1: 1.0, 2: 0.8, 3: 0.65}[self.phase] / self._dificultad

    # ------------------------------------------------------------ acciones

    def _elegir_accion(self):
        voleas = ["abanico", "apuntada", "anillo"] + (["espiral"] if self.phase >= 2 else []) \
            + (["lluvia"] if self.phase >= 3 else [])
        grandes = ["hilo", "embestida"] + (["salto"] if self.phase >= 2 else [])
        opciones = voleas + grandes if random.random() < 0.45 else voleas
        if self.ultimo in opciones and len(opciones) > 1:
            opciones.remove(self.ultimo)
        tipo = self.ultimo = random.choice(opciones)
        a = {"tipo": tipo, "fase": "aviso", "t": 0}
        if tipo in voleas:
            a["dur"] = 30 if self.phase < 3 else 24
        elif tipo == "hilo":
            a["dur"] = 60
            a["mira"] = [self._ship_x, self._ship_y]
        elif tipo == "embestida":
            a["dur"] = 44
            dx, dy = self._ship_x - self.x, self._ship_y - self.y
            dist = math.hypot(dx, dy) or 1.0
            a["dir"] = (dx / dist, dy / dist)
            a["origen"] = (self.x, self.y)
        else:
            a["dur"] = 50
            a["destino"] = (random.randint(140, GAME_WIDTH - 140), random.randint(90, 200))
        self.accion = a

    def _actualizar_accion(self):
        a = self.accion
        a["t"] += 1
        tipo = a["tipo"]
        if tipo == "hilo":
            if a["fase"] == "aviso":
                if a["t"] < a["dur"] - 16:
                    a["mira"][0] += (self._ship_x - a["mira"][0]) * 0.12
                    a["mira"][1] += (self._ship_y - a["mira"][1]) * 0.12
                if a["t"] >= a["dur"]:
                    return self._fin_accion(self._abanico_hacia(a["mira"], 5, 0.13, 6.5))
            return []
        if tipo == "embestida":
            if a["fase"] == "aviso":
                if a["t"] >= a["dur"]:
                    a["fase"], a["t"] = "carga", 0
                    return [AnomalyEmbestidaImpacto(self)]
                return []
            if a["fase"] == "carga":
                v = min(16.0, 3 + a["t"] * 1.2)
                self.x += a["dir"][0] * v
                self.y += a["dir"][1] * v
                if a["t"] % 2 == 0:
                    self.particles.append({'x': self.x, 'y': self.y, 'vx': 0, 'vy': 0,
                                           'life': 12, 'max_life': 12, 'fantasma': True})
                fuera = not (40 < self.x < GAME_WIDTH - 40 and 30 < self.y < GAME_HEIGHT - 40)
                if fuera or a["t"] > 40:
                    self.x = max(60, min(GAME_WIDTH - 60, self.x))
                    self.y = max(60, min(GAME_HEIGHT - 60, self.y))
                    a["fase"], a["t"] = "vuelta", 0
                return []
            # vuelve arriba
            self.y += (150 - self.y) * 0.08
            if abs(self.y - 150) < 8:
                self.target_x, self.target_y = self.x, self.y
                return self._fin_accion([])
            return []
        if tipo == "salto":
            if a["t"] >= a["dur"]:
                self.x, self.y = a["destino"]
                self.target_x, self.target_y = self.x, self.y
                self.glitch_timer = max(self.glitch_timer, 18)
                self._generar_clones()
                return self._fin_accion(self._abanico_hacia((self._ship_x, self._ship_y), 3, 0.15, 6.0))
            return []
        # voleas
        if a["t"] >= a["dur"]:
            return self._fin_accion(self._volea(tipo))
        return []

    def _fin_accion(self, balas):
        self.accion = None
        self.timer_accion = int(random.randint(40, 70) * self._ritmo())
        return balas

    def _lanza(self, x, y, ang, vel):
        return AnomalyLanza(x, y, math.cos(ang) * vel, math.sin(ang) * vel)

    def _abanico_hacia(self, punto, n, sep, vel):
        bx, by = self.x + self.BOCA[0], self.y + self.BOCA[1]
        base = math.atan2(punto[1] - by, punto[0] - bx)
        return [self._lanza(bx, by, base + (i - (n - 1) / 2) * sep, vel) for i in range(n)]

    def _volea(self, tipo):
        bx, by = self.x + self.BOCA[0], self.y + self.BOCA[1]
        if tipo == "abanico":
            n = 7 if self.phase < 3 else 9
            return [self._lanza(bx, by, math.radians(90 + (i - (n - 1) / 2) * 13), 4.2) for i in range(n)]
        if tipo == "apuntada":
            for k in range(4):
                self.cola.append((k * 6, lambda: self._abanico_hacia((self._ship_x, self._ship_y), 1, 0, 5.5)[0]))
            return []
        if tipo == "anillo":
            n = 14
            d = random.uniform(0, math.pi)
            return [self._lanza(self.x, self.y, d + 2 * math.pi * i / n, 3.2) for i in range(n)]
        if tipo == "espiral":
            for k in range(12):
                self.cola.append((k * 3, lambda k=k: [self._lanza(self.x, self.y, k * 0.35 + j * math.pi, 3.4)
                                                      for j in range(2)]))
            return []
        # lluvia: esquirlas que caen desde arriba en columnas, con un hueco
        hueco = random.randint(1, 8)
        return [AnomalyLanza(60 + i * 93, -10, 0, 3.6) for i in range(10) if i not in (hueco, hueco + 1)]

    def _soltar_cola(self):
        salen, quedan = [], []
        for demora, fabrica in self.cola:
            if demora <= 0:
                r = fabrica()
                salen.extend(r if isinstance(r, list) else [r])
            else:
                quedan.append((demora - 1, fabrica))
        self.cola = quedan
        return salen

    def _actualizar_zona(self):
        z = self.zona
        if z is None:
            self.timer_zona -= 1
            if self.timer_zona <= 0:
                self.zona = {"x": self._ship_x, "y": self._ship_y, "r": 95, "t": 0, "dur": 60}
            return []
        z["t"] += 1
        if z["t"] >= z["dur"]:
            self.zona = None
            self.timer_zona = int(random.randint(340, 440) * self._ritmo())
            esquirlas = []
            for i in range(12):
                a = i * math.pi / 6 + random.uniform(-0.2, 0.2)
                r = z["r"] * (0.35 if i % 2 else 0.8)
                esquirlas.append(AnomalyEsquirlaSuelo(z["x"] + math.cos(a) * r, z["y"] + math.sin(a) * r))
            esquirlas.append(AnomalyEsquirlaSuelo(z["x"], z["y"]))
            return esquirlas
        return []

    def _actualizar_grito(self):
        if self.phase < 3:
            return []
        g = self.grito
        if g is None:
            self.timer_grito -= 1
            if self.timer_grito <= 0 and self.accion is None:
                self.grito = {"t": 0, "hueco": math.atan2(self._ship_y - self.y, self._ship_x - self.x)
                              + random.uniform(-1.0, 1.0)}
            return []
        g["t"] += 1
        if g["t"] < 50:
            return []
        self.grito = None
        self.timer_grito = random.randint(340, 440)
        balas = []
        n = 24
        for i in range(n):
            a = 2 * math.pi * i / n
            if abs((a - g["hueco"] + math.pi) % (2 * math.pi) - math.pi) < math.radians(30):
                continue
            balas.append(self._lanza(self.x, self.y, a, 2.2))
        return balas

    # ------------------------------------------------------------ glitch y clones

    def _actualizar_glitch(self):
        if self.glitch_timer > 0:
            self.glitch_timer -= 1
            if self.t % 3 == 0:
                self._franjas = [(random.randint(-90, 90) // 3 * 3, random.choice((-9, -6, 6, 9)))
                                 for _ in range(random.randint(2, 4))]
            return
        self.glitch_cooldown -= 1
        if self.glitch_cooldown <= 0 and self.enter_timer <= 0:
            self.glitch_timer = random.randint(16, 26)
            self.glitch_cooldown = random.randint(*{1: (160, 220), 2: (110, 160), 3: (70, 110)}[self.phase])
            if self.phase >= 2 and not self.clones and random.random() < 0.5:
                self._generar_clones()

    def _generar_clones(self):
        self.clones = []
        # a los costados del jefe; si no hay lugar de un lado, mas lejos del otro
        d = random.uniform(230, 270)
        lados = [-1, 1]
        random.shuffle(lados)
        huecos = [self.x + lado * d * k for k in (1, 2) for lado in lados]
        huecos = [x for x in huecos if 90 < x < GAME_WIDTH - 90]
        for x in huecos[:1 if self.phase == 1 else 2]:
            self.clones.append({'x': x, 'y': max(80, min(GAME_HEIGHT // 2, self.y + random.uniform(-40, 40))),
                                'vida': random.randint(110, 150), 'disparo': random.randint(30, 50)})

    def _actualizar_clones(self):
        balas, vivos = [], []
        for c in self.clones:
            c['vida'] -= 1
            c['disparo'] -= 1
            if c['disparo'] <= 0:
                c['disparo'] = random.randint(50, 70)
                a = math.atan2(self._ship_y - c['y'], self._ship_x - c['x'])
                balas.append(self._lanza(c['x'], c['y'] + self.BOCA[1], a, 4.0))
            if c['vida'] > 0:
                vivos.append(c)
        self.clones = vivos
        return balas

    def _avanzar_particulas(self):
        if self.damaged_timer > 0 and random.random() < 0.5:
            a = random.uniform(0, 2 * math.pi)
            self.particles.append({'x': self.x, 'y': self.y, 'vx': math.cos(a) * 3, 'vy': math.sin(a) * 3,
                                   'life': 20, 'max_life': 20})
        if random.random() < 0.15:
            # motas de vacio que suben del craneo
            self.particles.append({'x': self.x + random.uniform(-50, 50), 'y': self.y - random.uniform(20, 70),
                                   'vx': 0, 'vy': -random.uniform(0.4, 1.0), 'life': 30, 'max_life': 30})
        vivas = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] > 0:
                vivas.append(p)
        self.particles = vivas

    # ------------------------------------------------------------ dibujo

    def _sprite(self):
        craneo, placas = COLORES_FASE[self.phase]
        w, h = sprites.tamano_pixel("boss", "anomalia_px", self.ESCALA)
        return sprites.get_boss_surface(craneo, placas, w, h, kind="anomalia_px")

    def _blit_glitch(self, screen, sprite, rect, alfa=255):
        """Sprite cortado en franjas corridas, con fantasmas rojo y cian."""
        if self.glitch_timer <= 0:
            if alfa < 255:
                copia = sprite.copy()
                copia.set_alpha(alfa)
                screen.blit(copia, rect)
            else:
                screen.blit(sprite, rect)
            return
        blanco = pixelfx.silueta_blanca(sprite)
        for color, dx in ((ROJO_AVISO, -6), (CIAN, 6)):
            fantasma = blanco.copy()
            fantasma.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
            fantasma.set_alpha(110 * alfa // 255)
            screen.blit(fantasma, rect.move(dx, 0))
        alto = sprite.get_height()
        franja = 12
        for y in range(0, alto, franja):
            dx = 0
            for fy, desp in self._franjas:
                if abs((y - alto // 2) - fy) < 18:
                    dx = desp
            parte = sprite.subsurface((0, y, sprite.get_width(), min(franja, alto - y)))
            if alfa < 255:
                parte = parte.copy()
                parte.set_alpha(alfa)
            screen.blit(parte, (rect.x + dx, rect.y + y))

    def _dibujar_ojos(self, screen, cx, cy, alfa=255):
        color = (255, 60, 110) if self.phase < 3 else (255, 255, 255)
        for ox, oy in self.OJOS:
            x, y = cx + ox, cy + oy
            dx, dy = self._ship_x - x, self._ship_y - y
            d = math.hypot(dx, dy) or 1.0
            px = x + int(dx / d * 6) // 3 * 3
            py = y + int(dy / d * 6) // 3 * 3
            if alfa == 255:
                pixelfx.dibujar_halo(screen, color, px, py, 14)
            screen.fill(color, (px - 6, py - 6, 12, 12))
            screen.fill(WHITE, (px - 3, py - 3, 6, 6))

    def _punteada(self, screen, x0, y0, x1, y1, color, hueco=3):
        largo = math.hypot(x1 - x0, y1 - y0)
        n = int(largo / 8)
        for k in range(n):
            if (k + self.t // 2) % hueco == 0:
                continue
            f = k / max(1, n)
            screen.fill(color, (int(x0 + (x1 - x0) * f) - 2, int(y0 + (y1 - y0) * f) - 2, 4, 4))

    def _dibujar_avisos(self, screen, cx, cy, ox, oy):
        a = self.accion
        if a is not None and a["fase"] == "aviso":
            prog = a["t"] / a["dur"]
            tipo = a["tipo"]
            if tipo == "hilo":
                fijo = a["t"] >= a["dur"] - 16
                color = ROJO_AVISO if fijo else CRISTAL
                mx, my = a["mira"][0] + ox, a["mira"][1] + oy
                self._punteada(screen, cx + self.BOCA[0], cy + self.BOCA[1], mx, my, color)
                pixelfx.dibujar_halo(screen, color, mx, my, 20)
                screen.fill(color, (int(mx) - 6, int(my) - 1, 12, 3))
                screen.fill(color, (int(mx) - 1, int(my) - 6, 3, 12))
            elif tipo == "embestida":
                dx, dy = a["dir"]
                nx, ny = -dy, dx
                largo = 900
                # bordes del carril por donde pasara el cuerpo
                color = ROJO_AVISO if (self.t // 4) % 2 or prog > 0.7 else CRISTAL
                for k in range(3, largo // 12):
                    if (k + self.t // 2) % 3 == 0:
                        continue
                    for lado in (-1, 1):
                        x = cx + dx * k * 12 + nx * lado * 50
                        y = cy + dy * k * 12 + ny * lado * 50
                        screen.fill(color, (int(x) - 2, int(y) - 2, 4, 4))
                # chevrones que avanzan por el centro
                for k in range(1, 16):
                    if (k - self.t // 4) % 3:
                        continue
                    x0 = cx + dx * (50 + k * 55)
                    y0 = cy + dy * (50 + k * 55)
                    for j in range(5):
                        for lado in (-1, 1):
                            x = x0 - dx * j * 6 + nx * lado * j * 7
                            y = y0 - dy * j * 6 + ny * lado * j * 7
                            screen.fill(ROJO_AVISO, (int(x) - 3, int(y) - 3, 6, 6))
            elif tipo == "salto":
                x, y = a["destino"][0] + ox, a["destino"][1] + oy
                alto = int(40 + 100 * prog)
                for k in range(0, alto, 6):
                    desp = ((k * 7 + self.t) % 5 - 2) * 3
                    screen.fill(CRISTAL if k % 12 else WHITE, (x + desp - 3, y - alto // 2 + k, 6, 6))
                pixelfx.dibujar_halo(screen, CRISTAL, x, y, 20 + 30 * prog)
            else:
                pixelfx.carga(screen, CRISTAL, cx + self.BOCA[0], cy + self.BOCA[1], prog, self.t, 18)
        z = self.zona
        if z is not None:
            prog = z["t"] / z["dur"]
            color = ROJO_AVISO if (self.t // 4) % 2 or prog > 0.8 else CRISTAL
            n = 28
            for i in range(n):
                if (i + self.t // 3) % 2:
                    continue
                ang = 2 * math.pi * i / n
                screen.fill(color, (int(z["x"] + ox + math.cos(ang) * z["r"]) - 3,
                                    int(z["y"] + oy + math.sin(ang) * z["r"]) - 3, 6, 6))
            r = int(z["r"] * prog)
            pixelfx.dibujar_halo(screen, color, z["x"] + ox, z["y"] + oy, max(4, r))
        g = self.grito
        if g is not None:
            # el anillo se cierra sobre el jefe; el hueco se marca en verde
            n = 24
            r = 140 + (50 - g["t"]) * 3
            for i in range(n):
                ang = 2 * math.pi * i / n
                en_hueco = abs((ang - g["hueco"] + math.pi) % (2 * math.pi) - math.pi) < math.radians(30)
                if en_hueco or (self.t // 4) % 2:
                    color = MENTA if en_hueco else ROJO_AVISO
                    screen.fill(color, (int(cx + math.cos(ang) * r) - 4, int(cy + math.sin(ang) * r) - 4, 8, 8))
            for borde in (-1, 1):
                ang = g["hueco"] + borde * math.radians(30)
                for k in range(12, 60):
                    if (k + self.t // 2) % 3:
                        continue
                    screen.fill(MENTA, (int(cx + math.cos(ang) * k * 8) - 2, int(cy + math.sin(ang) * k * 8) - 2, 4, 4))

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        ox, oy = offset_x, offset_y
        sprite = self._sprite()

        # rastro de la embestida y de las motas
        for p in self.particles:
            k = p['life'] / p['max_life']
            if p.get('fantasma'):
                copia = pixelfx.silueta_blanca(sprite).copy()
                copia.fill(CRISTAL, special_flags=pygame.BLEND_RGBA_MULT)
                copia.set_alpha(int(90 * k))
                screen.blit(copia, copia.get_rect(center=(int(p['x']) + ox, int(p['y']) + oy)))
            else:
                lado = 4 if k > 0.5 else 2
                screen.fill(pixelfx.aclarar(CRISTAL, 0.4 * k), (int(p['x']) + ox, int(p['y']) + oy, lado, lado))

        if self.enter_timer <= 0:
            self._dibujar_avisos(screen, cx, cy, ox, oy)

        for c in self.clones:
            rect = sprite.get_rect(center=(int(c['x']) + ox, int(c['y']) + oy))
            self._blit_glitch(screen, sprite, rect, 120)
            self._dibujar_ojos(screen, rect.centerx, rect.centery, 120)

        a = self.accion
        if a is not None and a["tipo"] == "embestida" and a["fase"] == "aviso":
            cx += random.randint(-3, 3)
        rect = sprite.get_rect(center=(cx, cy))
        if self.enter_timer > 0:
            self._blit_glitch(screen, sprite, rect, int(255 * (1 - self.enter_timer / 100)))
            return
        if self.glitch_timer > 0 and self._franjas:
            # el glitch se filtra al fondo: barras corridas alrededor
            for fy, desp in self._franjas:
                screen.fill(tuple(c // 3 for c in CRISTAL), (cx - 150 + desp * 4, cy + fy, 300, 3),
                            special_flags=pygame.BLEND_RGB_ADD)
        self._blit_glitch(screen, sprite, rect)
        if self.damaged_timer > 3 or (self.phase_transition and (self.phase_timer // 4) % 2 == 0):
            blanco = pixelfx.silueta_blanca(sprite)
            blanco.set_alpha(170)
            screen.blit(blanco, rect)
        pixelfx.dibujar_halo(screen, CIAN, cx + self.NUCLEO[0], cy + self.NUCLEO[1], 12 + (self.t // 6) % 3 * 3)
        self._dibujar_ojos(screen, cx, cy)

        temblor = (0, 0)
        if self.health_shake > 0:
            temblor = (random.randint(-self.health_shake, self.health_shake), 0)
            self.health_shake -= 1
        ratio = max(0.0, self.hp / self.max_hp)
        y_barra = max(14, cy - sprite.get_height() // 2 - 2)
        pixelfx.barra_jefe(screen, cx, y_barra, 156, ratio, self.health_deplete_anim, COLORES_FASE[self.phase][0], temblor)
        etiqueta = render_text(self.name, 11, WHITE)
        screen.blit(etiqueta, (cx - etiqueta.get_width() // 2, y_barra - 18))
