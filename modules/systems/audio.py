"""
Reproduccion de audio (efectos de sonido y musica) via pygame.mixer.

Sigue la misma filosofia que modules/systems/sprites.py: si el mixer no
puede inicializarse (sin tarjeta de sonido, sin drivers, etc.) o faltan los
archivos en assets/audio/, el juego sigue funcionando en silencio. Ninguna
funcion de este modulo lanza una excepcion que interrumpa una partida.

Regenerar los WAV:  python tools/generate_audio.py
"""

import os

import pygame

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
SFX_DIR = os.path.join(PROJECT_ROOT, "assets", "audio", "sfx")
MUSIC_DIR = os.path.join(PROJECT_ROOT, "assets", "audio", "music")

_NOMBRES_SFX = (
    "disparo", "explosion", "impacto", "powerup",
    "boton", "alerta_jefe", "victoria",
)

_habilitado = False
_sonidos = {}
_volumen_sfx = 0.6
_volumen_musica = 0.5
# ganancia extra de la pista que esta sonando (ver reproducir_musica)
_ganancia_pista = 1.0
_pista_actual = None
_silenciado = False


def inicializar():
    """Prepara pygame.mixer y precarga los efectos. Seguro de llamar mas de
    una vez (por ejemplo, si el menu y el main la llaman ambos)."""
    global _habilitado
    if _habilitado:
        return True
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        _habilitado = True
    except pygame.error:
        _habilitado = False
        return False

    for nombre in _NOMBRES_SFX:
        ruta = os.path.join(SFX_DIR, f"{nombre}.wav")
        if os.path.isfile(ruta):
            try:
                _sonidos[nombre] = pygame.mixer.Sound(ruta)
            except pygame.error:
                pass
    return True


def _reproducir(nombre):
    if not _habilitado or _silenciado:
        return
    sonido = _sonidos.get(nombre)
    if sonido is not None:
        sonido.set_volume(_volumen_sfx)
        sonido.play()


def sonido_disparo():
    _reproducir("disparo")


def sonido_explosion():
    _reproducir("explosion")


def sonido_impacto():
    _reproducir("impacto")


def sonido_powerup():
    _reproducir("powerup")


def sonido_boton():
    _reproducir("boton")


def sonido_alerta_jefe():
    _reproducir("alerta_jefe")


def sonido_victoria():
    _reproducir("victoria")


# Canciones propias que se reconocen solas por el nombre del archivo (sin
# mayusculas ni signos), dejandolas tal cual en assets/audio/music: por
# ejemplo "OIIA OIIA (Spinning Cat).mp3" suena al aparecer el Gato Pan.
_PALABRAS_CANCION_PROPIA = {
    "jefe_pan": ("oiia", "spinningcat"),
    "jefe_nyan": ("nyan",),
    "impostor": ("amongus", "impostor"),
    # final de la ruta cyberpunk (la Luna)
    "luna": ("stayatyourhouse", "ireallywanttostay", "edgerunners"),
}
_EXTENSIONES_PROPIAS = (".ogg", ".mp3", ".wav")


def _ruta_musica(nombre):
    """Archivo a reproducir para la pista `nombre`, en este orden:
      1. musica_<nombre>.ogg / .mp3 (cancion propia con el nombre exacto)
      2. cualquier .ogg/.mp3/.wav de MUSIC_DIR cuyo nombre contenga una de
         las palabras de _PALABRAS_CANCION_PROPIA[nombre]
      3. musica_<nombre>.wav (el tema generado por tools/generate_audio.py)"""
    for extension in (".ogg", ".mp3"):
        candidata = os.path.join(MUSIC_DIR, f"musica_{nombre}{extension}")
        if os.path.isfile(candidata):
            return candidata

    palabras = _PALABRAS_CANCION_PROPIA.get(nombre, ())
    if palabras and os.path.isdir(MUSIC_DIR):
        for archivo in sorted(os.listdir(MUSIC_DIR)):
            base, extension = os.path.splitext(archivo)
            if extension.lower() not in _EXTENSIONES_PROPIAS or base.startswith("musica_"):
                continue
            simple = "".join(c for c in base.lower() if c.isalnum())
            if any(p in simple for p in palabras):
                return os.path.join(MUSIC_DIR, archivo)

    generada = os.path.join(MUSIC_DIR, f"musica_{nombre}.wav")
    return generada if os.path.isfile(generada) else None


def _volumen_efectivo():
    return min(1.0, _volumen_musica * _ganancia_pista)


def reproducir_musica(nombre, loop=True, ganancia=1.0):
    """nombre: 'menu', 'juego' o 'muerte'. No hace nada si esa pista ya esta
    sonando, asi se puede llamar en cada frame sin reiniciar la cancion.
    loop=False se usa para el tema de derrota, que suena una sola vez.
    ganancia multiplica el volumen de musica solo mientras suene esta pista
    (la VICTORIA falsa la usa para sonar mas fuerte), sin tocar el ajuste."""
    global _pista_actual, _ganancia_pista
    if not _habilitado or _pista_actual == nombre:
        return
    ruta = _ruta_musica(nombre)
    if ruta is None:
        return
    try:
        pygame.mixer.music.load(ruta)
        _ganancia_pista = ganancia
        pygame.mixer.music.set_volume(0.0 if _silenciado else _volumen_efectivo())
        pygame.mixer.music.play(loops=-1 if loop else 0)
        _pista_actual = nombre
    except pygame.error:
        pass


def detener_musica():
    global _pista_actual
    if _habilitado:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
    _pista_actual = None


def pausar_musica():
    if _habilitado:
        try:
            pygame.mixer.music.pause()
        except pygame.error:
            pass


def reanudar_musica():
    if _habilitado and not _silenciado:
        try:
            pygame.mixer.music.unpause()
        except pygame.error:
            pass


def set_volumen_sfx(valor):
    global _volumen_sfx
    _volumen_sfx = max(0.0, min(1.0, valor))


def set_volumen_musica(valor):
    global _volumen_musica
    _volumen_musica = max(0.0, min(1.0, valor))
    if _habilitado and not _silenciado:
        try:
            pygame.mixer.music.set_volume(_volumen_efectivo())
        except pygame.error:
            pass


def alternar_silencio():
    """Silencia/reactiva musica y efectos. Devuelve el nuevo estado (True = silenciado)."""
    global _silenciado
    _silenciado = not _silenciado
    if _habilitado:
        try:
            pygame.mixer.music.set_volume(0.0 if _silenciado else _volumen_efectivo())
        except pygame.error:
            pass
    return _silenciado


def esta_silenciado():
    return _silenciado
