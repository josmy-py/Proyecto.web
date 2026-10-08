"""
Genera en pixel art neon las naves (assets/sprites/ships/), los enemigos
comunes (assets/sprites/enemies/) y los jefes (assets/sprites/boss/).

Cada nave se dibuja a mano como un mapa de caracteres (solo la mitad
izquierda; la derecha se obtiene en espejo) sobre una grilla chica. Las naves
miran hacia arriba y los enemigos hacia abajo. De cada mapa salen cinco PNG:

  <clase>_body.png    casco en escala de grises (se tinta con el color de casco)
  <clase>_wing.png    alas en escala de grises (se tinta con el color de alas)
  <clase>_neon.png    lineas neon en blanco (se tinta con el color de alas
                      aclarado, para que brillen mas que el resto)
  <clase>_detail.png  contorno, cabina, toberas y luces (no se tinta)
  <clase>_glow.png    halo suave de las lineas neon y toberas, a 4x de
                      resolucion (se tinta con el color de alas y va debajo)

body/wing/neon/detail quedan a la resolucion de la grilla: el juego los agranda
sin suavizar (pixeles en bloque, ver sprites.get_ship_surface).

Uso:  python tools/generate_pixel_sprites.py
"""

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "sprites")

PAD = 3            # celdas libres alrededor para que entre el halo
GLOW_SCALE = 4     # resolucion del halo respecto de la grilla
GLOW_BLUR = 5.0

# Leyenda de los mapas -----------------------------------------------------
#   .  vacio
#   o  contorno oscuro
#   B b d   casco: claro / medio / sombra       (capa body)
#   W w v   ala:   claro / medio / sombra       (capa wing)
#   N       linea neon (capa neon + halo)
#   C c h   cristal de cabina: claro / oscuro / reflejo
#   e E     tobera: carcasa / nucleo encendido (+ halo)
#   G       luz de navegacion (verde a la izquierda, roja en el espejo)
#   x u     sombra mas oscura del casco / del ala
#   A a Y   piloto alien: piel clara / oscura / brillo de los ojos
#   K       hueso: cuernos y garras

BODY = {"B": 235, "b": 172, "d": 112, "x": 70}
WING = {"W": 200, "w": 140, "v": 88, "u": 55}
NEON = {"N": 255}
DETAIL = {
    "o": (12, 6, 34, 255),
    "C": (90, 236, 255, 255),
    "c": (34, 120, 210, 255),
    "h": (240, 255, 255, 255),
    "e": (44, 40, 78, 255),
    "E": (200, 252, 255, 255),
    "G": (90, 255, 170, 255),
    "R": (255, 70, 120, 255),
    "A": (120, 240, 130, 255),
    "a": (40, 150, 80, 255),
    "Y": (255, 255, 255, 255),
    "K": (236, 226, 204, 255),
}
GLOW = {"N": 1.0, "E": 1.0, "G": 0.8, "R": 0.8, "C": 0.35, "h": 0.35}

SHIPS = {
    "scout": """
....................
...................o
..................oN
..................oB
.................oBB
.................oBC
................obBC
................obCh
................obCC
................obcC
...............odbcC
...............odbBB
...............odbBN
..............oodbBB
.............oNwodbB
............oNWvodbB
...........oNWwvodbB
..........oNWwwvodbN
.........oNWwwvvodbB
........oNWwwvvoodbB
.......oNWwwvvo.odbB
......oNWwwvvo..odbB
.....oNWwwvvo...odbB
....oGWwwvvo...oodbN
....ovvvvoo...oNodbB
.....ooo.....oNWodbe
............oNWwoeeE
............ovvvoeEE
.............ooo.oEE
.................oE.
..................E.
....................
""",
    "tank": """
....................
....................
..................oo
.................oNB
................obBB
...............obBBB
..............odbBCC
.............oodbChC
............oNodbCCC
...........oNWodbcCC
..........oNWwodbccC
..........oWwvodbBBB
.....ooo..oWwvodbBBN
....oNNNo.owvvodbBBB
...oNWWWWooWvvodbbBB
..oNWWwwwwWwvvodbbBB
.oNWWwwwwwwwvvodbbBN
.oWWwwwwwwwwvvodbbBB
.oWwwwwwwwwwvvodbbBB
.oGwwvvvvvvvvvodbbBB
.owwvvvvvvvvvvodbbBN
.ovvvoooooooooodbbBB
..ooo.........odbbBB
.............oddbbBB
.............odddbbB
.............oeeeeoo
.............oeEEeo.
.............oeEEeo.
..............oEEo..
...............EE...
....................
....................
""",
    "interceptor": """
...................o
...................N
..................oB
..................oB
..................oB
.................obC
.................obh
.................obC
..............oo.obC
.............oNWoobc
............oNWwvobB
.............ooovobB
.................obN
................odbB
...............oNdbB
..............oNWodB
.............oNWwodB
............oNWwvodB
...........oNWwwvodB
..........oNWwwvvodN
.........oNWwwvvvodB
........oNWwwvvvvodB
.......oNWwwvvvvoodB
......oNWwwvvvvo.odB
.....oGWwwvvvoo..odB
.....ovvvvooo...oeeo
......ooo.......oEeo
................oEEo
.................EE.
....................
....................
....................
""",
    "bomber": """
....................
....................
....................
.................ooo
...............ooNBB
..............obBBBB
.............obBBCCC
............odbBChCC
............odbBCCCC
...........oddbBcCCC
...........oddbBBccc
...........oddbBBBBB
....oo.....oddbBBBBN
...oNNo....oddbBBBBB
..oNWWWoooooddbBBBBB
..oWWwWNWWWWoddbBBBB
..oWwwvWwwwwoddbbBBN
..oWwwvWwwwwoddbbBBB
..oWwwvWwwvvoddbbBBB
..oGwwvWwvvvoddbbBBB
..ovvvvoovvvoddbbBBN
..oeEEeo.oooodddbbBB
..oeEEeo....oddddbbB
...oEEo.....oeeeoeee
....EE......oeEeooeE
............oeEeo.oE
.............oEo..oE
..............E....E
....................
....................
....................
....................
""",
}


