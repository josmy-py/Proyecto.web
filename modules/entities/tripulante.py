"""
El tripulante rojo (Among Us) del jefe bonus: aparece cuando el Gato Alien
invencible te derrota (ver bonus_estado "game_over_falso" en main.py).

  - CinematicaTripulante: el tripulante rompe la pantalla de GAME OVER
    (tiros, grietas y una trompada que la hace estallar en pedazos), te
    ofrece "una mano" y te devuelve todas las vidas, corazon por corazon,
    antes de volver a la pelea.
  - TripulanteAliado: vuela al lado de la nave disparandole con su pistola
    al jefe de turno hasta que cae el Gato Alien, y ahi se despide metiendose
    por una ventila.

Todo el arte es pixel art dibujado por codigo (como en nyan_boss.py), mas
detallado que el de los gatos: contorno oscuro de 1 pixel, dos tonos de
rojo con la "costura" en zigzag, visor con borde/reflejo, mochila y la
mano con la pistola."""

import math
import random

import pygame

from modules.constants import GAME_WIDTH, GAME_HEIGHT, WHITE, AMARILLO, MENTA
from modules.systems.fonts import get_font, render_text
from modules.systems import neon
from modules.entities.nyan_boss import sprite_pixel, ESTRELLA_VERDE

CONTORNO = (38, 6, 22)
ROJO = (197, 17, 17)
ROJO_BRILLO = (236, 84, 84)
ROJO_OSCURO = (122, 8, 56)
VISOR_BORDE = (24, 40, 58)
VISOR = (149, 202, 220)
VISOR_OSCURO = (86, 134, 166)
GRIS = (170, 185, 195)
GRIS_OSCURO = (88, 104, 116)
BOTON = (230, 30, 40)
BOTON_ENCENDIDO = (255, 240, 120)
CORAZON = (255, 70, 110)
CORAZON_BRILLO = (255, 190, 210)
VENTILA = (70, 76, 90)
VENTILA_OSCURA = (30, 32, 42)


# ------------------------------------------------------------------ arte

def _formas_tripulante(s, color_cuerpo, color_mano, color_arma, objeto="pistola"):
    """Dibuja las formas planas del tripulante mirando a la derecha (se usa
    dos veces: una para la silueta del contorno y otra con los colores de
    verdad). objeto: "pistola" o "control" (el control remoto con antena de
    la cinematica)."""
    pygame.draw.rect(s, color_cuerpo, (1, 8, 6, 11), border_radius=2)  # mochila
    pygame.draw.ellipse(s, color_cuerpo, (4, 0, 18, 18))                # cabeza
    s.fill(color_cuerpo, (4, 9, 18, 12))                                # cuerpo
    s.fill(color_cuerpo, (5, 20, 7, 5))                                 # pierna de atras
    s.fill(color_cuerpo, (14, 20, 8, 5))                                # pierna de adelante
    pygame.draw.ellipse(s, color_cuerpo, (10, 4, 14, 9))                # visor (sobresale)
    if objeto == "control":
        s.fill(color_arma, (28, 0, 1, 3))                               # control: antena
        s.fill(color_arma, (25, 2, 6, 10))                              # control: cuerpo
    else:
        s.fill(color_arma, (24, 4, 9, 4))                               # pistola: corredera
        s.fill(color_arma, (25, 7, 3, 5))                               # pistola: empuñadura
    pygame.draw.ellipse(s, color_mano, (23, 9, 7, 8))                   # mano


