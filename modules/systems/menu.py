"""
Menu principal: fondo de estrellas, botones (JUGAR/AJUSTES/SALIR) y las
pantallas de "AJUSTES" (volumen, sensibilidad, camara) y "ELEGI LA
DIFICULTAD" que se abren desde ahi. MenuScene.state guarda cual de las tres
esta activa; ver su docstring para el detalle de cada una."""

import pygame
import random
import math
from modules.constants import WHITE, AZUL, MENTA
from modules.systems import audio
from modules.systems.fonts import render_texto_pixelado
from modules import settings
from modules.systems import sprites, pixelfx
from modules.entities.ship import TIPOS_NAVE, ORDEN_NAVES
from modules.skins import get_skin_colors


class Star:
    """Punto de fondo que titila; puramente decorativo."""
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.size = random.uniform(0.5, 2.5)
        self.twinkle_speed = random.uniform(0.02, 0.05)
        self.phase = random.uniform(0, math.pi * 2)
        self.base_alpha = random.uniform(0.3, 0.8)

    def update(self):
        self.phase += self.twinkle_speed

    def draw(self, surface):
        alpha = self.base_alpha + 0.3 * math.sin(self.phase)
        alpha = max(0.1, min(1.0, alpha))
        color = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), int(self.size))


from modules.systems.fonts import get_font


