"""
Aspectos (colores) de cada clase de nave: 4 predefinidos por clase mas un
aspecto "custom" con el color que elija el jugador, persistido en
custom_skins.json. La nave siempre arranca con el aspecto "default" (ya no
hay pantalla de menu para elegir otro), pero el sistema sigue funcionando
si algo lo pide con otro skin_id."""

import json
import os

from modules.constants import (
    AZUL, AZUL_CIELO, MELON, ROSA, ROSA_CHICLE, LAVANDA,
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_COLORS_FILE = os.path.join(_PROJECT_ROOT, "custom_skins.json")

DEFAULT_CUSTOM_COLOR = {
    "scout": AZUL,
    "tank": MELON,
    "interceptor": LAVANDA,
    "bomber": ROSA,
}

CUSTOM_COLORS = {}


def load_custom_colors():
    """Recupera los colores personalizados guardados en la partida anterior."""
    CUSTOM_COLORS.clear()
    try:
        with open(CUSTOM_COLORS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for ship_type, rgb in data.items():
            if isinstance(rgb, (list, tuple)) and len(rgb) >= 3:
                CUSTOM_COLORS[ship_type] = tuple(
                    max(0, min(255, int(c))) for c in rgb[:3]
                )
    except (OSError, ValueError, TypeError):
        pass
    return CUSTOM_COLORS


def save_custom_colors():
    """Guarda los colores personalizados en disco (silencioso si falla)."""
    try:
        with open(CUSTOM_COLORS_FILE, "w", encoding="utf-8") as fh:
            json.dump({k: list(v) for k, v in CUSTOM_COLORS.items()}, fh, indent=2)
        return True
    except OSError:
        return False


def set_custom_color(ship_type, rgb, persist=False):
    """Fija el color personalizado de una clase de nave.

    persist=False mientras se arrastra el selector (barato, solo memoria),
    persist=True al confirmar para que sobreviva al cierre del juego.
    """
    CUSTOM_COLORS[ship_type] = tuple(max(0, min(255, int(c))) for c in rgb[:3])
    if persist:
        save_custom_colors()
    return CUSTOM_COLORS[ship_type]


def get_custom_color(ship_type):
    return CUSTOM_COLORS.get(ship_type, DEFAULT_CUSTOM_COLOR.get(ship_type, AZUL))


SHIP_SKINS = {
    "scout": {
        "default": {
            "name": "Explorador",
            "body_color": AZUL,
            "wing_color": AZUL_CIELO,
            "glow_color": (140, 210, 255),
            "flame_color": AZUL,
        },
        "neon": {
            "name": "Neon",
            "body_color": (0, 255, 200),
            "wing_color": (0, 180, 255),
            "glow_color": (0, 255, 220),
            "flame_color": (0, 255, 180),
        },
        "arctic": {
            "name": "Artico",
            "body_color": (200, 230, 255),
            "wing_color": (160, 200, 240),
            "glow_color": (220, 245, 255),
            "flame_color": (180, 220, 255),
        },
        "camo": {
            "name": "Camuflaje",
            "body_color": (90, 130, 90),
            "wing_color": (70, 110, 70),
            "glow_color": (110, 150, 110),
            "flame_color": (100, 160, 100),
        },
    },
    "tank": {
        "default": {
            "name": "Tanque",
            "body_color": MELON,
            "wing_color": (200, 140, 100),
            "glow_color": (255, 190, 140),
            "flame_color": MELON,
        },
        "desert": {
            "name": "Desierto",
            "body_color": (210, 180, 120),
            "wing_color": (180, 150, 90),
            "glow_color": (230, 200, 140),
            "flame_color": (220, 190, 110),
        },
        "magma": {
            "name": "Magma",
            "body_color": (255, 100, 30),
            "wing_color": (220, 80, 20),
            "glow_color": (255, 140, 50),
            "flame_color": (255, 120, 40),
        },
        "golden": {
            "name": "Dorado",
            "body_color": (255, 215, 0),
            "wing_color": (200, 170, 0),
            "glow_color": (255, 230, 80),
            "flame_color": (255, 220, 60),
        },
    },
    "interceptor": {
        "default": {
            "name": "Interceptor",
            "body_color": LAVANDA,
            "wing_color": ROSA_CHICLE,
            "glow_color": (200, 150, 255),
            "flame_color": LAVANDA,
        },
        "cosmic": {
            "name": "Cosmico",
            "body_color": (140, 80, 255),
            "wing_color": (100, 50, 220),
            "glow_color": (160, 100, 255),
            "flame_color": (130, 90, 255),
        },
        "shadow": {
            "name": "Sombra",
            "body_color": (60, 60, 80),
            "wing_color": (40, 40, 60),
            "glow_color": (100, 100, 130),
            "flame_color": (80, 80, 110),
        },
        "neon_purple": {
            "name": "Neon Purpura",
            "body_color": (200, 100, 255),
            "wing_color": (180, 60, 240),
            "glow_color": (220, 120, 255),
            "flame_color": (210, 90, 255),
        },
    },
    "bomber": {
        "default": {
            "name": "Bombardero",
            "body_color": ROSA,
            "wing_color": (200, 100, 120),
            "glow_color": (255, 130, 150),
            "flame_color": ROSA,
        },
        "inferno": {
            "name": "Infierno",
            "body_color": (255, 60, 60),
            "wing_color": (220, 40, 40),
            "glow_color": (255, 100, 100),
            "flame_color": (255, 80, 50),
        },
        "rose": {
            "name": "Rosa",
            "body_color": (255, 182, 193),
            "wing_color": (240, 150, 170),
            "glow_color": (255, 200, 210),
            "flame_color": (255, 190, 200),
        },
        "blood": {
            "name": "Sangre",
            "body_color": (120, 20, 20),
            "wing_color": (90, 10, 10),
            "glow_color": (160, 40, 40),
            "flame_color": (140, 30, 30),
        },
    },
}


def _shade(color, delta):
    """Aclara (delta > 0) u oscurece (delta < 0) un color, canal por canal."""
    return tuple(max(0, min(255, int(c) + delta)) for c in color[:3])


def normalize_skin(skin, fallback_body=AZUL):
    """Completa las claves de color que falten a partir del color de casco."""
    body = tuple(skin.get("body_color", fallback_body))[:3]
    return {
        "name": skin.get("name", "Skin"),
        "body_color": body,
        "wing_color": tuple(skin.get("wing_color", _shade(body, -45)))[:3],
        "glow_color": tuple(skin.get("glow_color", _shade(body, 40)))[:3],
        "flame_color": tuple(skin.get("flame_color", body))[:3],
    }


def get_available_skins(ship_type):
    """Todos los aspectos de esa clase (los predefinidos de SHIP_SKINS mas
    "custom")."""
    skins = dict(SHIP_SKINS.get(ship_type, SHIP_SKINS["scout"]))
    if "custom" not in skins:
        skins["custom"] = {"name": "Personalizado"}
    return skins


def get_skin_data(ship_type, skin_id):
    """Datos completos (name + 4 colores) del aspecto pedido, resolviendo
    "custom" con el ultimo color guardado en custom_skins.json."""
    if skin_id == "custom":
        return create_custom_skin(ship_type, get_custom_color(ship_type))
    skins = get_available_skins(ship_type)
    data = skins.get(skin_id) or skins["default"]
    if "body_color" not in data:
        return create_custom_skin(ship_type, get_custom_color(ship_type))
    return normalize_skin(data)


def get_skin_colors(ship_type, skin_id):
    """(body, wing, glow, flame) listos para tintar el sprite."""
    skin = get_skin_data(ship_type, skin_id)
    return (
        skin["body_color"],
        skin["wing_color"],
        skin["glow_color"],
        skin["flame_color"],
    )


def apply_skin_to_ship(ship, skin_id):
    """Pinta la nave con ese aspecto e invalida su sprite cacheado para que
    se recomponga con los colores nuevos en el siguiente draw()."""
    skin = get_skin_data(ship.ship_type, skin_id)
    ship.skin_id = skin_id
    ship.skin_name = skin["name"]
    ship.body_color = skin["body_color"]
    ship.wing_color = skin["wing_color"]
    ship.glow_color = skin["glow_color"]
    ship.flame_color = skin["flame_color"]
    # el sprite cacheado deja de ser valido en cuanto cambian los colores
    invalidate = getattr(ship, "invalidate_sprite", None)
    if callable(invalidate):
        invalidate()


def create_custom_skin(ship_type, body_color):
    """Deriva alas/glow/llama de un unico color de casco elegido a mano."""
    body = tuple(max(0, min(255, int(c))) for c in body_color[:3])
    return {
        "name": "Personalizado",
        "body_color": body,
        "wing_color": tuple(int(c * 0.62) for c in body),
        "glow_color": _shade(body, 55),
        "flame_color": _shade(body, 20),
    }


load_custom_colors()