def _arte_tripulante(objeto="pistola", encendido=False):
    s = pygame.Surface((35, 27), pygame.SRCALPHA)

    # contorno grueso como en el juego: la silueta corrida un pixel a cada lado
    silueta = pygame.Surface((35, 27), pygame.SRCALPHA)
    _formas_tripulante(silueta, CONTORNO, CONTORNO, CONTORNO, objeto)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
        s.blit(silueta, (dx, dy))

    _formas_tripulante(s, ROJO, ROJO, GRIS_OSCURO if objeto == "control" else GRIS, objeto)

    # sombra con borde duro: la espalda, la mochila y la parte de abajo
    for y in range(27):
        for x in range(23):
            if tuple(s.get_at((x, y)))[:3] != ROJO:
                continue
            borde = 7 + int(2 * math.sin(y / 26 * math.pi))
            if x < 7 or (x < borde + 2 and y > 6) or y >= 19:
                s.set_at((x, y), ROJO_OSCURO)
    # costura entre la mochila y el cuerpo, y entre las piernas
    s.fill(CONTORNO, (6, 10, 1, 8))
    s.fill(CONTORNO, (12, 21, 2, 4))
    s.fill((0, 0, 0, 0), (12, 23, 2, 4))
    # brillo arriba de la cabeza
    s.fill(ROJO_BRILLO, (9, 1, 6, 1))
    s.fill(ROJO_BRILLO, (8, 2, 2, 1))
    s.fill(ROJO_BRILLO, (2, 9, 1, 3))

    # visor grande mirando a la derecha, con su reflejo
    pygame.draw.ellipse(s, VISOR_BORDE, (10, 4, 14, 9))
    pygame.draw.ellipse(s, VISOR, (11, 5, 12, 7))
    pygame.draw.ellipse(s, VISOR_OSCURO, (11, 8, 12, 4))
    s.fill(VISOR, (12, 7, 10, 1))
    s.fill(WHITE, (17, 6, 4, 1))
    s.fill(WHITE, (19, 7, 2, 1))

    if objeto == "control":
        # control remoto: frente claro, boton rojo (amarillo al apretarlo)
        # y la puntita de la antena que se enciende
        s.fill(GRIS, (26, 3, 4, 6))
        s.fill(BOTON_ENCENDIDO if encendido else BOTON, (26, 4, 4, 2))
        s.fill(GRIS_OSCURO, (26, 7, 1, 1))
        s.fill(GRIS_OSCURO, (28, 7, 1, 1))
        s.set_at((28, 0), BOTON_ENCENDIDO if encendido else BOTON)
    else:
        # pistola: sombra, ranuras y brillo
        s.fill(GRIS_OSCURO, (24, 7, 9, 1))
        for rx in (28, 30):
            s.fill(GRIS_OSCURO, (rx, 5, 1, 2))
        s.fill(WHITE, (25, 5, 2, 1))
        s.fill(GRIS_OSCURO, (25, 10, 3, 2))
    # mano: brillo y sombra
    s.fill(ROJO_BRILLO, (25, 10, 2, 1))
    s.fill(ROJO_OSCURO, (23, 14, 6, 2))
    return s


def _arte_corazon():
    filas = (".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X...")
    s = pygame.Surface((7, 6), pygame.SRCALPHA)
    for y, fila in enumerate(filas):
        for x, c in enumerate(fila):
            if c == "X":
                s.set_at((x, y), CORAZON)
    s.set_at((1, 1), CORAZON_BRILLO)
    s.set_at((2, 1), CORAZON_BRILLO)
    s.set_at((1, 2), CORAZON_BRILLO)
    return s


def _arte_ventila(abierta):
    s = pygame.Surface((20, 7), pygame.SRCALPHA)
    s.fill(CONTORNO, (0, 0, 20, 7))
    s.fill(VENTILA_OSCURA if abierta else VENTILA, (1, 1, 18, 5))
    if not abierta:
        for x in range(3, 18, 3):
            s.fill(VENTILA_OSCURA, (x, 1, 1, 5))
    return s


_ARTES = {"tripulante": _arte_tripulante, "corazon": _arte_corazon,
          "tripulante_control": lambda: _arte_tripulante("control"),
          "tripulante_control_on": lambda: _arte_tripulante("control", True),
          "ventila": lambda: _arte_ventila(False), "ventila_abierta": lambda: _arte_ventila(True)}
_CACHE = {}


def sprite(nombre, escala, voltear=False):
    clave = (nombre, escala, voltear)
    surf = _CACHE.get(clave)
    if surf is None:
        arte = _ARTES[nombre]()
        surf = pygame.transform.scale(arte, (arte.get_width() * escala, arte.get_height() * escala))
        if voltear:
            surf = pygame.transform.flip(surf, True, False)
        _CACHE[clave] = surf
    return surf


