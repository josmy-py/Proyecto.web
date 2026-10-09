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


def generar_musica_jefe_nyan():
    """Jefe bonus pixel art (Nyan Cat y su pandilla): chiptune alegre en
    tonalidad MAYOR y rapido -melodia de pulso angosto arpegiando cada
    acorde, bajo de onda cuadrada saltando de octava- para que el cambio a
    "entorno pixel" se escuche tanto como se ve, en contraste con los
    temas oscuros (escala menor) del resto de los jefes."""
    slot = 0.13

    def notas(semitonos, onda_fn, base_freq, caida, volumen):
        n = int(SR * slot)
        trozos = []
        for semi in semitonos:
            if semi is None:
                trozos.append(np.zeros(n))
                continue
            freq = nota_a_frecuencia(semi, base_freq)
            trozos.append(onda_fn(freq, slot) * envolvente(n, 0.004, caida) * volumen)
        return np.concatenate(trozos)

    # I I IV V vi IV V V, 8 corcheas por acorde
    acordes = [(0, 4), (0, 4), (5, 4), (7, 4), (9, 3), (5, 4), (7, 4), (7, 4)]
    semis_bajo = []
    semis_lead = []
    for raiz, tercera in acordes:
        semis_bajo.extend([raiz, raiz + 12] * 4)
        tonos = [raiz, raiz + tercera, raiz + 7, raiz + 12]
        semis_lead.extend(tonos[i] if i is not None else None for i in (0, 1, 2, 3, 2, 1, None, 2))

    bajo = notas(semis_bajo, onda_cuadrada, 110.0, slot * 0.8, 0.45)
    lead = notas(semis_lead, lambda f, d: onda_cuadrada(f, d, ancho_pulso=0.25), 440.0, slot * 0.7, 0.3)
    patron_percusion = ["kick" if i % 4 == 0 else "hat" if i % 2 == 0 else None
                         for i in range(len(semis_bajo))]
    percusion = construir_percusion(patron_percusion, slot) * 0.4

    n = min(len(bajo), len(lead), len(percusion))
    mezcla = bajo[:n] + lead[:n] + percusion[:n]
    mezcla = fundido_de_bucle(mezcla)
    return normalizar(mezcla, 0.8)


