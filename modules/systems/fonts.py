"""
Renderizado de texto del juego (menu, HUD, jefes, pantallas de fin de
partida, etc.): una fuente monoespaciada de "terminal" (Lucida Console -la
fuente clasica de la consola de Windows-, con respaldo a Consolas, Courier
New y Ubuntu Mono si no estuviera instalada) para que todo el texto tenga
ese aire binario/de codigo de ciberespacio, renderizada limpia y con
antialias (sin bloques de pixel art) mas un contorno oscuro sutil para que
se lea bien sobre fondos con estrellas, explosiones y luces parpadeantes.

render_text() (por tamaño) y render_texto_pixelado() (por objeto Font ya
creado) son los dos puntos de entrada; ambos pasan por el mismo contorno
asi que todo el texto del juego luce consistente.
"""

import pygame

_CACHE = {}
_TEXT_CACHE = {}
_TEXT_CACHE_LIMIT = 400

_CONTORNO_COLOR = (8, 6, 18)
_CONTORNO_ALPHA = 210
_CONTORNO_GROSOR = 1

# Fuente "digital"/de terminal por defecto para todo el juego. SysFont
# prueba los nombres en orden y se queda con el primero instalado.
FUENTE_DIGITAL = "lucidaconsole,consolas,couriernew,ubuntumono"


def get_font(size, name=FUENTE_DIGITAL, bold=False, italic=False):
    key = (name, size, bold, italic)
    fnt = _CACHE.get(key)
    if fnt is None:
        fnt = pygame.font.SysFont(name, size, bold=bold, italic=italic)
        _CACHE[key] = fnt
    return fnt


def _cap_text_cache():
    while len(_TEXT_CACHE) > _TEXT_CACHE_LIMIT:
        _TEXT_CACHE.pop(next(iter(_TEXT_CACHE)))


def _contorno_texto(superficie, color=_CONTORNO_COLOR, alpha=_CONTORNO_ALPHA, grosor=_CONTORNO_GROSOR):
    """Contorno oscuro fino alrededor de la silueta del texto: mejora la
    legibilidad sobre fondos con estrellas, nebulosas y explosiones de
    color sin volver el texto "grueso" ni pixelado."""
    w, h = superficie.get_size()
    if w <= 0 or h <= 0 or grosor <= 0:
        return superficie
    try:
        mascara = pygame.mask.from_surface(superficie, 40)
    except (pygame.error, ValueError):
        return superficie
    if mascara.count() == 0:
        return superficie

    silueta = mascara.to_surface(
        setcolor=(color[0], color[1], color[2], alpha),
        unsetcolor=(0, 0, 0, 0),
    )
    resultado = pygame.Surface((w + grosor * 2, h + grosor * 2), pygame.SRCALPHA)
    for dx in range(-grosor, grosor + 1):
        for dy in range(-grosor, grosor + 1):
            if dx == 0 and dy == 0:
                continue
            if dx * dx + dy * dy > grosor * grosor + 1:
                continue
            resultado.blit(silueta, (grosor + dx, grosor + dy))
    resultado.blit(superficie, (grosor, grosor))
    return resultado


def render_texto_pixelado(fuente, texto, color, factor_pixel=None, ancho_maximo=None, contorno=True):
    """Renderiza texto limpio (con antialias, sin bloques de pixel art) con
    un objeto Font ya creado, mas un contorno sutil opcional. factor_pixel
    se ignora (se conserva el parametro por compatibilidad con quienes ya
    lo pasaban)."""
    superficie = fuente.render(texto, True, color)
    if ancho_maximo and superficie.get_width() > ancho_maximo > 0:
        factor = ancho_maximo / superficie.get_width()
        nuevo_alto = max(1, int(superficie.get_height() * factor))
        superficie = pygame.transform.smoothscale(superficie, (ancho_maximo, nuevo_alto))

    if contorno:
        superficie = _contorno_texto(superficie)
    return superficie


def render_text(text, size, color, name=FUENTE_DIGITAL, bold=False, italic=False, antialias=True,
                 pixelate=False, pixel_factor=None, outline=True):
    """Punto de entrada mas usado en el juego (HUD, jefes, enemigos,
    pantallas de fin de partida...). Texto limpio con antialias en la
    fuente de terminal, cacheado por combinacion de parametros para no
    repetir el trabajo de mascara/contorno en cada frame. pixelate/
    pixel_factor se ignoran (se conservan por compatibilidad)."""
    color = (int(color[0]), int(color[1]), int(color[2]))
    key = (text, size, color, name, bold, italic, antialias, outline)
    cached = _TEXT_CACHE.get(key)
    if cached is not None:
        return cached

    fnt = get_font(size, name, bold, italic)
    surface = fnt.render(text, antialias, color)
    if outline:
        surface = _contorno_texto(surface)

    _TEXT_CACHE[key] = surface
    _cap_text_cache()
    return surface
