"""
Genera las naves del jugador en pixel art neon (assets/sprites/ships/).

Cada nave se dibuja a mano como un mapa de caracteres (solo la mitad
izquierda; la derecha se obtiene en espejo) sobre una grilla chica. De ese
mapa salen cinco PNG por clase:

  <clase>_body.png    casco en escala de grises (se tinta con el color de casco)
  <clase>_wing.png    alas en escala de grises (se tinta con el color de alas)
  <clase>_neon.png    lineas neon en blanco (se tinta con el color de alas
                      aclarado, para que brillen mas que el resto)
  <clase>_detail.png  contorno, cabina, toberas y luces (no se tinta)
  <clase>_glow.png    halo suave de las lineas neon y toberas, a 4x de
                      resolucion (se tinta con el color de alas y va debajo)

body/wing/neon/detail quedan a la resolucion de la grilla: el juego los agranda
sin suavizar (pixeles en bloque, ver sprites.get_ship_surface).

Uso:  python tools/generate_pixel_ships.py
"""

import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "sprites", "ships")

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

BODY = {"B": 235, "b": 172, "d": 112}
WING = {"W": 200, "w": 140, "v": 88}
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


def parse(mapa):
    filas = [f for f in mapa.strip("\n").split("\n")]
    ancho = max(len(f) for f in filas)
    grilla = []
    for f in filas:
        izq = f.ljust(ancho, ".")
        der = izq[::-1].replace("G", "R")
        grilla.append(izq + der)
    return grilla


def build(kind):
    grilla = parse(SHIPS[kind])
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
    os.makedirs(OUT_DIR, exist_ok=True)
    for kind in SHIPS:
        capas = build(kind)
        for nombre, img in capas.items():
            img.save(os.path.join(OUT_DIR, f"{kind}_{nombre}.png"))
        print(f"{kind}: {capas['body'].size[0]}x{capas['body'].size[1]}")


if __name__ == "__main__":
    main()
