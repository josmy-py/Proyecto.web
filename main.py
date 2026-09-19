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
import importlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import pygame
import random
import math

from modules.systems.input import init_hand_landmarker, process_camera_frame, set_frame_skip

from modules.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GAME_WIDTH, GAME_HEIGHT,
    PREVIEW_WIDTH, PREVIEW_HEIGHT, FPS,
    WHITE, RED, GREEN, YELLOW, CYAN, BLUE, ORANGE,
    DARK_BG, DARKER_BG, PURPLE, PINK,
    ROSA, AMARILLO, AZUL, AZUL_CIELO, MELON, LAVANDA, ROSA_CHICLE, MENTA, ELECTRICO,
    BUFF_TYPE_EXTRA_LIFE, BUFF_TYPE_FAST_SHOOT, BUFF_TYPE_TRIPLE_SHOT,
    POWERUP_SPAWN_EVERY, SHIP_WIDTH, SHIP_HEIGHT, BOSS_SPAWN_WAVE,
    FINAL_BOSS_SPAWN_WAVE, FINAL_BOSS_MAX_HP, FINAL_BOSS_SHOOT_RATE,
    DIFICULTADES, DIFICULTAD_DEFECTO,
)
from modules.entities.ship import Ship
from modules.entities.bullet import Bullet
from modules.entities.enemy import AlienShip, AlienBullet
from modules.entities.asteroid import Asteroid, Particle, Explosion
from modules.entities.powerup import PowerUp, random_buff_type
from modules.systems.input import (
    init_hand_landmarker,
    process_camera_frame,
    set_frame_skip,
    is_fist,
    find_hand_position,
    WRIST_IDX,
)
from modules.systems.ui import draw_hud, draw_countdown, draw_camera_preview, draw_game_over, draw_buff_hud, draw_victory_screen, draw_boss_rewards
from modules.core.boss_system import get_boss_for_wave, WaveBoss, WaveBossBullet
from modules.entities.boss import FinalBoss
from modules.systems.menu import MenuScene, Star
from modules.systems import audio
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

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 30)

    set_frame_skip(2)
    hand_detector = init_hand_landmarker(MODEL_PATH)

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
    wave_timer = 0
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

    # Fondo de estrellas de la partida (independiente del que usa el menu).
    # No se reinicia entre partidas, es solo decoracion de fondo.
    estrellas_juego = [Star(GAME_WIDTH, GAME_HEIGHT) for _ in range(90)]

    menu_scene = MenuScene(SCREEN_WIDTH, SCREEN_HEIGHT)

    start_time = pygame.time.get_ticks()
    start_countdown = 5

    def reset_game():
        nonlocal ship, bullets, asteroids, powerups, alien_ships, alien_bullets
        nonlocal bosses, boss_bullets, explosions, particles, lightning_bolts
        nonlocal score, wave, wave_timer, spawn_timer, asteroid_kills, alien_spawn_timer
        nonlocal game_over, game_victory, dying, death_timer, game_over_selected
        nonlocal last_boss_rewards, boss_reward_timer, start_time, start_countdown
        nonlocal paused, nuevo_record, dificultad
        nonlocal stats_disparos, stats_aciertos, stats_alienigenas, stats_jefes, tiempo_sobrevivido
        if hasattr(draw_hud, 'hud'):
            del draw_hud.hud
        if hasattr(draw_buff_hud, 'hud'):
            del draw_buff_hud.hud
        ship = Ship(GAME_WIDTH // 2, GAME_HEIGHT - 60, selected_ship_type, selected_skin_id)
        bullets.clear(); asteroids.clear(); powerups.clear()
        alien_ships.clear(); alien_bullets.clear()
        bosses.clear(); boss_bullets.clear()
        explosions.clear(); particles.clear(); lightning_bolts.clear()
        score = 0; wave = 1; wave_timer = 0; spawn_timer = 0
        asteroid_kills = 0; alien_spawn_timer = 0
        game_over = False; game_victory = False
        dying = False; death_timer = 0; game_over_selected = 0
        last_boss_rewards = []; boss_reward_timer = 0
        paused = False; nuevo_record = False
        dificultad = dificultad_base
        stats_disparos = 0; stats_aciertos = 0
        stats_alienigenas = 0; stats_jefes = 0; tiempo_sobrevivido = 0.0
        start_time = pygame.time.get_ticks()
        start_countdown = 5
        audio.reproducir_musica("juego")

    def terminar_partida(victoria):
        """Marca fin de partida (derrota o victoria) y registra el record."""
        nonlocal game_over, game_victory, nuevo_record, tiempo_sobrevivido
        game_over = True
        game_victory = victoria
        tiempo_sobrevivido = max(0.0, (pygame.time.get_ticks() - start_time) / 1000.0 - start_countdown)
        nuevo_record = progress.registrar_partida(score, wave)
        if victoria:
            audio.sonido_victoria()

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
        dt = clock.tick(FPS)
        timestamp_ms = int(pygame.time.get_ticks())
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
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
                if event.key == pygame.K_p and not menu_scene.active and not game_over:
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

        # Se lee la camara una sola vez por frame y se reutiliza tanto para
        # el seguimiento de mano como para el preview de abajo (antes se
        # llamaba a cap.read() dos veces por frame, el doble de lecturas de
        # las que hacen falta).
        frame_actual = None
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

                if is_fist(hand_lm):
                    new_bullets = ship.shoot()
                    if new_bullets:
                        audio.sonido_disparo()
                    for b in new_bullets:
                        if b:
                            bullets.append(b)
                            stats_disparos += 1
            else:
                hand_active = False
                ship.target_x = last_hand_x
                ship.target_y = last_hand_y

        if not paused:
            ship.update()

        if dying and not paused:
            death_timer -= 1
            if death_timer <= 0:
                dying = False
                terminar_partida(False)

        if not game_over and countdown_val <= 0 and not paused:
            wave_timer += 1
            if wave_timer > 250:
                wave += 1
                wave_timer = 0

            spawn_timer += 1
            spawn_rate = max(12, (70 - wave * 5) / dificultad)
            if spawn_timer >= spawn_rate and len(bosses) == 0:
                spawn_timer = 0
                size = random.randint(18, 38)
                x = random.randint(size, GAME_WIDTH - size)
                nuevo_asteroide = Asteroid(x, -size - 10, size)
                nuevo_asteroide.speed *= dificultad
                asteroids.append(nuevo_asteroide)

            alien_spawn_timer += 1
            if alien_spawn_timer >= max(90, 200 / dificultad) and wave >= 2 and len(bosses) == 0:
                alien_spawn_timer = 0
                side = random.choice(["left", "right", "top"])
                alien_ships.append(AlienShip(side))

            boss_def = get_boss_for_wave(wave)
            if boss_def and len(bosses) == 0 and len(alien_ships) == 0:
                if boss_def.spawn_wave == 20:
                    # La Anomalia Final: la version con sprites y 3 fases de
                    # boss.py, en vez del dibujo vectorial generico de WaveBoss.
                    jefe_final = FinalBoss()
                    jefe_final.definition = boss_def
                    bosses.append(jefe_final)
                else:
                    bosses.append(WaveBoss(boss_def))
                audio.sonido_alerta_jefe()

            for b in bosses[:]:
                if isinstance(b, (WaveBoss, FinalBoss)):
                    ret_b = b.update(ship)
                    if ret_b:
                        for rb in ret_b:
                            boss_bullets.append(rb)
                    if not b.active:
                        if not b.rewarded:
                            b.rewarded = True
                            stats_jefes += 1
                            score += 500 * (b.definition.spawn_wave // 5)
                            last_boss_rewards = list(b.definition.rewards)
                            boss_reward_timer = 180
                            for reward in b.definition.rewards:
                                powerups.append(PowerUp(b.x + random.uniform(-40, 40), b.y, reward.buff_type))
                            explosion_color = ROSA if b.definition.spawn_wave == 20 else RED
                            explosion_size = 80 if b.definition.spawn_wave == 20 else 50
                            explosions.append(Explosion(b.x, b.y, explosion_color, explosion_size))
                            particle_count = 50 + b.definition.spawn_wave
                            particles.extend([Particle(b.x, b.y, AMARILLO) for _ in range(particle_count)])
                            particles.extend([Particle(b.x, b.y, ORANGE) for _ in range(particle_count - 10)])
                            audio.sonido_victoria()
                            dificultad += 0.2
                            if b.definition.spawn_wave == 20:
                                particles.extend([Particle(b.x, b.y, WHITE) for _ in range(30)])
                                terminar_partida(True)
                        bosses.remove(b)

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
                bullet = aship.update()
                if bullet:
                    alien_bullets.append(bullet)
                if not aship.active:
                    alien_ships.remove(aship)
                    buff = random_buff_type()
                    powerups.append(PowerUp(aship.x, aship.y, buff))
                    explosions.append(Explosion(aship.x, aship.y, PURPLE, 15))
                    particles.extend([Particle(aship.x, aship.y, PINK) for _ in range(8)])
                    score += 50

            for b in bullets[:]:
                for a in asteroids[:]:
                    dist = math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)
                    if dist < a.size + b.radius:
                        a.flash_timer = 6
                        explosions.append(Explosion(a.x, a.y, ORANGE, 20))
                        particles.extend([Particle(a.x, a.y, RED) for _ in range(8)])
                        audio.sonido_explosion()
                        asteroid_kills += 1
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
                        buff = random_buff_type()
                        powerups.append(PowerUp(aship.x, aship.y, buff))
                        explosions.append(Explosion(aship.x, aship.y, PURPLE, 15))
                        particles.extend([Particle(aship.x, aship.y, PINK) for _ in range(8)])
                        audio.sonido_explosion()
                        stats_aciertos += 1
                        stats_alienigenas += 1
                        score += 50
                        if not b.piercing:
                            b.active = False
                        aship.active = False
                        break

            for b in bullets[:]:
                for boss in bosses[:]:
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
                            stats_jefes += 1
                            if hasattr(boss, 'definition') and boss.definition.spawn_wave == 20:
                                score += 1000
                                for _ in range(5):
                                    buff = random_buff_type()
                                    powerups.append(PowerUp(boss.x + random.uniform(-40, 40), boss.y, buff))
                                explosions.append(Explosion(boss.x, boss.y, ROSA, 80))
                                particles.extend([Particle(boss.x, boss.y, AMARILLO) for _ in range(50)])
                                particles.extend([Particle(boss.x, boss.y, ORANGE) for _ in range(40)])
                                particles.extend([Particle(boss.x, boss.y, WHITE) for _ in range(30)])
                                audio.sonido_victoria()
                                terminar_partida(True)
                            else:
                                score += 500 * (boss.definition.spawn_wave // 5 if hasattr(boss, 'definition') else 1)
                                for reward in (boss.definition.rewards if hasattr(boss, 'definition') else []):
                                    powerups.append(PowerUp(boss.x + random.uniform(-30, 30), boss.y, reward.buff_type))
                                explosions.append(Explosion(boss.x, boss.y, RED, 50))
                                particles.extend([Particle(boss.x, boss.y, YELLOW) for _ in range(30)])
                                particles.extend([Particle(boss.x, boss.y, ORANGE) for _ in range(20)])
                                audio.sonido_victoria()
                                dificultad += 0.2
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
                        score += objetivo.size // 10 + 1
                        if asteroid_kills % POWERUP_SPAWN_EVERY == 0:
                            powerups.append(PowerUp(objetivo.x, objetivo.y, random_buff_type()))
                        objetivo.active = False
                    elif objetivo_tipo == "alien":
                        powerups.append(PowerUp(objetivo.x, objetivo.y, random_buff_type()))
                        stats_alienigenas += 1
                        score += 50
                        objetivo.active = False
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
                    msg = ship.apply_buff(p.buff_type)
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

        screen.fill(DARKER_BG)

        game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        game_surface.fill(DARK_BG)
        for estrella in estrellas_juego:
            estrella.update()
            estrella.draw(game_surface)

        if countdown_val > 0:
            draw_countdown(game_surface, GAME_WIDTH, GAME_HEIGHT, countdown_val, font, info_font, big_font)

        elif not game_over and not dying:
            for p in powerups:
                p.draw(game_surface)
            for aship in alien_ships:
                aship.draw(game_surface)
            for boss in bosses:
                boss.draw(game_surface)
            for ab in alien_bullets:
                ab.draw(game_surface)
            for bb in boss_bullets:
                bb.draw(game_surface)
            for a in asteroids:
                a.draw(game_surface)
            for b in bullets:
                b.draw(game_surface)
            ship.draw(game_surface)
            for lb in lightning_bolts:
                dibujar_rayo(game_surface, lb)
            for e in explosions:
                e.draw(game_surface)
            for p in particles:
                p.draw(game_surface)

            draw_hud(game_surface, score, wave, ship.lives, ship.buffs, font, small_font, hand_active, ship.max_lives)
            draw_buff_hud(screen, ship.buffs, game_offset_x, game_offset_y)

            if boss_reward_timer > 0 and last_boss_rewards:
                draw_boss_rewards(game_surface, "Jefe Derrotado", last_boss_rewards, GAME_WIDTH // 2, GAME_HEIGHT - 60)

            if hand_active:
                indicator = render_texto_pixelado(small_font, "Manos detectada | Punio = Disparar (3 en rafaga)", GREEN)
            else:
                indicator = render_texto_pixelado(small_font, "Buscando mano...", RED)
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
            fade = 255 - int(200 * (death_timer / 180))
            overlay = pygame.Surface(game_surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, fade))
            game_surface.blit(overlay, (0, 0))
            dying_text = render_texto_pixelado(font, "¡Impacto crítico!", ROSA)
            game_surface.blit(dying_text, (GAME_WIDTH // 2 - dying_text.get_width() // 2, GAME_HEIGHT // 2))

        if game_over:
            for p in powerups:
                p.draw(game_surface)
            for aship in alien_ships:
                aship.draw(game_surface)
            for boss in bosses:
                boss.draw(game_surface)
            for ab in alien_bullets:
                ab.draw(game_surface)
            for bb in boss_bullets:
                bb.draw(game_surface)
            for a in asteroids:
                a.draw(game_surface)
            for b in bullets:
                b.draw(game_surface)
            ship.draw(game_surface)
            for e in explosions:
                e.draw(game_surface)
            for p in particles:
                p.draw(game_surface)

            if boss_reward_timer > 0 and last_boss_rewards:
                draw_boss_rewards(game_surface, "Jefe Derrotado", last_boss_rewards, GAME_WIDTH // 2, GAME_HEIGHT - 60)

            if game_victory:
                draw_victory_screen(game_surface, GAME_WIDTH, GAME_HEIGHT, score, wave, font, big_font, stats=stats_actuales())
            else:
                draw_game_over(game_surface, GAME_WIDTH, GAME_HEIGHT, score, wave, font, big_font, GOButtons, game_over_selected, stats=stats_actuales())

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
        screen.blit(game_surface, (game_offset_x, game_offset_y))

        pygame.draw.rect(screen, CYAN, (game_offset_x - 2, game_offset_y - 2, GAME_WIDTH + 4, GAME_HEIGHT + 4), 2)

        if not game_over and frame_actual is not None:
            preview_resized = resize_frame(frame_actual, PREVIEW_WIDTH, PREVIEW_HEIGHT)
            preview_surf = surface_from_frame(preview_resized)
            preview_rect = preview_surf.get_rect(topright=(SCREEN_WIDTH - 8, 8))
            draw_camera_preview(screen, preview_surf, preview_rect, pygame.time.get_ticks())

        pygame.display.flip()

    cap.release()
    hand_detector.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()