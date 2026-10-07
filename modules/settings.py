"""
Ajustes del jugador (volumen de musica/efectos, silenciado, pantalla
completa) guardados en disco. Mismo patron tolerante a errores que
modules/progress.py y modules/skins.py: si el archivo no existe, esta
corrupto o no se puede escribir, el juego sigue funcionando con los
valores por defecto.
"""

import json
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(_PROJECT_ROOT, "ajustes.json")

_VALORES_POR_DEFECTO = {
    "volumen_musica": 0.5,
    "volumen_sfx": 0.6,
    "silenciado": False,
    "pantalla_completa": True,
    "sensibilidad_mano": 1.0,
    "camera_index": 0,
    # Jefe bonus (Nyan Cat): arrancar la pelea con todos los buffs activos
    "bonus_todos_buffs": False,
    # ELEGIR FASE: arrancar la partida elegida con todos los buffs activos
    "fase_todos_buffs": False,
}
_ajustes = dict(_VALORES_POR_DEFECTO)


def cargar():
    """Lee ajustes.json (si existe) y lo deja disponible en este modulo."""
    global _ajustes
    _ajustes = dict(_VALORES_POR_DEFECTO)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            datos = json.load(fh)
        for clave, valor_defecto in _VALORES_POR_DEFECTO.items():
            if clave in datos and isinstance(datos[clave], type(valor_defecto)):
                _ajustes[clave] = datos[clave]
    except (OSError, ValueError, TypeError):
        pass
    return _ajustes


def guardar():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(_ajustes, fh)
    except OSError:
        pass


def get(clave):
    return _ajustes.get(clave, _VALORES_POR_DEFECTO.get(clave))


def set_valor(clave, valor):
    _ajustes[clave] = valor
    guardar()
