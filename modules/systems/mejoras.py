"""
Mejoras entre oleadas: cartas en pixel art neon para elegir una de tres.

Al arrancar la partida, cada 5 oleadas y despues de cada jefe el juego se
congela y aparecen tres cartas (SeleccionMejora). Se elige moviendo la nave
debajo de la carta y cerrando el puño (o el boton del mando), con las
flechas/1-2-3 + ENTER, o con el mouse. Cada mejora dura toda la partida y
algunas se pueden subir de nivel. Es la UNICA forma de conseguir buffs:
los enemigos y jefes ya no sueltan power-ups (ver MEJORAS); EstadoMejoras guarda los
niveles y los drones escolta."""

import math
import random

import pygame

from modules.constants import (
    GAME_WIDTH, GAME_HEIGHT, WHITE,
    BUFF_TYPE_TRIPLE_SHOT, BUFF_TYPE_PIERCING, BUFF_TYPE_LIGHTNING,
)
from modules.systems import pixelfx, audio, neon
from modules.systems.fonts import get_font, render_text

CONTORNO = pixelfx.CONTORNO
FONDO_CARTA = (22, 12, 52)

RAREZAS = {
    "comun": {"nombre": "COMUN", "color": (90, 220, 255), "peso": 6},
    "rara": {"nombre": "RARA", "color": (255, 90, 220), "peso": 3},
    "epica": {"nombre": "EPICA", "color": (255, 200, 60), "peso": 1},
}

# iconos de 11x11: o = contorno, c = color, l = color claro, w = blanco
_ICONOS = {
    "danio": [
        ".....o.....",
        "....olo....",
        ".o..olo..o.",
        "olo.olo.olo",
        ".olocwcolo.",
        "..ocwwwco..",
        ".olocwcolo.",
        "olo.olo.olo",
        ".o..olo..o.",
        "....olo....",
        ".....o.....",
    ],
    "cadencia": [
        "..o..o..o..",
        ".owo.owo.ow",
        ".olo.olo.ol",
        ".olo.olo.ol",
        ".oco.oco.oc",
        ".oco.oco.oc",
        "..o..o..o..",
        "...........",
        "..o..o..o..",
        ".oco.oco.oc",
        "..o..o..o..",
    ],
    "velocidad": [
        ".....o.....",
        "....owo....",
        "...olllo...",
        "..olcocco..",
        ".olco.ocllo",
        "olco...ocll",
        "..o.owo.o..",
        "...olllo...",
        "..olcocco..",
        ".olco.ocllo",
        ".oo.....oo.",
    ],
    "vida": [
        "...........",
        ".ooo...ooo.",
        "owllo.ollco",
        "owlllolllco",
        "olllllllcco",
        "olllllllcco",
        ".olllllcco.",
        "..ollllco..",
        "...ollco...",
        "....oco....",
        ".....o.....",
    ],
    "escudo": [
        "ooooooooooo",
        "owlllllllco",
        "olwlllllcco",
        "olllcwcllco",
        "olllwwwllco",
        "olllcwcllco",
        ".ollllllco.",
        ".olllllcco.",
        "..olllcco..",
        "...olcco...",
        "....ooo....",
    ],
    "triple": [
        "o....o....o",
        "wo..owo..ow",
        "lo..olo..ol",
        ".lo.olo.ol.",
        ".co.oco.oc.",
        "..o.oco.o..",
        "...........",
        "...ooooo...",
        "..olllllo..",
        ".olcwwwclo.",
        "ooooooooooo",
    ],
    "perforante": [
        ".....o.....",
        "....owo....",
        "...owwwo...",
        "....olo....",
        "oooooloooo.",
        "occcclcccco",
        "oooooloooo.",
        "....olo....",
        "....oco....",
        "...occco...",
        "....ooo....",
    ],
    "rayo": [
        "......oooo.",
        ".....owllo.",
        "....owllo..",
        "...owllo...",
        "..owllloooo",
        ".ollllllwlo",
        "ooooollllo.",
        "...ollllo..",
        "..ollco....",
        ".olco......",
        ".oo........",
    ],
    "dron": [
        "...........",
        "oooo...oooo",
        "llll...llll",
        "..o.....o..",
        "..oooooooo.",
        ".ollllllllo",
        "olllcwwcllo",
        "olllcwwclo.",
        ".occcccco..",
        "..o.o.o.o..",
        "...........",
    ],
    "zorrito": [
        ".o.......o.",
        "olo.....olo",
        "olco...ocl.",
        "ollcoooocl.",
        "olllllllllo",
        "ollwolwollo",
        "ollllllllo.",
        ".olwwwwwlo.",
        "..olwowlo..",
        "...ooooo...",
        "...........",
    ],
    "reparar": [
        "...ooooo...",
        "..olllllo..",
        ".ollwwwllo.",
        "olllwwwlllo",
        "owwwwwwwwwo",
        "owwwwwwwwwo",
        "olllwwwlllo",
        ".ollwwwllo.",
        "..olllllo..",
        "...ooooo...",
        "...........",
    ],
}

