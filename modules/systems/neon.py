"""
Piezas de interfaz en pixel art neon compartidas por las cartas de mejora,
los carteles, las pantallas de fin de partida y las cinematicas: marco con
esquinas en escalon, panel oscuro con scanlines, titulos con halo, cinta de
etiqueta, globos de dialogo y franjas de cine. Asi todo lo que no es el
juego en si se ve como las cartas de mejora."""

import math

import pygame

from modules.constants import WHITE
from modules.systems import pixelfx
from modules.systems.fonts import get_font

CONTORNO = pixelfx.CONTORNO
FONDO = (22, 12, 52)
LINEA = (28, 16, 62)
CIAN = (90, 220, 255)
MAGENTA = (255, 90, 220)
ORO = (255, 200, 60)
VERDE = (120, 255, 170)
ROJO = (255, 70, 110)


def marco_pixel(surface, rect, color, grosor=4):
    """Marco con las esquinas recortadas en escalon."""
    x, y, w, h = rect
    p = grosor
    surface.fill(color, (x + p * 2, y, w - p * 4, p))
    surface.fill(color, (x + p * 2, y + h - p, w - p * 4, p))
    surface.fill(color, (x, y + p * 2, p, h - p * 4))
    surface.fill(color, (x + w - p, y + p * 2, p, h - p * 4))
    for cx, cy in ((x + p, y + p), (x + w - p * 2, y + p), (x + p, y + h - p * 2), (x + w - p * 2, y + h - p * 2)):
        surface.fill(color, (cx, cy, p, p))


