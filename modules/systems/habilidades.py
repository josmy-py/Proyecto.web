"""
Habilidades de las cartas de mejora que tienen comportamiento propio
durante la partida (las demas solo cambian numeros de la nave, ver
mejoras.EstadoMejoras.aplicar):

  - MISILES: cada tanto sale un misil que persigue al enemigo mas cercano.
  - CRITICO: algunas balas salen doradas y pegan triple a los jefes.
  - NOVA: cuando una bala enemiga se acerca, una onda la borra (con recarga).
  - ORBITA: esferas que giran alrededor de la nave, frenan balas y rompen rocas.
  - RECOLECTOR: cada tantos enemigos destruidos recuperas una vida.
  - FENIX: la primera vez que caes, renaces (ver Ship.take_damage).

main.py llama a actualizar() una vez por cuadro de juego activo y a
dibujar() despues de la nave."""

import math
import random

from modules.constants import WHITE
from modules.entities.bullet import Bullet
from modules.systems import pixelfx, neon

ORO = (255, 210, 70)
NOVA = (150, 230, 255)
ORBITA = (190, 140, 255)

PROB_CRITICO = (0.0, 0.12, 0.2, 0.28)     # por nivel
RECARGA_MISIL = (0, 80, 55)               # cuadros entre misiles, por nivel
RECARGA_NOVA = (0, 420, 270)
RADIO_NOVA = 170
BAJAS_RECOLECTOR = (0, 30, 20)
RADIO_ORBITA = 52


class MisilJugador(Bullet):
    """Bala que gira hacia el blanco mas cercano (rocas, naves o jefes) y
    pega como tres balas a los jefes."""

    def __init__(self, x, y, angulo, blancos):
        super().__init__(x, y, piercing=False)
        self.angulo = angulo
        self.speed = 7.5
        self.radius = 6
        self.dano_jefe = 3.0
        self.blancos = blancos   # listas de main: asteroids, alien_ships, bosses
        self.t = 0

    def _blanco(self):
        mejor, mejor_d = None, 1e9
        for lista in self.blancos:
            for obj in lista:
                if not getattr(obj, "active", True):
                    continue
                d = (obj.x - self.x) ** 2 + (obj.y - self.y) ** 2
                if d < mejor_d:
                    mejor, mejor_d = obj, d
        return mejor

    def update(self):
        self.t += 1
        objetivo = self._blanco() if self.t > 8 else None
        if objetivo is not None:
            deseado = math.atan2(objetivo.y - self.y, objetivo.x - self.x)
            diferencia = (deseado - self.angulo + math.pi) % (2 * math.pi) - math.pi
            self.angulo += max(-0.12, min(0.12, diferencia))
        self.x += math.cos(self.angulo) * self.speed
        self.y += math.sin(self.angulo) * self.speed
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        if self.t > 240 or not (-40 < self.x < 1200 and -40 < self.y < 720):
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        for i, (tx, ty) in enumerate(self.trail[:-1]):
            neon.cuadro_pixel(screen, pixelfx.apagar((255, 170, 80), 0.3 + 0.08 * i), tx + offset_x, ty + offset_y, 4)
        pixelfx.misil(screen, self.x + offset_x, self.y + offset_y, self.angulo, self.t,
                      cuerpo=(220, 226, 240), punta=ORO, largo=4)


def marcar_critico(bala, nivel):
    """Al disparar: con suerte la bala sale critica (dorada, triple a jefes)."""
    if nivel and random.random() < PROB_CRITICO[min(nivel, 3)]:
        bala.dano_jefe *= 3
        bala.color = ORO
        bala.critico = True