# id, nombre, texto, rareza, nivel maximo, color del icono
MEJORAS = {
    "danio": ("POTENCIA", "Cada bala pega +1 de daño", "rara", 2, (255, 120, 90)),
    "cadencia": ("CADENCIA", "Disparas un 20% mas seguido", "comun", 3, (120, 230, 255)),
    "velocidad": ("TURBO", "La nave se mueve mas rapido", "comun", 3, (130, 255, 190)),
    "vida": ("CASCO EXTRA", "+1 vida maxima y vida llena", "comun", 3, (255, 110, 150)),
    "escudo": ("ESCUDO VIVO", "Una carga de escudo que se recarga sola", "comun", 2, (110, 200, 255)),
    "triple": ("TRIPLE CAÑON", "Rafaga triple para siempre", "epica", 1, (255, 210, 90)),
    "perforante": ("PERFORADOR", "Las balas atraviesan todo", "rara", 1, (255, 170, 110)),
    "rayo": ("TORMENTA", "Campo electrico para siempre", "epica", 1, (185, 240, 255)),
    "dron": ("DRON ESCOLTA", "Un dron que dispara a tu lado", "rara", 2, (120, 255, 200)),
    "zorrito": ("ZORRITO", "El Zorrito Espacial se une ya", "epica", 1, (245, 132, 42)),
    "reparar": ("REPARAR", "Recupera toda la vida", "comun", 99, (130, 255, 150)),
}


def icono(mejora_id, escala=2):
    clave = ("mejora_icono", mejora_id, escala)
    surf = pixelfx._cache.get(clave)
    if surf is not None:
        return surf
    color = MEJORAS[mejora_id][4]
    colores = {"o": CONTORNO, "c": color, "l": pixelfx.aclarar(color, 0.45), "w": WHITE}
    filas = _ICONOS[mejora_id]
    surf = pygame.Surface((len(filas[0]) * escala, len(filas) * escala), pygame.SRCALPHA)
    for y, fila in enumerate(filas):
        for x, ch in enumerate(fila):
            c = colores.get(ch)
            if c is not None:
                surf.fill(c, (x * escala, y * escala, escala, escala))
    return pixelfx._guardar(clave, surf)


def _buff_para_siempre(ship, buff_type):
    """El buff queda como los de clase: no vence y el HUD lo muestra fijo."""
    ship.apply_buff(buff_type)
    ship.class_buffs.add(buff_type)


