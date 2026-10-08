"""
Cinematicas de entrada y de derrota de los jefes, armadas a partir de la
ficha de cada uno en el Grimorio de Jefes (su capitulo, su historia y una
frase al llegar y otra al caer).

  - CinematicaEntradaJefe: alerta, el jefe llega a su manera (ver
    FICHAS[...]["llegada"]) y se presenta con su nombre y su frase.
  - CinematicaDerrotaJefe: el golpe final congela todo, el jefe dice sus
    ultimas palabras y cae a su manera (estalla, se desvanece, se
    estrella o se duerme); su pagina del grimorio queda tachada.
  - CinematicaRenacerColoso: a la mitad de su pelea el Coloso estalla y
    sus pedazos se vuelven a unir en la Esfera de Combate.

Las dos reciben el sprite del jefe (ver retrato) y una funcion que dibuja
el fondo de la fase, asi sirven igual para los jefes de las oleadas y los
de las rutas bonus. Los jefes cyberpunk ya tienen su entrada propia
(cyberpunk_cine.CinematicaEntradaCyber), el Gato Alien llega con su golpe
(nyan_boss.CinematicaGolpeAlien) y el Coloso cae con la huida a toda
velocidad de main._cinematica_victoria.

Interfaz de las otras cinematicas: update(), draw(surface), terminada,
saltar(), temblor y eventos ("alerta", "golpe", "carga", "glitch",
"explosion"; los sonidos los pone main.py)."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.systems import neon, pixelfx
from modules.entities.nyan_boss import PIXEL_BONUS, pixelar, _blit_centrado

NEGRO = (0, 0, 0)
ARCOIRIS = ((255, 60, 60), (255, 160, 40), (255, 235, 60), (80, 230, 90), (60, 160, 255), (150, 90, 255))

# Ficha de cada jefe: capitulo del grimorio, apodo, frases, colores y como
# llega y como cae. "habla" False: la frase sale en una cinta (no habla);
# "femenina": "¡... DERROTADA!".
FICHAS = {
    "centinela": dict(
        nombre="CENTINELA CORRUPTO", capitulo="TOMO I · CAPÍTULO 1", apodo="EL VIGÍA DEL CINTURÓN",
        entrada="Frontera cerrada. Todo intruso será eliminado.",
        derrota="Señal... perdida... frontera... abierta...",
        color=(90, 220, 255), color2=(255, 70, 110), llegada="escaneo", caida="estalla"),
    "dragon": dict(
        nombre="DRAGÓN ESPACIAL", capitulo="TOMO I · CAPÍTULO 2", apodo="NACIDO DE UNA ESTRELLA MORIBUNDA",
        entrada="Mi estrella murió... y tú vas a arder con ella.",
        derrota="Vuelvo... al corazón de mi estrella...",
        color=(255, 140, 50), color2=(255, 230, 90), llegada="picada", caida="estalla"),
    "titan": dict(
        nombre="TITÁN DEL VACÍO", capitulo="TOMO I · CAPÍTULO 3", apodo="EL PULPO QUE DOMINA EL CIELO",
        entrada="EL VACÍO TE OBSERVA", derrota="EL OJO DEL VACÍO SE CIERRA",
        color=(170, 110, 255), color2=(90, 255, 200), llegada="tentaculos", caida="estalla", habla=False),
    "anomalia": dict(
        nombre="LA ANOMALÍA FINAL", capitulo="TOMO I · CAPÍTULO 4", apodo="UN ERROR EN EL TEJIDO DEL ESPACIO",
        entrada="ERROR... tu existencia no está permitida.",
        derrota="ERR0R... ERR... r e i n i c i a n d o...",
        color=(200, 120, 255), color2=(120, 255, 170), llegada="grieta", caida="glitch", femenina=True),
    "coloso": dict(
        nombre="COLOSO ESTELAR", capitulo="TOMO I · CAPÍTULO 5", apodo="LA FORTALEZA DEL BORDE DE LA GALAXIA",
        entrada="Este es el borde de la galaxia. Nadie lo cruza.",
        derrota="", color=(255, 200, 60), color2=(255, 90, 220), llegada="gigante", caida="estalla"),
    "nyan": dict(
        nombre="NYAN CAT", capitulo="TOMO II · CAPÍTULO 1", apodo="EL PRIMERO EN CRUZAR LA GRIETA",
        entrada="¡Nyan nyan nyan! ¿Jugamos?", derrota="Nyan... nyaaan... me mareé...",
        color=(255, 120, 200), color2=(255, 235, 60), llegada="arcoiris", caida="arcoiris"),
    "alien": dict(
        nombre="GATO ALIEN", capitulo="TOMO II · CAPÍTULO 2", apodo="EL PLATO QUE ABDUCE NAVES",
        entrada="", derrota="¡Miau-day! ¡Miau-day! ¡Me caigo!",
        color=(120, 255, 170), color2=(90, 220, 255), llegada="baja", caida="cae"),
    "oiia": dict(
        nombre="GATO OIIA", capitulo="TOMO II · CAPÍTULO 3", apodo="EL GATO QUE NUNCA DEJA DE GIRAR",
        entrada="¡OIIA OIIA! ¡OIIA OIIA!", derrota="oiia... oi... ia... zzz...",
        color=(255, 200, 60), color2=(255, 70, 110), llegada="giro", caida="duerme"),
    "calabaza": dict(
        nombre="REY CALABAZA", capitulo="TOMO III · CAPÍTULO 1", apodo="SOBERANO DEL HUERTO EMBRUJADO",
        entrada="¡De rodillas ante el rey del huerto!", derrota="¡Mi corona...! ¡Mi huerto...!",
        color=(255, 154, 60), color2=(140, 255, 90), llegada="sube", caida="estalla"),
    "bruja": dict(
        nombre="BRUJA NEÓN", capitulo="TOMO III · CAPÍTULO 2", apodo="HECHICERA DE LAS NEBULOSAS",
        entrada="Qué nave tan linda... ¿probamos una poción?",
        derrota="Mis estrellas... se apagan...",
        color=(120, 210, 255), color2=(228, 250, 255), llegada="vuelo", caida="estrellas", femenina=True),
    "parca": dict(
        nombre="LA PARCA", capitulo="TOMO III · CAPÍTULO 3", apodo="LA QUE ESPERA AL FINAL DE TODOS LOS CAMINOS",
        entrada="Todos los caminos terminan conmigo.", derrota="Esto... no termina aquí. Volveré.",
        color=(150, 255, 210), color2=(255, 70, 110), llegada="aparicion", caida="desvanece", femenina=True),
    "netrunner": dict(
        nombre="NETRUNNER FANTASMA", capitulo="TOMO IV · CAPÍTULO 1", apodo="EL FANTASMA DE LA RED",
        entrada="", derrota="Conexión... perdida... desconectando...",
        color=(0, 240, 255), color2=(255, 40, 200), llegada="baja", caida="glitch"),
    "tarantula": dict(
        nombre="TARÁNTULA-9", capitulo="TOMO IV · CAPÍTULO 2", apodo="CAZADORA MECÁNICA",
        entrada="", derrota="OBJETIVO... PERDIDO... APAGANDO...",
        color=(255, 60, 80), color2=(255, 230, 40), llegada="baja", caida="cae", femenina=True),
    "kaiser": dict(
        nombre="KAISER CROMADO", capitulo="TOMO IV · CAPÍTULO 3", apodo="PURO CROMO",
        entrada="", derrota="Imposible... ¿Cómo una nave tan chica...?",
        color=(255, 230, 40), color2=(255, 40, 200), llegada="baja", caida="estalla"),
}

# clase del jefe -> ficha (por nombre, para no importar todas las clases)
_CLAVES = {
    "DragonBoss": "dragon", "TitanBoss": "titan", "FinalBoss": "anomalia", "MegaBoss": "coloso",
    "NyanBoss": "nyan", "GatoAlienBoss": "alien", "GatoPanBoss": "oiia",
    "ReyCalabazaBoss": "calabaza", "BrujaBoss": "bruja", "ParcaBoss": "parca",
    "NetrunnerBoss": "netrunner", "TarantulaBoss": "tarantula", "KaiserBoss": "kaiser",
}


def clave_de(boss):
    """Ficha que le toca a un jefe, o None (el duelo de la Parca tiene sus
    propias cinematicas)."""
    nombre = type(boss).__name__
    if nombre == "WaveBoss":
        return "centinela" if getattr(boss.definition, "boss_id", "") == "sentinel" else None
    return _CLAVES.get(nombre)


def retrato(boss):
    """Sprite del jefe tal como se ve ahora. Los de las oleadas tienen
    _sprite() (su draw() suma la barra de vida); los bonus se dibujan
    enteros (la barra va aparte, en draw_ui) y se recortan."""
    metodo = getattr(boss, "_sprite", None)
    if metodo is not None:
        try:
            spr = metodo()
        except TypeError:
            spr = metodo(0)
        if spr is not None:
            return spr.copy()
    lienzo = pygame.Surface((GAME_WIDTH * 2, GAME_HEIGHT * 2), pygame.SRCALPHA)
    guardado = boss.x, boss.y, boss.active
    boss.x, boss.y, boss.active = GAME_WIDTH, GAME_HEIGHT, True
    # sin destellos, y el Gato OIIA de frente (no a mitad de su giro)
    otros = {attr: getattr(boss, attr) for attr in ("flash", "escudo", "angulo") if hasattr(boss, attr)}
    for attr in otros:
        setattr(boss, attr, 0)
    try:
        boss.draw(lienzo)
    finally:
        boss.x, boss.y, boss.active = guardado
        for attr, valor in otros.items():
            setattr(boss, attr, valor)
    zona = lienzo.get_bounding_rect()
    if zona.w == 0:
        return pygame.Surface((8, 8), pygame.SRCALPHA)
    return lienzo.subsurface(zona).copy()


def escala_presentacion(sprite):
    """Cuanto se agranda el jefe en sus cinematicas (de a medio, hasta x2)
    para que se luzca sin tapar los carteles."""
    w, h = sprite.get_size()
    k = min(2.0, 340 / max(1, h), 640 / max(1, w))
    return max(1.0, math.floor(k * 2) / 2)


def _agrandar(sprite, k):
    if k == 1.0:
        return sprite
    return pygame.transform.scale(sprite, (int(sprite.get_width() * k), int(sprite.get_height() * k)))


def _ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


def _oscuro(color, f):
    return tuple(int(c * f) for c in color[:3])


class _Particulas:
    """Cuadraditos de pixel con velocidad, gravedad y vida."""

    def __init__(self):
        self.lista = []

    def soltar(self, x, y, color, cantidad, vel=4.0, vida=(30, 60), tam=(4, 8), grav=0.0, arriba=0.0):
        for _ in range(cantidad):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.3, 1.0) * vel
            self.lista.append([x, y, math.cos(a) * v, math.sin(a) * v - arriba, random.randint(*vida), 0,
                               color if not isinstance(color, (list, tuple)) or isinstance(color[0], int)
                               else random.choice(color), random.randint(*tam), grav])

    def update(self):
        for p in self.lista:
            p[0] += p[2]
            p[1] += p[3]
            p[2] *= 0.97
            p[3] = p[3] * 0.97 + p[8]
            p[5] += 1
        self.lista = [p for p in self.lista if p[5] < p[4]]

    def draw(self, surface):
        for x, y, _, _, vida, edad, color, tam, _ in self.lista:
            k = 1 - edad / vida
            neon.cuadro_pixel(surface, _oscuro(color, 0.4 + 0.6 * k), x, y, max(2, tam * (0.4 + 0.6 * k)))


class _CineBase:
    DURACION = 300
    FUNDIDO = 20

    def __init__(self, clave, sprite, fondo, pixel):
        self.clave = clave
        self.ficha = FICHAS[clave]
        self.sprite_juego = sprite
        self.k = escala_presentacion(sprite)
        self.sprite = _agrandar(sprite, self.k)
        self.blanca = pixelfx.silueta_blanca(self.sprite)
        self.fondo = fondo
        self.pixel = pixel
        self.t = 0
        self.fin = self.DURACION
        self.eventos = []
        self.temblor = 0
        self.particulas = _Particulas()

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 25:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def _sacudir(self, n, evento=None):
        self.temblor = max(self.temblor, n)
        if evento:
            self.eventos.append(evento)

    def _fundidos(self, surface):
        neon.scanlines(surface)
        if self.t < 14:
            neon.velo(surface, NEGRO, int(255 * (1 - self.t / 14)))
        restante = self.fin - self.t
        if restante < self.FUNDIDO:
            neon.velo(surface, NEGRO, int(255 * (1 - max(0, restante) / self.FUNDIDO)))

    def _globo(self, surface, texto, x, y, color):
        if self.ficha.get("habla", True):
            neon.globo(surface, texto, x, y, color, cola_derecha=x > GAME_WIDTH / 2, tam=18)
        else:
            neon.cinta(surface, texto, color, (GAME_WIDTH // 2, 92), tam=20)


# ------------------------------------------------------------------ entrada

class CinematicaEntradaJefe(_CineBase):
    """Alerta, llegada y presentacion del jefe (nombre, capitulo del
    grimorio y su frase)."""

    DURACION = 310
    T_LLEGA = 40      # empieza la llegada
    T_LLEGO = 150     # ya esta en su lugar
    T_NOMBRE = 160

    def __init__(self, clave, sprite, fondo, pixel=False):
        super().__init__(clave, sprite, fondo, pixel)
        w, h = self.sprite.get_size()
        self.destino = (GAME_WIDTH / 2, max(h / 2 + 70, min(250, GAME_HEIGHT - 190 - h / 2)))
        self.x, self.y = self.destino[0], -h
        self.escala = 1.0
        self.alfa = 255
        self.volteo = 1.0
        self.rastro = []
        self.extra = {}

    # cada llegada mueve self.x/y (y escala, alfa, volteo) entre T_LLEGA y T_LLEGO
    def _llegada(self, k, t):
        tipo = self.ficha["llegada"]
        dx, dy = self.destino
        h = self.sprite.get_height()
        c, c2 = self.ficha["color"], self.ficha["color2"]
        if tipo == "escaneo":
            self.y = -h / 2 + (dy + h / 2) * _ease(k)
            if t % 3 == 0 and k > 0.6:
                # chispas que se juntan en el nucleo
                a = random.uniform(0, 2 * math.pi)
                self.particulas.lista.append([dx + math.cos(a) * 160, dy + math.sin(a) * 160,
                                              -math.cos(a) * 5, -math.sin(a) * 5, 32, 0, c2, 6, 0])
            if t == self.T_LLEGO - 10:
                self._sacudir(8, "carga")
        elif tipo == "picada":
            if k < 0.45:   # cruza en picada de arriba a la derecha hacia abajo a la izquierda
                q = k / 0.45
                self.x, self.y = GAME_WIDTH + 200 - q * (GAME_WIDTH + 400), -150 + q * (GAME_HEIGHT + 300)
                self.escala = 0.6
                self.particulas.soltar(self.x, self.y, (c, c2, WHITE), 3, vel=2, vida=(20, 40))
            else:
                q = _ease((k - 0.45) / 0.55)
                self.escala = 1.0
                self.x, self.y = dx, -h + (dy + h) * q
                if t % 2 == 0:
                    self.particulas.soltar(self.x, self.y + h / 2, (c, c2), 2, vel=2.5, vida=(20, 40), arriba=-1.5)
            if t == self.T_LLEGO - 5:
                self._sacudir(16, "golpe")
                self.particulas.soltar(dx, dy, (c, c2, WHITE), 60, vel=9)
        elif tipo == "tentaculos":
            self.extra["tent"] = min(1.0, k * 1.8)
            self.y = -h / 2 + (dy + h / 2) * _ease((k - 0.35) / 0.65)
            if t == self.T_LLEGO - 8:
                self._sacudir(14, "golpe")
        elif tipo == "grieta":
            self.extra["grieta"] = min(1.0, k * 2.2)
            self.x, self.y = dx, dy
            self.alfa = int(255 * max(0.0, min(1.0, (k - 0.4) / 0.5)))
            if t % 14 == 0:
                self.eventos.append("glitch")
                self.temblor = max(self.temblor, 5)
        elif tipo == "gigante":
            # primero su sombra cruza la pantalla, despues baja despacio
            self.extra["sombra"] = k
            self.y = -h / 2 + (dy + h / 2) * _ease((k - 0.4) / 0.6)
            if k > 0.4:
                self.temblor = max(self.temblor, 3)
            if t == self.T_LLEGO - 6:
                self._sacudir(18, "golpe")
        elif tipo == "arcoiris":
            q = _ease(k)
            self.x = -150 + (dx + 150) * q
            self.y = dy + math.sin(t * 0.12) * 40 * (1 - q)
            self.rastro.append((self.x, self.y))
            self.rastro = self.rastro[-70:]
        elif tipo == "giro":
            self.x, self.y = dx, dy
            self.escala = 0.1 + 0.9 * _ease(k)
            self.volteo = math.cos(t * (0.45 - 0.25 * k))
            if t % 20 == 0:
                self.eventos.append("carga")
        elif tipo == "sube":
            q = _ease(k)
            self.y = GAME_HEIGHT + h - (GAME_HEIGHT + h - dy) * q
            if t % 2 == 0:
                self.particulas.soltar(self.x + random.uniform(-60, 60), self.y + h / 2, c2, 2, vel=1.5,
                                       vida=(25, 45), arriba=2.5)
            if t == self.T_LLEGA + 2:
                self._sacudir(10, "golpe")
        elif tipo == "vuelo":
            if k < 0.6:
                q = k / 0.6
                self.x = GAME_WIDTH + 140 - q * (GAME_WIDTH + 280)
                self.y = 170 - math.sin(q * math.pi) * 60
                self.volteo = 1.0
                if t % 2 == 0:
                    self.particulas.soltar(self.x + 40, self.y, (c, c2), 2, vel=1, vida=(30, 50))
            else:
                q = _ease((k - 0.6) / 0.4)
                self.x = -140 + (dx + 140) * q
                self.y = dy - 60 * (1 - q)
                self.volteo = -1.0 if q < 0.98 else 1.0
        elif tipo == "aparicion":
            self.x, self.y = dx, dy
            parpadeo = 0.6 + 0.4 * math.sin(t * 0.9)
            self.alfa = int(255 * max(0.0, min(1.0, (k - 0.2) / 0.7)) * (parpadeo if k < 0.9 else 1))
            if t % 3 == 0:
                self.particulas.soltar(random.uniform(0, GAME_WIDTH), GAME_HEIGHT - 60, (_oscuro(c, 0.5), c),
                                       1, vel=0.6, vida=(60, 90), arriba=1.2, tam=(6, 12))
            if t == self.T_LLEGO - 4:
                self._sacudir(12, "golpe")
                self.extra["tajo"] = t
        else:  # "baja"
            self.y = -h / 2 + (dy + h / 2) * _ease(k)
            if t == self.T_LLEGO - 6:
                self._sacudir(12, "golpe")

    def update(self):
        self.t += 1
        t = self.t
        self.temblor = max(0, self.temblor - 1)
        if t in (2, 24):
            self.eventos.append("alerta")
        if self.T_LLEGA <= t <= self.T_LLEGO:
            self._llegada((t - self.T_LLEGA) / (self.T_LLEGO - self.T_LLEGA), t)
        elif t > self.T_LLEGO:
            dx, dy = self.destino
            self.x, self.y = dx, dy + math.sin((t - self.T_LLEGO) * 0.06) * 6
            self.escala, self.alfa = 1.0, 255
            if self.ficha["llegada"] == "giro":
                self.volteo = math.cos(t * 0.2)
            elif self.ficha["llegada"] != "vuelo":
                self.volteo = 1.0
        self.particulas.update()

    # ---------------------------------------------------------------- draw

    def _sprite_actual(self):
        spr = self.sprite
        if self.escala != 1.0 or abs(self.volteo) != 1.0:
            w = max(1, int(spr.get_width() * self.escala * abs(self.volteo)))
            h = max(1, int(spr.get_height() * self.escala))
            spr = pygame.transform.scale(spr, (w, h))
        if self.volteo < 0:
            spr = pygame.transform.flip(spr, True, False)
        if self.alfa < 255:
            spr = spr.copy()
            spr.set_alpha(self.alfa)
        return spr

    def _dibujar_motivo(self, mundo):
        """Lo que acompaña a cada llegada, detras del jefe."""
        t, tipo = self.t, self.ficha["llegada"]
        c, c2 = self.ficha["color"], self.ficha["color2"]
        dx, dy = self.destino
        if tipo == "escaneo" and self.T_LLEGA < t:
            # rayo tractor que barre el piso
            px = self.x + math.sin(t * 0.07) * 260
            cono = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(cono, (*c, 60), [(self.x - 20, self.y), (self.x + 20, self.y),
                                                 (px + 70, GAME_HEIGHT), (px - 70, GAME_HEIGHT)])
            mundo.blit(cono, (0, 0))
            for x in range(int(px) - 70, int(px) + 70, 12):
                mundo.fill(c if (x // 12 + t // 4) % 2 else c2, (x, GAME_HEIGHT - 70, 8, 4))
        elif tipo == "tentaculos":
            k = self.extra.get("tent", 0)
            for i in range(6):
                base_x = dx + (i - 2.5) * 110
                largo = k * (dy + 120 + (i % 2) * 60)
                for j in range(0, int(largo), 18):
                    ox = math.sin(t * 0.08 + j * 0.03 + i) * (10 + j * 0.08)
                    r = max(5, 16 - j // 30)
                    pygame.draw.circle(mundo, _oscuro(c, 0.55), (int(base_x + ox), j), r + 3)
                    pygame.draw.circle(mundo, c if (j // 18) % 3 else c2, (int(base_x + ox), j), r)
        elif tipo == "grieta":
            k = self.extra.get("grieta", 0)
            if k > 0:
                random.seed(7)
                puntos = [(dx + random.uniform(-30, 30), y) for y in range(int(dy - 220), int(dy + 230), 30)]
                random.seed()
                ancho = 2 + int(k * 26) + int(3 * math.sin(t * 0.5))
                capa = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
                pygame.draw.lines(capa, (*c, 120), False, puntos, ancho + 18)
                pygame.draw.lines(capa, (*c2, 200), False, puntos, ancho + 6)
                pygame.draw.lines(capa, (255, 255, 255, 255), False, puntos, max(2, ancho))
                mundo.blit(capa, (0, 0))
        elif tipo == "gigante":
            k = self.extra.get("sombra", 0)
            if 0 < k < 0.5:
                q = k / 0.5
                sombra = pygame.transform.scale(self.sprite, (self.sprite.get_width() * 3, self.sprite.get_height() * 3))
                sombra = pixelfx.silueta_blanca(sombra).copy()
                sombra.fill((0, 0, 0, 170), special_flags=pygame.BLEND_RGBA_MULT)
                _blit_centrado(mundo, sombra, -sombra.get_width() / 2 + q * (GAME_WIDTH + sombra.get_width()),
                               GAME_HEIGHT / 2)
            if self.T_LLEGA < t and (t // 10) % 2:
                for x in (40, GAME_WIDTH - 40):
                    pixelfx.dibujar_halo(mundo, c2, x, 90, 50)
                    mundo.fill(c2, (x - 8, 82, 16, 16))
        elif tipo == "arcoiris":
            # la estela: una franja de arcoiris por cada lugar por donde paso
            for x, y in self.rastro:
                for b, color in enumerate(ARCOIRIS):
                    mundo.fill(color, (int(x) - 70, int(y) - 27 + b * 9, 14, 9))
            if t % 2 == 0:
                self.particulas.soltar(self.x - 60, self.y, ARCOIRIS, 1, vel=1.2, vida=(20, 40))
        elif tipo == "vuelo":
            # estrellas que titilan a su paso
            for i in range(14):
                sx = (i * 173) % GAME_WIDTH
                sy = 40 + (i * 97) % 260
                if (t // 6 + i) % 4:
                    neon.cuadro_pixel(mundo, c2, sx, sy, 4)
        elif tipo == "sube":
            # llamas verdes al ras del piso
            for x in range(0, GAME_WIDTH, 16):
                alto = 26 + int(16 * math.sin(t * 0.3 + x * 0.05))
                piso = GAME_HEIGHT - 48
                mundo.fill(_oscuro(c2, 0.6), (x, piso - alto, 12, alto))
                mundo.fill(c2, (x + 3, piso - alto + 6, 6, alto - 6))
        elif tipo == "aparicion":
            neon.velo(mundo, (10, 20, 18), 90)

    def _dibujar_jefe(self, mundo):
        spr = self._sprite_actual()
        t = self.t
        if self.ficha["llegada"] == "grieta" and self.alfa > 0 and t < self.T_LLEGO + 20:
            # aparece cortado en franjas (glitch) y con dos clones fantasma
            for lado in (-1, 1):
                fantasma = spr.copy()
                fantasma.set_alpha(70)
                _blit_centrado(mundo, fantasma, self.x + lado * 210, self.y + 10)
            alto = max(6, spr.get_height() // 10)
            for y in range(0, spr.get_height(), alto):
                corrido = random.randint(-24, 24) if random.random() < 0.35 else 0
                mundo.blit(spr, (int(self.x - spr.get_width() / 2 + corrido), int(self.y - spr.get_height() / 2 + y)),
                           (0, y, spr.get_width(), alto))
            return
        # un halo de su color detras, para que se lea sobre fondos oscuros
        radio = 200 if self.ficha["llegada"] == "gigante" else max(spr.get_width(), spr.get_height()) * 0.6
        pixelfx.dibujar_halo(mundo, _oscuro(self.ficha["color"], 0.35 * self.alfa / 255), self.x, self.y, radio)
        _blit_centrado(mundo, spr, self.x, self.y)
        if t > self.T_LLEGO and (t - self.T_LLEGO) < 8:
            blanca = self.blanca.copy()
            blanca.set_alpha(220 - (t - self.T_LLEGO) * 25)
            _blit_centrado(mundo, blanca, self.x, self.y)

    def _dibujar_alerta(self, surface):
        t = self.t
        if t > self.T_LLEGA + 30:
            return
        c2 = self.ficha["color2"]
        k = min(1.0, t / 10) * min(1.0, (self.T_LLEGA + 30 - t) / 12)
        alto = int(46 * k)
        for yc in (GAME_HEIGHT // 2 - 90, GAME_HEIGHT // 2 + 90):
            banda = pygame.Rect(0, yc - alto // 2, GAME_WIDTH, alto)
            surface.fill((20, 4, 10), banda)
            for x in range(-60, GAME_WIDTH + 60, 40):
                xx = x + (t * 4) % 40
                pygame.draw.polygon(surface, c2, [(xx, banda.top), (xx + 20, banda.top),
                                                  (xx + 20 - alto // 2, banda.bottom), (xx - alto // 2, banda.bottom)])
        if alto > 30 and (t // 5) % 6:
            neon.titulo(surface, "¡ALERTA!", 34, WHITE, GAME_WIDTH // 2, GAME_HEIGHT // 2)

    def draw(self, surface):
        t = self.t
        f = self.ficha
        mundo = pygame.Surface(surface.get_size())
        self.fondo(mundo)
        neon.velo(mundo, NEGRO, 90 if t < self.T_LLEGA else 50)
        self._dibujar_motivo(mundo)
        if self.T_LLEGA <= t:
            self._dibujar_jefe(mundo)
        self.particulas.draw(mundo)
        if "tajo" in self.extra and t - self.extra["tajo"] < 16:
            # el tajo de la guadaña cruza la pantalla
            k = (t - self.extra["tajo"]) / 16
            pygame.draw.line(mundo, WHITE, (0, GAME_HEIGHT * (0.9 - k * 0.2)), (GAME_WIDTH, GAME_HEIGHT * (0.1 + k * 0.2)),
                             max(2, int(14 * (1 - k))))
        surface.blit(pixelar(mundo, PIXEL_BONUS) if self.pixel else mundo, (0, 0))

        neon.franjas_cine(surface, t / 25, f["color"], alto=48)
        self._dibujar_alerta(surface)
        if t >= self.T_NOMBRE:
            tam = 50 + int(3 * math.sin(t * 0.2))
            entra = _ease((t - self.T_NOMBRE) / 14)
            cx = int(-300 + (GAME_WIDTH // 2 + 300) * entra)
            neon.titulo(surface, f["nombre"], tam, f["color"], cx, GAME_HEIGHT - 142)
        if f["entrada"] and self.T_NOMBRE + 30 <= t < self.DURACION - 15:
            sh = self.sprite.get_height()
            self._globo(surface, f["entrada"], self.x + 60, max(110, self.y - sh / 2 + 10), f["color2"])
        self._fundidos(surface)


# ------------------------------------------------------------------ derrota

class CinematicaDerrotaJefe(_CineBase):
    """El golpe final: todo se congela, el jefe dice sus ultimas palabras,
    cae a su manera y su pagina del grimorio queda tachada."""

    DURACION = 290
    T_ZOOM = 24
    T_CAE = 96        # el golpe final (estalla / se desvanece / se estrella)
    T_TITULO = 128

    def __init__(self, clave, sprite, fondo, pos, pixel=False):
        super().__init__(clave, sprite, fondo, pixel)
        # la camara se acerca: del lugar donde cayo (a tamaño de juego) al
        # centro y agrandado, en los primeros T_ZOOM cuadros
        self.desde = (max(80, min(GAME_WIDTH - 80, pos[0])), max(80, min(GAME_HEIGHT - 160, pos[1])))
        h = self.sprite.get_height()
        self.centro = (GAME_WIDTH / 2, max(h / 2 + 70, min(250, GAME_HEIGHT - 200 - h / 2)))
        self.x, self.y = self.desde
        self.x0, self.y0 = self.x, self.y
        self.zoom = 1.0
        self.pedazos = []
        self.angulo = 0.0
        self.alfa = 255
        self.zzz = []
        self.caida = self.ficha["caida"]
        self.visible = True

    def _romper(self):
        """El sprite se parte en pedazos reales que salen volando."""
        spr = self.sprite
        w, h = spr.get_size()
        cols = max(3, min(10, w // 14))
        filas = max(3, min(10, h // 14))
        pw, ph = w / cols, h / filas
        for fila in range(filas):
            for col in range(cols):
                rect = pygame.Rect(int(col * pw), int(fila * ph), max(1, int(pw) + 1), max(1, int(ph) + 1)).clip(spr.get_rect())
                if rect.w <= 0 or rect.h <= 0:
                    continue
                pieza = spr.subsurface(rect).copy()
                if pieza.get_bounding_rect().w == 0:
                    continue
                bx, by = rect.centerx - w / 2, rect.centery - h / 2
                d = math.hypot(bx, by) or 1
                v = random.uniform(3, 8)
                self.pedazos.append([self.x + bx, self.y + by, bx / d * v, by / d * v - 2, 0, random.uniform(-12, 12), pieza])
        self.visible = False

    def update(self):
        self.t += 1
        t = self.t
        c, c2 = self.ficha["color"], self.ficha["color2"]
        self.temblor = max(0, self.temblor - 1)
        if t == 1:
            self._sacudir(14, "golpe")
            self.particulas.soltar(self.x, self.y, (c, c2, WHITE), 40, vel=7)
        caida = self.caida
        if t <= self.T_ZOOM:
            e = _ease(t / self.T_ZOOM)
            self.zoom = 1 + (self.k - 1) * e
            self.x0 = self.desde[0] + (self.centro[0] - self.desde[0]) * e
            self.y0 = self.desde[1] + (self.centro[1] - self.desde[1]) * e
            self.x, self.y = self.x0, self.y0
        if t < self.T_CAE:
            if caida == "duerme":
                # gira cada vez mas lento hasta quedarse quieto
                self.angulo = math.cos(t * max(0.0, 0.5 - t * 0.005))
            elif caida == "cae":
                # humo y chispas: se va inclinando y empieza a caer
                self.angulo = min(35, t * 0.5)
                if t > 50:
                    self.y += (t - 50) * 0.25
                if t % 3 == 0:
                    self.particulas.soltar(self.x + random.uniform(-30, 30), self.y, ((70, 70, 80), (120, 120, 130)), 1,
                                           vel=1, vida=(40, 70), arriba=1.5, tam=(8, 14))
            else:
                self.x = self.x0 + random.randint(-4, 4) * (t % 2)
                if t % 9 == 0:
                    # explosiones chicas sobre el cuerpo
                    w, h = self.sprite.get_size()
                    ex, ey = self.x + random.uniform(-w / 3, w / 3), self.y + random.uniform(-h / 3, h / 3)
                    self.particulas.soltar(ex, ey, (c, c2, WHITE), 14, vel=4, vida=(15, 30))
                    self.eventos.append("explosion")
                    self.temblor = max(self.temblor, 6)
            if caida == "desvanece" and t > 40:
                self.alfa = max(0, int(255 * (1 - (t - 40) / (self.T_CAE - 40))))
                if t % 2 == 0:
                    w, h = self.sprite.get_size()
                    self.particulas.soltar(self.x + random.uniform(-w / 2, w / 2), self.y + random.uniform(-h / 2, h / 2),
                                           (c, WHITE), 2, vel=0.5, vida=(40, 70), arriba=2, tam=(6, 10))
        elif t == self.T_CAE:
            if caida == "duerme":
                self.eventos.append("carga")
            elif caida == "desvanece":
                self.visible = False
                self._sacudir(10, "golpe")
                self.particulas.soltar(self.x, self.y, (c, WHITE), 50, vel=3, vida=(50, 90), arriba=1.5)
            elif caida == "cae":
                self.visible = False
                self.y = GAME_HEIGHT - 70
                self._sacudir(22, "golpe")
                self.particulas.soltar(self.x, self.y, ((255, 200, 60), (255, 120, 40), WHITE), 90, vel=10, grav=0.15,
                                       arriba=4)
            else:
                self._romper()
                self._sacudir(24, "golpe")
                colores = {
                    "arcoiris": ARCOIRIS, "estrellas": (c, c2, WHITE, (255, 235, 140)),
                    "glitch": (c, c2, WHITE, (0, 0, 0)),
                }.get(caida, (c, c2, WHITE, (255, 200, 60)))
                self.particulas.soltar(self.x, self.y, colores, 140, vel=11, vida=(40, 90), tam=(4, 10))
        if caida == "duerme" and t >= self.T_CAE and t % 26 == 0:
            self.zzz.append([self.x + 40, self.y - 40, t])
        for p in self.pedazos:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.12
            p[4] += p[5]
        self.pedazos = [p for p in self.pedazos if p[1] < GAME_HEIGHT + 80]
        self.particulas.update()

    def draw(self, surface):
        t = self.t
        f = self.ficha
        c, c2 = f["color"], f["color2"]
        mundo = pygame.Surface(surface.get_size())
        self.fondo(mundo)
        neon.velo(mundo, NEGRO, 70)
        if t < self.T_CAE and self.caida not in ("duerme", "cae"):
            # rayos de luz que salen del jefe y giran
            capa = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
            largo = 900
            for i in range(10):
                a = i * math.pi / 5 + t * 0.03
                abre = 0.06 + 0.04 * (t / self.T_CAE)
                pts = [(self.x, self.y),
                       (self.x + math.cos(a - abre) * largo, self.y + math.sin(a - abre) * largo),
                       (self.x + math.cos(a + abre) * largo, self.y + math.sin(a + abre) * largo)]
                pygame.draw.polygon(capa, (*(c if i % 2 else c2), 30 + int(60 * t / self.T_CAE)), pts)
            mundo.blit(capa, (0, 0))
        if self.visible:
            spr = self.sprite if t > self.T_ZOOM else _agrandar(self.sprite_juego, self.zoom)
            if self.caida == "duerme":
                w = max(1, int(spr.get_width() * abs(self.angulo)))
                spr = pygame.transform.scale(spr, (w, spr.get_height()))
                if self.angulo < 0:
                    spr = pygame.transform.flip(spr, True, False)
            elif self.caida == "cae":
                spr = pygame.transform.rotate(spr, -self.angulo)
            elif self.caida == "glitch" and t > 30 and random.random() < 0.3:
                spr = spr.copy()
                spr.fill((*c2, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if self.alfa < 255:
                spr = spr.copy()
                spr.set_alpha(self.alfa)
            pixelfx.dibujar_halo(mundo, _oscuro(c, 0.3 * self.alfa / 255), self.x, self.y,
                                 max(spr.get_width(), spr.get_height()) * 0.6)
            _blit_centrado(mundo, spr, self.x, self.y)
            if self.caida not in ("duerme",) and t < self.T_CAE and (t // 4) % 3 == 0:
                blanca = pixelfx.silueta_blanca(spr)
                _blit_centrado(mundo, blanca, self.x, self.y)
        for x, y, _, _, ang, _, pieza in self.pedazos:
            rot = pygame.transform.rotate(pieza, ang)
            _blit_centrado(mundo, rot, x, y)
        self.particulas.draw(mundo)
        surface.blit(pixelar(mundo, PIXEL_BONUS) if self.pixel else mundo, (0, 0))

        for x, y, t0 in self.zzz:
            edad = t - t0
            neon.titulo(surface, "Z" if edad % 52 < 26 else "z", 22 + edad // 6, WHITE,
                        x + math.sin(edad * 0.1) * 12 + edad * 0.6, y - edad * 1.2, halo=False)
        neon.franjas_cine(surface, t / 20, c2, alto=48)
        if f["derrota"] and 12 <= t < self.T_CAE - 4:
            letras = f["derrota"][:max(1, (t - 12) // 2)]
            sh = self.sprite.get_height()
            self._globo(surface, letras, self.x + 60, max(110, self.y - sh / 2 + 6), c)
        if self.T_CAE <= t < self.T_CAE + 10 and self.caida != "duerme":
            neon.velo(surface, WHITE, 255 * (1 - (t - self.T_CAE) / 10))
        if t >= self.T_TITULO:
            verbo = {"duerme": "SE DURMIÓ", "desvanece": "SE DESVANECE"}.get(self.caida, "DERROTADO")
            if f.get("femenina") and verbo == "DERROTADO":
                verbo = "DERROTADA"
            y = GAME_HEIGHT - 190   # debajo del jefe (el Gato OIIA se queda dormido ahi)
            if (t - self.T_TITULO) < 6 or (t // 5) % 6:
                neon.titulo(surface, f"¡{f['nombre']} {verbo}!", 40, c, GAME_WIDTH // 2, y)
        self._fundidos(surface)


# ------------------------------------------------------- renacer del Coloso

class CinematicaRenacerColoso(_CineBase):
    """A la mitad de la pelea el Coloso no explota y se rearma en el juego:
    el crucero se sobrecarga y estalla, sus pedazos quedan flotando y un
    nucleo que late los atrapa con tentaculos de luz; en una especie de
    simbiosis cada pedazo cambia de forma y se suelda en la ESFERA DE
    COMBATE (fase 2). Despues sigue el combate (main._cinematica_renacer_coloso)."""

    DURACION = 500
    T_ZOOM = 24
    T_ESTALLA = 96
    T_UNION = 176       # el nucleo empieza a tirar de los pedazos
    T_LLEGAN = 236      # el ultimo pedazo arranca aca (y tarda DUR_VIAJE)
    DUR_VIAJE = 110
    T_ESFERA = 360      # la esfera queda entera
    T_TITULO = 384
    VIVO = (90, 255, 210)   # color de los tentaculos (la "simbiosis")

    def __init__(self, crucero, esfera, fondo, pos, pixel=False):
        super().__init__("coloso", crucero, fondo, pixel)
        self.k_esfera = escala_presentacion(esfera)
        self.esfera = _agrandar(esfera, self.k_esfera)
        self.esfera_blanca = pixelfx.silueta_blanca(self.esfera)
        self.desde = (max(160, min(GAME_WIDTH - 160, pos[0])), max(90, min(GAME_HEIGHT - 200, pos[1])))
        self.centro = (GAME_WIDTH / 2, 270)
        self.x, self.y = self.desde
        self.zoom = 1.0
        self.visible = True
        self.trozos = []
        self.nucleo = 0.0      # tamaño del nucleo que late (0 = no esta)
        self.ondas = []

    # pedazos -----------------------------------------------------------

    @staticmethod
    def _cortar(spr, cols, filas):
        w, h = spr.get_size()
        piezas = []
        for fila in range(filas):
            for col in range(cols):
                rect = pygame.Rect(col * w // cols, fila * h // filas,
                                   (col + 1) * w // cols - col * w // cols,
                                   (fila + 1) * h // filas - fila * h // filas)
                pieza = spr.subsurface(rect).copy()
                if pieza.get_bounding_rect().w == 0:
                    continue
                piezas.append((pieza, rect.centerx - w / 2, rect.centery - h / 2))
        return piezas

    def _estallar(self):
        """El crucero se parte; a cada pedazo le toca uno de la esfera (en
        el que se va a convertir) y una hora para empezar a volver."""
        cx, cy = self.x, self.y
        del_crucero = self._cortar(self.sprite, 9, 5)
        de_la_esfera = self._cortar(self.esfera, 7, 7)
        random.shuffle(de_la_esfera)
        n = max(len(del_crucero), len(de_la_esfera))
        for i in range(n):
            sc = del_crucero[i] if i < len(del_crucero) else None
            se = de_la_esfera[i] if i < len(de_la_esfera) else None
            base = sc or del_crucero[i % len(del_crucero)]
            d = math.hypot(base[1], base[2]) or 1.0
            v = random.uniform(5, 11)
            self.trozos.append({
                "x": cx + base[1], "y": cy + base[2],
                "vx": base[1] / d * v + random.uniform(-1, 1), "vy": base[2] / d * v + random.uniform(-1, 1),
                "ang": 0.0, "giro": random.uniform(-6, 6),
                "crucero": sc[0] if sc else None, "esfera": se[0] if se else None,
                "dx": se[1] if se else 0.0, "dy": se[2] if se else 0.0,
                # los de mas afuera vuelven al final: la esfera se arma de adentro hacia afuera
                "sale": 0, "p": 0.0, "llego": False,
                "dist": math.hypot(se[1], se[2]) if se else 999.0,
            })
        orden = sorted(self.trozos, key=lambda tr: tr["dist"])
        for i, tr in enumerate(orden):
            tr["sale"] = self.T_UNION + int((self.T_LLEGAN - self.T_UNION) * i / max(1, len(orden) - 1))
            tr["x0"] = tr["y0"] = None
        self.visible = False

    # update ------------------------------------------------------------

    def update(self):
        self.t += 1
        t = self.t
        c, c2 = self.ficha["color"], self.ficha["color2"]
        self.temblor = max(0, self.temblor - 1)
        if t <= self.T_ZOOM:
            e = _ease(t / self.T_ZOOM)
            self.zoom = 1 + (self.k - 1) * e
            self.x = self.desde[0] + (self.centro[0] - self.desde[0]) * e
            self.y = self.desde[1] + (self.centro[1] - self.desde[1]) * e
        if t == 1:
            self._sacudir(12, "golpe")
        if t < self.T_ESTALLA:
            # sobrecarga: explosiones chicas cada vez mas seguidas
            if t > self.T_ZOOM and t % max(3, 12 - t // 10) == 0:
                w, h = self.sprite.get_size()
                ex, ey = self.x + random.uniform(-w / 2.4, w / 2.4), self.y + random.uniform(-h / 3, h / 3)
                self.particulas.soltar(ex, ey, (c, (255, 120, 40), WHITE), 12, vel=4, vida=(14, 28))
                self.temblor = max(self.temblor, 5)
                if t % 2 == 0:
                    self.eventos.append("explosion")
        elif t == self.T_ESTALLA:
            self._estallar()
            self._sacudir(26, "golpe")
            self.eventos.append("explosion")
            self.particulas.soltar(self.x, self.y, (c, c2, WHITE, (255, 120, 40)), 160, vel=13, vida=(40, 90),
                                   tam=(4, 10))
            self.ondas.append([self.x, self.y, 0, WHITE])
        if t >= self.T_ESTALLA + 30:
            # el nucleo: primero una chispa que late, despues crece
            objetivo = 26 if t < self.T_ESFERA else 0
            self.nucleo += (objetivo - self.nucleo) * 0.05
            if t == self.T_ESTALLA + 50:
                self.eventos.append("carga")
        for tr in self.trozos:
            if t < tr["sale"]:
                # flotan y se frenan, girando despacio
                tr["x"] += tr["vx"]
                tr["y"] += tr["vy"]
                tr["vx"] *= 0.93
                tr["vy"] *= 0.93
                tr["ang"] += tr["giro"]
                tr["giro"] *= 0.97
                # que no se escapen de la pantalla
                tr["x"] = max(30, min(GAME_WIDTH - 30, tr["x"]))
                tr["y"] = max(70, min(GAME_HEIGHT - 70, tr["y"]))
            elif not tr["llego"]:
                if tr["x0"] is None:
                    tr["x0"], tr["y0"], tr["ang0"] = tr["x"], tr["y"], tr["ang"] % 360
                    if tr["ang0"] > 180:
                        tr["ang0"] -= 360
                tr["p"] = min(1.0, (t - tr["sale"]) / self.DUR_VIAJE)
                # un tirón: primero se acercan despacio, despues se sueldan rapido
                e = tr["p"] ** 2.2
                tx, ty = self.centro[0] + tr["dx"], self.centro[1] + tr["dy"]
                curva = math.sin(tr["p"] * math.pi) * 40 * (1 if tr["dx"] >= 0 else -1)
                tr["x"] = tr["x0"] + (tx - tr["x0"]) * e + curva * (1 - e)
                tr["y"] = tr["y0"] + (ty - tr["y0"]) * e
                tr["ang"] = tr["ang0"] * (1 - e)
                if tr["p"] >= 1.0:
                    tr["llego"] = True
                    if tr["esfera"] is not None:
                        self.particulas.soltar(tx, ty, (self.VIVO, WHITE), 6, vel=3, vida=(10, 22), tam=(3, 6))
                    if random.random() < 0.18:
                        self.eventos.append("glitch")
                elif random.random() < 0.08:
                    # chispitas que corren por el tentaculo hacia el nucleo
                    self.particulas.soltar(tr["x"], tr["y"], self.VIVO, 1, vel=1, vida=(14, 24), tam=(3, 5))
        if t == self.T_ESFERA:
            self._sacudir(20, "golpe")
            self.eventos.append("carga")
            self.ondas.append([self.centro[0], self.centro[1], 0, c2])
            self.ondas.append([self.centro[0], self.centro[1], -8, self.VIVO])
            self.particulas.soltar(self.centro[0], self.centro[1], ARCOIRIS + (WHITE,), 90, vel=10, vida=(30, 70))
        for o in self.ondas:
            o[2] += 1
        self.ondas = [o for o in self.ondas if o[2] < 50]
        self.particulas.update()

    # draw --------------------------------------------------------------

    def _tentaculo(self, mundo, x0, y0, x1, y1, fase, color):
        """Hilo de cuadraditos que ondula como algo vivo."""
        largo = math.hypot(x1 - x0, y1 - y0)
        if largo < 4:
            return
        nx, ny = -(y1 - y0) / largo, (x1 - x0) / largo
        pasos = max(4, int(largo / 7))
        for i in range(pasos + 1):
            k = i / pasos
            onda = math.sin(k * 7 + fase) * 10 * math.sin(k * math.pi)
            x = x0 + (x1 - x0) * k + nx * onda
            y = y0 + (y1 - y0) * k + ny * onda
            neon.cuadro_pixel(mundo, color if i % 3 else WHITE, x, y, 4 if 0.15 < k < 0.85 else 6)

    def draw(self, surface):
        t = self.t
        f = self.ficha
        c, c2 = f["color"], f["color2"]
        mundo = pygame.Surface(surface.get_size())
        self.fondo(mundo)
        neon.velo(mundo, NEGRO, 90 if t < self.T_ESTALLA else 130)
        cx, cy = self.centro

        if self.visible:
            spr = self.sprite if t > self.T_ZOOM else _agrandar(self.sprite_juego, self.zoom)
            x = self.x + (random.randint(-4, 4) if t > self.T_ZOOM else 0)
            pixelfx.dibujar_halo(mundo, _oscuro((255, 120, 40), 0.25 + 0.3 * t / self.T_ESTALLA), x, self.y,
                                 spr.get_width() * 0.55)
            _blit_centrado(mundo, spr, x, self.y)
            if (t // 3) % 4 == 0 or t > self.T_ESTALLA - 16:
                blanca = pixelfx.silueta_blanca(spr)
                blanca.set_alpha(120 + int(135 * min(1.0, t / self.T_ESTALLA)))
                _blit_centrado(mundo, blanca, x, self.y)

        if self.nucleo > 1 and t < self.T_ESFERA:
            late = 1 + 0.25 * math.sin(t * 0.25)
            pixelfx.dibujar_halo(mundo, _oscuro(c2, 0.6), cx, cy, self.nucleo * 3 * late)
            neon.cuadro_pixel(mundo, c2, cx, cy, self.nucleo * late)
            neon.cuadro_pixel(mundo, WHITE, cx, cy, self.nucleo * 0.45 * late)

        # tentaculos del nucleo a cada pedazo que todavia no se soldo
        if self.T_UNION - 30 <= t < self.T_ESFERA:
            for i, tr in enumerate(self.trozos):
                if tr["llego"] or t < tr["sale"] - 30:
                    continue
                color = self.VIVO if i % 2 else c2
                self._tentaculo(mundo, cx, cy, tr["x"], tr["y"], t * 0.2 + i, color)

        # pedazos: el del crucero se va convirtiendo en el de la esfera
        for tr in self.trozos:
            if t >= self.T_ESFERA:
                break
            p = tr["p"]
            for surf, alfa in ((tr["crucero"], 1 - p), (tr["esfera"], p)):
                if surf is None or alfa <= 0.02:
                    continue
                pieza = surf
                if tr["ang"]:
                    pieza = pygame.transform.rotate(pieza, tr["ang"])
                if alfa < 0.98:
                    pieza = pieza.copy()
                    pieza.set_alpha(int(255 * alfa))
                _blit_centrado(mundo, pieza, tr["x"], tr["y"])
            if 0.6 < p < 1.0 and (t // 2) % 2 == 0 and tr["esfera"] is not None:
                blanca = pixelfx.silueta_blanca(tr["esfera"])
                blanca.set_alpha(110)
                _blit_centrado(mundo, blanca, tr["x"], tr["y"])

        if t >= self.T_ESFERA:
            late = 1 + 0.04 * math.sin(t * 0.15)
            pixelfx.dibujar_halo(mundo, _oscuro(c2, 0.45), cx, cy, self.esfera.get_width() * 0.62 * late)
            _blit_centrado(mundo, self.esfera, cx, cy)
            k = (t - self.T_ESFERA) / 24
            if k < 1:
                blanca = self.esfera_blanca.copy()
                blanca.set_alpha(int(255 * (1 - k)))
                _blit_centrado(mundo, blanca, cx, cy)

        for x, y, edad, color in self.ondas:
            if edad > 0:
                neon.anillo_pixel(mundo, pixelfx.apagar(color, 1 - edad / 50), x, y, 30 + edad * 11, tam=6)
        self.particulas.draw(mundo)
        surface.blit(pixelar(mundo, PIXEL_BONUS) if self.pixel else mundo, (0, 0))

        neon.franjas_cine(surface, t / 20, c2, alto=48)
        if t < self.T_ESTALLA:
            if t > 30:
                frase = "¿Crees que esto se acabó?"
                self._globo(surface, frase[:max(1, (t - 30) // 2)], self.x + 120,
                            self.y - self.sprite.get_height() / 2 + 10, c)
        if self.T_ESTALLA <= t < self.T_ESTALLA + 12:
            neon.velo(surface, WHITE, 255 * (1 - (t - self.T_ESTALLA) / 12))
        if self.T_ESFERA <= t < self.T_ESFERA + 8:
            neon.velo(surface, WHITE, 200 * (1 - (t - self.T_ESFERA) / 8))
        if t >= self.T_TITULO:
            y = GAME_HEIGHT - 120
            if (t - self.T_TITULO) < 6 or (t // 5) % 6:
                neon.titulo(surface, "ESFERA DE COMBATE", 40, c2, GAME_WIDTH // 2, y)
            if t >= self.T_TITULO + 20:
                frase = "Lo que es parte de mí nunca muere del todo."
                self._globo(surface, frase[:max(1, (t - self.T_TITULO - 20) // 2)], cx + 110,
                            cy - self.esfera.get_height() / 2 + 6, c2)
        self._fundidos(surface)
