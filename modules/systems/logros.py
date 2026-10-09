"""
Records y medallas, en pixel art neon:

  - EntradaNombre: al terminar una partida que entra en la tabla, tres
    letras como en los arcades (flechas o mando para cambiar la letra,
    teclado para escribirla, ENTER para seguir, click en la letra para
    subirla/bajarla y en OK para guardar).
  - MEDALLAS: logros que se guardan en progreso.json (ver
    modules/progress.py). main.py llama a progress.desbloquear_medalla y,
    si es nueva, la muestra con AvisoMedallas.
  - dibujar_tabla_records / dibujar_medallas: la pantalla RECORDS del menu.
"""

import math

import pygame

from modules.constants import WHITE
from modules.systems import neon, pixelfx
from modules.systems.fonts import get_font, render_texto_pixelado

ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
AMARILLO = (255, 220, 90)

# id -> (nombre, que hay que hacer, color)
MEDALLAS = {
    "primer_jefe": ("PRIMERA SANGRE", "Derrota a tu primer jefe", (255, 110, 110)),
    "intocable": ("INTOCABLE", "Vence a un jefe sin recibir daño", (120, 230, 255)),
    "coloso": ("MATACOLOSOS", "Derrota al Coloso Estelar", (255, 200, 60)),
    "ruta_gatos": ("AMIGO DE LOS GATOS", "Termina la ruta de los gatos", (255, 130, 210)),
    "ruta_halloween": ("NOCHE DE BRUJAS", "Termina la ruta de Halloween", (255, 150, 50)),
    "ruta_cyber": ("EDGERUNNER", "Termina la ruta cyberpunk", (0, 230, 255)),
    "trilogia": ("TRILOGÍA", "Termina las tres rutas", (190, 140, 255)),
    "parca": ("DUELO GANADO", "Vence a la Parca en su dimensión", (150, 255, 210)),
    "rush": ("SIN DESCANSO", "Termina el Jefe Rush", (255, 90, 220)),
    "combo": ("ALQUIMISTA", "Arma un combo de cartas", (255, 235, 140)),
    "demoledor": ("DEMOLEDOR", "Destruye 150 asteroides en una partida", (200, 160, 120)),
    "fenix": ("RENACIDO", "Vuelve a la vida con el Fénix", (255, 120, 40)),
}

_MEDALLA = (
    ".AA..AA.",
    ".AA..AA.",
    "..AAAA..",
    "...BB...",
    "..BCCB..",
    ".BCWCCB.",
    ".BCCCCB.",
    ".BCCCCB.",
    "..BCCB..",
    "...BB...",
)


def icono_medalla(color, encendida=True, escala=4):
    clave = ("medalla", tuple(color), encendida, escala)
    surf = pixelfx._cache.get(clave)
    if surf is not None:
        return surf
    if encendida:
        cinta, borde, cuerpo, brillo = (255, 70, 110), pixelfx.apagar(color, 0.55), color, WHITE
    else:
        cinta, borde, cuerpo, brillo = (50, 40, 70), (40, 34, 60), (60, 52, 84), (80, 72, 104)
    colores = {"A": cinta, "B": borde, "C": cuerpo, "W": brillo}
    surf = pygame.Surface((len(_MEDALLA[0]) * escala, len(_MEDALLA) * escala), pygame.SRCALPHA)
    for y, fila in enumerate(_MEDALLA):
        for x, c in enumerate(fila):
            if c in colores:
                surf.fill(colores[c], (x * escala, y * escala, escala, escala))
    pixelfx._guardar(clave, surf)
    return surf


