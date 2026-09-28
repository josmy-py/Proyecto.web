"""
Dragon Espacial (oleada 20): jefe unico como FinalBoss/TitanBoss/MegaBoss,
ya no un WaveBoss generico con el molde "platillo". Es un DRAGON de
verdad -craneo con cuernos, dos ojos que siguen a la nave con la mirada,
alas de murcielago bien abiertas a los costados, brazos con garras y una
cola larga que se curva hacia un lado, ver build_dragon_robot() en
tools/generate_sprites.py- no una nave ni un casco blindado. Los nombres
DRAGON_ROBOT_*/get_dragon_robot_surface se mantienen por compatibilidad
con el resto del codigo aunque ya no hay nada robotico en el diseño.

"apertura" (0.0 a 1.0) no es un iris abriendose: es cuanto DAÑO/heridas
tiene encima, y anima cuadro a cuadro por un flipbook real de 11 sprites
(ver sprites.get_dragon_robot_surface) en vez de solo cambiar de color -se
ve herirse de verdad, cada cambio de fase lo deja MAS lastimado que antes
(mas grietas, mas heridas al rojo vivo). El daño en si no es un dibujo
estatico: cada herida titila con brasas animadas y fase propia
(_dibujar_daños_dinamicos) y ademas escupe chispas de verdad hacia arriba
con probabilidad proporcional a su severidad (ver _emitir_chispas_daño),
asi que se ve "vivo" y no solo pintado:

  Modo Acecho (fase 1, apertura 0.0 - casi intacto): dardos de fuego
  dirigidos y rapidos, se reposiciona seguido.

  Modo Envite (fase 2, apertura 0.5 - ya con heridas visibles): cono de
  fuego frontal denso mas dos zarpazos incendiarios a los costados.

  Modo Furia (fase 3, apertura 1.0 - cubierto de heridas al rojo vivo):
  barrida circular pesada de fuego mas un ALIENTO DE FUEGO telegrafiado
  desde la garganta (la misma mecanica de "rayo de sobrecarga" de antes,
  reubicada en la boca en vez del ojo -un dragon respira fuego, no
  dispara laseres con la mirada), la version mas lenta pero mas letal.

Al cruzar cada umbral de vida se queda quieto (igual que los demas jefes
en phase_transition) mientras la transformacion entera se ve en pantalla
-no es un destello de color, son los cuadros intermedios del flipbook
reproduciendose en tiempo real, con chispas y sacudida- antes de volver a
atacar ya en el modo nuevo, MAS lastimado.

Al morir no desaparece de golpe: primero se queda temblando en un ultimo
gesto desafiante (death_state="riendo", los ojos estroboscopicos
rojo/blanco a toda velocidad, ver _dibujar_ojos) y despues estalla en
pedazos reales -no un destello vectorial- recortando su propio sprite en
una grilla que sale disparada hacia afuera girando y desvaneciendose
(death_state="explotando", ver _iniciar_explosion/_actualizar_explosion,
misma tecnica de fragmentacion que MegaBoss pero de una sola vez, sin
implosionar de vuelta). Mientras el death_state este activo sigue con
self.active=True a proposito, para que main.py no lo recompense/remueva a
mitad de la secuencia -recien pone self.active=False al terminar la
explosion, momento en el que el bucle principal dispara la recompensa
normal."""

import random
import math

from modules.constants import (
    ROSA, AMARILLO, WHITE, GAME_WIDTH, GAME_HEIGHT,
)
from modules.core.boss_system import WaveBossBullet
from modules.systems.fonts import render_text
from modules.systems import sprites

import pygame

# Tinte principal por fase/modo.
TINTES_POR_FASE = {
    1: (140, 100, 220),
    2: (230, 150, 70),
    3: (230, 70, 70),
}

NOMBRE_MODO = {
    1: "MODO ACECHO",
    2: "MODO ENVITE",
    3: "MODO FURIA",
}

_APERTURA_OBJETIVO = {1: 0.0, 2: 0.5, 3: 1.0}

