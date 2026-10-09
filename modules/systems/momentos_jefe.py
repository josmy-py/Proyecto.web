"""
Animaciones de ataque y "momentos unicos" de los jefes, para todos a la vez.

DirectorJefes mira a los jefes desde afuera (sin tocar sus clases):

  - ANIMACIONES DE ATAQUE: cuando un jefe arranca un especial (su atributo
    `especial` pasa de None a algo) se carga: chispas que se juntan en el y
    un halo que crece. Cuando suelta una rafaga (4 balas o mas en un mismo
    cuadro) sale una onda expansiva con fogonazos en la boca de cada bala y
    la pantalla tiembla un poco. Al cambiar de fase (phase_transition) da
    un rugido de ondas.

  - MOMENTO UNICO: una sola vez por pelea, cuando a un jefe le queda cierta
    vida (MOMENTOS[clave]["umbral"]), la pelea se detiene unos segundos:
    franjas de cine, su frase, un efecto propio (el escaneo del Centinela,
    el reloj de la Parca, el hackeo del Netrunner...) y al final un remate
    con un patron de balas propio. Mientras dura, el jefe no se mueve ni
    recibe daño; el remate ya se puede esquivar.

main.py llama, por cuadro de juego: congela()/invulnerable() en el bucle de
jefes y en los choques, observar() despues de cada boss.update(),
actualizar() una vez, dibujar_mundo() despues de dibujar a los jefes y
dibujar_pantalla() encima de todo (nitido aunque el entorno este pixelado).
Los eventos ("vibrar", "alerta", "explosion") quedan en `eventos`.
"""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.systems import neon, pixelfx
from modules.entities.nyan_boss import BalaPixel, ARCOIRIS
from modules.entities import cine_jefes

NEGRO = (0, 0, 0)

# clave -> umbral de vida, frase y colores del momento. Los efectos y los
# remates estan mas abajo (_EFECTOS / _REMATES), con la misma clave.
MOMENTOS = {
    "centinela": dict(umbral=0.6, frase="Amenaza detectada. Protocolo de exterminio."),
    "dragon": dict(umbral=0.6, frase="¡Siente el fuego de una estrella muerta!"),
    "titan": dict(umbral=0.6, frase="EL VACÍO TE RECLAMA"),
    "anomalia": dict(umbral=0.6, frase="ERROR... la realidad se rompe..."),
    # el Coloso renace a la mitad: su momento va antes
    "coloso": dict(umbral=0.8, frase="¡Todas las baterías: fuego a discreción!"),
    "nyan": dict(umbral=0.6, frase="¡Nyan nyan nyan nyan nyan!"),
    "oiia": dict(umbral=0.6, frase="¡OIIA OIIA OIIA!"),
    "alien": dict(umbral=0.6, frase="Espécimen localizado. Iniciando abducción."),
    "calabaza": dict(umbral=0.6, frase="¡Tu sangre va a regar mi huerto!"),
    # la Bruja se vuelve gigante a la mitad: su momento va antes
    "bruja": dict(umbral=0.75, frase="Un hechizo solo para ti, cariño."),
    "parca": dict(umbral=0.6, frase="Tu tiempo se acabó."),
    "netrunner": dict(umbral=0.6, frase="Estás en mi red. Ejecutando daemon."),
    "tarantula": dict(umbral=0.6, frase="OBJETIVO ATRAPADO."),
    "kaiser": dict(umbral=0.6, frase="¡Puro cromo, puro poder!"),
}

T_ENTRA = 30       # franjas y velo
T_CARGA = 120      # empieza a juntar energia
T_REMATE = 165     # suelta el remate y el jefe vuelve a pelear
T_FIN = 200


def clave_jefe(boss):
    clave = cine_jefes.clave_de(boss)
    if clave is None and type(boss).__name__ == "ParcaDimension":
        clave = "parca"
    return clave


def colores_jefe(boss):
    ficha = cine_jefes.FICHAS.get(clave_jefe(boss) or "", {})
    return ficha.get("color", (255, 120, 200)), ficha.get("color2", WHITE)


