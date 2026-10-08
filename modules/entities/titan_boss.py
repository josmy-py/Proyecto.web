"""
Titan del Vacio (oleada 30): pulpo mecanico en pixel art neon (arte "titan"
en tools/generate_pixel_sprites.py) que domina la mitad de arriba de la
pantalla. No dispara: pelea con los tentaculos, que se dibujan en pixeles
segmento a segmento y se estiran de verdad hasta el lugar que golpean.

Cada golpe se marca antes en el piso (una mira que se cierra) y el
tentaculo tarda en llegar, asi que siempre se puede salir:

  SISMO: un tentaculo baja desde el vientre hasta donde estaba la nave.
  BRAZO: sale de un hombro siguiendo la altura de la nave y barre de
  costado hasta el otro lado.
  EMBOSCADA (fase 2+): puñalada corta desde el vientre, con menos aviso.
  ENJAMBRE: los seis tentaculos a la vez en abanico a la altura de la
  nave; las miras muestran los huecos por donde pasar.
  GUARDIA: cruza dos tentaculos delante del ojo y bloquea los disparos
  que caen ahi (bloquea_disparo); hay que rodearla para pegarle al ojo.

En fase 3 cada golpe del sismo suelta ademas un anillo lento de tinta.
Solo hay un golpe grande a la vez (sismo, brazo o enjambre); la emboscada
y la guardia pueden coincidir con ellos."""

import math
import random

import pygame

from modules.constants import AMARILLO, GAME_HEIGHT, GAME_WIDTH, MELON, ROSA, WHITE
from modules.core.boss_system import WaveBossBullet
from modules.systems import pixelfx, sprites
from modules.systems.fonts import render_text

# (casco, tentaculos) por fase
COLORES_FASE = {
    1: ((140, 100, 220), (110, 80, 190)),
    2: ((200, 90, 160), (160, 70, 140)),
    3: ((230, 80, 70), (180, 60, 70)),
}
TINTA = (120, 60, 200)

# Raices de los tentaculos en px de pantalla respecto del centro del
# sprite (salen de los muñones y los hombros del arte)
RAIZ_HOMBROS = ((-90, 18), (90, 18))
RAIZ_VIENTRE = (0, 62)
# los seis de reposo/enjambre con su angulo de reposo en grados
RAICES_IDLE = (
    ((-60, 48), 125), ((60, 48), 55),
    ((-36, 60), 110), ((36, 60), 70),
    ((-12, 66), 98), ((12, 66), 82),
)


class TentaculoImpacto:
    """Zona de golpe de un tentaculo: aparece donde y cuando llega la
    punta y dura pocos cuadros. Tiene la forma de una bala (x, y, radius,
    active, update, draw) para ir a boss_bullets de main.py."""

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
        k = max(0.0, self._vida / self._vida_max)
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        r = int(self.radius * (0.6 + 0.6 * (1 - k)))
        pixelfx.dibujar_halo(screen, self.color, cx, cy, r)
        # onda expansiva en bloques
        for i in range(16):
            a = i * math.pi / 8
            x = cx + int(math.cos(a) * r) // 4 * 4
            y = cy + int(math.sin(a) * r * 0.6) // 4 * 4
            screen.fill(pixelfx.aclarar(self.color, 0.5), (x - 3, y - 3, 6, 6))