ENEMIES = {
    "fighter": """
..............
..oo.......ooo
.oNo......oeEE
.oWvo.....oeeE
.oWwvo....obBB
..oWwvo..obBBB
..oWwwvo.obBBB
...oWwwvoobBBN
...oWwwwvobBBB
....oWwwvobBBB
....oNWwvobBCC
.....oNWvobBCh
.....oNWvobBCC
......oNvobBcC
......oNvobBcc
.......ovobBBB
........oobBBN
.........obBBB
.........odbBB
.........odbBB
..........odbB
..........odbB
...........odN
...........odB
............oN
.............o
..............
..............
""",
    "gunner": """
..............
..............
...oooo.......
..oNWWNo..oooo
..oWwwvo.oeEEE
..oWwwvoobBBBB
..oWwwvobBBBBB
..oWwwvobBddBB
..oNwwvobBdoCC
..oWwwvobBdoCh
..oWwwvobBdoCC
..oWwwvobBddBB
..oWwwvobBBBBB
..oNwwvobBBBBN
...oWvoobBBBBB
...oeeo.obBBBB
...oeeo..obBBB
...oeeo...obBB
...oEEo....obB
....EE......oN
.............o
..............
..............
..............
..............
..............
..............
..............
""",
    # dardo: aguja fina con alas cortas cerca del morro y dos motores
    "fighter_b": """
..............
..............
...........ooo
..........oeEE
..........oeee
...........obB
...........obB
..........odbB
..........odbB
..........odbN
..........odbB
.........oodbB
........oNodbC
.......oNWodbC
......oNWwodCh
.....oNWwvodCC
....oNWwvvodcC
...oNWwvvoodBB
...oWwvvo.odBN
....ooo...odbB
..........odbB
...........odB
...........odN
............oB
............oN
.............o
..............
..............
""",
    # mantis: alas en media luna que se curvan hacia abajo como garras
    "fighter_c": """
..............
..............
..........oooo
.........oeEEE
.........oeeee
...oo...obBBBB
..oNWo.obBBBBB
.oNWwvoobBBdBB
.oWwwvvobBddBB
.oWwwvvobBdoCC
.oWwvvoobBdoCh
.oWwvo.obBdoCC
.oWwvo.obBddBB
.oNwvo..obBBBN
.oNwvo..obBBBB
.oNWvo...obBBB
..oNvo...obBBB
..oNvo....obBB
...oNo....obBN
...oNo.....obB
....o......obB
............oN
.............o
..............
..............
..............
..............
..............
""",
    # torreta: cuerpo redondo con cuatro cañones hacia abajo
    "gunner_b": """
..............
..............
..............
.......ooooooo
.....ooWWWWWWW
....oWWWwwwwww
...oWWwwooooob
...oWwwobBBBBB
..oWwwobBBddBB
..oWwvobBdooCC
..oNwvobBdoCCh
..oNwvobBdoCCC
..oWwvobBBdooo
..oWwvvobBBddd
...oWvvvobbbbb
...oWvvvvooooo
....ovvvvvvvvv
.....oovvvvvvv
......oeoooeoo
......oeo.oeo.
......oeo.oeo.
......oEo.oEo.
.......E...E..
..............
..............
..............
..............
..............
""",
    # acorazado: casco ancho con dos vainas de cañones a los costados
    "gunner_c": """
..............
..............
......oooooooo
.....oNWWWWWWW
....oWwwwwwwww
.ooooWwvvvvvvv
oeEeoWwvoooooo
oeeeoWwvobBBBB
oeeeoWwvobBBBB
oeeeoWwvobBddd
oNNNoWwvobBdCC
oWwvoWwvobBdCh
oWwvoWwvobBdCC
oWwvoWwvobBddd
oWwvoWwvobBBBB
oWwvoNwvobBBBN
oeeeoNwvobBBBB
oeEeooWvvobBBB
.oEo.oWvvobBBB
..E..oWvvvobBB
.....oNWvvobBB
......oNvvvobN
.......ooooobB
............oB
.............o
..............
..............
..............
""",

}


# ---------------------------------------------------------------- platillos