class Habilidades:
    """Estado por partida de las habilidades activas."""

    def __init__(self):
        self.t = 0
        self.recarga_misil = 0
        self.recarga_nova = 0
        self.ondas = []           # [x, y, edad]
        self.golpes_orbita = {}   # id(roca) -> cuadros sin volver a pegarle
        self.bajas_base = None

    def _esferas(self, ship, nivel):
        n = 2 * nivel
        return [(ship.x + math.cos(self.t * 0.07 + 2 * math.pi * i / n) * RADIO_ORBITA,
                 ship.y + math.sin(self.t * 0.07 + 2 * math.pi * i / n) * RADIO_ORBITA * 0.8)
                for i in range(n)]

    def actualizar(self, niveles, ship, bullets, asteroids, alien_ships, bosses, balas_enemigas,
                   explosiones, crear_explosion, golpear_asteroide, bajas):
        """Un cuadro de juego. Devuelve un aviso [titulo, texto] o None."""
        self.t += 1
        aviso = None
        # MISILES
        nivel = niveles.get("misiles", 0)
        if nivel and ship.alive:
            self.recarga_misil -= 1
            if self.recarga_misil <= 0 and (asteroids or alien_ships or bosses):
                self.recarga_misil = RECARGA_MISIL[min(nivel, 2)]
                for lado in ((-1, 1) if nivel >= 2 else (random.choice((-1, 1)),)):
                    bullets.append(MisilJugador(ship.x + lado * 18, ship.y, -math.pi / 2 + lado * 0.6,
                                                (asteroids, alien_ships, bosses)))
        # NOVA: se dispara sola si una bala enemiga se acerca
        nivel = niveles.get("nova", 0)
        if nivel:
            self.recarga_nova -= 1
            if self.recarga_nova <= 0 and ship.alive:
                cerca = any((b.x - ship.x) ** 2 + (b.y - ship.y) ** 2 < 90 ** 2
                            for lista in balas_enemigas for b in lista if getattr(b, "active", True))
                if cerca:
                    self.recarga_nova = RECARGA_NOVA[min(nivel, 2)]
                    self.ondas.append([ship.x, ship.y, 0])
                    for lista in balas_enemigas:
                        for b in lista:
                            if (b.x - ship.x) ** 2 + (b.y - ship.y) ** 2 < RADIO_NOVA ** 2:
                                b.active = False
                    explosiones.append(crear_explosion(ship.x, ship.y, NOVA, 30))
        for o in self.ondas:
            o[2] += 1
        self.ondas = [o for o in self.ondas if o[2] < 22]
        # ORBITA: frena balas y rompe rocas
        nivel = niveles.get("orbita", 0)
        if nivel:
            esferas = self._esferas(ship, nivel)
            for lista in balas_enemigas:
                for b in lista:
                    if any((b.x - ex) ** 2 + (b.y - ey) ** 2 < 14 ** 2 for ex, ey in esferas):
                        b.active = False
                        explosiones.append(crear_explosion(b.x, b.y, ORBITA, 8))
            for clave in list(self.golpes_orbita):
                self.golpes_orbita[clave] -= 1
                if self.golpes_orbita[clave] <= 0:
                    del self.golpes_orbita[clave]
            for a in asteroids[:]:
                if not a.active or id(a) in self.golpes_orbita:
                    continue
                if any((a.x - ex) ** 2 + (a.y - ey) ** 2 < (a.size + 8) ** 2 for ex, ey in esferas):
                    self.golpes_orbita[id(a)] = 20
                    golpear_asteroide(a)
        # RECOLECTOR: vida por cada tantas bajas
        nivel = niveles.get("recolector", 0)
        if self.bajas_base is None or not nivel:
            self.bajas_base = bajas
        elif bajas - self.bajas_base >= BAJAS_RECOLECTOR[min(nivel, 2)]:
            self.bajas_base = bajas
            if ship.lives < ship.max_lives:
                ship.lives += 1
                ship.health_deplete_anim = ship.lives / max(1, ship.max_lives)
                explosiones.append(crear_explosion(ship.x, ship.y, (130, 255, 150), 26))
                aviso = ["¡RECOLECTOR!", "Recuperas una vida"]
        # FENIX (lo hace Ship.take_damage; aca solo el aviso y el fuego)
        if getattr(ship, "fenix_evento", False):
            ship.fenix_evento = False
            explosiones.append(crear_explosion(ship.x, ship.y, (255, 150, 50), 90))
            self.ondas.append([ship.x, ship.y, 0])
            for lista in balas_enemigas:
                for b in lista:
                    b.active = False
            aviso = ["¡FÉNIX!", "Renaces de tus cenizas"]
        return aviso

    def dibujar(self, surface, niveles, ship):
        if niveles.get("orbita", 0) and ship.alive:
            for ex, ey in self._esferas(ship, niveles["orbita"]):
                pixelfx.dibujar_halo(surface, ORBITA, ex, ey, 14)
                neon.cuadro_pixel(surface, ORBITA, ex, ey, 10)
                neon.cuadro_pixel(surface, WHITE, ex, ey, 4)
        for x, y, edad in self.ondas:
            k = edad / 22
            neon.anillo_pixel(surface, pixelfx.apagar(NOVA, 1 - k * 0.7), x, y, 20 + RADIO_NOVA * k, tam=6)
        if niveles.get("fenix", 0) and getattr(ship, "fenix", 0) > 0 and ship.alive and (self.t // 20) % 3 == 0:
            # una plumita encendida sobre la nave: el fenix sigue disponible
            neon.cuadro_pixel(surface, (255, 150, 50), ship.x, ship.y - 34, 6)
            neon.cuadro_pixel(surface, ORO, ship.x, ship.y - 38, 4)