class AvisoMedallas:
    """Cartel "¡MEDALLA!" arriba a la derecha, de a una por vez."""

    DURACION = 200

    def __init__(self):
        self.cola = []
        self.t = 0

    def agregar(self, medalla_id):
        self.cola.append(medalla_id)
        if len(self.cola) == 1:
            self.t = 0

    def update(self):
        if not self.cola:
            return
        self.t += 1
        if self.t >= self.DURACION:
            self.cola.pop(0)
            self.t = 0

    def draw(self, surface, game_w):
        if not self.cola:
            return
        nombre, _, color = MEDALLAS[self.cola[0]]
        entra = min(1.0, self.t / 14) * min(1.0, (self.DURACION - self.t) / 14)
        caja = pygame.Rect(0, 0, 330, 62)
        caja.topright = (game_w - 14 + int((1 - entra) * 360), 196)
        neon.panel(surface, caja, color, self.t, halo=False)
        icono = icono_medalla(color, escala=4)
        surface.blit(icono, icono.get_rect(midleft=(caja.x + 14, caja.centery)))
        surface.blit(neon.texto(14, "¡MEDALLA!", AMARILLO), (caja.x + 62, caja.y + 10))
        surface.blit(neon.texto(17, nombre, WHITE), (caja.x + 62, caja.y + 30))