def _globo(surface, texto, x, y, cola_derecha=True):
    """Globo de dialogo neon (panel oscuro con marco rojo y cola en
    escalon hacia el que habla)."""
    fuente = get_font(20, bold=True)
    t = fuente.render(texto, True, WHITE)
    rect = pygame.Rect(0, 0, t.get_width() + 32, t.get_height() + 20)
    rect.midbottom = (x, y)
    rect.clamp_ip(pygame.Rect(6, 6, GAME_WIDTH - 12, GAME_HEIGHT - 12))
    surface.fill(neon.CONTORNO, rect.inflate(8, 8))
    surface.fill(neon.FONDO, rect)
    neon.marco_pixel(surface, rect, ROJO_BRILLO, 3)
    cola_x = rect.right - 34 if cola_derecha else rect.left + 20
    for i in range(4):
        surface.fill(neon.CONTORNO, (cola_x + i * 4 - 4, rect.bottom + i * 4, 16 - i * 4 + 4, 4))
        surface.fill(ROJO_BRILLO, (cola_x + i * 4, rect.bottom + i * 4 - 3, max(0, 12 - i * 4), 3))
    surface.blit(t, (rect.x + 16, rect.y + 10))


# ------------------------------------------------------------ aliado

class BalaAliada:
    """Tiro de la pistola del tripulante: apuntado al jefe. Misma interfaz
    que Bullet (x, y, radius, piercing, active, update, draw) para que
    main.py la trate como un disparo mas de la nave."""

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = 4
        self.piercing = False
        self.active = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < GAME_WIDTH + 20 and -20 < self.y < GAME_HEIGHT + 20):
            self.active = False

    def draw(self, screen, offset_x=0, offset_y=0):
        cx, cy = int(self.x) + offset_x, int(self.y) + offset_y
        screen.fill(ROJO, (cx - 5, cy - 5, 10, 10))
        screen.fill(AMARILLO, (cx - 3, cy - 3, 6, 6))
        screen.fill(WHITE, (cx - 1, cy - 1, 2, 2))


