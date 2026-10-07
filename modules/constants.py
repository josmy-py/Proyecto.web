"""
Constantes globales del juego: dimensiones de pantalla, paleta de colores,
indices de landmarks de MediaPipe, y la configuracion de oleadas/jefes/
buffs/dificultad. No depende de ningun otro modulo del proyecto a
proposito, para poder importarse desde cualquier lado sin ciclos."""

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
GAME_WIDTH = 960
GAME_HEIGHT = 640
PREVIEW_WIDTH = 240
PREVIEW_HEIGHT = 160
FPS = 60

WHITE = (255, 255, 255)
ROSA = (255, 130, 150)
MENTA = (120, 255, 170)
AMARILLO = (255, 235, 160)
AZUL = (140, 210, 255)
AZUL_CIELO = (100, 170, 255)
MELON = (255, 190, 140)
LAVANDA = (200, 150, 255)
ROSA_CHICLE = (255, 160, 210)
DARK_BG = (18, 18, 45)
DARKER_BG = (10, 10, 30)

ELECTRICO = (185, 240, 255)

GLASS_WHITE = (255, 255, 255, 25)
GLASS_BLACK = (0, 0, 0, 40)
SHADOW = (0, 0, 0, 60)

SHIP_WIDTH = 40
SHIP_HEIGHT = 32

WRIST_IDX = 0
INDEX_TIP_IDX = 8
INDEX_PIP_IDX = 6
MIDDLE_TIP_IDX = 12
MIDDLE_PIP_IDX = 10
RING_TIP_IDX = 16
RING_PIP_IDX = 14
PINKY_TIP_IDX = 20
PINKY_PIP_IDX = 18

FIST_BURST_SHOTS = 1
FIST_CONFIRM_FRAMES = 2

GAMEPAD_MOVE_SPEED = 10.0
GAMEPAD_DEADZONE = 0.2

POWERUP_SPAWN_EVERY = 5

# Nave bonus (ver modules/entities/enemy.py: tank/interceptor/bomber
# reciclan los sprites de assets/sprites/ships que dejo libres quitar la
# seleccion de clase de nave del jugador). Aparece rara vez a partir de
# BONUS_SHIP_MIN_WAVE, ya no muere de un solo golpe (ver "hp" en
# BONUS_SHIP_VARIANTS) y suelta varios power-ups de golpe al ser
# destruida -menos que antes, para que no se sienta gratuita.
BONUS_SHIP_MIN_WAVE = 3
BONUS_SHIP_SPAWN_CHANCE = 0.16
BONUS_SHIP_POWERUP_COUNT = 3
BONUS_SHIP_SCORE = 300

# De vez en cuando (BONUS_SHIP_MINIBOSS_CHANCE, se sortea aparte de la
# chance de aparicion normal de arriba) la nave bonus que le toca aparecer
# se activa como mini-jefe: mas grande, mucho mas resistente y con
# ataques de nave de combate real (salvas de misiles con homing suave,
# ver AlienShip.is_miniboss/AlienMissile en modules/entities/enemy.py),
# a cambio de una recompensa proporcionalmente mayor.
BONUS_SHIP_MINIBOSS_CHANCE = 0.14
BONUS_SHIP_MINIBOSS_POWERUP_MULT = 2.5
BONUS_SHIP_MINIBOSS_SCORE_MULT = 3.0

DIFICULTADES = {
    "facil": 0.75,
    "normal": 1.0,
    "dificil": 1.8,
}
DIFICULTAD_DEFECTO = "normal"

FINAL_BOSS_SPAWN_WAVE = 40

# Cuota de objetivos (asteroides + naves alienigenas) para que una oleada
# pase a la siguiente: WAVE_OBJETIVOS_INICIAL en las oleadas 1 a
# WAVE_OBJETIVOS_HASTA_OLEADA y WAVE_OBJETIVOS_AVANZADO de ahi en adelante
# (ver cuota_de_oleada). Reemplaza el avance por tiempo de antes, para que
# el juego no "salte" oleadas sin que el jugador haya hecho nada.
WAVE_OBJETIVOS_INICIAL = 10
WAVE_OBJETIVOS_AVANZADO = 15
WAVE_OBJETIVOS_HASTA_OLEADA = 30


def cuota_de_oleada(wave):
    """Objetivos a destruir para pasar la oleada `wave`."""
    if wave <= WAVE_OBJETIVOS_HASTA_OLEADA:
        return WAVE_OBJETIVOS_INICIAL
    return WAVE_OBJETIVOS_AVANZADO

# Oleada del mega-jefe final unico (dos fases: crucero -> esfera de combate).
MEGA_BOSS_SPAWN_WAVE = 50

BUFF_TYPE_EXTRA_LIFE = "extra_life"
BUFF_TYPE_FAST_SHOOT = "fast_shoot"
BUFF_TYPE_TRIPLE_SHOT = "triple_shot"
BUFF_TYPE_SHIELD = "shield"
BUFF_TYPE_PIERCING = "piercing"
BUFF_TYPE_ATTRACT = "attract"
BUFF_TYPE_DAMAGE_UP = "damage_up"
BUFF_TYPE_SPEED_UP = "speed_up"
BUFF_TYPE_MAX_LIFE_UP = "max_life_up"
BUFF_TYPE_RAPID_FIRE = "rapid_fire"
BUFF_TYPE_LIGHTNING = "lightning_field"
BUFF_DURATION = 900
# Duracion base de los buffs con tiempo: 20 segundos para todos (antes
# variaba entre ~10 y 15s segun el buff). Ver Ship._extender_buff para la
# curva de apilado al agarrar el mismo power-up de nuevo mientras sigue
# activo: 1ra vez dura esto; 2da vez se duplica lo que quedaba; de la 3ra
# en adelante cada agarrada solo suma BUFF_STACK_BONUS mas.
BUFF_DURATION_FAST = 20 * FPS
BUFF_DURATION_TRIPLE = 20 * FPS

# Tres balas por disparo ya es 3x el daño de un tiro normal (cada bala
# pega igual); esta penalidad de cadencia (Ship.apply_buff, se revierte al
# expirar) baja un poco ese total sin tocar el daño por bala -+18% de
# tiempo entre disparos, ~15% menos daño por segundo neto- para que siga
# siendo fuerte pero no rompa el ritmo contra los jefes.
TRIPLE_SHOT_CADENCIA_PENALIDAD = 1.18
BUFF_DURATION_SHIELD = 20 * FPS
BUFF_DURATION_PIERCING = 20 * FPS
BUFF_DURATION_ATTRACT = 20 * FPS
BUFF_DURATION_DAMAGE_UP = 99999
BUFF_DURATION_SPEED_UP = 99999
BUFF_DURATION_MAX_LIFE_UP = 99999
BUFF_DURATION_RAPID_FIRE = 99999
BUFF_DURATION_LIGHTNING = 20 * FPS
BUFF_STACK_BONUS = 10 * FPS
LIGHTNING_ZAP_INTERVAL = 12
LIGHTNING_RADIUS = 130

RED = ROSA
GREEN = MENTA
YELLOW = AMARILLO
CYAN = AZUL
BLUE = AZUL_CIELO
ORANGE = MELON
PURPLE = LAVANDA
PINK = ROSA_CHICLE