class EntradaNombre:
    """Tres letras para la tabla de records."""

    def __init__(self, puntaje, nombre_previo="AAA"):
        self.puntaje = puntaje
        self.letras = [ALFABETO.index(c) if c in ALFABETO else 0 for c in (nombre_previo + "AAA")[:3]]
        self.pos = 0
        self.listo = False
        self.t = 0

    @property
    def nombre(self):
        return "".join(ALFABETO[i] for i in self.letras)

    def _cambiar(self, paso):
        self.letras[self.pos] = (self.letras[self.pos] + paso) % len(ALFABETO)

    def _rects(self, game_w, game_h):
        cajas = [pygame.Rect(game_w // 2 - 130 + i * 90, game_h // 2 - 40, 70, 84) for i in range(3)]
        ok = pygame.Rect(game_w // 2 - 70, game_h // 2 + 70, 140, 42)
        return cajas, ok

    def handle_event(self, event, offset_x, offset_y, game_w, game_h):
        if event.type == pygame.KEYDOWN:
            letra = (event.unicode or "").upper()
            if letra and letra in ALFABETO:
                self.letras[self.pos] = ALFABETO.index(letra)
                self.pos = min(2, self.pos + 1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._cambiar(1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._cambiar(-1)
            elif event.key == pygame.K_RIGHT:
                self.pos = min(2, self.pos + 1)
            elif event.key in (pygame.K_LEFT, pygame.K_BACKSPACE):
                self.pos = max(0, self.pos - 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.pos < 2:
                    self.pos += 1
                else:
                    self.listo = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos[0] - offset_x, event.pos[1] - offset_y
            cajas, ok = self._rects(game_w, game_h)
            for i, caja in enumerate(cajas):
                if caja.collidepoint(x, y):
                    self.pos = i
                    self._cambiar(1 if y < caja.centery else -1)
            if ok.collidepoint(x, y):
                self.listo = True

    def draw(self, surface, game_w, game_h):
        self.t += 1
        neon.velo(surface, (6, 2, 20), 200)
        panel = pygame.Rect(0, 0, 520, 330)
        panel.center = (game_w // 2, game_h // 2 - 10)
        neon.panel(surface, panel, neon.ORO, self.t)
        neon.titulo(surface, "¡ENTRASTE EN LA TABLA!", 30, AMARILLO, game_w // 2, panel.y + 40)
        linea = render_texto_pixelado(get_font(16), f"Puntaje: {self.puntaje}   -   Escribe tus iniciales", (200, 200, 230))
        surface.blit(linea, linea.get_rect(center=(game_w // 2, panel.y + 78)))
        cajas, ok = self._rects(game_w, game_h)
        for i, caja in enumerate(cajas):
            marcada = i == self.pos
            color = neon.CIAN if marcada else pixelfx.apagar(neon.CIAN, 0.45)
            surface.fill(neon.CONTORNO, caja.inflate(6, 6))
            surface.fill(neon.FONDO, caja)
            neon.marco_pixel(surface, caja, color, 3)
            letra = neon.texto(48, ALFABETO[self.letras[i]], WHITE if marcada else (170, 170, 200))
            surface.blit(letra, letra.get_rect(center=caja.center))
            if marcada and (self.t // 15) % 2 == 0:
                for dy, signo in ((-14, -1), (14, 1)):
                    yy = caja.top + dy if signo < 0 else caja.bottom + dy
                    for k in range(4):
                        ancho = 2 + k * 4 if signo < 0 else 14 - k * 4
                        surface.fill(color, (caja.centerx - ancho // 2, yy - 6 + k * 3, ancho, 3))
        neon.boton(surface, ok, "OK", neon.VERDE, self.pos == 2, self.t)
        ayuda = render_texto_pixelado(get_font(12), "Flechas o mando para elegir la letra - ENTER para seguir",
                                      (150, 160, 200))
        surface.blit(ayuda, ayuda.get_rect(center=(game_w // 2, panel.bottom - 22)))


def dibujar_tabla_records(surface, rect, records, t=0):
    neon.panel(surface, rect, neon.ORO, t)
    neon.titulo(surface, "TOP 10", 26, AMARILLO, rect.centerx, rect.y + 30, halo=False)
    y = rect.y + 66
    if not records:
        vacio = render_texto_pixelado(get_font(15), "Todavia no hay records: ¡juga una partida!", (170, 170, 200))
        surface.blit(vacio, vacio.get_rect(center=(rect.centerx, y + 40)))
        return
    fuente = get_font(17, bold=True)
    for i, r in enumerate(records[:10]):
        color = AMARILLO if i == 0 else (WHITE if i < 3 else (190, 190, 220))
        modo = {"rush": "RUSH"}.get(r.get("modo", ""), f"OL {r.get('oleada', 1)}")
        for texto, x, alinear in ((f"{i + 1}.", rect.x + 26, "izq"), (r.get("nombre", "???"), rect.x + 70, "izq"),
                                  (str(r.get("puntaje", 0)), rect.right - 110, "der"), (modo, rect.right - 22, "der")):
            s = fuente.render(texto, True, color)
            surface.blit(s, s.get_rect(**({"topleft": (x, y)} if alinear == "izq" else {"topright": (x, y)})))
        y += 30


def dibujar_medallas(surface, rect, desbloqueadas, seleccion, t=0):
    neon.panel(surface, rect, neon.MAGENTA, t)
    total = len(desbloqueadas & set(MEDALLAS))
    neon.titulo(surface, f"MEDALLAS  {total}/{len(MEDALLAS)}", 26, (255, 140, 230), rect.centerx, rect.y + 30, halo=False)
    cols = 4
    ancho = (rect.w - 40) // cols
    for i, (mid, (nombre, _, color)) in enumerate(MEDALLAS.items()):
        cx = rect.x + 20 + ancho * (i % cols) + ancho // 2
        cy = rect.y + 96 + (i // cols) * 96
        encendida = mid in desbloqueadas
        if i == seleccion:
            pixelfx.dibujar_halo(surface, pixelfx.apagar(color if encendida else WHITE, 0.4), cx, cy, 40 + 3 * math.sin(t * 0.15))
        icono = icono_medalla(color, encendida, escala=5)
        surface.blit(icono, icono.get_rect(center=(cx, cy)))
        etiqueta = render_texto_pixelado(get_font(11), nombre if encendida else "???",
                                         WHITE if encendida else (110, 100, 140))
        surface.blit(etiqueta, etiqueta.get_rect(center=(cx, cy + 36)))
    mid = list(MEDALLAS)[seleccion]
    nombre, desc, color = MEDALLAS[mid]
    texto = f"{nombre}: {desc}" if mid in desbloqueadas else f"???: {desc}"
    linea = render_texto_pixelado(get_font(14), texto, color if mid in desbloqueadas else (180, 170, 210))
    surface.blit(linea, linea.get_rect(center=(rect.centerx, rect.bottom - 24)))