# Modelos de platillo: cada uno cambia la forma del anillo, la cantidad de
# paneles y luces, el tamaño de la cupula y el tipo de ojo.
PLATILLOS = {
    # clasico: anillo ancho, 8 puertos de luz, cupula grande con ojo
    "drone": dict(paneles=8, puertos=8, cupula=4.9, ojo="punto", pinchos=0, aro=10.0, oval=1.0),
    # cazador: 4 pinchos hacia afuera, cupula chica con ojo en rendija
    "drone_b": dict(paneles=6, puertos=4, cupula=3.9, ojo="rendija", pinchos=4, aro=9.4, oval=1.0),
    # nodriza: ovalado y achatado, muchas luces chicas, triple ojo
    "drone_c": dict(paneles=12, puertos=12, cupula=4.4, ojo="triple", pinchos=0, aro=10.4, oval=0.78),
    # sierra: borde dentado de 8 dientes, sin cupula, nucleo de energia
    "drone_d": dict(paneles=8, puertos=0, cupula=3.4, ojo="nucleo", pinchos=8, aro=8.6, oval=1.0),
}


def _cerca(ang, cada, ancho, desfase=0.0):
    paso = 360.0 / cada
    return abs(((ang + desfase + paso / 2) % paso) - paso / 2) < ancho


def platillo(nombre, n=30):
    """Platillo visto desde arriba, armado por distancia y angulo al centro:
    borde, anillo exterior con paneles y muescas neon, canal con puertos de
    luz, placa del casco con nervaduras y cupula con ojo."""
    p = PLATILLOS[nombre]
    c = (n - 1) / 2.0
    filas = []
    for y in range(n):
        fila = ""
        for x in range(n):
            dx = x - c
            dy = (y - c) / p["oval"]
            r = math.hypot(dx, dy)
            ang = math.degrees(math.atan2(dy, dx)) % 360
            luz = (-dx - dy) / (r + 1e-6)          # 1 arriba-izquierda, -1 abajo-derecha
            borde = 12.9
            if p["pinchos"]:
                # pinchos/dientes que sobresalen del borde
                if _cerca(ang, p["pinchos"], 7.0 if p["pinchos"] <= 4 else 9.0):
                    borde = 13.9 if p["pinchos"] > 4 else 14.6
                elif p["pinchos"] > 4:
                    borde = 12.2
            if r > borde + 1.0:
                ch = "."
            elif r > borde:
                ch = "o"
            elif r > 12.9 and p["pinchos"]:
                ch = "N" if r > borde - 0.9 and p["pinchos"] <= 4 else "W" if luz > 0 else "v"
            elif r > p["aro"]:
                if _cerca(ang, p["paneles"], 3.5, 180.0 / p["paneles"]) and p["aro"] + 0.6 < r < 12.4:
                    ch = "N"
                elif _cerca(ang, p["paneles"], 2.2):
                    ch = "v"
                elif r > 12.2:
                    ch = "W" if luz > -0.2 else "w"
                else:
                    ch = "W" if luz > 0.45 else "w" if luz > -0.45 else "v"
            elif r > p["aro"] - 1.0:
                ch = "E" if p["puertos"] and _cerca(ang, p["puertos"], 4.5, 180.0 / p["puertos"]) else "o"
            elif r > p["cupula"] + 1.1:
                if _cerca(ang, 6, 4.0) and r > p["cupula"] + 1.7:
                    ch = "d"
                elif r > p["aro"] - 1.7:
                    ch = "B" if luz > -0.3 else "b"
                elif r < p["cupula"] + 1.8:
                    ch = "b" if luz > 0.0 else "d"
                else:
                    ch = "B" if luz > 0.5 else "b" if luz > -0.4 else "d"
            elif r > p["cupula"]:
                ch = "o"
            else:
                ch = _ojo(p["ojo"], dx, dy, r, luz, p["cupula"])
            fila += ch
        filas.append(fila)
    return filas


def _ojo(tipo, dx, dy, r, luz, radio):
    if tipo == "nucleo":
        return "h" if r < 1.2 else "E" if r < radio - 1.0 else "C"
    if tipo == "rendija":
        if abs(dx) < 0.6 and abs(dy) < radio - 1.2:
            return "R"
        if abs(dx) < 1.6 and abs(dy) < radio - 1.6:
            return "o"
    elif tipo == "triple":
        for ox in (-2.5, 0.0, 2.5):
            d = math.hypot(dx - ox, dy)
            if d < 0.8:
                return "R"
            if d < 1.3:
                return "o"
    else:
        if r < 1.5:
            return "R"
        if r < 2.4:
            return "o"
    if dx < -0.5 and dy < -0.5 and r > radio * 0.6:
        return "h"
    return "C" if luz > -0.3 else "c"


# Los platillos se arman por codigo (mapa completo, sin espejo).
for _nombre in PLATILLOS:
    ENEMIES[_nombre] = platillo(_nombre)


# ------------------------------------------------------------------ jefes
# Mapas completos (sin espejo), armados por codigo. Los puntos fijos que el
# juego anima encima (luces, emisor, torretas) estan copiados como
# constantes en la clase de cada jefe.