class SettingsSlider:
    """Barra horizontal arrastrable para un valor entre minimo y maximo
    (volumen 0.0-1.0, sensibilidad 0.5-2.0, etc). get_value/on_change
    desacoplan la barra de donde se guarda el valor real (modules/settings.py
    + modules/systems/audio.py). formato personaliza como se muestra el
    valor (por defecto, porcentaje)."""

    def __init__(self, x, y, width, height, label, get_value, on_change,
                 minimo=0.0, maximo=1.0, formato=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.get_value = get_value
        self.on_change = on_change
        self.minimo = minimo
        self.maximo = maximo
        self.formato = formato or (lambda v: f"{int(round((v - minimo) / (maximo - minimo) * 100))}%")
        self.dragging = False

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(0, 16).collidepoint(mouse_pos):
                self.dragging = True
                self._update_from_mouse(mouse_pos)
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        return False

    def update(self, mouse_pos, mouse_pressed):
        if self.dragging and mouse_pressed[0]:
            self._update_from_mouse(mouse_pos)
        elif self.dragging and not mouse_pressed[0]:
            self.dragging = False

    def _update_from_mouse(self, mouse_pos):
        t = (mouse_pos[0] - self.rect.x) / max(1, self.rect.width)
        t = max(0.0, min(1.0, t))
        self.on_change(self.minimo + t * (self.maximo - self.minimo))

    def draw(self, surface, color):
        r = self.rect
        rango = self.maximo - self.minimo
        valor = self.get_value()
        t = (valor - self.minimo) / rango if rango else 0.0
        t = max(0.0, min(1.0, t))

        label_surf = render_texto_pixelado(get_font(14, bold=True), f"{self.label}  {self.formato(valor)}",
                                           (215, 215, 235))
        surface.blit(label_surf, (r.x, r.y - 24))

        pygame.draw.rect(surface, (26, 26, 42), r, border_radius=r.height // 2)
        fill_w = int(r.width * t)
        if fill_w > 0:
            pygame.draw.rect(surface, color, (r.x, r.y, fill_w, r.height), border_radius=r.height // 2)
        pygame.draw.rect(surface, WHITE, r, width=1, border_radius=r.height // 2)

        knob_x = r.x + fill_w
        pygame.draw.circle(surface, (10, 10, 25), (knob_x, r.centery), r.height // 2 + 5)
        pygame.draw.circle(surface, WHITE, (knob_x, r.centery), r.height // 2 + 5, 2)


class MenuButton:
    """Boton con hover/press animado, particulas orbitando y ondas de clic
    (OrbitParticle/Ripple). Se reutiliza tanto en el menu principal como en
    las pantallas de ajustes y dificultad."""

    def __init__(self, x, y, width, height, text, font, color=None):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hovered = False
        self.pressed = False
        self.press_scale = 1.0
        self.target_scale = 1.0
        self.glow_phase = 0
        self.gradient_offset = 0
        self.particles = []
        self.ripples = []
        self.enabled = True
        self.pulse_phase = 0

        for _ in range(10):
            self.particles.append(OrbitParticle(
                self.rect.centerx,
                self.rect.centery,
                max(width, height) * 0.75
            ))

    def update(self, mouse_pos, mouse_pressed):
        if not self.enabled:
            self.target_scale = 1.0
            self.hovered = False
            self.pressed = False
        else:
            self.hovered = self.rect.collidepoint(mouse_pos)
            self.pressed = self.hovered and mouse_pressed[0]
            self.target_scale = 0.95 if self.pressed else (1.05 if self.hovered else 1.0)

        self.press_scale += (self.target_scale - self.press_scale) * 0.2
        self.glow_phase += 0.08
        self.gradient_offset = (self.gradient_offset + 0.5) % 400
        self.pulse_phase += 0.04

        for p in self.particles:
            p.update(self.hovered and self.enabled, self.rect.centerx, self.rect.centery)

        self.ripples = [r for r in self.ripples if r.active]
        for r in self.ripples:
            r.update()

    def handle_event(self, event):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                self._spawn_ripple(event.pos)
                audio.sonido_boton()
                return True
        return False

    def _spawn_ripple(self, pos):
        max_radius = max(self.rect.width, self.rect.height) * 1.5
        self.ripples.append(Ripple(pos[0], pos[1], max_radius, AZUL))

    def draw(self, surface, extra_offset=0, marcado=False):
        """marcado: elegido con flechas / mando (brilla como en hover)."""
        if not self.enabled:
            alpha_factor = 0.4
        else:
            alpha_factor = 1.0

        cx, cy = self.rect.center
        w, h = self.rect.width, self.rect.height
        scale = self.press_scale
        draw_w = int(w * scale)
        draw_h = int(h * scale)
        draw_x = cx - draw_w // 2 + extra_offset
        draw_y = cy - draw_h // 2

        shadow_surf = pygame.Surface((draw_w + 8, draw_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60), (4, 4, draw_w, draw_h), border_radius=draw_h // 2)
        surface.blit(shadow_surf, (draw_x, draw_y))

        btn_surf = pygame.Surface((draw_w, draw_h), pygame.SRCALPHA)

        bg_grad = pygame.Surface((draw_w, draw_h), pygame.SRCALPHA)
        offset = int(self.gradient_offset) % draw_w
        base_c = self.color or AZUL
        for x_pos in range(draw_w):
            t = (x_pos + offset) / draw_w
            r = int(base_c[0] * (0.08 + 0.07 * math.sin(t * math.pi * 2)))
            g = int(base_c[1] * (0.08 + 0.07 * math.sin(t * math.pi * 2)))
            b = int(base_c[2] * (0.08 + 0.07 * math.sin(t * math.pi * 2)))
            pygame.draw.line(bg_grad, (r, g, b, int(alpha_factor * 255)), (x_pos, 0), (x_pos, draw_h))
        pygame.draw.rect(bg_grad, (0, 0, 0, 0), (0, 0, draw_w, draw_h), border_radius=draw_h // 2)
        btn_surf.blit(bg_grad, (0, 0))

        pulse = 0.5 + 0.5 * math.sin(self.pulse_phase)
        glow_intensity = int(20 + 15 * pulse) if not (self.hovered or marcado) else int(40 + 20 * pulse)
        glow_surf = pygame.Surface((draw_w + 20, draw_h + 20), pygame.SRCALPHA)
        for i in range(4):
            ga = max(0, glow_intensity - i * 8)
            pygame.draw.rect(
                glow_surf,
                (*base_c[:3], int(ga * alpha_factor)),
                (10 - i * 5, 10 - i * 5, draw_w + i * 10, draw_h + i * 10),
                border_radius=draw_h // 2 + i * 2
            )
        surface.blit(glow_surf, (draw_x - 10, draw_y - 10))

        if marcado and self.enabled:
            # marco del color del boton, bien visible
            pygame.draw.rect(surface, base_c[:3], (draw_x - 4, draw_y - 4, draw_w + 8, draw_h + 8),
                             width=3, border_radius=draw_h // 2 + 4)

        border_color = (
            int(255 * alpha_factor),
            int(255 * alpha_factor),
            int(255 * alpha_factor),
            int(200 * alpha_factor)
        )
        pygame.draw.rect(btn_surf, border_color, (0, 0, draw_w, draw_h), width=2, border_radius=draw_h // 2)

        highlight_h = max(1, draw_h // 3)
        hl_surf = pygame.Surface((draw_w, highlight_h), pygame.SRCALPHA)
        for row in range(highlight_h):
            a = int(40 * (1 - row / highlight_h) * alpha_factor)
            pygame.draw.line(hl_surf, (255, 255, 255, a), (0, row), (draw_w - 1, row))
        btn_surf.blit(hl_surf, (0, 0))

        max_texto_w = draw_w - 20  # margen para que el texto no toque los bordes redondeados
        text_surf = render_texto_pixelado(self.font, self.text, WHITE, ancho_maximo=max_texto_w)
        text_rect = text_surf.get_rect(center=(draw_w // 2, draw_h // 2))
        btn_surf.blit(text_surf, text_rect)

        surface.blit(btn_surf, (draw_x, draw_y))

        for r in self.ripples:
            r.draw(surface)

        for p in self.particles:
            p.draw(surface)


class OrbitParticle:
    """Punto que orbita alrededor de un MenuButton; gira mas rapido y brilla
    mas fuerte mientras el boton esta en hover."""

    def __init__(self, center_x, center_y, base_radius):
        self.center_x = center_x
        self.center_y = center_y
        self.angle = random.uniform(0, math.pi * 2)
        self.base_radius = base_radius
        self.radius = base_radius + random.uniform(-10, 10)
        self.speed = random.uniform(0.015, 0.035)
        self.size = random.uniform(1.5, 3.5)
        self.base_alpha = random.uniform(0.4, 0.9)
        self.alpha = self.base_alpha

    def update(self, is_hovering, center_x, center_y):
        self.center_x = center_x
        self.center_y = center_y
        self.angle += self.speed * (2.5 if is_hovering else 1.0)
        self.alpha = self.base_alpha * (1.5 if is_hovering else 1.0)

    def draw(self, surface):
        x = self.center_x + math.cos(self.angle) * self.radius
        y = self.center_y + math.sin(self.angle) * self.radius
        alpha = max(0, min(255, int(self.alpha * 255)))
        color = (*AZUL[:3], alpha)
        particle_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surf, color, (self.size, self.size), self.size)
        surface.blit(particle_surf, (x - self.size, y - self.size))


class Ripple:
    """Onda expansiva que se dispara al hacer clic en un MenuButton; crece
    hasta max_radius y se desvanece, luego active pasa a False."""

    def __init__(self, x, y, max_radius, color=AZUL):
        self.x = x
        self.y = y
        self.radius = 0
        self.max_radius = max_radius
        self.color = color
        self.alpha = 180
        self.active = True
        self.speed = 8

    def update(self):
        self.radius += self.speed
        self.alpha = max(0, 180 * (1 - self.radius / self.max_radius))
        if self.radius >= self.max_radius:
            self.active = False

    def draw(self, surface):
        if not self.active:
            return
        ripple_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            ripple_surf,
            (*self.color[:3], int(self.alpha)),
            (self.radius, self.radius),
            self.radius,
            width=3
        )
        surface.blit(ripple_surf, (self.x - self.radius, self.y - self.radius))


# Puntos de partida de "ELEGIR FASE": (id que entiende main.py, etiqueta,
# es_bonus). "wN" arranca en la oleada N; "nyan"/"alien"/"pan" van directo
# a ese jefe del bonus secreto.
FASES_INICIO = (
    ("w1", "OLEADA 1 - INICIO", False),
    ("w10", "OLEADA 10 - CENTINELA", False),
    ("w20", "OLEADA 20 - DRAGON", False),
    ("w25", "OLEADA 25 - ZORRITO", False),
    ("w30", "OLEADA 30 - TITAN", False),
    ("w40", "OLEADA 40 - ANOMALIA", False),
    ("w50", "OLEADA 50 - MEGA JEFE", False),
    ("nyan", "BONUS - NYAN CAT", True),
    ("alien", "BONUS - GATO ALIEN", True),
    ("pan", "BONUS - GATO OIIA", True),
)


class MenuScene:
    """Pantalla de menu completa. self.state controla que se dibuja/procesa:

    - "main": los 4 botones (JUGAR, ELEGIR FASE, AJUSTES, SALIR).
    - "fases": se entra con ELEGIR FASE; lista de puntos de partida (ver
      FASES_INICIO). Elegido uno sigue el camino de JUGAR (modo de control
      -> dificultad) y START_GAME lleva ":<id de la fase>" al final, mas
      ":buffs" si esta prendido "TODOS LOS BUFFS" (boton o tecla T).
    - "control_mode": se entra al elegir JUGAR; CAMARA (gestos de mano) o
      MANDO (joystick). MANDO se deshabilita si no hay ningun mando
      conectado. La eleccion queda en self.modo_control ("camara"/"mando").
    - "dificultad": se entra tras elegir el modo de control (FACIL/NORMAL/
      DIFICIL) y lleva a "nave".
    - "nave": cuatro cartas con las naves de TIPOS_NAVE (ship.py); la
      elegida devuelve "START_GAME:<nave>:<skin>:<dificultad>:<modo_control>"
      que main.py interpreta para arrancar la partida.
    - "settings": volumen de musica/efectos, sensibilidad de mano y camara
      (modules/settings.py los persiste en ajustes.json); pantalla completa
      y cambio de camara se resuelven en main.py via los resultados
      "TOGGLE_FULLSCREEN"/"CHANGE_CAMERA" que devuelve handle_event().
      Ademas "JUGAR NIVEL BONUS" lleva por el mismo camino que JUGAR
      (modo de control -> dificultad) pero agrega ":bonus" al START_GAME,
      y main.py arranca directo en la pelea contra Nyan Cat.

    handle_event() devuelve None salvo que haya que avisarle algo a main.py
    (arrancar partida, salir, o esas dos señales de ajustes)."""

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        self.active = True
        self.transition_alpha = 255
        self.transitioning_out = False
        self.title_phase = 0

        self.title_font = get_font(52, bold=True)
        self.subtitle_font = get_font(18)
        self.button_font = get_font(24, bold=True)

        self.stars = [Star(screen_width, screen_height) for _ in range(120)]

        btn_w, btn_h = 260, 56
        gap = 20
        total_h = 4 * btn_h + 3 * gap
        start_y = screen_height // 2 - total_h // 2 + btn_h // 2
        cx = screen_width // 2
        self.buttons = [
            MenuButton(cx, start_y, btn_w, btn_h, "JUGAR", self.button_font, (30, 200, 120)),
            MenuButton(cx, start_y + btn_h + gap, btn_w, btn_h, "ELEGIR FASE", self.button_font, (120, 140, 255)),
            MenuButton(cx, start_y + 2 * (btn_h + gap), btn_w, btn_h, "AJUSTES", self.button_font, (200, 180, 60)),
            MenuButton(cx, start_y + 3 * (btn_h + gap), btn_w, btn_h, "SALIR", self.button_font, (220, 80, 80)),
        ]

        # ELEGIR FASE: grilla de 2 columnas x 5 filas + VOLVER
        fase_font = get_font(17, bold=True)
        self.fase_botones = []
        for i, (_, etiqueta, es_bonus) in enumerate(FASES_INICIO):
            col, fila = i // 5, i % 5
            color = (255, 110, 200) if es_bonus else (100, 150, 255)
            self.fase_botones.append(MenuButton(cx - 200 + col * 400, 190 + fila * 66, 360, 50, etiqueta, fase_font, color))
        self.btn_fases_buffs = MenuButton(cx, 522, 340, 44, "TODOS LOS BUFFS: NO", get_font(16, bold=True), (255, 200, 90))
        self.btn_fases_volver = MenuButton(cx, 582, 200, 44, "VOLVER", get_font(16, bold=True), (90, 90, 115))
        self.fase_seleccionada = 0
        # id de FASES_INICIO elegido (None = partida normal desde JUGAR)
        self.inicio_elegido = None
        self.selected = 0
        self.hover_amp = 0
        self.state = "main"

        slider_w = 380
        slider_h = 18
        self.slider_musica = SettingsSlider(
            cx - slider_w // 2, 165, slider_w, slider_h, "MUSICA",
            lambda: settings.get("volumen_musica"), self._cambiar_volumen_musica,
        )
        self.slider_sfx = SettingsSlider(
            cx - slider_w // 2, 225, slider_w, slider_h, "EFECTOS",
            lambda: settings.get("volumen_sfx"), self._cambiar_volumen_sfx,
        )
        self.slider_sensibilidad = SettingsSlider(
            cx - slider_w // 2, 285, slider_w, slider_h, "SENSIBILIDAD",
            lambda: settings.get("sensibilidad_mano"), self._cambiar_sensibilidad,
            minimo=0.5, maximo=2.0, formato=lambda v: f"{v:.1f}x",
        )
        toggle_font = get_font(16, bold=True)
        self.btn_silencio = MenuButton(cx, 345, 300, 44, "SILENCIO: NO", toggle_font, (150, 150, 175))
        self.btn_pantalla = MenuButton(cx, 397, 300, 44, "PANTALLA COMPLETA: SI", toggle_font, (150, 150, 175))
        self.btn_camara = MenuButton(cx, 449, 300, 44, "CAMARA: 0", toggle_font, (150, 150, 175))
        self.btn_bonus_buffs = MenuButton(cx, 507, 340, 44, "BONUS CON TODOS LOS BUFFS: NO", toggle_font, (255, 110, 200))
        self.btn_bonus = MenuButton(cx, 559, 300, 44, "JUGAR NIVEL BONUS", toggle_font, (255, 110, 200))
        self.btn_volver = MenuButton(cx, 619, 200, 44, "VOLVER", toggle_font, (90, 90, 115))
        self.settings_widgets = [self.slider_musica, self.slider_sfx, self.slider_sensibilidad,
                                 self.btn_silencio, self.btn_pantalla, self.btn_camara,
                                 self.btn_bonus_buffs, self.btn_bonus, self.btn_volver]
        # True cuando se entro al flujo de partida desde "JUGAR NIVEL BONUS"
        self.partida_bonus = False
        # widget de AJUSTES marcado con flechas / mando
        self.ajuste_sel = 0
        # main.py lo pone en True cuando lo ultimo que se toco fue el mando
        # (cambia los textos de ayuda y preselecciona MANDO al elegir control)
        self.usando_mando = False

        dif_btn_w, dif_btn_h, dif_gap = 240, 56, 24
        dif_total_h = 3 * dif_btn_h + 2 * dif_gap
        dif_start_y = screen_height // 2 - dif_total_h // 2
        self.dificultad_ids = ["facil", "normal", "dificil"]
        self.dificultad_botones = [
            MenuButton(cx, dif_start_y, dif_btn_w, dif_btn_h, "FACIL", self.button_font, (60, 200, 120)),
            MenuButton(cx, dif_start_y + dif_btn_h + dif_gap, dif_btn_w, dif_btn_h, "NORMAL", self.button_font, (200, 180, 60)),
            MenuButton(cx, dif_start_y + 2 * (dif_btn_h + dif_gap), dif_btn_w, dif_btn_h, "DIFICIL", self.button_font, (220, 80, 80)),
        ]
        self.dificultad_seleccionada = 1

        cm_btn_w, cm_btn_h, cm_gap = 260, 56, 24
        cm_total_h = 2 * cm_btn_h + cm_gap
        cm_start_y = screen_height // 2 - cm_total_h // 2
        self.control_mode_ids = ["camara", "mando"]
        self.control_mode_botones = [
            MenuButton(cx, cm_start_y, cm_btn_w, cm_btn_h, "CAMARA (MANO)", self.button_font, (60, 200, 120)),
            MenuButton(cx, cm_start_y + cm_btn_h + cm_gap, cm_btn_w, cm_btn_h, "MANDO (JOYSTICK)", self.button_font, (80, 140, 220)),
        ]
        self.control_mode_seleccionada = 0
        self.modo_control = "camara"

        # ELEGI TU NAVE: cuatro cartas; la eleccion se recuerda entre partidas
        self.nave_seleccionada = 0
        self.dificultad_elegida = "normal"
        self.nave_t = 0

    def _ayuda(self, teclado, mando):
        return mando if self.usando_mando else teclado

    def _dibujar_ayuda(self, teclado, mando, y=None):
        hint = render_texto_pixelado(get_font(13), self._ayuda(teclado, mando), (160, 160, 185))
        y = self.screen_height - 50 if y is None else y
        self.surface.blit(hint, hint.get_rect(center=(self.screen_width // 2, y)))

    def _ir_a_modo_control(self):
        """Pantalla ELEGI COMO JUGAR; si se viene usando el mando ya queda
        marcado MANDO."""
        self.state = "control_mode"
        hay_mando = pygame.joystick.get_count() > 0
        self.control_mode_seleccionada = 1 if (self.usando_mando and hay_mando) else 0

    def _cambiar_volumen_musica(self, valor):
        audio.set_volumen_musica(valor)
        settings.set_valor("volumen_musica", valor)

    def _cambiar_volumen_sfx(self, valor):
        audio.set_volumen_sfx(valor)
        settings.set_valor("volumen_sfx", valor)

    def _cambiar_sensibilidad(self, valor):
        settings.set_valor("sensibilidad_mano", valor)

    def update(self, mouse_pos, mouse_pressed):
        if self.transitioning_out:
            self.transition_alpha = max(0, self.transition_alpha - 8)
            if self.transition_alpha <= 0:
                self.active = False

        for star in self.stars:
            star.update()

        if self.transitioning_out:
            return

        if self.state == "settings":
            self.slider_musica.update(mouse_pos, mouse_pressed)
            self.slider_sfx.update(mouse_pos, mouse_pressed)
            self.slider_sensibilidad.update(mouse_pos, mouse_pressed)
            self.btn_silencio.update(mouse_pos, mouse_pressed)
            self.btn_pantalla.update(mouse_pos, mouse_pressed)
            self.btn_camara.update(mouse_pos, mouse_pressed)
            self.btn_bonus_buffs.update(mouse_pos, mouse_pressed)
            self.btn_bonus.update(mouse_pos, mouse_pressed)
            self.btn_volver.update(mouse_pos, mouse_pressed)
            for i, w in enumerate(self.settings_widgets):
                if isinstance(w, MenuButton) and w.hovered:
                    self.ajuste_sel = i
            self.hover_amp += 0.12
            self.title_phase += 0.025
            return

        if self.state == "control_mode":
            self.control_mode_botones[1].enabled = pygame.joystick.get_count() > 0
            for btn in self.control_mode_botones:
                btn.update(mouse_pos, mouse_pressed)
            self.hover_amp += 0.12
            self.title_phase += 0.025
            return

        if self.state == "dificultad":
            for btn in self.dificultad_botones:
                btn.update(mouse_pos, mouse_pressed)
            self.hover_amp += 0.12
            self.title_phase += 0.025
            return

        if self.state == "nave":
            self.nave_t += 1
            for i in range(len(ORDEN_NAVES)):
                if self._rect_nave(i).collidepoint(mouse_pos):
                    self.nave_seleccionada = i
            self.title_phase += 0.025
            return

        if self.state == "fases":
            for i, btn in enumerate(self.fase_botones):
                btn.update(mouse_pos, mouse_pressed)
                if btn.hovered:
                    self.fase_seleccionada = i
            self.btn_fases_buffs.update(mouse_pos, mouse_pressed)
            self.btn_fases_volver.update(mouse_pos, mouse_pressed)
            self.hover_amp += 0.12
            self.title_phase += 0.025
            return

        prev = self.selected
        for i, btn in enumerate(self.buttons):
            btn.update(mouse_pos, mouse_pressed)
            if btn.hovered:
                self.selected = i
        if self.selected != prev:
            self.hover_amp = 0.0
        self.hover_amp += 0.12
        self.title_phase += 0.025

    def handle_event(self, event):
        if not self.active or self.transitioning_out:
            return None

        if self.state == "settings":
            return self._handle_settings_event(event)
        if self.state == "control_mode":
            return self._handle_control_mode_event(event)
        if self.state == "dificultad":
            return self._handle_dificultad_event(event)
        if self.state == "nave":
            return self._handle_nave_event(event)
        if self.state == "fases":
            return self._handle_fases_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = max(0, self.selected - 1)
                self.hover_amp = 0.0
                return None
            if event.key == pygame.K_DOWN:
                self.selected = min(len(self.buttons) - 1, self.selected + 1)
                self.hover_amp = 0.0
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                audio.sonido_boton()
                return self._trigger_selected()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self.buttons):
                if btn.handle_event(event):  # ya reproduce el sonido y el ripple
                    self.selected = i
                    return self._trigger_selected()
        return None

    def _handle_settings_event(self, event):
        mouse_pos = event.pos if hasattr(event, 'pos') else pygame.mouse.get_pos()
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.exit_settings()
                audio.sonido_boton()
                return None
            total = len(self.settings_widgets)
            widget = self.settings_widgets[self.ajuste_sel]
            if event.key == pygame.K_UP:
                self.ajuste_sel = (self.ajuste_sel - 1) % total
                self.hover_amp = 0.0
                return None
            if event.key == pygame.K_DOWN:
                self.ajuste_sel = (self.ajuste_sel + 1) % total
                self.hover_amp = 0.0
                return None
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT) and isinstance(widget, SettingsSlider):
                paso = (widget.maximo - widget.minimo) * 0.05 * (1 if event.key == pygame.K_RIGHT else -1)
                widget.on_change(max(widget.minimo, min(widget.maximo, widget.get_value() + paso)))
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and isinstance(widget, MenuButton):
                audio.sonido_boton()
                return self._activar_ajuste(widget)
            return None
        if self.slider_musica.handle_event(event, mouse_pos):
            return None
        if self.slider_sfx.handle_event(event, mouse_pos):
            return None
        if self.slider_sensibilidad.handle_event(event, mouse_pos):
            return None
        for widget in self.settings_widgets:
            if isinstance(widget, MenuButton) and widget.handle_event(event):
                return self._activar_ajuste(widget)
        return None

    def _activar_ajuste(self, widget):
        if widget is self.btn_silencio:
            silenciado = audio.alternar_silencio()
            settings.set_valor("silenciado", silenciado)
            return None
        if widget is self.btn_pantalla:
            nueva = not settings.get("pantalla_completa")
            settings.set_valor("pantalla_completa", nueva)
            return "TOGGLE_FULLSCREEN"
        if widget is self.btn_camara:
            nuevo_indice = (settings.get("camera_index") + 1) % 4
            settings.set_valor("camera_index", nuevo_indice)
            return "CHANGE_CAMERA"
        if widget is self.btn_bonus_buffs:
            settings.set_valor("bonus_todos_buffs", not settings.get("bonus_todos_buffs"))
            return None
        if widget is self.btn_bonus:
            self.partida_bonus = True
            self._ir_a_modo_control()
            return None
        if widget is self.btn_volver:
            self.exit_settings()
        return None

    def _handle_control_mode_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.state = "main"
                audio.sonido_boton()
                return None
            if event.key == pygame.K_UP:
                self.control_mode_seleccionada = max(0, self.control_mode_seleccionada - 1)
                return None
            if event.key == pygame.K_DOWN:
                self.control_mode_seleccionada = min(len(self.control_mode_botones) - 1, self.control_mode_seleccionada + 1)
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._elegir_modo_control(self.control_mode_seleccionada)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self.control_mode_botones):
                if btn.handle_event(event):
                    self.control_mode_seleccionada = i
                    return self._elegir_modo_control(i)
        return None

    def _handle_fases_event(self, event):
        total = len(self.fase_botones)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.state = "main"
                audio.sonido_boton()
                return None
            if event.key == pygame.K_UP:
                self.fase_seleccionada = (self.fase_seleccionada - 1) % total
            elif event.key == pygame.K_DOWN:
                self.fase_seleccionada = (self.fase_seleccionada + 1) % total
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.fase_seleccionada = (self.fase_seleccionada + 5) % total
            elif event.key == pygame.K_t:
                self._alternar_buffs_fase()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                audio.sonido_boton()
                return self._elegir_fase(self.fase_seleccionada)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self.fase_botones):
                if btn.handle_event(event):
                    self.fase_seleccionada = i
                    return self._elegir_fase(i)
            if self.btn_fases_buffs.handle_event(event):
                self._alternar_buffs_fase()
                return None
            if self.btn_fases_volver.handle_event(event):
                self.state = "main"
        return None

    def _alternar_buffs_fase(self):
        settings.set_valor("fase_todos_buffs", not settings.get("fase_todos_buffs"))
        audio.sonido_boton()

    def _elegir_fase(self, indice):
        self.inicio_elegido = FASES_INICIO[indice][0]
        self.partida_bonus = False
        self._ir_a_modo_control()
        return None

    def _etiqueta_inicio(self):
        for fase_id, etiqueta, _ in FASES_INICIO:
            if fase_id == self.inicio_elegido:
                return etiqueta
        return None

    def _elegir_modo_control(self, indice):
        if not self.control_mode_botones[indice].enabled:
            return None
        self.modo_control = self.control_mode_ids[indice]
        self.state = "dificultad"
        self.dificultad_seleccionada = 1
        audio.sonido_boton()
        return None

    def _handle_dificultad_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.state = "control_mode"
                audio.sonido_boton()
                return None
            if event.key == pygame.K_UP:
                self.dificultad_seleccionada = max(0, self.dificultad_seleccionada - 1)
                return None
            if event.key == pygame.K_DOWN:
                self.dificultad_seleccionada = min(len(self.dificultad_botones) - 1, self.dificultad_seleccionada + 1)
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._elegir_dificultad(self.dificultad_seleccionada)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self.dificultad_botones):
                if btn.handle_event(event):
                    self.dificultad_seleccionada = i
                    return self._elegir_dificultad(i)
        return None

    def _elegir_dificultad(self, indice):
        self.dificultad_elegida = self.dificultad_ids[indice]
        self.state = "nave"
        self.nave_t = 0
        audio.sonido_boton()
        return None

    def _rect_nave(self, i):
        ancho, alto, gap = 250, 400, 26
        total = len(ORDEN_NAVES) * ancho + (len(ORDEN_NAVES) - 1) * gap
        x0 = self.screen_width // 2 - total // 2
        return pygame.Rect(x0 + i * (ancho + gap), 150, ancho, alto)

    def _handle_nave_event(self, event):
        n = len(ORDEN_NAVES)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.state = "dificultad"
                audio.sonido_boton()
                return None
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.nave_seleccionada = (self.nave_seleccionada - 1) % n
                audio.sonido_boton()
                return None
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self.nave_seleccionada = (self.nave_seleccionada + 1) % n
                audio.sonido_boton()
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._iniciar_partida(self.dificultad_elegida)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(n):
                if self._rect_nave(i).collidepoint(event.pos):
                    self.nave_seleccionada = i
                    return self._iniciar_partida(self.dificultad_elegida)
        return None

    def _iniciar_partida(self, dificultad_id):
        self.transitioning_out = True
        audio.sonido_boton()
        if self.partida_bonus:
            sufijo = ":bonus"
        elif self.inicio_elegido:
            sufijo = f":{self.inicio_elegido}"
            if settings.get("fase_todos_buffs"):
                sufijo += ":buffs"
        else:
            sufijo = ""
        nave = ORDEN_NAVES[self.nave_seleccionada]
        return f"START_GAME:{nave}:default:{dificultad_id}:{self.modo_control}{sufijo}"

    def _trigger_selected(self):
        label = self.buttons[self.selected].text
        if label == "JUGAR":
            self.partida_bonus = False
            self.inicio_elegido = None
            self._ir_a_modo_control()
            return None
        if label == "ELEGIR FASE":
            self.state = "fases"
            return None
        if label == "AJUSTES":
            self.state = "settings"
            self.ajuste_sel = 0
            return None
        if label == "SALIR":
            return "QUIT"
        return None

    def exit_settings(self):
        self.state = "main"
        self.selected = 0

    def draw(self, surface):
        self.surface.fill((0, 0, 0, 0))

        for star in self.stars:
            star.draw(self.surface)

        title_surf = render_texto_pixelado(self.title_font, "NAVE VS ASTEROIDES", WHITE)
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 56))
        float_y = math.sin(self.title_phase) * 6
        glow_alpha = int(80 + 40 * math.sin(self.title_phase * 0.7))
        glow_surf = pygame.Surface(
            (title_rect.width + 48, title_rect.height + 48), pygame.SRCALPHA
        )
        for i in range(6):
            offset = i * 4
            pygame.draw.rect(
                glow_surf,
                (*AZUL[:3], max(0, glow_alpha - i * 12)),
                (24 - offset, 24 - offset,
                 title_rect.width + offset * 2,
                 title_rect.height + offset * 2),
                border_radius=10,
            )
        self.surface.blit(
            glow_surf,
            (title_rect.x - 24, title_rect.y - 24 + int(float_y)),
        )
        self.surface.blit(title_surf, (title_rect.x, title_rect.y + int(float_y)))

        if self.state == "settings":
            sub = render_texto_pixelado(self.subtitle_font, "AJUSTES", (200, 200, 220))
            self.surface.blit(sub, sub.get_rect(center=(self.screen_width // 2, 106)))
            self._draw_settings()
            surface.blit(self.surface, (0, 0))
            return

        if self.state == "control_mode":
            titulo = "NIVEL BONUS: ELEGI COMO JUGAR" if self.partida_bonus else "ELEGI COMO JUGAR"
            if self._etiqueta_inicio():
                titulo = f"{self._etiqueta_inicio()}: ELEGI COMO JUGAR"
            sub = render_texto_pixelado(self.subtitle_font, titulo, (200, 200, 220))
            self.surface.blit(sub, sub.get_rect(center=(self.screen_width // 2, 106)))
            for i, btn in enumerate(self.control_mode_botones):
                extra = int(math.sin(self.hover_amp * 1.0) * 8) if i == self.control_mode_seleccionada else 0
                btn.draw(self.surface, extra_offset=extra, marcado=i == self.control_mode_seleccionada)
            if not self.control_mode_botones[1].enabled:
                aviso = render_texto_pixelado(get_font(13), "Conecta un mando para habilitar esta opcion", (220, 140, 140))
                self.surface.blit(aviso, aviso.get_rect(center=(self.screen_width // 2, self.screen_height - 80)))
            self._dibujar_ayuda("Flechas para moverte - ENTER para elegir - ESC para volver",
                                "Palanca o cruceta para moverte - A para elegir - B para volver")
            surface.blit(self.surface, (0, 0))
            return

        if self.state == "dificultad":
            titulo = "NIVEL BONUS: ELEGI LA DIFICULTAD" if self.partida_bonus else "ELEGI LA DIFICULTAD"
            if self._etiqueta_inicio():
                titulo = f"{self._etiqueta_inicio()}: ELEGI LA DIFICULTAD"
            sub = render_texto_pixelado(self.subtitle_font, titulo, (200, 200, 220))
            self.surface.blit(sub, sub.get_rect(center=(self.screen_width // 2, 106)))
            for i, btn in enumerate(self.dificultad_botones):
                extra = int(math.sin(self.hover_amp * 1.0) * 8) if i == self.dificultad_seleccionada else 0
                btn.draw(self.surface, extra_offset=extra, marcado=i == self.dificultad_seleccionada)
            self._dibujar_ayuda("Flechas para moverte - ENTER para elegir - ESC para volver",
                                "Palanca o cruceta para moverte - A para elegir - B para volver")
            surface.blit(self.surface, (0, 0))
            return

        if self.state == "nave":
            sub = render_texto_pixelado(self.subtitle_font, "ELEGI TU NAVE", (200, 200, 220))
            self.surface.blit(sub, sub.get_rect(center=(self.screen_width // 2, 106)))
            for i in range(len(ORDEN_NAVES)):
                if i != self.nave_seleccionada:
                    self._dibujar_carta_nave(i)
            self._dibujar_carta_nave(self.nave_seleccionada)
            self._dibujar_ayuda("Flechas para moverte - ENTER para despegar - ESC para volver",
                                "Palanca o cruceta para moverte - A para despegar - B para volver")
            self._dibujar_transicion()
            surface.blit(self.surface, (0, 0))
            return

        if self.state == "fases":
            sub = render_texto_pixelado(self.subtitle_font, "ELEGI EN QUE FASE EMPEZAR", (200, 200, 220))
            self.surface.blit(sub, sub.get_rect(center=(self.screen_width // 2, 106)))
            for i, btn in enumerate(self.fase_botones):
                extra = int(math.sin(self.hover_amp * 1.0) * 6) if i == self.fase_seleccionada else 0
                btn.draw(self.surface, extra_offset=extra, marcado=i == self.fase_seleccionada)
            self.btn_fases_buffs.text = f"TODOS LOS BUFFS: {'SI' if settings.get('fase_todos_buffs') else 'NO'}"
            self.btn_fases_buffs.draw(self.surface)
            self.btn_fases_volver.draw(self.surface)
            self._dibujar_ayuda("Flechas para moverte - ENTER para elegir - T = todos los buffs - ESC para volver",
                                "Palanca o cruceta para moverte - A para elegir - Y = todos los buffs - B para volver")
            surface.blit(self.surface, (0, 0))
            return

        sub = render_texto_pixelado(self.subtitle_font, "CONTROL POR GESTOS DE MANO", (200, 200, 220))
        self.surface.blit(
            sub, sub.get_rect(center=(self.screen_width // 2, 106))
        )

        for i, btn in enumerate(self.buttons):
            extra = 0
            if i == self.selected:
                extra = int(math.sin(self.hover_amp * 1.0) * 8)
            btn.draw(self.surface, extra_offset=extra, marcado=i == self.selected)
        self._dibujar_ayuda("Flechas para moverte - ENTER para elegir",
                            "Palanca o cruceta para moverte - A para elegir")

        self._dibujar_transicion()
        surface.blit(self.surface, (0, 0))

    def _dibujar_transicion(self):
        if self.transitioning_out or self.transition_alpha < 255:
            overlay = pygame.Surface(
                (self.screen_width, self.screen_height), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, max(0, 255 - self.transition_alpha)))
            self.surface.blit(overlay, (0, 0))

    def _dibujar_carta_nave(self, i):
        """Carta de una nave: sprite grande con su llama, nombre, barras de
        VELOCIDAD/CADENCIA/VIDAS en bloques y el rasgo propio."""
        tipo = ORDEN_NAVES[i]
        datos = TIPOS_NAVE[tipo]
        marcada = i == self.nave_seleccionada
        t = self.nave_t
        rect = self._rect_nave(i)
        entrada = max(0.0, min(1.0, (t - i * 5) / 18))
        rect.y += int((1 - (1 - (1 - entrada) ** 3)) * 300)
        if marcada:
            rect.y -= 12 + int(math.sin(t * 0.12) * 3)
        neon = (90, 220, 255) if not marcada else (255, 120, 230)
        borde = neon if marcada else (70, 110, 170)

        if marcada:
            pixelfx.dibujar_halo(self.surface, neon, rect.centerx, rect.centery, int(rect.w * 0.62))
        self.surface.fill(pixelfx.CONTORNO, rect.inflate(8, 8))
        self.surface.fill((20, 12, 48), rect)
        for y in range(rect.y + 6, rect.bottom - 4, 6):
            self.surface.fill((27, 17, 60), (rect.x + 6, y, rect.w - 12, 2))
        p = 4
        x, y, w, h = rect
        for caja in ((x + 2 * p, y, w - 4 * p, p), (x + 2 * p, y + h - p, w - 4 * p, p),
                     (x, y + 2 * p, p, h - 4 * p), (x + w - p, y + 2 * p, p, h - 4 * p),
                     (x + p, y + p, p, p), (x + w - 2 * p, y + p, p, p),
                     (x + p, y + h - 2 * p, p, p), (x + w - 2 * p, y + h - 2 * p, p, p)):
            self.surface.fill(borde, caja)

        # nave con llama
        cuerpo, ala, glow, _ = get_skin_colors("scout", "default")
        sw, sh = sprites.get_ship_size(tipo, 40, 32)
        escala = 2
        nave = sprites.get_ship_surface(tipo, cuerpo, ala, sw * escala, sh * escala)
        ncx = rect.centerx
        ncy = rect.y + 110 + int(math.sin(t * 0.08 + i) * 4)
        pixelfx.dibujar_halo(self.surface, glow, ncx, ncy, 70 if marcada else 52)
        self.surface.blit(nave, nave.get_rect(center=(ncx, ncy)))

        nombre = render_texto_pixelado(get_font(22, bold=True), datos["nombre"], WHITE if marcada else (200, 205, 230))
        self.surface.blit(nombre, nombre.get_rect(center=(rect.centerx, rect.y + 206)))

        stats = (
            ("VELOCIDAD", (datos["speed"] - 0.10) / 0.14, (120, 255, 190)),
            ("CADENCIA", (30 - datos["shoot_delay"]) / 15, (255, 220, 110)),
            ("VIDAS", datos["max_lives"] / 7, (255, 120, 150)),
        )
        fuente = get_font(12, bold=True)
        for k, (etiqueta, valor, color) in enumerate(stats):
            yy = rect.y + 238 + k * 30
            lab = fuente.render(etiqueta, True, (170, 175, 210))
            self.surface.blit(lab, (rect.x + 18, yy))
            llenos = max(1, min(7, int(round(valor * 7))))
            for n in range(7):
                caja = (rect.x + 112 + n * 17, yy + 1, 13, 12)
                self.surface.fill(pixelfx.CONTORNO, pygame.Rect(caja).inflate(2, 2))
                self.surface.fill(color if n < llenos else (45, 34, 84), caja)

        rasgo_font = get_font(14)
        palabras, lineas, actual = datos["rasgo"].split(), [], ""
        for palabra in palabras:
            prueba = f"{actual} {palabra}".strip()
            if rasgo_font.size(prueba)[0] > rect.w - 30 and actual:
                lineas.append(actual)
                actual = palabra
            else:
                actual = prueba
        lineas.append(actual)
        for k, linea in enumerate(lineas):
            s = rasgo_font.render(linea, True, neon if marcada else (150, 190, 230))
            self.surface.blit(s, s.get_rect(center=(rect.centerx, rect.y + 340 + k * 18)))

        if marcada:
            ay = rect.bottom + 12 + int(math.sin(t * 0.2) * 3)
            for k in range(5):
                self.surface.fill(neon, (rect.centerx - (5 - k) * 2, ay + k * 2, (5 - k) * 4, 2))

    def _draw_settings(self):
        self.slider_musica.draw(self.surface, AZUL)
        self.slider_sfx.draw(self.surface, MENTA)
        self.slider_sensibilidad.draw(self.surface, (255, 200, 100))

        self.btn_silencio.text = f"SILENCIO: {'SI' if audio.esta_silenciado() else 'NO'}"
        self.btn_pantalla.text = f"PANTALLA COMPLETA: {'SI' if settings.get('pantalla_completa') else 'NO'}"
        self.btn_camara.text = f"CAMARA: {settings.get('camera_index')}"
        self.btn_bonus_buffs.text = f"BONUS CON TODOS LOS BUFFS: {'SI' if settings.get('bonus_todos_buffs') else 'NO'}"
        marcado = self.settings_widgets[self.ajuste_sel]
        for widget in self.settings_widgets:
            if isinstance(widget, MenuButton):
                extra = int(math.sin(self.hover_amp) * 8) if widget is marcado else 0
                widget.draw(self.surface, extra_offset=extra, marcado=widget is marcado)
        # flechita neon a la izquierda de lo marcado
        r = marcado.rect
        ay = r.centery if isinstance(marcado, MenuButton) else r.y - 16
        ax = r.x - 26 + int(math.sin(self.hover_amp) * 3)
        for k in range(5):
            self.surface.fill((255, 120, 230), (ax + k * 2, ay - (5 - k) * 2, 2, (5 - k) * 4))

        self._dibujar_ayuda("Flechas para moverte - IZQ/DER cambia el valor - ENTER para elegir - ESC para volver",
                            "Palanca o cruceta para moverte - IZQ/DER cambia el valor - A para elegir - B para volver",
                            self.screen_height - 30)
