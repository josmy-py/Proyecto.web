"""
Naves alienigenas comunes (no jefes): aparecen desde la oleada 2, entran por
un costado o por arriba y disparan balas hacia la nave del jugador. Los
jefes de oleada viven en modules/core/boss_system.py y modules/entities/boss.py,
no en este archivo.
"""

import pygame
import random
import math
from modules.constants import (
    MELON, AMARILLO,
    GAME_WIDTH, GAME_HEIGHT, SHIP_WIDTH, SHIP_HEIGHT,
)
from modules.systems import sprites, pixelfx
from modules.skins import get_available_skins, get_skin_colors


# Colores neon de los enemigos comunes: rojo, naranja, violeta y verde
# acido, lejos del azul/magenta de la nave del jugador para leerlos rapido.
COLORES_ENEMIGO = [(255, 70, 90), (255, 150, 40), (180, 90, 255), (120, 255, 90)]

# Modelos de dibujo de cada enemigo comun (ver ENEMIES y PLATILLOS en
# tools/generate_pixel_sprites.py): cada nave sortea uno al aparecer.
MODELOS_PLATILLO = ("drone", "drone_b", "drone_c", "drone_d")
MODELOS_ENEMIGO = {
    "fighter": ("fighter", "fighter_b", "fighter_c"),
    "drone": MODELOS_PLATILLO,
    "gunner": ("gunner", "gunner_b", "gunner_c"),
}

# Variantes de nave enemiga comun (sprites en assets/sprites/enemies).
# Mueren de un solo golpe, sin hp propio (ver AlienShip.take_damage).
ENEMY_VARIANTS = {
    "fighter": {"size": 18, "speed": (1.2, 2.6), "rate": (55, 150)},
    "drone": {"size": 20, "speed": (0.8, 1.7), "rate": (70, 180)},
    "gunner": {"size": 19, "speed": (0.9, 1.9), "rate": (45, 120)},
}

# Naves bonus: reciclan los sprites de la nave del jugador (assets/sprites/
# ships/tank, interceptor, bomber -> ver modules/systems/sprites.py) que
# quedaron sin uso al eliminarse la seleccion de clase de nave. Son
# infrecuentes, mas grandes que un enemigo comun, aguantan varios golpes
# (ver "hp") y cada una dispara distinto (ver AlienShip._crear_disparo):
# tank = trebolada de tres disparos amplios, interceptor = un solo tiro
# rapido apuntado, bomber = un proyectil pesado y lento. Sueltan varios
# power-ups de golpe en vez de uno solo al morir (ver BONUS_SHIP_* en
# modules/constants.py y su uso en main.py).
BONUS_SHIP_KINDS = ("tank", "interceptor", "bomber")
BONUS_SHIP_VARIANTS = {
    "tank": {"size": 30, "speed": (0.6, 1.0), "rate": (85, 150), "hp": 4},
    "interceptor": {"size": 24, "speed": (1.8, 2.8), "rate": (55, 110), "hp": 2},
    "bomber": {"size": 32, "speed": (0.55, 0.9), "rate": (100, 170), "hp": 3},
}

# Mini-jefe (ver BONUS_SHIP_MINIBOSS_CHANCE en modules/constants.py): la
# nave bonus que le toca se agranda, se pone mucho mas dura y ademas de
# su disparo normal larga salvas de misiles con homing suave (ver
# AlienMissile/_crear_misiles) - una nave de combate real, no un blanco
# facil mas grande.
MINIBOSS_SIZE_MULT = 1.85
MINIBOSS_HP_MULT = 3.5
MINIBOSS_MISIL_RATE = (150, 210)
MINIBOSS_MISILES_POR_SALVA = 3