class TripulanteAliado:
    """Vuela a un costado de la nave y le dispara al jefe activo. despedirse()
    arranca la salida por la ventila; `terminado` avisa que ya se fue."""

    ESCALA = 2
    CADENCIA = 16

    def __init__(self, ship):
        self.x = ship.x - 90
        self.y = ship.y + 40
        self.t = 0
        self.timer_disparo = 40
        self.fogonazo = 0
        self.estado = "activo"
        self.timer_ventila = 0
        self.terminado = False
        self.frase = ("¡Te cubro!", 150)

    def _punta_arma(self):
        # la boca de la pistola esta en el pixel de arte (33, 5), el centro en (17, 13)
        return self.x + (33 - 17) * self.ESCALA, self.y + (5 - 13) * self.ESCALA

    def update(self, ship, bosses):
        self.t += 1
        if self.fogonazo > 0:
            self.fogonazo -= 1
        if self.frase is not None:
            texto, vida = self.frase
            self.frase = (texto, vida - 1) if vida > 1 else None

        if self.estado == "ventila":
            self.timer_ventila += 1
            if self.timer_ventila > 95:
                self.terminado = True
            return []

        lado = 1 if ship.x < 150 else -1
        objetivo_x = ship.x + lado * 85
        objetivo_y = ship.y - 20 + math.sin(self.t * 0.07) * 6
        self.x += (objetivo_x - self.x) * 0.12
        self.y += (objetivo_y - self.y) * 0.12

        blancos = [b for b in bosses if b.active and not getattr(b, "entrando", False)]
        self.timer_disparo -= 1
        if blancos and self.timer_disparo <= 0:
            self.timer_disparo = self.CADENCIA
            self.fogonazo = 4
            bx, by = self._punta_arma()
            blanco = blancos[0]
            a = math.atan2(blanco.y - by, blanco.x - bx) + random.uniform(-0.04, 0.04)
            return [BalaAliada(bx, by, math.cos(a) * 11, math.sin(a) * 11)]
        return []

    def despedirse(self):
        if self.estado != "ventila":
            self.estado = "ventila"
            self.timer_ventila = 0
            self.frase = ("¡Suerte!", 60)

    def draw(self, screen, offset_x=0, offset_y=0):
        spr = sprite("tripulante", self.ESCALA)
        x = int(self.x) - spr.get_width() // 2 + offset_x
        y = int(self.y) - spr.get_height() // 2 + offset_y

        if self.estado == "ventila":
            # la ventila se abre bajo sus pies, se hunde y se cierra
            tv = self.timer_ventila
            piso = y + spr.get_height()
            abierta = 15 < tv < 80
            ventila = sprite("ventila_abierta" if abierta else "ventila", self.ESCALA)
            vx = int(self.x) - ventila.get_width() // 2 + offset_x
            if tv < 70:
                hundido = 0 if tv < 25 else min(spr.get_height(), (tv - 25) * 3)
                visible = spr.get_height() - hundido
                if visible > 0:
                    screen.blit(spr.subsurface((0, 0, spr.get_width(), visible)), (x, y + hundido))
            screen.blit(ventila, (vx, piso - ventila.get_height() // 2))
        else:
            screen.blit(spr, (x, y))
            if self.fogonazo > 0:
                bx, by = self._punta_arma()
                r = 4 + self.fogonazo * 2
                screen.fill(AMARILLO, (int(bx) - r + offset_x, int(by) - r // 2 + offset_y, r * 2, r))
                screen.fill(WHITE, (int(bx) - r // 2 + offset_x, int(by) - 2 + offset_y, r, 4))

        if self.frase is not None:
            texto = render_text(self.frase[0], 13, WHITE)
            fondo = pygame.Rect(0, 0, texto.get_width() + 12, texto.get_height() + 6)
            fondo.midbottom = (int(self.x) + offset_x, y - 6)
            screen.fill(CONTORNO, fondo.inflate(4, 4))
            screen.fill((250, 250, 255), fondo)
            texto = render_text(self.frase[0], 13, (30, 10, 30), outline=False)
            screen.blit(texto, (fondo.x + 6, fondo.y + 3))


# -------------------------------------------------------------- cinematica

class CinematicaTripulante:
    """Despues del GAME OVER, en dos actos:

      ROTURA: desde "adentro" de la pantalla de GAME OVER el tripulante le
        pega tres tiros (agujero de bala, grietas que se ramifican, temblor)
        y despues la atraviesa de una trompada: el vidrio estalla en pedazos
        (recortes reales de la pantalla) que salen volando y caen girando.
      RESCATE: escenario rojo oscuro con dos focos, con la nave apagada y
        el plato del Gato Alien con su escudo. Primero asoma solo la mano
        del tripulante; despues entra el con un control remoto, aprieta el
        boton y la señal viaja hasta el plato: el escudo se agrieta y
        estalla ("¡ESCUDO DESACTIVADO!"). Recien ahi "¿Necesitas una
        mano?", te devuelve las vidas corazon por corazon, "Vamos por ese
        gato." y destello de vuelta a la pelea.

    eventos: lista de "disparo"/"rotura"/"boton"/"escudo"/"corazon" que main.py consume para
    los sonidos; temblor: pixeles de sacudida para este cuadro. saltar()
    adelanta el final; terminada indica que ya se puede revivir."""

    FUNDIDO = 40
    IMPACTOS = ((0.63, 0.40, 28), (0.38, 0.56, 50), (0.55, 0.66, 70))
    T_PUNO = 92
    T_ROTURA = 104
    # rescate (cuadros desde la rotura)
    MANO_HASTA = 90
    ENTRA_DESDE = 90
    PULSA = 200
    ESCUDO_GRIETA = 222
    ESCUDO_ROTO = 240

    def __init__(self, captura, sprite_nave, vidas):
        self.captura = captura
        self.sprite_nave = sprite_nave
        self.vidas = max(1, vidas)
        self.t = 0
        self.eventos = []
        self.temblor = 0
        self.grietas = []
        self.agujeros = []
        self.pedazos = []
        # el rescate arranca despues de la rotura: todos sus tiempos son
        # relativos a T_ROTURA (ver _tr)
        self.inicio_corazones = 330
        self.fin_corazones = self.inicio_corazones + self.vidas * 22 + 40
        self.duracion = self.T_ROTURA + self.fin_corazones + 190
        self.fin = self.duracion
        self.nave_pos = (GAME_WIDTH * 0.22, GAME_HEIGHT * 0.70)
        self.ovni_pos = (GAME_WIDTH * 0.28, GAME_HEIGHT * 0.24)
        self.chispas = []
        self.pedazos_escudo = []

    @property
    def terminada(self):
        return self.t >= self.fin

    def saltar(self):
        if self.t > 40:
            self.fin = min(self.fin, self.t + self.FUNDIDO)

    def _tr(self):
        """Cuadros desde que se rompio la pantalla (negativo antes)."""
        return self.t - self.T_ROTURA

    # ---------------------------------------------------------- rotura
    def _agregar_grietas(self, x, y):
        """Grietas que salen del impacto: caminos quebrados con ramitas."""
        for _ in range(7):
            a = random.uniform(0, 2 * math.pi)
            px, py = x, y
            puntos = [(px, py)]
            for _ in range(random.randint(4, 7)):
                a += random.uniform(-0.5, 0.5)
                largo = random.uniform(18, 45)
                px += math.cos(a) * largo
                py += math.sin(a) * largo
                puntos.append((px, py))
                if random.random() < 0.3:
                    b = a + random.choice((-1, 1)) * random.uniform(0.6, 1.1)
                    self.grietas.append([(px, py), (px + math.cos(b) * 25, py + math.sin(b) * 25)])
            self.grietas.append(puntos)

    def _romper(self):
        """Parte la pantalla (con sus grietas) en pedazos poligonales que
        salen disparados desde el centro."""
        rota = self.captura.copy()
        self._dibujar_grietas(rota)
        columnas, filas = 7, 5
        cw, ch = GAME_WIDTH / columnas, GAME_HEIGHT / filas
        vertices = {}
        for i in range(columnas + 1):
            for j in range(filas + 1):
                jx = 0 if i in (0, columnas) else random.uniform(-cw * 0.3, cw * 0.3)
                jy = 0 if j in (0, filas) else random.uniform(-ch * 0.3, ch * 0.3)
                vertices[(i, j)] = (i * cw + jx, j * ch + jy)
        cx, cy = GAME_WIDTH / 2, GAME_HEIGHT / 2
        for i in range(columnas):
            for j in range(filas):
                esquinas = [vertices[(i, j)], vertices[(i + 1, j)], vertices[(i + 1, j + 1)], vertices[(i, j + 1)]]
                # cada celda se parte en dos triangulos por una diagonal al azar
                if random.random() < 0.5:
                    triangulos = [esquinas[:3], [esquinas[0], esquinas[2], esquinas[3]]]
                else:
                    triangulos = [[esquinas[0], esquinas[1], esquinas[3]], esquinas[1:]]
                for tri in triangulos:
                    xs = [p[0] for p in tri]
                    ys = [p[1] for p in tri]
                    caja = pygame.Rect(int(min(xs)), int(min(ys)), int(max(xs) - min(xs)) + 2, int(max(ys) - min(ys)) + 2)
                    caja = caja.clip(pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT))
                    if caja.w < 2 or caja.h < 2:
                        continue
                    pieza = pygame.Surface(caja.size, pygame.SRCALPHA)
                    pieza.blit(rota, (0, 0), caja)
                    mascara = pygame.Surface(caja.size, pygame.SRCALPHA)
                    local = [(px - caja.x, py - caja.y) for px, py in tri]
                    pygame.draw.polygon(mascara, (255, 255, 255, 255), local)
                    pieza.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                    pygame.draw.polygon(pieza, (255, 255, 255, 160), local, 1)
                    px, py = caja.center
                    d = math.hypot(px - cx, py - cy) or 1
                    fuerza = random.uniform(5, 11) * (1.2 - min(1.0, d / 500))
                    self.pedazos.append({
                        'surf': pieza, 'x': float(px), 'y': float(py),
                        'vx': (px - cx) / d * fuerza + random.uniform(-1, 1),
                        'vy': (py - cy) / d * fuerza - random.uniform(2, 5),
                        'ang': 0.0, 'va': random.uniform(-9, 9),
                    })

    def _dibujar_grietas(self, surface):
        for puntos in self.grietas:
            if len(puntos) >= 2:
                sombra = [(x + 1, y + 1) for x, y in puntos]
                pygame.draw.lines(surface, (20, 10, 20), False, sombra, 3)
                pygame.draw.lines(surface, (235, 245, 255), False, puntos, 1)
        for x, y in self.agujeros:
            pygame.draw.circle(surface, (235, 245, 255), (int(x), int(y)), 9)
            pygame.draw.circle(surface, (15, 8, 15), (int(x), int(y)), 6)

    def _corazones_entregados(self):
        return max(0, min(self.vidas, (self._tr() - self.inicio_corazones) // 22))

    def update(self):
        self.t += 1
        self.temblor = max(0, self.temblor - 1)
        for fx, fy, ti in self.IMPACTOS:
            if self.t == ti:
                x, y = fx * GAME_WIDTH, fy * GAME_HEIGHT
                self.agujeros.append((x, y))
                self._agregar_grietas(x, y)
                self.eventos.append("disparo")
                self.temblor = 9
        if self.t == self.T_ROTURA:
            self._romper()
            self.eventos.append("rotura")
            self.temblor = 20
        for p in self.pedazos:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.4
            p['ang'] += p['va']
        self.pedazos = [p for p in self.pedazos if p['y'] < GAME_HEIGHT + 200]

        for c in self.chispas:
            c[0] += c[2]
            c[1] += c[3]
            c[4] -= 1
        self.chispas = [c for c in self.chispas if c[4] > 0]
        tr = self._tr()
        if tr == self.PULSA:
            self.eventos.append("boton")
        if tr == self.ESCUDO_ROTO:
            self.eventos.append("escudo")
            self.temblor = 12
            ox, oy = self.ovni_pos
            for _ in range(22):
                a = random.uniform(0, 2 * math.pi)
                v = random.uniform(3, 8)
                self.pedazos_escudo.append({'x': ox + math.cos(a) * 80, 'y': oy + math.sin(a) * 80,
                                            'vx': math.cos(a) * v, 'vy': math.sin(a) * v - 2,
                                            'ang': a, 'va': random.uniform(-0.3, 0.3),
                                            'tam': random.randint(8, 18)})
        for e in self.pedazos_escudo:
            e['x'] += e['vx']
            e['y'] += e['vy']
            e['vy'] += 0.3
            e['ang'] += e['va']
        self.pedazos_escudo = [e for e in self.pedazos_escudo if e['y'] < GAME_HEIGHT + 40]
        # cada corazon que llega a la nave suelta un estallido de chispas
        paso = tr - self.inicio_corazones
        if paso > 0 and paso % 22 == 0 and paso // 22 <= self.vidas:
            self.eventos.append("corazon")
            for _ in range(14):
                a = random.uniform(0, 2 * math.pi)
                v = random.uniform(1.5, 4)
                self.chispas.append([self.nave_pos[0], self.nave_pos[1], math.cos(a) * v, math.sin(a) * v, 30])

    # ---------------------------------------------------------- dibujo
    def _pos_tripulante(self):
        entrada = min(1.0, max(0.0, (self._tr() - self.ENTRA_DESDE) / 70))
        suave = 1 - (1 - entrada) ** 3
        x = GAME_WIDTH + 160 - suave * (GAME_WIDTH * 0.32 + 160)
        y = GAME_HEIGHT * 0.56 + math.sin(self.t * 0.06) * 6
        return x, y

    def _dibujar_escenario(self, surface):
        surface.fill((25, 4, 12))
        luz = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        alfa = min(45, max(0, self._tr()) * 2)
        # focos en escalones de 8 px (pixel art) en vez de un poligono liso
        for bx in (GAME_WIDTH * 0.25, GAME_WIDTH * 0.68):
            for y in range(0, GAME_HEIGHT, 8):
                medio = 40 + 90 * y / GAME_HEIGHT
                luz.fill((255, 230, 200, alfa), (int(bx - medio) // 8 * 8, y, int(medio * 2) // 8 * 8, 8))
        surface.blit(luz, (0, 0))
        # piso de grilla synthwave
        horizonte = int(GAME_HEIGHT * 0.80)
        surface.fill((40, 6, 30), (0, horizonte, GAME_WIDTH, GAME_HEIGHT - horizonte))
        for k in range(7):
            y = horizonte + int((k / 6) ** 1.7 * (GAME_HEIGHT - horizonte))
            surface.fill((150, 30, 90), (0, y, GAME_WIDTH, 2))
        for k in range(-8, 9):
            x0 = GAME_WIDTH // 2 + k * 40
            x1 = GAME_WIDTH // 2 + k * 150
            pygame.draw.line(surface, (120, 24, 80), (x0, horizonte), (x1, GAME_HEIGHT), 2)
        surface.fill(neon.ROJO, (0, horizonte, GAME_WIDTH, 3))

    def draw(self, surface):
        tr = self._tr()
        if tr < 0:
            # 1) la pantalla de GAME OVER recibe los tiros y se agrieta
            surface.blit(self.captura, (0, 0))
            self._dibujar_grietas(surface)
            for fx, fy, ti in self.IMPACTOS:
                if 0 <= self.t - ti < 6:
                    r = 40 - (self.t - ti) * 5
                    destello = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(destello, (255, 240, 180, 200), (r, r), r)
                    surface.blit(destello, (int(fx * GAME_WIDTH) - r, int(fy * GAME_HEIGHT) - r))
            if self.t >= self.T_PUNO:
                # el puño con la pistola atraviesa el centro, cada vez mas grande
                p = (self.t - self.T_PUNO) / (self.T_ROTURA - self.T_PUNO)
                escala = int(6 + p * 8)
                trip = sprite("tripulante", escala)
                mano = trip.subsurface((23 * escala, 1 * escala, 12 * escala, 19 * escala))
                surface.blit(mano, (GAME_WIDTH // 2 - mano.get_width() // 2, GAME_HEIGHT // 2 - mano.get_height() // 2))
            self._dibujar_pedazos(surface)
            return

        # 2) rescate: escenario, plato del Alien, nave apagada, tripulante
        self._dibujar_escenario(surface)
        self._dibujar_ovni(surface, tr)

        nx, ny = self.nave_pos
        entregados = self._corazones_entregados()
        if self.sprite_nave is not None:
            nave = pygame.transform.scale(self.sprite_nave, (self.sprite_nave.get_width() * 2,
                                                             self.sprite_nave.get_height() * 2))
            brillo = entregados / self.vidas
            if brillo < 1:
                nave = nave.copy()
                gris = int(170 * (1 - brillo))
                nave.fill((gris, gris, gris, 0), special_flags=pygame.BLEND_RGBA_SUB)
            surface.blit(nave, (int(nx) - nave.get_width() // 2, int(ny) - nave.get_height() // 2))

        # a) primero asoma solo la mano (con la pistola) por la derecha
        if tr < self.MANO_HASTA:
            if tr < 30:
                p = 1 - (1 - tr / 30) ** 3
            elif tr < 62:
                p = 1.0
            else:
                p = max(0.0, 1 - (tr - 62) / 28)
            escala = 10
            mano = sprite("tripulante", escala).subsurface((23 * escala, 1 * escala, 12 * escala, 19 * escala))
            mx = GAME_WIDTH + 20 - p * (GAME_WIDTH * 0.30)
            my = GAME_HEIGHT * 0.45 + (math.sin(tr * 0.35) * 10 if 30 <= tr < 62 else 0)
            surface.blit(mano, (int(mx) - mano.get_width() // 2, int(my) - mano.get_height() // 2))

        # b) entra el tripulante con el control remoto
        tx, ty = self._pos_tripulante()
        encendido = self.PULSA <= tr < self.PULSA + 30
        trip = sprite("tripulante_control_on" if encendido else "tripulante_control", 6)
        if tr >= self.ENTRA_DESDE:
            surface.blit(trip, (int(tx) - trip.get_width() // 2, int(ty) - trip.get_height() // 2))
        mano_x = tx + (27 - 17) * 6
        mano_y = ty - 10
        antena = (tx + (28 - 17) * 6, ty + (0 - 13) * 6)

        # c) la señal del control viaja hasta el plato
        ox, oy = self.ovni_pos
        for k in range(3):
            p = (tr - self.PULSA - k * 7) / 30
            if 0 <= p <= 1:
                sx = antena[0] + (ox - antena[0]) * p
                sy = antena[1] + (oy - antena[1]) * p
                r = int(10 + 22 * p)
                neon.anillo_pixel(surface, BOTON_ENCENDIDO, sx, sy, r, 6)
        if self.PULSA - 12 <= tr < self.PULSA:
            # el dedo por apretar: un destello chiquito en el boton
            surface.fill(WHITE, (int(mano_x) - 4, int(ty) - 60, 8, 8))

        # d) corazones de la mano a la nave
        corazon = sprite("corazon", 5)
        for i in range(self.vidas):
            salida = self.inicio_corazones - 40 + i * 22
            p = (tr - salida) / 40
            if 0 <= p < 1:
                x = mano_x + (nx - mano_x) * p
                y = mano_y + (ny - mano_y) * p - math.sin(math.pi * p) * 120
                surface.blit(corazon, (int(x) - corazon.get_width() // 2, int(y) - corazon.get_height() // 2))
        for c in self.chispas:
            neon.cuadro_pixel(surface, CORAZON if c[4] % 4 < 2 else CORAZON_BRILLO, c[0], c[1], 6)

        chico = sprite("corazon", 3)
        total_w = self.vidas * (chico.get_width() + 6)
        for i in range(self.vidas):
            cx = int(nx) - total_w // 2 + i * (chico.get_width() + 6)
            if i < entregados:
                surface.blit(chico, (cx, int(ny) + 60))
            else:
                surface.fill((70, 40, 55), (cx + 3, int(ny) + 66, chico.get_width() - 6, chico.get_height() - 8))

        # e) textos
        globo_y = int(ty) - trip.get_height() // 2 - 12
        if self.ENTRA_DESDE + 70 < tr < self.PULSA:
            _globo(surface, "¿Invencible? Ja.", int(tx) - 40, globo_y)
        if self.ESCUDO_ROTO <= tr < self.ESCUDO_ROTO + 80 and (tr // 6) % 4 != 0:
            neon.titulo(surface, "¡ESCUDO DESACTIVADO!", 36, BOTON_ENCENDIDO, GAME_WIDTH // 2, 72)
        if self.ESCUDO_ROTO + 50 < tr < self.inicio_corazones + 20:
            _globo(surface, "¿Necesitas una mano?", int(tx) - 40, globo_y)
        if tr >= self.fin_corazones - 20:
            neon.titulo(surface, "¡VIDAS RESTAURADAS!", 40, MENTA, GAME_WIDTH // 2, 72)
        if tr >= self.fin_corazones + 40:
            _globo(surface, "Vamos por ese gato.", int(tx) - 40, globo_y)

        # los ultimos vidrios siguen cayendo por delante
        self._dibujar_pedazos(surface)
        neon.franjas_cine(surface, tr / 30, neon.ROJO, alto=44)
        neon.scanlines(surface)

        restante = self.fin - self.t
        if restante < self.FUNDIDO:
            velo = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            velo.fill((255, 255, 255, int(255 * (1 - max(0, restante) / self.FUNDIDO))))
            surface.blit(velo, (0, 0))

    def _dibujar_ovni(self, surface, tr):
        """El plato del Gato Alien arriba a la izquierda: con su burbuja de
        escudo hasta que llega la señal (se agrieta) y estalla."""
        ox, oy = self.ovni_pos
        temblor = random.randint(-4, 4) if self.ESCUDO_GRIETA <= tr < self.ESCUDO_ROTO + 25 else 0
        ovni = sprite_pixel("ovni", (self.t // 10) % 2, 4)
        surface.blit(ovni, (int(ox) - ovni.get_width() // 2 + temblor, int(oy) - ovni.get_height() // 2))
        if tr < self.ESCUDO_ROTO:
            radio = 82
            burbuja = pygame.Surface((radio * 2 + 8, radio * 2 + 8), pygame.SRCALPHA)
            brillo = 90 + int(40 * math.sin(self.t * 0.12))
            if self.PULSA + 25 <= tr:
                brillo = 200 if (tr // 3) % 2 else 120  # la señal le pega: parpadea
            pygame.draw.circle(burbuja, (*ESTRELLA_VERDE, brillo // 3), (radio + 4, radio + 4), radio)
            # borde de la burbuja en bloques de pixel
            neon.anillo_pixel(burbuja, (*ESTRELLA_VERDE, brillo), radio + 4, radio + 4, radio - 3, 8, 44)
            if tr >= self.ESCUDO_GRIETA:
                # grietas que crecen desde el punto de impacto de la señal
                largo = min(1.0, (tr - self.ESCUDO_GRIETA) / (self.ESCUDO_ROTO - self.ESCUDO_GRIETA))
                rng = random.Random(7)
                for _ in range(6):
                    a = rng.uniform(0, 2 * math.pi)
                    x0, y0 = radio + 4 + 20, radio + 4 + 30
                    pygame.draw.line(burbuja, (255, 255, 255, 230), (x0, y0),
                                     (x0 + math.cos(a) * radio * largo, y0 + math.sin(a) * radio * largo), 3)
            surface.blit(burbuja, (int(ox) - radio - 4 + temblor, int(oy) - radio - 4))
        for e in self.pedazos_escudo:
            neon.cuadro_pixel(surface, neon.CONTORNO, e['x'], e['y'], e['tam'] + 4)
            neon.cuadro_pixel(surface, ESTRELLA_VERDE, e['x'], e['y'], e['tam'])
            neon.cuadro_pixel(surface, WHITE, e['x'] - e['tam'] // 4, e['y'] - e['tam'] // 4, 2)

    def _dibujar_pedazos(self, surface):
        for p in self.pedazos:
            girada = pygame.transform.rotate(p['surf'], p['ang'])
            surface.blit(girada, (int(p['x']) - girada.get_width() // 2, int(p['y']) - girada.get_height() // 2))
