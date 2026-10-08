"""
Asteroides (pixel art dibujado por codigo, ver _arte_roca) y los efectos
visuales de particulas que usa todo el juego (Particle/Explosion las
reutilizan jefes y enemigos, no solo los asteroides)."""

import random
import math

import pygame

from modules.constants import MELON, GAME_WIDTH, GAME_HEIGHT
from modules.systems import pixelfx


# ------------------------------------------------------------- asteroides

PIXEL_ROCA = 3          # px de juego por "pixel de arte"
VARIANTES_ROCA = 10

# Tipos de roca: (contorno, sombra, medio, luz, brillo, veta, veta_luz).
# Roca oscura con vetas de energia neon que se encienden al agrietarse.
PALETAS_ROCA = {
    "magma":   ((24, 8, 20), (70, 34, 44), (112, 62, 62), (156, 98, 84), (204, 150, 120), (255, 110, 40), (255, 230, 120)),
    "cristal": ((8, 14, 32), (36, 52, 84), (64, 88, 124), (100, 128, 164), (160, 190, 220), (60, 220, 255), (210, 250, 255)),
    "plasma":  ((20, 6, 34), (52, 30, 76), (86, 56, 112), (124, 90, 150), (180, 150, 210), (255, 70, 220), (255, 200, 250)),
    "toxica":  ((10, 20, 14), (40, 58, 46), (68, 90, 70), (104, 126, 98), (160, 180, 140), (130, 255, 90), (230, 255, 190)),
}
_TIPOS_ROCA = tuple(PALETAS_ROCA)

# matriz de Bayer 4x4 para el tramado entre tonos (borde de luz y sombra)
_BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

_CACHE_ROCAS = {}


