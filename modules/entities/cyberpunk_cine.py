"""
Cinematicas de la ruta cyberpunk (ver cyberpunk.py y main.py):

  - CinematicaVictoriaCyber: la VICTORIA falsa hackeada (lluvia de codigo,
    una terminal que escribe sola y "ACCESO CONCEDIDO").
  - CinematicaEntradaCyber: la entrada de cada uno de los tres jefes.
  - CinematicaLuna: el final. La nave viaja a la Luna y aterriza, Lucy
    baja, camina y se queda mirando la Tierra en el horizonte. Al terminar
    la escena sigue animada detras de la victoria final, que sale al
    costado (ver ui.draw_victory_lateral y la victoria en main.py).

Interfaz de las otras cinematicas: update(), draw(surface), terminada,
saltar(), temblor y eventos."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from modules.systems import neon
from modules.systems.fonts import get_font
from modules.entities.nyan_boss import PIXEL_BONUS, CinematicaVictoriaFalsa, pixelar, _blit_centrado
from modules.entities.cyberpunk import (
    FondoCyber, NetrunnerBoss, TarantulaBoss, KaiserBoss, sprite_cyber, _dibujar_glitch,
    PALABRAS_CYBER, COLORES_CYBER, CIAN, MAGENTA, AMARILLO, ROJO, VERDE_CODIGO,
)

NEGRO = (0, 0, 0)


def _ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


_GLIFOS = {}


def _glifo(caracter, color):
    clave = (caracter, color)
    s = _GLIFOS.get(clave)
    if s is None:
        s = get_font(16, bold=True).render(caracter, True, color)
        _GLIFOS[clave] = s
    return s


# ------------------------------------------------------- victoria hackeada

class CinematicaVictoriaCyber(CinematicaVictoriaFalsa):
    """La VICTORIA falsa, pero a mitad del glitch la hackean: llueve codigo
    verde, todo se tiñe de cian y magenta, las palabras pasan a ser de
    hacker ("BREACH PROTOCOL", "ICE ROTO"...), una terminal escribe sola y
    al final una franja de peligro amarilla con "ACCESO CONCEDIDO".
    eventos agrega "hackeo" (cuando empieza) y "acceso"."""

    P_HACK = 0.3
    P_ACCESO = 0.78
    LINEAS = ("> conectando a VICTORIA.EXE ...", "> rompiendo ICE .......... OK",
              "> instalando daemon ....... OK", "> jefes encontrados: 3", "> bienvenido a NEO CIUDAD_")

    def __init__(self, captura):
        super().__init__(captura)
        self.hackeado = False
        self.acceso = False
        self.columnas = []

    def update(self):
        super().update()
        p = self._progreso()
        if self.t >= self.DURACION_NORMAL and p >= self.P_HACK and not self.hackeado:
            self.hackeado = True
            self.eventos.append("hackeo")
            self.temblor = 14
            self.PALABRAS = PALABRAS_CYBER
            self.COLORES = COLORES_CYBER
            self.COLORES_PANEL = (CIAN, MAGENTA, AMARILLO)
            self.TITULO_COLOR = AMARILLO
            self.columnas = [[x, random.uniform(-GAME_HEIGHT, 0), random.uniform(6, 12), random.randint(6, 16)]
                             for x in range(8, GAME_WIDTH, 22)]
        if p >= self.P_ACCESO and not self.acceso:
            self.acceso = True
            self.eventos.append("acceso")
            self.temblor = 10
        for c in self.columnas:
            c[1] += c[2]
            if c[1] - c[3] * 18 > GAME_HEIGHT:
                c[1] = random.uniform(-200, 0)

    def _dibujar_extra(self, surface, p):
        if not self.hackeado:
            return
        tinte = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        tinte.fill((*(CIAN if (self.t // 5) % 2 else MAGENTA), 50))
        surface.blit(tinte, (0, 0))
        # lluvia de codigo: la cabeza blanca, la cola verde
        for i, (x, y, v, largo) in enumerate(self.columnas):
            for k in range(largo):
                cy = y - k * 18
                if -18 < cy < GAME_HEIGHT:
                    caracter = "01"[(i * 7 + k * 3 + self.t // 4) % 2]
                    surface.blit(_glifo(caracter, WHITE if k == 0 else VERDE_CODIGO), (x, int(cy)))
        # terminal que escribe sola
        k = (p - self.P_HACK) / (self.P_ACCESO - self.P_HACK)
        caja = pygame.Rect(30, GAME_HEIGHT - 210, 520, 180)
        neon.panel(surface, caja, CIAN, self.t, halo=False, alfa=220)
        fuente = get_font(18, bold=True)
        letras = int(k * sum(len(linea) for linea in self.LINEAS))
        for n, linea in enumerate(self.LINEAS):
            if letras <= 0:
                break
            texto = fuente.render(linea[:letras], True, AMARILLO if n == len(self.LINEAS) - 1 else VERDE_CODIGO)
            surface.blit(texto, (caja.x + 18, caja.y + 18 + n * 30))
            letras -= len(linea)
        if self.acceso:
            # franja de peligro amarilla y negra con ACCESO CONCEDIDO
            y = GAME_HEIGHT // 2 + 92
            surface.fill(AMARILLO, (0, y, GAME_WIDTH, 64))
            for x in range(-64, GAME_WIDTH + 64, 48):
                desplaza = (self.t * 3) % 48
                pygame.draw.polygon(surface, NEGRO, ((x + desplaza, y), (x + desplaza + 22, y),
                                                     (x + desplaza - 2, y + 64), (x + desplaza - 24, y + 64)))
            caja = pygame.Rect(0, 0, 520, 50)
            caja.center = (GAME_WIDTH // 2, y + 32)
            surface.fill(NEGRO, caja)
            self._texto_glitch(surface, "ACCESO CONCEDIDO", 40, AMARILLO, GAME_WIDTH // 2 + random.randint(-3, 3),
                               y + 32, 3)


# ------------------------------------------------------ entrada de los jefes

class CinematicaEntradaCyber:
    """Antes de cada jefe de la ruta: la ciudad bajo la lluvia y el jefe
    que llega a su manera (el Netrunner se materializa en glitch, la
    Tarantula baja colgada de un cable, el Kaiser aterriza con los
    propulsores), con su nombre y una frase. eventos: "glitch", "golpe",
    "ojos", "carga" (sonidos en main.py)."""

    DURACION = 330
    FUNDIDO = 20
    DATOS = {
        "netrunner": (NetrunnerBoss, "JEFE 1 / 3  -  EL FANTASMA DE LA RED", "Tu nave ya es mia. Solo vine a borrarte."),
        "tarantula": (TarantulaBoss, "JEFE 2 / 3  -  CAZADORA MECANICA", "OBJETIVO DETECTADO. INICIANDO CAZA."),
        "kaiser": (KaiserBoss, "JEFE FINAL  -  PURO CROMO", "¿Todo eso para llegar hasta mi? Que tierno."),
    }

    def __init__(self, jefe):
        self.jefe = jefe
        self.t = 0
        self.fin = self.DURACION
        self.eventos = []
        self.temblor = 0
        self.fondo = FondoCyber()
        clase, self.subtitulo, self.frase = self.DATOS[jefe]
        self.boss = clase(1.0)
        self.boss.entrando = False
        self.boss.x = GAME_WIDTH / 2
        self.boss.y = -300

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 30:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        self.fondo.update()
        t, b = self.t, self.boss
        b.t = t
        if self.jefe == "netrunner":
            b.y = 230 + math.sin(t * 0.05) * 10
            b.alfa = max(0.0, min(1.0, (t - 70) / 70))
            b.hackea = 30 if 150 <= t < 300 else 0
            if t in (30, 55, 75, 100):
                self.eventos.append("glitch")
                self.temblor = 6
        elif self.jefe == "tarantula":
            k = _ease((t - 40) / 60)
            b.y = -200 + k * 430
            b.paso += 0.08 if t < 100 else 0
            if t == 100:
                self.eventos.append("golpe")
                self.temblor = 14
            if t in (120, 135, 150):
                self.eventos.append("ojos")
            b.dispara = 8 if 230 <= t < 260 and t % 10 < 5 else 0
        else:
            k = _ease((t - 30) / 80)
            b.y = -240 + k * 470
            if t == 110:
                self.eventos.append("golpe")
                self.temblor = 16
            if t == 170:
                self.eventos.append("carga")
            b.dispara = 6 if 170 <= t < 230 else 0

    def _dibujar_mundo(self, mundo):
        t, b = self.t, self.boss
        self.fondo.draw(mundo)
        if self.jefe == "tarantula":
            # el cable del que baja colgada
            mundo.fill((150, 150, 180), (int(b.x) - 2, 0, 4, max(0, int(b.y) - 50)))
            if t < 40:
                neon.velo(mundo, NEGRO, 160)
        if self.jefe == "netrunner" and t < 140:
            spr = sprite_cyber("netrunner", 0, b.ESCALA)
            if b.alfa > 0:
                _dibujar_glitch(mundo, spr, b.x, b.y, 40 * (1 - b.alfa), int(255 * b.alfa))
        else:
            b.draw(mundo)
        if self.jefe == "kaiser" and 170 <= t < 230:
            # el cañon carga: anillo que se cierra en la boca
            cx, cy = b._boca_canon()
            r = int(40 - (t - 170) * 0.6)
            pygame.draw.circle(mundo, CIAN if (t // 4) % 2 else WHITE, (int(cx), int(cy)), max(6, r), 4)

    def draw(self, surface):
        t = self.t
        mundo = pygame.Surface(surface.get_size())
        self._dibujar_mundo(mundo)
        surface.blit(pixelar(mundo, PIXEL_BONUS), (0, 0))
        neon.franjas_cine(surface, t / 25, CIAN if self.jefe != "kaiser" else AMARILLO, alto=48)
        if self.jefe == "netrunner" and 10 <= t < 90:
            texto = "> conexion entrante desde ???"[:max(0, (t - 10) // 2)]
            neon.titulo(surface, texto, 26, VERDE_CODIGO, GAME_WIDTH // 2, GAME_HEIGHT // 2, halo=False)
        if self.jefe == "tarantula" and 120 <= t:
            ojos = min(6, (t - 120) // 6 + 1)
            if t < 160:
                for k in range(ojos):
                    x = GAME_WIDTH // 2 - 30 + (k % 3) * 30
                    neon.cuadro_pixel(surface, ROJO, x, 245 + (k // 3) * 10, 4)
        if t >= 150:
            tam = 54 + int(3 * math.sin(t * 0.2))
            color = {"netrunner": CIAN, "tarantula": ROJO, "kaiser": AMARILLO}[self.jefe]
            neon.titulo(surface, self.boss.nombre, tam, color, GAME_WIDTH // 2, GAME_HEIGHT - 150)
        if 190 <= t < 310:
            if self.jefe == "tarantula":
                neon.cinta(surface, self.frase, ROJO, (GAME_WIDTH // 2, 100), tam=18)
            else:
                neon.globo(surface, self.frase, GAME_WIDTH / 2 + 70, 130,
                           MAGENTA if self.jefe == "netrunner" else AMARILLO, cola_derecha=False, tam=20)
        neon.scanlines(surface)
        if t < 16:
            neon.velo(surface, NEGRO, int(255 * (1 - t / 16)))
        restante = self.fin - t
        if restante < self.FUNDIDO:
            neon.velo(surface, NEGRO, int(255 * (1 - max(0, restante) / self.FUNDIDO)))


# ----------------------------------------------------------- final en la Luna

_TIERRA_R = 36      # radio en "pixeles de arte" (se dibuja x3)
_TIERRA_ESCALA = 3
_TIERRA_PASOS = 120  # cuadros de una vuelta completa (se cachean)


class _Tierra:
    """La Tierra vista desde la Luna: continentes y nubes que giran, el
    lado de noche con luces de ciudades y un halo de atmosfera."""

    def __init__(self):
        rng = random.Random(2077)
        self.ancho, self.alto = 96, 48
        # continentes: manchas al azar sumadas y cortadas en un umbral
        manchas = [(rng.uniform(0, self.ancho), rng.uniform(6, self.alto - 6), rng.uniform(4, 11)) for _ in range(22)]
        nubes = [(rng.uniform(0, self.ancho), rng.uniform(4, self.alto - 4), rng.uniform(2, 5)) for _ in range(30)]
        self.tierra = [[False] * self.ancho for _ in range(self.alto)]
        self.nubes = [[False] * self.ancho for _ in range(self.alto)]
        for v in range(self.alto):
            for u in range(self.ancho):
                for tabla, lista, umbral in ((self.tierra, manchas, 1.0), (self.nubes, nubes, 1.2)):
                    total = 0.0
                    for mx, my, r in lista:
                        dx = min(abs(u - mx), self.ancho - abs(u - mx))
                        total += math.exp(-((dx * dx + (v - my) ** 2) / (r * r)))
                    tabla[v][u] = total > umbral
        # por cada pixel del disco: longitud, fila de la textura y luz
        self.pixeles = []
        luz = (0.5, -0.3, 0.81)
        r = _TIERRA_R
        for y in range(2 * r):
            for x in range(2 * r):
                nx, ny = (x + 0.5 - r) / r, (y + 0.5 - r) / r
                d = nx * nx + ny * ny
                if d >= 1:
                    continue
                nz = math.sqrt(1 - d)
                lat = math.asin(-ny)
                lon = math.atan2(nx, nz)
                fila = int((0.5 - lat / math.pi) * (self.alto - 1))
                brillo = max(0.0, nx * luz[0] + ny * luz[1] + nz * luz[2])
                self.pixeles.append((x, y, lon / (2 * math.pi), fila, brillo, abs(lat) > 1.2))
        # desiertos: otras manchas, mas chicas, dentro de los continentes
        arenas = [(rng.uniform(0, self.ancho), rng.uniform(14, self.alto - 14), rng.uniform(3, 6)) for _ in range(9)]
        self.desierto = [[sum(math.exp(-((min(abs(u - mx), self.ancho - abs(u - mx)) ** 2 + (v - my) ** 2) / (r * r)))
                              for mx, my, r in arenas) > 0.7 for u in range(self.ancho)] for v in range(self.alto)]
        self.cuadros = {}

    def cuadro(self, paso):
        paso %= _TIERRA_PASOS
        s = self.cuadros.get(paso)
        if s is not None:
            return s
        arte = pygame.Surface((2 * _TIERRA_R, 2 * _TIERRA_R), pygame.SRCALPHA)
        giro = paso / _TIERRA_PASOS
        for x, y, lon, fila, brillo, polo in self.pixeles:
            u = int((lon + giro) * self.ancho) % self.ancho
            un = int((lon + giro * 1.6) * self.ancho) % self.ancho
            if polo:
                base = (236, 244, 255)
            elif self.nubes[fila][un]:
                base = (240, 244, 255)
            elif self.tierra[fila][u]:
                base = (186, 160, 96) if self.desierto[fila][u] else (64, 164, 86)
            else:
                base = (30, 96, 210)
            if brillo < 0.12:
                # lado de noche: luces de ciudades en la tierra firme
                if self.tierra[fila][u] and not self.nubes[fila][un] and (u * 7 + fila * 3) % 5 == 0:
                    color = (255, 214, 120)
                else:
                    color = (8, 16, 46)
            else:
                k = 0.35 + 0.65 * min(1.0, brillo * 1.3)
                color = (int(base[0] * k), int(base[1] * k), int(base[2] * k))
            arte.set_at((x, y), color)
        s = pygame.transform.scale(arte, (arte.get_width() * _TIERRA_ESCALA, arte.get_height() * _TIERRA_ESCALA))
        self.cuadros[paso] = s
        return s


class CinematicaLuna:
    """Final de la ruta cyberpunk. Viaje a la Luna con las estrellas
    corriendo, aterrizaje con polvo, Lucy baja de la nave, camina dejando
    huellas y se queda de espaldas mirando la Tierra que asoma en el
    horizonte. Al terminar (T_FIN) sigue animandose con update/draw: main.py
    la deja de fondo y pone la victoria final al costado. Todo depende de
    self.t, asi saltar() puede adelantarla de una."""

    T_VIAJE = 420
    T_TOCA = 600
    T_SALE = 660
    T_CAMINA = 700
    T_LLEGA = 870
    T_FIN = 1040
    FRASE = "Al final... llegamos a la Luna."

    HORIZONTE = 430
    PISO = 566
    NAVE_X = 170
    TIERRA = (330, 360)
    LUCY_X0, LUCY_X1 = 250, 440

    def __init__(self, sprite_nave):
        self.t = 0
        self.fin = self.T_FIN
        self.eventos = []
        self.temblor = 0
        self.nave = None
        if sprite_nave is not None:
            alto = 170
            ancho = max(1, int(sprite_nave.get_width() * alto / max(1, sprite_nave.get_height())))
            self.nave = pygame.transform.scale(sprite_nave, (ancho, alto))
        rng = random.Random(9)
        self.estrellas_viaje = [[rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.05, 1)] for _ in range(160)]
        self.estrellas = [(rng.randrange(GAME_WIDTH), rng.randrange(self.HORIZONTE), rng.randrange(120))
                          for _ in range(130)]
        self.luna = self._textura_luna()
        self.suelo = self._suelo()
        self.tierra = _Tierra()

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t < self.T_FIN - 40:
            self.t = self.T_FIN - 40

    # --------------------------------------------------------- preparacion

    @staticmethod
    def _textura_luna():
        r = 220
        s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        pygame.draw.circle(s, (210, 210, 222), (r, r), r)
        rng = random.Random(4)
        for _ in range(40):
            a, d = rng.uniform(0, 6.3), rng.uniform(0, r * 0.85)
            cr = rng.uniform(6, 30)
            cx, cy = r + math.cos(a) * d, r + math.sin(a) * d
            pygame.draw.circle(s, (170, 170, 188), (int(cx), int(cy)), int(cr))
            pygame.draw.circle(s, (230, 230, 240), (int(cx - cr * 0.2), int(cy - cr * 0.2)), int(cr * 0.6))
        # sombra del lado izquierdo
        sombra = pygame.Surface((2 * r, 2 * r))
        pygame.draw.circle(sombra, (70, 70, 60), (r - 70, r + 40), r)
        s.blit(sombra, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
        return s

    def _suelo(self):
        """Suelo lunar (fijo): horizonte apenas curvo, bandas de gris,
        crateres con borde iluminado y piedras."""
        s = pygame.Surface((GAME_WIDTH, GAME_HEIGHT - self.HORIZONTE + 30), pygame.SRCALPHA)
        puntos = [(0, 14)]
        for x in range(0, GAME_WIDTH + 1, 40):
            puntos.append((x, 14 - math.sin(math.pi * x / GAME_WIDTH) * 14))
        puntos += [(GAME_WIDTH, s.get_height()), (0, s.get_height())]
        pygame.draw.polygon(s, (128, 128, 146), puntos)
        bandas = ((116, 116, 134), (104, 104, 122), (92, 92, 110), (80, 80, 98))
        for i, color in enumerate(bandas):
            y = 40 + i * 45
            s.fill(color, (0, y, GAME_WIDTH, s.get_height() - y))
        rng = random.Random(12)
        for _ in range(26):
            cx, cy = rng.randrange(GAME_WIDTH), rng.randrange(24, s.get_height() - 10)
            ancho = rng.randint(20, 40) + cy // 3
            alto = max(6, ancho // 4)
            pygame.draw.ellipse(s, (66, 66, 84), (cx - ancho // 2, cy - alto // 2, ancho, alto))
            pygame.draw.ellipse(s, (160, 160, 176), (cx - ancho // 2, cy - alto // 2, ancho, alto), 2)
        for _ in range(40):
            x, y = rng.randrange(GAME_WIDTH), rng.randrange(20, s.get_height())
            tam = 3 + y // 40
            s.fill((60, 60, 78), (x, y, tam, tam // 2 + 1))
            s.fill((170, 170, 186), (x, y, tam, 1))
        return s

    # ---------------------------------------------------------- animacion

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        t = self.t
        if t == 1:
            self.eventos.append("despega")
        if t == self.T_TOCA:
            self.eventos.append("aterriza")
            self.temblor = 8
        if t == self.T_SALE:
            self.eventos.append("puerta")
        if t == self.T_LLEGA:
            self.eventos.append("mira")

    def _nave_y(self):
        """Centro de la nave en la escena de la Luna."""
        alto = self.nave.get_height() if self.nave else 120
        piso = self.PISO - alto // 2
        k = _ease((self.t - self.T_VIAJE) / (self.T_TOCA - self.T_VIAJE))
        return -120 + (piso + 120) * k

    def _dibujar_nave(self, surface, x, y, llama):
        if llama > 0:
            largo = int(llama * (20 + (self.t % 4) * 5))
            alto = self.nave.get_height() if self.nave else 80
            surface.fill((255, 150, 40), (int(x) - 9, int(y) + alto // 2 - 6, 18, largo))
            surface.fill(AMARILLO, (int(x) - 5, int(y) + alto // 2 - 6, 10, max(1, largo - 8)))
        if self.nave is not None:
            _blit_centrado(surface, self.nave, x, y)
        else:
            pygame.draw.polygon(surface, (200, 220, 255), ((x, y - 60), (x + 40, y + 60), (x - 40, y + 60)))
            pygame.draw.polygon(surface, CIAN, ((x, y - 24), (x + 14, y + 14), (x - 14, y + 14)))

    def _viaje(self, surface):
        t = self.t
        surface.fill((6, 4, 16))
        k = t / self.T_VIAJE
        velocidad = 0.03 * (1 - k) + 0.004
        cx, cy = GAME_WIDTH / 2, GAME_HEIGHT / 2 - 40
        for e in self.estrellas_viaje:
            z_antes = e[2]
            e[2] -= velocidad
            if e[2] <= 0.02:
                e[0], e[1], e[2] = random.uniform(-1, 1), random.uniform(-1, 1), 1.0
                continue
            x, y = cx + e[0] / e[2] * 300, cy + e[1] / e[2] * 300
            xa, ya = cx + e[0] / z_antes * 300, cy + e[1] / z_antes * 300
            brillo = int(255 * min(1.0, (1 - e[2]) * 1.5))
            color = (brillo, brillo, min(255, brillo + 30))
            if velocidad > 0.012:
                pygame.draw.line(surface, color, (xa, ya), (x, y), 2)
            else:
                surface.fill(color, (int(x), int(y), 3, 3))
        # la Luna crece adelante
        r = int(26 + 330 * k ** 2.2)
        luna = pygame.transform.scale(self.luna, (2 * r, 2 * r))
        _blit_centrado(surface, luna, cx, cy - 40 + k * 60)
        y_nave = GAME_HEIGHT - 150 + math.sin(t * 0.08) * 6
        self._dibujar_nave(surface, GAME_WIDTH / 2, y_nave, 1.0)

    def _escena(self, surface):
        t = self.t
        surface.fill((4, 4, 14))
        for x, y, fase in self.estrellas:
            if ((t + fase) // 40) % 6:
                surface.fill((210, 210, 240) if fase % 3 else (150, 200, 255), (x, y, 2, 2))
        # estrella fugaz de vez en cuando
        fugaz = (t - self.T_LLEGA) % 400 if t > self.T_LLEGA else -1
        if 0 <= fugaz < 30:
            x0 = 900 - fugaz * 14
            y0 = 60 + fugaz * 4
            pygame.draw.line(surface, WHITE, (x0, y0), (x0 + 60, y0 - 16), 2)
        # la Tierra asomando en el horizonte, con su halo de atmosfera
        tx, ty = self.TIERRA
        tierra = self.tierra.cuadro(t // 6)
        halo = pygame.Surface((tierra.get_width() + 60, tierra.get_height() + 60), pygame.SRCALPHA)
        for k, alfa in ((0, 22), (8, 34), (16, 50), (24, 70)):
            pygame.draw.circle(halo, (110, 200, 255, alfa), (halo.get_width() // 2, halo.get_height() // 2),
                               tierra.get_width() // 2 + 28 - k)
        _blit_centrado(surface, halo, tx, ty)
        _blit_centrado(surface, tierra, tx, ty)
        surface.blit(self.suelo, (0, self.HORIZONTE - 14))

        # nave: baja, aterriza y levanta polvo
        y_nave = self._nave_y()
        llama = 0.0 if t >= self.T_TOCA else max(0.3, 1 - (t - self.T_VIAJE) / (self.T_TOCA - self.T_VIAJE))
        self._dibujar_nave(surface, self.NAVE_X, y_nave, llama)
        if self.T_TOCA - 20 <= t < self.T_TOCA + 70:
            k = (t - self.T_TOCA + 20) / 90
            for i in range(10):
                a = math.pi * (i + 0.5) / 10
                px = self.NAVE_X + math.cos(a) * 140 * k
                py = self.PISO - math.sin(a) * 26 * k
                tam = int(16 * (1 - k)) + 4
                surface.fill((170, 170, 186), (int(px) - tam // 2, int(py) - tam // 2, tam, tam))
        if self.T_SALE - 10 <= t < self.T_SALE + 30:
            # la puerta se abre: un rectangulo de luz al pie de la nave
            surface.fill((200, 250, 255), (self.NAVE_X + 24, self.PISO - 60, 24, 52))

        if t >= self.T_SALE:
            self._dibujar_lucy(surface)

    def _lucy_x(self):
        k = (self.t - self.T_CAMINA) / (self.T_LLEGA - self.T_CAMINA)
        k = max(0.0, min(1.0, k))
        return self.LUCY_X0 + (self.LUCY_X1 - self.LUCY_X0) * k

    def _dibujar_lucy(self, surface):
        t = self.t
        x = self._lucy_x()
        # huellas detras de ella
        for hx in range(self.LUCY_X0 + 10, int(x) - 14, 22):
            surface.fill((70, 70, 88), (hx, self.PISO + 2 + (hx // 22) % 2 * 4, 10, 4))
        caminando = self.T_CAMINA <= t < self.T_LLEGA
        if t >= self.T_LLEGA:
            cuadro = 2
        else:
            cuadro = (t // 9) % 2 if caminando else 1
        spr = sprite_cyber("lucy", cuadro, 4)
        bob = 4 if caminando and cuadro == 0 else 0
        x0 = int(x) - spr.get_width() // 2
        y0 = self.PISO - spr.get_height() + bob
        if t < self.T_SALE + 30:
            spr = spr.copy()
            spr.set_alpha(int(255 * (t - self.T_SALE) / 30))
        surface.blit(spr, (x0, y0))
        # casco de burbuja transparente con un brillo
        cx = x0 + (7 if cuadro != 2 else 8) * 4
        cy = y0 + 5 * 4
        casco = pygame.Surface((90, 90), pygame.SRCALPHA)
        pygame.draw.circle(casco, (170, 230, 255, 40), (45, 45), 38)
        pygame.draw.circle(casco, (200, 240, 255, 150), (45, 45), 38, 3)
        casco.fill((255, 255, 255, 200), (22, 18, 8, 4))
        casco.fill((255, 255, 255, 200), (18, 23, 4, 8))
        surface.blit(casco, (cx - 45, cy - 45))

    def draw(self, surface):
        t = self.t
        mundo = pygame.Surface(surface.get_size())
        if t < self.T_VIAJE:
            self._viaje(mundo)
        else:
            self._escena(mundo)
        surface.blit(pixelar(mundo, 2), (0, 0))

        # franjas de cine (se van al terminar, para la victoria final)
        franjas = 1.0 if t < self.T_FIN - 30 else max(0.0, (self.T_FIN - t) / 30)
        neon.franjas_cine(surface, min(t / 30, franjas), MAGENTA, alto=44)
        if 50 <= t < 240:
            neon.cinta(surface, "RUMBO A LA LUNA", CIAN, (GAME_WIDTH // 2, 74), tam=16)
        if self.T_LLEGA + 20 <= t < self.T_FIN - 10:
            letras = min(len(self.FRASE), (t - self.T_LLEGA - 20) // 3)
            fuente = get_font(24, bold=True)
            sombra = fuente.render(self.FRASE[:letras], True, NEGRO)
            frente = fuente.render(self.FRASE[:letras], True, (236, 236, 252))
            x = GAME_WIDTH // 2 - fuente.size(self.FRASE)[0] // 2
            surface.blit(sombra, (x + 2, GAME_HEIGHT - 86))
            surface.blit(frente, (x, GAME_HEIGHT - 88))
        neon.scanlines(surface, 30)
        # fundidos: entra desde blanco (la explosion del Kaiser), negro
        # entre el viaje y la Luna
        if t < 40:
            neon.velo(surface, WHITE, int(255 * (1 - t / 40)))
        if self.T_VIAJE - 40 <= t < self.T_VIAJE:
            neon.velo(surface, NEGRO, int(255 * (t - self.T_VIAJE + 40) / 40))
        elif self.T_VIAJE <= t < self.T_VIAJE + 30:
            neon.velo(surface, NEGRO, int(255 * (1 - (t - self.T_VIAJE) / 30)))

    def entrada_panel(self):
        """0..1: cuanto entro la victoria final al costado (main.py)."""
        return _ease((self.t - self.T_FIN) / 45)
