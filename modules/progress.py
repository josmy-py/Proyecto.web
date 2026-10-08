"""
Progreso guardado del jugador: puntaje maximo, oleada mas alta alcanzada y
la ultima ruta bonus que salio (para no repetirla en la partida siguiente).

Mismo patron que modules/skins.py usa para los colores personalizados: un
JSON en la raiz del proyecto, tolerante a errores (si el archivo no existe,
esta corrupto o no se puede escribir, el juego sigue funcionando y solo se
pierde el registro de records).
"""

import json
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS_FILE = os.path.join(_PROJECT_ROOT, "progreso.json")

_VALORES_POR_DEFECTO = {"puntaje_maximo": 0, "oleada_maxima": 1, "ultima_ruta": ""}
_progreso = dict(_VALORES_POR_DEFECTO)


def cargar():
    """Lee progreso.json (si existe) y lo deja disponible en este modulo."""
    global _progreso
    _progreso = dict(_VALORES_POR_DEFECTO)
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as fh:
            datos = json.load(fh)
        for clave in _VALORES_POR_DEFECTO:
            if clave in datos and isinstance(datos[clave], type(_VALORES_POR_DEFECTO[clave])):
                _progreso[clave] = datos[clave]
    except (OSError, ValueError, TypeError):
        pass
    return _progreso


def guardar():
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as fh:
            json.dump(_progreso, fh)
    except OSError:
        pass


def puntaje_maximo():
    return _progreso.get("puntaje_maximo", 0)


def ultima_ruta():
    return _progreso.get("ultima_ruta", "")


def registrar_ruta(ruta):
    """Guarda la ruta bonus que acaba de salir."""
    _progreso["ultima_ruta"] = ruta
    guardar()


def registrar_partida(puntaje, oleada):
    """Actualiza y guarda los records al terminar una partida. Devuelve True
    si el puntaje de esta partida establecio un nuevo record."""
    hay_record_nuevo = puntaje > _progreso.get("puntaje_maximo", 0)
    if hay_record_nuevo:
        _progreso["puntaje_maximo"] = puntaje
    if oleada > _progreso.get("oleada_maxima", 1):
        _progreso["oleada_maxima"] = oleada
    guardar()
    return hay_record_nuevo