class AlienShip:
    """Nave enemiga. Entra por 'left', 'right' o 'top', avanza hacia el lado
    opuesto y dispara segun su variante a intervalos aleatorios. Las
    variantes fighter/drone/gunner (ver ENEMY_VARIANTS) son el enemigo
    comun, mueren de un golpe; tank/interceptor/bomber (ver
    BONUS_SHIP_VARIANTS) son la nave bonus infrecuente -con hp propio y
    patron de disparo unico cada una- que reutiliza los sprites de
    assets/sprites/ships, y opcionalmente se activa como mini-jefe (ver
    miniboss/is_miniboss)."""

    def __init__(self, side="left", variant=None, miniboss=False):
        self.side = side
        self.is_bonus = variant in BONUS_SHIP_VARIANTS
        self.is_miniboss = bool(miniboss) and self.is_bonus
        if self.is_bonus:
            self.variant = variant
            cfg = BONUS_SHIP_VARIANTS[self.variant]
            skin_id = random.choice(list(get_available_skins(self.variant).keys()))
            body_color, wing_color, glow_color, _flame_color = get_skin_colors(self.variant, skin_id)
            self.color = body_color
            self.wing_color = wing_color
            self.glow_color = glow_color
            self.max_hp = cfg["hp"]
            if self.is_miniboss:
                self.max_hp = max(cfg["hp"] + 1, int(round(cfg["hp"] * MINIBOSS_HP_MULT)))
        else:
            self.variant = variant or random.choice(list(ENEMY_VARIANTS.keys()))
            cfg = ENEMY_VARIANTS[self.variant]
            self.color = random.choice(COLORES_ENEMIGO)
            self.wing_color = tuple(int(c * 0.62) for c in self.color[:3])
            self.glow_color = None
            self.max_hp = 1
            self.diseno = random.choice(MODELOS_ENEMIGO[self.variant])
            if self.variant == "drone":
                # los platillos giran sobre si mismos
                self.giro = random.uniform(1.4, 3.2) * random.choice((-1, 1))
        self.hp = self.max_hp
        self.hit_flash = 0
        self.size = cfg["size"] * (MINIBOSS_SIZE_MULT if self.is_miniboss else 1.0)
        self.x = random.randint(40, GAME_WIDTH - 40)
        self.y = random.randint(-80, -20) if side == "top" else (0 if side == "left" else GAME_WIDTH)
        self.speed = random.uniform(*cfg["speed"]) * (0.82 if self.is_miniboss else 1.0)
        self.vertical_speed = random.uniform(0.8, 1.8)
        self.active = True
        self.shoot_timer = random.randint(30, 120)
        self.shoot_rate = random.randint(*cfg["rate"])
        self.wave = 0
        self.glow_phase = random.uniform(0, math.pi * 2)
        # balanceo suave en vez de girar sobre si misma
        self.bank_phase = random.uniform(0, math.pi * 2)
        self.rotation = 0.0
        self.rot_speed = 0.0
        self.diseno = getattr(self, "diseno", self.variant)
        self._sprite_key = ("enemy", self.diseno, self.color, self.size)

        self.misil_timer = random.randint(*MINIBOSS_MISIL_RATE) if self.is_miniboss else 0

    def update(self, ship=None):
        """Avanza segun el lado de entrada, actualiza el balanceo visual y
        dispara cuando el temporizador llega a cero. Devuelve la lista de
        proyectiles creados este frame (puede estar vacia). Se marca
        inactiva al salir del area de juego."""
        if self.side == "left":
            self.x += self.speed
            self.y += self.vertical_speed * 0.5
        elif self.side == "right":
            self.x -= self.speed
            self.y += self.vertical_speed * 0.5
        else:
            self.y += self.vertical_speed

        self.bank_phase += 0.05
        base_tilt = 12.0 if self.side == "right" else (-12.0 if self.side == "left" else 0.0)
        if self.variant == "drone":
            self.rotation = (self.rotation + self.giro) % 360
        else:
            self.rotation = base_tilt + math.sin(self.bank_phase) * 7.0
        self.wave += 1
        self.glow_phase += 0.12
        self.hit_flash = max(0, self.hit_flash - 1)

        proyectiles = []
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_rate
            proyectiles.extend(self._crear_disparo(ship))

        if self.is_miniboss:
            self.misil_timer -= 1
            if self.misil_timer <= 0:
                self.misil_timer = random.randint(*MINIBOSS_MISIL_RATE)
                proyectiles.extend(self._crear_misiles(ship))

        if self.y > GAME_HEIGHT + 30 or self.x < -40 or self.x > GAME_WIDTH + 40:
            self.active = False

        return proyectiles

    def take_damage(self, amount=1):
        """Devuelve True si el golpe la destruye. Los enemigos comunes
        tienen hp=1 (mueren siempre de un golpe, sin cambiar nada para
        ellos); las naves bonus aguantan varios segun BONUS_SHIP_VARIANTS
        (mas si son mini-jefe, ver MINIBOSS_HP_MULT)."""
        self.hp -= amount
        self.hit_flash = 7
        if self.hp <= 0:
            self.active = False
            return True
        return False

    def _crear_disparo(self, ship):
        if not self.is_bonus:
            return [self._create_bullet()]
        if self.variant == "tank":
            return self._disparo_tank(ship)
        if self.variant == "interceptor":
            return self._disparo_interceptor(ship)
        return self._disparo_bomber(ship)

    def _create_bullet(self):
        return AlienBullet(self.x, self.y + self.size, self.side, color=self.color)

    def _disparo_tank(self, ship):
        """Tank: trebolada de tres disparos amplios -suprime una zona en
        vez de apuntar con precision, hace falta mantenerse en movimiento."""
        base_angle = math.atan2(ship.y - self.y, ship.x - self.x) if ship is not None else math.pi / 2
        balas = []
        for i in (-1, 0, 1):
            angle = base_angle + i * 0.24
            speed = 3.1
            balas.append(AlienBullet(self.x, self.y, self.side, color=self.color,
                                      vx=math.cos(angle) * speed, vy=math.sin(angle) * speed, radius=4))
        return balas

    def _disparo_interceptor(self, ship):
        """Interceptor: un solo tiro rapido apuntado directo a la nave -
        hit-and-run, poca cadencia de balas pero certera."""
        if ship is None:
            return [self._create_bullet()]
        angle = math.atan2(ship.y - self.y, ship.x - self.x)
        speed = 6.2
        return [AlienBullet(self.x, self.y, self.side, color=self.color,
                             vx=math.cos(angle) * speed, vy=math.sin(angle) * speed, radius=4)]

    def _disparo_bomber(self, ship):
        """Bomber: un unico proyectil pesado y lento (mas radio, mas
        facil de esquivar si no te quedas quieto, pero pega fuerte)."""
        base_angle = math.atan2(ship.y - self.y, ship.x - self.x) if ship is not None else math.pi / 2
        angle = base_angle + random.uniform(-0.1, 0.1)
        speed = 2.5
        return [AlienBullet(self.x, self.y, self.side, color=self.color,
                             vx=math.cos(angle) * speed, vy=math.sin(angle) * speed, radius=6)]

    def _crear_misiles(self, ship):
        """Mini-jefe: salva de misiles con homing suave (ver
        AlienMissile) ademas de su disparo normal - lo que lo hace sentir
        una nave de combate real, no solo una version grande del bonus."""
        if ship is None:
            return []
        misiles = []
        n = MINIBOSS_MISILES_POR_SALVA
        base_angle = math.atan2(ship.y - self.y, ship.x - self.x)
        for i in range(n):
            angle = base_angle + (i - (n - 1) / 2.0) * 0.3
            speed = 3.0
            misiles.append(AlienMissile(self.x, self.y, math.cos(angle) * speed, math.sin(angle) * speed, ship))
        return misiles

    def draw(self, screen, offset_x=0, offset_y=0):
        """Dibuja el sprite tintado de la variante (o el poligono de
        respaldo si faltan los PNG de assets/sprites). Las bonus (tank/
        interceptor/bomber) usan los sprites de assets/sprites/ships y una
        aureola pulsante que las distingue de un vistazo del enemigo comun
        -roja/de alerta en vez de dorada si es mini-jefe-, mas una fila de
        pips de vida si aguantan mas de un golpe y un flash blanco al
        recibir daño sin morir."""
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        if self.is_bonus:
            pulse = 0.5 + 0.5 * math.sin(self.glow_phase)
            glow_r = int(self.size * (2.4 if self.is_miniboss else 2.1))
            glow_color = (255, 90, 70) if self.is_miniboss else AMARILLO
            k = (0.55 if self.is_miniboss else 0.4) * (0.6 + 0.4 * pulse)
            pixelfx.dibujar_halo(screen, tuple(int(c * k) for c in glow_color[:3]), cx, cy, glow_r)

            width = int(self.size * 2.4)
            height = int(width * SHIP_HEIGHT / SHIP_WIDTH)
            if sprites.es_nave_pixel(self.variant):
                # agrandado en multiplos enteros para no deformar los pixeles
                escala = max(2, round(width / SHIP_WIDTH))
                width, height = sprites.tamano_pixel("ships", self.variant, escala)
            sprite = sprites.get_ship_surface(self.variant, self.color, self.wing_color, width, height)
        else:
            sprite = sprites.get_enemy_surface(self.diseno, self.color, self.wing_color, self.size)

        if self.variant == "drone" and not self.is_bonus:
            girado = sprites.get_enemy_surface_girado(
                self.diseno, self.color, self.wing_color, self.size, self.rotation)
            sprites.blit_centered(screen, girado, cx, cy)
        elif sprite is not None:
            # Los PNG de assets/sprites/ships tienen el morro hacia ARRIBA
            # (mismo criterio que la nave del jugador); los de
            # assets/sprites/enemies ya vienen dibujados apuntando hacia
            # ABAJO, mirando al jugador (ver enemy_geometry() en
            # tools/generate_sprites.py). Sin este giro de 180 grados la nave
            # bonus quedaria mirando para el lado contrario a todo enemigo.
            angle = self.rotation + 180 if self.is_bonus else self.rotation
            rotated = sprites.get_rotated(sprite, angle, self._sprite_key)
            sprites.blit_centered(screen, rotated, cx, cy)
        # Sin PNG en assets/sprites/enemies (o assets/sprites/ships para las
        # bonus) no se dibuja una silueta de respaldo por codigo: la nave
        # simplemente no se ve hasta que se regeneren los sprites.

        if self.hit_flash > 0:
            alpha = int(180 * (self.hit_flash / 7))
            flash_r = int(self.size * 1.1)
            flash_surf = pygame.Surface((flash_r * 2, flash_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 255, alpha), (flash_r, flash_r), flash_r)
            screen.blit(flash_surf, (cx - flash_r, cy - flash_r))

        if self.is_bonus and self.max_hp > 1:
            pip_r = 4
            total_w = self.max_hp * (pip_r * 2 + 3) - 3
            px0 = cx - total_w // 2
            py = cy - int(self.size * (1.7 if self.is_miniboss else 1.5))
            for i in range(self.max_hp):
                px = px0 + i * (pip_r * 2 + 3) + pip_r
                lleno = i < self.hp
                color = (255, 90, 70) if self.is_miniboss else AMARILLO
                pygame.draw.circle(screen, color if lleno else (40, 40, 50), (px, py), pip_r)
                pygame.draw.circle(screen, (15, 15, 20), (px, py), pip_r, 1)


