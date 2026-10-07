"""
Extrae la animacion de un jefe bonus (Nyan Cat o el Gato Pan que gira) de
un video o GIF propio y la deja lista para el juego (ver
modules/entities/nyan_boss.py):

  - frames PNG con fondo transparente en assets/sprites/bonus/<jefe>/
  - opcionalmente copia la cancion (.mp3/.ogg/.wav) a
    assets/audio/music/musica_jefe_<jefe>.<ext>, que suena solo en la fase
    de ese jefe.

  --jefe nyan (defecto): Nyan Cat volando; se reproduce a 12 cuadros/s.
  --jefe pan: el gato girando ("OIIA OIIA"); el juego recorre los frames
      segun su angulo de giro, asi que el rango --inicio/--duracion tiene
      que abarcar UNA vuelta completa.

El fondo se quita por color: se toma el color mas comun del borde del
cuadro (el azul del cielo) y se borra todo lo parecido; despues se
descartan las manchas chicas (las estrellitas) y se recortan todos los
frames al mismo rectangulo para que la animacion no "salte".

Uso:
  python tools/extraer_nyan_video.py VIDEO [--jefe nyan|pan] [--inicio 0] [--duracion 1]
      [--frames 12] [--tolerancia 45] [--x-min 0] [--x-max 1]
      [--audio CANCION.mp3]

  --x-min/--x-max recortan el video horizontalmente ANTES de procesarlo
  (fracciones 0..1 del ancho), por ejemplo --x-min 0.45 para quedarse con
  el gato sin el arcoiris (el juego ya dibuja su propia estela).

Solo usa OpenCV y numpy (ya son dependencias del juego). pygame lee
.mp3/.ogg directamente, asi que la cancion se copia tal cual.
"""

import argparse
import glob
import os
import shutil
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_BONUS = os.path.join(ROOT, "assets", "sprites", "bonus")
CARPETA_MUSICA = os.path.join(ROOT, "assets", "audio", "music")


def leer_frames(ruta, inicio, duracion, cantidad):
    cap = cv2.VideoCapture(ruta)
    if not cap.isOpened():
        sys.exit(f"No se pudo abrir el video: {ruta}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    primero = int(inicio * fps)
    ultimo = int((inicio + duracion) * fps)
    if total:
        ultimo = min(ultimo, total - 1)
    if ultimo <= primero:
        sys.exit("El rango --inicio/--duracion no tiene frames")
    indices = sorted(set(np.linspace(primero, ultimo, cantidad, endpoint=False).astype(int)))

    frames = []
    cap.set(cv2.CAP_PROP_POS_FRAMES, primero)
    actual = primero
    pendientes = list(indices)
    while pendientes:
        ok, frame = cap.read()
        if not ok:
            break
        if actual == pendientes[0]:
            frames.append(frame)
            pendientes.pop(0)
        actual += 1
    cap.release()
    if not frames:
        sys.exit("No se pudo leer ningun frame en ese rango")
    return frames


def color_de_fondo(frame):
    """Color mas repetido en el borde del cuadro (cuantizado)."""
    borde = np.concatenate([frame[0], frame[-1], frame[:, 0], frame[:, -1]])
    cuantizado = (borde // 8).astype(np.int32)
    claves = cuantizado[:, 0] * 1024 + cuantizado[:, 1] * 32 + cuantizado[:, 2]
    valores, cuentas = np.unique(claves, return_counts=True)
    clave = valores[np.argmax(cuentas)]
    return np.array([(clave // 1024) * 8 + 4, (clave // 32 % 32) * 8 + 4, (clave % 32) * 8 + 4], dtype=np.float32)


def mascara_sin_fondo(frame, fondo, tolerancia):
    distancia = np.linalg.norm(frame.astype(np.float32) - fondo, axis=2)
    mascara = (distancia > tolerancia).astype(np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    # se queda con las manchas grandes (el gato) y tira las estrellitas
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)
    if n <= 1:
        return mascara
    areas = stats[1:, cv2.CC_STAT_AREA]
    minimo = areas.max() * 0.04
    limpia = np.zeros_like(mascara)
    for i, area in enumerate(areas, start=1):
        if area >= minimo:
            limpia[etiquetas == i] = 1
    return limpia


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video")
    parser.add_argument("--jefe", choices=("nyan", "pan"), default="nyan",
                        help="nyan = Nyan Cat, pan = el Gato Pan que gira (OIIA)")
    parser.add_argument("--inicio", type=float, default=0.0, help="segundo desde donde tomar frames")
    parser.add_argument("--duracion", type=float, default=1.0, help="segundos a recorrer (un ciclo de la animacion)")
    parser.add_argument("--frames", type=int, default=12, help="cantidad de frames a extraer")
    parser.add_argument("--tolerancia", type=float, default=45.0, help="cuanto puede diferir un pixel del fondo y seguir siendo fondo")
    parser.add_argument("--x-min", type=float, default=0.0)
    parser.add_argument("--x-max", type=float, default=1.0)
    parser.add_argument("--audio", help="cancion (.mp3/.ogg/.wav) para la fase de ese jefe")
    args = parser.parse_args()

    frames = leer_frames(args.video, args.inicio, args.duracion, args.frames)
    ancho = frames[0].shape[1]
    x0, x1 = int(ancho * args.x_min), int(ancho * args.x_max)
    frames = [f[:, x0:x1] for f in frames]

    fondo = color_de_fondo(frames[0])
    mascaras = [mascara_sin_fondo(f, fondo, args.tolerancia) for f in frames]

    # rectangulo comun a todos los frames
    union = np.zeros_like(mascaras[0])
    for m in mascaras:
        union |= m
    ys, xs = np.nonzero(union)
    if len(xs) == 0:
        sys.exit("No quedo nada despues de quitar el fondo: proba con menos --tolerancia")
    y0, y1, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

    carpeta = os.path.join(CARPETA_BONUS, args.jefe)
    os.makedirs(carpeta, exist_ok=True)
    for viejo in glob.glob(os.path.join(carpeta, "frame_*.png")):
        os.remove(viejo)
    for i, (frame, mascara) in enumerate(zip(frames, mascaras)):
        rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = mascara * 255
        cv2.imwrite(os.path.join(carpeta, f"frame_{i:02d}.png"), rgba[y0:y1, xa:xb])
    print(f"{len(frames)} frames ({xb - xa}x{y1 - y0}) guardados en {carpeta}")

    if args.audio:
        extension = os.path.splitext(args.audio)[1].lower()
        if extension not in (".mp3", ".ogg", ".wav"):
            sys.exit("El audio tiene que ser .mp3, .ogg o .wav")
        for ext in (".mp3", ".ogg"):
            anterior = os.path.join(CARPETA_MUSICA, f"musica_jefe_{args.jefe}{ext}")
            if os.path.isfile(anterior):
                os.remove(anterior)
        # .wav reemplaza al chiptune generado; .mp3/.ogg tienen prioridad sobre el
        destino = os.path.join(CARPETA_MUSICA, f"musica_jefe_{args.jefe}{extension}")
        shutil.copyfile(args.audio, destino)
        print(f"Cancion copiada a {destino}")


if __name__ == "__main__":
    main()