def _segmento(radio, color, ventosa):
    """Disco de tentaculo en pixel art (cacheado)."""
    clave = ("titan_seg", radio, color, ventosa)
    surf = pixelfx._cache.get(clave)
    if surf is not None:
        return surf
    n = radio * 2 + 3
    base = pygame.Surface((n, n), pygame.SRCALPHA)
    c = n // 2
    pygame.draw.circle(base, pixelfx.CONTORNO, (c, c), radio + 1)
    pygame.draw.circle(base, color, (c, c), radio)
    claro = pixelfx.aclarar(color, 0.35)
    pygame.draw.circle(base, claro, (c - max(1, radio // 3), c - max(1, radio // 3)), max(1, radio // 2))
    if ventosa:
        base.fill((240, 210, 230), (c, c + radio // 2, 1, 1))
    surf = pygame.transform.scale(base, (n * 3, n * 3))
    return pixelfx._guardar(clave, surf)


class TitanBoss:
    ESCALA = 3
    OJO = (0, 32)

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH / 2
        self.y = -150.0
        self.target_x = self.x
        self.target_y = 130.0
        self.active = True
        self._dificultad = dificultad
        self.max_hp = max(1, int(550 * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.size = 66
        self.speed = 0.5 * dificultad
        self.name = "TITAN DEL VACIO"
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
        self._ship = None
        self._ship_x, self._ship_y = self.x, GAME_HEIGHT - 80
        # golpe grande en curso (sismo / brazo / enjambre)
        self.golpe = None
        self.timer_golpe = 120
        self.ultimo_golpe = None
        self.emboscada = None
        self.timer_emboscada = 260
        self.guardia = None
        self.timer_guardia = 300
        self._guardia_radio = 34

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
            self.golpe = None
            self.emboscada = None
            self._chispas(30)

    def bloquea_disparo(self, x, y):
        g = self.guardia
        if g is None or g["fase"] != "activa":
            return False
        for zx in (g["x"] - 22, g["x"] + 22):
            if (x - zx) ** 2 + (y - g["y"]) ** 2 < self._guardia_radio ** 2:
                return True
        return False

    def update(self, ship=None):
        self.t += 1
        self._ship = ship
        if ship is not None:
            self._ship_x, self._ship_y = ship.x, ship.y
        self.damaged_timer = max(0, self.damaged_timer - 1)
        if self.health_deplete_anim > self.hp / self.max_hp:
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.01)
        self._avanzar_particulas()

        if self.enter_timer > 0:
            self.enter_timer -= 1
            self.y += (self.target_y - self.y) * 0.04
            return []
        if self.phase_transition:
            self.phase_timer -= 1
            if self.phase_timer % 8 == 0:
                self._chispas(5)
            if self.phase_timer <= 0:
                self.phase_transition = False
            return []

        if self.golpe is None:
            self._mover()
        balas = []
        balas += self._actualizar_golpe()
        balas += self._actualizar_emboscada()
        self._actualizar_guardia()
        return balas

    def _mover(self):
        dx, dy = self.target_x - self.x, self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 6:
            self.move_timer += 1
            if self.move_timer > 120:
                self.move_timer = 0
                self.target_x = random.randint(170, GAME_WIDTH - 170)
                self.target_y = random.randint(110, 150)
        else:
            paso = min(dist, self.speed)
            self.x += dx / dist * paso
            self.y += dy / dist * paso

    def _ritmo(self):
        return {1: 1.0, 2: 0.8, 3: 0.65}[self.phase] / self._dificultad

    # ------------------------------------------------------------ golpes

    def _iniciar_golpe(self):
        opciones = ["sismo", "brazo"] + (["enjambre"] if self.phase >= 2 else [])
        if self.ultimo_golpe in opciones:
            opciones.remove(self.ultimo_golpe)
        tipo = self.ultimo_golpe = random.choice(opciones)
        sy = min(GAME_HEIGHT - 50, self._ship_y)
        if tipo == "sismo":
            self.golpe = {"tipo": tipo, "fase": "aviso", "t": 0, "dur": 90,
                          "raices": [RAIZ_VIENTRE], "blancos": [(self._ship_x, sy)]}
        elif tipo == "brazo":
            lado = -1 if self._ship_x > GAME_WIDTH / 2 else 1
            raiz = RAIZ_HOMBROS[0 if lado < 0 else 1]
            x0 = 60 if lado < 0 else GAME_WIDTH - 60
            self.golpe = {"tipo": tipo, "fase": "aviso", "t": 0, "dur": 95, "lado": lado,
                          "raices": [raiz], "blancos": [(x0, sy)]}
        else:
            margen = 90
            paso = (GAME_WIDTH - 2 * margen) / 5
            self.golpe = {"tipo": tipo, "fase": "aviso", "t": 0, "dur": 120,
                          "raices": [r for r, _ in RAICES_IDLE],
                          "blancos": [(margen + i * paso, sy) for i in range(6)]}

    def _actualizar_golpe(self):
        g = self.golpe
        if g is None:
            self.timer_golpe -= 1
            if self.timer_golpe <= 0:
                self._iniciar_golpe()
            return []
        g["t"] += 1
        if g["fase"] == "aviso":
            if g["tipo"] == "brazo":
                # sigue la altura de la nave con retraso
                bx, by = g["blancos"][0]
                g["blancos"][0] = (bx, by + (min(GAME_HEIGHT - 50, self._ship_y) - by) * 0.04)
            if g["t"] >= g["dur"]:
                g["fase"], g["t"] = "golpe", 0
                if g["tipo"] == "brazo":
                    return []
                return self._impactos(g)
            return []
        if g["fase"] == "golpe":
            if g["tipo"] == "brazo":
                # barre de costado hasta el otro lado
                bx, by = g["blancos"][0]
                bx -= g["lado"] * 26
                g["blancos"][0] = (bx, by)
                if g["t"] % 2 == 0:
                    return [TentaculoImpacto(bx, by, 40, ROSA, 6)]
                if bx < 40 or bx > GAME_WIDTH - 40:
                    g["fase"], g["t"] = "retiro", 0
                return []
            if g["t"] >= 14:
                g["fase"], g["t"] = "retiro", 0
            return []
        if g["t"] >= 40:
            self.golpe = None
            self.timer_golpe = int(random.randint(70, 110) * self._ritmo())
        return []

    def _impactos(self, g):
        color = MELON if g["tipo"] == "sismo" else AMARILLO
        radio = 52 if g["tipo"] == "sismo" else 40
        balas = [TentaculoImpacto(x, y, radio, color, 16) for x, y in g["blancos"]]
        if g["tipo"] == "sismo" and self.phase == 3:
            x, y = g["blancos"][0]
            desfase = random.uniform(0, math.pi)
            balas += [WaveBossBullet(x, y, math.cos(a) * 2.0, math.sin(a) * 2.0, TINTA, 5)
                      for a in (desfase + i * math.pi / 5 for i in range(10))]
        return balas

    def _actualizar_emboscada(self):
        e = self.emboscada
        if e is None:
            if self.phase >= 2:
                self.timer_emboscada -= 1
                if self.timer_emboscada <= 0:
                    sy = min(GAME_HEIGHT - 50, self._ship_y)
                    self.emboscada = {"fase": "aviso", "t": 0, "dur": 46, "blanco": (self._ship_x, sy)}
            return []
        e["t"] += 1
        if e["fase"] == "aviso" and e["t"] >= e["dur"]:
            e["fase"], e["t"] = "golpe", 0
            return [TentaculoImpacto(e["blanco"][0], e["blanco"][1], 38, AMARILLO, 12)]
        if e["fase"] == "golpe" and e["t"] >= 10:
            e["fase"], e["t"] = "retiro", 0
        if e["fase"] == "retiro" and e["t"] >= 26:
            self.emboscada = None
            self.timer_emboscada = int(random.randint(200, 260) * self._ritmo())
        return []

    def _actualizar_guardia(self):
        g = self.guardia
        if g is None:
            self.timer_guardia -= 1
            if self.timer_guardia <= 0 and self.golpe is None:
                self.guardia = {"fase": "subida", "t": 0,
                                "x": max(220, min(GAME_WIDTH - 220, self._ship_x)), "y": self.y + 150}
            return
        g["t"] += 1
        if g["fase"] == "subida" and g["t"] >= 22:
            g["fase"], g["t"] = "activa", 0
        elif g["fase"] == "activa" and g["t"] >= 140:
            g["fase"], g["t"] = "bajada", 0
        elif g["fase"] == "bajada" and g["t"] >= 22:
            self.guardia = None
            self.timer_guardia = int(random.randint(280, 360) * self._ritmo())

    # ------------------------------------------------------------ efectos

    def _chispas(self, n):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.5, 3.5)
            self.particles.append({'x': self.x + random.uniform(-70, 70), 'y': self.y + random.uniform(-50, 50),
                                   'vx': math.cos(a) * v, 'vy': math.sin(a) * v,
                                   'life': random.randint(16, 30), 'max_life': 30})

    def _avanzar_particulas(self):
        if self.damaged_timer > 0 and random.random() < 0.5:
            self._chispas(1)
        vivas = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] > 0:
                vivas.append(p)
        self.particles = vivas

    # ------------------------------------------------------------ dibujo

    @staticmethod
    def _extension(estado):
        if estado is None:
            return 0.0
        if estado["fase"] == "aviso":
            k = estado["t"] / estado["dur"]
            return 0.15 + 0.6 * k * k       # se asoma y despues se estira
        if estado["fase"] in ("golpe", "activa"):
            return 1.0
        if estado["fase"] == "subida":
            return estado["t"] / 22
        if estado["fase"] == "bajada":
            return 1 - estado["t"] / 22
        return max(0.0, 1 - estado["t"] / 30)

    def _tentaculo(self, screen, x0, y0, x1, y1, ext, color, grosor=11, onda=8.0, ox=0, oy=0):
        """Cadena de discos desde la raiz hasta ext (0..1) del camino a la
        punta, con una ondulacion que se apaga en la punta."""
        if ext <= 0.01:
            return
        dx, dy = x1 - x0, y1 - y0
        largo = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / largo, dx / largo
        n = max(4, int(largo * ext / 13))
        for i in range(n, -1, -1):
            f = i / n
            k = f * ext
            ondula = math.sin(self.t * 0.12 + f * 5) * onda * math.sin(math.pi * f)
            x = x0 + dx * k + nx * ondula
            y = y0 + dy * k + ny * ondula
            r = max(2, round(grosor * (1 - 0.6 * f) / 3))
            seg = _segmento(r, color, i % 2 == 0)
            screen.blit(seg, (int(x) + ox - seg.get_width() // 2, int(y) + oy - seg.get_height() // 2))

    def _mira(self, screen, x, y, prog, color):
        """Marca del golpe: un cuadrado que se cierra sobre el blanco."""
        lado = int(70 - 46 * prog) // 2 * 2
        c = color if (self.t // 4) % 2 else pixelfx.aclarar(color, 0.5)
        x, y = int(x), int(y)
        for sx in (-1, 1):
            for sy in (-1, 1):
                ex, ey = x + sx * lado // 2, y + sy * lado // 2
                screen.fill(c, (min(ex, ex - sx * 12), ey - 2, 12, 4))
                screen.fill(c, (ex - 2, min(ey, ey - sy * 12), 4, 12))
        screen.fill(c, (x - 2, y - 2, 4, 4))
        pixelfx.dibujar_halo(screen, color, x, y, 16 + 14 * prog)

    def _sprite(self):
        casco, _ = COLORES_FASE[self.phase]
        w, h = sprites.tamano_pixel("boss", "titan_px", self.ESCALA)
        return sprites.get_boss_surface(casco, pixelfx.aclarar(casco, 0.3), w, h, kind="titan_px")

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        _, color_t = COLORES_FASE[self.phase]
        ox, oy = cx - self.x, cy - self.y

        # tentaculos de reposo (los que no estan en el enjambre)
        enjambre = self.golpe is not None and self.golpe["tipo"] == "enjambre"
        if not enjambre:
            for i, ((rx, ry), ang) in enumerate(RAICES_IDLE):
                a = math.radians(ang + math.sin(self.t * 0.03 + i * 1.3) * 12)
                largo = 70 + 12 * math.sin(self.t * 0.04 + i)
                x0, y0 = self.x + rx, self.y + ry
                self._tentaculo(screen, x0, y0, x0 + math.cos(a) * largo, y0 + math.sin(a) * largo,
                                1.0, color_t, 12, 6, ox, oy)

        # marcas de los golpes en el piso
        g = self.golpe
        if g is not None and g["fase"] == "aviso":
            prog = g["t"] / g["dur"]
            for bx, by in g["blancos"]:
                self._mira(screen, bx + offset_x, by + offset_y, prog, (255, 80, 110))
            if g["tipo"] == "brazo":
                bx, by = g["blancos"][0]
                for x in range(40, GAME_WIDTH - 40, 24):
                    if (x // 24 + self.t // 4) % 2:
                        screen.fill((255, 80, 110), (x + offset_x, int(by) + offset_y + 26, 12, 3))
        e = self.emboscada
        if e is not None and e["fase"] == "aviso":
            self._mira(screen, e["blanco"][0] + offset_x, e["blanco"][1] + offset_y, e["t"] / e["dur"], AMARILLO)

        sprite = self._sprite()
        rect = sprite.get_rect(center=(cx, cy))
        if self.enter_timer > 0:
            copia = sprite.copy()
            copia.set_alpha(int(255 * (1 - self.enter_timer / 100)))
            screen.blit(copia, rect)
        else:
            screen.blit(sprite, rect)
            if self.damaged_timer > 3 or (self.phase_transition and (self.phase_timer // 4) % 2 == 0):
                blanco = pixelfx.silueta_blanca(sprite)
                blanco.set_alpha(170)
                screen.blit(blanco, rect)
        self._dibujar_ojo(screen, cx + self.OJO[0], cy + self.OJO[1])

        # tentaculos de ataque (encima del cuerpo)
        if g is not None:
            ext = self._extension(g)
            for (rx, ry), (bx, by) in zip(g["raices"], g["blancos"]):
                self._tentaculo(screen, self.x + rx, self.y + ry, bx, by, ext, color_t, 16,
                                0 if g["fase"] == "golpe" else 10, ox, oy)
        if e is not None:
            # sale del muñon mas cercano al blanco
            rx, ry = min((r for r, _ in RAICES_IDLE), key=lambda r: abs(self.x + r[0] - e["blanco"][0]))
            self._tentaculo(screen, self.x + rx, self.y + ry,
                            e["blanco"][0], e["blanco"][1], self._extension(e), color_t, 13, 6, ox, oy)
        gd = self.guardia
        if gd is not None:
            ext = self._extension(gd)
            claro = pixelfx.aclarar(color_t, 0.25)
            for (rx, ry), lado in zip(RAIZ_HOMBROS, (1, -1)):
                self._tentaculo(screen, self.x + rx, self.y + ry, gd["x"] + lado * 30, gd["y"], ext,
                                claro, 16, 0, ox, oy)
            if gd["fase"] == "activa":
                for zx in (gd["x"] - 22, gd["x"] + 22):
                    pixelfx.dibujar_halo(screen, claro, zx + offset_x, gd["y"] + offset_y, 30)

        for p in self.particles:
            k = p['life'] / p['max_life']
            c = (int(200 + 55 * k), int(150 + 100 * k), 255)
            lado = 4 if k > 0.5 else 2
            screen.fill(c, (int(p['x']) + offset_x, int(p['y']) + offset_y, lado, lado))

        if self.enter_timer <= 0:
            temblor = (0, 0)
            if self.health_shake > 0:
                temblor = (random.randint(-self.health_shake, self.health_shake), 0)
                self.health_shake -= 1
            ratio = max(0.0, self.hp / self.max_hp)
            y_barra = max(14, cy - sprite.get_height() // 2 - 2)
            pixelfx.barra_jefe(screen, cx, y_barra, 160, ratio, self.health_deplete_anim,
                               COLORES_FASE[self.phase][0], temblor)
            etiqueta = render_text(self.name, 11, WHITE)
            screen.blit(etiqueta, (cx - etiqueta.get_width() // 2, y_barra - 18))

    def _dibujar_ojo(self, screen, ox, oy):
        """Pupila en pixeles que sigue a la nave dentro de la cuenca."""
        dx, dy = self._ship_x - ox, self._ship_y - oy
        dist = math.hypot(dx, dy) or 1.0
        px = ox + int(dx / dist * 9) // 3 * 3
        py = oy + int(dy / dist * 9) // 3 * 3
        color = (255, 60, 70) if self.phase < 3 else (255, 140, 40)
        pixelfx.dibujar_halo(screen, color, px, py, 22)
        screen.fill(color, (px - 9, py - 9, 18, 18))
        screen.fill(color, (px - 12, py - 6, 24, 12))
        screen.fill(color, (px - 6, py - 12, 12, 24))
        screen.fill((30, 6, 12), (px - 3, py - 6, 6, 12))
        screen.fill((255, 255, 255), (px - 9, py - 9, 3, 3))