class EstadoMejoras:
    """Niveles tomados en la partida y los drones escolta."""

    def __init__(self):
        self.niveles = {}
        self.drones = []

    def nivel(self, mejora_id):
        return self.niveles.get(mejora_id, 0)

    def opciones(self, ship, tiene_mascota, cantidad=3):
        """Tres mejoras distintas al azar, pesadas por rareza."""
        disponibles = []
        for mid, (_, _, rareza, maximo, _) in MEJORAS.items():
            if self.nivel(mid) >= maximo:
                continue
            if mid == "reparar" and ship.lives >= ship.max_lives:
                continue
            if mid == "zorrito" and tiene_mascota:
                continue
            if mid == "perforante" and BUFF_TYPE_PIERCING in ship.class_buffs:
                continue
            disponibles.append(mid)
        elegidas = []
        while disponibles and len(elegidas) < cantidad:
            pesos = [RAREZAS[MEJORAS[m][2]]["peso"] for m in disponibles]
            mid = random.choices(disponibles, weights=pesos)[0]
            disponibles.remove(mid)
            elegidas.append(mid)
        return elegidas

    def aplicar(self, mejora_id, ship):
        """Aplica la mejora a la nave. "zorrito" lo resuelve main.py (la
        mascota vive ahi); el resto queda listo aca."""
        from modules.entities.dron import DronEscolta

        self.niveles[mejora_id] = self.nivel(mejora_id) + 1
        if mejora_id == "danio":
            ship.damage_multiplier += 1.0
        elif mejora_id == "cadencia":
            ship.base_shoot_delay = max(6, int(round(ship.base_shoot_delay * 0.8)))
            ship.shoot_delay = max(5, int(round(ship.shoot_delay * 0.8)))
        elif mejora_id == "velocidad":
            ship.permanent_speed_bonus += 0.03
        elif mejora_id == "vida":
            ship.max_lives += 1
            ship.lives = ship.max_lives
        elif mejora_id == "escudo":
            ship.sumar_escudo_recargable()
        elif mejora_id == "triple":
            _buff_para_siempre(ship, BUFF_TYPE_TRIPLE_SHOT)
        elif mejora_id == "perforante":
            _buff_para_siempre(ship, BUFF_TYPE_PIERCING)
        elif mejora_id == "rayo":
            _buff_para_siempre(ship, BUFF_TYPE_LIGHTNING)
        elif mejora_id == "dron":
            lado = -1 if len(self.drones) % 2 == 0 else 1
            self.drones.append(DronEscolta(ship, lado))
        elif mejora_id == "reparar":
            ship.lives = ship.max_lives
        ship.health_deplete_anim = ship.lives / max(1, ship.max_lives)


def _envolver(texto, fuente, ancho):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