# Posiciones (en celdas de la grilla, sin PAD) de los enchufes de luz del
# anillo: boss_system.py dibuja ahi las luces que corren.
CENTINELA_W, CENTINELA_H = 78, 40


def centinela():
    """Nave nodriza del Centinela, de frente y un poco desde arriba: cupula
    con el piloto alien, casco con ojos de buey, anillo ancho con enchufes
    para las luces, panza con el emisor del rayo y dos torretas."""
    W, H = CENTINELA_W, CENTINELA_H
    g = [["."] * W for _ in range(H)]
    cx = (W - 1) / 2.0

    def put(x, y, ch):
        if 0 <= x < W and 0 <= y < H:
            g[y][x] = ch

    def tono(luz, tonos):
        # tonos de claro a oscuro; luz en [-1, 1]
        i = int((1 - (luz + 1) / 2) * len(tonos))
        return tonos[max(0, min(len(tonos) - 1, i))]

    for y in range(H):
        for x in range(W):
            dx = x - cx
            # anillo (ala): cara de arriba clara, canto frontal oscuro
            e = ((dx) / 38.5) ** 2 + ((y - 21.5) / 4.6) ** 2
            if e <= 1.0 and 18 <= y:
                if e > 0.82:
                    put(x, y, "o")
                elif y <= 20:
                    put(x, y, tono(-dx / 40 + 0.4, "WWw"))
                elif y == 21:
                    put(x, y, "N")
                else:
                    put(x, y, tono(-dx / 40 - 0.2, "wvvu"))
            # casco inferior (panza)
            e = (dx / 25) ** 2 + ((y - 23) / 9.5) ** 2
            if y >= 24 and e <= 1.0:
                if e > 0.84:
                    put(x, y, "o")
                elif y == 25:
                    put(x, y, "e" if int(abs(dx)) % 3 == 0 else "x")
                else:
                    put(x, y, tono(-dx / 26 - (y - 24) / 6, "bddx"))
            # casco superior
            e = (dx / 27.5) ** 2 + ((y - 19) / 8.5) ** 2
            if y <= 18 and e <= 1.0:
                if e > 0.87:
                    put(x, y, "o")
                elif y == 15 and 5 < abs(dx) < 24:
                    put(x, y, "N" if abs(dx) > 9 else "o")
                elif y == 17 and abs(dx) < 23 and int(abs(dx) + 1.5) % 5 == 0:
                    put(x, y, "E")
                elif y >= 16 and abs(abs(dx) - 13) < 0.5:
                    put(x, y, "x")
                else:
                    put(x, y, tono(-dx / 28 - (y - 14) / 7, "BBbbd"))
            # cupula
            e = (dx / 10.5) ** 2 + ((y - 13) / 10.5) ** 2
            if y <= 13 and e <= 1.0:
                if e > 0.8:
                    put(x, y, "o")
                else:
                    luz = -dx / 10 - (y - 9) / 8
                    if 0.45 < e < 0.62 and dx < -1 and y < 10:
                        put(x, y, "h")
                    else:
                        put(x, y, "c" if luz < 0.6 else "C")
    # piloto alien dentro de la cupula
    alien = [
        "..AAAA..",
        ".AAAAAA.",
        "AYoAAYoA",
        "AooAAooA",
        ".AAAAAA.",
        "..aaaa..",
        ".aAAAAa.",
    ]
    ax, ay = int(cx) - 3, 6
    for j, fila in enumerate(alien):
        for i, ch in enumerate(fila):
            if ch != ".":
                put(ax + i, ay + j, ch)
    put(int(cx), 4, "o")
    put(int(cx) + 1, 4, "o")
    # emisor central del rayo
    for y in range(28, 35):
        half = {28: 6, 29: 5, 30: 5, 31: 4, 32: 3, 33: 2, 34: 1}[y]
        x0, x1 = int(cx - half) + 1, int(cx + half)
        for x in range(x0 - 1, x1 + 1):
            borde = x in (x0 - 1, x1) or y == 34
            put(x, y, "o" if borde else ("E" if y >= 31 else "e"))
    # torretas laterales
    for s in (-1, 1):
        tx = int(round(cx + s * 15.5))
        for y in range(27, 33):
            for x in range(tx - 2, tx + 3):
                borde = abs(x - tx) == 2 or y == 32
                put(x, y, "o" if borde else ("E" if y == 31 else "e" if y > 28 else "x"))
    # enchufes de las luces del anillo (las prende el juego)
    for k in range(-4, 5):
        put(int(round(cx + k * 7.6)), 23, "e")
    put(int(cx - 36), 21, "G")
    put(int(cx + 37), 21, "R")
    return ["".join(f) for f in g]



DRAGON_W, DRAGON_H = 72, 56
_CH = ".oBbdxWwvuNCchEeGRAaYK"


def _contorno(filas):
    """Agrega contorno oscuro alrededor de todo lo dibujado."""
    H, W = len(filas), len(filas[0])
    g = [list(f) for f in filas]
    for y in range(H):
        for x in range(W):
            if filas[y][x] != ".":
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < W and 0 <= yy < H and filas[yy][xx] not in ".o":
                    g[y][x] = "o"
                    break
    return ["".join(f) for f in g]