def _alto(boss):
    return getattr(boss, "alto_sprite", None) or 140


# ------------------------------------------------------------ efectos chicos

class _Chispa:
    def __init__(self, x, y, vx, vy, color, vida, tam=4):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color, self.vida, self.vida0, self.tam = color, vida, vida, tam

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94
        self.vida -= 1

    def draw(self, s):
        k = self.vida / self.vida0
        tam = max(2, int(self.tam * (0.5 + k)))
        s.fill(pixelfx.apagar(self.color, 0.4 + 0.6 * k), (int(self.x) - tam // 2, int(self.y) - tam // 2, tam, tam))


class _Carga:
    """El jefe junta energia antes de un especial: chispas que vuelan hacia
    el y un halo que late cada vez mas fuerte."""

    DURA = 42

    def __init__(self, boss, color, color2):
        self.boss, self.color, self.color2, self.t = boss, color, color2, 0
        self.chispas = []

    @property
    def vivo(self):
        return self.t < self.DURA or self.chispas

    def update(self):
        self.t += 1
        bx, by = self.boss.x, self.boss.y
        if self.t < self.DURA - 8:
            for _ in range(2):
                a = random.uniform(0, 2 * math.pi)
                d = random.uniform(90, 150)
                x, y = bx + math.cos(a) * d, by + math.sin(a) * d
                self.chispas.append(_Chispa(x, y, (bx - x) / 14, (by - y) / 14,
                                            random.choice((self.color, self.color2, WHITE)), 16, 5))
        for c in self.chispas:
            c.update()
        self.chispas = [c for c in self.chispas if c.vida > 0]

    def draw(self, s):
        k = min(1.0, self.t / self.DURA)
        if self.t < self.DURA:
            latido = 0.5 + 0.5 * math.sin(self.t * 0.6)
            pixelfx.dibujar_halo(s, pixelfx.apagar(self.color, 0.35 + 0.4 * k * latido),
                                 self.boss.x, self.boss.y, 50 + 50 * k)
            neon.anillo_pixel(s, pixelfx.apagar(self.color2, 0.4 + 0.5 * k), self.boss.x, self.boss.y,
                              110 - 70 * k, tam=4, cantidad=16)
        for c in self.chispas:
            c.draw(s)


class _Onda:
    """Onda expansiva (rafagas, rugidos y remates)."""

    def __init__(self, x, y, color, radio_max=140, dura=18, grosor=6):
        self.x, self.y, self.color = x, y, color
        self.radio_max, self.dura, self.grosor, self.t = radio_max, dura, grosor, 0

    @property
    def vivo(self):
        return self.t < self.dura

    def update(self):
        self.t += 1

    def draw(self, s):
        k = self.t / self.dura
        neon.anillo_pixel(s, pixelfx.apagar(self.color, 1 - k * 0.8), self.x, self.y,
                          20 + self.radio_max * (1 - (1 - k) ** 2), tam=self.grosor)


class _Fogonazo:
    def __init__(self, x, y, color):
        self.x, self.y, self.color, self.t = x, y, color, 0

    @property
    def vivo(self):
        return self.t < 7

    def update(self):
        self.t += 1

    def draw(self, s):
        tam = 14 - self.t * 2
        if tam > 0:
            s.fill(WHITE if self.t < 2 else self.color, (int(self.x) - tam // 2, int(self.y) - tam // 2, tam, tam))


# ------------------------------------------------------------ remates

def _bala(x, y, a, vel, color, tam=12, forma="cuadro"):
    return BalaPixel(x, y, math.cos(a) * vel, math.sin(a) * vel, color=color, tam=tam, forma=forma)


def _remate_cuadricula(boss, ship, c1, c2):
    # el Centinela: filas que bajan con un hueco donde estaba la nave
    balas = []
    hueco = ship.x
    for fila in range(3):
        for x in range(30, GAME_WIDTH, 50):
            if abs(x - hueco) > 70 + fila * 10:
                balas.append(BalaPixel(x, -10 - fila * 70, 0, 3.2, color=c1 if fila % 2 else c2, tam=12))
    return balas


def _remate_aliento(boss, ship, c1, c2):
    # el Dragon: un cono de fuego hacia la nave
    a0 = math.atan2(ship.y - boss.y, ship.x - boss.x)
    return [_bala(boss.x, boss.y + 30, a0 + k * 0.07, random.uniform(3.6, 5.2),
                  random.choice((c1, c2, (255, 80, 30))), 14) for k in range(-7, 8)]


def _remate_espiral(boss, ship, c1, c2, brazos=3, n=8, forma="cuadro"):
    balas = []
    for b in range(brazos):
        for i in range(n):
            a = 2 * math.pi * b / brazos + i * 0.22
            balas.append(_bala(boss.x, boss.y, a, 2.0 + i * 0.32, c1 if b % 2 else c2, 12, forma))
    return balas


def _remate_anillos(boss, ship, c1, c2):
    # la Anomalia: tres anillos a distinta velocidad y desfasados
    balas = []
    for k, vel in enumerate((2.0, 2.8, 3.6)):
        for i in range(14):
            a = 2 * math.pi * i / 14 + k * 0.22
            balas.append(_bala(boss.x, boss.y, a, vel, (c1, c2, WHITE)[k], 12))
    return balas


def _remate_lluvia(boss, ship, c1, c2, forma="cuadro"):
    # bajan en diagonal desde arriba, dejando un pasillo
    balas = []
    hueco = random.uniform(GAME_WIDTH * 0.25, GAME_WIDTH * 0.75)
    for i in range(22):
        x = 20 + i * (GAME_WIDTH - 40) / 21
        if abs(x - hueco) < 70:
            continue
        balas.append(BalaPixel(x, -20 - (i % 3) * 40, 0.6, random.uniform(3.0, 4.2),
                               color=c1 if i % 2 else c2, tam=12, forma=forma))
    return balas


def _remate_arcoiris(boss, ship, c1, c2):
    # Nyan: una ola de bloques de arcoiris que baja ondulando
    balas = []
    for i in range(16):
        a = math.pi / 2 + (i - 7.5) * 0.14
        bala = _bala(boss.x, boss.y, a, 3.2 + math.sin(i) * 0.6, ARCOIRIS[i % len(ARCOIRIS)], 18, "arcoiris")
        balas.append(bala)
    return balas


def _remate_cruz(boss, ship, c1, c2, vueltas=2):
    balas = []
    for v in range(vueltas):
        for brazo in range(4):
            for i in range(5):
                a = brazo * math.pi / 2 + v * math.pi / 4
                balas.append(_bala(boss.x, boss.y, a, 2.2 + i * 0.5, c1 if v % 2 else c2, 12))
    return balas


def _remate_bruja(boss, ship, c1, c2):
    # dos anillos de estrellas encontrados
    balas = []
    for k, vel in enumerate((2.2, 3.0)):
        for i in range(16):
            a = 2 * math.pi * i / 16 + k * math.pi / 16
            balas.append(_bala(boss.x, boss.y, a, vel, c1 if k else c2, 14, "estrella"))
    return balas


def _remate_guadanas(boss, ship, c1, c2):
    # la Parca: dos arcos como cortes de guadaña con un hueco cada uno
    balas = []
    for k, desfase in enumerate((-0.35, 0.35)):
        hueco = random.randint(3, 13)
        for i in range(17):
            if hueco <= i <= hueco + 1:
                continue
            a = math.pi * 0.15 + i * math.pi * 0.7 / 16 + desfase * 0.2
            balas.append(_bala(boss.x, boss.y, a, 2.6 + k * 0.8, c2 if k else (255, 70, 70), 14))
    return balas


def _remate_datos(boss, ship, c1, c2):
    # el Netrunner: columnas de datos que caen, una al lado de la otra
    balas = []
    for col in range(10):
        x = 50 + col * (GAME_WIDTH - 100) / 9
        if abs(x - ship.x) < 60:
            continue
        for k in range(3):
            balas.append(BalaPixel(x, -10 - k * 34 - col * 12, 0, 3.4, color=c1 if k else c2, tam=10))
    return balas


def _remate_red(boss, ship, c1, c2):
    # la Tarantula: una telaraña de dos anillos unidos por radios
    balas = []
    for i in range(12):
        a = 2 * math.pi * i / 12
        for vel in (1.8, 2.6, 3.4):
            balas.append(_bala(boss.x, boss.y, a, vel, c1 if vel > 2 else c2, 10))
    return balas


def _remate_kaiser(boss, ship, c1, c2):
    return _remate_cruz(boss, ship, c1, c2, vueltas=2) + _remate_espiral(boss, ship, c2, c1, brazos=2, n=6)


_REMATES = {
    "centinela": _remate_cuadricula,
    "dragon": _remate_aliento,
    "titan": lambda b, s, c1, c2: _remate_espiral(b, s, c1, c2, brazos=4, n=7),
    "anomalia": _remate_anillos,
    "coloso": _remate_lluvia,
    "nyan": _remate_arcoiris,
    "oiia": lambda b, s, c1, c2: _remate_espiral(b, s, c1, c2, brazos=5, n=6),
    "alien": _remate_cruz,
    "calabaza": lambda b, s, c1, c2: _remate_lluvia(b, s, (220, 20, 34), (140, 0, 16)),
    "bruja": _remate_bruja,
    "parca": _remate_guadanas,
    "netrunner": _remate_datos,
    "tarantula": _remate_red,
    "kaiser": _remate_kaiser,
}


# ------------------------------------------------------------ efectos propios

def _ef_escaneo(s, m, t, ship):
    # el Centinela barre la pantalla con una grilla roja y fija la mira
    rojo = (255, 60, 80)
    y = (t * 7) % (GAME_HEIGHT + 80) - 40
    s.fill(rojo, (0, int(y), GAME_WIDTH, 3))
    for x in range(0, GAME_WIDTH, 60):
        s.fill(pixelfx.apagar(rojo, 0.35), (x, 0, 1, GAME_HEIGHT))
    if t > 50:
        r = max(26, 90 - (t - 50))
        pygame.draw.circle(s, rojo, (int(ship.x), int(ship.y)), int(r), 2)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            s.fill(rojo, (int(ship.x + dx * (r + 4)) - 6 * abs(dx) - 1, int(ship.y + dy * (r + 4)) - 6 * abs(dy) - 1,
                          12 * abs(dx) + 3, 12 * abs(dy) + 3))


def _ef_inhala(s, m, t, ship):
    # el Dragon inhala: brasas que giran y entran a su boca
    b = m.boss
    for i in range(24):
        a = t * 0.12 + i * 2 * math.pi / 24
        d = 160 - (t * 2 + i * 7) % 150
        x, y = b.x + math.cos(a) * d, b.y + 30 + math.sin(a) * d * 0.7
        s.fill(random.choice(((255, 140, 50), (255, 230, 90), (255, 80, 30))), (int(x), int(y), 5, 5))
    pixelfx.dibujar_halo(s, (120, 40, 10), b.x, b.y + 30, 60 + t * 0.3)


def _ef_vacio(s, m, t, ship):
    # el Titan: anillos de vacio que laten y un ojo enorme detras
    b = m.boss
    for k in range(4):
        r = ((t * 3 + k * 60) % 240)
        neon.anillo_pixel(s, pixelfx.apagar((170, 110, 255), 1 - r / 240), b.x, b.y, r, tam=6)
    abre = min(1.0, max(0.0, (t - 30) / 50))
    if abre > 0:
        alto = int(80 * abre)
        pygame.draw.ellipse(s, (40, 10, 70), (GAME_WIDTH // 2 - 200, 40 - alto // 2 + 60, 400, max(2, alto)))
        pygame.draw.ellipse(s, (90, 255, 200), (GAME_WIDTH // 2 - 40, 100 - min(alto, 60) // 2, 80, max(2, min(alto, 60))))
        s.fill(NEGRO, (GAME_WIDTH // 2 - 6, 100 - min(alto, 50) // 2, 12, max(2, min(alto, 50))))


def _ef_glitch(s, m, t, ship):
    # la Anomalia rompe la imagen en franjas corridas
    copia = s.copy()
    for _ in range(6):
        y = random.randrange(0, GAME_HEIGHT - 20)
        alto = random.randint(6, 26)
        s.blit(copia, (random.randint(-30, 30), y), (0, y, GAME_WIDTH, alto))
    if t % 10 < 3:
        tinte = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        tinte.fill((120, 255, 170, 30) if t % 20 < 10 else (200, 120, 255, 30))
        s.blit(tinte, (0, 0))


def _ef_alarma(s, m, t, ship):
    # el Coloso: luces de alarma que giran en los costados
    if (t // 10) % 2 == 0:
        velo = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        velo.fill((255, 30, 30, 40))
        s.blit(velo, (0, 0))
    for lado in (0, GAME_WIDTH - 40):
        for k in range(6):
            y = (t * 6 + k * 110) % GAME_HEIGHT
            s.fill((255, 60, 40), (lado, y, 40, 12))


def _ef_arcoiris(s, m, t, ship):
    # Nyan: franjas de arcoiris que cruzan la pantalla
    franja = 12
    x0 = int((t * 14) % (GAME_WIDTH + 400)) - 400
    for i, color in enumerate(ARCOIRIS):
        y = 140 + i * franja + int(math.sin((t + i * 4) * 0.2) * 6)
        s.fill(color, (0, y, max(0, x0 + 400), franja))
    for k in range(10):
        x = (k * 131 + t * 9) % GAME_WIDTH
        y = (k * 67) % GAME_HEIGHT
        neon.cuadro_pixel(s, WHITE, x, y, 6 if (t + k) % 8 < 4 else 3)


def _ef_giro(s, m, t, ship):
    # OIIA: el gato gira cada vez mas rapido y suelta "OIIA" alrededor
    b = m.boss
    vel = 0.05 + t * 0.003
    for i in range(6):
        a = t * vel + i * math.pi / 3
        x, y = b.x + math.cos(a) * 120, b.y + math.sin(a) * 80
        letra = neon.texto(18, "OIIA", (255, 230, 120) if i % 2 else (255, 120, 220))
        s.blit(letra, letra.get_rect(center=(int(x), int(y))))


def _ef_abduccion(s, m, t, ship):
    # el Alien: un rayo verde baja hasta la nave
    b = m.boss
    ancho = 40 + int(20 * math.sin(t * 0.2))
    rayo = pygame.Surface((ancho * 2 + 40, GAME_HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(rayo, (120, 255, 140, 70), ((ancho, 0), (ancho + 40, 0), (ancho * 2 + 40, GAME_HEIGHT),
                                                    (0, GAME_HEIGHT)))
    s.blit(rayo, (int(ship.x) - ancho - 20, int(b.y)), (0, 0, ancho * 2 + 40, max(0, int(ship.y - b.y + 30))))
    for k in range(5):
        y = b.y + ((t * 5 + k * 40) % max(1, int(ship.y - b.y)))
        s.fill((200, 255, 200), (int(ship.x) - 20, int(y), 40, 2))


def _ef_sangre(s, m, t, ship):
    # el Rey Calabaza: la pantalla late en rojo y chorrea sangre desde arriba
    velo = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    velo.fill((160, 0, 20, 40 + int(30 * math.sin(t * 0.25))))
    s.blit(velo, (0, 0))
    for i in range(18):
        x = 20 + i * 61 % GAME_WIDTH
        largo = min(GAME_HEIGHT * 0.5, (t * (2 + i % 4)) * 1.2)
        s.fill((140, 0, 16), (x, 0, 6, int(largo)))
        s.fill((220, 20, 34), (x - 1, int(largo) - 6, 8, 8))


def _ef_aquelarre(s, m, t, ship):
    # la Bruja: un circulo magico enorme gira detras de ella
    b = m.boss
    r = min(170, 30 + t * 2)
    color, color2 = (170, 236, 255), (205, 130, 255)
    pygame.draw.circle(s, color, (int(b.x), int(b.y)), r, 3)
    pygame.draw.circle(s, color2, (int(b.x), int(b.y)), int(r * 0.8), 2)
    for desfase in (0, math.pi / 3):
        puntos = [(b.x + math.cos(t * 0.03 + desfase + 2 * math.pi * i / 3) * r * 0.8,
                   b.y + math.sin(t * 0.03 + desfase + 2 * math.pi * i / 3) * r * 0.8) for i in range(3)]
        pygame.draw.polygon(s, color, puntos, 2)
    for i in range(12):
        a = -t * 0.02 + 2 * math.pi * i / 12
        s.fill(WHITE if i % 3 == 0 else color2, (int(b.x + math.cos(a) * r * 0.9) - 3, int(b.y + math.sin(a) * r * 0.9) - 3, 6, 6))


def _ef_reloj(s, m, t, ship):
    # la Parca detiene el tiempo: todo se apaga a gris y un reloj de arena
    # enorme gira detras de ella
    gris = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    gris.fill((30, 20, 24, 120))
    s.blit(gris, (0, 0))
    b = m.boss
    giro = min(math.pi, t * 0.03)
    arena = (240, 190, 90)
    alto, ancho = 150, 90
    puntos = [(-ancho / 2, -alto / 2), (ancho / 2, -alto / 2), (0, 0), (ancho / 2, alto / 2), (-ancho / 2, alto / 2), (0, 0)]
    rot = [(b.x + x * math.cos(giro) - y * math.sin(giro), b.y + x * math.sin(giro) + y * math.cos(giro))
           for x, y in puntos]
    pygame.draw.lines(s, arena, True, rot, 4)
    neon.anillo_pixel(s, (190, 24, 40), b.x, b.y, 120, tam=5, cantidad=12)


def _ef_hackeo(s, m, t, ship):
    # el Netrunner: lluvia de codigo y ventanas de error
    for col in range(0, GAME_WIDTH, 28):
        y = (t * (4 + col % 5) + col * 7) % (GAME_HEIGHT + 60) - 60
        for k in range(5):
            s.fill(pixelfx.apagar((0, 240, 255), 1 - k * 0.18), (col, int(y) - k * 12, 6, 8))
    if t > 40 and (t // 6) % 3:
        for k in range(min(4, (t - 40) // 15 + 1)):
            caja = pygame.Rect(80 + k * 230, 120 + (k % 2) * 160, 200, 60)
            s.fill((10, 10, 30), caja)
            pygame.draw.rect(s, (255, 40, 200), caja, 2)
            letras = neon.texto(14, "DAEMON.EXE", (255, 40, 200))
            s.blit(letras, letras.get_rect(center=caja.center))


def _ef_telarana(s, m, t, ship):
    # la Tarantula teje una red desde las esquinas hasta ella
    b = m.boss
    k = min(1.0, t / 80)
    puntas = [(0, 0), (GAME_WIDTH, 0), (0, GAME_HEIGHT), (GAME_WIDTH, GAME_HEIGHT), (GAME_WIDTH // 2, GAME_HEIGHT),
              (0, GAME_HEIGHT // 2), (GAME_WIDTH, GAME_HEIGHT // 2)]
    color = (230, 230, 240)
    for px, py in puntas:
        pygame.draw.line(s, color, (int(b.x), int(b.y)), (int(b.x + (px - b.x) * k), int(b.y + (py - b.y) * k)), 2)
    for r in (80, 160, 240, 320):
        if r < 340 * k:
            neon.anillo_pixel(s, pixelfx.apagar(color, 0.7), b.x, b.y, r, tam=3, cantidad=28)


def _ef_sobrecarga(s, m, t, ship):
    # el Kaiser: rayos amarillos que saltan de su armadura de cromo
    b = m.boss
    for _ in range(3):
        x, y = b.x, b.y
        a = random.uniform(0, 2 * math.pi)
        puntos = [(x, y)]
        for _k in range(5):
            x += math.cos(a) * 30 + random.uniform(-14, 14)
            y += math.sin(a) * 30 + random.uniform(-14, 14)
            puntos.append((x, y))
        pygame.draw.lines(s, (255, 230, 40), False, puntos, 3)
    if t % 12 < 2:
        flash = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, 60))
        s.blit(flash, (0, 0))


_EFECTOS = {
    "centinela": _ef_escaneo, "dragon": _ef_inhala, "titan": _ef_vacio, "anomalia": _ef_glitch,
    "coloso": _ef_alarma, "nyan": _ef_arcoiris, "oiia": _ef_giro, "alien": _ef_abduccion,
    "calabaza": _ef_sangre, "bruja": _ef_aquelarre, "parca": _ef_reloj, "netrunner": _ef_hackeo,
    "tarantula": _ef_telarana, "kaiser": _ef_sobrecarga,
}


# ------------------------------------------------------------ el momento

class _Momento:
    def __init__(self, boss, clave):
        self.boss, self.clave, self.t = boss, clave, 0
        self.color, self.color2 = colores_jefe(boss)
        self.frase = MOMENTOS[clave]["frase"]
        self.chispas = []

    @property
    def terminado(self):
        return self.t >= T_FIN

    def update(self):
        self.t += 1
        b = self.boss
        if T_CARGA <= self.t < T_REMATE:
            for _ in range(3):
                a = random.uniform(0, 2 * math.pi)
                d = random.uniform(120, 220)
                x, y = b.x + math.cos(a) * d, b.y + math.sin(a) * d
                self.chispas.append(_Chispa(x, y, (b.x - x) / 12, (b.y - y) / 12,
                                            random.choice((self.color, self.color2, WHITE)), 14, 6))
        for c in self.chispas:
            c.update()
        self.chispas = [c for c in self.chispas if c.vida > 0]

    def dibujar_mundo(self, s, ship):
        if self.t < T_REMATE:
            efecto = _EFECTOS.get(self.clave)
            if efecto is not None and self.t >= T_ENTRA // 2:
                efecto(s, self, self.t - T_ENTRA // 2, ship)
            if self.t >= T_CARGA:
                k = (self.t - T_CARGA) / (T_REMATE - T_CARGA)
                pixelfx.dibujar_halo(s, pixelfx.apagar(self.color, 0.4 + 0.5 * k), self.boss.x, self.boss.y, 60 + 90 * k)
        for c in self.chispas:
            c.draw(s)

    def dibujar_pantalla(self, s):
        t = self.t
        if t < T_ENTRA:
            k = t / T_ENTRA
        elif t < T_REMATE:
            k = 1.0
        else:
            k = max(0.0, 1 - (t - T_REMATE) / (T_FIN - T_REMATE))
        if k > 0:
            neon.franjas_cine(s, k, self.color, alto=44)
        if T_ENTRA <= t < T_CARGA + 20:
            letras = self.frase[:max(0, (t - T_ENTRA) * 2)]   # se escribe de a poco
            if letras:
                # bajo la franja de cine y el HUD aunque el jefe este arriba
                y = max(160, self.boss.y - _alto(self.boss) / 2 + 10)
                neon.globo(s, letras, self.boss.x, y, self.color, tam=18)
        if T_REMATE <= t < T_REMATE + 6:
            neon.velo(s, WHITE, int(200 * (1 - (t - T_REMATE) / 6)))


def _sin_dano(*_args, **_kw):
    return False


def _blindar(boss, si):
    """Mientras carga su momento el jefe no recibe dano de ninguna fuente
    (balas, misiles, rayo, nova...): se tapa take_damage en la instancia."""
    if si:
        boss.take_damage = _sin_dano
    elif boss.__dict__.get("take_damage") is _sin_dano:
        del boss.take_damage


class DirectorJefes:
    def __init__(self):
        self.momento = None
        self.vistos = set()
        self.efectos = []
        self.sacudida = 0
        self.eventos = []
        self._previo = {}

    # --- consultas del bucle de main
    def congela(self, boss):
        return self.momento is not None and self.momento.boss is boss and self.momento.t < T_REMATE

    invulnerable = congela

    @property
    def activo(self):
        return self.momento is not None

    # --- animaciones de ataque
    def observar(self, boss, balas):
        clave = clave_jefe(boss)
        if clave is None:
            return
        color, color2 = colores_jefe(boss)
        previo = self._previo.get(id(boss), {})
        especial = getattr(boss, "especial", None) is not None
        transicion = bool(getattr(boss, "phase_transition", False))
        if especial and not previo.get("especial"):
            self.efectos.append(_Carga(boss, color, color2))
        if transicion and not previo.get("transicion"):
            for k in range(3):
                self.efectos.append(_Onda(boss.x, boss.y, (color, color2, WHITE)[k], 160 + k * 60, 20 + k * 6, 6))
            self.sacudida = max(self.sacudida, 10)
            self.eventos.append(("vibrar", 0.6, 300))
        self._previo[id(boss)] = {"especial": especial, "transicion": transicion}
        balas = balas or []
        if len(balas) >= 4:
            self.efectos.append(_Onda(boss.x, boss.y, color2, 120, 14, 5))
            self.sacudida = max(self.sacudida, 4)
        for bala in balas[:6]:
            if getattr(bala, "visible", True):
                self.efectos.append(_Fogonazo(bala.x, bala.y, color2))

    # --- el momento unico
    def _elegible(self, boss):
        clave = clave_jefe(boss)
        if clave not in MOMENTOS or id(boss) in self.vistos or not boss.active:
            return None
        if (getattr(boss, "entrando", False) or getattr(boss, "transformando", False)
                or getattr(boss, "invencible", False) or getattr(boss, "gigante", False)
                or getattr(boss, "phase_transition", False) or getattr(boss, "pide_cinematica", None)
                or getattr(boss, "enter_timer", 0) > 0):
            return None
        vida = getattr(boss, "hp", 0) / max(1, getattr(boss, "max_hp", 1))
        if 0 < vida <= MOMENTOS[clave]["umbral"]:
            return clave
        return None

    def actualizar(self, bosses, ship, boss_bullets, puede=True):
        self.eventos = []
        if self.momento is None and puede:
            for boss in bosses:
                clave = self._elegible(boss)
                if clave is not None:
                    self.vistos.add(id(boss))
                    self.momento = _Momento(boss, clave)
                    _blindar(boss, True)
                    if hasattr(boss, "especial"):
                        boss.especial = None   # el momento corta lo que estaba haciendo
                    for bb in boss_bullets:
                        bb.active = False
                        self.efectos.append(_Fogonazo(bb.x, bb.y, self.momento.color))
                    self.eventos.append(("alerta",))
                    break
        m = self.momento
        if m is not None:
            m.update()
            if m.t >= T_CARGA:
                self.sacudida = max(self.sacudida, 1 + (m.t - T_CARGA) // 12)
            if m.t == T_REMATE:
                _blindar(m.boss, False)
                balas = _REMATES[m.clave](m.boss, ship, m.color, m.color2)
                boss_bullets.extend(balas)
                for k in range(3):
                    self.efectos.append(_Onda(m.boss.x, m.boss.y, (m.color, m.color2, WHITE)[k], 220 + k * 80, 22 + k * 6, 8))
                self.sacudida = 16
                self.eventos.append(("explosion",))
                self.eventos.append(("vibrar", 1.0, 500))
            if m.terminado or not m.boss.active:
                _blindar(m.boss, False)
                self.momento = None
        for e in self.efectos:
            e.update()
        self.efectos = [e for e in self.efectos if e.vivo]
        if self.sacudida > 0:
            self.sacudida -= 1

    def desplazamiento(self):
        if self.sacudida <= 0:
            return 0, 0
        return random.randint(-self.sacudida, self.sacudida), random.randint(-self.sacudida, self.sacudida)

    # --- dibujo
    def dibujar_mundo(self, surface, ship):
        if self.momento is not None:
            self.momento.dibujar_mundo(surface, ship)
        for e in self.efectos:
            e.draw(surface)

    def dibujar_pantalla(self, surface):
        if self.momento is not None:
            self.momento.dibujar_pantalla(surface)
