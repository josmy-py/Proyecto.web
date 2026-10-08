"""
Punto de entrada del juego: inicializa pygame/camara/MediaPipe y corre el
bucle principal (60 FPS) dentro de main(). Ahi vive el estado de la
partida (nave, listas de entidades, puntaje, estadisticas) y se coordinan
todos los modulos: control de mano (modules/systems/input.py), dibujo
(modules/systems/ui.py y modules/systems/menu.py), audio
(modules/systems/audio.py) y persistencia (modules/progress.py,
modules/settings.py)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import pygame
import random
import math

from modules.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GAME_WIDTH, GAME_HEIGHT,
    PREVIEW_WIDTH, PREVIEW_HEIGHT, FPS,
    WHITE, RED, GREEN, CYAN, ORANGE, DARK_BG, DARKER_BG,
    PURPLE, PINK, ROSA, AMARILLO,
    AZUL, AZUL_CIELO, ROSA_CHICLE, MENTA, ELECTRICO, BUFF_TYPE_EXTRA_LIFE, BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT, BUFF_TYPE_SHIELD,
    BUFF_TYPE_PIERCING, BUFF_TYPE_ATTRACT, BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_SPEED_UP,
    BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_RAPID_FIRE, BUFF_TYPE_LIGHTNING, POWERUP_SPAWN_EVERY,
    SHIP_WIDTH, SHIP_HEIGHT, FINAL_BOSS_SPAWN_WAVE,
    MEGA_BOSS_SPAWN_WAVE, cuota_de_oleada, DIFICULTADES,
    DIFICULTAD_DEFECTO, GAMEPAD_MOVE_SPEED,
    GAMEPAD_DEADZONE,
    BONUS_SHIP_MIN_WAVE, BONUS_SHIP_SPAWN_CHANCE,
    BONUS_SHIP_POWERUP_COUNT, BONUS_SHIP_SCORE,
    BONUS_SHIP_MINIBOSS_CHANCE, BONUS_SHIP_MINIBOSS_POWERUP_MULT, BONUS_SHIP_MINIBOSS_SCORE_MULT,
)
from modules.entities.ship import Ship
from modules.entities.enemy import AlienShip, BONUS_SHIP_KINDS
from modules.entities.asteroid import Asteroid, Particle, Explosion
from modules.entities.powerup import PowerUp, random_buff_type
from modules.systems.input import (
    init_hand_landmarker,
    process_camera_frame,
    set_frame_skip,
    is_fist,
    find_hand_position,
)
from modules.systems.ui import draw_hud, draw_countdown, draw_camera_preview, draw_game_over, draw_buff_hud, draw_victory_screen, draw_boss_rewards, draw_viewport_frame, draw_ship_status_bar, draw_victory_final
from modules.core.boss_system import get_boss_for_wave, WaveBoss, BossReward
from modules.entities.boss import FinalBoss
from modules.entities.titan_boss import TitanBoss
from modules.entities.dragon_boss import DragonBoss
from modules.entities.mega_boss import MegaBoss
from modules.entities.nyan_boss import (
    JefeGatoBase, NyanBoss, GatoPanBoss, GatoAlienBoss,
    FondoPixel, pixelar, dibujar_scanlines, PIXEL_BONUS,
    CinematicaGatoDormido, CinematicaVictoriaFalsa, sprite_pixel,
)
from modules.entities.tripulante import TripulanteAliado, CinematicaTripulante
from modules.entities import mascota as mascota_mod
from modules.entities.mascota import ZorritoEspacial, CapsulaMascota, dibujar_aviso_mascota
from modules.systems.menu import MenuScene, Star
from modules.systems import audio
from modules.systems import sprites
from modules.systems.fonts import render_text, render_texto_pixelado, get_font
from modules import progress
from modules import settings

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'hand_landmarker.task')


_RGB_SURF = None


def resize_frame(frame, w, h):
    return cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)


def surface_from_frame(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def dibujar_rayo(surface, lb):
    """Descarga del bonus 'campo electrico': una linea quebrada de la nave
    al objetivo, mas tenue en cada frame hasta desaparecer."""
    x1, y1, x2, y2 = lb['x1'], lb['y1'], lb['x2'], lb['y2']
    alpha = max(0, int(255 * (lb['life'] / lb['max_life'])))
    dist = math.hypot(x2 - x1, y2 - y1)
    segmentos = max(2, int(dist // 18))
    puntos = [(x1, y1)]
    for i in range(1, segmentos):
        t = i / segmentos
        px = x1 + (x2 - x1) * t
        py = y1 + (y2 - y1) * t
        nx, ny = -(y2 - y1), (x2 - x1)
        largo_normal = math.hypot(nx, ny) or 1
        offset = random.uniform(-8, 8)
        px += (nx / largo_normal) * offset
        py += (ny / largo_normal) * offset
        puntos.append((px, py))
    puntos.append((x2, y2))

    ancho_surf = int(abs(x2 - x1)) + 40
    alto_surf = int(abs(y2 - y1)) + 40
    off_x = min(x1, x2) - 20
    off_y = min(y1, y2) - 20
    bolt_surf = pygame.Surface((max(1, ancho_surf), max(1, alto_surf)), pygame.SRCALPHA)
    local_pts = [(px - off_x, py - off_y) for px, py in puntos]
    pygame.draw.lines(bolt_surf, (*WHITE[:3], alpha), False, local_pts, 3)
    pygame.draw.lines(bolt_surf, (*ELECTRICO[:3], alpha), False, local_pts, 1)
    surface.blit(bolt_surf, (off_x, off_y))


def main():
    pygame.init()
    pygame.joystick.init()
    progress.cargar()
    settings.cargar()
    audio.inicializar()
    audio.set_volumen_musica(settings.get("volumen_musica"))
    audio.set_volumen_sfx(settings.get("volumen_sfx"))
    if settings.get("silenciado"):
        audio.alternar_silencio()

    fullscreen = settings.get("pantalla_completa")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN if fullscreen else 0)
    pygame.display.set_caption("Nave vs Asteroides")
    clock = pygame.time.Clock()
    font = get_font(24)
    big_font = get_font(48)
    info_font = get_font(20)
    small_font = get_font(18)

    game_offset_x = (SCREEN_WIDTH - GAME_WIDTH) // 2
    game_offset_y = (SCREEN_HEIGHT - GAME_HEIGHT) // 2

    # La camara y el detector de MediaPipe se cargan recien cuando hace
    # falta (modo camara elegido en el menu), asi el modo mando no prende
    # la webcam ni carga el modelo de manos para nada.
    cap = None
    hand_detector = None
    joystick = None
    modo_control = "camara"

    def activar_modo_camara():
        nonlocal cap, hand_detector
        if hand_detector is None:
            set_frame_skip(2)
            hand_detector = init_hand_landmarker(MODEL_PATH)
        if cap is None:
            cap = cv2.VideoCapture(settings.get("camera_index"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv2.CAP_PROP_FPS, 30)

    def activar_modo_mando():
        nonlocal cap, joystick
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
            cap = None
        if joystick is None and pygame.joystick.get_count() > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

    selected_ship_type = "scout"
    selected_skin_id = "default"

    ship = Ship(GAME_WIDTH // 2, GAME_HEIGHT - 60, selected_ship_type, selected_skin_id)
    bullets = []
    asteroids = []
    powerups = []
    alien_ships = []
    alien_bullets = []
    bosses = []
    boss_bullets = []
    explosions = []
    particles = []
    lightning_bolts = []
    score = 0
    wave = 1
    objetivos_oleada = 0
    spawn_timer = 0
    asteroid_kills = 0
    alien_spawn_timer = 0
    game_over = False
    game_victory = False
    dying = False
    death_timer = 0
    game_over_selected = 0
    GOButtons = [("Volver al Menu", AZUL), ("Intentar de Nuevo", ROSA)]
    hand_active = False
    last_hand_x = GAME_WIDTH // 2
    last_hand_y = GAME_HEIGHT - 60
    frame_count = 0
    countdown_val = 1
    last_boss_rewards = []
    boss_reward_timer = 0
    paused = False
    nuevo_record = False
    dificultad_base = DIFICULTADES[DIFICULTAD_DEFECTO]
    dificultad = dificultad_base
    stats_disparos = 0
    stats_aciertos = 0
    stats_alienigenas = 0
    stats_jefes = 0
    tiempo_sobrevivido = 0.0

    # Jefe bonus secreto (ver modules/entities/nyan_boss.py): al caer el
    # mega-jefe viene la cinematica de VICTORIA falsa (techno, despues
    # musica epica y la pantalla que se rompe con "NEW BOSS READY") y
    # revela un combate en entorno pixel art.
    #   None -> partida normal
    #   "victoria_falsa" -> pendiente la cinematica (corre al inicio del
    #       cuadro siguiente, fuera del bucle de jefes que la disparo)
    #   "nyan" -> pelea contra Nyan Cat
    #   "interludio_alien" -> Nyan cayo, en breve entra el Gato Alien
    #   "alien" -> pelea contra el Gato Alien (arranca INVENCIBLE)
    #   "game_over_falso" -> el Alien invencible te mato: GAME OVER de mentira
    #       y despues la cinematica del tripulante (Among Us) que te devuelve
    #       las vidas y se queda de aliado hasta que cae el Alien
    #   "interludio_pan" -> cayo el Alien, en breve entra el Gato Pan
    #   "pan" -> pelea contra el Gato Pan (gira, "OIIA OIIA")
    #   "final" -> cayo el Gato Pan: cinematica del gatito durmiendo y la victoria de verdad
    #   "terminado" -> victoria real mostrada (sigue el entorno pixel)
    GAME_OVER_FALSO_FRAMES = 170
    congelados_bonus = ("victoria_falsa", "game_over_falso")
    aliado = None

    # Mascota de mitad de partida (ver modules/entities/mascota.py): al
    # llegar a MASCOTA_OLEADA baja una capsula con el Zorrito Espacial; al
    # tocarla se une a la nave por el resto de la partida.
    mascota = None
    capsula_mascota = None
    mascota_ofrecida = False
    aviso_mascota = None
    bonus_estado = None
    bonus_timer = 0
    # Punto de partida elegido en el menu (ELEGIR FASE, ver FASES_INICIO en
    # modules/systems/menu.py): "wN" arranca en la oleada N; "nyan"/"alien"/
    # "pan" entran directo a ese jefe del bonus al terminar la cuenta
    # regresiva (sin la partida normal ni la victoria falsa; AJUSTES > "JUGAR
    # NIVEL BONUS" equivale a "nyan"). "Intentar de nuevo" lo respeta.
    JEFES_BONUS_DIRECTOS = ("nyan", "alien", "pan")
    inicio_partida = "w1"
    # ELEGIR FASE con "TODOS LOS BUFFS": la nave arranca con todo (ver
    # _dar_todos_los_buffs)
    inicio_con_buffs = False
    bonus_directo_pendiente = None
    bonus_banner = None
    fondo_pixel = None

    # Fondo de estrellas de la partida (independiente del que usa el menu).
    # No se reinicia entre partidas, es solo decoracion de fondo.
    estrellas_juego = [Star(GAME_WIDTH, GAME_HEIGHT) for _ in range(90)]

    # Estrellas de fondo para el margen fuera del area de juego (la franja
    # entre el borde de la pantalla y el marco cian): sin esto se veia un
    # borde plano de color solido; con esto el espacio "sigue" mas alla del
    # viewport en vez de cortarse en seco.
    estrellas_fondo = [Star(SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(150)]

    menu_scene = MenuScene(SCREEN_WIDTH, SCREEN_HEIGHT)

    start_time = pygame.time.get_ticks()
    start_countdown = 5

    def reset_game():
        nonlocal ship, bullets, asteroids, powerups, alien_ships, alien_bullets
        nonlocal bosses, boss_bullets, explosions, particles, lightning_bolts
        nonlocal score, wave, objetivos_oleada, spawn_timer, asteroid_kills, alien_spawn_timer
        nonlocal game_over, game_victory, dying, death_timer, game_over_selected
        nonlocal last_boss_rewards, boss_reward_timer, start_time, start_countdown
        nonlocal paused, nuevo_record, dificultad
        nonlocal stats_disparos, stats_aciertos, stats_alienigenas, stats_jefes, tiempo_sobrevivido
        nonlocal bonus_estado, bonus_timer, bonus_banner, fondo_pixel, bonus_directo_pendiente, aliado
        nonlocal mascota, capsula_mascota, mascota_ofrecida, aviso_mascota
        if hasattr(draw_hud, 'hud'):
            del draw_hud.hud
        if hasattr(draw_buff_hud, 'hud'):
            del draw_buff_hud.hud
        ship = Ship(GAME_WIDTH // 2, GAME_HEIGHT - 60, selected_ship_type, selected_skin_id)
        bullets.clear(); asteroids.clear(); powerups.clear()
        alien_ships.clear(); alien_bullets.clear()
        bosses.clear(); boss_bullets.clear()
        explosions.clear(); particles.clear(); lightning_bolts.clear()
        score = 0; wave = 1; objetivos_oleada = 0; spawn_timer = 0
        asteroid_kills = 0; alien_spawn_timer = 0
        game_over = False; game_victory = False
        dying = False; death_timer = 0; game_over_selected = 0
        last_boss_rewards = []; boss_reward_timer = 0
        paused = False; nuevo_record = False
        dificultad = dificultad_base
        stats_disparos = 0; stats_aciertos = 0
        stats_alienigenas = 0; stats_jefes = 0; tiempo_sobrevivido = 0.0
        bonus_estado = None; bonus_timer = 0; bonus_banner = None; fondo_pixel = None
        aliado = None
        mascota = None; capsula_mascota = None; mascota_ofrecida = False; aviso_mascota = None
        if inicio_partida in JEFES_BONUS_DIRECTOS:
            bonus_directo_pendiente = inicio_partida
            # la cuenta regresiva ya se ve sobre el cielo pixel del bonus
            fondo_pixel = FondoPixel()
        else:
            bonus_directo_pendiente = None
            wave = int(inicio_partida[1:])
        if inicio_con_buffs:
            _dar_todos_los_buffs()
        start_time = pygame.time.get_ticks()
        start_countdown = 5
        _musica_partida()

    def _musica_partida():
        """Musica de la partida entre jefes: cada jefe de oleada que queda
        atras la hace mas pesada (musica_juego en las oleadas 1-10 y
        musica_juego_metal1..4 en 11-20, 21-30, 31-40 y 41-50). Se puede
        llamar todos los cuadros: no reinicia la pista si ya esta sonando."""
        nivel = min(4, max(0, (wave - 1) // 10))
        audio.reproducir_musica("juego" if nivel == 0 else f"juego_metal{nivel}")

    def terminar_partida(victoria):
        """Marca fin de partida (derrota o victoria) y registra el record."""
        nonlocal game_over, game_victory, nuevo_record, tiempo_sobrevivido
        game_over = True
        game_victory = victoria
        tiempo_sobrevivido = max(0.0, (pygame.time.get_ticks() - start_time) / 1000.0 - start_countdown)
        nuevo_record = progress.registrar_partida(score, wave)
        if victoria:
            audio.sonido_victoria()

    def _recompensar_jefe(boss):
        """Recompensa comun a cualquier jefe derrotado (WaveBoss, FinalBoss
        o MegaBoss): entrega los power-ups de su BossDefinition/self.rewards
        y explosion/particulas de celebracion. Los jefes ya NO dan puntaje
        directo (solo lo que el jugador ya sumo destruyendo asteroides y
        naves alienigenas en el camino); derrotar al MegaBoss de la oleada
        MEGA_BOSS_SPAWN_WAVE es la unica forma de terminar la partida con
        "victoria" (La Anomalia Final de la oleada FINAL_BOSS_SPAWN_WAVE ya
        no lo hace, queda como un jefe intermedio mas).

        Ademas, para un WaveBoss/FinalBoss, esta funcion es la que hace
        avanzar `wave` (a spawn_wave + 1): las oleadas de jefe (10/20/30/40)
        quedan excluidas del avance generico por `objetivos_oleada` (ver el
        bucle principal) para que la oleada no pueda saltarse el jefe ni
        quedar pegada peleandolo para siempre; derrotarlo es lo unico que la
        mueve."""
        nonlocal stats_jefes, dificultad, last_boss_rewards, boss_reward_timer
        nonlocal wave, objetivos_oleada
        if isinstance(boss, JefeGatoBase):
            _recompensar_jefe_bonus(boss)
            return
        stats_jefes += 1
        rewards = boss.rewards if isinstance(boss, MegaBoss) else boss.definition.rewards
        last_boss_rewards = list(rewards)
        boss_reward_timer = 180
        for reward in rewards:
            powerups.append(PowerUp(boss.x + random.uniform(-40, 40), boss.y, reward.buff_type))

        if isinstance(boss, MegaBoss):
            for _ in range(6):
                powerups.append(PowerUp(boss.x + random.uniform(-70, 70), boss.y + random.uniform(-20, 20), random_buff_type()))
            explosions.append(Explosion(boss.x, boss.y, WHITE, 100))
            particles.extend([Particle(boss.x, boss.y, AMARILLO) for _ in range(80)])
            particles.extend([Particle(boss.x, boss.y, ORANGE) for _ in range(60)])
            particles.extend([Particle(boss.x, boss.y, WHITE) for _ in range(40)])
            _cinematica_victoria(boss)
            _iniciar_victoria_falsa()
        else:
            explosion_color = ROSA if boss.definition.spawn_wave == FINAL_BOSS_SPAWN_WAVE else RED
            explosion_size = 80 if boss.definition.spawn_wave == FINAL_BOSS_SPAWN_WAVE else 50
            explosions.append(Explosion(boss.x, boss.y, explosion_color, explosion_size))
            particle_count = 50 + boss.definition.spawn_wave
            particles.extend([Particle(boss.x, boss.y, AMARILLO) for _ in range(particle_count)])
            particles.extend([Particle(boss.x, boss.y, ORANGE) for _ in range(max(0, particle_count - 10))])
            audio.sonido_victoria()
            dificultad += 0.2
            wave = boss.definition.spawn_wave + 1
            objetivos_oleada = 0

    def _cinematica_victoria(boss):
        """Cutscene final al derrotar al mega-jefe (unica forma de terminar
        la partida con "victoria"), en dos tiempos:

          EXPLOSION: el mega-jefe estalla en pedazos reales -recorta su
          propio sprite, como el resto de fragmentaciones de MegaBoss, en
          vez de una forma vectorial- con miles de destellos acumulados
          cuadro a cuadro.

          ESCAPE: la nave del jugador -mas dos naves escolta- sale
          disparada hacia ARRIBA (alejandose de donde quedo la explosion)
          dejando su propio rastro de explosiones chicas detras, entre
          estelas de hiperespacio; la "camara" (un desplazamiento vertical
          que se le aplica a todo lo que esta en el mundo, ver camera_y)
          las sigue duranta varios segundos en vez de dejarlas salir de
          cuadro de inmediato -con ganancia 0.22 + un CLAMP duro
          (MAX_LAG_CAM) para que la nave nunca quede fuera de cuadro por
          mas que acelere; con la ganancia vieja (0.06) el retraso crecia
          sin limite y la nave terminaba saliendose por arriba.

        Corre en su propio mini-bucle, con su propio pump de eventos/tick/
        flip, en vez de sumar un estado mas al bucle principal: es un
        cutscene de duracion fija, no una mecanica de juego que deba
        conservarse en reset_game()."""
        cx0, cy0 = boss.x, boss.y

        # El mini-bucle no llama a ship.update(), asi que si el jefe cae
        # durante el parpadeo de invencibilidad el timer quedaria congelado
        # y Ship.draw() se saltaria la nave en todos los cuadros.
        ship.invincible_timer = 0

        sprite_actual = sprites.get_mega_boss_surface(boss.phase_name)
        pedazos = []
        if sprite_actual is not None:
            display_w, display_h = sprite_actual.get_size()
            cols, filas = 10, 8
            pw, ph = display_w / cols, display_h / filas
            for fila in range(filas):
                for col in range(cols):
                    rx0, ry0 = int(col * pw), int(fila * ph)
                    rx1 = display_w if col == cols - 1 else int((col + 1) * pw)
                    ry1 = display_h if fila == filas - 1 else int((fila + 1) * ph)
                    rect = pygame.Rect(rx0, ry0, max(1, rx1 - rx0), max(1, ry1 - ry0))
                    pieza = sprite_actual.subsurface(rect).copy()
                    base_x = rect.centerx - display_w / 2.0
                    base_y = rect.centery - display_h / 2.0
                    dist = math.hypot(base_x, base_y) or 1.0
                    pedazos.append({
                        'surf': pieza,
                        'x': cx0 + base_x, 'y': cy0 + base_y,
                        'vx': (base_x / dist) * random.uniform(2.2, 6.5),
                        'vy': (base_y / dist) * random.uniform(2.2, 6.5),
                        'ang': 0.0, 'ang_vel': random.uniform(-10, 10),
                        'vida': random.randint(110, 170),
                    })

        # Dos naves escolta que se le suman a la nave del jugador para la
        # huida (reciclan el sprite "scout" con otro tinte, no son
        # AlienShip ni nada que el resto del juego necesite conocer).
        escoltas = []
        for dx, dy, color in ((-70, 26, AZUL_CIELO), (70, 34, MENTA)):
            aw = int(SHIP_WIDTH * 1.05)
            ah = int(aw * SHIP_HEIGHT / SHIP_WIDTH)
            spr = sprites.get_ship_surface("scout", color, tuple(int(c * 0.68) for c in color[:3]), aw, ah)
            escoltas.append({'x': ship.x + dx, 'y': ship.y + dy, 'spr': spr, 'fase': random.uniform(0, 6.28),
                              'rastro_timer': random.randint(0, 8)})

        estelas = []
        explosiones_cine = []
        particulas_cine = []
        camera_y = 0.0
        ANCLA_Y = GAME_HEIGHT * 0.58
        rastro_timer_ship = 0

        fase = "explosion"
        timer = 0
        DUR_EXPLOSION = 130
        DUR_ESCAPE = 220
        shake = 0

        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            clock.tick(FPS)
            timer += 1

            for p in pedazos:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['vx'] *= 0.992
                p['vy'] *= 0.992
                p['ang'] += p['ang_vel']
                p['vida'] -= 1
            pedazos[:] = [p for p in pedazos if p['vida'] > 0]

            if fase == "explosion":
                for _ in range(random.randint(14, 22)):
                    ang = random.uniform(0, 2 * math.pi)
                    rad = random.uniform(0, 160)
                    particulas_cine.append({
                        'x': cx0 + math.cos(ang) * rad, 'y': cy0 + math.sin(ang) * rad,
                        'vx': random.uniform(-1.5, 1.5), 'vy': random.uniform(-1.5, 1.5),
                        'vida': random.randint(8, 22), 'vida_max': 22,
                        'color': random.choice([WHITE, AMARILLO, ORANGE, ROSA]),
                        'r': random.randint(1, 3),
                    })
                if timer % 18 == 0:
                    explosiones_cine.append(Explosion(
                        cx0 + random.uniform(-60, 60), cy0 + random.uniform(-40, 40),
                        random.choice([WHITE, AMARILLO, ORANGE]), random.randint(30, 60),
                    ))
                    shake = 10
                    audio.sonido_explosion()
                if timer >= DUR_EXPLOSION:
                    fase = "escape"
                    timer = 0
                    audio.sonido_explosion()
                    explosiones_cine.append(Explosion(cx0, cy0, WHITE, 140))
                    shake = 22

            elif fase == "escape":
                # se aleja de la explosion (que quedo donde estaba el
                # mega-jefe) disparandose hacia ARRIBA; la camara la sigue
                # -camera_y persigue a la nave con un suavizado, en vez de
                # engancharse de golpe- para que se la vea escapar en
                # pantalla en vez de perderla de vista al instante.
                t = min(1.0, timer / 40.0)
                velocidad = 4 + 22 * t * t
                ship.y -= velocidad
                ship.x += math.sin(timer * 0.05) * 1.4
                for esc in escoltas:
                    esc['fase'] += 0.05
                    esc['y'] -= velocidad * 0.96
                    esc['x'] += math.sin(timer * 0.05 + esc['fase']) * 1.6

                # ganancia bastante mas fuerte que antes (0.06 -> 0.22): con
                # la nave acelerando hasta ~26px/frame, un suavizado tan
                # suave se quedaba atras sin limite (el retraso en regimen
                # permanente es velocidad/ganancia) y la nave terminaba
                # saliendose del cuadro por arriba. Ademas un CLAMP duro:
                # pase lo que pase la nave nunca queda a mas de MAX_LAG_CAM
                # del ancla en pantalla, se ve siempre.
                objetivo_camara = ship.y - ANCLA_Y
                camera_y += (objetivo_camara - camera_y) * 0.22
                MAX_LAG_CAM = 130
                camera_y = max(objetivo_camara - MAX_LAG_CAM, min(objetivo_camara + MAX_LAG_CAM, camera_y))

                # rastro de explosiones chicas detras de cada nave (la del
                # jugador y las dos escoltas): se sueltan cada tantos
                # cuadros en la posicion ACTUAL, y como ya no se mueven se
                # quedan marcando el camino recorrido.
                rastro_timer_ship -= 1
                if rastro_timer_ship <= 0:
                    rastro_timer_ship = random.randint(9, 14)
                    explosiones_cine.append(Explosion(ship.x, ship.y + 30, random.choice([WHITE, AZUL_CIELO]), 22))
                for esc in escoltas:
                    esc['rastro_timer'] -= 1
                    if esc['rastro_timer'] <= 0:
                        esc['rastro_timer'] = random.randint(10, 16)
                        explosiones_cine.append(Explosion(esc['x'], esc['y'] + 24, MENTA, 16))

                # estelas de hiperespacio: nacen arriba y bajan -quedan
                # "atras" de la nave que sube, como el fondo corriendo
                # hacia atras cuando se acelera hacia adelante.
                if random.random() < 0.9:
                    estelas.append({
                        'x': random.uniform(0, GAME_WIDTH), 'y': -10,
                        'largo': random.uniform(40, 140), 'vy': random.uniform(18, 34) * (0.4 + t),
                        'color': random.choice([WHITE, AZUL_CIELO, MENTA]),
                    })
                estelas[:] = [e for e in estelas if e['y'] - camera_y < GAME_HEIGHT + 20]
                for e in estelas:
                    e['y'] += e['vy']

                if timer % 26 == 0 and pedazos:
                    pieza = random.choice(pedazos)
                    explosiones_cine.append(Explosion(pieza['x'], pieza['y'], ORANGE, 24))

                if timer >= DUR_ESCAPE:
                    break

            for p in particulas_cine[:]:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['vida'] -= 1
                if p['vida'] <= 0:
                    particulas_cine.remove(p)

            for ex in explosiones_cine[:]:
                ex.update()
                if not ex.active:
                    explosiones_cine.remove(ex)

            if shake > 0:
                shake -= 1

            cam_y_int = int(camera_y)
            cine_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
            cine_surface.fill(DARK_BG)

            if fase in ("explosion", "escape"):
                for estrella in estrellas_juego:
                    estrella.update()
                    estrella.draw(cine_surface)

                for e in estelas:
                    ex = int(e['x'])
                    ey = int(e['y'] - cam_y_int)
                    pygame.draw.line(cine_surface, e['color'], (ex, ey), (ex, ey + e['largo']), 2)

                for p in pedazos:
                    rotada = pygame.transform.rotate(p['surf'], p['ang'])
                    rect = rotada.get_rect(center=(int(p['x']), int(p['y'] - cam_y_int)))
                    cine_surface.blit(rotada, rect)

                for p in particulas_cine:
                    alpha = p['vida'] / p['vida_max']
                    size = max(1, int(p['r'] * alpha))
                    c = tuple(int(ch * alpha) for ch in p['color'][:3])
                    pygame.draw.circle(cine_surface, c, (int(p['x']), int(p['y'] - cam_y_int)), size)

                for ex in explosiones_cine:
                    ex.draw(cine_surface, offset_y=-cam_y_int)

                for esc in escoltas:
                    if esc['spr'] is not None:
                        rect = esc['spr'].get_rect(center=(int(esc['x']), int(esc['y'] - cam_y_int)))
                        cine_surface.blit(esc['spr'], rect)

                ship.draw(cine_surface, offset_y=-cam_y_int)

            if fase == "explosion" and timer > DUR_EXPLOSION - 25:
                alfa = min(200, int(255 * (timer - (DUR_EXPLOSION - 25)) / 25))
                flash = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
                flash.fill((255, 255, 255, alfa))
                cine_surface.blit(flash, (0, 0))
            if fase == "escape" and timer > DUR_ESCAPE - 30:
                alfa = min(255, int(255 * (timer - (DUR_ESCAPE - 30)) / 30))
                flash = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
                flash.fill((255, 255, 255, alfa))
                cine_surface.blit(flash, (0, 0))

            sx = game_offset_x + (random.randint(-shake, shake) if shake else 0)
            sy = game_offset_y + (random.randint(-shake, shake) if shake else 0)
            screen.fill((0, 0, 0))
            screen.blit(cine_surface, (sx, sy))
            draw_viewport_frame(screen, sx, sy, GAME_WIDTH, GAME_HEIGHT, pygame.time.get_ticks())
            pygame.display.flip()

    def _iniciar_victoria_falsa():
        """En vez de terminar la partida al caer el mega-jefe, deja pendiente
        la cinematica de VICTORIA falsa (sin registrar el record todavia):
        _actualizar_bonus la corre al empezar el cuadro siguiente, asi no
        vacia la lista de jefes mientras se la esta recorriendo."""
        nonlocal bonus_estado
        bonus_estado = "victoria_falsa"

    def _cinematica_victoria_falsa():
        """La pantalla de VICTORIA de siempre con techno de fondo; a los 6 s
        la musica se vuelve epica y todo se rompe en glitch con "NEW BOSS
        READY" y compañia (ver CinematicaVictoriaFalsa). Enter salta la
        parte tranquila; el glitch se ve entero."""
        nonlocal tiempo_sobrevivido
        # el tiempo de verdad en la pantalla trampa (terminar_partida lo
        # recalcula al final de todo)
        tiempo_sobrevivido = max(0.0, (pygame.time.get_ticks() - start_time) / 1000.0 - start_countdown)
        captura = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        captura.fill(DARK_BG)
        for estrella in estrellas_juego:
            estrella.draw(captura)
        _dibujar_mundo(captura)
        for e in explosions:
            e.draw(captura)
        for p in particles:
            p.draw(captura)
        draw_victory_screen(captura, GAME_WIDTH, GAME_HEIGHT, score, wave, font, big_font, stats=stats_actuales())
        record_surf = render_text(f"Récord: {progress.puntaje_maximo()}", 14, WHITE)
        captura.blit(record_surf, (GAME_WIDTH // 2 - record_surf.get_width() // 2, GAME_HEIGHT // 2 + 100))

        audio.sonido_victoria()
        # mas fuerte que el resto de la musica (sin tocar el ajuste guardado)
        audio.reproducir_musica("victoria_tecno", ganancia=1.7)
        cine = CinematicaVictoriaFalsa(captura)
        cine_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        while not cine.terminada:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if (evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_r)) \
                        or evento.type in (pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
                    cine.saltar()
            clock.tick(FPS)
            cine.update()
            for ev in cine.eventos:
                if ev == "epica":
                    audio.reproducir_musica("glitch_epica", loop=False, ganancia=1.7)
                else:
                    audio.sonido_impacto()
            cine.eventos.clear()
            cine.draw(cine_surface)
            sx = game_offset_x + (random.randint(-cine.temblor, cine.temblor) if cine.temblor else 0)
            sy = game_offset_y + (random.randint(-cine.temblor, cine.temblor) if cine.temblor else 0)
            screen.fill((0, 0, 0))
            screen.blit(cine_surface, (sx, sy))
            draw_viewport_frame(screen, game_offset_x, game_offset_y, GAME_WIDTH, GAME_HEIGHT, pygame.time.get_ticks())
            pygame.display.flip()

    def _iniciar_pelea_bonus(jefe="nyan"):
        """Limpia el mundo, recoloca la nave (la cinematica la dejo muy
        arriba) y hace entrar al primer jefe del bonus en el entorno pixel:
        Nyan Cat, o directamente el Gato Alien / el Gato Pan si la partida
        se arranco ahi desde ELEGIR FASE."""
        nonlocal bonus_estado, bonus_banner, fondo_pixel
        bullets.clear(); asteroids.clear(); powerups.clear()
        alien_ships.clear(); alien_bullets.clear()
        bosses.clear(); boss_bullets.clear()
        explosions.clear(); particles.clear(); lightning_bolts.clear()
        ship.x = ship.target_x = GAME_WIDTH // 2
        ship.y = ship.target_y = GAME_HEIGHT - 60
        ship.invincible_timer = 90
        fondo_pixel = FondoPixel()
        if settings.get("bonus_todos_buffs"):
            _dar_todos_los_buffs()
        if jefe == "alien":
            _entrar_gato_alien()
        elif jefe == "pan":
            bosses.append(GatoPanBoss(dificultad))
            bonus_estado = "pan"
            bonus_banner = ["¡JEFE BONUS!", "GATO OIIA  -  OIIA OIIA", 170]
            audio.reproducir_musica("jefe_pan")
        else:
            bosses.append(NyanBoss(dificultad))
            bonus_estado = "nyan"
            bonus_banner = ["¡JEFE BONUS!", "NYAN CAT", 170]
            audio.reproducir_musica("jefe_nyan")
        audio.sonido_alerta_jefe()

    def _entrar_gato_alien():
        """El Gato Alien entra INVENCIBLE y el casco de la nave queda con una
        sola vida (sin escudo): esta fase es corta a proposito, termina en
        el GAME OVER falso y el tripulante te devuelve todas las vidas (ver
        _revivir_con_aliado)."""
        nonlocal bonus_estado, bonus_banner
        bosses.append(GatoAlienBoss(dificultad, invencible=True))
        bonus_estado = "alien"
        ship.lives = 1
        ship.shield_hits = 0
        ship.buffs.pop(BUFF_TYPE_SHIELD, None)
        explosions.append(Explosion(ship.x, ship.y, RED, 30))
        bonus_banner = ["¡GATO ALIEN!", "Tu casco quedo con 1 sola vida", 170]
        audio.sonido_impacto()
        audio.reproducir_musica("jefe_gatos")

    def _dar_todos_los_buffs():
        """Opcion de AJUSTES "BONUS CON TODOS LOS BUFFS": aplica cada buff
        una vez, llena la vida y deja los temporales sin vencimiento para
        toda la pelea bonus (el escudo igual se rompe tras sus golpes).
        Tambien lo usa ELEGIR FASE con "TODOS LOS BUFFS" al arrancar; una
        nave que ya los tiene no los recibe de nuevo (no suma otra vida
        maxima ni mas daño)."""
        if getattr(ship, "todos_los_buffs", False):
            return
        ship.todos_los_buffs = True
        for buff in (BUFF_TYPE_MAX_LIFE_UP, BUFF_TYPE_DAMAGE_UP, BUFF_TYPE_SPEED_UP, BUFF_TYPE_RAPID_FIRE,
                     BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT, BUFF_TYPE_SHIELD, BUFF_TYPE_PIERCING,
                     BUFF_TYPE_ATTRACT, BUFF_TYPE_LIGHTNING, BUFF_TYPE_EXTRA_LIFE):
            ship.apply_buff(buff)
            datos = ship.buffs.get(buff)
            if datos is not None:
                datos["timer"] = datos["max_timer"] = 99999
                datos["permanent"] = True
        ship.lives = ship.max_lives

    def _recompensar_jefe_bonus(boss):
        """Cadena de jefes bonus: Nyan Cat -> Gato Alien -> Gato Pan (el que
        gira, OIIA). Entre uno y otro suelta ayuda y hay un respiro con
        cartel; al caer el Gato Pan arranca la victoria de verdad."""
        nonlocal stats_jefes, bonus_estado, bonus_timer, bonus_banner
        nonlocal last_boss_rewards, boss_reward_timer
        stats_jefes += 1
        explosions.append(Explosion(boss.x, boss.y, WHITE, 90))
        for color in (ROSA, AMARILLO, MENTA, AZUL_CIELO):
            particles.extend([Particle(boss.x, boss.y, color) for _ in range(20)])
        audio.sonido_explosion()
        if isinstance(boss, GatoPanBoss):
            # un respiro para ver la explosion y despues la cinematica del
            # gatito durmiendo (ver _actualizar_bonus / _cinematica_gato_durmiendo)
            bonus_estado = "final"
            bonus_timer = 100
            bonus_banner = None
            audio.sonido_victoria()
            return
        for buff in (BUFF_TYPE_EXTRA_LIFE, BUFF_TYPE_SHIELD, random_buff_type(), random_buff_type()):
            powerups.append(PowerUp(boss.x + random.uniform(-60, 60), boss.y + random.uniform(-20, 20), buff))
        last_boss_rewards = [BossReward(BUFF_TYPE_EXTRA_LIFE, "+1", "Vida extra"),
                             BossReward(BUFF_TYPE_SHIELD, "DEF", "Escudo +1 golpe")]
        boss_reward_timer = 180
        bonus_timer = 180
        if isinstance(boss, NyanBoss):
            bonus_estado = "interludio_alien"
            bonus_banner = ["¡SIGUIENTE JEFE!", "GATO ALIEN", 170]
        else:
            bonus_estado = "interludio_pan"
            bonus_banner = ["¡ULTIMO JEFE!", "GATO OIIA  -  OIIA OIIA", 170]
            if aliado is not None:
                aliado.despedirse()  # se va por una ventila
        audio.sonido_victoria()

    def _actualizar_bonus():
        """Avanza los estados con tiempo del jefe bonus (una vez por frame,
        salvo en pausa)."""
        nonlocal bonus_estado, bonus_timer, bonus_banner
        if bonus_banner is not None:
            bonus_banner[2] -= 1
            if bonus_banner[2] <= 0:
                bonus_banner = None
        if bonus_estado == "victoria_falsa":
            _cinematica_victoria_falsa()
            _iniciar_pelea_bonus()
        elif bonus_estado in ("interludio_alien", "interludio_pan"):
            bonus_timer -= 1
            if bonus_timer <= 0:
                # cada gato con su tema: musica_jefe_gatos (chiptune) para el
                # Alien y musica_jefe_pan.* (la cancion OIIA si se agrego una
                # propia, ver tools/extraer_nyan_video.py) para el Gato Pan
                if bonus_estado == "interludio_alien":
                    _entrar_gato_alien()
                else:
                    bosses.append(GatoPanBoss(dificultad))
                    bonus_estado = "pan"
                    audio.reproducir_musica("jefe_pan")
                audio.sonido_alerta_jefe()
        elif bonus_estado == "game_over_falso":
            bonus_timer -= 1
            if bonus_timer <= 0:
                _cinematica_tripulante()
                _revivir_con_aliado()
        elif bonus_estado == "final":
            bonus_timer -= 1
            if bonus_timer <= 0 and not dying and not game_over:
                _cinematica_gato_durmiendo()
                bonus_estado = "terminado"
                terminar_partida(True)

    def _cinematica_gato_durmiendo():
        """Final del bonus: el Gato Pan se duerme ("¡FELICIDADES! Ayudaste a
        dormir a mi gato") con una cancion de cuna. Mini-bucle propio como
        _cinematica_victoria; Enter/Espacio/click/boton del mando la saltan."""
        bullets.clear(); boss_bullets.clear(); alien_bullets.clear()
        audio.reproducir_musica("cuna")
        cine = CinematicaGatoDormido()
        cine_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        while not cine.terminada:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if (evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE))                         or evento.type in (pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
                    cine.saltar()
            clock.tick(FPS)
            cine.update()
            cine.draw(cine_surface)
            screen.fill((0, 0, 0))
            screen.blit(cine_surface, (game_offset_x, game_offset_y))
            draw_viewport_frame(screen, game_offset_x, game_offset_y, GAME_WIDTH, GAME_HEIGHT, pygame.time.get_ticks())
            pygame.display.flip()

    def _cinematica_tripulante():
        """El tripulante rojo rompe la pantalla de GAME OVER y te da una mano:
        devuelve las vidas corazon por corazon (ver CinematicaTripulante). Mini-bucle propio como las otras
        cinematicas; Enter/Espacio/click/boton del mando la adelantan."""
        audio.detener_musica()
        # copia de la pantalla de GAME OVER (recortada a lo que realmente
        # entra en la ventana, por si es mas chica que el area de juego)
        captura = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        zona = pygame.Rect(game_offset_x, game_offset_y, GAME_WIDTH, GAME_HEIGHT).clip(screen.get_rect())
        if zona.w > 0 and zona.h > 0:
            captura.blit(screen.subsurface(zona), (zona.x - game_offset_x, zona.y - game_offset_y))
        cine = CinematicaTripulante(captura, ship._get_sprite(), ship.max_lives)
        cine_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        while not cine.terminada:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if (evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE)) \
                        or evento.type in (pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
                    cine.saltar()
            clock.tick(FPS)
            cine.update()
            for ev in cine.eventos:
                if ev == "disparo":
                    audio.sonido_impacto()
                elif ev in ("rotura", "escudo"):
                    audio.sonido_explosion()
                elif ev == "boton":
                    audio.sonido_boton()
                else:
                    audio.sonido_powerup()
            cine.eventos.clear()
            cine.draw(cine_surface)
            sx = game_offset_x + (random.randint(-cine.temblor, cine.temblor) if cine.temblor else 0)
            sy = game_offset_y + (random.randint(-cine.temblor, cine.temblor) if cine.temblor else 0)
            screen.fill((0, 0, 0))
            screen.blit(cine_surface, (sx, sy))
            draw_viewport_frame(screen, game_offset_x, game_offset_y, GAME_WIDTH, GAME_HEIGHT, pygame.time.get_ticks())
            pygame.display.flip()

    def _revivir_con_aliado():
        """Vuelta a la pelea contra el Gato Alien: nave con todas las vidas,
        el Alien ya sin escudo y el tripulante volando al lado."""
        nonlocal bonus_estado, bonus_banner, aliado
        ship.alive = True
        ship.lives = ship.max_lives
        ship.invincible_timer = 150
        ship.x = ship.target_x = GAME_WIDTH // 2
        ship.y = ship.target_y = GAME_HEIGHT - 60
        boss_bullets.clear(); alien_bullets.clear(); bullets.clear()
        explosions.clear(); particles.clear()
        for b in bosses:
            if isinstance(b, GatoAlienBoss):
                b.volverse_vulnerable()
        aliado = TripulanteAliado(ship)
        bonus_estado = "alien"
        bonus_banner = ["¡TRIPULANTE AL RESCATE!", "El Gato Alien perdio su escudo", 150]
        audio.reproducir_musica("jefe_gatos")

    def _dibujar_banner_bonus(surface):
        if bonus_banner is None:
            return
        titulo, subtitulo, restante = bonus_banner
        if restante < 30 and restante % 6 < 3:
            return
        franja = pygame.Surface((GAME_WIDTH, 96), pygame.SRCALPHA)
        franja.fill((0, 0, 0, 150))
        surface.blit(franja, (0, GAME_HEIGHT // 2 - 60))
        t = render_texto_pixelado(big_font, titulo, AMARILLO)
        surface.blit(t, (GAME_WIDTH // 2 - t.get_width() // 2, GAME_HEIGHT // 2 - 54))
        if subtitulo:
            st = render_texto_pixelado(font, subtitulo, ROSA_CHICLE)
            surface.blit(st, (GAME_WIDTH // 2 - st.get_width() // 2, GAME_HEIGHT // 2 + 2))

    def _dibujar_mundo(surface, incluir_nitidos=True):
        """Entidades del mundo en el orden de siempre (juego activo, muerte
        y pantallas de fin de partida). incluir_nitidos=False en el entorno
        pixel: la nave y los power-ups se dibujan aparte, despues de pixelar
        (ver _dibujar_nitidos), para que se vean nitidos."""
        if incluir_nitidos:
            for p in powerups:
                p.draw(surface)
        for aship in alien_ships:
            aship.draw(surface)
        for boss in bosses:
            boss.draw(surface)
        for ab in alien_bullets:
            ab.draw(surface)
        for bb in boss_bullets:
            bb.draw(surface)
        for a in asteroids:
            a.draw(surface)
        for b in bullets:
            b.draw(surface)
        if incluir_nitidos:
            _dibujar_companeros(surface)
            ship.draw(surface)

    def _dibujar_nitidos(surface):
        """Lo que en el entorno pixel se dibuja encima del cuadro ya pixelado:
        los power-ups (buffs), el tripulante aliado (pixel art propio, mas
        detallado que la grilla del entorno) y la nave del jugador."""
        for p in powerups:
            p.draw(surface)
        if aliado is not None:
            aliado.draw(surface)
        _dibujar_companeros(surface)
        ship.draw(surface)

    def _dibujar_companeros(surface):
        """Capsula de rescate y Zorrito Espacial (en la partida normal van
        con el resto del mundo; en el entorno pixel, nitidos encima)."""
        if capsula_mascota is not None:
            capsula_mascota.draw(surface)
        if mascota is not None:
            mascota.draw(surface)

    def _soltar_recompensa_bonus(x, y, miniboss=False):
        """Recompensa de una nave bonus (tank/interceptor/bomber reciclados
        como enemigo especial infrecuente, ver BONUS_SHIP_* en
        modules/entities/enemy.py): varios power-ups dispersos en vez de
        uno solo, para que valga la pena arriesgarse a ir por ella -mas
        todavia si era un mini-jefe (ver BONUS_SHIP_MINIBOSS_*)."""
        cantidad = BONUS_SHIP_POWERUP_COUNT
        if miniboss:
            cantidad = max(BONUS_SHIP_POWERUP_COUNT, int(round(BONUS_SHIP_POWERUP_COUNT * BONUS_SHIP_MINIBOSS_POWERUP_MULT)))
        for _ in range(cantidad):
            powerups.append(PowerUp(x + random.uniform(-45, 45), y + random.uniform(-30, 30), random_buff_type()))
        explosions.append(Explosion(x, y, AMARILLO, 60 if not miniboss else 90))
        particles.extend([Particle(x, y, AMARILLO) for _ in range(20 if not miniboss else 34)])
        particles.extend([Particle(x, y, PINK) for _ in range(12 if not miniboss else 20)])

    def stats_actuales():
        return {
            "disparos": stats_disparos,
            "aciertos": stats_aciertos,
            "tiempo": tiempo_sobrevivido,
            "asteroides": asteroid_kills,
            "alienigenas": stats_alienigenas,
            "jefes": stats_jefes,
        }

    running = True
    while running:
        frame_count += 1
        clock.tick(FPS)
        timestamp_ms = int(pygame.time.get_ticks())
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.JOYBUTTONDOWN and modo_control == "mando":
                if not menu_scene.active and not game_over and not paused and countdown_val <= 0:
                    ship.queue_shot()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    screen = pygame.display.set_mode(
                        (SCREEN_WIDTH, SCREEN_HEIGHT),
                        pygame.FULLSCREEN if fullscreen else 0,
                    )
                    settings.set_valor("pantalla_completa", fullscreen)
                if event.key == pygame.K_m:
                    settings.set_valor("silenciado", audio.alternar_silencio())
                if bonus_estado == "game_over_falso" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                    # "volver al menu" desde la victoria falsa: la rompe ya
                    bonus_timer = min(bonus_timer, 1)
                if event.key == pygame.K_p and not menu_scene.active and not game_over and bonus_estado not in congelados_bonus:
                    paused = not paused
                    if paused:
                        audio.pausar_musica()
                    else:
                        audio.reanudar_musica()
                if game_over and not game_victory:
                    if event.key == pygame.K_LEFT:
                        game_over_selected = max(0, game_over_selected - 1)
                    elif event.key == pygame.K_RIGHT:
                        game_over_selected = min(len(GOButtons) - 1, game_over_selected + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        if GOButtons[game_over_selected][0].startswith("Volver"):
                            menu_scene.active = True
                            menu_scene.transitioning_out = False
                            menu_scene.transition_alpha = 255
                            menu_scene.state = "main"
                            game_over = False
                            paused = False
                        else:
                            reset_game()
                    elif event.key == pygame.K_r:
                        reset_game()
                elif game_over and game_victory:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                        menu_scene.active = True
                        menu_scene.transitioning_out = False
                        menu_scene.transition_alpha = 255
                        menu_scene.state = "main"
                        game_over = False
                        game_victory = False
                        paused = False

            if menu_scene.active:
                result = menu_scene.handle_event(event)
                if result and result.startswith("START_GAME:"):
                    parts = result.split(":")
                    selected_ship_type = parts[1]
                    selected_skin_id = parts[2] if len(parts) > 2 else "default"
                    dificultad_id = parts[3] if len(parts) > 3 else DIFICULTAD_DEFECTO
                    dificultad_base = DIFICULTADES.get(dificultad_id, DIFICULTADES[DIFICULTAD_DEFECTO])
                    modo_control = parts[4] if len(parts) > 4 else "camara"
                    inicio_partida = parts[5] if len(parts) > 5 else "w1"
                    inicio_con_buffs = len(parts) > 6 and parts[6] == "buffs"
                    if inicio_partida == "bonus":
                        inicio_partida = "nyan"
                    if inicio_partida not in JEFES_BONUS_DIRECTOS and not (
                            inicio_partida.startswith("w") and inicio_partida[1:].isdigit()):
                        inicio_partida = "w1"
                    if modo_control == "mando":
                        activar_modo_mando()
                    else:
                        modo_control = "camara"
                        activar_modo_camara()
                    reset_game()
                elif result == "QUIT":
                    running = False
                elif result == "TOGGLE_FULLSCREEN":
                    fullscreen = settings.get("pantalla_completa")
                    screen = pygame.display.set_mode(
                        (SCREEN_WIDTH, SCREEN_HEIGHT),
                        pygame.FULLSCREEN if fullscreen else 0,
                    )
                elif result == "CHANGE_CAMERA":
                    if cap is not None:
                        try:
                            cap.release()
                        except Exception:
                            pass
                        cap = cv2.VideoCapture(settings.get("camera_index"))
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                        cap.set(cv2.CAP_PROP_FPS, 30)

        if menu_scene.active:
            audio.reproducir_musica("menu")
            menu_scene.update(mouse_pos, mouse_pressed)
            screen.fill(DARKER_BG)
            menu_scene.draw(screen)
            pygame.display.flip()
            continue

        elapsed = (pygame.time.get_ticks() - start_time) / 1000.0
        countdown_val = start_countdown - int(elapsed)
        countdown_fraction = max(0.0, min(1.0, (start_countdown - elapsed) / start_countdown))

        # En modo camara se lee un frame por ciclo y se reutiliza tanto para
        # el seguimiento de mano como para el preview de abajo (antes se
        # llamaba a cap.read() dos veces por frame, el doble de lecturas de
        # las que hacen falta). En modo mando no se toca la camara para nada.
        frame_actual = None
        if modo_control == "camara":
            if not game_over:
                ret, frame = cap.read()
                if ret:
                    frame_actual = cv2.flip(frame, 1)

            if not game_over and countdown_val <= 0 and not paused and frame_actual is not None:
                result = process_camera_frame(hand_detector, frame_actual, timestamp_ms)
                hand_active = False

                if result is not None and result.hand_landmarks and len(result.hand_landmarks) > 0:
                    hand_lm = result.hand_landmarks[0]
                    hand_active = True

                    h_x, h_y = find_hand_position(hand_lm, GAME_WIDTH, GAME_HEIGHT, settings.get("sensibilidad_mano"))
                    last_hand_x = h_x
                    last_hand_y = h_y

                    ship.target_x = h_x
                    ship.target_y = h_y * 0.7 + GAME_HEIGHT * 0.3

                    ship.trigger_fist_burst(is_fist(hand_lm))
                else:
                    hand_active = False
                    ship.target_x = last_hand_x
                    ship.target_y = last_hand_y
                    ship.reset_fist_tracking()
        else:
            hand_active = joystick is not None
            if not game_over and countdown_val <= 0 and not paused and joystick is not None:
                try:
                    axis_x = joystick.get_axis(0)
                    axis_y = joystick.get_axis(1)
                except pygame.error:
                    axis_x = axis_y = 0.0
                if abs(axis_x) < GAMEPAD_DEADZONE:
                    axis_x = 0.0
                if abs(axis_y) < GAMEPAD_DEADZONE:
                    axis_y = 0.0
                ship.target_x = max(0, min(GAME_WIDTH, ship.target_x + axis_x * GAMEPAD_MOVE_SPEED))
                ship.target_y = max(0, min(GAME_HEIGHT, ship.target_y + axis_y * GAMEPAD_MOVE_SPEED))

        if bonus_directo_pendiente and countdown_val <= 0 and not paused and not game_over:
            _iniciar_pelea_bonus(bonus_directo_pendiente)
            bonus_directo_pendiente = None

        en_bonus = bonus_estado is not None
        congelado_bonus = bonus_estado in congelados_bonus
        if en_bonus and not paused:
            _actualizar_bonus()
            en_bonus = bonus_estado is not None
            congelado_bonus = bonus_estado in congelados_bonus

        if not paused and not congelado_bonus:
            ship.update()
            new_bullets = ship.update_burst_fire()
            if new_bullets:
                audio.sonido_disparo()
            for b in new_bullets:
                if b:
                    bullets.append(b)
                    stats_disparos += 1

        if dying and not paused:
            death_timer -= 1
            if death_timer <= 0:
                dying = False
                if bonus_estado == "alien" and any(isinstance(b, GatoAlienBoss) and b.invencible for b in bosses):
                    # lo mato el Alien invencible: GAME OVER de mentira y
                    # despues el tripulante al rescate (ver _actualizar_bonus)
                    bonus_estado = "game_over_falso"
                    bonus_timer = GAME_OVER_FALSO_FRAMES
                    # el tiempo de verdad, para que la pantalla trampa no
                    # muestre 0:00 (terminar_partida lo recalcula al final)
                    tiempo_sobrevivido = max(0.0, (pygame.time.get_ticks() - start_time) / 1000.0 - start_countdown)
                else:
                    terminar_partida(False)

        if not game_over and countdown_val <= 0 and not paused and not congelado_bonus:
            cuota_oleada = cuota_de_oleada(wave)
            boss_def = None if en_bonus else get_boss_for_wave(wave)
            # Oleada de jefe (10/20/30/40, o el mega-jefe en MEGA_BOSS_SPAWN_WAVE):
            # mientras dure (desde que se llega a esa oleada hasta que el jefe
            # cae) el avance generico por objetivos_oleada queda excluido -
            # subir de oleada aca es trabajo exclusivo de _recompensar_jefe, al
            # derrotarlo. jefe_pendiente ademas congela los spawns de
            # asteroides/alienigenas mientras el jefe todavia no aparecio, para
            # que la nave/alienigena que quedaba en pantalla termine de irse y
            # el jefe aparezca si o si (en vez de arriesgarse a que sigan
            # entrando naves nuevas y `len(alien_ships) == 0` no se cumpla
            # nunca). Sin esto la oleada podia saltearse el jefe por completo,
            # o quedar pegada peleandolo para siempre.
            # (durante el jefe bonus todo spawn normal queda apagado)
            es_oleada_de_jefe = boss_def is not None or wave == MEGA_BOSS_SPAWN_WAVE or en_bonus
            jefe_pendiente = es_oleada_de_jefe and len(bosses) == 0

            if objetivos_oleada >= cuota_oleada and not es_oleada_de_jefe:
                objetivos_oleada = 0
                wave += 1

            spawn_timer += 1
            spawn_rate = max(12, (70 - wave * 5) / dificultad)
            if spawn_timer >= spawn_rate and len(bosses) == 0 and not jefe_pendiente:
                spawn_timer = 0
                size = random.randint(18, 38)
                x = random.randint(size, GAME_WIDTH - size)
                nuevo_asteroide = Asteroid(x, -size - 10, size)
                nuevo_asteroide.speed *= dificultad
                asteroids.append(nuevo_asteroide)

            alien_spawn_timer += 1
            if alien_spawn_timer >= max(90, 200 / dificultad) and wave >= 2 and len(bosses) == 0 and not jefe_pendiente:
                alien_spawn_timer = 0
                side = random.choice(["left", "right", "top"])
                if wave >= BONUS_SHIP_MIN_WAVE and random.random() < BONUS_SHIP_SPAWN_CHANCE:
                    es_miniboss = random.random() < BONUS_SHIP_MINIBOSS_CHANCE
                    alien_ships.append(AlienShip(side, variant=random.choice(BONUS_SHIP_KINDS), miniboss=es_miniboss))
                else:
                    alien_ships.append(AlienShip(side))

            if boss_def and len(bosses) == 0 and len(alien_ships) == 0:
                if boss_def.spawn_wave == FINAL_BOSS_SPAWN_WAVE:
                    # La Anomalia Final: la version con sprites, 3 fases y
                    # ataques propios de boss.py, en vez del generico
                    # WaveBoss. Ya no termina la partida al derrotarla:
                    # queda como un jefe intermedio mas camino al mega-jefe
                    # de la oleada MEGA_BOSS_SPAWN_WAVE (ver _recompensar_jefe).
                    jefe_final = FinalBoss(dificultad)
                    jefe_final.definition = boss_def
                    bosses.append(jefe_final)
                elif boss_def.boss_id == "titan":
                    # Titan del Vacio: jefe unico (sismo telegrafiado +
                    # lanza que rastrea a la nave) de titan_boss.py, en vez
                    # del generico WaveBoss.
                    jefe_titan = TitanBoss(dificultad)
                    jefe_titan.definition = boss_def
                    bosses.append(jefe_titan)
                elif boss_def.boss_id == "dragon":
                    # Vanguardia Autonoma: nave-robot que se transforma de
                    # verdad al cambiar de fase (flipbook de sprites, ver
                    # dragon_boss.py), en vez del generico WaveBoss.
                    jefe_dragon = DragonBoss(dificultad)
                    jefe_dragon.definition = boss_def
                    bosses.append(jefe_dragon)
                else:
                    bosses.append(WaveBoss(boss_def, dificultad))
                audio.sonido_alerta_jefe()
                # Tema propio por jefe (ver generar_musica_jefe_* en
                # tools/generate_audio.py) en vez de que siga sonando la
                # musica generica del juego durante toda la pelea.
                audio.reproducir_musica(f"jefe_{boss_def.boss_id}")
            elif wave == MEGA_BOSS_SPAWN_WAVE and not en_bonus and len(bosses) == 0 and len(alien_ships) == 0:
                # El mega-jefe final unico: dos fases (crucero -> esfera de
                # combate) con silueta y ataques propios, ver
                # modules/entities/mega_boss.py. Su derrota es la unica
                # forma de terminar la partida con "victoria".
                bosses.append(MegaBoss(dificultad))
                audio.sonido_alerta_jefe()
                audio.reproducir_musica("jefe_mega")

            for b in bosses[:]:
                if isinstance(b, MegaBoss):
                    resultado_jefe = b.update(ship)
                    if resultado_jefe:
                        for rb in resultado_jefe.get("bullets", []):
                            boss_bullets.append(rb)
                        for nuevo_meteoro in resultado_jefe.get("asteroides", []):
                            asteroids.append(nuevo_meteoro)
                        for nueva_nave in resultado_jefe.get("alien_ships", []):
                            alien_ships.append(nueva_nave)
                    if not b.active:
                        if not b.rewarded:
                            b.rewarded = True
                            _recompensar_jefe(b)
                        bosses.remove(b)
                elif isinstance(b, (WaveBoss, FinalBoss, TitanBoss, DragonBoss, JefeGatoBase)):
                    ret_b = b.update(ship)
                    if ret_b:
                        for rb in ret_b:
                            boss_bullets.append(rb)
                    if getattr(b, "pide_matar_nave", False):
                        # rayo de abduccion del Gato Alien invencible: ni el
                        # escudo ni la invencibilidad salvan a la nave
                        b.pide_matar_nave = False
                        if ship.alive and not dying:
                            ship.lives = 0
                            ship.alive = False
                            explosions.append(Explosion(ship.x, ship.y, RED, 50))
                            particles.extend([Particle(ship.x, ship.y, CYAN) for _ in range(25)])
                            audio.sonido_explosion()
                            audio.reproducir_musica("muerte", loop=False)
                            dying = True
                            death_timer = 180
                    if not b.active:
                        if not b.rewarded:
                            b.rewarded = True
                            _recompensar_jefe(b)
                        bosses.remove(b)

            if aliado is not None:
                bullets.extend(aliado.update(ship, bosses))
                if aliado.terminado:
                    aliado = None

            # mascota: la capsula aparece una sola vez al llegar a la mitad
            if (not mascota_ofrecida and mascota is None and not en_bonus
                    and wave >= mascota_mod.MASCOTA_OLEADA):
                mascota_ofrecida = True
                capsula_mascota = CapsulaMascota()
                aviso_mascota = ["¡CAPSULA DE RESCATE!", "Toca la capsula con tu nave", 240]
                audio.sonido_powerup()
            if capsula_mascota is not None:
                capsula_mascota.update()
                if capsula_mascota.recogida(ship):
                    mascota = ZorritoEspacial(ship)
                    explosions.append(Explosion(capsula_mascota.x, capsula_mascota.y, ORANGE, 40))
                    particles.extend([Particle(capsula_mascota.x, capsula_mascota.y, AMARILLO) for _ in range(20)])
                    capsula_mascota = None
                    aviso_mascota = ["¡NUEVO COMPAÑERO!", "El Zorrito Espacial se une a tu aventura", 260]
                    audio.sonido_victoria()
            if mascota is not None:
                bullets.extend(mascota.update(ship, asteroids + alien_ships + bosses,
                                              alien_bullets + boss_bullets, powerups))

            if not bosses and not game_over and bonus_estado is None:
                # se derroto al ultimo jefe en pantalla (o no hay ninguno
                # activo todavia): vuelve a sonar la musica generica del
                # juego en vez de dejar sonando el tema de un jefe que ya
                # no esta. No-op si ya es la pista actual (ver
                # audio.reproducir_musica), asi que es seguro llamarlo
                # todos los frames sin jefe en pantalla.
                _musica_partida()

            for b in bullets[:]:
                b.update()
                if not b.active:
                    bullets.remove(b)

            for ab in alien_bullets[:]:
                ab.update()
                if not ab.active:
                    alien_bullets.remove(ab)

            for a in asteroids[:]:
                a.update()
                if not a.active:
                    asteroids.remove(a)

            for aship in alien_ships[:]:
                nuevos_proyectiles = aship.update(ship)
                for p in nuevos_proyectiles:
                    alien_bullets.append(p)
                if not aship.active:
                    # la recompensa (si corresponde) ya se otorgo en el
                    # momento del golpe letal (take_damage) mas abajo o en
                    # el rayo electrico; aca solo se limpia de la lista -
                    # una nave que sale volando de pantalla sin que la
                    # maten NO debe soltar nada.
                    alien_ships.remove(aship)

            for b in bullets[:]:
                for a in asteroids[:]:
                    dist = math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)
                    if dist < a.size + b.radius:
                        a.flash_timer = 6
                        explosions.append(Explosion(a.x, a.y, ORANGE, 20))
                        particles.extend([Particle(a.x, a.y, RED) for _ in range(8)])
                        audio.sonido_explosion()
                        asteroid_kills += 1
                        objetivos_oleada += 1
                        stats_aciertos += 1
                        score += a.size // 10 + 1
                        if asteroid_kills % POWERUP_SPAWN_EVERY == 0:
                            buff = random_buff_type()
                            powerups.append(PowerUp(a.x, a.y, buff))
                        if not b.piercing:
                            b.active = False
                        a.active = False
                        break

            for b in bullets[:]:
                for aship in alien_ships[:]:
                    dist = math.sqrt((b.x - aship.x) ** 2 + (b.y - aship.y) ** 2)
                    if dist < aship.size + b.radius:
                        # las bonus ya no mueren de un solo golpe (ver
                        # AlienShip.take_damage/hp): solo se otorga
                        # recompensa y se cuenta como objetivo cumplido en
                        # el golpe que de verdad la destruye.
                        murio = aship.take_damage(max(1, int(ship.damage_multiplier)))
                        if murio:
                            if aship.is_bonus:
                                _soltar_recompensa_bonus(aship.x, aship.y, miniboss=aship.is_miniboss)
                                score += int(BONUS_SHIP_SCORE * (BONUS_SHIP_MINIBOSS_SCORE_MULT if aship.is_miniboss else 1))
                            else:
                                buff = random_buff_type()
                                powerups.append(PowerUp(aship.x, aship.y, buff))
                                explosions.append(Explosion(aship.x, aship.y, PURPLE, 15))
                                particles.extend([Particle(aship.x, aship.y, PINK) for _ in range(8)])
                                score += 50
                            audio.sonido_explosion()
                            stats_alienigenas += 1
                            objetivos_oleada += 1
                        else:
                            explosions.append(Explosion(aship.x, aship.y, WHITE, 8))
                            audio.sonido_impacto()
                        stats_aciertos += 1
                        if not b.piercing:
                            b.active = False
                        break

            for b in bullets[:]:
                for boss in bosses[:]:
                    # Titan puede levantar un tentaculo de guardia que
                    # bloquea los disparos que le peguen a el (ver
                    # TitanBoss.bloquea_disparo): se descarta la bala ahi,
                    # como un parry, sin llegar a tocar el cuerpo/ojo. Con
                    # hasattr() no afecta a ningun otro tipo de jefe.
                    if hasattr(boss, 'bloquea_disparo') and boss.bloquea_disparo(b.x, b.y):
                        if not b.piercing:
                            b.active = False
                        explosions.append(Explosion(b.x, b.y, WHITE, 10))
                        break
                    dist = math.sqrt((b.x - boss.x) ** 2 + (b.y - boss.y) ** 2)
                    boss_hit_radius = 50
                    if hasattr(boss, 'definition'):
                        boss_hit_radius = max(boss.definition.max_hp // 8, 50)
                    if hasattr(boss, 'size'):
                        boss_hit_radius = max(boss.size, boss_hit_radius)
                    if hasattr(boss, 'width'):
                        boss_hit_radius = max(boss_hit_radius, boss.width // 2)
                    if dist < boss_hit_radius + b.radius:
                        damage = max(1, int(ship.damage_multiplier))
                        boss.take_damage(damage)
                        stats_aciertos += 1
                        if not b.piercing:
                            b.active = False
                        explosions.append(Explosion(boss.x, boss.y, ROSA, 8))
                        particles.extend([Particle(boss.x, boss.y, AMARILLO) for _ in range(5)])
                        if not boss.active and not boss.rewarded:
                            boss.rewarded = True
                            _recompensar_jefe(boss)
                        break

            if ship.puede_descargar_rayo():
                objetivo = None
                objetivo_tipo = None
                mejor_dist = ship.lightning_radius
                for a in asteroids:
                    dist = math.sqrt((a.x - ship.x) ** 2 + (a.y - ship.y) ** 2)
                    if dist < mejor_dist:
                        mejor_dist = dist
                        objetivo, objetivo_tipo = a, "asteroide"
                for aship in alien_ships:
                    dist = math.sqrt((aship.x - ship.x) ** 2 + (aship.y - ship.y) ** 2)
                    if dist < mejor_dist:
                        mejor_dist = dist
                        objetivo, objetivo_tipo = aship, "alien"
                for boss in bosses:
                    dist = math.sqrt((boss.x - ship.x) ** 2 + (boss.y - ship.y) ** 2)
                    if dist < mejor_dist:
                        mejor_dist = dist
                        objetivo, objetivo_tipo = boss, "boss"

                if objetivo is not None:
                    ship.reiniciar_descarga_rayo()
                    lightning_bolts.append({
                        'x1': ship.x, 'y1': ship.y, 'x2': objetivo.x, 'y2': objetivo.y,
                        'life': 8, 'max_life': 8,
                    })
                    explosions.append(Explosion(objetivo.x, objetivo.y, ELECTRICO, 14))
                    particles.extend([Particle(objetivo.x, objetivo.y, CYAN) for _ in range(6)])
                    audio.sonido_impacto()
                    if objetivo_tipo == "asteroide":
                        asteroid_kills += 1
                        objetivos_oleada += 1
                        score += objetivo.size // 10 + 1
                        if asteroid_kills % POWERUP_SPAWN_EVERY == 0:
                            powerups.append(PowerUp(objetivo.x, objetivo.y, random_buff_type()))
                        objetivo.active = False
                    elif objetivo_tipo == "alien":
                        # respeta el hp igual que un golpe de bala normal
                        # (ver AlienShip.take_damage): una bonus/mini-jefe
                        # no muere de un solo rayo solo porque el rayo sea
                        # instantaneo.
                        if objetivo.take_damage(max(1, int(ship.damage_multiplier))):
                            if getattr(objetivo, "is_bonus", False):
                                es_mb = getattr(objetivo, "is_miniboss", False)
                                _soltar_recompensa_bonus(objetivo.x, objetivo.y, miniboss=es_mb)
                                score += int(BONUS_SHIP_SCORE * (BONUS_SHIP_MINIBOSS_SCORE_MULT if es_mb else 1))
                            else:
                                powerups.append(PowerUp(objetivo.x, objetivo.y, random_buff_type()))
                                score += 50
                            stats_alienigenas += 1
                            objetivos_oleada += 1
                    else:
                        objetivo.take_damage(max(1, int(ship.damage_multiplier)))

            for ab in alien_bullets[:]:
                dist = math.sqrt((ab.x - ship.x) ** 2 + (ab.y - ship.y) ** 2)
                if dist < ab.radius + SHIP_WIDTH // 2:
                    ab.active = False
                    if ship.take_damage():
                        explosions.append(Explosion(ship.x, ship.y, RED, 35))
                        particles.extend([Particle(ship.x, ship.y, CYAN) for _ in range(15)])
                        audio.sonido_impacto()
                        if not ship.alive:
                            audio.reproducir_musica("muerte", loop=False)
                            dying = True
                            death_timer = 180
                    break

            for bb in boss_bullets[:]:
                bb.update()
                if not bb.active:
                    boss_bullets.remove(bb)

            for bb in boss_bullets[:]:
                dist = math.sqrt((bb.x - ship.x) ** 2 + (bb.y - ship.y) ** 2)
                if dist < bb.radius + SHIP_WIDTH // 2:
                    bb.active = False
                    if ship.take_damage():
                        explosions.append(Explosion(ship.x, ship.y, RED, 35))
                        particles.extend([Particle(ship.x, ship.y, CYAN) for _ in range(15)])
                        audio.sonido_impacto()
                        if not ship.alive:
                            audio.reproducir_musica("muerte", loop=False)
                            dying = True
                            death_timer = 180
                    break

            for a in asteroids[:]:
                dist = math.sqrt((a.x - ship.x) ** 2 + (a.y - ship.y) ** 2)
                if dist < a.size + SHIP_WIDTH // 2:
                    if ship.take_damage():
                        explosions.append(Explosion(ship.x, ship.y, RED, 35))
                        particles.extend([Particle(ship.x, ship.y, CYAN) for _ in range(15)])
                        audio.sonido_impacto()
                        if not ship.alive:
                            audio.reproducir_musica("muerte", loop=False)
                            dying = True
                            death_timer = 180
                    a.active = False
                    break

            for p in powerups[:]:
                p.update()
                if not p.active:
                    powerups.remove(p)

            for p in powerups[:]:
                dist = math.sqrt((p.x - ship.x) ** 2 + (p.y - ship.y) ** 2)
                if ship.attract_active and dist < 180:
                    pdx = ship.x - p.x
                    pdy = ship.y - p.y
                    pdist = math.sqrt(pdx * pdx + pdy * pdy)
                    if pdist > 0:
                        p.x += (pdx / pdist) * 4
                        p.y += (pdy / pdist) * 4
                if dist < p.radius + SHIP_WIDTH // 2:
                    p.active = False
                    powerups.remove(p)
                    ship.apply_buff(p.buff_type)
                    explosions.append(Explosion(p.x, p.y, p.color, 12))
                    particles.extend([Particle(p.x, p.y, WHITE) for _ in range(6)])
                    audio.sonido_powerup()

            for e in explosions[:]:
                e.update()
                if not e.active:
                    explosions.remove(e)

            for p in particles[:]:
                p.update()
                if p.life <= 0:
                    particles.remove(p)

            for lb in lightning_bolts[:]:
                lb['life'] -= 1
                if lb['life'] <= 0:
                    lightning_bolts.remove(lb)

        if boss_reward_timer > 0:
            boss_reward_timer -= 1

        game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        # Entorno pixel del jefe bonus: fondo propio y, mas abajo, el cuadro
        # entero pixelado antes de dibujar HUD/textos encima (nitidos).
        entorno_pixel = fondo_pixel is not None
        if entorno_pixel:
            if not paused and not game_over:
                fondo_pixel.update()
            fondo_pixel.draw(game_surface)
        else:
            game_surface.fill(DARK_BG)
            for estrella in estrellas_juego:
                estrella.update()
                estrella.draw(game_surface)

        # Los paneles de buffs y la consola de vida van en el margen fuera
        # del viewport (ver draw_viewport_frame mas abajo), asi que se
        # dibujan sobre `screen`, no sobre `game_surface`; esta bandera
        # recuerda si corresponde mostrarlos este frame (solo en juego
        # activo) para cuando se compone la pantalla final.
        mostrar_hud_margenes = False

        if countdown_val > 0:
            if modo_control == "camara":
                control_hint = "Cerra el puño para disparar"
            else:
                control_hint = "Boton del mando para disparar"
            draw_countdown(game_surface, GAME_WIDTH, GAME_HEIGHT, countdown_val, countdown_fraction,
                            font, info_font, big_font, control_hint)

        elif bonus_estado == "game_over_falso":
            # GAME OVER de mentira (el Alien invencible te mato): igual al de
            # verdad, sobre el mundo pixel congelado; despues viene la
            # cinematica del tripulante.
            _dibujar_mundo(game_surface, incluir_nitidos=False)
            for e in explosions:
                e.draw(game_surface)
            for p in particles:
                p.draw(game_surface)
            game_surface = pixelar(game_surface, PIXEL_BONUS)
            dibujar_scanlines(game_surface)
            draw_game_over(game_surface, GAME_WIDTH, GAME_HEIGHT, score, wave, font, big_font, GOButtons,
                           game_over_selected, stats=stats_actuales())
            record_surf = render_text(f"Récord: {progress.puntaje_maximo()}", 14, WHITE)
            game_surface.blit(record_surf, (GAME_WIDTH // 2 - record_surf.get_width() // 2, GAME_HEIGHT // 2 + 100))

        elif not game_over and not dying:
            _dibujar_mundo(game_surface, incluir_nitidos=not entorno_pixel)
            if not entorno_pixel:
                for lb in lightning_bolts:
                    dibujar_rayo(game_surface, lb)
            for e in explosions:
                e.draw(game_surface)
            for p in particles:
                p.draw(game_surface)

            if entorno_pixel:
                game_surface = pixelar(game_surface, PIXEL_BONUS)
                dibujar_scanlines(game_surface)
                _dibujar_nitidos(game_surface)
                # rayos del buff "campo electrico", tambien nitidos
                for lb in lightning_bolts:
                    dibujar_rayo(game_surface, lb)
                for boss in bosses:
                    if hasattr(boss, "draw_ui"):
                        boss.draw_ui(game_surface)
                _dibujar_banner_bonus(game_surface)

            if aviso_mascota is not None:
                dibujar_aviso_mascota(game_surface, aviso_mascota[0], aviso_mascota[1], aviso_mascota[2], frame_count)
                if not paused:
                    aviso_mascota[2] -= 1
                    if aviso_mascota[2] <= 0:
                        aviso_mascota = None

            cuota_hud = cuota_de_oleada(wave)
            draw_hud(game_surface, score, wave, ship.lives, ship.buffs, font, small_font, hand_active, ship.max_lives,
                     objetivos_oleada, cuota_hud, len(bosses) > 0)
            mostrar_hud_margenes = True

            if boss_reward_timer > 0 and last_boss_rewards:
                draw_boss_rewards(game_surface, "Jefe Derrotado", last_boss_rewards, GAME_WIDTH // 2, GAME_HEIGHT - 60)

            if modo_control == "camara":
                if hand_active:
                    indicator = render_texto_pixelado(small_font, "Mano detectada | Puño = Disparar", GREEN)
                else:
                    indicator = render_texto_pixelado(small_font, "Buscando mano...", RED)
            else:
                if hand_active:
                    indicator = render_texto_pixelado(small_font, "Mando conectado | Boton = Disparar", GREEN)
                else:
                    indicator = render_texto_pixelado(small_font, "Mando no detectado", RED)
            game_surface.blit(indicator, (GAME_WIDTH - indicator.get_width() - 8, 8))

            if paused:
                overlay_pausa = pygame.Surface(game_surface.get_size(), pygame.SRCALPHA)
                overlay_pausa.fill((0, 0, 0, 130))
                game_surface.blit(overlay_pausa, (0, 0))
                texto_pausa = render_texto_pixelado(big_font, "PAUSA", WHITE)
                game_surface.blit(texto_pausa, (GAME_WIDTH // 2 - texto_pausa.get_width() // 2, GAME_HEIGHT // 2 - 40))
                texto_ayuda = render_texto_pixelado(info_font, "Presiona P para continuar", WHITE)
                game_surface.blit(texto_ayuda, (GAME_WIDTH // 2 - texto_ayuda.get_width() // 2, GAME_HEIGHT // 2 + 20))

        if dying:
            for e in explosions:
                e.draw(game_surface)
            for p in particles:
                p.draw(game_surface)
            if entorno_pixel:
                game_surface = pixelar(game_surface, PIXEL_BONUS)
            fade = 255 - int(200 * (death_timer / 180))
            overlay = pygame.Surface(game_surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, fade))
            game_surface.blit(overlay, (0, 0))
            dying_text = render_texto_pixelado(font, "¡Impacto crítico!", ROSA)
            game_surface.blit(dying_text, (GAME_WIDTH // 2 - dying_text.get_width() // 2, GAME_HEIGHT // 2))

        if game_over:
            _dibujar_mundo(game_surface, incluir_nitidos=not entorno_pixel)
            for e in explosions:
                e.draw(game_surface)
            for p in particles:
                p.draw(game_surface)
            if entorno_pixel:
                game_surface = pixelar(game_surface, PIXEL_BONUS)
                dibujar_scanlines(game_surface)
                _dibujar_nitidos(game_surface)

            if boss_reward_timer > 0 and last_boss_rewards:
                draw_boss_rewards(game_surface, "Jefe Derrotado", last_boss_rewards, GAME_WIDTH // 2, GAME_HEIGHT - 60)

            if game_victory:
                if bonus_estado == "terminado":
                    icono = sprite_pixel("durmiendo", 1 if math.sin(frame_count * 0.05) > 0 else 0, 4)
                    draw_victory_final(game_surface, GAME_WIDTH, GAME_HEIGHT, score, wave, stats_actuales(),
                                       f"Récord: {progress.puntaje_maximo()}", nuevo_record, frame_count, icono=icono)
                else:
                    draw_victory_screen(game_surface, GAME_WIDTH, GAME_HEIGHT, score, wave, font, big_font, stats=stats_actuales())
            else:
                draw_game_over(game_surface, GAME_WIDTH, GAME_HEIGHT, score, wave, font, big_font, GOButtons, game_over_selected, stats=stats_actuales())

            if bonus_estado != "terminado":  # la pantalla final ya trae su record
                texto_record = f"Récord: {progress.puntaje_maximo()}"
                if nuevo_record:
                    texto_record = "¡Nuevo récord! " + texto_record
                record_surf = render_text(texto_record, 14, AMARILLO if nuevo_record else WHITE)
                game_surface.blit(record_surf, (GAME_WIDTH // 2 - record_surf.get_width() // 2, GAME_HEIGHT // 2 + 100))

            go_buttons = GOButtons if not game_victory else []
            if go_buttons:
                btn_w = 150
                btn_h = 40
                spacing = 180
                base_x = game_offset_x + GAME_WIDTH // 2 - btn_w - spacing // 2 + btn_w
                btn_y = game_offset_y + GAME_HEIGHT // 2 + 30
                mouse_pos = pygame.mouse.get_pos()
                for i, (_, _) in enumerate(go_buttons):
                    r = pygame.Rect(base_x + i * spacing, btn_y, btn_w, btn_h)
                    if r.collidepoint(mouse_pos):
                        game_over_selected = i
                    if r.collidepoint(mouse_pos) and mouse_pressed[0]:
                        if i == 0:
                            menu_scene.active = True
                            menu_scene.transitioning_out = False
                            menu_scene.transition_alpha = 255
                            menu_scene.state = "main"
                            game_over = False
                            paused = False
                        else:
                            reset_game()

        screen.fill(DARKER_BG)
        for estrella in estrellas_fondo:
            estrella.update()
            estrella.draw(screen)

        screen.blit(game_surface, (game_offset_x, game_offset_y))
        draw_viewport_frame(screen, game_offset_x, game_offset_y, GAME_WIDTH, GAME_HEIGHT, pygame.time.get_ticks())

        if mostrar_hud_margenes:
            draw_buff_hud(screen, ship.buffs, game_offset_x, game_offset_y, ship.class_buffs)
            draw_ship_status_bar(screen, ship.lives, ship.max_lives, game_offset_x, game_offset_y, pygame.time.get_ticks())

        if not game_over and frame_actual is not None:
            preview_resized = resize_frame(frame_actual, PREVIEW_WIDTH, PREVIEW_HEIGHT)
            preview_surf = surface_from_frame(preview_resized)
            preview_rect = preview_surf.get_rect(topright=(SCREEN_WIDTH - 8, 8))
            draw_camera_preview(screen, preview_surf, preview_rect, pygame.time.get_ticks())

        pygame.display.flip()

    if cap is not None:
        cap.release()
    if hand_detector is not None:
        hand_detector.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()