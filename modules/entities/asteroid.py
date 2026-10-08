"""
Asteroides y los efectos visuales de particulas que usa todo el juego
(Particle/Explosion las reutilizan bosses, enemigos y power-ups, no solo
los asteroides)."""

import random
import math
from modules.constants import MELON, GAME_HEIGHT
from modules.systems import pixelfx, sprites


# Paleta de roca: pocos tonos para que el cache de sprites se reutilice
ROCK_TINTS = [
    (196, 172, 146),
    (168, 150, 138),
    (150, 132, 116),
    (186, 182, 178),
    (140, 152, 164),
]


class Asteroid:
    """Roca que cae desde arriba del area de juego. Usa uno de los 14
    sprites generados por tools/generate_sprites.py (tintado y rotado)."""

    def __init__(self, x, y, size=25):
        self.x = x
        self.y = y
        self.size = size
        self.speed = random.uniform(2.0, 5.0)
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-2.2, 2.2)
        self.active = True
        self.variant = random.randrange(sprites.ASTEROID_VARIANTS)
        self.color = random.choice(ROCK_TINTS)
        self.dark_color = tuple(max(0, c - 35) for c in self.color)
        self.light_color = tuple(min(255, c + 35) for c in self.color)
        self.flash_timer = 0
        self.glow_phase = random.uniform(0, math.pi * 2)
        self._sprite_key = ("rock", self.variant, self.size, self.color)

    def update(self):
        self.y += self.speed
        self.rotation = (self.rotation + self.rot_speed) % 360
        self.glow_phase += 0.06
        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.y > GAME_HEIGHT + self.size + 20:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        hit = self.flash_timer > 0
        tint = (255, 255, 255) if hit else self.color
        sprite = sprites.get_asteroid_surface(self.variant, self.size, tint)

        if sprite is not None:
            key = self._sprite_key + (hit,)
            rotated = sprites.get_rotated(sprite, self.rotation, key)
            sprites.blit_centered(screen, rotated, cx, cy)
        # Sin PNG en assets/sprites/asteroids no se dibuja una roca de
        # respaldo por codigo: simplemente no se ve hasta que se regeneren
        # los sprites.


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
