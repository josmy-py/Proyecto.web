"""
Generador de audio del juego (assets/audio/*.wav).

Todo el audio se sintetiza con numpy (ondas seno/cuadrada/sierra + ruido) y se
guarda como WAV de 16 bits. No hace falta ninguna libreria de audio externa
para generarlo, solo numpy (ya es una dependencia del proyecto):

    python tools/generate_audio.py

El juego SOLO necesita pygame.mixer para reproducirlos
(modules/systems/audio.py). Si borras assets/audio/ el juego sigue
funcionando en silencio, igual que sigue funcionando sin assets/sprites.

Como los graficos, el audio esta pensado para poder retocarse facil: cambia
las notas/duraciones de las funciones generar_* y vuelve a correr el script.
"""

import math
import os
import wave

import numpy as np

SR = 44100  # muestras por segundo (calidad de CD)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(ROOT, "assets", "audio", "sfx")
MUSIC_DIR = os.path.join(ROOT, "assets", "audio", "music")

ESCALA_MENOR = [0, 2, 3, 5, 7, 8, 10]  # semitonos de la escala menor natural


# ---------------------------------------------------------------- utilidades

def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def nota_a_frecuencia(semitonos_desde_base, base_freq=440.0):
    """Frecuencia en Hz de una nota a N semitonos de base_freq."""
    return base_freq * (2.0 ** (semitonos_desde_base / 12.0))


def nota_en_escala(grado, base_freq=220.0, escala=ESCALA_MENOR):
    """Frecuencia del grado N de una escala (permite grados >= len(escala),
    sube de octava automaticamente)."""
    octava, indice = divmod(int(grado), len(escala))
    semitonos = escala[indice] + 12 * octava
    return nota_a_frecuencia(semitonos, base_freq)


