"""
Integracion con MediaPipe Hand Landmarker: deteccion de la mano en cada
frame de camara, si esta cerrada en puño (dispara) y el mapeo de la
posicion de la muñeca a coordenadas del area de juego."""

import cv2
import importlib
import mediapipe as mp_module

vis = importlib.import_module('mediapipe.tasks.python.vision')
ImgFmt = importlib.import_module('mediapipe.tasks.python.vision.core.image').ImageFormat

BaseOptions = vis.core.base_options.BaseOptions if hasattr(vis, 'core') else None

try:
    from mediapipe.tasks.python.core.base_options import BaseOptions as _BaseOptions
except ImportError:
    _BaseOptions = None

HandLandmarker = vis.HandLandmarker
HandLandmarkerOptions = vis.HandLandmarkerOptions
RunningMode = vis.RunningMode

WRIST_IDX = 0
INDEX_TIP_IDX = 8
INDEX_PIP_IDX = 6
MIDDLE_TIP_IDX = 12
MIDDLE_PIP_IDX = 10
RING_TIP_IDX = 16
RING_PIP_IDX = 14
PINKY_TIP_IDX = 20
PINKY_PIP_IDX = 18

_FRAME_SKIP = 0
_LAST_FRAME_TS = 0


def get_base_options(model_path):
    if _BaseOptions is not None:
        return _BaseOptions(model_asset_path=model_path)
    return BaseOptions(model_asset_path=model_path)


def init_hand_landmarker(model_path, num_hands=1):
    """Crea el detector en modo VIDEO (usa el timestamp para tracking
    temporal entre frames, mas preciso que tratar cada uno como suelto)."""
    options = HandLandmarkerOptions(
        base_options=get_base_options(model_path),
        running_mode=RunningMode.VIDEO,
        num_hands=num_hands,
    )
    return HandLandmarker.create_from_options(options)


def set_frame_skip(skip: int):
    global _FRAME_SKIP
    _FRAME_SKIP = max(0, int(skip))


def process_camera_frame(detector, frame, timestamp_ms):
    """Detecta la mano en el frame, salvo que el frame-skip diga que hay
    que descartarlo (devuelve None en ese caso)."""
    global _LAST_FRAME_TS
    if timestamp_ms - _LAST_FRAME_TS < max(1, _FRAME_SKIP):
        return None
    _LAST_FRAME_TS = timestamp_ms
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp_module.Image(image_format=ImgFmt.SRGB, data=rgb)
    return detector.detect_for_video(mp_img, timestamp_ms)


def is_fist(hand_lm):
    """True si las puntas de los 4 dedos (indice/medio/anular/meñique)
    estan por debajo de su propia articulacion PIP: mano cerrada = puño.
    En coordenadas de imagen "y" crece hacia abajo, asi que un dedo
    extendido tiene la punta por encima del PIP (tip.y < pip.y) y un dedo
    curvado hacia la palma la tiene por debajo (tip.y > pip.y)."""
    checks = [
        (INDEX_TIP_IDX, INDEX_PIP_IDX),
        (MIDDLE_TIP_IDX, MIDDLE_PIP_IDX),
        (RING_TIP_IDX, RING_PIP_IDX),
        (PINKY_TIP_IDX, PINKY_PIP_IDX),
    ]
    for tip_idx, pip_idx in checks:
        if hand_lm[tip_idx].y <= hand_lm[pip_idx].y:
            return False
    return True


def find_hand_position(hand_lm, game_w, game_h, sensibilidad=1.0):
    """Posicion de la mano mapeada al area de juego. sensibilidad amplifica
    (>1.0) o atenua (<1.0) el desplazamiento respecto del centro: con mas
    sensibilidad, un movimiento chico de mano mueve mas la nave."""
    h_x = hand_lm[WRIST_IDX].x * game_w
    h_y = hand_lm[WRIST_IDX].y * game_h
    if sensibilidad != 1.0:
        cx, cy = game_w / 2.0, game_h / 2.0
        h_x = cx + (h_x - cx) * sensibilidad
        h_y = cy + (h_y - cy) * sensibilidad
    return h_x, h_y