def _arte_roca(variante, radio, tipo, rajada):
    """Roca pixel art de `radio` pixeles de arte: silueta irregular con
    contorno oscuro, tres tonos con tramado (luz arriba a la izquierda),
    crateres, vetas de energia y, si esta `rajada` (le queda 1 golpe),
    grietas encendidas que la cruzan y un pedazo de borde saltado."""
    clave = (variante, radio, tipo, rajada)
    arte = _CACHE_ROCAS.get(clave)
    if arte is not None:
        return arte
    contorno, sombra, medio, luz, brillo, veta, veta_luz = PALETAS_ROCA[tipo]
    rng = random.Random(variante * 7919 + radio * 31)
    lado = radio * 2 + 3
    c = lado / 2.0

    # silueta: radio variable por angulo (suavizado), algunas rocas alargadas
    n = 16
    crudo = [rng.uniform(0.68, 1.0) for _ in range(n)]
    perfil = [(crudo[i - 1] + 2 * crudo[i] + crudo[(i + 1) % n]) / 4 for i in range(n)]
    estirar = rng.uniform(0.82, 1.0)
    giro = rng.uniform(0, math.pi)

    def dentro(x, y):
        dx, dy = x + 0.5 - c, y + 0.5 - c
        rx = dx * math.cos(giro) + dy * math.sin(giro)
        ry = (-dx * math.sin(giro) + dy * math.cos(giro)) / estirar
        a = math.atan2(ry, rx) % (2 * math.pi)
        k = a / (2 * math.pi) * n
        i = int(k) % n
        f = k - int(k)
        r = (perfil[i] * (1 - f) + perfil[(i + 1) % n] * f) * radio
        return rx * rx + ry * ry <= r * r

    mascara = [[dentro(x, y) for x in range(lado)] for y in range(lado)]
    if rajada:
        # un pedazo del borde saltado por el primer golpe
        a = rng.uniform(0, 2 * math.pi)
        mx, my = c + math.cos(a) * radio, c + math.sin(a) * radio
        for y in range(lado):
            for x in range(lado):
                if (x - mx) ** 2 + (y - my) ** 2 < (radio * 0.32) ** 2:
                    mascara[y][x] = False

    arte = pygame.Surface((lado, lado), pygame.SRCALPHA)
    crateres = [(c + rng.uniform(-0.5, 0.5) * radio, c + rng.uniform(-0.5, 0.5) * radio,
                 rng.uniform(0.14, 0.26) * radio) for _ in range(rng.randint(2, 4))]
    for y in range(lado):
        for x in range(lado):
            if not mascara[y][x]:
                continue
            borde = any(not (0 <= x + dx < lado and 0 <= y + dy < lado and mascara[y + dy][x + dx])
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if borde:
                arte.set_at((x, y), contorno)
                continue
            dx, dy = (x + 0.5 - c) / radio, (y + 0.5 - c) / radio
            luz_k = -(dx * 0.62 + dy * 0.78) + 0.25 * (1 - dx * dx - dy * dy)
            umbral = (_BAYER[y % 4][x % 4] / 16.0 - 0.5) * 0.28
            for cx, cy, cr in crateres:
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if d < cr:
                    # hueco: oscuro arriba a la izquierda, borde claro abajo a la derecha
                    luz_k = -0.6 if (x - cx) + (y - cy) < cr * 0.4 else 0.55
            v = luz_k + umbral
            color = brillo if v > 0.62 else luz if v > 0.22 else medio if v > -0.28 else sombra
            arte.set_at((x, y), color)

    def pintar(x, y, color):
        x, y = int(x), int(y)
        if 0 <= x < lado and 0 <= y < lado and mascara[y][x]:
            arte.set_at((x, y), color)

    # vetas de energia: caminatas cortas desde adentro
    for _ in range(rng.randint(1, 2) + (1 if radio > 9 else 0)):
        x, y = c + rng.uniform(-0.4, 0.4) * radio, c + rng.uniform(-0.4, 0.4) * radio
        a = rng.uniform(0, 2 * math.pi)
        for paso in range(rng.randint(3, 3 + radio // 2)):
            pintar(x, y, veta_luz if rajada and paso % 2 == 0 else veta)
            a += rng.uniform(-0.7, 0.7)
            x += math.cos(a)
            y += math.sin(a)
    if rajada:
        # grietas encendidas que cruzan la roca desde el centro
        for _ in range(3):
            x, y = c, c
            a = rng.uniform(0, 2 * math.pi)
            while 0 <= x < lado and 0 <= y < lado:
                pintar(x, y, veta_luz)
                pintar(x + 1, y, veta)
                a += rng.uniform(-0.5, 0.5)
                x += math.cos(a)
                y += math.sin(a)
    else:
        # destellito de luz arriba a la izquierda
        pintar(c - radio * 0.45, c - radio * 0.5, (255, 255, 255))
        pintar(c - radio * 0.45 + 1, c - radio * 0.5, brillo)

    _CACHE_ROCAS[clave] = arte
    return arte


class Asteroid:
    """Roca pixel art que cae desde arriba del area de juego.

    vida: golpes que aguanta. Las de las oleadas salen con 2: el primer
    golpe la raja (grietas neon encendidas, pedazo saltado) y el segundo la
    rompe en dos fragmentos de 1 golpe que salen despedidos a los costados
    (ver fragmentos()). Los meteoros de los jefes usan el valor por defecto
    (1 golpe, sin dividirse)."""

    def __init__(self, x, y, size=25, vida=1, tipo=None, fragmento=False):
        self.x = x
        self.y = y
        self.size = size
        self.speed = random.uniform(2.0, 5.0)
        self.vx = 0.0
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-2.2, 2.2)
        self.active = True
        self.vida = vida
        self.vida_max = vida
        self.fragmento = fragmento
        self.tipo = tipo or random.choice(_TIPOS_ROCA)
        self.variant = random.randrange(VARIANTES_ROCA)
        self.flash_timer = 0
        self.temblor = 0
        self.glow_phase = random.uniform(0, math.pi * 2)

    @property
    def color(self):
        """Color de la veta (para chispas y explosiones)."""
        return PALETAS_ROCA[self.tipo][5]

    @property
    def rajada(self):
        return self.vida < self.vida_max

    def take_damage(self, amount=1):
        """Resta vida; True si la roca se rompe con este golpe."""
        self.vida -= max(1, int(amount))
        self.flash_timer = 6
        if self.vida <= 0:
            self.active = False
            return True
        self.temblor = 8
        return False

    def fragmentos(self):
        """Los dos pedazos de 1 golpe en que se parte una roca de las
        oleadas al romperse (una que ya es fragmento no se divide mas)."""
        if self.fragmento or self.vida_max < 2:
            return []
        tam = max(14, int(self.size * 0.6))
        pedazos = []
        for lado in (-1, 1):
            p = Asteroid(self.x + lado * tam * 0.6, self.y, tam, vida=1, tipo=self.tipo, fragmento=True)
            p.vx = lado * random.uniform(1.4, 2.4)
            p.speed = max(2.0, self.speed * random.uniform(0.9, 1.15))
            p.rot_speed = lado * random.uniform(3, 5)
            pedazos.append(p)
        return pedazos

    def update(self):
        self.y += self.speed
        self.x += self.vx
        self.vx *= 0.99
        self.rotation = (self.rotation + self.rot_speed) % 360
        self.glow_phase += 0.06
        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.temblor > 0:
            self.temblor -= 1
        if self.y > GAME_HEIGHT + self.size + 20 or not (-self.size - 40 < self.x < GAME_WIDTH + self.size + 40):
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x + (random.randint(-2, 2) if self.temblor else 0)
        cy = int(self.y) + offset_y

        radio = max(4, round(self.size * 1.1 / PIXEL_ROCA))
        arte = _arte_roca(self.variant, radio, self.tipo, self.rajada)
        if self.flash_timer > 0:
            arte = pixelfx.silueta_blanca(arte)
        # se gira el arte chico (a pasos de 15 grados) y recien despues se
        # agranda sin filtrado: los pixeles quedan cuadrados y del mismo tamaño
        girado = pygame.transform.rotate(arte, -(int(self.rotation) // 15) * 15)
        grande = pygame.transform.scale(girado, (girado.get_width() * PIXEL_ROCA, girado.get_height() * PIXEL_ROCA))
        if self.rajada:
            # las grietas laten con un halo del color de la veta
            pulso = round(2 + 2 * math.sin(self.glow_phase * 3)) / 4
            pixelfx.dibujar_halo(screen, pixelfx.apagar(self.color, 0.25 + 0.25 * pulso), cx, cy, int(self.size * 1.3))
        screen.blit(grande, (cx - grande.get_width() // 2, cy - grande.get_height() // 2))


FUEGO = (255, 150, 50)
HUMO = (70, 64, 84)


def _mezcla(a, b, f):
    return tuple(int(x + (y - x) * f) for x, y in zip(a[:3], b[:3]))


class Particle:
    """Chispa pixel: sale disparada dejando una estela corta, frena de a
    poco, titila y pasa de blanco a su color y despues a oscuro."""

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        ang = random.uniform(0, 2 * math.pi)
        vel = random.uniform(0.6, 4.6)
        self.vx = math.cos(ang) * vel
        self.vy = math.sin(ang) * vel
        self.life = random.randint(15, 40)
        self.max_life = self.life
        self.radius = random.randint(1, 4)
        self.color = tuple(color[:3])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= 1

    def draw(self, screen, offset_x=0, offset_y=0):
        if self.life <= 0:
            return
        k = self.life / self.max_life
        lado = 2 * max(1, round(self.radius * (0.4 + 0.6 * k)))
        x, y = int(self.x) + offset_x, int(self.y) + offset_y
        color = pixelfx.apagar(self.color, k)
        if self.life % 7 == 0 and k < 0.6:
            color = pixelfx.aclarar(color, 0.6)      # titila
        # estela: dos cuadraditos mas chicos hacia atras
        for paso in (2, 1):
            c = tuple(v * (3 - paso) // 4 for v in color)
            l2 = max(2, lado - paso * 2)
            screen.fill(c, (int(x - self.vx * paso * 1.6) - l2 // 2, int(y - self.vy * paso * 1.6) - l2 // 2, l2, l2))
        screen.fill(color, (x - lado // 2, y - lado // 2, lado, lado))


class Explosion:
    """Explosion pixel neon en capas: destello con rayos, bolas de fuego
    que se inflan y se apagan (las grandes encadenan explosiones
    secundarias), onda de choque doble, chispas con estela, escombros,
    humo que sube y brasas. count es el tamaño: 8 es un chispazo, 100 o
    mas una explosion de jefe. active pasa a False cuando ya no queda
    nada en pantalla."""

    def __init__(self, x, y, color=MELON, count=20):
        self.x, self.y = x, y
        self.color = tuple(color[:3])
        self.radio = min(70, 6 + count * 0.45)
        r = self.radio
        self.t = 0
        self.dur_onda = 12 + int(r / 4)
        self.particles = [Particle(x, y, color) for _ in range(max(4, count // 2))]
        for p in self.particles:
            f = 0.7 + r / 35
            p.vx *= f
            p.vy *= f
        # bolas de fuego: la central y otras alrededor, algunas con retraso
        self.bolas = [{'x': x, 'y': y, 'r': r * 0.75, 'retraso': 0, 'dur': 14 + int(r / 3)}]
        for i in range(2 + int(r / 9)):
            a = random.uniform(0, 2 * math.pi)
            d = random.uniform(0.3, 1.0) * r
            self.bolas.append({'x': x + math.cos(a) * d, 'y': y + math.sin(a) * d,
                               'r': random.uniform(0.3, 0.55) * r,
                               'retraso': random.randint(1, 4 + int(r / 5)),
                               'dur': random.randint(10, 16 + int(r / 4))})
        # escombros: pedazos grandes que giran y se van frenando
        self.escombros = []
        for _ in range(int(r / 6)):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(1.5, 3.5 + r / 20)
            self.escombros.append([x, y, math.cos(a) * v, math.sin(a) * v, random.randint(24, 44)])
        # humo y brasas
        self.humo = []
        self.brasas = [[x + random.uniform(-r, r) * 0.6, y + random.uniform(-r, r) * 0.6,
                        random.uniform(-0.4, 0.4), random.uniform(-1.2, -0.3), random.randint(30, 60)]
                       for _ in range(int(r / 5))]
        self.active = True

    def update(self):
        self.t += 1
        vivo = self.t <= self.dur_onda
        for p in self.particles:
            if p.life > 0:
                p.update()
                vivo = True
        for b in self.bolas:
            if self.t == b['retraso'] + b['dur'] - 4 and len(self.humo) < 14:
                self.humo.append([b['x'], b['y'], b['r'] * 0.5, 40])
            if self.t < b['retraso'] + b['dur']:
                vivo = True
        for e in self.escombros:
            if e[4] > 0:
                e[0] += e[2]
                e[1] += e[3]
                e[2] *= 0.96
                e[3] = e[3] * 0.96 + 0.05
                e[4] -= 1
                vivo = True
        for h in self.humo:
            if h[3] > 0:
                h[1] -= 0.45
                h[2] += 0.35
                h[3] -= 1
                vivo = True
        for b in self.brasas:
            if b[4] > 0:
                b[0] += b[2] + math.sin((self.t + b[4]) * 0.3) * 0.3
                b[1] += b[3]
                b[4] -= 1
                vivo = True
        if not vivo:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        ox, oy = offset_x, offset_y
        x, y = int(self.x) + ox, int(self.y) + oy
        r = self.radio
        # humo (detras de todo)
        for hx, hy, hr, vida in self.humo:
            if vida > 0:
                k = vida / 40
                c = _mezcla((14, 10, 24), HUMO, k)
                d = pixelfx.disco(c, hr)
                screen.blit(d, (int(hx) + ox - d.get_width() // 2, int(hy) + oy - d.get_height() // 2))
        # destello con rayos en cruz
        if self.t <= 5:
            k = self.t / 5
            pixelfx.dibujar_halo(screen, pixelfx.aclarar(self.color, 0.5), x, y, r * (2.4 - k))
            largo = int(r * (2.2 - 1.6 * k))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for i in range(0, largo, 4):
                    lado = 6 if i < largo * 0.4 else 4 if i < largo * 0.75 else 2
                    screen.fill((255, 255, 255), (x + dx * i - lado // 2, y + dy * i - lado // 2, lado, lado))
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                for i in range(0, largo // 2, 4):
                    screen.fill(pixelfx.aclarar(self.color, 0.6), (x + dx * i - 2, y + dy * i - 2, 4, 4))
        # bolas de fuego: blanco -> amarillo -> color -> rojo oscuro
        for b in self.bolas:
            t = self.t - b['retraso']
            if not 0 <= t < b['dur']:
                continue
            k = t / b['dur']
            radio = b['r'] * (0.5 + 1.2 * k if k < 0.35 else 0.92 - 0.5 * (k - 0.35))
            if k < 0.15:
                c_ext, c_int = (255, 255, 255), (255, 255, 255)
            elif k < 0.45:
                c_ext, c_int = _mezcla(FUEGO, self.color, 0.4), (255, 240, 170)
            elif k < 0.75:
                c_ext, c_int = _mezcla(self.color, (150, 30, 40), 0.5), _mezcla(FUEGO, self.color, 0.5)
            else:
                c_ext, c_int = (70, 20, 34), (130, 36, 44)
            bx, by = int(b['x']) + ox, int(b['y']) + oy
            if k < 0.5:
                pixelfx.dibujar_halo(screen, c_ext, bx, by, radio * 1.5)
            d = pixelfx.disco(c_ext, radio)
            screen.blit(d, (bx - d.get_width() // 2, by - d.get_height() // 2))
            d = pixelfx.disco(c_int, radio * 0.6)
            screen.blit(d, (bx - d.get_width() // 2 - 2, by - d.get_height() // 2 - 2))
        # onda de choque doble
        if self.t <= self.dur_onda:
            k = self.t / self.dur_onda
            for f, lado0, brillo in ((1.0, 6, 1.0), (0.72, 4, 0.55)):
                rr = r * (0.6 + 1.7 * k) * f
                n = max(12, int(rr * 0.7))
                lado = max(2, int(lado0 * (1 - k)) // 2 * 2)
                color = pixelfx.apagar(self.color, (1 - k) * brillo)
                for i in range(n):
                    a = 2 * math.pi * i / n
                    screen.fill(color, (int(x + math.cos(a) * rr) - lado // 2,
                                        int(y + math.sin(a) * rr) - lado // 2, lado, lado))
        # escombros
        for ex, ey, vx, vy, vida in self.escombros:
            if vida > 0:
                c = pixelfx.apagar(_mezcla(self.color, (120, 110, 130), 0.5), min(1.0, vida / 30))
                screen.fill(pixelfx.CONTORNO, (int(ex) + ox - 4, int(ey) + oy - 4, 8, 8))
                screen.fill(c, (int(ex) + ox - 3, int(ey) + oy - 3, 6, 6))
                screen.fill(pixelfx.aclarar(c, 0.5), (int(ex) + ox - 3, int(ey) + oy - 3, 2, 2))
                if vida % 3 == 0:
                    screen.fill(FUEGO, (int(ex - vx * 3) + ox - 1, int(ey - vy * 3) + oy - 1, 2, 2))
        for p in self.particles:
            p.draw(screen, offset_x, offset_y)
        # brasas que suben titilando
        for bx, by, _, _, vida in self.brasas:
            if vida > 0 and self.t > 6 and (vida // 3) % 3:
                screen.fill(_mezcla(FUEGO, (255, 240, 170), (vida % 5) / 5),
                            (int(bx) + ox - 1, int(by) + oy - 1, 2, 2))