def onda_seno(freq, duracion, sr=SR):
    t = np.linspace(0, duracion, int(sr * duracion), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def onda_cuadrada(freq, duracion, sr=SR, ancho_pulso=0.5):
    t = np.linspace(0, duracion, int(sr * duracion), endpoint=False)
    fase = (freq * t) % 1.0
    return np.where(fase < ancho_pulso, 1.0, -1.0)


def onda_sierra(freq, duracion, sr=SR):
    t = np.linspace(0, duracion, int(sr * duracion), endpoint=False)
    fase = (freq * t) % 1.0
    return 2.0 * fase - 1.0


def ruido_blanco(duracion, sr=SR, semilla=None):
    rng = np.random.default_rng(semilla)
    return rng.uniform(-1.0, 1.0, int(sr * duracion))


def suavizar(señal, ventana):
    """Promedio movil: funciona como un filtro pasa-bajos barato (quita el
    silbido agudo del ruido blanco y lo deja mas parecido a una explosion)."""
    if ventana <= 1:
        return señal
    kernel = np.ones(ventana) / ventana
    return np.convolve(señal, kernel, mode="same")


def deslizar_frecuencia(freq_inicial, freq_final, duracion, sr=SR, forma="sine"):
    """Como onda_seno/onda_cuadrada pero la frecuencia cambia linealmente en
    el tiempo (para el efecto de laser bajando de tono)."""
    n = int(sr * duracion)
    t = np.linspace(0, duracion, n, endpoint=False)
    freq_t = np.linspace(freq_inicial, freq_final, n)
    fase = 2 * np.pi * np.cumsum(freq_t) / sr
    if forma == "square":
        return np.where(np.sin(fase) >= 0, 1.0, -1.0)
    return np.sin(fase)


def envolvente(n, ataque=0.01, caida=0.2, sr=SR):
    """Amplitud que sube en `ataque` segundos y luego decae exponencialmente
    en `caida` segundos (asi cada sonido empieza y termina en silencio, sin
    "clicks", y las pistas de musica hacen loop sin sonar cortadas)."""
    env = np.ones(n)
    n_ataque = min(n, max(1, int(ataque * sr)))
    env[:n_ataque] = np.linspace(0, 1, n_ataque)
    t = np.arange(n) / sr
    env *= np.exp(-t / max(caida, 0.001))
    return env


def normalizar(señal, pico=0.9):
    maximo = np.max(np.abs(señal)) if len(señal) else 0
    if maximo < 1e-9:
        return señal
    return señal / maximo * pico


def fundido_de_bucle(señal, ms=25, sr=SR):
    """Fuerza el inicio y el final del arreglo a silencio (fundido lineal
    de `ms` milisegundos en cada punta). Sin esto, la union entre el final
    y el reinicio de una pista en loop suena como un "clic" perceptible,
    porque el volumen de la ultima nota casi nunca cae exactamente a 0
    justo en la ultima muestra del archivo."""
    n_fundido = min(int(sr * ms / 1000), len(señal) // 2)
    if n_fundido <= 0:
        return señal
    señal = señal.copy()
    señal[:n_fundido] *= np.linspace(0.0, 1.0, n_fundido)
    señal[-n_fundido:] *= np.linspace(1.0, 0.0, n_fundido)
    return señal


def guardar_wav(path, señal, sr=SR):
    _ensure_dir(os.path.dirname(path))
    señal = np.clip(señal, -1.0, 1.0)
    datos = (señal * 32767).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(datos.tobytes())


def construir_patron(grados, duracion_nota, onda_fn, base_freq, ataque=0.01, caida=None, volumen=1.0):
    """Concatena una nota por cada grado de la lista (None = silencio).
    Cada nota lleva su propia envolvente, por eso se pueden pegar una tras
    otra sin que se escuche un click en la union."""
    caida = caida if caida is not None else duracion_nota * 0.9
    trozos = []
    n = int(SR * duracion_nota)
    for grado in grados:
        if grado is None:
            trozos.append(np.zeros(n))
            continue
        freq = nota_en_escala(grado, base_freq)
        trozo = onda_fn(freq, duracion_nota) * envolvente(n, ataque, caida)
        trozos.append(trozo * volumen)
    return np.concatenate(trozos) if trozos else np.zeros(0)


# ------------------------------------------------------------- efectos (sfx)

def generar_disparo():
    """Laser corto bajando de tono, como el disparo clasico de nave arcade."""
    dur = 0.12
    n = int(SR * dur)
    onda = deslizar_frecuencia(1100, 250, dur, forma="square") * 0.6
    onda += onda_seno(250, dur) * 0.2
    onda *= envolvente(n, ataque=0.002, caida=0.05)
    return normalizar(onda, 0.7)


def generar_explosion():
    """Estallido de asteroide/nave: ruido filtrado + golpe grave al inicio."""
    dur = 0.5
    n = int(SR * dur)
    ruido = suavizar(ruido_blanco(dur, semilla=1), 6)
    golpe = onda_seno(90, dur) * np.exp(-np.arange(n) / SR / 0.08)
    onda = ruido * 0.8 + golpe * 0.6
    onda *= envolvente(n, ataque=0.001, caida=0.22)
    return normalizar(onda, 0.85)


def generar_impacto():
    """Golpe corto y grave: cuando el jugador recibe daño."""
    dur = 0.28
    n = int(SR * dur)
    golpe = onda_seno(140, dur)
    ruido = suavizar(ruido_blanco(dur, semilla=2), 4) * 0.5
    onda = golpe * 0.7 + ruido
    onda *= envolvente(n, ataque=0.001, caida=0.09)
    return normalizar(onda, 0.85)


def generar_powerup():
    """Arpegio ascendente alegre: al recoger un power-up."""
    onda = construir_patron([0, 4, 7, 12], 0.09, onda_cuadrada, base_freq=220.0,
                             ataque=0.002, caida=0.07, volumen=1.0)
    return normalizar(onda, 0.7)


def generar_boton():
    """Click corto de interfaz."""
    dur = 0.045
    n = int(SR * dur)
    onda = onda_cuadrada(1800, dur) * 0.5 + suavizar(ruido_blanco(dur, semilla=3), 2) * 0.3
    onda *= envolvente(n, ataque=0.001, caida=0.02)
    return normalizar(onda, 0.5)


def generar_alerta_jefe():
    """Aviso grave y repetitivo de que aparecio un jefe."""
    notas = [-12, -12, -5, -12]
    trozos = []
    for grado in notas:
        freq = nota_a_frecuencia(grado, base_freq=220.0)
        dur = 0.28
        n = int(SR * dur)
        onda = onda_sierra(freq, dur) * 0.5 + onda_sierra(freq * 1.005, dur) * 0.5
        onda *= envolvente(n, ataque=0.01, caida=0.22)
        trozos.append(onda)
        trozos.append(np.zeros(int(SR * 0.02)))
    return normalizar(np.concatenate(trozos), 0.8)


def generar_victoria():
    """Fanfarria corta ascendente: jefe derrotado / partida ganada."""
    onda = construir_patron([0, 4, 7, 12, 16], 0.16, onda_cuadrada, base_freq=261.63,
                             ataque=0.005, caida=0.14, volumen=0.85)
    onda += construir_patron([0, 4, 7, 12, 16], 0.16, onda_seno, base_freq=261.63,
                              ataque=0.005, caida=0.14, volumen=0.35)
    return normalizar(onda, 0.85)


# --------------------------------------------------------------- percusion

def _golpe_percusion(tipo, duracion_slot):
    n = int(SR * duracion_slot)
    t = np.arange(n) / SR
    if tipo == "kick":
        onda = np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.09)
    elif tipo == "hat":
        onda = suavizar(ruido_blanco(duracion_slot, semilla=None), 2) * np.exp(-t / 0.03)
    else:
        onda = np.zeros(n)
    return onda


def construir_percusion(patron, duracion_slot):
    """patron: lista de 'kick' / 'hat' / None, un elemento por slot."""
    return np.concatenate([_golpe_percusion(p, duracion_slot) for p in patron])


# ------------------------------------------------------------------ musica
#
# Ambas pistas se arman pegando notas de duracion fija (nunca un oscilador
# continuo de principio a fin), y cada nota entra y sale en silencio gracias
# a `envolvente()`. Por eso el archivo hace loop limpio: el final ya esta en
# silencio cuando pygame.mixer.music vuelve a empezar desde el principio.

def generar_musica_juego():
    """Pista energica para el gameplay: bajo + arpegio + percusion simple."""
    slot = 0.25  # duracion de una corchea
    grados_bajo = [0, 0, 3, 3, 4, 4, 2, 2]  # 8 compases de 1s = 8s de loop
    bajo = construir_patron(grados_bajo, slot * 4, onda_cuadrada, base_freq=110.0,
                             ataque=0.01, caida=slot * 3.5, volumen=0.5)

    # el arpegio sigue el acorde de cada nota del bajo (root, 3ra, 5ta, 3ra)
    grados_lead = []
    for grado in grados_bajo:
        grados_lead.extend([grado, grado + 2, grado + 4, grado + 2])
    lead = construir_patron(grados_lead, slot, onda_cuadrada, base_freq=440.0,
                             ataque=0.005, caida=slot * 0.8, volumen=0.32)

    patron_percusion = ["kick" if i % 4 == 0 else "hat" if i % 4 == 2 else None
                         for i in range(32)]
    percusion = construir_percusion(patron_percusion, slot) * 0.4

    n = min(len(bajo), len(lead), len(percusion))
    mezcla = bajo[:n] + lead[:n] + percusion[:n]
    mezcla = fundido_de_bucle(mezcla)
    return normalizar(mezcla, 0.8)


def generar_musica_menu():
    """Pista calma y ambiental para el menu: acordes largos, sin percusion."""
    slot = 0.4

    def pad(freq, dur):
        # dos senos ligeramente desafinados entre si -> sonido "calido"
        return onda_seno(freq, dur) * 0.6 + onda_seno(freq * 1.003, dur) * 0.4

    grados_bajo = [0, 0, 5, 5, 3, 3, 4, 4]
    bajo = construir_patron(grados_bajo, slot * 4, pad, base_freq=110.0,
                             ataque=0.4, caida=slot * 3.2, volumen=0.5)

    grados_lead = []
    for grado in grados_bajo:
        grados_lead.extend([grado + 7, None, grado + 9, None])
    lead = construir_patron(grados_lead, slot, onda_seno, base_freq=440.0,
                             ataque=0.05, caida=slot * 0.9, volumen=0.3)

    n = min(len(bajo), len(lead))
    mezcla = bajo[:n] + lead[:n]
    mezcla = fundido_de_bucle(mezcla)
    return normalizar(mezcla, 0.75)


def generar_musica_muerte():
    """Tema de "Game Over" al estilo de los juegos de pelea arcade clasicos:
    un golpe grave de entrada, una caida melodica dramatica en tono menor y
    un acorde final sostenido y oscuro. Se reproduce una sola vez (sin loop),
    reemplazando a la musica del juego en el momento en que el jugador muere.
    """
    # 1) golpe de impacto inicial (como un gong/tambor grave)
    dur_golpe = 0.9
    n_golpe = int(SR * dur_golpe)
    t_golpe = np.arange(n_golpe) / SR
    golpe = (np.sin(2 * np.pi * 55 * t_golpe) * 0.7 + np.sin(2 * np.pi * 82 * t_golpe) * 0.3)
    golpe *= np.exp(-t_golpe / 0.35)
    golpe += suavizar(ruido_blanco(dur_golpe, semilla=7), 8) * np.exp(-t_golpe / 0.12) * 0.5

    # 2) caida melodica dramatica (sierra desafinada = sonido "oscuro")
    def sierra_oscura(freq, dur):
        return onda_sierra(freq, dur) * 0.5 + onda_sierra(freq * 0.997, dur) * 0.5

    caida = construir_patron([7, 5, 3, 0], 0.42, sierra_oscura, base_freq=196.0,
                              ataque=0.01, caida=0.32, volumen=0.75)

    # 3) acorde final sostenido, grave y oscuro (tonica menor)
    dur_final = 1.6
    n_final = int(SR * dur_final)
    fundamental = nota_en_escala(0, base_freq=98.0)
    quinta = nota_en_escala(4, base_freq=98.0)
    final = onda_seno(fundamental, dur_final) * 0.6 + onda_seno(quinta, dur_final) * 0.4
    final *= envolvente(n_final, ataque=0.05, caida=1.1)

    # el golpe suena debajo del arranque de la caida; el acorde final entra justo despues
    largo_total = len(caida) + len(final)
    pista = np.zeros(largo_total)
    pista[:len(golpe)] += golpe * 0.8
    pista[:len(caida)] += caida
    pista[len(caida):len(caida) + len(final)] += final

    pista = fundido_de_bucle(pista, ms=15)
    return normalizar(pista, 0.9)


# ----------------------------------------------------------------- ejecucion

SFX = {
    "disparo": generar_disparo,
    "explosion": generar_explosion,
    "impacto": generar_impacto,
    "powerup": generar_powerup,
    "boton": generar_boton,
    "alerta_jefe": generar_alerta_jefe,
    "victoria": generar_victoria,
}

MUSICA = {
    "musica_juego": generar_musica_juego,
    "musica_menu": generar_musica_menu,
    "musica_muerte": generar_musica_muerte,
}



def generate_all(verbose=True):
    _ensure_dir(SFX_DIR)
    _ensure_dir(MUSIC_DIR)
    escritos = []

    for nombre, generador in SFX.items():
        ruta = os.path.join(SFX_DIR, f"{nombre}.wav")
        guardar_wav(ruta, generador())
        escritos.append(ruta)

    for nombre, generador in MUSICA.items():
        ruta = os.path.join(MUSIC_DIR, f"{nombre}.wav")
        guardar_wav(ruta, generador())
        escritos.append(ruta)

    if verbose:
        print(f"{len(escritos)} archivos de audio generados en {os.path.join(ROOT, 'assets', 'audio')}")
    return escritos


if __name__ == "__main__":
    generate_all()
