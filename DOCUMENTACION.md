# Documentacion Completa - Nave vs Asteroides

## Indice
1. [Registro de Tecnologias](#registro-de-tecnologias)
2. [Descripcion General](#descripcion-general)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Modulos](#modulos)
5. [MediaPipe Hand Landmarker](#mediapipe-hand-landmarker)
6. [Sistema de Juego](#sistema-de-juego)
7. [Control por Mano](#control-por-mano)
8. [Sistema de Texto](#sistema-de-texto)
9. [Sistema de Sprites](#sistema-de-sprites)
10. [Sistema de Audio](#sistema-de-audio)
11. [Menu, Dificultad y Ajustes](#menu-dificultad-y-ajustes)
12. [Estadisticas de Partida](#estadisticas-de-partida)
13. [API de OpenCV usada](#api-de-opencv-usada)
14. [API de Pygame usada](#api-de-pygame-pygame-ce-usada)
15. [Optimizaciones](#optimizaciones)
16. [Historial de correcciones](#historial-de-correcciones)

---

## Registro de Tecnologias

| Tecnologia | Tipo | Proposito |
|-----------|------|-----------|
| Python 3.14 | Lenguaje | Lenguaje de programacion principal |
| pygame-ce 2.5.x | Biblioteca de juegos | Renderizado grafico, ventana, entrada, audio |
| SDL2 (incluido en pygame-ce) | Motor grafico | Backend de renderizado, audio, eventos |
| opencv-python | Vision por computadora | Captura de camara, conversion de color |
| NumPy | Computacion cientifica | Arreglos para procesamiento de imagenes y sintesis de audio |
| Pillow | Procesamiento de imagenes | Generacion procedural de los sprites (solo en tools/, no en tiempo de juego) |
| mediapipe | ML/IA | Deteccion de mano en tiempo real |
| hand_landmarker.task | Modelo ML | 21 landmarks por mano para tracking |

---

## Descripcion General

Nave vs Asteroides es un juego de nave espacial contra asteroides y naves
alienigenas controlado por gestos de mano usando la camara web y MediaPipe
Hand Landmarker. El jugador mueve la nave con la mano y cierra el puño para
disparar (rafaga de 3 balas con el buff correspondiente). Cada 5 asteroides
destruidos aparece un power-up. Hay jefes de oleada en las oleadas 5, 10, 15
y 20; el ultimo ("La Anomalia Final") tiene 3 fases y sprite propio.

Antes de jugar el menu deja elegir la dificultad (facil/normal/dificil) y
tiene una pantalla de ajustes (volumen, sensibilidad de mano, camara). Al
terminar la partida se muestra precision de disparo, tiempo sobrevivido y
el desglose de enemigos destruidos, ademas del puntaje y el record.

Todos los graficos (naves, enemigos, asteroides, jefes, power-ups) y todo
el audio (musica y efectos) son generados de forma procedural por los
scripts de `tools/`; no hay ningun asset descargado de internet.

---

## Estructura del Proyecto

```
Proyecto/
├── main.py                     # Punto de entrada - bucle principal del juego
├── requirements.txt            # Lista de dependencias pip
├── README.md                   # Instrucciones de usuario
├── DOCUMENTACION.md            # Este archivo
├── progreso.json               # Puntaje maximo y oleada maxima (se crea solo)
├── ajustes.json                # Volumen, sensibilidad, camara, pantalla completa (se crea solo)
├── custom_skins.json           # Color de nave personalizado, si se usa (se crea solo)
├── models/
│   └── hand_landmarker.task    # Modelo de deteccion de mano de MediaPipe
├── assets/
│   ├── sprites/                # PNG generados por tools/generate_sprites.py
│   │   ├── ships/               # scout, tank, interceptor, bomber (x body/wing/detail)
│   │   ├── enemies/              # fighter, drone, gunner (x body/wing/detail)
│   │   ├── asteroids/             # 14 variantes (un PNG cada una)
│   │   ├── boss/                 # mothership (saucer), dragon, titan (x body/wing/detail)
│   │   └── powerups/              # 10 tipos de bonus (x body/detail)
│   └── audio/                  # WAV generados por tools/generate_audio.py (sfx/ y music/)
├── tools/
│   ├── generate_sprites.py     # Genera los PNG de assets/sprites (Pillow + numpy)
│   ├── generate_audio.py       # Genera los WAV de assets/audio (numpy)
│   └── preview_sprites.py      # Hoja de contacto para revisar sprites (solo desarrollo)
└── modules/                    # Todos los modulos del juego
    ├── __init__.py
    ├── constants.py            # Constantes globales (colores, dimensiones, buffs, dificultad)
    ├── skins.py                # Aspectos/colores de nave (custom_skins.json)
    ├── progress.py             # Puntaje/oleada maxima (progreso.json)
    ├── settings.py             # Ajustes del jugador (ajustes.json)
    ├── entities/
    │   ├── ship.py              # Clase Ship (jugador, buffs, disparo)
    │   ├── bullet.py             # Clase Bullet (bala del jugador)
    │   ├── asteroid.py           # Asteroid, Particle, Explosion
    │   ├── enemy.py              # AlienShip, AlienBullet (enemigos comunes)
    │   ├── powerup.py            # PowerUp y tipos de buff
    │   └── boss.py               # FinalBoss (oleada 20) + FinalBossBullet
    ├── core/
    │   └── boss_system.py       # BossDefinition, BossReward, WaveBoss (oleadas 5/10/15) + WaveBossBullet
    └── systems/
        ├── input.py              # Integracion con MediaPipe Hand Landmarker
        ├── sprites.py            # Carga/tintado/cache de los PNG de assets/sprites
        ├── audio.py              # Reproduccion de efectos y musica (assets/audio)
        ├── menu.py               # Menu principal, dificultad, ajustes
        ├── ui.py                 # HUD, countdown, game over/victoria, estadisticas
        └── fonts.py              # Fuente de terminal + cache de texto renderizado
```

---

## Modulos

### `modules/constants.py`
Todas las constantes del juego, sin dependencias de otros modulos (para
poder importarse desde cualquier lado sin ciclos).

- Dimensiones de pantalla y del area de juego (`SCREEN_WIDTH/HEIGHT`, `GAME_WIDTH/HEIGHT`)
- Paleta de colores nombrada (`WHITE`, `ROSA`, `AZUL`, `ELECTRICO`, etc.) mas alias en ingles (`RED`, `CYAN`...) para el codigo mas viejo
- Indices de landmarks de MediaPipe (muñeca, dedos, articulaciones)
- Constantes de power-ups: `BUFF_TYPE_*`, `BUFF_DURATION_*`, `LIGHTNING_ZAP_INTERVAL`, `LIGHTNING_RADIUS`
- Constantes de jefes: `BOSS_SPAWN_WAVE`, `FINAL_BOSS_SPAWN_WAVE`, `FINAL_BOSS_MAX_HP`, etc.
- `DIFICULTADES` (mapa nombre -> multiplicador) y `DIFICULTAD_DEFECTO`

### `modules/skins.py`
Aspectos (colores) de cada clase de nave. Cada aspecto es un diccionario
con `body_color`, `wing_color`, `glow_color` y `flame_color`; hay 4
predefinidos por clase mas el aspecto `custom` (color elegido a mano,
persistido en `custom_skins.json`). La nave siempre arranca con el aspecto
`default` porque ya no hay pantalla de menu para elegir otro, pero el
sistema entero sigue funcionando si algo pide un `skin_id` distinto.

### `modules/progress.py`
Puntaje maximo y oleada mas alta alcanzada, guardados en `progreso.json`.
Tolerante a archivo ausente o corrupto (usa los valores por defecto y
sigue andando). `registrar_partida(puntaje, oleada)` se llama una sola vez
al terminar la partida y devuelve si se establecio un record nuevo.

### `modules/settings.py`
Ajustes del jugador guardados en `ajustes.json`, mismo patron tolerante a
errores que `progress.py`: `volumen_musica`, `volumen_sfx`, `silenciado`,
`pantalla_completa`, `sensibilidad_mano` y `camera_index`. `cargar()` se
llama una vez al arrancar `main()`; `get(clave)`/`set_valor(clave, valor)`
leen y escriben (esta ultima persiste a disco en el momento).

### `modules/entities/ship.py`
Clase `Ship`, la nave del jugador.

**Atributos clave:** `x/y` (posicion), `target_x/target_y` (destino, lo
fija la mano detectada), `lives/max_lives`, `invincible_timer` (parpadeo
tras un golpe), `buffs` (diccionario de buffs activos con su timer),
`lightning_active`/`lightning_zap_cooldown` (campo electrico).

**Metodos:** `update()` interpola la nave hacia el destino y hace avanzar
timers/buffs; `draw()` dibuja el sprite, la barra de vida y las auras de
cada buff activo; `shoot()` devuelve 1 o 3 `Bullet` segun el buff de
rafaga triple; `apply_buff(tipo)` aplica un buff y devuelve un mensaje;
`take_damage()` resta una vida (o un golpe de escudo) y activa la
invencibilidad temporal — devuelve `True` solo si de verdad se perdio una
vida (ver la nota sobre este metodo en
[Historial de correcciones](#historial-de-correcciones)); `puede_descargar_rayo()`
/ `reiniciar_descarga_rayo()` controlan la cadencia del campo electrico.

### `modules/entities/bullet.py`
Clase `Bullet`: bala del jugador, viaja recto hacia arriba con una estela
que se desvanece. `piercing=True` (buff o clase bombardero) evita que se
desactive al primer impacto.

### `modules/entities/asteroid.py`
- **Asteroid**: usa uno de los 14 sprites de `assets/sprites/asteroids`
  (tintado y rotado); si faltan los PNG cae a un poligono aleatorio.
- **Particle**: chispa individual con velocidad aleatoria y desvanecimiento.
- **Explosion**: grupo de `Particle` para el efecto de destruccion; la
  reutilizan tambien enemigos, jefes y power-ups, no solo los asteroides.

### `modules/entities/enemy.py`
- **AlienShip**: nave enemiga comun (variantes fighter/drone/gunner, ver
  `ENEMY_VARIANTS`). Entra por un costado o por arriba, avanza hacia el
  lado opuesto y dispara `AlienBullet` a intervalos aleatorios. Aparecen
  desde la oleada 2.
- **AlienBullet**: bala pequeña que viaja en linea recta segun el lado de
  origen.

Los jefes de oleada **no** viven aca (antes habia una clase `BossShip`
vieja en este archivo, sin usar; se elimino, ver
[Historial de correcciones](#historial-de-correcciones)): estan en
`modules/core/boss_system.py` y `modules/entities/boss.py`.

### `modules/entities/powerup.py`
Clase `PowerUp`: capsula que cae lentamente y desaparece si no se recoge.
`buff_type` es uno de los `BUFF_TYPE_*` de `constants.py`; color, etiqueta
e icono salen de ahi. `random_buff_type()` sortea un tipo de "drop comun"
(no incluye los permanentes que solo reparten los jefes) y
`buff_duration(tipo)` da la duracion en frames.

| Tipo | Etiqueta | Efecto |
|------|----------|--------|
| `extra_life` | +1 | Vida extra instantanea |
| `fast_shoot` | FAST | Cadencia de disparo mejorada |
| `triple_shot` | 3X | Rafaga de 3 balas |
| `shield` | DEF | Absorbe 3 golpes |
| `piercing` | PEN | Las balas atraviesan varios objetivos |
| `attract` | MAG | Imanta los power-ups cercanos |
| `lightning_field` | RAYO | Campo electrico: zapea lo mas cercano cada ~0.2s (ver mas abajo) |
| `damage_up`, `speed_up`, `max_life_up`, `rapid_fire` | DMG+/SPD+/MAX+/RAPID | Permanentes, solo los reparten los jefes |

**Bonus "Rayo" (campo electrico):** mientras esta activo, cada
`LIGHTNING_ZAP_INTERVAL` frames la nave descarga un rayo sobre el
asteroide/alien/jefe mas cercano dentro de `LIGHTNING_RADIUS` (ver
`Ship.puede_descargar_rayo()`/`reiniciar_descarga_rayo()` en `ship.py` y el
bloque que arma el rayo en el bucle principal de `main.py`). El rayo se
dibuja como una linea quebrada (`dibujar_rayo()` en `main.py`) que se
desvanece en unos pocos frames. Asteroides y naves alien mueren de un
zap; los jefes reciben daño normal (`take_damage`).

### `modules/entities/boss.py`
Clase `FinalBoss` (oleada 20, "La Anomalia Final") + `FinalBossBullet`.
Tiene 3 fases (sube al pasar 66% y 33% de vida) y cada fase agrega
patrones de ataque (`SPREAD`, `AIMED`, `CIRCULAR`, `SPIRAL`, `RAIN`). Usa
el sprite "anomaly" (comparte archivo con "saucer", ver `mothership_*.png`)
si esta disponible, si no cae al dibujo vectorial.

### `modules/core/boss_system.py`
- **BossDefinition**: datos fijos de un jefe de oleada (vida, velocidad,
  patrones, colores, `body_type` para elegir sprite, `rewards`).
- **BossReward**: un buff que el jefe reparte al morir.
- **BOSS_DEFINITIONS**: la lista de los 4 jefes (`sentinel` oleada 5,
  `dragon` oleada 10, `titan` oleada 15, `anomalia` oleada 20 — este ultimo
  en realidad se instancia como `FinalBoss`, no como `WaveBoss`).
- **WaveBoss** / **WaveBossBullet**: instancia jugable de un jefe de oleada
  construida a partir de una `BossDefinition`. Mismo esquema de fases que
  `FinalBoss`. Agregar un jefe nuevo es sumar una `BossDefinition` sin
  tocar la logica de `WaveBoss`.

### `modules/systems/input.py`
Integracion con MediaPipe para deteccion de mano.

- `init_hand_landmarker(model_path)`: crea el detector en modo VIDEO.
- `process_camera_frame(detector, frame, timestamp_ms)`: detecta la mano,
  o devuelve `None` si el frame-skip descarta ese frame.
- `is_fist(hand_lm)`: puño cerrado = punta de los 4 dedos por encima de su
  propia articulacion PIP.
- `find_hand_position(hand_lm, game_w, game_h, sensibilidad=1.0)`: posicion
  de la muñeca mapeada al area de juego; `sensibilidad` amplifica (>1.0) o
  atenua (<1.0) el desplazamiento respecto del centro (ver
  [Menu, Dificultad y Ajustes](#menu-dificultad-y-ajustes)).

### `modules/systems/menu.py`
Ver la seccion [Menu, Dificultad y Ajustes](#menu-dificultad-y-ajustes).

### `modules/systems/ui.py`
HUD y pantallas del juego en si (no del menu): `draw_countdown`,
`draw_hud`/`draw_buff_hud` (con las clases `ModernHUD`, `HealthBar`,
`BuffChip`, `BuffHUD`), `draw_camera_preview`, `draw_boss_rewards`, y
`draw_game_over`/`draw_victory_screen` con las estadisticas de la partida
(ver [Estadisticas de Partida](#estadisticas-de-partida)).

### `modules/systems/fonts.py`
Ver la seccion [Sistema de Texto](#sistema-de-texto).

### `main.py`
Punto de entrada: inicializa pygame, carga progreso/ajustes, abre la
camara con OpenCV y corre el bucle principal a 60 FPS.

**Flujo por frame (resumen):**
1. Lee eventos (`ESC`, `F11` pantalla completa, `M` silenciar, `P` pausa,
   clicks/teclas del menu).
2. Si el menu esta activo, lo actualiza/dibuja y saltea el resto (`continue`).
3. Lee un frame de camara y detecta la mano (una sola vez por frame).
4. Mueve la nave hacia la mano (con la sensibilidad configurada) y dispara
   si detecta puño.
5. Actualiza balas, asteroides, naves alien, jefes, power-ups, particulas
   y el campo electrico si esta activo.
6. Resuelve colisiones (balas↔asteroides/aliens/jefes, aliens/asteroides/
   balas de jefe↔nave, power-ups↔nave) y actualiza las estadisticas de la
   partida en el proceso.
7. Dibuja todo (area de juego + HUD + preview de camara) y hace `flip()`.

---

## MediaPipe Hand Landmarker

### API
`mediapipe.tasks.python.vision.HandLandmarker`

- `HandLandmarkerOptions` con `base_options` (ruta al modelo),
  `running_mode=VIDEO` y `num_hands=1`.
- `HandLandmarker.create_from_options(options)` crea el detector.
- `detect_for_video(image, timestamp_ms)` usa el timestamp para tracking
  temporal entre frames (menos latencia que tratar cada frame suelto).

### Modelo
`hand_landmarker.task` (float16) con 21 landmarks por mano detectada, cada
uno con `.x`, `.y`, `.z` normalizados entre 0.0 y 1.0.

```
0: WRIST (muñeca) - usado para posicionar la nave
1-4: THUMB (pulgar)
5-8: INDEX (indice) - 8=tip, 6=PIP
9-12: MIDDLE (medio) - 12=tip, 10=PIP
13-16: RING (anular) - 16=tip, 14=PIP
17-20: PINKY (meñique) - 20=tip, 18=PIP
```

### Deteccion de puño (fist)
Se verifica que las puntas de los 4 dedos (8, 12, 16, 20) esten por encima
de sus respectivas articulaciones PIP (6, 10, 14, 18). Si se cumple para
los 4, la mano esta cerrada y se dispara.

### Por que MediaPipe Tasks en vez de MediaPipe Solutions
`solutions` esta deprecado desde las versiones 0.10+; `tasks` es la API
vigente, y `detect_for_video()` con timestamps reduce la latencia
perceptible frente a procesar cada frame como imagen suelta.

---

## Sistema de Juego

### Nave del jugador
Sprite propio por clase (scout/tank/interceptor/bomber, cada una con su
velocidad/cadencia/vida y un buff de clase), glow, animacion de llama del
motor, parpadeo de invencibilidad tras un golpe, barra de vida propia y
las auras visuales de cada buff activo (escudo, perforante, iman, campo
electrico).

### Oleadas y dificultad
La oleada sube cada ~250 frames (~4 segundos). Mas asteroides y naves
alien por oleada segun `dificultad` (multiplicador elegido al empezar mas
un incremento fijo cada jefe derrotado). Naves alien desde la oleada 2;
jefes en las oleadas 5, 10, 15 y 20.

### Colisiones
- Balas ↔ Asteroides / Naves alien / Jefes: por distancia entre centros.
- Balas de jefe / Naves alien / Asteroides ↔ Nave: idem, activan
  `Ship.take_damage()`.
- Power-ups ↔ Nave: al tocarse se aplica el buff (`Ship.apply_buff`).
- Campo electrico ↔ lo mas cercano: ver el bonus "Rayo" mas arriba.

---

## Control por Mano

### Flujo de deteccion
1. OpenCV captura un frame de la camara (una sola vez por frame de juego).
2. Se voltea horizontalmente (espejo) y se convierte de BGR a RGB.
3. Se arma un `mediapipe.Image` desde el array NumPy y se detecta la mano
   con `detect_for_video()`.
4. Se toma el landmark de la muñeca (indice 0) y se mapea a coordenadas
   del area de juego, aplicando la sensibilidad configurada.
5. Se revisa si es puño (4 dedos cerrados) y, si lo es, se dispara.

### Interpolacion suave
La nave no salta directo al destino: `Ship.update()` la acerca gradualmente
(`x += (target_x - x) * velocidad_de_interpolacion`), lo que evita
movimientos bruscos por temblores de la mano o del tracking.

### Sensibilidad
El ajuste "Sensibilidad" (pantalla de Ajustes, 0.5x a 2.0x) amplifica o
atenua el desplazamiento de la mano respecto del centro de la camara antes
de mapearlo al area de juego (`find_hand_position`, ver
`modules/systems/input.py`). Con 2.0x un movimiento chico de mano mueve la
nave el doble; con 0.5x hace falta mover la mano el doble para el mismo
desplazamiento en pantalla.

---

## Sistema de Texto

Todo el texto del juego (menu, HUD, jefes, pantallas de fin de partida)
pasa por `modules/systems/fonts.py`, que define una unica fuente "de
terminal" para dar ese aire binario/de codigo:

```python
FUENTE_DIGITAL = "lucidaconsole,consolas,couriernew,ubuntumono"
```

`pygame.font.SysFont` prueba los nombres en ese orden y usa el primero
instalado en el sistema; Lucida Console (la fuente clasica de la consola
de Windows) es la que mas se acerca a un aspecto "hacker/binario" de las
disponibles sin depender de una fuente pixel-art de terceros.

El texto se renderiza limpio y con antialias (sin bloques de pixel art:
esa etapa se probo y se saco porque volvia ilegibles palabras en minuscula
a menos de ~20px de alto) y se le agrega un contorno oscuro fino
(`_contorno_texto`) para que se lea bien sobre fondos con estrellas,
explosiones y luces parpadeantes.

**Puntos de entrada:**
- `render_text(text, size, color, ...)`: crea la fuente por tamaño (con
  cache) y renderiza; cachea tambien la superficie final.
- `render_texto_pixelado(fuente, texto, color, ancho_maximo=None, ...)`:
  igual pero con un objeto `Font` ya creado (por ejemplo, para reducir el
  texto de un boton si no entra). El nombre quedo de una version anterior
  con pixel art real; hoy solo aplica el contorno.

---

## Sistema de Sprites

> Detalle de generacion en `tools/generate_sprites.py` (Pillow + NumPy) y
> de carga/cache en `modules/systems/sprites.py`.

### Capas tintables
Cada nave/enemigo/jefe se exporta en 2 o 3 capas PNG:

| Archivo | Contenido | Tintado en runtime |
|---------|-----------|---------------------|
| `<clase>_body.png` | Casco, en escala de grises | Si (color principal) |
| `<clase>_wing.png` | Alas/anillo, en escala de grises | Si (color secundario) |
| `<clase>_detail.png` | Cabina, luces, contorno, iconos | No |

El tintado multiplica la capa gris por un color
(`pygame.BLEND_RGBA_MULT`): un pixel gris 255 da el color puro y los
grises mas oscuros producen el sombreado, asi que un solo PNG cubre
infinitas combinaciones de color. Los power-ups solo tienen `body` +
`detail` (no tienen "ala").

### Que se genera
- **4 naves** (scout/tank/interceptor/bomber) x 3 capas.
- **14 asteroides**, un PNG cada uno, con "familias" de forma distintas
  (redonda/alargada/irregular/fragmento/afilada).
- **3 enemigos comunes** (fighter/drone/gunner) x 3 capas.
- **3 siluetas de jefe**: `saucer` (platillo clasico, se guarda como
  `mothership_*.png` por compatibilidad — la usan el jefe Centinela y La
  Anomalia Final), `dragon` (casco alargado con colmillos y ojo
  luminoso) y `titan` (casco hexagonal blindado con remaches grandes). Las
  tres comparten la posicion del anillo de nodos y la plataforma de la
  cupula, porque `boss.py`/`boss_system.py` dibujan encima, en tiempo
  real, la cupula animada, el piloto y las luces parpadeantes usando esas
  coordenadas fijas.
- **10 tipos de power-up**: una capsula compartida (estilo caja de bonus
  de recreativa, con remaches y tapa brillante) mas un icono grabado
  distinto por tipo (corazon, rayo, iman, escudo, espada...) y una
  etiqueta de texto debajo para que se entienda de un vistazo que hace
  cada uno.

### Carga y cache (`modules/systems/sprites.py`)
`load_raw` cachea cada PNG (devuelve `None` si falta); `get_ship_surface`,
`get_enemy_surface`, `get_asteroid_surface`, `get_boss_surface` y
`get_powerup_surface` componen+tiñen+escalan y cachean el resultado;
`get_rotated` cachea rotaciones en pasos de 6 grados. Los colores de cache
se cuantizan a multiplos de 8 para no generar cientos de superficies al
arrastrar un selector. Si falta `assets/sprites/` entero, todas las
funciones devuelven `None` y cada entidad dibuja su version vectorial de
respaldo: el juego nunca se cae por un PNG faltante.

Regenerar todo: `python tools/generate_sprites.py`.

---

## Sistema de Audio

Los WAV se sintetizan con NumPy (ondas seno/cuadrada/sierra + ruido
blanco) y se guardan con el modulo estandar `wave`, sin libreria de audio
externa (`tools/generate_audio.py`). Produce 7 efectos
(`assets/audio/sfx/*.wav`: disparo, explosion, impacto, powerup, boton,
alerta_jefe, victoria) y 3 pistas de musica en loop
(`assets/audio/music/*.wav`: menu, juego, muerte).

`modules/systems/audio.py` sigue la misma filosofia que `sprites.py`: si
`pygame.mixer` no puede inicializarse o faltan los WAV, todas las
funciones fallan en silencio.

| Funcion | Que hace |
|---------|----------|
| `inicializar()` | Inicia el mixer y precarga los efectos |
| `sonido_*()` | Reproduce un efecto |
| `reproducir_musica("menu"/"juego"/"muerte", loop=...)` | Cambia de pista solo si no es ya la actual; la de muerte suena una vez |
| `pausar_musica()` / `reanudar_musica()` | Tecla P |
| `set_volumen_musica(v)` / `set_volumen_sfx(v)` | Sliders de la pantalla de Ajustes |
| `alternar_silencio()` | Tecla M o boton de Ajustes; devuelve el nuevo estado |

---

## Menu, Dificultad y Ajustes

`modules/systems/menu.py` define `MenuScene`, cuyo atributo `state`
controla que pantalla esta activa:

- **`"main"`**: los 3 botones — JUGAR, AJUSTES, SALIR.
- **`"dificultad"`**: se entra al elegir JUGAR. Botones FACIL / NORMAL /
  DIFICIL (multiplicadores en `constants.DIFICULTADES`, ver mas abajo).
  Elegir uno arranca la partida devolviendo
  `"START_GAME:<nave>:<skin>:<dificultad>"`, que `main.py` interpreta para
  llamar a `reset_game()` con esa dificultad como base.
- **`"settings"`**: sliders de volumen de musica y efectos
  (`modules/systems/audio.py`), slider de sensibilidad de mano (0.5x-2.0x),
  y botones de silencio, pantalla completa y camara. Estos ultimos dos
  devuelven las señales `"TOGGLE_FULLSCREEN"` / `"CHANGE_CAMERA"`, que
  `main.py` resuelve recreando la ventana o reabriendo `cv2.VideoCapture`
  con el indice nuevo. Todo se persiste al toque via `modules/settings.py`.

> Nota: la version anterior del menu tenia una pantalla de "PERSONALIZAR"
> para elegir nave/color con un selector HSV (`ColorPicker`, `ShipCard`,
> `SkinCard`). Se removio a pedido (junto con las clases correspondientes,
> que quedaban sin usar) y en su lugar esta la pantalla de Ajustes.

### Dificultad
```python
DIFICULTADES = {"facil": 0.75, "normal": 1.0, "dificil": 1.4}
```
El multiplicador elegido es el valor inicial de la variable `dificultad`
en `main.py`, que ademas sube +0.2 cada vez que se derrota un jefe de
oleada. Afecta la velocidad de aparicion y la velocidad de asteroides y
naves alien (mas alto = mas dificil).

---

## Estadisticas de Partida

`main.py` trackea, ademas del puntaje y la oleada:

- **Disparos y aciertos**: `stats_disparos` sube por cada bala disparada;
  `stats_aciertos` por cada impacto contra un asteroide, nave alien o
  jefe (piercing puede sumar mas de un acierto por bala). La precision
  mostrada es `aciertos / disparos * 100`.
- **Tiempo sobrevivido**: se calcula en `terminar_partida()` a partir de
  `start_time`, descontando la cuenta regresiva inicial.
- **Enemigos destruidos por tipo**: asteroides (reutiliza `asteroid_kills`),
  alienigenas y jefes, contados tanto si el kill fue por bala como por el
  campo electrico.

`stats_actuales()` arma el diccionario que consumen
`draw_game_over`/`draw_victory_screen` (`modules/systems/ui.py`) para
mostrar "Precision: X%   Tiempo: M:SS" y "Asteroides: N   Alienigenas: N
Jefes: N" en la pantalla de fin de partida.

---

## API de OpenCV usada

| Funcion | Uso |
|---------|-----|
| `cv2.VideoCapture(indice)` | Abre la camara web (el indice sale de Ajustes) |
| `cap.read()` | Lee un frame (una sola vez por frame de juego) |
| `cv2.flip(frame, 1)` | Volteo horizontal (espejo) |
| `cv2.cvtColor(frame, COLOR_BGR2RGB)` | Conversion de color para MediaPipe |
| `cv2.resize(frame, (w, h))` | Redimensionar para el preview |

---

## API de Pygame (pygame-ce) usada

| Funcion/Metodo | Uso |
|----------------|-----|
| `pygame.init()` | Inicializa todos los sub-modulos |
| `pygame.display.set_mode(size, FULLSCREEN\|0)` | Crea la ventana (pantalla completa o no, segun Ajustes) |
| `pygame.display.flip()` | Actualiza toda la pantalla |
| `pygame.Surface((w, h), SRCALPHA)` | Superficies off-screen para componer capas con transparencia |
| `pygame.font.SysFont(name, size)` | Fuente de texto (cacheada en `modules/systems/fonts.py`) |
| `pygame.mask.from_surface(...)` | Silueta del texto para el contorno |
| `surface.blit(source, pos)` | Dibuja una superficie sobre otra |
| `pygame.draw.polygon/circle/rect/ellipse/lines()` | Formas geometricas |
| `pygame.transform.rotate/scale/smoothscale()` | Rotacion y escalado de sprites y texto |
| `pygame.mixer` | Musica y efectos (`modules/systems/audio.py`) |
| `pygame.time.Clock().tick(FPS)` | Controla FPS |
| `pygame.event.get()` | Eventos de entrada del sistema |

---

## Optimizaciones

1. **`detect_for_video()` con timestamps**: tracking temporal entre
   frames en vez de tratar cada uno como imagen suelta.
2. **Una sola lectura de camara por frame**: se reutiliza tanto para la
   deteccion de mano como para el preview.
3. **Off-screen rendering**: se dibuja en una superficie `game_surface` de
   `GAME_WIDTH x GAME_HEIGHT` y se hace `blit` a la pantalla principal,
   asi el preview de camara y el HUD no interfieren con el area de juego.
4. **Iterar copias de listas** (`for b in bullets[:]`) para poder remover
   elementos inactivos dentro del mismo bucle.
5. **`break` en colisiones**: al resolver el primer impacto de una bala se
   corta el bucle interno.
6. **Cache de sprites compuestos y de rotaciones** (`modules/systems/sprites.py`),
   con tope y desalojo FIFO para no crecer sin limite en partidas largas.
7. **Cache de texto renderizado** (`modules/systems/fonts.py`): la mascara
   y el contorno de cada combinacion texto/color/tamaño se calculan una
   sola vez.

---

## Historial de correcciones

Bugs reales encontrados y arreglados durante el desarrollo de las
funciones descritas arriba (no son solo mejoras, cambiaban el
comportamiento del juego):

- **Morir de un solo golpe con varias vidas de sobra**: en `main.py`, las
  tres colisiones que dañan a la nave (bala de jefe, nave alien, asteroide)
  disparaban la secuencia completa de "fin de partida" apenas
  `ship.take_damage()` devolvia `True`, sin fijarse si de verdad se habian
  agotado las vidas. Ahora solo terminan la partida cuando
  `not ship.alive`.
- **"Volver al Menu" y volver a jugar no reiniciaba la partida**: el flujo
  de `JUGAR` desde el menu no llamaba a `reset_game()`, asi que puntaje,
  oleada y la nave (potencialmente ya destruida) quedaban de la partida
  anterior. Ahora `START_GAME` siempre pasa por `reset_game()`, que ademas
  aplica la dificultad elegida.
- **Crash de color fuera de rango en jefes**: durante la transicion de
  fase, el brillo animado de la cupula (`180 + 120 * sin(...)`) podia
  superar 255 o bajar de 0, y pygame no acepta esos valores como color.
  Pasaba tanto en `WaveBoss` (`boss_system.py`) como en `FinalBoss`
  (`boss.py`); se acoto con `max(0, min(255, ...))` en ambos.
- **Botones de Game Over desalineados del click**: al agregar las
  estadisticas de partida se corrio la posicion visual de los botones,
  pero el rectangulo usado para detectar el click en `main.py` quedo en
  la posicion vieja.
- **Codigo muerto con comentarios en ingles**: `BossShip`/`BossBullet` en
  `modules/entities/enemy.py` (jefe viejo, ~300 lineas, reemplazado hace
  tiempo por `boss_system.py`/`boss.py` pero nunca borrado) no se
  importaban desde ningun lado. Se eliminaron junto con el import sin usar
  de `draw_rounded_rect`/`draw_glow_circle`. De paso, era la unica fuente
  de comentarios en ingles que quedaba en el proyecto.
- **Selector de color en el menu**: en una version anterior solo
  respondia la barra de tono y los colores rapidos no eran clicables; el
  selector completo (`ColorPicker`) se termino removiendo junto con toda
  la pantalla de personalizar nave.
