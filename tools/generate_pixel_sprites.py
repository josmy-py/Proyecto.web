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
from PIL import Image, ImageFilter

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


JEFES = {"centinela": centinela()}


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
