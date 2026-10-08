"""
HUD y pantallas de estado del juego en si (no del menu, ver
modules/systems/menu.py para eso): la cuenta regresiva inicial, el HUD de
vida/puntaje/oleada, la barra de casco, la vista previa de camara
y las pantallas de fin de partida (game over / victoria) con sus
estadisticas."""

import pygame
import math
from modules.constants import (
    WHITE, ROSA, MENTA, AMARILLO, AZUL, AZUL_CIELO, MELON, LAVANDA, ROSA_CHICLE,
    GAME_WIDTH, GAME_HEIGHT, SHADOW,
)
from modules.systems.fonts import get_font, render_text, render_texto_pixelado
from modules.systems import neon, pixelfx


def _texto_ajustado(texto, fuente, color, ancho_maximo):
    """Renderiza texto pixelado y lo reduce (si hace falta) para que quepa
    en ancho_maximo, sin importar que fuente termine cargando el sistema en
    la maquina donde corra el juego."""
    return render_texto_pixelado(fuente, texto, color, ancho_maximo=ancho_maximo)


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def clamp(val, min_val, max_val):
    return max(min_val, min(max_val, val))


class AnimatedValue:
    """Numero que persigue a `target` con resorte amortiguado en vez de
    saltar de golpe (usado por el puntaje y las vidas del HUD)."""

    def __init__(self, value, speed=0.15):
        self.current = float(value)
        self.target = float(value)
        self.speed = speed
        self.velocity = 0.0

    def set(self, value):
        self.target = float(value)

    def update(self):
        diff = self.target - self.current
        self.velocity += diff * self.speed
        self.velocity *= 0.85
        self.current += self.velocity
        if abs(diff) < 0.01 and abs(self.velocity) < 0.01:
            self.current = self.target
            self.velocity = 0.0

    def get(self):
        return self.current


# jefe que espera al final de cada tramo de oleadas -> sprite pixel y
# colores con los que aparece en la pelea (fase 1)
_SILUETA_JEFE = {
    "sentinel": "centinela",
    "dragon": "dragon_a",
    "titan": "titan_px",
    "anomalia": "anomalia_px",
    "mega": "coloso_crucero",
}


def _colores_jefe(boss_id):
    if boss_id == "sentinel":
        from modules.core.boss_system import BOSS_DEFINITIONS
        d = BOSS_DEFINITIONS[0]
        return d.primary_color, tuple(d.secondary_color[:3])
    if boss_id == "dragon":
        from modules.entities.dragon_boss import COLORES_FASE
        return COLORES_FASE[1]
    if boss_id == "titan":
        from modules.entities.titan_boss import COLORES_FASE
        return COLORES_FASE[1][0], pixelfx.aclarar(COLORES_FASE[1][0], 0.3)
    if boss_id == "anomalia":
        from modules.entities.boss import COLORES_FASE
        return COLORES_FASE[1]
    from modules.systems.sprites import MEGA_FASES
    return MEGA_FASES["cruiser"][1], MEGA_FASES["cruiser"][2]


def _jefes_por_oleada():
    from modules.core.boss_system import BOSS_DEFINITIONS
    from modules.constants import MEGA_BOSS_SPAWN_WAVE
    jefes = [(d.spawn_wave, d.boss_id) for d in BOSS_DEFINITIONS]
    jefes.append((MEGA_BOSS_SPAWN_WAVE, "mega"))
    return sorted(jefes)


