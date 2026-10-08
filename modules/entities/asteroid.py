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


class Particle:
    """Chispa pixel: un cuadradito que sale disparado, frena de a poco y
    pasa de blanco a su color y despues a oscuro. Explosion agrupa varias."""

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        ang = random.uniform(0, 2 * math.pi)
        vel = random.uniform(0.6, 4.2)
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
        screen.fill(pixelfx.apagar(self.color, k),
                    (int(self.x) + offset_x - lado // 2, int(self.y) + offset_y - lado // 2, lado, lado))


class Explosion:
    """Explosion pixel neon: destello blanco, onda de choque en cuadraditos
    que se abre y se apaga, y chispas (Particle) que salen volando. count
    es el tamaño: 8 es un chispazo, 100 o mas una explosion de jefe.
    active pasa a False cuando ya no queda nada en pantalla."""

    def __init__(self, x, y, color=MELON, count=20):
        self.x, self.y = x, y
        self.color = tuple(color[:3])
        self.radio = min(70, 6 + count * 0.45)
        self.particles = [Particle(x, y, color) for _ in range(max(4, count // 2))]
        for p in self.particles:
            # las chispas grandes vuelan mas lejos
            f = 0.6 + self.radio / 40
            p.vx *= f
            p.vy *= f
        self.t = 0
        self.dur_onda = 10 + int(self.radio / 4)
        self.active = True

    def update(self):
        self.t += 1
        vivas = False
        for p in self.particles:
            if p.life > 0:
                p.update()
                vivas = True
        if not vivas and self.t > self.dur_onda:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        x, y = int(self.x) + offset_x, int(self.y) + offset_y
        if self.t <= self.dur_onda:
            k = self.t / self.dur_onda
            # destello: nucleo blanco que se achica rapido
            if k < 0.45:
                r = self.radio * (0.9 - k)
                pixelfx.dibujar_halo(screen, self.color, x, y, self.radio * 1.6 * (1 - k))
                nucleo = pixelfx.disco(pixelfx.aclarar(self.color, 0.5), r)
                screen.blit(nucleo, (x - nucleo.get_width() // 2, y - nucleo.get_height() // 2))
                blanco = pixelfx.disco((255, 255, 255), r * 0.6)
                screen.blit(blanco, (x - blanco.get_width() // 2, y - blanco.get_height() // 2))
            # onda de choque
            r = self.radio * (0.5 + 1.3 * k)
            n = max(10, int(r * 0.7))
            lado = 6 if k < 0.4 else 4 if k < 0.75 else 2
            color = pixelfx.apagar(self.color, 1 - k)
            for i in range(n):
                a = 2 * math.pi * i / n
                screen.fill(color, (int(x + math.cos(a) * r) - lado // 2, int(y + math.sin(a) * r) - lado // 2,
                                    lado, lado))
        for p in self.particles:
            p.draw(screen, offset_x, offset_y)