# Colores de fuego reutilizados en varios ataques (dardos, cono, zarpazos,
# barrida y el aliento) - todo el arsenal es fuego, no proyectiles
# genericos de nave.
_FUEGO_ROJO = (230, 70, 40)
_FUEGO_NARANJA = (255, 140, 50)
_FUEGO_AMARILLO = (255, 200, 90)


class DragonBoss:
    """Jefe de la oleada 20. take_damage() sube de fase (1->2->3) al pasar
    los umbrales de 66%/33% de vida; cada cambio de fase dispara una
    transformacion visual real (ver apertura/_APERTURA_OBJETIVO) que lo
    deja mas lastimado que antes, ademas de cambiar el modo de combate. Al
    llegar a 0 de vida no muere al instante: ver
    _iniciar_muerte/_actualizar_muerte."""

    def __init__(self, dificultad=1.0):
        self.x = GAME_WIDTH // 2
        self.y = 100
        self.target_x = self.x
        self.target_y = self.y
        self.active = True
        self.max_hp = max(1, int(420 * (1.0 + (dificultad - 1.0) * 0.5)))
        self.hp = self.max_hp
        self.display_hp = float(self.max_hp)
        self.rotation = 0.0
        self._dificultad = dificultad
        self.phase = 1
        self.apertura = 0.0
        self.damaged_timer = 0
        self.particles = []
        self.chispas = []
        self.move_timer = 0
        self.move_cooldown = 70
        self.health_shake = 0
        self.health_deplete_anim = 1.0
        self.phase_transition = False
        self.phase_timer = 0
        self.name = "DRAGON ESPACIAL"
        self.rewarded = False

        self.shoot_timer = 30
        self.shoot_rate = max(6, int(26 / dificultad))

        # Aliento de fuego (fase 3 unicamente): aviso (carga en la
        # garganta) -> disparo (el chorro de fuego en si).
        self.rayo_cooldown = random.randint(260, 320) / dificultad
        self.rayo_state = None
        self.rayo_timer = 0
        self.rayo_angulo = 0.0
        self._ship_x, self._ship_y = self.x, self.y + 400

        # Secuencia de muerte: None mientras pelea con normalidad; "riendo"
        # -> "explotando" al llegar a 0 de vida (ver _iniciar_muerte).
        # active se mantiene True durante toda la secuencia a proposito.
        self.death_state = None
        self.death_timer = 0
        self.risa_fase = 0.0
        self.frag_pieces = []
        self.frag_timer = 0

    @property
    def speed(self):
        # mas agil casi intacto (fase 1), mas pesado y lastimado (fase 3).
        return (1.5 - 0.55 * self.apertura) * self._dificultad

    def take_damage(self, amount=1):
        if self.death_state is not None:
            return  # ya esta muriendo, ignora golpes de mas
        prev_hp = self.hp
        self.hp = max(0, self.hp - amount)
        if prev_hp > self.hp:
            self.health_deplete_anim = prev_hp / self.max_hp
        self.damaged_timer = 10
        self.health_shake = 10
        if self.hp <= 0:
            self._iniciar_muerte()
            return
        if self.hp < self.max_hp * 0.66 and self.phase == 1:
            self._transformar(2)
        elif self.hp < self.max_hp * 0.33 and self.phase == 2:
            self._transformar(3)

    def _transformar(self, fase_nueva):
        self.phase = fase_nueva
        self.phase_transition = True
        self.phase_timer = 100
        self.rayo_state = None
        for _ in range(26):
            self.chispas.append({
                'x': self.x + random.uniform(-70, 70),
                'y': self.y + random.uniform(-30, 30),
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'life': random.randint(30, 60),
                'max_life': 60,
            })

    # -------------------------------------------------------------- muerte

    def _iniciar_muerte(self):
        """Arranca la secuencia de derrota: primero se queda temblando en
        un ultimo gesto desafiante (death_state="riendo", los ojos
        estroboscopicos, ver _dibujar_ojos) antes de estallar en pedazos
        de verdad (ver _iniciar_explosion)."""
        self.death_state = "riendo"
        self.death_timer = 75
        self.risa_fase = 0.0
        self.rayo_state = None
        for _ in range(24):
            self.chispas.append({
                'x': self.x + random.uniform(-50, 50),
                'y': self.y + random.uniform(-60, 40),
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-3, 0.5),
                'life': random.randint(25, 50),
                'max_life': 50,
            })

    def _actualizar_muerte(self):
        if self.death_state == "riendo":
            self.risa_fase += 1
            if random.random() < 0.5:
                self.chispas.append({
                    'x': self.x + random.uniform(-45, 45),
                    'y': self.y + random.uniform(-50, 30),
                    'vx': random.uniform(-1.5, 1.5),
                    'vy': random.uniform(-2.5, -0.3),
                    'life': random.randint(20, 40),
                    'max_life': 40,
                })
            self.death_timer -= 1
            if self.death_timer <= 0:
                self._iniciar_explosion()
            return []
        # "explotando"
        self._actualizar_explosion()
        return []

    def _iniciar_explosion(self):
        """Recorta el sprite ACTUAL (ya en el peor estado de daño, fase 3)
        en una grilla de pedazos reales -no una forma vectorial- y les da
        una direccion de salida propia; a diferencia de MegaBoss no
        implosiona de vuelta: esta vez muere de verdad."""
        self.death_state = "explotando"
        display_w = sprites.DRAGON_ROBOT_DISPLAY_W
        display_h = sprites.DRAGON_ROBOT_DISPLAY_H
        sprite = sprites.get_dragon_robot_surface(1.0, TINTES_POR_FASE[3], display_w, display_h)
        self.frag_pieces = []
        if sprite is not None:
            cols, rows = 5, 7
            pw, ph = display_w / cols, display_h / rows
            for row in range(rows):
                for col in range(cols):
                    rx0, ry0 = int(col * pw), int(row * ph)
                    rx1 = display_w if col == cols - 1 else int((col + 1) * pw)
                    ry1 = display_h if row == rows - 1 else int((row + 1) * ph)
                    rect = pygame.Rect(rx0, ry0, max(1, rx1 - rx0), max(1, ry1 - ry0))
                    pieza = sprite.subsurface(rect).copy()
                    base_x = rect.centerx - display_w / 2.0
                    base_y = rect.centery - display_h / 2.0
                    dist = math.hypot(base_x, base_y) or 1.0
                    self.frag_pieces.append({
                        'surf': pieza,
                        'base_x': base_x, 'base_y': base_y,
                        'dir_x': base_x / dist, 'dir_y': base_y / dist,
                        'off': 0.0,
                        'ang': 0.0, 'ang_vel': random.uniform(-9, 9),
                    })
        self.frag_timer = 70
        self._frag_dur = 70
        for _ in range(60):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2, 7)
            self.particles.append({
                'x': self.x, 'y': self.y,
                'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
                'life': random.randint(30, 60), 'max_life': 60,
                'radius': random.randint(2, 5),
            })

    def _actualizar_explosion(self):
        t = 1.0 - max(0.0, self.frag_timer / self._frag_dur)
        for p in self.frag_pieces:
            p['off'] = 150 * (t * t)
            p['ang'] += p['ang_vel']
        if random.random() < 0.7:
            ang = random.uniform(0, 2 * math.pi)
            rad = random.uniform(10, 90)
            self.chispas.append({
                'x': self.x + math.cos(ang) * rad, 'y': self.y + math.sin(ang) * rad,
                'vx': random.uniform(-2, 2), 'vy': random.uniform(-3, -0.5),
                'life': random.randint(20, 40), 'max_life': 40,
            })
        self.frag_timer -= 1
        if self.frag_timer <= 0:
            self.frag_pieces = []
            self.active = False

    # -------------------------------------------------------------- update

    def update(self, ship=None):
        bullets = []
        self._ship_x = ship.x if ship is not None else self.x
        self._ship_y = ship.y if ship is not None else self.y + 400

        if self.death_state is not None:
            self.particles = [p for p in self._avanzar(self.particles)]
            self.chispas = [p for p in self._avanzar(self.chispas)]
            return self._actualizar_muerte()

        objetivo_apertura = _APERTURA_OBJETIVO[self.phase]
        self.apertura += (objetivo_apertura - self.apertura) * 0.045

        if self.phase_transition:
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase_transition = False
                self.apertura = objetivo_apertura

        self._update_movement()
        self.rotation += 0.6
        self.damaged_timer = max(0, self.damaged_timer - 1)

        if not self.phase_transition:
            self.shoot_timer -= 1
            if self.shoot_timer <= 0:
                self.shoot_timer = self.shoot_rate
                bullets.extend(self._crear_ataque(ship))

            if self.phase == 3:
                if self.rayo_state is not None:
                    bullets.extend(self._actualizar_rayo())
                else:
                    self.rayo_cooldown -= 1
                    if self.rayo_cooldown <= 0:
                        self._iniciar_rayo()

        if self.damaged_timer > 0 and random.random() < 0.4:
            self.particles.append({
                'x': self.x + random.uniform(-15, 15),
                'y': self.y + random.uniform(-10, 10),
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-2, 2),
                'life': random.randint(15, 35),
                'max_life': 35,
                'radius': random.randint(2, 5),
            })

        self._emitir_chispas_daño()

        self.particles = [p for p in self._avanzar(self.particles)]
        self.chispas = [p for p in self._avanzar(self.chispas)]

        if self.health_deplete_anim > self.hp / self.max_hp:
            self.health_deplete_anim = max(self.hp / self.max_hp, self.health_deplete_anim - 0.025)

        return bullets

    @staticmethod
    def _avanzar(lista):
        vivos = []
        for p in lista:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] > 0:
                vivos.append(p)
        return vivos

    def _update_movement(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 10:
            self.move_timer += 1
            if self.move_timer >= self.move_cooldown:
                self.move_timer = 0
                padding = 110
                self.target_x = random.randint(padding, GAME_WIDTH - padding)
                self.target_y = random.randint(60, GAME_HEIGHT // 3)
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
        self.x = max(90, min(GAME_WIDTH - 90, self.x))
        self.y = max(50, min(GAME_HEIGHT // 3 + 20, self.y))

    def _emitir_chispas_daño(self):
        """Ademas de la grieta ya horneada en el sprite (ver
        tools/generate_sprites.py _dragon_grieta), cada herida sigue
        "viva" en tiempo real mientras dura: brasas que saltan hacia
        arriba con probabilidad proporcional a la severidad actual (ver
        sprites.DRAGON_DAÑOS_FRAC), reutilizando self.chispas -mismo
        aspecto que las chispas de las transformaciones."""
        ancho, alto = sprites.DRAGON_ROBOT_DISPLAY_W, sprites.DRAGON_ROBOT_DISPLAY_H
        for fx, fy, inicio, fin in sprites.DRAGON_DAÑOS_FRAC:
            severidad = max(0.0, min(1.0, (self.apertura - inicio) / (fin - inicio)))
            if severidad <= 0 or random.random() >= severidad * 0.4:
                continue
            px = self.x + (fx - 0.5) * ancho
            py = self.y + (fy - 0.5) * alto
            self.chispas.append({
                'x': px + random.uniform(-4, 4),
                'y': py + random.uniform(-4, 4),
                'vx': random.uniform(-0.6, 0.6),
                'vy': random.uniform(-1.7, -0.4),
                'life': random.randint(14, 26),
                'max_life': 26,
            })

    # ------------------------------------------------------------ ataques

    def _crear_ataque(self, ship):
        if self.phase == 1:
            return self._ataque_acecho(ship)
        if self.phase == 2:
            return self._ataque_envite()
        return self._ataque_furia()

    def _ataque_acecho(self, ship):
        """Modo Acecho: dardos de fuego dirigidos y rapidos, tres a la
        vez en abanico angosto."""
        bullets = []
        if ship is None:
            return bullets
        angle_base = math.atan2(ship.y - self.y, ship.x - self.x)
        for i in range(3):
            angle = angle_base + (i - 1) * 0.1
            speed = 5.5
            bullets.append(WaveBossBullet(self.x, self.y, math.cos(angle) * speed, math.sin(angle) * speed, _FUEGO_NARANJA, 4))
        return bullets

    def _ataque_envite(self):
        """Modo Envite: cono de fuego frontal denso mas dos zarpazos
        incendiarios a los costados (ya con heridas visibles a esta
        altura del daño)."""
        bullets = []
        for i in range(-3, 4):
            angle = math.pi / 2 + i * 0.16
            bullets.append(WaveBossBullet(self.x, self.y + 10, math.cos(angle) * 4.2, math.sin(angle) * 4.2, _FUEGO_AMARILLO))
        for signo in (-1, 1):
            bullets.append(WaveBossBullet(self.x, self.y + signo * 30, signo * 1.5, 4.5, _FUEGO_ROJO, 5))
        return bullets

    def _ataque_furia(self):
        """Modo Furia: barrida circular pesada de fuego."""
        bullets = []
        count = 14
        base = self.rotation * 0.05
        for i in range(count):
            angle = base + (2 * math.pi * i) / count
            speed = 3.4
            bullets.append(WaveBossBullet(self.x, self.y, math.cos(angle) * speed, math.sin(angle) * speed, _FUEGO_ROJO, 6))
        return bullets

    def _iniciar_rayo(self):
        self.rayo_state = "aviso"
        self.rayo_timer = 65
        self.rayo_angulo = math.atan2(self._ship_y - self.y, self._ship_x - self.x)
        self.rayo_cooldown = random.randint(320, 400) / self._dificultad

    def _actualizar_rayo(self):
        self.rayo_timer -= 1
        if self.rayo_state == "aviso":
            # sigue apuntando mientras carga en la garganta, con suavizado
            objetivo = math.atan2(self._ship_y - self.y, self._ship_x - self.x)
            diff = (objetivo - self.rayo_angulo + math.pi) % (2 * math.pi) - math.pi
            self.rayo_angulo += diff * 0.08
            if self.rayo_timer <= 0:
                self.rayo_state = "disparo"
                self.rayo_timer = 22
            return []
        bullets = []
        vx = math.cos(self.rayo_angulo) * 9.0
        vy = math.sin(self.rayo_angulo) * 9.0
        bullets.append(WaveBossBullet(self.x, self.y, vx, vy, (255, 120, 60), 9))
        if self.rayo_timer <= 0:
            self.rayo_state = None
        return bullets

    # ---------------------------------------------------------------- draw

    def draw(self, screen, offset_x=0, offset_y=0):
        if self.death_state == "explotando":
            self._dibujar_explosion(screen, offset_x, offset_y)
            return

        temblor_y = 0
        if self.death_state == "riendo":
            # el ultimo gesto desafiante: un rebote vertical ritmico, no
            # un temblor al azar.
            temblor_y = int(6 * math.sin(self.risa_fase * 0.9))

        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y + temblor_y

        sombra_surf = pygame.Surface((200, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra_surf, (0, 0, 0, 55), (0, 0, 200, 40))
        screen.blit(sombra_surf, (cx - 100, cy + 90))

        color = TINTES_POR_FASE.get(self.phase, TINTES_POR_FASE[1])
        ancho = sprites.DRAGON_ROBOT_DISPLAY_W
        alto = sprites.DRAGON_ROBOT_DISPLAY_H
        sprite = sprites.get_dragon_robot_surface(self.apertura, color, ancho, alto)

        if sprite is not None:
            rect = sprite.get_rect(center=(cx, cy))
            screen.blit(sprite, rect)
            manto_top = rect.top
            manto_cx = rect.centerx
            ojo_izq_x = rect.left + ancho * sprites.DRAGON_OJO_IZQ_X_FRAC
            ojo_der_x = rect.left + ancho * sprites.DRAGON_OJO_DER_X_FRAC
            ojo_y = rect.top + alto * sprites.DRAGON_OJO_CY_FRAC
            ojo_r = ancho * sprites.DRAGON_OJO_R_FRAC
            self._dibujar_daños_dinamicos(screen, rect, ancho, alto)
            self._dibujar_garganta(screen, rect, ancho, alto)
        else:
            # Sin PNG no se dibuja un casco de respaldo por codigo: solo
            # quedan los "detalles" (ojos, barra de vida, chispas, particulas).
            manto_top = cy - 90
            manto_cx = cx
            ojo_izq_x, ojo_der_x, ojo_y, ojo_r = cx - 26, cx + 26, cy - 40, 12

        self._dibujar_ojos(screen, ojo_izq_x, ojo_der_x, ojo_y, ojo_r)

        if self.rayo_state is not None:
            self._dibujar_rayo(screen, cx, cy, offset_x, offset_y)

        if self.death_state != "riendo":
            barra_w = 150
            barra_h = 13
            barra_x = manto_cx - barra_w // 2
            barra_y = manto_top - 24

            temblor_x = temblor_y2 = 0
            if self.health_shake > 0:
                temblor_x = random.randint(-self.health_shake, self.health_shake)
                temblor_y2 = random.randint(-self.health_shake, self.health_shake)
                self.health_shake -= 1

            bx, by = barra_x + temblor_x, barra_y + temblor_y2
            sombra_barra = pygame.Surface((barra_w + 6, barra_h + 6), pygame.SRCALPHA)
            pygame.draw.rect(sombra_barra, (0, 0, 0, 60), (3, 3, barra_w, barra_h), border_radius=barra_h // 2)
            screen.blit(sombra_barra, (bx - 3, by - 3))

            fondo = (bx, by, barra_w, barra_h)
            pygame.draw.rect(screen, (20, 20, 35), fondo, border_radius=barra_h // 2)
            proporcion = max(0, self.hp / self.max_hp)
            relleno = int((barra_w - 2) * self.health_deplete_anim)
            if relleno > 0:
                color_vida = ROSA if proporcion > 0.66 else (AMARILLO if proporcion > 0.33 else _FUEGO_ROJO)
                pygame.draw.rect(screen, color_vida, (bx + 1, by + 1, relleno, barra_h - 2), border_radius=barra_h // 2)
            pygame.draw.rect(screen, WHITE, fondo, width=1, border_radius=barra_h // 2)

            etiqueta = f"{self.name} · {NOMBRE_MODO.get(self.phase, '')}"
            etiqueta_surf = render_text(etiqueta, 11, WHITE)
            screen.blit(etiqueta_surf, (manto_cx - etiqueta_surf.get_width() // 2, by - 18))
            porcentaje_surf = render_text(f"{int(proporcion * 100)}%", 10, WHITE)
            screen.blit(porcentaje_surf, (manto_cx - porcentaje_surf.get_width() // 2, by - 32))

        if self.phase_transition:
            alfa = int(150 * (0.5 + 0.5 * math.sin(self.phase_timer * 0.4)))
            destello = pygame.Surface((ancho + 60, alto + 60), pygame.SRCALPHA)
            pygame.draw.ellipse(destello, (255, 255, 255, alfa), (0, 0, ancho + 60, alto + 60), 6)
            screen.blit(destello, (cx - (ancho + 60) // 2, cy - (alto + 60) // 2))
            aviso_surf = render_text("TRANSFORMANDO...", 13, (255, 255, 255))
            screen.blit(aviso_surf, (cx - aviso_surf.get_width() // 2, manto_top - 52))

        if self.damaged_timer > 0:
            alfa_impacto = int(140 * (self.damaged_timer / 10))
            impacto_surf = pygame.Surface((90, 90), pygame.SRCALPHA)
            pygame.draw.circle(impacto_surf, (255, 130, 150, alfa_impacto), (45, 45), 45)
            screen.blit(impacto_surf, (cx - 45, cy - 20))

        for p in self.particles:
            alpha = p['life'] / p['max_life']
            size = max(1, int(p['radius'] * alpha))
            c = (int(200 * alpha), int(180 * alpha), int(255 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)

        for p in self.chispas:
            alpha = p['life'] / p['max_life']
            size = max(1, int(3 * alpha))
            c = (255, int(220 * alpha), int(120 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)

    def _dibujar_ojos(self, screen, ojo_izq_x, ojo_der_x, ojo_y, ojo_r):
        for ojo_x in (ojo_izq_x, ojo_der_x):
            self._dibujar_ojo(screen, ojo_x, ojo_y, ojo_r)

    def _dibujar_ojo(self, screen, ojo_x, ojo_y, ojo_r):
        """La pupila es 100% dinamica (la cuenca vacia ya viene horneada
        en el sprite, ver DRAGON_OJO_* en tools/generate_sprites.py): se
        desplaza cada frame hacia la nave, clampeada dentro de la cuenca,
        para que ambos ojos la sigan con la mirada en tiempo real (mismo
        truco que TitanBoss/FinalBoss, duplicado). En el ultimo gesto
        desafiante antes de morir (death_state) el pulso se vuelve mucho
        mas rapido y blanco, estroboscopico."""
        zocalo_r = ojo_r * 0.72
        dx, dy = self._ship_x - ojo_x, self._ship_y - ojo_y
        dist = math.hypot(dx, dy) or 1.0
        alcance = zocalo_r * 0.5
        despl_x = dx / dist * min(alcance, dist * 0.06)
        despl_y = dy / dist * min(alcance, dist * 0.06)
        px, py = ojo_x + despl_x, ojo_y + despl_y

        if self.death_state == "riendo":
            pulse = 0.5 + 0.5 * math.sin(self.risa_fase * 0.9)
            color = (255, int(60 + 150 * pulse), int(50 + 120 * pulse))
            intensidad = int(120 + 110 * pulse)
        else:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
            color = (255, int(190 + 35 * pulse), int(60 + 25 * pulse))
            intensidad = int(90 + 50 * pulse)

        glow = pygame.Surface((int(zocalo_r * 3), int(zocalo_r * 3)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, intensidad), (glow.get_width() // 2, glow.get_height() // 2), int(zocalo_r * 1.3))
        screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))
        pygame.draw.circle(screen, color, (int(px), int(py)), max(2, int(zocalo_r * 0.62)))
        pygame.draw.circle(screen, (255, 245, 225), (int(px), int(py)), max(2, int(zocalo_r * 0.28)))
        pygame.draw.circle(screen, WHITE, (int(px - zocalo_r * 0.14), int(py - zocalo_r * 0.14)), max(1, int(zocalo_r * 0.14)))

    def _dibujar_daños_dinamicos(self, screen, rect, ancho, alto):
        """La grieta en si ya viene horneada en el sprite (ver
        _dragon_grieta en tools/generate_sprites.py), pero el fuego que
        sale de ella es 100% en tiempo real: un resplandor que titila con
        una fase propia por punto (no todas parpadean sincronizadas, se
        ve mas organico) superpuesto encima de cada herida segun su
        severidad actual."""
        t = pygame.time.get_ticks()
        for fx, fy, inicio, fin in sprites.DRAGON_DAÑOS_FRAC:
            severidad = max(0.0, min(1.0, (self.apertura - inicio) / (fin - inicio)))
            if severidad <= 0:
                continue
            px = rect.left + fx * ancho
            py = rect.top + fy * alto
            titileo = 0.5 + 0.5 * math.sin(t * 0.02 + fx * 37.0 + fy * 19.0)
            r = (9 + 15 * severidad) * (0.7 + 0.3 * titileo)
            alpha = int(100 * severidad * (0.55 + 0.45 * titileo))
            glow = pygame.Surface((int(r * 2.6), int(r * 2.6)), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 130, 60, alpha), (glow.get_width() // 2, glow.get_height() // 2), int(r))
            screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))

    def _dibujar_garganta(self, screen, rect, ancho, alto):
        """Resplandor de la garganta -100% en tiempo real, nada horneado
        en el PNG-: un brillo tenue en reposo (como brasas siempre
        encendidas adentro), que se intensifica mientras carga el aliento
        de fuego (rayo_state == "aviso") y estalla brillante en el
        instante del disparo, en vez de una luz de nave parpadeando sola
        sin motivo."""
        px = rect.left + ancho * sprites.DRAGON_GARGANTA_X_FRAC
        py = rect.top + alto * sprites.DRAGON_GARGANTA_Y_FRAC
        t = pygame.time.get_ticks()
        if self.rayo_state == "aviso":
            carga = 1.0 - max(0.0, self.rayo_timer / 65.0)
            pulse = 0.5 + 0.5 * math.sin(t * 0.04)
            r = 10 + 22 * carga * (0.8 + 0.2 * pulse)
            alpha = int(120 + 120 * carga)
        elif self.rayo_state == "disparo":
            r = 30
            alpha = 220
        else:
            pulse = 0.5 + 0.5 * math.sin(t * 0.01)
            r = 8 + 2 * pulse
            alpha = int(70 + 30 * pulse)
        glow = pygame.Surface((int(r * 3), int(r * 3)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 160, 60, alpha), (glow.get_width() // 2, glow.get_height() // 2), int(r))
        screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))

    def _dibujar_explosion(self, screen, offset_x, offset_y):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        for p in self.frag_pieces:
            dx = p['base_x'] + p['dir_x'] * p['off']
            dy = p['base_y'] + p['dir_y'] * p['off']
            rotada = pygame.transform.rotate(p['surf'], p['ang'])
            t = max(0.0, min(1.0, self.frag_timer / self._frag_dur))
            rotada.set_alpha(max(0, int(255 * min(1.0, t * 1.6))))
            rect = rotada.get_rect(center=(int(cx + dx), int(cy + dy)))
            screen.blit(rotada, rect)

        for p in self.particles:
            alpha = p['life'] / p['max_life']
            size = max(1, int(p['radius'] * alpha))
            c = (int(255 * alpha), int(160 * alpha), int(60 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)

        for p in self.chispas:
            alpha = p['life'] / p['max_life']
            size = max(1, int(3 * alpha))
            c = (255, int(200 * alpha), int(90 * alpha))
            pygame.draw.circle(screen, c, (int(p['x']) + offset_x, int(p['y']) + offset_y), size)

    def _dibujar_rayo(self, screen, cx, cy, offset_x, offset_y):
        # Linea de mira/chorro de fuego dibujada directo sobre screen (sin
        # alpha, para no crear una superficie del tamaño de la pantalla
        # cada frame): alcanza y sobra con que la linea llegue bien afuera
        # del viewport.
        largo = math.hypot(GAME_WIDTH, GAME_HEIGHT) + 100
        x1 = cx + math.cos(self.rayo_angulo) * largo
        y1 = cy + math.sin(self.rayo_angulo) * largo
        if self.rayo_state == "aviso":
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.03)
            color = tuple(int(c * (0.5 + 0.5 * pulse)) for c in (255, 110, 60))
            pygame.draw.line(screen, color, (cx, cy), (x1, y1), 2)
            pygame.draw.circle(screen, (255, 140, 80), (cx, cy), int(8 + 6 * pulse), 2)
        elif self.rayo_state == "disparo":
            pygame.draw.line(screen, (255, 170, 80), (cx, cy), (x1, y1), 20)
            pygame.draw.line(screen, (255, 235, 200), (cx, cy), (x1, y1), 7)