class AlienBullet:
    """Bala disparada por un AlienShip. Por defecto viaja en linea recta
    segun el lado de origen (horizontal si vino de un costado, vertical si
    vino de arriba, comportamiento original de los enemigos comunes); si
    se le da vx/vy explicitos (naves bonus, ver AlienShip._crear_disparo)
    viaja en esa direccion libre en vez de la del lado de entrada."""

    def __init__(self, x, y, side, color=None, vx=None, vy=None, radius=3):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = tuple(color[:3]) if color else MELON
        self.side = side
        if vx is not None or vy is not None:
            self._libre = True
            self.vx = vx or 0.0
            self.vy = vy or 0.0
        else:
            self._libre = False
            self.speed = 4.0 if side == "left" else -4.0 if side == "right" else 4.0
        self.active = True

    def update(self):
        if self._libre:
            self.x += self.vx
            self.y += self.vy
        elif self.side == "left":
            self.x += self.speed
        elif self.side == "right":
            self.x += self.speed
        else:
            self.y += self.speed
        if self.y > GAME_HEIGHT + 10 or self.y < -10 or self.x < -10 or self.x > GAME_WIDTH + 10:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        pixelfx.dibujar_halo(screen, self.color, cx, cy, self.radius * 2.5 + 5)
        self._fase = getattr(self, "_fase", 0) + 1
        sprite = pixelfx.bala_enemiga(self.color, self.radius, (self._fase // 6) % 2)
        screen.blit(sprite, (cx - sprite.get_width() // 2, cy - sprite.get_height() // 2))


class AlienMissile:
    """Misil de homing suave disparado por una nave bonus activada como
    mini-jefe (ver AlienShip.is_miniboss/_crear_misiles). Guarda una
    referencia directa a la nave del jugador y gira gradualmente hacia
    ella cada frame -el giro esta acotado (giro_max), no es un tracking
    perfecto, asi que moverse de verdad todavia sirve para esquivarlo-
    ademas de una estela de propulsion. Duck-typed igual que AlienBullet
    (x, y, radius, active, update(), draw()) para sumarse a alien_bullets
    sin tocar main.py."""

    def __init__(self, x, y, vx, vy, ship, radius=5, vida=260):
        self.x = x
        self.y = y
        self.radius = radius
        self._ship = ship
        self.angle = math.atan2(vy, vx)
        self.speed = math.hypot(vx, vy) or 3.0
        self.giro_max = 0.045
        self.active = True
        self.vida = vida
        self.trail = []

    def update(self):
        if self._ship is not None:
            objetivo = math.atan2(self._ship.y - self.y, self._ship.x - self.x)
            diff = (objetivo - self.angle + math.pi) % (2 * math.pi) - math.pi
            self.angle += max(-self.giro_max, min(self.giro_max, diff))
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.vida -= 1
        if self.vida <= 0 or self.y > GAME_HEIGHT + 20 or self.y < -20 or self.x < -20 or self.x > GAME_WIDTH + 20:
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        # humo detras
        for i, (tx, ty) in enumerate(self.trail[:-2]):
            k = (i + 1) / len(self.trail)
            gris = int(50 + 70 * k)
            lado = 2 if k < 0.5 else 4
            screen.fill((gris, gris - 6, gris + 18),
                        (int(tx) + offset_x - lado // 2, int(ty) + offset_y - lado // 2, lado, lado))
        pixelfx.misil(screen, self.x + offset_x, self.y + offset_y, self.angle, self.vida,
                      cuerpo=(176, 130, 230), largo=5)