def _silueta_jefe(boss_id, apagado=False, alto=30):
    """Mini retrato del jefe con sus colores de verdad (el mismo sprite
    pixel de la pelea, achicado) y contorno oscuro. El Titan suma sus
    tentaculos, que en el juego se dibujan aparte. apagado: version oscura
    para cuando el jefe todavia esta lejos."""
    clave = ("retrato_hud", boss_id, apagado, alto)
    s = pixelfx._cache.get(clave)
    if s is not None:
        return s
    from modules.systems import sprites
    kind = _SILUETA_JEFE[boss_id]
    if not sprites.es_pixel("boss", kind):
        return None
    cuerpo, alas = _colores_jefe(boss_id)
    w, h = sprites.tamano_pixel("boss", kind, 1)
    sprite = sprites.get_boss_surface(cuerpo, alas, w, h, kind=kind)
    if boss_id == "titan":
        # tentaculos colgando del vientre
        con_tentaculos = pygame.Surface((w, h + 8), pygame.SRCALPHA)
        con_tentaculos.blit(sprite, (0, 0))
        _, color_t = __import__("modules.entities.titan_boss", fromlist=["COLORES_FASE"]).COLORES_FASE[1]
        for k, x0 in enumerate(range(w // 6, w - w // 8, max(2, w // 6))):
            for paso in range(6):
                x = x0 + int(math.sin(paso * 0.9 + k) * 1.5)
                con_tentaculos.fill(color_t, (x, h - 4 + paso * 2, 2, 2))
        sprite = con_tentaculos
    ancho = max(1, round(sprite.get_width() * alto / sprite.get_height()))
    chico = pygame.transform.scale(sprite, (ancho, alto))
    if apagado:
        chico = chico.copy()
        chico.fill((95, 85, 140, 255), special_flags=pygame.BLEND_RGBA_MULT)
    # contorno de un pixel alrededor
    mascara = pygame.mask.from_surface(chico)
    borde = mascara.to_surface(setcolor=(*neon.CONTORNO, 255), unsetcolor=(0, 0, 0, 0))
    s = pygame.Surface((ancho + 4, alto + 4), pygame.SRCALPHA)
    for dx, dy in ((0, 2), (4, 2), (2, 0), (2, 4), (1, 1), (3, 3), (1, 3), (3, 1)):
        s.blit(borde, (dx, dy))
    s.blit(chico, (2, 2))
    return pixelfx._guardar(clave, s)


def _color_rgb(t, desfase=0, sat=75):
    color = pygame.Color(0)
    color.hsva = ((t * 2 + desfase) % 360, sat, 100, 100)
    return (color.r, color.g, color.b)


class ModernHUD:
    """Contador de arriba a la izquierda en estilo neon RGB: puntaje,
    oleada y una barra de progreso hasta el proximo jefe con su silueta.
    La vida esta en la barra de CASCO de abajo (draw_ship_status_bar)."""

    ANCHO = 236
    ALTO = 112

    def __init__(self, max_hp):
        self.score_value = AnimatedValue(0, speed=0.2)
        self.progreso = AnimatedValue(0, speed=0.08)
        self.wave_value = 1
        self.objetivos = 0
        self.objetivos_meta = 1
        self.jefe_activo = False
        self.t = 0
        self.jefes = _jefes_por_oleada()

    def update(self, score, wave, lives, buffs, hand_active, objetivos=0, objetivos_meta=1, jefe_activo=False):
        self.t += 1
        self.score_value.set(score)
        self.score_value.update()
        self.wave_value = wave
        self.objetivos = objetivos
        self.objetivos_meta = max(1, objetivos_meta)
        self.jefe_activo = jefe_activo
        desde, jefe_wave, _ = self._tramo()
        if jefe_wave is None:
            meta = 1.0
        elif jefe_activo or wave >= jefe_wave:
            meta = 1.0
        else:
            hechas = (wave - desde) + min(1.0, objetivos / self.objetivos_meta)
            meta = hechas / max(1, jefe_wave - desde)
        self.progreso.set(max(0.0, min(1.0, meta)))
        self.progreso.update()

    def _tramo(self):
        """(oleada donde empezo el tramo, oleada del proximo jefe, boss_id)."""
        anterior = 1
        for jefe_wave, boss_id in self.jefes:
            if self.wave_value <= jefe_wave:
                return anterior, jefe_wave, boss_id
            anterior = jefe_wave + 1
        return anterior, None, None

    def draw(self, surface):
        t = self.t
        borde = _color_rgb(t)
        caja = pygame.Rect(10, 10, self.ANCHO, self.ALTO)
        neon.panel(surface, caja, borde, t, halo=False, alfa=215, brillo_interno=False)

        # puntaje: etiqueta con letras de colores y numero con sombra
        x = caja.x + 14
        for k, letra in enumerate("SCORE"):
            l = neon.texto(13, letra, _color_rgb(t, k * 40))
            surface.blit(l, (x, caja.y + 10))
            x += l.get_width() + 1
        oleada = neon.texto(13, f"OLEADA {self.wave_value}", neon.CIAN)
        surface.blit(oleada, (caja.right - oleada.get_width() - 14, caja.y + 10))
        valor = neon.texto(26, f"{int(self.score_value.get()):,}".replace(",", "."), WHITE)
        sombra = neon.texto(26, f"{int(self.score_value.get()):,}".replace(",", "."), neon.CONTORNO)
        surface.blit(sombra, (caja.x + 16, caja.y + 30))
        surface.blit(valor, (caja.x + 14, caja.y + 28))

        # progreso hasta el proximo jefe
        _, jefe_wave, boss_id = self._tramo()
        barra = pygame.Rect(caja.x + 14, caja.y + 80, 150, 14)
        if jefe_wave is None:
            etiqueta = "FASE BONUS"
        elif self.jefe_activo:
            etiqueta = "¡JEFE EN PANTALLA!"
        else:
            etiqueta = f"PROXIMO JEFE: OLEADA {jefe_wave}"
        txt = neon.texto(11, etiqueta, ROSA_CHICLE if self.jefe_activo else (200, 200, 230), bold=False)
        surface.blit(txt, (barra.x, barra.y - 16))
        surface.fill(neon.CONTORNO, barra.inflate(6, 6))
        surface.fill(neon.FONDO, barra.inflate(2, 2))
        bloques = 12
        ancho = barra.w / bloques
        llenos = self.progreso.get() * bloques
        for k in range(bloques):
            r = pygame.Rect(int(barra.x + k * ancho) + 1, barra.y + 1, int(ancho) - 2, barra.h - 2)
            if k < int(llenos) or (k == int(llenos) and llenos - int(llenos) > 0.5):
                c = _color_rgb(t, -k * 22)
                surface.fill(c, r)
                surface.fill(pixelfx.aclarar(c, 0.5), (r.x, r.y, r.w, 3))
            else:
                surface.fill((45, 34, 84), r)

        if boss_id is not None:
            cerca = self.jefe_activo or self.progreso.get() > 0.85
            sil = _silueta_jefe(boss_id, apagado=not (cerca and (t // 10) % 2 == 0))
            if sil is not None:
                cx, cy = caja.right - 34, barra.centery - 4
                if cerca:
                    pixelfx.dibujar_halo(surface, pixelfx.apagar(ROSA_CHICLE, 0.4), cx, cy, 28)
                surface.blit(sil, sil.get_rect(center=(cx, cy)))


def draw_hud(surface, score, wave, lives, buffs, font, small_font, hand_active=False, max_hp=3,
             objetivos=0, objetivos_meta=1, jefe_activo=False):
    if not hasattr(draw_hud, 'hud'):
        draw_hud.hud = ModernHUD(max_hp)
    hud = draw_hud.hud
    hud.update(score, wave, lives, buffs, hand_active, objetivos, objetivos_meta, jefe_activo)
    hud.draw(surface)


def draw_ship_status_bar(surface, lives, max_lives, offset_x, offset_y, ticks=0):
    """Consola de vida de la nave en el margen inferior (fuera del
    viewport): un segmento iluminado por vida restante, estilo panel de
    nave, en vez de una barra continua (mas legible con pocas vidas). Se
    dibuja aparte de la barrita chica del panel de score, mas visible."""
    max_lives = max(1, int(max_lives))
    cx = offset_x + GAME_WIDTH // 2
    bar_y = offset_y + GAME_HEIGHT + 12

    seg_w, seg_h, seg_gap = 34, 16, 6
    total_w = max_lives * seg_w + (max_lives - 1) * seg_gap
    start_x = cx - total_w // 2

    label = render_texto_pixelado(get_font(12, bold=True), "CASCO", (205, 215, 235))
    surface.blit(label, (start_x - label.get_width() - 12, bar_y + seg_h // 2 - label.get_height() // 2))

    ratio = lives / max_lives if max_lives else 0
    color = ROSA if ratio > 0.5 else (AMARILLO if ratio > 0.25 else MELON)
    pulse = 0.5 + 0.5 * math.sin(ticks * 0.008)

    for i in range(max_lives):
        seg_x = start_x + i * (seg_w + seg_gap)
        rect = (seg_x, bar_y, seg_w, seg_h)
        if i < lives:
            fill_color = color
            if lives == 1 and max_lives > 1:
                # ultima vida: parpadea como alarma de casco critico
                fill_color = tuple(min(255, int(c * (0.6 + 0.5 * pulse))) for c in color[:3])
            pygame.draw.rect(surface, fill_color, rect, border_radius=3)
            hl_h = max(1, seg_h // 3)
            hl = pygame.Surface((seg_w - 4, hl_h), pygame.SRCALPHA)
            for row in range(hl_h):
                a = int(80 * (1 - row / hl_h))
                pygame.draw.line(hl, (255, 255, 255, a), (0, row), (seg_w - 5, row))
            surface.blit(hl, (seg_x + 2, bar_y + 2))
        else:
            pygame.draw.rect(surface, (22, 22, 34), rect, border_radius=3)
        pygame.draw.rect(surface, (*AZUL_CIELO[:3], 190), rect, width=1, border_radius=3)

    ship_x = start_x + total_w + 18
    ship_y = bar_y + seg_h // 2
    pygame.draw.polygon(surface, AZUL_CIELO, [
        (ship_x, ship_y - 8), (ship_x - 7, ship_y + 7), (ship_x, ship_y + 3), (ship_x + 7, ship_y + 7),
    ])


def draw_viewport_frame(surface, x, y, w, h, timestamp):
    """Marco del area de juego con resplandor pulsante y acentos en las
    esquinas, para que el borde se sienta parte del espacio de fondo (donde
    ya se dibujaron estrellas) en vez de una linea plana y estatica."""
    pulse = 0.5 + 0.5 * math.sin(timestamp * 0.0015)

    glow_surf = pygame.Surface((w + 64, h + 64), pygame.SRCALPHA)
    base_alpha = 22 + int(14 * pulse)
    for i in range(5):
        expand = i * 6
        alpha = max(0, base_alpha - i * 4)
        pygame.draw.rect(
            glow_surf, (*AZUL_CIELO[:3], alpha),
            (30 - expand, 30 - expand, w + 4 + expand * 2, h + 4 + expand * 2),
            width=2, border_radius=8,
        )
    surface.blit(glow_surf, (x - 32, y - 32))

    pygame.draw.rect(surface, AZUL, (x - 2, y - 2, w + 4, h + 4), width=2, border_radius=4)

    corner = 18
    for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        pygame.draw.line(surface, WHITE, (cx, cy), (cx + dx * corner, cy), 2)
        pygame.draw.line(surface, WHITE, (cx, cy), (cx, cy + dy * corner), 2)


def draw_camera_preview(surface, preview_surf, preview_rect, timestamp):
    shadow_surf = pygame.Surface((preview_rect.width + 4, preview_rect.height + 4), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, SHADOW, (2, 2, preview_rect.width, preview_rect.height), border_radius=8)
    surface.blit(shadow_surf, (preview_rect.x - 2, preview_rect.y - 2))

    border_surf = pygame.Surface((preview_rect.width + 4, preview_rect.height + 4), pygame.SRCALPHA)
    pulse = abs(math.sin(timestamp * 0.004))
    border_color = (int(AZUL[0] * (0.7 + 0.3 * pulse)), int(AZUL[1] * (0.7 + 0.3 * pulse)), int(AZUL[2] * (0.7 + 0.3 * pulse)), 200)
    pygame.draw.rect(border_surf, border_color, (2, 2, preview_rect.width, preview_rect.height), width=1, border_radius=8)
    surface.blit(border_surf, (preview_rect.x - 2, preview_rect.y - 2))

    surface.blit(preview_surf, preview_rect)

    label_surf = render_text("CAM", 11, WHITE)
    surface.blit(label_surf, (preview_rect.x + 4, preview_rect.y + preview_rect.height + 3))


def draw_countdown(surface, game_w, game_h, countdown_val, countdown_fraction, font, info_font, big_font, control_hint=""):
    """Pantalla de preparacion antes de que arranque la partida, en pixel
    art neon: un anillo de bloques que se van apagando con el tiempo
    restante y el numero grande en el centro, sobre el fondo de estrellas
    que ya dibujo el llamador. countdown_fraction va de 1.0 (recien
    empezo) a 0.0 (arranca la partida)."""
    t = pygame.time.get_ticks() // 16
    cx, cy = game_w // 2, game_h // 2 - 20
    radio = 84

    neon.titulo(surface, "NAVE VS ASTEROIDES", 22, (170, 190, 255), cx, cy - radio - 70, halo=False)

    frac = max(0.0, min(1.0, countdown_fraction))
    segmentos = 28
    encendidos = int(round(frac * segmentos))
    pixelfx.dibujar_halo(surface, neon.CIAN, cx, cy, radio + 40)
    for i in range(segmentos):
        a = -math.pi / 2 + 2 * math.pi * i / segmentos
        x, y = cx + math.cos(a) * radio, cy + math.sin(a) * radio
        if i < encendidos:
            color = neon.CIAN if i < encendidos - 1 or (t // 6) % 2 else WHITE
            neon.cuadro_pixel(surface, neon.CONTORNO, x, y, 14)
            neon.cuadro_pixel(surface, color, x, y, 10)
        else:
            neon.cuadro_pixel(surface, (40, 30, 80), x, y, 8)

    neon.titulo(surface, str(countdown_val), 86, WHITE, cx, cy + 4)
    neon.cinta(surface, "PREPARATE", neon.CIAN, (cx, cy + radio + 34), tam=16)

    if control_hint:
        hint = render_texto_pixelado(get_font(14), control_hint, (150, 160, 200))
        surface.blit(hint, (game_w // 2 - hint.get_width() // 2, cy + radio + 62))


def formatear_tiempo(segundos):
    segundos = max(0, int(segundos))
    return f"{segundos // 60}:{segundos % 60:02d}"


def _dibujar_stats_partida(surface, game_w, y, stats):
    """Dos lineas compactas con precision/tiempo y el desglose de enemigos
    destruidos. stats es un dict (ver terminar_partida() en main.py); si es
    None no se dibuja nada (compatibilidad con llamadas viejas)."""
    if not stats:
        return y
    disparos = stats.get("disparos", 0)
    aciertos = stats.get("aciertos", 0)
    precision = int(round(100 * aciertos / disparos)) if disparos > 0 else 0
    tiempo = formatear_tiempo(stats.get("tiempo", 0))

    linea1 = render_texto_pixelado(get_font(15), f"Precision: {precision}%   Tiempo: {tiempo}", MENTA)
    surface.blit(linea1, (game_w // 2 - linea1.get_width() // 2, y))

    linea2 = render_texto_pixelado(
        get_font(15),
        f"Asteroides: {stats.get('asteroides', 0)}   "
        f"Alienigenas: {stats.get('alienigenas', 0)}   "
        f"Jefes: {stats.get('jefes', 0)}",
        (200, 200, 220),
    )
    surface.blit(linea2, (game_w // 2 - linea2.get_width() // 2, y + 22))
    return y + 22 + linea2.get_height()


def _pantalla_final(surface, game_w, game_h, color):
    """Velo oscuro + panel neon de las pantallas de fin de partida."""
    neon.velo(surface, (6, 2, 20), 175)
    caja = pygame.Rect(0, 0, 620, 268)
    caja.midtop = (game_w // 2, game_h // 2 - 178)
    neon.panel(surface, caja, color, pygame.time.get_ticks() // 16)
    return caja


_CALAVERA_BOTON = (
    "..XXXXX..",
    ".XXXXXXX.",
    "XXXXXXXXX",
    "XOOXXXOOX",
    "XOOXXXOOX",
    "XXXXOXXXX",
    ".XXXXXXX.",
    "..X.X.X..",
    "..XXXXX..",
)


def _dibujar_calavera_boton(surface, cx, cy, t):
    """Calavera que late sobre "Intentar de Nuevo": aviso de que, si
    reintentas, te espera la Parca."""
    pulso = 0.5 + 0.5 * math.sin(t * 0.12)
    escala = 3 + (1 if pulso > 0.75 else 0)
    ojo = (255, int(40 + 150 * pulso), 60)
    w, h = len(_CALAVERA_BOTON[0]) * escala, len(_CALAVERA_BOTON) * escala
    x0, y0 = cx - w // 2, cy - h // 2
    brillo = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
    pygame.draw.ellipse(brillo, (255, 40, 70, int(50 + 70 * pulso)), brillo.get_rect())
    surface.blit(brillo, (x0 - 12, y0 - 12))
    for fy, fila in enumerate(_CALAVERA_BOTON):
        for fx, c in enumerate(fila):
            if c == ".":
                continue
            color = (235, 230, 220) if c == "X" else ojo
            surface.fill(color, (x0 + fx * escala, y0 + fy * escala, escala, escala))
    for fy, fila in enumerate(_CALAVERA_BOTON):
        for fx, c in enumerate(fila):
            if c != ".":
                continue
            vecinos = [(fx + dx, fy + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if any(0 <= vx < len(fila) and 0 <= vy < len(_CALAVERA_BOTON) and _CALAVERA_BOTON[vy][vx] != "."
                   for vx, vy in vecinos):
                surface.fill((40, 0, 10), (x0 + fx * escala, y0 + fy * escala, escala, escala))


def draw_game_over(surface, game_w, game_h, score, wave, font, big_font, buttons=None, selected=0, stats=None,
                   calavera=False):
    caja = _pantalla_final(surface, game_w, game_h, neon.ROJO)
    neon.titulo(surface, "GAME OVER", 50, (255, 110, 140), game_w // 2, caja.y + 40)
    sc_text = render_texto_pixelado(font, f"Puntuacion Final: {score}", WHITE)
    wt_text = render_texto_pixelado(font, f"Oleada Alcanzada: {wave}", AZUL)
    surface.blit(sc_text, (game_w // 2 - sc_text.get_width() // 2, game_h // 2 - 98))
    surface.blit(wt_text, (game_w // 2 - wt_text.get_width() // 2, game_h // 2 - 72))

    _dibujar_stats_partida(surface, game_w, game_h // 2 - 40, stats)

    if buttons:
        btn_w = 150
        btn_h = 40
        spacing = 180
        base_x = game_w // 2 - btn_w // 2 - spacing // 2
        y = game_h // 2 + 30
        t = pygame.time.get_ticks() // 16
        for i, (label, color) in enumerate(buttons):
            if calavera and i == 1:
                color = (255, 50, 70)
            neon.boton(surface, (base_x + i * spacing, y, btn_w, btn_h), label, color, i == selected, t)
        if calavera and len(buttons) > 1:
            _dibujar_calavera_boton(surface, base_x + spacing + btn_w - 2, y - 4, t)
    neon.scanlines(surface)


def draw_victory_screen(surface, game_w, game_h, score, wave, font, big_font, stats=None,
                        subtitulo="Has derrotado al Coloso"):
    caja = _pantalla_final(surface, game_w, game_h, neon.ORO)
    neon.titulo(surface, "VICTORIA", 54, AMARILLO, game_w // 2, caja.y + 42)
    sub = render_texto_pixelado(font, subtitulo, WHITE)
    sc_text = render_texto_pixelado(font, f"Puntuacion Final: {score}", WHITE)
    wt_text = render_texto_pixelado(font, f"Oleada Alcanzada: {wave}", AZUL)
    surface.blit(sub, (game_w // 2 - sub.get_width() // 2, game_h // 2 - 104))
    surface.blit(sc_text, (game_w // 2 - sc_text.get_width() // 2, game_h // 2 - 72))
    surface.blit(wt_text, (game_w // 2 - wt_text.get_width() // 2, game_h // 2 - 46))

    _dibujar_stats_partida(surface, game_w, game_h // 2 - 16, stats)

    neon.cinta(surface, "Presiona R para volver al menu", neon.ORO, (game_w // 2, game_h // 2 + 58), tam=15)
    neon.scanlines(surface)


# ------------------------------------------------ pantalla final (jefe bonus)

_ARCOIRIS_FINAL = [(255, 70, 70), (255, 160, 40), (255, 235, 60), (80, 230, 90), (60, 160, 255), (150, 90, 255)]


def dibujar_texto_arcoiris(surface, texto, fuente, cx, y, t, amplitud=6, contorno=True):
    """Texto centrado en cx con cada letra de un color del arcoiris que va
    rotando con el tiempo y saltando en ola (t en cuadros)."""
    letras = []
    ancho_total = 0
    for i, letra in enumerate(texto):
        color = pygame.Color(0)
        color.hsva = (((t * 3 + i * 28) % 360), 70, 100, 100)
        surf = fuente.render(letra, True, color)
        letras.append((surf, i))
        ancho_total += surf.get_width()
    x = cx - ancho_total // 2
    for surf, i in letras:
        dy = int(math.sin(t * 0.12 + i * 0.55) * amplitud)
        if contorno:
            sombra = fuente.render(texto[i], True, (20, 10, 40))
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (3, 3)):
                surface.blit(sombra, (x + ox, y + dy + oy))
        surface.blit(surf, (x, y + dy))
        x += surf.get_width()


def _confeti(surface, game_w, game_h, t, cantidad=70):
    """Confeti deterministico (depende solo de t): no necesita estado."""
    for i in range(cantidad):
        velocidad = 0.8 + (i * 37 % 100) / 60.0
        x = (i * 97 + int(math.sin(t * 0.02 + i) * 30)) % game_w
        y = int((t * velocidad + i * 53) % (game_h + 40)) - 20
        color = _ARCOIRIS_FINAL[i % len(_ARCOIRIS_FINAL)]
        giro = abs(math.sin(t * 0.08 + i))
        w = max(2, int(10 * giro)) // 2 * 2
        surface.fill(color, (x // 2 * 2 - w // 2, y // 2 * 2, w, 6))


def draw_victory_final(surface, game_w, game_h, score, wave, stats, texto_record, nuevo_record, t,
                       icono=None, mensaje="Derrotaste a Nyan Cat y su pandilla... y el gatito ya duerme",
                       zetas=True):
    """Pantalla de victoria de verdad (despues del Gato OIIA): mas festiva
    que draw_victory_screen -confeti, titulo arcoiris, franja estilo Nyan y
    las estadisticas en cartas neon como las de mejora-.
    icono: Surface opcional (el gatito durmiendo) para el panel.
    mensaje y zetas: la ruta de Halloween pone su propio texto y su
    calabaza sin las "Zzz"."""
    # fondo: degrade violeta -> azul noche en bandas
    fondo = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
    for yy in range(0, game_h, 8):
        k = yy / game_h
        fondo.fill((int(40 - 26 * k), int(14 + 8 * k), int(70 + 20 * k), 220), (0, yy, game_w, 8))
    surface.blit(fondo, (0, 0))
    _confeti(surface, game_w, game_h, t)

    # franja arcoiris ondulada detras del titulo
    franja_y = 58
    for i, color in enumerate(_ARCOIRIS_FINAL):
        for sx in range(0, game_w, 16):
            ondula = 4 if ((sx // 16) + t // 8) % 2 else 0
            surface.fill(color, (sx, franja_y + i * 7 + ondula, 16, 7))

    dibujar_texto_arcoiris(surface, "¡VICTORIA TOTAL!", get_font(60, bold=True), game_w // 2, 40, t)
    sub = render_texto_pixelado(get_font(20), mensaje, WHITE)
    surface.blit(sub, (game_w // 2 - sub.get_width() // 2, 132))

    # panel central con el marco que cambia de color
    card = pygame.Rect(game_w // 2 - 330, 170, 660, 330)
    borde = pygame.Color(0)
    borde.hsva = ((t * 2) % 360, 60, 100, 100)
    neon.panel(surface, card, tuple(borde)[:3], t)

    stats = stats or {}
    disparos = stats.get("disparos", 0)
    precision = int(round(100 * stats.get("aciertos", 0) / disparos)) if disparos > 0 else 0
    chips = [
        ("PUNTUACION", f"{score}", AMARILLO),
        ("OLEADA", f"{wave}", AZUL),
        ("JEFES", f"{stats.get('jefes', 0)}", ROSA),
        ("PRECISION", f"{precision}%", MENTA),
        ("TIEMPO", formatear_tiempo(stats.get("tiempo", 0)), LAVANDA),
        ("ENEMIGOS", f"{stats.get('asteroides', 0) + stats.get('alienigenas', 0)}", MELON),
    ]
    chip_w, chip_h = 190, 78
    for i, (etiqueta, valor, color) in enumerate(chips):
        col, fila = i % 3, i // 3
        cx = card.x + 30 + col * (chip_w + 10)
        cy = card.y + 28 + fila * (chip_h + 12) + int(math.sin(t * 0.06 + i) * 2)
        chip = pygame.Rect(cx, cy, chip_w, chip_h)
        surface.fill(neon.CONTORNO, chip.inflate(6, 6))
        surface.fill((34, 20, 70), chip)
        neon.marco_pixel(surface, chip, color, 3)
        neon.cinta(surface, etiqueta, color, (chip.centerx, chip.y + 14), tam=11)
        va = render_texto_pixelado(get_font(30, bold=True), valor, WHITE)
        surface.blit(va, (chip.centerx - va.get_width() // 2, cy + 32))

    # gatito durmiendo + Zzz en la parte baja del panel
    base_y = card.y + 232
    if icono is not None:
        surface.blit(icono, (card.x + 40, base_y + 6))
        for k in range(3 if zetas else 0):
            fase = (t * 0.02 + k / 3) % 1.0
            z = render_text("z" if k < 2 else "Z", 14 + k * 5, (220, 220, 255))
            z.set_alpha(int(255 * (1 - fase)))
            surface.blit(z, (card.x + 40 + icono.get_width() - 8 + k * 12, base_y - int(fase * 30) + 4))

    pulso = 0.5 + 0.5 * math.sin(t * 0.15)
    color_record = AMARILLO if nuevo_record else WHITE
    if nuevo_record:
        color_record = (255, int(200 + 55 * pulso), int(90 + 100 * pulso))
    centro_x = card.x + 250 + (card.w - 250) // 2
    if nuevo_record:
        neon.cinta(surface, "¡NUEVO RÉCORD!", neon.ORO, (centro_x, base_y + 4), tam=13)
    rec = render_texto_pixelado(get_font(22, bold=True), texto_record, color_record)
    surface.blit(rec, (centro_x - rec.get_width() // 2, base_y + 20))
    gracias = render_texto_pixelado(get_font(15), "¡Gracias por jugar!", ROSA_CHICLE)
    surface.blit(gracias, (centro_x - gracias.get_width() // 2, base_y + 56))

    # boton de salida neon con el color que rota
    color_pill = pygame.Color(0)
    color_pill.hsva = ((t * 2 + 180) % 360, 45, 100, 100)
    neon.boton(surface, (game_w // 2 - 190, card.bottom + 26, 380, 40), "ENTER / R  -  volver al menu",
               tuple(color_pill)[:3], True, t)
    neon.scanlines(surface)