def generar_musica_jefe_pan():
    """Gato Pan (el gato que gira, ultimo jefe bonus): tema de respaldo si
    no se agrego una cancion propia (musica_jefe_pan.mp3/.ogg). Cada golpe
    del lead es un "oi-ia": un deslizamiento de tono que sube y vuelve a
    bajar, como una voz cantando mientras el gato da vueltas, sobre un bajo
    saltarin en tonalidad mayor."""
    slot = 0.15
    trozos = []
    for i in range(32):
        base = 330.0 if (i // 8) % 2 == 0 else 392.0
        if i % 4 == 3:
            trozos.append(np.zeros(int(SR * slot * 2)))
            continue
        # "oi" (sube) + "ia" (sube mas y cae)
        oi = deslizar_frecuencia(base, base * 1.5, slot, forma="square")
        ia = deslizar_frecuencia(base * 1.68, base * 1.12, slot, forma="square")
        n = len(oi)
        trozos.append(oi * envolvente(n, 0.004, slot * 0.9) * 0.3)
        trozos.append(ia * envolvente(n, 0.004, slot * 0.9) * 0.3)
    lead = np.concatenate(trozos)

    n_slot = int(SR * slot)
    bajo = []
    for i in range(len(lead) // n_slot):
        raiz = 0 if (i // 16) % 2 == 0 else 5
        semi = raiz + (12 if i % 2 else 0)
        bajo.append(onda_cuadrada(nota_a_frecuencia(semi, 110.0), slot) * envolvente(n_slot, 0.004, slot * 0.7) * 0.4)
    bajo = np.concatenate(bajo)
    patron = ["kick" if i % 4 == 0 else "hat" if i % 2 == 0 else None for i in range(len(lead) // n_slot)]
    percusion = construir_percusion(patron, slot) * 0.4

    n = min(len(bajo), len(lead), len(percusion))
    mezcla = bajo[:n] + lead[:n] + percusion[:n]
    mezcla = fundido_de_bucle(mezcla)
    return normalizar(mezcla, 0.8)


def generar_musica_cuna():
    """Cinematica final (el gatito se duerme): la "Cancion de cuna" de
    Brahms (Wiegenlied, 1868, dominio publico) como caja de musica -seno
    con un armonico agudo y caida de campanita- sobre un colchon suave de
    fundamentales."""
    pulso = 0.42
    # (semitonos desde Do4, duracion en pulsos)
    melodia = [
        (4, .5), (4, .5), (7, 2),
        (4, .5), (4, .5), (7, 2),
        (4, .5), (7, .5), (12, 1), (11, 1.5), (9, .5), (9, 1), (7, 1),
        (2, .5), (4, .5), (5, 1), (2, 1), (2, .5), (4, .5), (5, 2),
        (2, .5), (5, .5), (11, .5), (9, .5), (7, 1), (11, 1), (12, 3),
    ]

    def campanita(freq, dur):
        return onda_seno(freq, dur) * 0.8 + onda_seno(freq * 2, dur) * 0.2

    trozos = []
    for semi, pulsos in melodia:
        dur = pulso * pulsos
        n = int(SR * dur)
        trozos.append(campanita(nota_a_frecuencia(semi, 523.25), dur) * envolvente(n, 0.004, 0.45) * 0.5)
    lead = np.concatenate(trozos)

    # acompañamiento: Do / Sol alternados, muy suave
    n_acorde = int(SR * pulso * 3)
    acomp = []
    for i in range(len(lead) // n_acorde + 1):
        raiz = 0 if i % 2 == 0 else 7
        dur = pulso * 3
        acomp.append((onda_seno(nota_a_frecuencia(raiz, 130.81), dur) +
                      onda_seno(nota_a_frecuencia(raiz + 7, 130.81), dur) * 0.5) * envolvente(n_acorde, 0.08, 1.4) * 0.25)
    acomp = np.concatenate(acomp)[:len(lead)]

    mezcla = fundido_de_bucle(lead + acomp, ms=80)
    return normalizar(mezcla, 0.7)


TECNO_BPM = 132


def _filtro_pasabajos(señal, cortes):
    """Pasabajos de un polo con frecuencia de corte variable muestra a
    muestra (el "barrido" del bajo acid)."""
    alfas = 1.0 - np.exp(-2 * np.pi * np.asarray(cortes) / SR)
    salida = np.empty_like(señal)
    y = 0.0
    for i in range(len(señal)):
        y += alfas[i] * (señal[i] - y)
        salida[i] = y
    return salida


def _bombo_tecno(dur=0.28):
    t = np.arange(int(SR * dur)) / SR
    freq = 45 + 110 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.12)


def _hat_abierto(dur=0.12):
    n = int(SR * dur)
    ruido = np.diff(ruido_blanco(dur + 2 / SR, semilla=3))[:n]
    return ruido * np.exp(-np.arange(n) / SR / 0.04) * 0.5


def _palmas(dur=0.25):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ruido = suavizar(ruido_blanco(dur, semilla=5), 2)[:n]
    env = sum(np.where(t >= d, np.exp(-(t - d) / 0.008), 0) for d in (0.0, 0.011, 0.022))
    env = env + np.where(t >= 0.03, np.exp(-(t - 0.03) / 0.07) * 0.5, 0)
    return ruido * env


def _poner(mezcla, señal, t_seg, vol=1.0):
    i = int(t_seg * SR)
    if i >= len(mezcla):
        return
    fin = min(len(mezcla), i + len(señal))
    mezcla[i:fin] += señal[:fin - i] * vol


def _supersierra(freq, dur, voces=7, desafino=0.006, semilla=0):
    """Varias sierras levemente desafinadas y con fase al azar (el sonido
    "supersaw" de los himnos de trance/techno): gorda y ancha."""
    rng = np.random.default_rng(semilla)
    t = np.arange(int(SR * dur)) / SR
    salida = np.zeros(len(t))
    for k in range(voces):
        f = freq * (1 + desafino * (k - (voces - 1) / 2))
        salida += ((f * t + rng.random()) % 1.0) * 2 - 1
    return salida / voces


def _ganar_volumen(señal, empuje=1.8, pico=0.98):
    """Saturacion suave (tanh) sobre la señal normalizada: sube el volumen
    percibido (mas RMS) sin recortar de golpe los picos."""
    señal = normalizar(señal, 1.0)
    return np.tanh(señal * empuje) / np.tanh(empuje) * pico


# progresion del techno epico: (semitonos del acorde respecto de La4,
# desplazamiento de la raiz del bajo, arpegio del lead en corcheas)
_PROGRESION_TECNO = (
    ((-12, -9, -5), 0, (0, 3, 7, 12, 10, 7, 3, 7)),      # La menor
    ((-16, -12, -9), -4, (-4, 0, 3, 8, 7, 3, 0, 3)),     # Fa
    ((-9, -5, -2), 3, (-5, -2, 3, 7, 5, 3, -2, 3)),      # Do
    ((-14, -10, -7), -2, (-7, -2, 2, 5, 10, 5, 2, -2)),  # Sol
)


def generar_musica_victoria_tecno():
    """Pantalla de VICTORIA falsa (antes del jefe bonus): techno de rave a
    132 BPM en el estilo de la escena de apertura de Blade, llevado a himno
    epico -bombo en negras, hat abierto a contratiempo, palmas en 2 y 4,
    bajo acid en semicorcheas que sigue los acordes, un colchon de
    supersaw que "bombea" con el bombo (sidechain), melodia de lead que
    arranca en el segundo compas, golpes de orquesta y subidas de ruido-
    sobre La menor - Fa - Do - Sol. Saturado para que suene fuerte. Loop de
    8 compases."""
    pulso = 60.0 / TECNO_BPM
    compas = pulso * 4
    compases = 8
    total = int(SR * compas * compases)
    mezcla = np.zeros(total)
    t_total = np.arange(total) / SR
    bombo, hat, palmas = _bombo_tecno(), _hat_abierto(), _palmas()

    for c in range(compases):
        for b in range(4):
            t = c * compas + b * pulso
            _poner(mezcla, bombo, t, 1.0)
            _poner(mezcla, hat, t + pulso / 2, 0.35)
            if b in (1, 3):
                _poner(mezcla, palmas, t, 0.5)

    def acorde_de(c):
        return _PROGRESION_TECNO[(c // 2) % len(_PROGRESION_TECNO)]

    # bajo acid: el riff de siempre, transportado a la raiz de cada acorde
    riff = [0, 0, 12, 0, 3, 0, 10, 0, 0, 0, 12, 7, 5, 0, 3, 0]
    semicorchea = pulso / 4
    n_nota = int(SR * semicorchea)
    notas = []
    for c in range(compases):
        raiz = acorde_de(c)[1]
        for k, semi in enumerate(riff):
            freq = nota_a_frecuencia(semi + raiz, 55.0)
            nota = onda_sierra(freq, semicorchea) * envolvente(n_nota, 0.002, semicorchea * 0.8)
            notas.append(nota * (1.2 if k % 4 == 0 else 0.9))
    bajo = np.concatenate(notas)
    t = np.arange(len(bajo)) / SR
    barrido = 350 + 1900 * (0.5 + 0.5 * np.sin(2 * np.pi * t / (compas * 4) - np.pi / 2))
    acento = 1 + 0.8 * np.exp(-(t % semicorchea) / 0.03)
    bajo = np.tanh(_filtro_pasabajos(bajo, barrido * acento) * 2.5) * 0.4
    mezcla[:len(bajo)] += bajo[:len(mezcla)]

    # colchon supersaw (2 compases por acorde) que se agacha con cada bombo
    sidechain = 1 - 0.65 * np.exp(-(t_total % pulso) / 0.11)
    colchon = np.zeros(total)
    for c in range(0, compases, 2):
        dur = compas * 2
        n = int(SR * dur)
        acorde = sum(_supersierra(nota_a_frecuencia(sem, 440.0), dur, semilla=c + i)
                     for i, sem in enumerate(acorde_de(c)[0]))
        acorde = suavizar(acorde, 5) * np.minimum(1, np.arange(n) / SR / 0.05)
        _poner(colchon, acorde, c * compas)
    mezcla += colchon * sidechain * 0.3

    # melodia de himno en corcheas desde el compas 1 (el lead se abre en la
    # segunda vuelta subiendo una octava las ultimas notas)
    corchea = pulso / 2
    n_corchea = int(SR * corchea)
    for c in range(1, compases):
        arpegio = acorde_de(c)[2]
        for k, semi in enumerate(arpegio):
            if c >= 4 and k >= 6:
                semi += 12
            lead = _supersierra(nota_a_frecuencia(semi, 440.0), corchea, voces=5, semilla=k)
            lead = suavizar(lead, 3) * envolvente(n_corchea, 0.004, corchea * 1.4)
            _poner(mezcla, lead, c * compas + k * corchea, 0.22)

    # golpes de orquesta al empezar cada mitad (boom grave + acorde + crash)
    for c in (0, 4):
        dur = 1.6
        n = int(SR * dur)
        tt = np.arange(n) / SR
        boom = np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-tt / 0.08)) / SR) * np.exp(-tt / 0.5)
        crash = suavizar(ruido_blanco(dur, semilla=31 + c), 2)[:n] * np.exp(-tt / 0.4) * 0.35
        acorde = sum(_supersierra(nota_a_frecuencia(sem, 440.0), dur, semilla=50 + i)
                     for i, sem in enumerate((-24, -12, -9, -5, 0)))
        golpe = boom * 0.9 + crash + suavizar(acorde, 4) * np.exp(-tt / 0.35) * 0.5
        _poner(mezcla, golpe, c * compas)

    # subidas de ruido hacia la mitad y hacia el final del loop
    for c in (3, 7):
        n = int(SR * compas)
        subida = np.diff(ruido_blanco(compas + 2 / SR, semilla=60 + c))[:n] * np.linspace(0, 1, n) ** 2.5
        _poner(mezcla, subida * 0.25, c * compas)

    # stabs de acorde en el "y" del tiempo 3
    for c in range(2, compases):
        dur = 0.16
        n = int(SR * dur)
        stab = sum(onda_sierra(nota_a_frecuencia(sem + 12, 440.0), dur) for sem in acorde_de(c)[0])
        stab = suavizar(stab, 4) * envolvente(n, 0.002, 0.07) * 0.12
        _poner(mezcla, stab, c * compas + 2.5 * pulso)

    return _ganar_volumen(fundido_de_bucle(mezcla))


def generar_musica_glitch_epica():
    """Cuando la VICTORIA falsa se rompe (5 s, suena una sola vez y dura lo
    mismo que la fase "glitch" del juego): el techno sigue un compas y se
    transforma en musica epica -golpe de orquesta, coro, timbales en
    crescendo y una melodia de metales que sube- mientras el audio se
    "rompe" con tartamudeos y bitcrush; termina con un golpe final justo
    cuando aparece el jefe bonus."""
    dur = 5.7
    mezcla = np.zeros(int(SR * dur))

    # 0 - 1.4 s: el techno que venia sonando, desvaneciendose
    tecno = generar_musica_victoria_tecno()[:int(SR * 1.4)]
    tecno = tecno * np.linspace(1.0, 0.0, len(tecno)) ** 0.7
    mezcla[:len(tecno)] += tecno * 0.8

    def acorde_sierra(semis, base, dur, caida):
        n = int(SR * dur)
        voces = sum(onda_sierra(nota_a_frecuencia(s, base) * d, dur)
                    for s in semis for d in (0.997, 1.003))
        return suavizar(voces, 6) * envolvente(n, 0.004, caida)

    def golpe(t_seg, semis, vol=1.0):
        n = int(SR * 1.3)
        tt = np.arange(n) / SR
        boom = np.sin(2 * np.pi * 50 * tt) * np.exp(-tt / 0.35)
        crash = suavizar(ruido_blanco(1.3, semilla=11), 2)[:n] * np.exp(-tt / 0.25) * 0.4
        _poner(mezcla, (acorde_sierra(semis, 110.0, 1.3, 0.5) * 0.25 + boom + crash) * vol, t_seg)

    golpe(0.9, (0, 7, 12, 15, 19))

    # coro: cada voz, tres senos desafinados con vibrato
    progresion = [(0.9, 2.3, (0, 3, 7)), (2.3, 3.4, (-4, 0, 3)), (3.4, 4.4, (-2, 2, 5)), (4.4, 5.0, (-5, -1, 2))]
    for ini, fin, semis in progresion:
        d = fin - ini
        n = int(SR * d)
        tt = np.arange(n) / SR
        vibrato = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * tt)
        voz = np.zeros(n)
        for s in semis:
            f = nota_a_frecuencia(s + 12, 220.0)
            for det in (0.995, 1.0, 1.005):
                voz += np.sin(2 * np.pi * np.cumsum(f * det * vibrato) / SR)
        env = np.minimum(1, tt / 0.2) * np.minimum(1, (d - tt) / 0.08)
        _poner(mezcla, voz * env * 0.06, ini)

    # timbales: cada vez mas seguidos y mas fuertes
    t_tom = 0.9
    while t_tom < 5.0:
        p = (t_tom - 0.9) / 4.1
        n = int(SR * 0.3)
        tt = np.arange(n) / SR
        freq = 70 + 60 * np.exp(-tt / 0.05)
        tom = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-tt / 0.12)
        _poner(mezcla, tom, t_tom, 0.35 + 0.6 * p)
        t_tom += 0.24 - 0.17 * p

    # metales: melodia que sube sobre la progresion
    melodia = [(0.9, 0, .45), (1.35, 3, .45), (1.8, 7, .5), (2.3, 8, .37), (2.67, 7, .37), (3.04, 5, .36),
               (3.4, 10, .33), (3.73, 8, .33), (4.06, 7, .34), (4.4, 11, .6)]
    for ini, semi, d in melodia:
        n = int(SR * d)
        f = nota_a_frecuencia(semi, 220.0)
        metal = suavizar(onda_sierra(f, d) + onda_sierra(f * 1.004, d), 5)
        _poner(mezcla, metal * envolvente(n, 0.03, d * 1.2) * 0.2, ini)

    # platillo al reves que sube hacia el golpe final
    n = int(SR * 0.6)
    subida = suavizar(ruido_blanco(0.6, semilla=21), 2)[:n] * np.linspace(0, 1, n) ** 2 * 0.5
    _poner(mezcla, subida, 4.4)
    golpe(5.0, (0, 7, 12, 16, 19), vol=1.2)

    # la musica "se rompe": tartamudeos (un pedacito repetido) y bitcrush
    for ini, largo, veces in ((2.95, 0.07, 4), (3.6, 0.05, 6), (4.2, 0.09, 3), (4.62, 0.04, 8)):
        i, n_largo = int(SR * ini), int(SR * largo)
        pedazo = mezcla[i:i + n_largo].copy()
        for k in range(1, veces):
            _poner_sobre = i + k * n_largo
            mezcla[_poner_sobre:_poner_sobre + n_largo] = pedazo[:len(mezcla[_poner_sobre:_poner_sobre + n_largo])]
    i0, i1 = int(SR * 3.85), int(SR * 4.2)
    crush = mezcla[i0:i1] / (np.max(np.abs(mezcla)) or 1)
    crush = np.repeat(np.round(crush[::8] * 6) / 6, 8)[:i1 - i0]
    mezcla[i0:i1] = crush * np.max(np.abs(mezcla))

    fundido = int(SR * 0.05)
    mezcla[:fundido] *= np.linspace(0, 1, fundido)
    mezcla[-fundido:] *= np.linspace(1, 0, fundido)
    return _ganar_volumen(mezcla, empuje=2.6)


# ------------------------------------------------ musica de partida "metal"
#
# Despues de cada jefe de oleada la musica de la partida se pone mas
# pesada: musica_juego (oleadas 1-10) y despues musica_juego_metal1..4
# (11-20, 21-30, 31-40, 41-50). Mismo riff en Mi menor en todos los
# niveles para que se sienta una evolucion y no temas sueltos.

def _power_chord(freq, dur, ganancia, apagado):
    """Quinta distorsionada (raiz + quinta + octava, dos sierras
    desafinadas). apagado=True: "palm mute" corto y mas oscuro."""
    n = int(SR * dur)
    onda = (onda_sierra(freq * 0.998, dur) + onda_sierra(freq * 1.002, dur)
            + 0.8 * onda_sierra(freq * 1.5, dur) + 0.5 * onda_sierra(freq * 2, dur))
    onda = suavizar(onda, 3)
    distorsion = np.tanh(onda * ganancia)
    # "gabinete" del amplificador: le saca el filo de arriba
    distorsion = suavizar(distorsion, 7 if apagado else 3)
    return distorsion * envolvente(n, 0.002, 0.07 if apagado else dur * 0.9)


def _redoble(dur=0.22):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ruido = ruido_blanco(dur, semilla=71)[:n] * np.exp(-t / 0.07)
    tono = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    return ruido * 0.7 + tono * 0.6


def _platillo(dur=1.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    return np.diff(ruido_blanco(dur + 2 / SR, semilla=73))[:n] * np.exp(-t / 0.5) * 0.35


def _lead_guitarra(freq, dur, ganancia):
    n = int(SR * dur)
    t = np.arange(n) / SR
    vibrato = 1 + 0.006 * np.sin(2 * np.pi * 6 * t) * np.minimum(1, t / 0.15)
    onda = 2 * ((np.cumsum(freq * vibrato) / SR) % 1.0) - 1
    onda = suavizar(np.tanh(suavizar(onda, 2) * ganancia), 4)
    return onda * envolvente(n, 0.005, dur * 1.1)


def _filtro_acido(señal, corte, resonancia):
    """Filtro pasabajos resonante (state variable) con el corte variando
    muestra a muestra: el "chillido" del bajo acido del techno (TB-303)."""
    salida = np.zeros(len(señal))
    bajo = banda = 0.0
    amort = 2.0 - 1.9 * resonancia
    for i in range(len(señal)):
        f = 2.0 * np.sin(np.pi * min(corte[i], SR / 6) / SR)
        alto = señal[i] - bajo - amort * banda
        banda += f * alto
        bajo += f * banda
        salida[i] = bajo
    return salida


def _bombeo(total, pulso, profundidad):
    """Envolvente de "sidechain": todo lo que no es bateria se agacha en cada
    golpe del bombo y vuelve a subir, el vaiven tipico del techno."""
    t = (np.arange(total) / SR) % pulso
    return 1.0 - profundidad * np.exp(-t / (pulso * 0.28))


def generar_musica_juego_metal(nivel):
    """nivel 0..4 (el juego elige cual en main._musica_partida). El 0 (oleadas
    1-10) es metal liviano con una melodia de sintetizador arcade. Con cada
    nivel sube el tempo (130 -> 160 BPM) y la distorsion; el 2 suma un
    acorde abierto a mitad de compas, bombo extra, platillo en cada compas
    y guitarra lider en la segunda mitad; el 3 pasa a semicorcheas con
    doble bombo y lead en todo el loop; el 4 baja la afinacion, mete blast
    beat en la segunda mitad y armoniza el lead en quintas.

    Ademas, desde el nivel 1 se suma una capa techno que crece con cada
    jefe: bombo en negras, hat a contratiempo, palmas, bajo acido con el
    filtro abriendose y "sidechain" (todo se agacha en cada bombo); el 2
    suma acordes supersaw a contratiempo y el 3 semicorcheas de hat y una
    subida de ruido al final del loop."""
    bpm = 120 + 10 * nivel
    pulso = 60.0 / bpm
    corchea = pulso / 2
    compas = pulso * 4
    compases = 8
    total = int(SR * compas * compases)
    guitarra = np.zeros(total)
    bajo = np.zeros(total)
    bateria = np.zeros(total)
    lead = np.zeros(total)

    afinacion = -2 if nivel >= 4 else 0          # el ultimo nivel baja la afinacion
    base_freq = 82.41 * (2.0 ** (afinacion / 12))  # Mi grave
    raices = [0, 0, 3, -2, 5, 3, 0, -2]            # Mi Mi Sol Re | La Sol Mi Re
    ganancia = (2.5, 3, 6, 10, 16)[nivel]
    subdivision = 4 if nivel >= 3 else 2           # corcheas o semicorcheas

    bombo, redoble, hat, platillo = _bombo_tecno(0.22), _redoble(), _hat_abierto(0.05), _platillo()

    for c in range(compases):
        raiz = raices[c]
        f = base_freq * (2.0 ** (raiz / 12))
        inicio = c * compas
        # guitarra ritmica: acorde abierto al empezar el compas, el resto chugs
        golpe = compas / (4 * subdivision)
        for k in range(4 * subdivision):
            abierto = k == 0 or (nivel >= 2 and k == 2 * subdivision)
            dur = golpe * (3 if abierto else 1)
            _poner(guitarra, _power_chord(f, dur, ganancia, not abierto), inicio + k * golpe, 0.9 if abierto else 0.7)
            nota_bajo = onda_seno(f / 2, golpe) + 0.4 * onda_sierra(f / 2, golpe)
            _poner(bajo, suavizar(nota_bajo, 8) * envolvente(int(SR * golpe), 0.003, golpe * 0.8), inicio + k * golpe, 0.6)

        # bateria
        blast = nivel >= 4 and c >= 4
        for b in range(4):
            t = inicio + b * pulso
            if blast:
                # blast beat: bombo y redoble alternados en semicorcheas
                for s in range(4):
                    _poner(bateria, bombo if s % 2 == 0 else redoble, t + s * pulso / 4, 0.8 if s % 2 == 0 else 0.55)
                continue
            if nivel >= 3:
                for s in range(4):   # doble bombo
                    _poner(bateria, bombo, t + s * pulso / 4, 0.75)
            elif b in (0, 2) or (nivel >= 2 and b == 3):
                _poner(bateria, bombo, t, 0.9)
            if b in (1, 3):
                _poner(bateria, redoble, t, 0.8)
            for s in range(2):
                _poner(bateria, hat, t + s * corchea, 0.25)
        if nivel >= 2 or c % 4 == 0:
            _poner(bateria, platillo, inicio, 0.8 if nivel >= 3 else 0.6)

    # guitarra lider (Mi menor pentatonica) desde el nivel 2
    if nivel >= 2:
        frases = [
            [7, 10, 12, 10, 7, 5, 3, 5], [7, 10, 12, 15, 12, 10, 7, 10],
            [12, 10, 7, 5, 3, 5, 7, 3], [0, 3, 5, 7, 5, 3, 0, -2],
        ]
        desde = 4 if nivel == 2 else 0
        for c in range(desde, compases):
            frase = frases[c % 4]
            for k, semi in enumerate(frase):
                f = 329.63 * (2.0 ** ((semi + afinacion) / 12))
                nota = _lead_guitarra(f, corchea, 3 + nivel)
                _poner(lead, nota, c * compas + k * corchea, 0.35)
                if nivel >= 4:
                    # segunda voz a la quinta, como las guitarras gemelas del metal
                    _poner(lead, _lead_guitarra(f * 1.5, corchea, 3 + nivel), c * compas + k * corchea, 0.22)

    if nivel == 0:
        # melodia de sintetizador arcade (pulso angosto) sobre el riff liviano
        frase = [7, 10, 12, 10, 7, 5, 7, None, 3, 5, 7, 5, 3, 0, 3, None]
        for c in range(compases):
            for k in range(8):
                semi_lead = frase[(c % 2) * 8 + k]
                if semi_lead is None:
                    continue
                f = 329.63 * 2 ** (semi_lead / 12)
                nota = onda_cuadrada(f, corchea, ancho_pulso=0.25) * envolvente(int(SR * corchea), 0.004, corchea * 0.8)
                _poner(lead, nota, c * compas + k * corchea, 0.22)

    # ---- capa techno: crece con cada jefe derrotado (nivel 1..4)
    tecno = np.zeros(total)
    acido = np.zeros(total)
    sinte = np.zeros(total)
    if nivel >= 1:
        kick, palma, hat_tecno = _bombo_tecno(0.3), _palmas(), _hat_abierto(0.11)
        for c in range(compases):
            inicio = c * compas
            for b in range(4):
                t = inicio + b * pulso
                _poner(tecno, kick, t, 1.0)                    # bombo en negras
                _poner(tecno, hat_tecno, t + corchea, 0.45)    # hat a contratiempo
                if b in (1, 3):
                    _poner(tecno, palma, t, 0.5)
                if nivel >= 3:
                    for s16 in (1, 3):
                        _poner(tecno, _hat_abierto(0.03), t + s16 * pulso / 4, 0.22)

        # bajo acido en semicorcheas siguiendo el riff; el filtro se abre y
        # se cierra cada dos compases y chilla mas en cada nivel
        semi16 = pulso / 4
        patron = [0, 0, 12, 0, 0, 10, 0, 12, 0, 0, 7, 0, 12, 0, 3, 0]
        acento = [1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0]
        crudo = np.zeros(total)
        picos = np.zeros(total)
        for c in range(compases):
            f_raiz = base_freq * (2.0 ** (raices[c] / 12))
            for k in range(16):
                f = f_raiz * (2.0 ** (patron[k] / 12))
                dur = semi16 * (0.9 if acento[k] else 0.55)
                n = int(SR * dur)
                nota = onda_sierra(f, dur)[:n] * envolvente(n, 0.002, dur * 0.9)
                i = int((c * compas + k * semi16) * SR)
                fin = min(total, i + n)
                crudo[i:fin] += nota[:fin - i]
                tt = np.arange(fin - i) / SR
                picos[i:fin] = np.maximum(picos[i:fin], (1.0 if acento[k] else 0.5) * np.exp(-tt / 0.06))
        tiempo = np.arange(total) / SR
        barrido = 0.5 - 0.5 * np.cos(2 * np.pi * tiempo / (compas * 2))
        corte = 180 + (500 + 350 * nivel) * barrido + (900 + 300 * nivel) * picos
        acido = np.tanh(_filtro_acido(crudo, corte, 0.55 + 0.08 * nivel) * (1.5 + 0.5 * nivel))

    if nivel >= 2:
        # acordes "supersaw" a contratiempo (Mi menor sobre la raiz del riff)
        for c in range(compases):
            f_raiz = 164.81 * (2.0 ** ((raices[c] + afinacion) / 12))
            for b in range(4):
                dur = corchea * 0.8
                n = int(SR * dur)
                acorde = sum(_supersierra(f_raiz * (2.0 ** (iv / 12)), dur, voces=5, semilla=c * 4 + b + iv)
                             for iv in (0, 3, 7, 12))
                acorde = suavizar(acorde, 3)[:n] * envolvente(n, 0.004, dur * 0.6)
                _poner(sinte, acorde, c * compas + b * pulso + corchea, 0.32)

    if nivel >= 3:
        # subida de ruido en el ultimo compas, antes de que vuelva el loop
        dur = compas
        n = int(SR * dur)
        ruido = np.diff(ruido_blanco(dur + 2 / SR, semilla=91))[:n]
        _poner(sinte, ruido * np.linspace(0, 1, n) ** 2 * 0.5, (compases - 1) * compas, 1.0)

    bombeo = _bombeo(total, pulso, 0.12 * nivel)
    mezcla = ((guitarra * 0.55 + lead + sinte) * bombeo + bajo * 0.5 * bombeo
              + bateria * 0.7 + tecno * 0.6 + acido * (0.16 + 0.04 * nivel))
    return _ganar_volumen(fundido_de_bucle(mezcla), empuje=1.5 + 0.2 * nivel)


# ------------------------------------------------- jefes: metal arcade
#
# Cada jefe de oleada tiene su propio tema de metal con el espiritu de
# Metal Slug 3: guitarras distorsionadas con riff propio, bateria de rock,
# bajo, una melodia que se queda en la cabeza (guitarra lider o "metales"
# de orquesta) y golpes de bronces en los cambios de acorde. Todos estan
# armados en secciones (riff A -> riff B con melodia -> remate) de unos
# 25-35 segundos para que no canse el loop, y saturados para que suenen
# fuerte por encima de los disparos.

def _bronces(freq, dur, brillo=1.0, ataque=0.03):
    """Seccion de metales (trompetas/trombones): suma de armonicos que se
    van abriendo en el ataque, con un vibrato leve; dos voces desafinadas
    para que suene a grupo y no a una sola trompeta."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    apertura = np.minimum(1.0, t / max(ataque, 1e-3))
    salida = np.zeros(n)
    for desafino in (0.997, 1.003):
        fase = 2 * np.pi * freq * desafino * (t + 0.0015 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.3))
        for k in range(1, 11):
            if freq * k > SR / 2.2:
                break
            amp = (1.0 / k) * apertura ** (0.6 + 0.5 * k / brillo)
            salida += amp * np.sin(k * fase)
    salida = np.tanh(salida * 0.9)
    return salida * envolvente(n, 0.01, dur * 1.4)


def _coro(freq, dur):
    """Colchon de "voces" (pad de vocales "aaah") para los jefes grandes."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    salida = np.zeros(n)
    for k, d in enumerate((0.994, 1.0, 1.006, 2.0, 1.5)):
        fase = 2 * np.pi * freq * d * t + k
        salida += np.sin(fase) + 0.3 * np.sin(2 * fase) + 0.15 * np.sin(3 * fase)
    sube = np.minimum(1.0, t / 0.25)
    baja = np.minimum(1.0, (dur - t) / 0.3)
    return salida / 5 * sube * np.clip(baja, 0, 1)


def _arpegio_glitch(freq, dur, bits=4):
    """Cuadrada con "bitcrush" (pocos niveles de volumen): el sintetizador
    roto de la Anomalia."""
    onda = onda_cuadrada(freq, dur, ancho_pulso=0.3) * 0.6 + onda_sierra(freq * 2, dur) * 0.4
    niveles = 2 ** bits
    onda = np.round(onda * niveles) / niveles
    return onda * envolvente(int(SR * dur), 0.002, dur * 0.7)


def _tom(freq, dur=0.3):
    t = np.arange(int(SR * dur)) / SR
    f = freq * (1 + 0.6 * np.exp(-t / 0.02))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)


def _bateria_metal(mezcla, estilo, inicio, compas, kit, relleno=False):
    """Un compas de bateria. estilo: "rock", "galope", "thrash" (skank),
    "doble" (doble bombo), "mitad" (medio tiempo pesado), "blast"."""
    bombo, redoble, hat, platillo, toms = kit
    pulso = compas / 4
    semi = pulso / 4
    if relleno:
        # redoble de toms bajando para entrar a la seccion siguiente
        for s in range(16):
            golpe = redoble if s < 8 else toms[min(2, (s - 8) // 3)]
            _poner(mezcla, golpe, inicio + s * semi, 0.45 + 0.03 * s)
        return
    for b in range(4):
        t = inicio + b * pulso
        if estilo == "blast":
            for s in range(4):
                _poner(mezcla, bombo, t + s * semi, 0.8)
                _poner(mezcla, redoble if s % 2 else hat, t + s * semi, 0.5)
            continue
        if estilo == "thrash":
            _poner(mezcla, bombo, t, 0.9)
            _poner(mezcla, redoble, t + pulso / 2, 0.8)
            _poner(mezcla, hat, t, 0.3)
            continue
        if estilo == "mitad":
            if b == 0:
                _poner(mezcla, bombo, t, 1.0)
                _poner(mezcla, bombo, t + pulso * 0.75, 0.8)
            if b == 2:
                _poner(mezcla, redoble, t, 1.0)
            _poner(mezcla, hat, t, 0.3)
            continue
        if estilo == "doble":
            for s in range(4):
                _poner(mezcla, bombo, t + s * semi, 0.7)
        elif estilo == "galope":
            for s in (0, 2, 3):
                _poner(mezcla, bombo, t + s * semi, 0.8)
        elif b in (0, 2):
            _poner(mezcla, bombo, t, 0.9)
            if b == 2:
                _poner(mezcla, bombo, t + pulso / 2, 0.7)
        if b in (1, 3):
            _poner(mezcla, redoble, t, 0.85)
        for s in range(2):
            _poner(mezcla, hat, t + s * pulso / 2, 0.25)


def _tema_metal(bpm, tonica, secciones, ganancia, melodia=None, voz_melodia="guitarra",
                golpes_bronce=True, coro=False, glitch=False, empuje=2.0):
    """Arma un tema de jefe.
    tonica: frecuencia de la cuerda grave (raiz de los acordes).
    secciones: lista de (riff, raices, estilo_bateria, con_melodia). riff es
      un compas de 16 semicorcheas: numero = semitono sobre la raiz (golpe
      de power chord, apagado si es corto), "-" = sostener el anterior,
      None = silencio. raices: un semitono por compas.
    melodia: lista de (semitono sobre la tonica x4, duracion en corcheas);
      suena en las secciones con_melodia, repitiendose.
    voz_melodia: "guitarra", "bronces" o "gemelas" (dos guitarras en tercera)."""
    pulso = 60.0 / bpm
    compas = pulso * 4
    semi = compas / 16
    total_compases = sum(len(raices) for _, raices, _, _ in secciones)
    total = int(SR * compas * total_compases) + 1
    guitarra, bajo, bateria, arriba, fondo = (np.zeros(total) for _ in range(5))
    kit = (_bombo_tecno(0.2), _redoble(), _hat_abierto(0.04), _platillo(),
           [_tom(f) for f in (180, 130, 95)])

    c_global = 0
    for s_idx, (riff, raices, estilo, con_melodia) in enumerate(secciones):
        for c_local, raiz in enumerate(raices):
            inicio = c_global * compas
            f_raiz = tonica * 2 ** (raiz / 12)
            # guitarra ritmica y bajo siguiendo el riff
            k = 0
            while k < 16:
                paso = riff[k]
                largo = 1
                while k + largo < 16 and riff[k + largo] == "-":
                    largo += 1
                if paso is not None and paso != "-":
                    f = f_raiz * 2 ** (paso / 12)
                    dur = semi * largo
                    apagado = largo == 1
                    _poner(guitarra, _power_chord(f, dur, ganancia, apagado), inicio + k * semi,
                           0.7 if apagado else 0.9)
                    nb = int(SR * dur)
                    nota_bajo = suavizar(onda_seno(f / 2, dur) + 0.5 * onda_sierra(f / 2, dur), 6)
                    _poner(bajo, nota_bajo * envolvente(nb, 0.003, dur * 0.8), inicio + k * semi, 0.55)
                k += largo
            ultimo = c_local == len(raices) - 1
            ultima_seccion = s_idx == len(secciones) - 1
            _bateria_metal(bateria, estilo, inicio, compas, kit,
                           relleno=ultimo and not ultima_seccion and c_local % 4 == 3)
            if c_local % 4 == 0:
                _poner(bateria, kit[3], inicio, 0.75)
            if golpes_bronce and (c_local == 0 or raiz != raices[c_local - 1]):
                for intervalo in (0, 7, 12, 15):
                    _poner(arriba, _bronces(f_raiz * 4 * 2 ** (intervalo / 12), pulso * 0.9, ataque=0.015),
                           inicio, 0.12)
            if coro:
                for intervalo in (0, 3, 7):
                    _poner(fondo, _coro(f_raiz * 4 * 2 ** (intervalo / 12), compas), inicio, 0.18)
            if glitch:
                for n_arp in range(16):
                    if (n_arp * 7 + c_global) % 5 == 0:
                        continue  # se "cuelga" un paso
                    intervalo = (0, 3, 7, 10, 12, 10, 7, 3)[n_arp % 8]
                    _poner(fondo, _arpegio_glitch(f_raiz * 4 * 2 ** (intervalo / 12), semi), inicio + n_arp * semi, 0.2)
            c_global += 1

        # melodia de la seccion
        if con_melodia and melodia:
            t = (c_global - len(raices)) * compas
            fin = c_global * compas
            i = 0
            while t < fin - 1e-6:
                semitono, corcheas = melodia[i % len(melodia)]
                dur = min(corcheas * pulso / 2, fin - t)
                if semitono is not None:
                    f = tonica * 4 * 2 ** (semitono / 12)
                    if voz_melodia == "bronces":
                        _poner(arriba, _bronces(f, dur, brillo=1.4), t, 0.32)
                        _poner(arriba, _bronces(f / 2, dur, brillo=1.0), t, 0.18)
                    else:
                        _poner(arriba, _lead_guitarra(f, dur, 6), t, 0.32)
                        if voz_melodia == "gemelas":
                            _poner(arriba, _lead_guitarra(f * 2 ** (4 / 12), dur, 6), t, 0.2)
                t += dur
                i += 1

    mezcla = guitarra * 0.55 + bajo * 0.5 + bateria * 0.75 + arriba + fondo
    return _ganar_volumen(fundido_de_bucle(mezcla), empuje=empuje)


# riffs de un compas (16 semicorcheas)
_RIFF_GALOPE = [0, 0, 0, None, 0, 0, 0, None, 0, 0, 0, None, 3, "-", 5, "-"]
_RIFF_MARCHA = [0, "-", None, 0, 0, None, 0, None, 0, "-", None, 0, 7, "-", 5, "-"]


def generar_musica_jefe_sentinel():
    """Centinela Corrupto (oleada 10): marcha militar metalera en Mi menor a
    150 BPM. Galope de guitarras, redoblante de desfile y una fanfarria de
    bronces que es el "tema" del jefe, como los jefes del ejercito de
    Morden en Metal Slug."""
    melodia = [(7, 2), (7, 1), (7, 1), (10, 2), (7, 2), (12, 3), (10, 1), (7, 2), (5, 2),
               (3, 2), (5, 2), (7, 4), (None, 2), (7, 1), (7, 1), (12, 2), (15, 2), (14, 3),
               (12, 1), (10, 2), (12, 2), (7, 6), (None, 2)]
    return _tema_metal(
        150, 82.41,
        [(_RIFF_MARCHA, [0, 0, 3, 5], "rock", False),
         (_RIFF_GALOPE, [0, 0, 3, 5, 0, 0, 8, 7], "galope", True),
         (_RIFF_MARCHA, [5, 3, 7, 7], "doble", True)],
        ganancia=8, melodia=melodia, voz_melodia="bronces", empuje=2.0)


def generar_musica_jefe_dragon():
    """Vanguardia Autonoma / dragon (oleada 20): thrash rapido en Re menor a
    176 BPM, riff en tremolo con cromatismos y guitarras gemelas en la
    melodia, como persecucion a toda velocidad."""
    riff = [0, 0, 0, 0, 1, 1, 0, 0, 3, 3, 0, 0, 6, 5, 3, 1]
    riff_b = [0, 0, 12, 0, 0, 10, 0, 0, 8, 0, 0, 7, 0, 6, 5, 3]
    melodia = [(12, 1), (15, 1), (17, 1), (15, 1), (12, 2), (10, 2), (12, 1), (15, 1), (17, 1), (20, 1),
               (19, 4), (17, 1), (15, 1), (13, 1), (12, 1), (10, 2), (12, 2), (8, 2), (7, 2), (12, 4)]
    return _tema_metal(
        176, 73.42,
        [(riff, [0, 0, 0, 0], "thrash", False),
         (riff_b, [0, 0, -2, -4, 0, 0, 3, 1], "thrash", True),
         (riff, [5, 5, 3, 1], "blast", True)],
        ganancia=14, melodia=melodia, voz_melodia="gemelas", empuje=2.2)


def generar_musica_jefe_titan():
    """Titan del Vacio (oleada 30): metal lento y aplastante (doom) a 92 BPM
    en Do# grave, acordes que suenan largos, coro de fondo y bronces graves
    como pasos de un gigante."""
    riff = [0, "-", "-", "-", "-", "-", None, 0, 1, "-", "-", "-", 0, "-", None, None]
    riff_b = [0, "-", "-", 0, "-", "-", 3, "-", "-", "-", 1, "-", 0, None, 0, 0]
    melodia = [(0, 4), (3, 2), (1, 2), (0, 6), (None, 2), (7, 4), (8, 2), (7, 2), (3, 6), (None, 2)]
    return _tema_metal(
        92, 69.30,
        [(riff, [0, 0, 1, 0], "mitad", False),
         (riff_b, [0, 0, -2, 1, 0, 0, -4, -2], "mitad", True),
         (riff, [0, 1, 0, 0], "doble", True)],
        ganancia=12, melodia=melodia, voz_melodia="bronces", coro=True, empuje=2.1)


def generar_musica_jefe_anomalia():
    """La Anomalia Final (oleada 40): metal industrial en Fa# menor a 140
    BPM, chugs sincopados tipo djent, un sintetizador roto que se cuelga y
    melodia de guitarra lider inquietante."""
    riff = [0, None, 0, 0, None, 0, None, 0, 0, None, 0, None, 0, 0, 1, None]
    riff_b = [0, 0, None, 0, None, 0, 0, None, 3, "-", None, 0, 0, None, 6, "-"]
    melodia = [(12, 2), (13, 2), (12, 1), (10, 1), (8, 2), (7, 4), (None, 2), (12, 1), (15, 1),
               (18, 2), (17, 2), (13, 2), (12, 6), (None, 2)]
    return _tema_metal(
        140, 92.50,
        [(riff, [0, 0, 0, 1], "doble", False),
         (riff_b, [0, 0, 1, -1, 0, 0, 3, 1], "rock", True),
         (riff, [0, 0, 6, 5], "blast", True)],
        ganancia=16, melodia=melodia, voz_melodia="guitarra", golpes_bronce=False,
        glitch=True, empuje=2.2)


def generar_musica_jefe_mega():
    """El Coloso (oleada 50, jefe final): himno de metal epico en La menor a
    166 BPM con doble bombo, coro, bronces y guitarras gemelas; la ultima
    seccion sube un tono para el gran final."""
    riff = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, "-", 5, "-"]
    riff_b = [0, "-", "-", 0, 0, "-", 0, 0, 0, "-", "-", 0, 7, "-", 5, "-"]
    melodia = [(12, 2), (15, 2), (19, 2), (17, 1), (15, 1), (14, 2), (12, 2), (10, 2), (14, 2),
               (12, 6), (None, 2), (12, 2), (15, 2), (19, 2), (22, 2), (20, 3), (19, 1), (17, 2),
               (15, 2), (19, 8)]
    return _tema_metal(
        166, 110.0,
        [(riff, [0, 0, -4, -2], "doble", False),
         (riff_b, [0, -4, 3, -2, 0, -4, 3, -2], "doble", True),
         (riff_b, [2, -2, 5, 0, 2, -2, 5, 7], "blast", True)],
        ganancia=12, melodia=melodia, voz_melodia="gemelas", coro=True, empuje=2.3)


def _sinte_impostor(freq, dur):
    """Campanita de sintetizador fria (pulso finito + seno una octava
    arriba, con un vibrato que tiembla): la voz "sospechosa" del tema del
    tripulante."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    vibrato = 1 + 0.006 * np.sin(2 * np.pi * 6.5 * t)
    fase = np.cumsum(freq * vibrato) / SR
    pulso = np.where((fase % 1.0) < 0.125, 1.0, -0.15)
    campana = np.sin(2 * np.pi * 2 * fase)
    return (pulso * 0.45 + campana * 0.55) * envolvente(n, 0.004, dur * 0.9)


def generar_musica_impostor():
    """El tripulante al rescate: suspenso espacial "de impostor" (tema
    original, no la musica del juego). Do menor a 116 BPM: un ostinato de
    sintetizador frio con segundas menores que da desconfianza, golpes de
    alarma cada 4 compases y metal de medio tiempo que se vuelve doble
    bombo cuando la pelea arranca de verdad."""
    bpm = 116
    tonica = 65.41
    riff_a = [0, "-", "-", "-", None, None, None, None, 1, "-", "-", "-", None, None, None, None]
    riff_b = [0, None, 0, 0, None, 0, 1, None, 0, None, 0, 0, 6, "-", 5, "-"]
    riff_c = [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 8, "-", 7, "-"]
    melodia = [(0, 2), (1, 2), (0, 2), (None, 2), (7, 1), (8, 1), (7, 2), (1, 4), (None, 2),
               (12, 2), (11, 2), (8, 2), (7, 1), (6, 1), (7, 6), (None, 2)]
    secciones = [(riff_a, [0, 0, 0, 0], "mitad", False),
                 (riff_b, [0, 0, 1, 0, 0, 0, -2, -1], "rock", True),
                 (riff_c, [0, 1, 0, -1, 0, 1, 3, -1], "doble", True)]
    base = _tema_metal(bpm, tonica, secciones, ganancia=10, melodia=melodia,
                       voz_melodia="guitarra", golpes_bronce=False, empuje=1.8)

    # capa de suspenso encima de todo el tema
    pulso = 60.0 / bpm
    compas = pulso * 4
    capa = np.zeros(len(base))
    raices = [r for _, rs, _, _ in secciones for r in rs]
    figura = (0, 12, 1, 12, 0, 7, 1, 8)
    for c, raiz in enumerate(raices):
        inicio = c * compas
        f_raiz = tonica * 4 * 2 ** (raiz / 12)
        for k, intervalo in enumerate(figura):
            _poner(capa, _sinte_impostor(f_raiz * 2 ** (intervalo / 12), pulso / 2 * 0.95),
                   inicio + k * pulso / 2, 0.22)
        if c % 4 == 0:
            # golpe de alarma: racimo disonante grave + soplido de ruido
            for intervalo in (0, 1, 6):
                _poner(capa, _bronces(f_raiz / 2 * 2 ** (intervalo / 12), pulso * 1.5, brillo=1.3, ataque=0.005),
                       inicio, 0.16)
            n = int(SR * pulso)
            soplido = suavizar(ruido_blanco(pulso, semilla=c), 12) * np.linspace(0, 1, n) ** 2
            if c:
                _poner(capa, soplido, inicio - pulso, 0.35)
    mezcla = base * 0.85 + capa
    return _ganar_volumen(fundido_de_bucle(mezcla), empuje=2.0)


def _organo(freq, dur):
    """Organo de iglesia embrujada: fundamental + octavas + quinta con un
    leve tremolo (pipas que respiran)."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    onda = np.zeros(n)
    for mult, amp in ((0.5, 0.5), (1, 1.0), (1.5, 0.3), (2, 0.55), (4, 0.25)):
        onda += amp * np.sin(2 * np.pi * freq * mult * t)
    onda *= 1 + 0.12 * np.sin(2 * np.pi * 5.5 * t)
    return onda / 2.6 * envolvente(n, 0.03, dur * 3)


def _campana(freq, dur=2.5):
    """Campanada de cementerio: parciales inarmonicos que se apagan lento."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    onda = np.zeros(n)
    for mult, amp, caida in ((0.5, 0.6, 1.6), (1, 1.0, 1.2), (2.4, 0.5, 0.6), (2.76, 0.35, 0.5), (5.4, 0.2, 0.25)):
        onda += amp * np.sin(2 * np.pi * freq * mult * t) * np.exp(-t / caida)
    return onda / 2.4


def _capa_halloween(largo, bpm, tonica, raices, figura, voz, vol=0.2, campanas=False):
    """Capa encima de un _tema_metal: una figura de 8 corcheas por compas
    con `voz` (_organo o _sinte_impostor) siguiendo las raices, y si
    `campanas`, una campanada cada 4 compases."""
    pulso = 60.0 / bpm
    compas = pulso * 4
    capa = np.zeros(largo)
    for c, raiz in enumerate(raices):
        f_raiz = tonica * 4 * 2 ** (raiz / 12)
        for k, intervalo in enumerate(figura):
            if intervalo is None:
                continue
            _poner(capa, voz(f_raiz * 2 ** (intervalo / 12), pulso / 2 * 0.95), c * compas + k * pulso / 2, vol)
        if campanas and c % 4 == 0:
            _poner(capa, _campana(tonica * 2), c * compas, 0.45)
    return capa


def generar_musica_jefe_calabaza():
    """Rey Calabaza: metal "de feria embrujada" en Re menor a 160 BPM,
    galope con organo saltarin y una melodia de guitarra burlona."""
    bpm, tonica = 160, 73.42
    riff = [0, 0, 0, None, 0, 0, 1, None, 0, 0, 0, None, 3, "-", 1, "-"]
    riff_b = [0, None, 0, 3, None, 0, 6, "-", 5, None, 3, 0, 1, "-", 0, None]
    melodia = [(12, 1), (13, 1), (12, 1), (8, 1), (7, 2), (8, 2), (12, 1), (13, 1), (15, 1), (13, 1),
               (12, 4), (7, 1), (8, 1), (7, 1), (6, 1), (7, 2), (3, 2), (1, 2), (0, 6), (None, 2)]
    secciones = [(riff, [0, 0, 1, 0], "galope", False),
                 (riff_b, [0, 0, 3, 1, 0, 0, 6, 5], "galope", True),
                 (riff, [0, 1, 0, -1], "doble", True)]
    base = _tema_metal(bpm, tonica, secciones, ganancia=11, melodia=melodia, voz_melodia="guitarra",
                       golpes_bronce=False, empuje=1.9)
    raices = [r for _, rs, _, _ in secciones for r in rs]
    capa = _capa_halloween(len(base), bpm, tonica, raices, (0, 7, 12, 7, 1, 7, 12, 7), _organo, 0.22)
    return _ganar_volumen(fundido_de_bucle(base * 0.85 + capa), empuje=2.0)


def generar_musica_jefe_bruja():
    """Bruja Neon: thrash rapido en Mi menor a 182 BPM con un clavecin
    hechizado (sintetizador frio) en arpegios disminuidos."""
    bpm, tonica = 182, 82.41
    riff = [0, 0, 0, 0, 1, 0, 0, 0, 3, 0, 0, 0, 6, 5, 3, 1]
    riff_b = [0, 0, 6, 0, 0, 5, 0, 0, 3, 0, 1, 0, 0, 6, "-", "-"]
    melodia = [(12, 1), (15, 1), (18, 1), (21, 1), (24, 2), (21, 2), (18, 1), (15, 1), (12, 1), (15, 1),
               (13, 4), (12, 1), (13, 1), (15, 1), (18, 1), (17, 2), (15, 2), (13, 2), (12, 6)]
    secciones = [(riff, [0, 0, 0, 1], "thrash", False),
                 (riff_b, [0, 0, 1, -1, 0, 0, 3, 1], "thrash", True),
                 (riff, [0, 3, 6, 5], "blast", True)]
    base = _tema_metal(bpm, tonica, secciones, ganancia=14, melodia=melodia, voz_melodia="gemelas",
                       golpes_bronce=False, empuje=2.1)
    raices = [r for _, rs, _, _ in secciones for r in rs]
    capa = _capa_halloween(len(base), bpm, tonica, raices, (0, 3, 6, 9, 12, 9, 6, 3), _sinte_impostor, 0.2)
    return _ganar_volumen(fundido_de_bucle(base * 0.85 + capa), empuje=2.0)


def generar_musica_jefe_bruja_gigante():
    """Bruja Neon gigante (segunda fase): el thrash de la bruja mas lento y
    pesado, en Re menor a 150 BPM, con coro, organo y campanadas."""
    bpm, tonica = 150, 73.42
    riff = [0, "-", 0, 1, 0, "-", 6, "-", 5, "-", 3, 0, 1, "-", 0, None]
    riff_b = [0, 0, 3, 0, 0, 6, 0, 0, 5, 0, 3, 0, 1, 1, 0, 0]
    melodia = [(12, 2), (15, 2), (18, 2), (17, 2), (15, 4), (13, 2), (12, 2), (15, 1), (18, 1),
               (21, 2), (20, 2), (18, 4), (15, 2), (13, 2), (12, 8)]
    secciones = [(riff, [0, 0, 1, 0], "mitad", False),
                 (riff_b, [0, 0, 3, 1, 0, 0, 6, 5], "thrash", True),
                 (riff, [0, 3, 6, 5], "doble", True)]
    base = _tema_metal(bpm, tonica, secciones, ganancia=13, melodia=melodia, voz_melodia="gemelas",
                       golpes_bronce=False, coro=True, empuje=2.1)
    raices = [r for _, rs, _, _ in secciones for r in rs]
    capa = _capa_halloween(len(base), bpm, tonica, raices, (0, 3, 6, 9, 12, 9, 6, 3), _organo, 0.22,
                           campanas=True)
    return _ganar_volumen(fundido_de_bucle(base * 0.85 + capa), empuje=2.0)


def generar_musica_jefe_parca():
    """La Parca: doom de cementerio en Do# a 96 BPM, organo de iglesia,
    coro y campanadas cada cuatro compases."""
    bpm, tonica = 96, 69.30
    riff = [0, "-", "-", "-", "-", "-", None, 0, 1, "-", "-", "-", 0, "-", 6, "-"]
    riff_b = [0, "-", "-", 0, "-", "-", 1, "-", "-", "-", 3, "-", 1, None, 0, 0]
    melodia = [(12, 4), (13, 2), (12, 2), (8, 4), (7, 4), (None, 2), (6, 2), (7, 2), (8, 2), (7, 8)]
    secciones = [(riff, [0, 0, 1, 0], "mitad", False),
                 (riff_b, [0, 0, -2, 1, 0, 0, -4, -5], "mitad", True),
                 (riff, [0, 1, 0, 0], "doble", True)]
    base = _tema_metal(bpm, tonica, secciones, ganancia=12, melodia=melodia, voz_melodia="bronces",
                       golpes_bronce=False, coro=True, empuje=2.1)
    raices = [r for _, rs, _, _ in secciones for r in rs]
    capa = _capa_halloween(len(base), bpm, tonica, raices, (0, None, 7, None, 3, None, 7, None), _organo, 0.26,
                           campanas=True)
    return _ganar_volumen(fundido_de_bucle(base * 0.85 + capa), empuje=2.0)


def generar_musica_fin_halloween():
    """Final de la ruta de Halloween: vals de caja de musica embrujada
    (La menor, 3/4) con organo suave y una campanada al empezar cada vuelta."""
    bpm = 132
    pulso = 60.0 / bpm
    tonica = 220.0
    melodia = [(0, 1), (3, 1), (7, 1), (12, 2), (11, 1), (8, 1), (7, 1), (3, 1), (2, 2), (None, 1),
               (0, 1), (3, 1), (7, 1), (10, 2), (8, 1), (7, 1), (5, 1), (3, 1), (0, 3)]
    largo_pulsos = sum(d for _, d in melodia) * 2
    mezcla = np.zeros(int(SR * pulso * largo_pulsos) + 1)
    t = 0.0
    for vuelta in range(2):
        for semitono, d in melodia:
            dur = d * pulso
            if semitono is not None:
                f = tonica * 2 * 2 ** (semitono / 12)
                _poner(mezcla, _sinte_impostor(f, dur * 1.4), t, 0.35)
            t += dur
    acordes = [0, 0, 5, 5, 3, 3, 7, 0]
    compas = pulso * 3
    for c in range(int(len(mezcla) / SR / compas)):
        raiz = tonica / 2 * 2 ** (acordes[c % len(acordes)] / 12)
        _poner(mezcla, _organo(raiz, compas), c * compas, 0.28)
        for k in (1, 2):
            _poner(mezcla, _organo(raiz * 2 ** (7 / 12), pulso * 0.8), c * compas + k * pulso, 0.12)
        if c % 8 == 0:
            _poner(mezcla, _campana(tonica / 2), c * compas, 0.3)
    return normalizar(fundido_de_bucle(mezcla), pico=0.9)



def generar_musica_dimension_parca():
    """La dimension de la Parca (cinematicas del desafio): Do# menor muy
    lento, un zumbido grave que late como un corazon, coro de "aaah",
    organo en acordes y campanadas cada dos compases."""
    bpm, tonica = 60, 69.30
    pulso = 60.0 / bpm
    compas = pulso * 4
    acordes = [(0, 3, 7), (0, 3, 7), (-4, 0, 3), (-2, 1, 5), (0, 3, 7), (1, 5, 8), (-5, -1, 2), (-1, 2, 7)]
    largo = int(SR * compas * len(acordes))
    t = np.arange(largo) / SR
    mezcla = 0.25 * np.sin(2 * np.pi * tonica / 2 * t) * (1 + 0.3 * np.sin(2 * np.pi * 0.25 * t))
    mezcla += 0.12 * np.tanh(3 * np.sin(2 * np.pi * tonica * t))
    latido = deslizar_frecuencia(90, 40, 0.18) * envolvente(int(SR * 0.18), 0.002, 0.12)
    for c, acorde in enumerate(acordes):
        inicio = c * compas
        for nota in acorde:
            f = tonica * 4 * 2 ** (nota / 12)
            _poner(mezcla, _coro(f, compas), inicio, 0.22)
            _poner(mezcla, _organo(f / 2, compas), inicio, 0.12)
        for k in range(4):
            _poner(mezcla, latido, inicio + k * pulso, 0.7)
            _poner(mezcla, latido, inicio + k * pulso + 0.22, 0.45)
        if c % 2 == 0:
            _poner(mezcla, _campana(tonica * 2 * 2 ** (acorde[0] / 12), 3.5), inicio, 0.4)
    return _ganar_volumen(fundido_de_bucle(mezcla, ms=200), empuje=1.6, pico=0.9)


# ------------------------------------------------------- ruta cyberpunk

def _sinte_lead(freq, dur):
    """Lead de sintetizador: dos sierras apenas desafinadas, suavizadas,
    con un vibrato que entra despacio."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    vibrato = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.25)
    fase = np.cumsum(freq * vibrato) / SR
    onda = 0.5 * (((fase * 1.003) % 1.0) * 2 - 1) + 0.5 * (((fase * 0.997) % 1.0) * 2 - 1)
    return suavizar(onda, 3) * envolvente(n, 0.008, dur * 1.3)


def _bajo_synth(freq, dur):
    """Bajo de sierra filtrado que "pica" (decae rapido)."""
    n = int(SR * dur)
    onda = onda_sierra(freq, dur) * 0.7 + onda_cuadrada(freq / 2, dur) * 0.3
    return suavizar(onda, 10) * envolvente(n, 0.003, dur * 0.6)


def _piano_electrico(freq, dur):
    """Piano electrico suave (seno + armonicos que se apagan antes)."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    onda = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t / 0.3)
            + 0.12 * np.sin(2 * np.pi * 7 * freq * t) * np.exp(-t / 0.05))
    return onda * envolvente(n, 0.004, dur * 0.8)


def _eco(señal, retardo, ganancia, repeticiones=3):
    """Ecos (delay) que se van apagando."""
    salida = señal.copy()
    paso = int(SR * retardo)
    for k in range(1, repeticiones + 1):
        if paso * k >= len(señal):
            break
        salida[paso * k:] += señal[:-paso * k] * ganancia ** k
    return salida


def _tema_synth(bpm, tonica, acordes, compases, figura_bajo, melodia, glitch=False, empuje=2.0):
    """Tema electronico (darksynth): bombo en negras, palmas en 2 y 4, hats
    a contratiempo, bajo con la figura de 16 semicorcheas sobre la raiz de
    cada acorde, colchon de supersierras y arpegios (rotos si glitch).
    acordes: un acorde por compas (semitonos sobre la tonica), se repiten
    hasta llenar `compases`. melodia: (semitono sobre tonica x4, corcheas)
    desde el compas 5."""
    pulso = 60.0 / bpm
    compas = pulso * 4
    semi = compas / 16
    largo = int(SR * compas * compases) + 1
    bajo, bateria, colchon, arpegio, lead = (np.zeros(largo) for _ in range(5))
    bombo, palmas, hat = _bombo_tecno(0.3), _palmas(), _hat_abierto(0.05)
    for c in range(compases):
        inicio = c * compas
        acorde = acordes[c % len(acordes)]
        f_raiz = tonica * 2 ** (acorde[0] / 12)
        for k in range(4):
            _poner(bateria, bombo, inicio + k * pulso, 0.9)
            _poner(bateria, hat, inicio + k * pulso + pulso / 2, 0.35)
        for k in (1, 3):
            _poner(bateria, palmas, inicio + k * pulso, 0.55)
        for k, paso in enumerate(figura_bajo):
            if paso is not None:
                _poner(bajo, _bajo_synth(f_raiz * 2 ** (paso / 12), semi * 0.95), inicio + k * semi, 0.6)
        n = int(SR * compas)
        for nota in acorde:
            capa = suavizar(_supersierra(tonica * 4 * 2 ** (nota / 12), compas, voces=5, semilla=c), 14)
            _poner(colchon, capa * envolvente(n, 0.15, compas * 1.5), inicio, 0.14)
        notas = [acorde[i % len(acorde)] + 12 * (i // len(acorde) % 2) for i in range(16)]
        for k in range(16):
            if glitch and (k * 5 + c) % 7 == 0:
                continue
            f = tonica * 8 * 2 ** (notas[k] / 12)
            voz = _arpegio_glitch(f, semi) if glitch else _sinte_impostor(f, semi * 0.9)
            _poner(arpegio, voz, inicio + k * semi, 0.1)
    t = 4 * compas
    i = 0
    while t < largo / SR - 1e-6:
        semitono, corcheas = melodia[i % len(melodia)]
        dur = corcheas * pulso / 2
        if semitono is not None:
            _poner(lead, _sinte_lead(tonica * 4 * 2 ** (semitono / 12), dur), t, 0.3)
        t += dur
        i += 1
    lead = _eco(lead, pulso * 0.75, 0.35)
    mezcla = bajo * 0.6 + bateria * 0.8 + colchon + arpegio + lead
    return _ganar_volumen(fundido_de_bucle(mezcla), empuje=empuje)


def generar_musica_jefe_netrunner():
    """Netrunner Fantasma: darksynth en La menor a 124 BPM, bajo que bombea
    en octavas, arpegios rotos (bitcrush) y un lead con ecos."""
    acordes = [(0, 3, 7), (0, 3, 7), (-4, 0, 3), (-4, 0, 3), (3, 7, 10), (3, 7, 10), (-2, 2, 5), (-1, 2, 5)]
    bajo = [0, None, 12, 0, None, 0, 12, None, 0, None, 12, 0, 3, None, 12, 0]
    melodia = [(12, 2), (15, 2), (19, 3), (17, 1), (15, 2), (12, 2), (10, 2), (12, 6), (None, 2),
               (8, 2), (12, 2), (15, 3), (14, 1), (12, 2), (10, 2), (7, 2), (10, 6), (None, 2)]
    return _tema_synth(124, 55.0, acordes, 24, bajo, melodia, glitch=True)


def generar_musica_jefe_tarantula():
    """Tarantula-9: metal industrial en Re# a 170 BPM con arpegios rotos y
    guitarras gemelas."""
    bpm, tonica = 170, 77.78
    riff = [0, 0, None, 0, 0, None, 1, 0, 0, None, 0, 0, 6, "-", 5, "-"]
    riff_b = [0, None, 0, 0, 3, None, 0, 0, 5, None, 3, 0, 1, "-", 0, None]
    melodia = [(12, 1), (13, 1), (15, 1), (18, 1), (17, 2), (15, 2), (13, 1), (12, 1), (10, 1), (12, 1),
               (13, 4), (12, 2), (15, 2), (18, 2), (17, 2), (15, 6), (None, 2)]
    secciones = [(riff, [0, 0, 1, 0], "thrash", False),
                 (riff_b, [0, 0, 3, 1, 0, 0, 6, 5], "thrash", True),
                 (riff, [0, 1, 3, 1], "doble", True)]
    return _tema_metal(bpm, tonica, secciones, ganancia=13, melodia=melodia, voz_melodia="gemelas",
                       golpes_bronce=False, glitch=True, empuje=2.1)


def generar_musica_jefe_kaiser():
    """Kaiser Cromado (ultimo jefe cyberpunk): metal epico en Re menor a
    150 BPM con bronces, coro y arpegios electronicos rotos."""
    bpm, tonica = 150, 73.42
    riff = [0, "-", 0, 0, 3, "-", 0, 0, 5, "-", 3, 0, 7, "-", 5, "-"]
    riff_b = [0, 0, 0, None, 0, 0, 0, None, 1, 1, 1, None, 3, "-", 1, "-"]
    melodia = [(12, 2), (15, 2), (19, 4), (17, 2), (15, 2), (14, 2), (15, 2), (12, 8),
               (10, 2), (12, 2), (15, 4), (14, 2), (12, 2), (10, 2), (7, 2), (12, 8)]
    secciones = [(riff, [0, 0, -2, 0], "galope", False),
                 (riff_b, [0, 0, -4, -2, 0, 0, 3, 1], "doble", True),
                 (riff, [0, -2, -4, -5], "blast", True)]
    return _tema_metal(bpm, tonica, secciones, ganancia=12, melodia=melodia, voz_melodia="bronces",
                       golpes_bronce=True, coro=True, glitch=True, empuje=2.1)


def generar_musica_luna():
    """Final de la ruta cyberpunk (el viaje a la Luna): balada synthwave
    melancolica en Mi mayor a 84 BPM, medio tiempo, piano electrico,
    colchon calido, bajo redondo y un lead con ecos largos. Si en
    assets/audio/music hay una cancion propia cuyo nombre la nombre
    (ver audio._PALABRAS_CANCION_PROPIA["luna"]), suena esa en su lugar."""
    bpm, tonica = 84, 82.41
    pulso = 60.0 / bpm
    compas = pulso * 4
    # Mi, Do#m, La, Si (un compas cada uno)
    acordes = [(0, 4, 7, 11), (-3, 0, 4, 7), (-7, -3, 0, 4), (-5, -1, 2, 7)]
    melodia = [(7, 2), (4, 2), (2, 1), (4, 3), (4, 2), (2, 2), (0, 2), (-1, 2),
               (0, 3), (2, 1), (4, 2), (7, 2), (11, 4), (7, 2), (2, 2),
               (11, 2), (9, 2), (7, 2), (4, 2), (9, 3), (7, 1), (4, 4),
               (4, 2), (7, 2), (9, 2), (11, 2), (14, 4), (11, 4)]
    compases = 16
    largo = int(SR * compas * compases) + 1
    bajo, bateria, colchon, piano, lead = (np.zeros(largo) for _ in range(5))
    bombo, palmas, hat = _bombo_tecno(0.35), _palmas(0.4), _hat_abierto(0.04)
    for c in range(compases):
        inicio = c * compas
        acorde = acordes[c % len(acordes)]
        f_raiz = tonica * 2 ** (acorde[0] / 12)
        if c >= 2:
            _poner(bateria, bombo, inicio, 0.8)
            _poner(bateria, bombo, inicio + pulso * 2.5, 0.5)
            _poner(bateria, palmas, inicio + pulso * 2, 0.45)
            for k in range(8):
                _poner(bateria, hat, inicio + k * pulso / 2, 0.18 if k % 2 else 0.1)
        nb = int(SR * compas)
        _poner(bajo, onda_seno(f_raiz, compas) * envolvente(nb, 0.02, compas * 0.9), inicio, 0.5)
        _poner(bajo, onda_seno(f_raiz, pulso * 1.5) * envolvente(int(SR * pulso * 1.5), 0.02, pulso),
               inicio + pulso * 2.5, 0.35)
        for nota in acorde:
            capa = suavizar(_supersierra(tonica * 4 * 2 ** (nota / 12), compas, voces=5, desafino=0.004, semilla=c), 24)
            _poner(colchon, capa * envolvente(nb, 0.4, compas * 2.5), inicio, 0.12)
            for k in (0, 1.5, 3):
                _poner(piano, _piano_electrico(tonica * 4 * 2 ** (nota / 12), pulso * 1.4), inicio + k * pulso, 0.1)
    t = 4 * compas
    i = 0
    while t < largo / SR - 1e-6:
        semitono, corcheas = melodia[i % len(melodia)]
        dur = corcheas * pulso / 2
        if semitono is not None:
            _poner(lead, _sinte_lead(tonica * 4 * 2 ** (semitono / 12), dur * 1.1), t, 0.28)
            _poner(lead, onda_seno(tonica * 8 * 2 ** (semitono / 12), dur) * envolvente(int(SR * dur), 0.01, dur),
                   t, 0.08)
        t += dur
        i += 1
    lead = _eco(lead, pulso * 0.75, 0.45, repeticiones=4)
    bateria = _eco(bateria, pulso * 0.5, 0.2, repeticiones=2)
    mezcla = bajo * 0.7 + bateria * 0.6 + colchon + piano + lead
    return _ganar_volumen(fundido_de_bucle(mezcla, ms=120), empuje=1.5, pico=0.9)


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
    "musica_juego": lambda: generar_musica_juego_metal(0),
    "musica_juego_metal1": lambda: generar_musica_juego_metal(1),
    "musica_juego_metal2": lambda: generar_musica_juego_metal(2),
    "musica_juego_metal3": lambda: generar_musica_juego_metal(3),
    "musica_juego_metal4": lambda: generar_musica_juego_metal(4),
    "musica_menu": generar_musica_menu,
    "musica_muerte": generar_musica_muerte,
    "musica_jefe_sentinel": generar_musica_jefe_sentinel,
    "musica_jefe_dragon": generar_musica_jefe_dragon,
    "musica_jefe_titan": generar_musica_jefe_titan,
    "musica_jefe_anomalia": generar_musica_jefe_anomalia,
    "musica_jefe_mega": generar_musica_jefe_mega,
    "musica_jefe_nyan": generar_musica_jefe_nyan,
    # mismo chiptune para el duo de sub-jefes: asi, si musica_jefe_nyan se
    # reemplaza por una cancion propia (.mp3/.ogg), esa suena solo en la
    # fase de Nyan Cat
    "musica_jefe_gatos": generar_musica_jefe_nyan,
    "musica_jefe_pan": generar_musica_jefe_pan,
    "musica_impostor": generar_musica_impostor,
    "musica_jefe_calabaza": generar_musica_jefe_calabaza,
    "musica_jefe_bruja": generar_musica_jefe_bruja,
    "musica_jefe_bruja_gigante": generar_musica_jefe_bruja_gigante,
    "musica_jefe_parca": generar_musica_jefe_parca,
    "musica_fin_halloween": generar_musica_fin_halloween,
    "musica_dimension_parca": generar_musica_dimension_parca,
    "musica_jefe_netrunner": generar_musica_jefe_netrunner,
    "musica_jefe_tarantula": generar_musica_jefe_tarantula,
    "musica_jefe_kaiser": generar_musica_jefe_kaiser,
    "musica_luna": generar_musica_luna,
    "musica_cuna": generar_musica_cuna,
    "musica_victoria_tecno": generar_musica_victoria_tecno,
    "musica_glitch_epica": generar_musica_glitch_epica,
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