def _espejar(img):
    """Mitad izquierda dibujada -> mapa completo simetrico."""
    W, H = img.size
    px = img.load()
    filas = []
    for y in range(H):
        izq = "".join(_CH[px[x, y]] for x in range(W // 2))
        filas.append(izq + izq[::-1])
    return filas


def dragon(alas=0):
    """Dragon espacial visto desde arriba, bajando hacia la nave: cabeza
    abajo con las fauces abiertas, alas de murcielago abiertas y la cola
    hacia arriba. alas=0 alas arriba, 1 alas abajo (aleteo)."""
    img = Image.new("L", (DRAGON_W, DRAGON_H), 0)
    d = ImageDraw.Draw(img)
    c = DRAGON_W // 2          # las figuras se dibujan a la izquierda de c

    def P(pts, ch):
        d.polygon(pts, fill=_CH.index(ch))

    def L(pts, ch, ancho=1):
        d.line(pts, fill=_CH.index(ch), width=ancho)

    def E(caja, ch):
        d.ellipse(caja, fill=_CH.index(ch))

    # cola: sube hasta una punta de flecha, con pinchos neon en el lomo
    P([(c - 3, 24), (c - 2, 9), (c, 9), (c, 24)], "d")
    L([(c - 1, 22), (c - 1, 10)], "b")
    for y in (12, 16, 20):
        P([(c - 3, y), (c - 6, y + 1), (c - 3, y + 2)], "N")
    P([(c - 6, 9), (c - 1, 0), (c, 0), (c, 10)], "b")
    L([(c - 5, 8), (c - 1, 1)], "N")
    # alas: brazo del ala, tres dedos y membrana
    dy = 0 if alas == 0 else 7
    hombro = (c - 7, 25)
    codo = (c - 19, 13 + dy // 2)
    puntas = [(1, 6 + dy * 2), (2, 23 + dy), (9, 35 + dy // 2)]
    raiz = (c - 9, 34)
    tonos = ("w", "v", "w")
    for i, p in enumerate(puntas):
        sig = puntas[i + 1] if i + 1 < len(puntas) else raiz
        mx, my = (p[0] + sig[0]) // 2, (p[1] + sig[1]) // 2
        P([codo, p, (mx + 2, my - 1), sig], tonos[i])
    P([hombro, codo, raiz], "w")
    for p in puntas:
        L([codo, p], "N")
    L([hombro, codo], "W", 2)
    P([(codo[0] - 1, codo[1]), (codo[0] - 3, codo[1] - 4), (codo[0] + 1, codo[1] - 1)], "K")
    # cuerpo y pecho
    E([c - 10, 18, c + 9, 42], "d")
    E([c - 9, 19, c + 6, 39], "b")
    E([c - 7, 20, c + 2, 33], "B")
    for y in (27, 30, 33, 36):
        L([(c - 3, y), (c - 1, y)], "N")
    # patas con garras a los costados
    P([(c - 9, 34), (c - 15, 39), (c - 14, 42), (c - 8, 38)], "d")
    for k in range(3):
        d.point((c - 16 + k, 43 - (k == 1)), fill=_CH.index("K"))
    # cuello
    P([(c - 5, 38), (c - 4, 43), (c, 43), (c, 38)], "b")
    # cuernos largos hacia atras
    P([(c - 6, 42), (c - 13, 35), (c - 15, 30), (c - 11, 34), (c - 4, 39)], "K")
    L([(c - 14, 32), (c - 15, 30)], "h")
    P([(c - 8, 45), (c - 12, 44), (c - 8, 47)], "K")
    # cabeza con hocico largo hacia abajo
    E([c - 9, 40, c + 8, 51], "B")
    P([(c - 7, 47), (c - 4, 54), (c, 55), (c, 46)], "b")
    E([c - 7, 41, c - 2, 45], "B")
    L([(c - 1, 41), (c - 1, 44)], "N")
    # fauces abiertas con fuego adentro
    E([c - 3, 49, c + 2, 55], "o")
    E([c - 2, 50, c + 1, 54], "E")
    d.point((c - 2, 49), fill=_CH.index("K"))
    d.point((c - 3, 51), fill=_CH.index("K"))
    # ojo
    P([(c - 8, 45), (c - 4, 46), (c - 5, 47), (c - 8, 46)], "R")
    return _contorno(_espejar(img))


TITAN_W, TITAN_H = 76, 50


def titan():
    """Titan del Vacio: manto de pulpo blindado visto de frente, con un
    gran ojo-camara en el centro (la pupila la dibuja el juego), hombros
    con nucleos de energia y los muñones de donde salen los tentaculos."""
    img = Image.new("L", (TITAN_W, TITAN_H), 0)
    d = ImageDraw.Draw(img)
    c = TITAN_W // 2

    def E(caja, ch):
        d.ellipse(caja, fill=_CH.index(ch))

    def P(pts, ch):
        d.polygon(pts, fill=_CH.index(ch))

    def L(pts, ch, ancho=1):
        d.line(pts, fill=_CH.index(ch), width=ancho)

    # muñones de tentaculos (abajo, detras del cuerpo)
    for x, y in ((c - 20, 40), (c - 12, 44), (c - 4, 46)):
        E([x - 4, y - 4, x + 4, y + 4], "v")
        E([x - 2, y - 1, x + 2, y + 3], "u")
    # hombros: esferas con nucleo de energia
    E([c - 36, 22, c - 20, 38], "w")
    E([c - 34, 23, c - 24, 33], "W")
    E([c - 31, 27, c - 25, 33], "o")
    E([c - 30, 28, c - 26, 32], "E")
    # manto (la cabeza del pulpo)
    E([c - 24, 0, c + 24, 40], "d")
    E([c - 23, 1, c + 20, 37], "b")
    E([c - 20, 2, c + 8, 26], "B")
    # placas del blindaje: costuras oscuras y remaches neon
    for y in (12, 20):
        L([(c - 22, y + 4), (c - 14, y), (c - 6, y - 1), (c, y - 1)], "x")
    L([(c - 12, 3), (c - 14, 12)], "x")
    L([(c - 5, 1), (c - 6, 11)], "x")
    for x, y in ((c - 18, 9), (c - 10, 6), (c - 19, 17), (c - 3, 15)):
        d.point((x, y), fill=_CH.index("N"))
    # cresta neon en la frente
    L([(c - 2, 0), (c - 2, 9)], "N")
    L([(c - 1, 0), (c - 1, 9)], "N")
    # placa de la cara
    E([c - 18, 22, c + 17, 44], "x")
    E([c - 17, 23, c + 15, 42], "d")
    # ojo-camara: aro metalico y cuenca oscura
    E([c - 11, 22, c + 10, 43], "o")
    E([c - 10, 23, c + 9, 42], "W")
    E([c - 8, 25, c + 7, 40], "o")
    E([c - 7, 26, c + 6, 39], "e")
    # pico
    P([(c - 3, 43), (c, 49), (c, 43)], "K")
    # luces bajo el ojo
    for x in (c - 14, c - 16):
        d.point((x, 37 + (x == c - 16)), fill=_CH.index("R"))
    return _contorno(_espejar(img))


ANOMALIA_W, ANOMALIA_H = 64, 58


def anomalia():
    """La Anomalia Final: calavera de vacio con el craneo partido, un nucleo
    de energia en la frente, cuencas vacias (los ojos los dibuja el juego)
    y la mandibula abierta. Las placas laterales van en la capa de ala."""
    img = Image.new("L", (ANOMALIA_W, ANOMALIA_H), 0)
    d = ImageDraw.Draw(img)
    c = ANOMALIA_W // 2

    def E(caja, ch):
        d.ellipse(caja, fill=_CH.index(ch))

    def P(pts, ch):
        d.polygon(pts, fill=_CH.index(ch))

    def L(pts, ch, ancho=1):
        d.line(pts, fill=_CH.index(ch), width=ancho)

    # placas/aletas laterales (capa de ala)
    P([(c - 22, 14), (c - 31, 6), (c - 30, 24), (c - 22, 30)], "w")
    P([(c - 23, 18), (c - 29, 12), (c - 28, 22)], "v")
    L([(c - 30, 7), (c - 30, 23)], "N")
    P([(c - 20, 34), (c - 28, 36), (c - 24, 44), (c - 18, 42)], "w")
    # craneo
    E([c - 22, 2, c + 22, 42], "d")
    E([c - 21, 3, c + 18, 39], "b")
    E([c - 18, 4, c + 4, 26], "B")
    # grieta del craneo (neon)
    L([(c - 1, 3), (c - 4, 9), (c - 2, 13), (c - 6, 18)], "N")
    # nucleo de la frente
    P([(c, 9), (c - 5, 14), (c, 19)], "o")
    P([(c, 11), (c - 3, 14), (c, 17)], "E")
    # pomulos con mejillas hundidas
    E([c - 21, 26, c - 10, 37], "b")
    L([(c - 19, 33), (c - 13, 37)], "x")
    # cuencas inclinadas (mirada enojada)
    P([(c - 18, 20), (c - 4, 25), (c - 5, 32), (c - 11, 33), (c - 17, 29)], "o")
    P([(c - 16, 22), (c - 6, 26), (c - 7, 30), (c - 11, 31), (c - 15, 28)], "e")
    # nariz
    P([(c, 31), (c - 3, 36), (c, 37)], "o")
    # fila de dientes de arriba
    L([(c - 12, 38), (c, 38)], "o")
    for x in range(c - 11, c, 3):
        P([(x, 39), (x + 1, 39), (x + 1, 41), (x, 41)], "K")
        L([(x + 2, 39), (x + 2, 40)], "o")
    # boca abierta: hueco de vacio con fuego frio adentro
    P([(c - 12, 42), (c - 10, 46), (c, 47), (c, 42)], "o")
    L([(c - 7, 44), (c, 44)], "E")
    # mandibula separada
    P([(c - 13, 47), (c - 11, 53), (c - 5, 56), (c, 57), (c, 48), (c - 9, 47)], "d")
    P([(c - 11, 48), (c - 10, 52), (c - 5, 54), (c, 55), (c, 49), (c - 8, 48)], "b")
    for x in range(c - 10, c, 3):
        P([(x, 46), (x + 1, 46), (x + 1, 48), (x, 48)], "K")
    return _contorno(_espejar(img))


if __name__ == "__main__":
    for f in anomalia():
        print(f)


CRUCERO_W, CRUCERO_H = 100, 50


def coloso_crucero():
    """Coloso Estelar, fase 1: acorazado visto desde arriba con la proa
    hacia abajo. Toberas arriba, alas con troneras (las prende el juego),
    bahias de hangar a los lados del casco y el cañon de riel en la proa."""
    img = Image.new("L", (CRUCERO_W, CRUCERO_H), 0)
    d = ImageDraw.Draw(img)
    c = CRUCERO_W // 2

    def P(pts, ch):
        d.polygon(pts, fill=_CH.index(ch))

    def R(caja, ch):
        d.rectangle(caja, fill=_CH.index(ch))

    def L(pts, ch, ancho=1):
        d.line(pts, fill=_CH.index(ch), width=ancho)

    def E(caja, ch):
        d.ellipse(caja, fill=_CH.index(ch))

    # alas en flecha (capa de ala)
    P([(c - 15, 12), (c - 44, 20), (c - 49, 26), (c - 46, 30), (c - 16, 31)], "w")
    P([(c - 15, 12), (c - 44, 20), (c - 46, 23), (c - 16, 18)], "W")
    P([(c - 46, 28), (c - 16, 29), (c - 16, 31), (c - 46, 30)], "v")
    L([(c - 18, 22), (c - 42, 25)], "u")
    L([(c - 30, 17), (c - 30, 29)], "u")
    # gondola de la punta del ala
    R([c - 50, 19, c - 45, 32], "d")
    R([c - 49, 19, c - 47, 31], "b")
    L([(c - 48, 17), (c - 48, 19)], "x")
    d.point((c - 48, 33), fill=_CH.index("G"))
    # troneras del borde de ataque (las enciende el juego)
    for x in (c - 42, c - 36, c - 30, c - 24):
        R([x, 29, x + 1, 30], "e")
    # neon a lo largo del ala
    L([(c - 17, 16), (c - 43, 22)], "N")
    # casco central
    P([(c - 11, 1), (c - 15, 6), (c - 17, 14), (c - 17, 32), (c - 11, 41), (c - 4, 47), (c, 47), (c, 1)], "d")
    P([(c - 10, 2), (c - 14, 7), (c - 15, 14), (c - 15, 31), (c - 10, 39), (c - 4, 45), (c, 45), (c, 2)], "b")
    P([(c - 8, 3), (c - 11, 8), (c - 11, 28), (c - 6, 36), (c, 38), (c, 3)], "B")
    # biseles del casco y costuras sueltas
    L([(c - 14, 8), (c - 16, 14), (c - 16, 30), (c - 11, 38)], "x")
    L([(c - 11, 10), (c - 1, 10)], "d")
    L([(c - 11, 27), (c - 6, 27)], "d")
    L([(c - 6, 4), (c - 6, 14)], "d")
    L([(c - 9, 30), (c - 9, 36)], "d")
    # toberas de popa
    for x in (c - 13, c - 8):
        R([x, 0, x + 3, 3], "e")
        R([x + 1, 0, x + 2, 1], "E")
    # silos de misiles
    for x, y in ((c - 12, 12), (c - 12, 15), (c - 9, 12), (c - 9, 15)):
        R([x, y, x + 1, y + 1], "x")
    # bahia de hangar
    R([c - 17, 28, c - 12, 35], "x")
    R([c - 16, 29, c - 13, 34], "e")
    L([(c - 16, 28), (c - 13, 28)], "N")
    # puente de mando
    R([c - 5, 16, c - 1, 25], "d")
    R([c - 4, 17, c - 1, 24], "W")
    R([c - 3, 19, c - 1, 21], "c")
    d.point((c - 3, 19), fill=_CH.index("h"))
    d.point((c - 2, 19), fill=_CH.index("C"))
    # lineas neon del lomo
    L([(c - 11, 8), (c - 15, 14)], "N")
    L([(c - 15, 20), (c - 15, 26)], "N")
    L([(c - 1, 27), (c - 1, 34)], "N")
    L([(c - 1, 5), (c - 1, 14)], "N")
    # cañon de riel en la proa
    R([c - 2, 36, c - 1, 49], "x")
    R([c - 1, 37, c - 1, 48], "e")
    d.point((c - 1, 49), fill=_CH.index("E"))
    R([c - 3, 38, c - 3, 41], "d")
    return _contorno(_espejar(img))


ESFERA_W, ESFERA_H = 64, 64


def coloso_esfera():
    """Coloso Estelar, fase 2: esfera de combate blindada con una trinchera
    neon en el ecuador, cuatro torretas y la parabola del superlaser abajo
    (el juego dibuja la carga ahi)."""
    img = Image.new("L", (ESFERA_W, ESFERA_H), 0)
    d = ImageDraw.Draw(img)
    c = ESFERA_W // 2

    def E(caja, ch):
        d.ellipse(caja, fill=_CH.index(ch))

    def R(caja, ch):
        d.rectangle(caja, fill=_CH.index(ch))

    def L(pts, ch, ancho=1):
        d.line(pts, fill=_CH.index(ch), width=ancho)

    # torretas (detras de la esfera, asoman en diagonal)
    for y in (12, 46):
        R([2, y, 9, y + 5], "v")
        R([3, y + 1, 8, y + 4], "w")
        R([0, y + 2, 3, y + 3], "u")
        d.point((5, y + 2), fill=_CH.index("N"))
    # cuerpo
    E([3, 2, 60, 61], "d")
    E([4, 3, 59, 59], "b")
    E([10, 5, 50, 38], "B")
    E([14, 8, 52, 30], "b")
    E([12, 6, 44, 22], "B")
    # placas curvas
    d.arc([12, 3, 52, 60], 100, 260, fill=_CH.index("d"))
    d.arc([22, 3, 42, 60], 100, 260, fill=_CH.index("d"))
    d.arc([3, 10, 60, 30], 190, 350, fill=_CH.index("d"))
    d.arc([3, 34, 60, 56], 10, 170, fill=_CH.index("x"))
    # trinchera del ecuador
    R([5, 29, c - 1, 33], "x")
    R([5, 30, c - 1, 32], "u")
    for x in range(7, c, 4):
        d.point((x, 31), fill=_CH.index("N"))
    # sensor de la corona
    R([c - 3, 2, c - 1, 5], "x")
    R([c - 2, 3, c - 1, 4], "C")
    # parabola del superlaser
    E([c - 10, 37, c + 9, 55], "x")
    E([c - 9, 38, c + 8, 54], "v")
    E([c - 7, 40, c + 6, 52], "u")
    E([c - 4, 43, c + 3, 49], "x")
    E([c - 2, 45, c + 1, 47], "e")
    d.arc([c - 9, 38, c + 8, 54], 120, 240, fill=_CH.index("N"))
    d.point((10, 26), fill=_CH.index("G"))
    return _contorno(_espejar(img))


JEFES = {
    "centinela": centinela(),
    "dragon_a": dragon(0),
    "dragon_b": dragon(1),
    "titan_px": titan(),
    "anomalia_px": anomalia(),
    "coloso_crucero": coloso_crucero(),
    "coloso_esfera": coloso_esfera(),
}


def parse(mapa):
    filas = [f for f in mapa.strip("\n").split("\n")]
    ancho = max(len(f) for f in filas)
    grilla = []
    for f in filas:
        izq = f.ljust(ancho, ".")
        der = izq[::-1].replace("G", "R")
        grilla.append(izq + der)
    return grilla


def build(mapa):
    # un str es media nave a espejar; una lista ya es el mapa completo
    grilla = parse(mapa) if isinstance(mapa, str) else mapa
    h = len(grilla) + PAD * 2
    w = len(grilla[0]) + PAD * 2
    body = np.zeros((h, w, 4), np.uint8)
    wing = np.zeros((h, w, 4), np.uint8)
    neon = np.zeros((h, w, 4), np.uint8)
    detail = np.zeros((h, w, 4), np.uint8)
    glow = np.zeros((h, w), np.float32)
    for y, fila in enumerate(grilla):
        for x, ch in enumerate(fila):
            py, px = y + PAD, x + PAD
            if ch in BODY:
                v = BODY[ch]
                body[py, px] = (v, v, v, 255)
            elif ch in WING:
                v = WING[ch]
                wing[py, px] = (v, v, v, 255)
            elif ch in NEON:
                v = NEON[ch]
                neon[py, px] = (v, v, v, 255)
            elif ch in DETAIL:
                detail[py, px] = DETAIL[ch]
            glow[py, px] = GLOW.get(ch, 0.0)

    halo = Image.fromarray((glow * 255).astype(np.uint8), "L")
    halo = halo.resize((w * GLOW_SCALE, h * GLOW_SCALE), Image.NEAREST)
    halo = halo.filter(ImageFilter.GaussianBlur(GLOW_BLUR))
    alfa = np.clip(np.asarray(halo, np.float32) * 1.6, 0, 255).astype(np.uint8)
    glow_rgba = np.zeros((h * GLOW_SCALE, w * GLOW_SCALE, 4), np.uint8)
    glow_rgba[..., :3] = 255
    glow_rgba[..., 3] = alfa

    return {
        "body": Image.fromarray(body, "RGBA"),
        "wing": Image.fromarray(wing, "RGBA"),
        "neon": Image.fromarray(neon, "RGBA"),
        "detail": Image.fromarray(detail, "RGBA"),
        "glow": Image.fromarray(glow_rgba, "RGBA"),
    }


def main():
    for carpeta, mapas in (("ships", SHIPS), ("enemies", ENEMIES), ("boss", JEFES)):
        destino = os.path.join(OUT_DIR, carpeta)
        os.makedirs(destino, exist_ok=True)
        for kind, mapa in mapas.items():
            capas = build(mapa)
            for nombre, img in capas.items():
                img.save(os.path.join(destino, f"{kind}_{nombre}.png"))
            print(f"{carpeta}/{kind}: {capas['body'].size[0]}x{capas['body'].size[1]}")


if __name__ == "__main__":
    main()