def panel(surface, rect, color, t=0, halo=True, alfa=None, brillo_interno=True):
    """Panel tipo carta: halo del color, contorno oscuro, fondo violeta
    con scanlines y el marco neon. alfa (0-255) lo deja semitransparente."""
    rect = pygame.Rect(rect)
    if halo:
        pixelfx.dibujar_halo(surface, pixelfx.apagar(color, 0.3), rect.centerx, rect.centery,
                             int(min(rect.w, rect.h) * 0.75))
    if alfa is None:
        surface.fill(CONTORNO, rect.inflate(8, 8))
        surface.fill(FONDO, rect)
        for y in range(rect.y + 6, rect.bottom - 4, 6):
            surface.fill(LINEA, (rect.x + 6, y, rect.w - 12, 2))
    else:
        capa = pygame.Surface(rect.inflate(8, 8).size, pygame.SRCALPHA)
        capa.fill((*CONTORNO, alfa))
        capa.fill((*FONDO, alfa), (4, 4, rect.w, rect.h))
        for y in range(10, rect.h, 6):
            capa.fill((*LINEA, alfa), (10, y, rect.w - 12, 2))
        surface.blit(capa, (rect.x - 4, rect.y - 4))
    marco_pixel(surface, rect, color)
    if brillo_interno and (t // 8) % 2 == 0:
        marco_pixel(surface, rect.inflate(-12, -12), pixelfx.aclarar(color, 0.5), 2)
    return rect


def texto(tam, contenido, color, bold=True):
    return get_font(tam, bold=bold).render(contenido, True, color)


def titulo(surface, contenido, tam, color, cx, cy, halo=True, sombra=True):
    """Texto grande centrado con contorno oscuro pixelado y halo neon."""
    frente = texto(tam, contenido, color)
    rect = frente.get_rect(center=(int(cx), int(cy)))
    if halo:
        pixelfx.dibujar_halo(surface, pixelfx.apagar(color, 0.3), rect.centerx, rect.centery,
                             max(40, min(rect.w // 2 + 20, 170)))
    if sombra:
        oscuro = texto(tam, contenido, CONTORNO)
        paso = max(2, tam // 16)
        for dx, dy in ((-paso, 0), (paso, 0), (0, -paso), (0, paso), (paso, paso + 1)):
            surface.blit(oscuro, (rect.x + dx, rect.y + dy))
    surface.blit(frente, rect)
    return rect


def cinta(surface, contenido, color, centro, tam=13):
    """Etiqueta solida (como la de rareza de las cartas)."""
    letras = texto(tam, contenido, CONTORNO)
    caja = pygame.Rect(0, 0, letras.get_width() + 20, letras.get_height() + 6)
    caja.center = centro
    surface.fill(CONTORNO, caja.inflate(4, 4))
    surface.fill(color, caja)
    surface.blit(letras, letras.get_rect(center=caja.center))
    return caja


def globo(surface, contenido, x, y, color=CIAN, cola_derecha=True, tam=16):
    """Globo de dialogo pixel: panel chico con cola en escalon. (x, y) es
    la punta de la cola, el globo queda arriba."""
    letras = texto(tam, contenido, WHITE, bold=True)
    caja = pygame.Rect(0, 0, letras.get_width() + 28, letras.get_height() + 18)
    caja.midbottom = (int(x) + (-30 if cola_derecha else 30), int(y) - 12)
    caja.x = max(6, min(surface.get_width() - caja.w - 6, caja.x))
    surface.fill(CONTORNO, caja.inflate(8, 8))
    surface.fill(FONDO, caja)
    marco_pixel(surface, caja, color, 3)
    # cola en escalon hacia la punta
    for k in range(4):
        surface.fill(CONTORNO, (int(x) - 5 + (k * 2 if cola_derecha else -k * 2), caja.bottom + k * 3, 10, 4))
        surface.fill(color, (int(x) - 2 + (k * 2 if cola_derecha else -k * 2), caja.bottom + k * 3, 4, 3))
    surface.blit(letras, letras.get_rect(center=caja.center))
    return caja


def boton(surface, rect, contenido, color, marcado, t=0, tam=17):
    rect = pygame.Rect(rect)
    if marcado:
        rect.y -= 2 + int(math.sin(t * 0.15) * 2)
        pixelfx.dibujar_halo(surface, color, rect.centerx, rect.centery, rect.w // 2 + 10)
    surface.fill(CONTORNO, rect.inflate(6, 6))
    surface.fill(pixelfx.apagar(color, 0.35) if marcado else FONDO, rect)
    marco_pixel(surface, rect, color if marcado else pixelfx.apagar(color, 0.55), 3)
    letras = texto(tam, contenido, WHITE if marcado else (190, 190, 220))
    if letras.get_width() > rect.w - 14:
        letras = pygame.transform.smoothscale(
            letras, (rect.w - 14, max(1, int(letras.get_height() * (rect.w - 14) / letras.get_width()))))
    surface.blit(letras, letras.get_rect(center=rect.center))
    return rect


def scanlines(surface, alfa=40, paso=3):
    """Lineas CRT oscuras encima de todo."""
    ancho, alto = surface.get_size()
    clave = ("scan", ancho, alto, alfa, paso)
    capa = pixelfx._cache.get(clave)
    if capa is None:
        capa = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        for y in range(0, alto, paso):
            capa.fill((0, 0, 0, alfa), (0, y, ancho, 1))
        pixelfx._guardar(clave, capa)
    surface.blit(capa, (0, 0))


def franjas_cine(surface, k, color=CIAN, alto=56):
    """Franjas negras de cine arriba y abajo (k de 0 a 1) con un filo neon."""
    if k <= 0:
        return
    ancho = surface.get_width()
    h = int(alto * min(1.0, k))
    surface.fill((4, 2, 12), (0, 0, ancho, h))
    surface.fill((4, 2, 12), (0, surface.get_height() - h, ancho, h))
    for yy in (h - 3, surface.get_height() - h):
        for x in range(0, ancho, 12):
            surface.fill(color if (x // 12) % 2 == 0 else pixelfx.apagar(color, 0.5), (x, yy, 8, 3))


def cuadro_pixel(surface, color, x, y, tam):
    """Particula cuadrada (alineada a la grilla de pixel)."""
    tam = max(2, int(tam) // 2 * 2)
    surface.fill(color, (int(x) // 2 * 2 - tam // 2, int(y) // 2 * 2 - tam // 2, tam, tam))


def anillo_pixel(surface, color, cx, cy, radio, tam=6, cantidad=None):
    """Anillo de cuadraditos (en vez de un circulo liso)."""
    cantidad = cantidad or max(10, int(radio * 0.5))
    for i in range(cantidad):
        a = 2 * math.pi * i / cantidad
        cuadro_pixel(surface, color, cx + math.cos(a) * radio, cy + math.sin(a) * radio, tam)


def velo(surface, color, alfa):
    if alfa <= 0:
        return
    capa = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    capa.fill((*color[:3], max(0, min(255, int(alfa)))))
    surface.blit(capa, (0, 0))