class SeleccionMejora:
    """Overlay de tres cartas. update(ship) devuelve el id elegido una vez
    que termino la animacion de confirmacion (None mientras tanto)."""

    ANCHO = 236
    ALTO = 300
    CENTROS = (GAME_WIDTH // 2 - 280, GAME_WIDTH // 2, GAME_WIDTH // 2 + 280)
    ESPERA = 40          # cuadros antes de aceptar el puño (que no se elija sin querer)
    CONFIRMACION = 38

    def __init__(self, opciones, titulo, modo_control="camara", niveles=None):
        self.opciones = list(opciones)
        self.niveles = dict(niveles or {})
        self.titulo = titulo
        self.modo_control = modo_control
        self.t = 0
        self.cursor = len(self.opciones) // 2
        self.elegida = None
        self.timer_confirmar = 0
        self._ultimo_x = None
        self.cy = GAME_HEIGHT // 2 + 4

    def _rect(self, i):
        r = pygame.Rect(0, 0, self.ANCHO, self.ALTO)
        r.center = (self.CENTROS[i], self.cy)
        return r

    def _confirmar(self, i):
        if self.elegida is not None or not (0 <= i < len(self.opciones)):
            return
        self.cursor = i
        self.elegida = i
        self.timer_confirmar = self.CONFIRMACION
        audio.sonido_powerup()

    def handle_event(self, event, offset_x=0, offset_y=0):
        if self.elegida is not None:
            return
        n = len(self.opciones)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.cursor = (self.cursor - 1) % n
                audio.sonido_boton()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.cursor = (self.cursor + 1) % n
                audio.sonido_boton()
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self._confirmar(event.key - pygame.K_1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.t > 12:
                self._confirmar(self.cursor)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mx, my = event.pos[0] - offset_x, event.pos[1] - offset_y
            for i in range(n):
                if self._rect(i).collidepoint(mx, my):
                    self.cursor = i
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.t > 12:
                        self._confirmar(i)

    def update(self, ship):
        self.t += 1
        if self.elegida is not None:
            ship.burst_shots_pending = 0
            self.timer_confirmar -= 1
            if self.timer_confirmar <= 0:
                return self.opciones[self.elegida]
            return None
        # la carta que queda encima de la nave es la marcada
        if self._ultimo_x is None or abs(ship.x - self._ultimo_x) > 3:
            self._ultimo_x = ship.x
            if self.t > 1:
                cerca = min(range(len(self.opciones)), key=lambda i: abs(self.CENTROS[i] - ship.x))
                if cerca != self.cursor:
                    self.cursor = cerca
        if ship.burst_shots_pending > 0:
            ship.burst_shots_pending = 0
            if self.t > self.ESPERA:
                self._confirmar(self.cursor)
        return None

    # ------------------------------------------------------------- dibujo

    def _dibujar_carta(self, surface, i, mid):
        nombre, texto, rareza, maximo, color = MEJORAS[mid]
        r_color = RAREZAS[rareza]["color"]
        marcada = i == self.cursor
        rect = self._rect(i)

        # entrada: suben desde abajo una detras de otra
        entrada = max(0.0, min(1.0, (self.t - i * 6) / 22))
        entrada = 1 - (1 - entrada) ** 3
        rect.y += int((1 - entrada) * (GAME_HEIGHT - rect.y + 20))
        if marcada and self.elegida is None:
            rect.y -= 14 + int(math.sin(self.t * 0.15) * 3)

        if self.elegida is not None:
            k = 1 - self.timer_confirmar / self.CONFIRMACION
            if i == self.elegida:
                rect = rect.inflate(int(30 * math.sin(min(1.0, k * 2) * math.pi / 2)), int(30 * math.sin(min(1.0, k * 2) * math.pi / 2)))
                rect.y -= int(k * 20)
            else:
                rect.y += int(k * k * 420)

        # halo de la rareza
        brillo = r_color if marcada else pixelfx.apagar(r_color, 0.45)
        pixelfx.dibujar_halo(surface, brillo, rect.centerx, rect.centery, int(self.ANCHO * (0.8 if marcada else 0.62)))

        surface.fill(CONTORNO, rect.inflate(8, 8))
        surface.fill(FONDO_CARTA, rect)
        # franjas de scanline adentro
        for y in range(rect.y + 6, rect.bottom - 4, 6):
            surface.fill((28, 16, 62), (rect.x + 6, y, rect.w - 12, 2))
        neon.marco_pixel(surface, rect, r_color if marcada else pixelfx.apagar(r_color, 0.6))
        if marcada and (self.t // 8) % 2 == 0 and self.elegida is None:
            neon.marco_pixel(surface, rect.inflate(-12, -12), pixelfx.aclarar(r_color, 0.5), 2)

        # cartel de rareza arriba
        etiqueta = render_text(RAREZAS[rareza]["nombre"], 13, CONTORNO, bold=True, outline=False)
        cinta = pygame.Rect(0, 0, etiqueta.get_width() + 20, 22)
        cinta.midtop = (rect.centerx, rect.y + 10)
        surface.fill(r_color, cinta)
        surface.blit(etiqueta, etiqueta.get_rect(center=cinta.center))

        # icono grande con su luz
        ico = icono(mid, 7)
        icy = rect.y + 50 + ico.get_height() // 2 + int(math.sin(self.t * 0.08 + i) * 3)
        pixelfx.dibujar_halo(surface, color, rect.centerx, icy, 62 if marcada else 48)
        surface.blit(ico, ico.get_rect(center=(rect.centerx, icy)))

        nom = render_text(nombre, 20, pixelfx.aclarar(color, 0.35), bold=True)
        surface.blit(nom, nom.get_rect(center=(rect.centerx, rect.y + 160)))
        fuente = get_font(15)
        for k, linea in enumerate(_envolver(texto, fuente, rect.w - 32)):
            s = fuente.render(linea, True, (220, 222, 245))
            surface.blit(s, s.get_rect(center=(rect.centerx, rect.y + 194 + k * 20)))

        # niveles: un cuadrito por nivel (lleno = ya tomado, el que sigue late)
        nivel = self.niveles.get(mid, 0)
        if maximo <= 5:
            lado, gap = 12, 6
            total = maximo * lado + (maximo - 1) * gap
            x0 = rect.centerx - total // 2
            yb = rect.bottom - 38
            for n in range(maximo):
                caja = (x0 + n * (lado + gap), yb, lado, lado)
                surface.fill(CONTORNO, pygame.Rect(caja).inflate(4, 4))
                if n < nivel:
                    surface.fill(color, caja)
                elif n == nivel:
                    surface.fill(WHITE if (self.t // 10) % 2 == 0 else color, caja)
                else:
                    surface.fill((50, 36, 90), caja)

        if marcada and self.elegida is None:
            # flechita que apunta a la nave
            ay = rect.bottom + 14 + int(math.sin(self.t * 0.2) * 3)
            for k in range(5):
                surface.fill(r_color, (rect.centerx - (5 - k) * 2, ay + k * 2, (5 - k) * 4, 2))

        if self.elegida == i:
            k = self.timer_confirmar / self.CONFIRMACION
            if k > 0.6:
                flash = pygame.Surface(rect.size)
                flash.fill(tuple(int(255 * (k - 0.6) / 0.4) for _ in range(3)))
                surface.blit(flash, rect.topleft, special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, surface):
        velo = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        velo.fill((6, 2, 20, min(170, self.t * 12)))
        surface.blit(velo, (0, 0))

        titulo = render_text(self.titulo, 30, (255, 236, 160), bold=True)
        ty = 46 - max(0, 20 - self.t) * 3
        pixelfx.dibujar_halo(surface, (255, 180, 60), GAME_WIDTH // 2, ty + titulo.get_height() // 2, 150)
        surface.blit(titulo, titulo.get_rect(midtop=(GAME_WIDTH // 2, ty)))

        for i, mid in enumerate(self.opciones):
            if i != self.cursor:
                self._dibujar_carta(surface, i, mid)
        if self.opciones:
            self._dibujar_carta(surface, self.cursor, self.opciones[self.cursor])

        if self.elegida is None:
            if self.modo_control == "mando":
                ayuda = "Mueve la nave debajo de una carta y aprieta el boton"
            else:
                ayuda = "Mueve la nave debajo de una carta y cierra el puño"
            s = render_text(ayuda, 15, (200, 205, 235))
            surface.blit(s, s.get_rect(midbottom=(GAME_WIDTH // 2, GAME_HEIGHT - 32)))
            s2 = render_text("Teclado: flechas + ENTER  |  1 2 3  |  mouse", 12, (140, 145, 185))
            surface.blit(s2, s2.get_rect(midbottom=(GAME_WIDTH // 2, GAME_HEIGHT - 12)))


def dibujar_hud_mejoras(surface, estado, t=0):
    """Iconitos de las mejoras tomadas abajo a la izquierda del area de juego,
    con el nivel al lado cuando es mayor a 1."""
    x = 12
    y = GAME_HEIGHT - 48
    for mid, nivel in estado.niveles.items():
        if mid == "reparar" or nivel <= 0:
            continue
        color = MEJORAS[mid][4]
        ico = icono(mid, 3)
        caja = pygame.Rect(x - 4, y - 4, ico.get_width() + 8, ico.get_height() + 8)
        surface.fill(CONTORNO, caja.inflate(4, 4))
        surface.fill(FONDO_CARTA, caja)
        neon.marco_pixel(surface, caja, pixelfx.apagar(color, 0.7), 2)
        surface.blit(ico, (x, y))
        if nivel > 1:
            n = render_text(f"x{nivel}", 12, pixelfx.aclarar(color, 0.4), bold=True)
            surface.blit(n, (caja.right - n.get_width() + 4, caja.bottom - n.get_height() + 6))
        x += caja.w + 10
