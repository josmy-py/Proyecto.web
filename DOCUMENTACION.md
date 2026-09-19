# Documentacion Completa - Nave vs Asteroides

## Indice
1. [Registro de Tecnologias](#registro-de-tecnologias)
2. [Descripcion General](#descripcion-general)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Modulos](#modulos)
5. [MediaPipe Hand Landmarker](#mediapipe-hand-landmarker)
6. [Sistema de Juego](#sistema-de-juego)
7. [Control por Mano](#control-por-mano)
8. [API de OpenCV usada](#api-de-opencv-usada)
9. [API de Pygame usada](#api-de-pygame-pygame-ce-257-usada)
10. [Optimizaciones](#optimizaciones)
11. [Sistema de Sprites y Personalizacion](#sistema-de-sprites-y-personalizacion)
12. [Sistema de Audio](#sistema-de-audio)

---

## Registro de Tecnologias

| Tecnologia | Version | Tipo | Propósito |
|-----------|---------|------|-----------|
| Python | 3.14.6 | Lenguaje | Lenguaje de programacion principal |
| pygame-ce | 2.5.7 | Biblioteca de juegos | Renderizado grafico, ventana, entrada de usuario |
| SDL2 (incluido en pygame-ce) | 2.32.10 | Motor grafico | Backend de renderizado, audio, eventos |
| opencv-python | 5.0.0 | Vision por computadora | Captura de camara, conversion de color |
| NumPy | 2.5.1 | Computacion cientifica | Arreglos multidimensionales para procesamiento de imagenes |
| mediapipe | 0.10.35 | ML/IA | Deteccion de mano en tiempo real |
| hand_landmarker.task | 1 (float16) | Modelo ML | 21 landmarks por mano para tracking |
| MediaPipe Tasks API | - | SDK | Interfaz de programacion para ML tasks |

---

## Descripcion General

Es un juego de nave espacial contra asteroides y naves alienigenas controlado por gestos de mano usando la camara web y MediaPipe Hand Landmarker. El jugador mueve una nave espacial con la mano y dispara una rafaga de balas (triple con el power-up correspondiente) para destruir asteroides que caen desde arriba. Cada 5 asteroides destruidos otorga un power-up aleatorio. Aparecen jefes de oleada en las oleadas 5, 10, 15 y 20 (el ultimo es el jefe final, con sprites propios y 3 fases). Naves alienigenas aparecen desde la oleada 2 y disparan al jugador. El puntaje maximo y la oleada mas alta se guardan entre partidas, y el juego tiene musica y efectos de sonido generados proceduralmente (ver "Sistema de Sprites y de Audio" al final de este documento).

---

## Estructura del Proyecto

```
Proyecto/
├── main.py                     # Punto de entrada - bucle principal del juego
├── requirements.txt            # Lista de dependencias pip
├── README.md                   # Instrucciones de usuario
├── DOCUMENTACION.md            # Este archivo
├── progreso.json               # Puntaje maximo y oleada maxima (se crea solo)
├── custom_skins.json           # Colores de nave personalizados (se crea solo)
├── models/
│   └── hand_landmarker.task  # Modelo de deteccion de mano de MediaPipe (7.8 MB)
├── assets/
│   ├── sprites/                # PNG generados por tools/generate_sprites.py
│   └── audio/                  # WAV generados por tools/generate_audio.py (sfx/ y music/)
├── tools/
│   ├── generate_sprites.py     # Genera los PNG de assets/sprites (Pillow + numpy)
│   ├── generate_audio.py       # Genera los WAV de assets/audio (numpy)
│   └── preview_sprites.py      # Hoja de contacto para revisar sprites (solo desarrollo)
└── modules/                    # Todos los modulos del juego
    ├── __init__.py             # Hace que modules/ sea un paquete Python
    ├── constants.py            # Constantes globales (colores, dimensiones, indices)
    ├── skins.py                # Colores de nave personalizados (custom_skins.json)
    ├── progress.py             # Puntaje/oleada maxima (progreso.json)
    ├── entities/
    │   ├── ship.py              # Clase Ship (jugador con sistema de buffs)
    │   ├── bullet.py             # Clase Bullet (bala del jugador)
    │   ├── asteroid.py           # Clases Asteroid, Particle, Explosion (visual)
    │   ├── enemy.py              # AlienShip, AlienBullet
    │   ├── powerup.py            # Clase PowerUp y tipos de buffs
    │   └── boss.py               # FinalBoss (jefe de la oleada 20) + FinalBossBullet
    ├── core/
    │   └── boss_system.py       # BossDefinition, WaveBoss (oleadas 5/10/15) + WaveBossBullet
    └── systems/
        ├── input.py              # Integracion con MediaPipe Hand Landmarker
        ├── sprites.py            # Carga/tintado/cache de los PNG de assets/sprites
        ├── audio.py              # Reproduccion de efectos y musica (assets/audio)
        ├── menu.py               # Menu principal, personalizacion, selector de color
        ├── ui.py                 # HUD, pantallas de countdown/game over/victoria
        └── fonts.py              # Carga de fuentes con cache
```

---

## Modulos

> **Nota:** las rutas de esta seccion son historicas (de una version anterior
> del proyecto, cuando todo vivia directo en `modules/`). La ubicacion actual
> de cada clase esta en el arbol de arriba (`modules/entities/`, `modules/core/`,
> `modules/systems/`); el contenido descrito abajo sigue siendo valido salvo
> que se indique lo contrario mas adelante.

### `modules/constants.py`
Define todas las constantes del juego. Sin dependencias externas.

**Contenido:**
- Dimensiones de pantalla (`SCREEN_WIDTH`, `SCREEN_HEIGHT`, `GAME_WIDTH`, `GAME_HEIGHT`)
- Dimensiones del preview de camara (`PREVIEW_WIDTH`, `PREVIEW_HEIGHT`)
- FPS objetivo
- Colores RGB (constantes nombradas: `WHITE`, `RED`, `GREEN`, `CYAN`, `YELLOW`, `BLUE`, `ORANGE`, `PURPLE`, `PINK`, `DARK_BG`, `DARKER_BG`)
- Dimensiones de la nave (`SHIP_WIDTH`, `SHIP_HEIGHT`)
- Indices de landmarks de MediaPipe (muñeca, dedos, articulaciones)
- Constantes de power-ups (`POWERUP_SPAWN_EVERY`, `BUFF_TYPE_*`, `BUFF_DURATION*`)
- Constantes del boss (`BOSS_SPAWN_WAVE`, `BOSS_MAX_HP`, `BOSS_SPEED`, etc.)

### `modules/ship.py`
Clase `Ship` - la nave del jugador.

**Dependencias:** `pygame`, `math`, `modules.constants`, `modules.bullet`

**Atributos:**
- `x`, `y` - posicion actual
- `target_x`, `target_y` - posicion destino (seteada por la mano)
- `speed` - velocidad de interpolacion
- `shoot_cooldown` / `shoot_delay` - control de cadencia de disparo
- `lives` - vidas del jugador (3 al inicio, max 5)
- `triple_shot_active` - si el buff triple shot esta activo
- `buffs` - diccionario de buffs activos con timers
- `thrust_particles` - particulas de energia de los motores
- `engine_flame_phase` - animacion de llama del motor

**Metodos:**
- `update()` - interpolacion suave, limites de pantalla, degradacion de buffs
- `draw()` - renderiza la nave con glow, cockpit, wing accents, flame animation
- `shoot()` - retorna lista de 1 o 3 bullets segun triple_shot
- `apply_buff(buff_type)` - aplica un buff y retorna mensaje
- `take_damage()` - reduce vidas, activa invencibilidad temporal

### `modules/bullet.py`
Clase `Bullet` - bala del jugador. Ligera, sin dependencias externas.

**Dependencias:** `pygame`, `modules.constants`

**Metodos:**
- `update()` - mueve la bala hacia arriba
- `draw()` - dibuja la bala como circulo amarillo con borde blanco

### `modules/asteroid.py`
Clases `Asteroid`, `Particle`, `Explosion` - entorno del juego y efectos visuales.

**Dependencias:** `pygame`, `random`, `math`, `modules.constants`

**Asteroid:**
- Forma poligonal aleatoria generada en `__init__` (7-12 vertices)
- Tres capas de color (base, dark, light) para textura rocosa
- Crateres generados procedimentalmente (3-6 por asteroide)
- Destellos blancos al ser golpeada (`flash_timer`)
- Rotacion continua con `rot_speed`

**Particle:**
- Particulas individuales con alpha fade-out
- Velocidad aleatoria, vida limitada
- Tamaño se escala con la vida restante

**Explosion:**
- Coleccion de 20+ particles para efecto de destruccion

### `modules/powerup.py`
Clase `PowerUp` - objetos de poder que aparecen cada 5 asteroides destruidos.

**Dependencias:** `pygame`, `random`, `math`, `modules.constants`

**Tipos de buff:**
| Tipo | Color | Etiqueta | Duracion |
|------|-------|----------|----------|
| EXTRA_LIFE | ROJO | +1 | Instantaneo |
| FAST_SHOOT | CYAN | FAST | 400 frames (~7s) |
| TRIPLE_SHOT | PURPLE | 3X | 500 frames (~8s) |

**Metodos:**
- `update()` - movimiento hacia abajo, pulso visual, expiracion
- `draw()` - circulo pulsante con etiqueta

### `modules/alien_ship.py`
Clases `AlienShip`, `AlienBullet`, `BossShip`, `BossBullet` - enemigos.

**Dependencias:** `pygame`, `random`, `math`, `modules.constants`

**AlienShip:**
- Entra desde izquierda, derecha o arriba
- Movimiento sinusoidal
- Dispara balas alienigenas periodicamente
- Al ser destruida da +50 puntos y spawnea un power-up

**AlienBullet:**
- Balas pequenas disparadas por naves alienigenas
- Direccion segun el lado de origen

**BossShip (oleada 10):**
- 55px de tamaño, 200 HP
- Se mueve de lado a lado en la parte superior
- Dispara 3 rayos verticales cada 25 frames
- Barra de vida visible (colorea segun HP: verde > 50%, amarillo > 25%, rojo restante)
- Animaciones de daño: glow rojo, particulas de chispa, core se oscurece
- Al destruirse: explosion de 50 particulas + 3 power-ups aleatorios + 500 puntos

**BossBullet:**
- Balas grandes (radius 4) disparadas por el boss
- Color rojo con centro amarillo
- Se mueven hacia abajo a 5px/frame

### `modules/hand_tracker.py`
Integracion con MediaPipe para deteccion de mano.

**Dependencias:** `cv2`, `numpy`, `mediapipe`, `importlib`

**Funciones:**
- `init_hand_landmarker(model_path)` - crea el detector con opciones Video mode
- `process_camera_frame(detector, frame, timestamp_ms)` - procesa frame y retorna resultado
- `is_fist(hand_lm)` - detecta si la mano esta cerrada (puño) comparando tips vs PIPs
- `find_hand_position(hand_lm, game_w, game_h)` - retorna coordenadas x, y de la muñeca

### `main.py`
Entry point - contiene el bucle principal del juego.

**Flujo principal:**
1. Inicializa pygame (pantalla completa 1280x720) y MediaPipe
2. Abre camara web con OpenCV (640x480)
3. Bucle de juego a 60 FPS:
   a. Lee eventos (ESC, R, QUIT)
   b. Captura frame de camara
   c. Detecta mano con MediaPipe `detect_for_video()`
   d. Actualiza posicion de nave (interpolacion suave)
   e. Detecta puño → dispara rafaga de 3 balas
   f. Actualiza balas, asteroides, alien ships, boss ships, boss bullets
   g. Detecta colisiones (balas↔asteroides, balas↔aliens, boss bullets↔nave, aliens↔nave, asteroides↔nave, powerups↔nave)
   h. Spawnea power-ups cada 5 kills de asteroides
   i. Spawnea naves alienigenas tras oleada 2
   j. Spawnea boss en oleada 10
   k. Actualiza particles, explosiones
   l. Renderiza todo en pygame (game area + camera preview)
   m. Muestra countdown inicial (5s)

---

## MediaPipe Hand Landmarker

### Version utilizada
MediaPipe 0.10.35 (ultima version antes de 1.0 que elimino la API de `solutions`).

### API
`mediapipe.tasks.python.vision.HandLandmarker`

- `HandLandmarkerOptions` para configurar deteccion
  - `base_options` con `model_asset_path` apuntando al modelo descargado
  - `running_mode=VIDEO` optimizado para video en tiempo real
  - `num_hands=1` detecta solo una mano
- `HandLandmarker.create_from_options(options)` crea el detector
- `detect_for_video(image, timestamp_ms)` deteccion con timestamp (baja latencia)
- `HandLandmarkerResult` con `hand_landmarks` lista de landmarks por mano

### Modelo
`hand_landmarker.task` (7.8 MB, float16) - descargado de Google Cloud Storage
- 21 puntos de referencia (landmarks) por mano detectada
- Cada landmark tiene `.x`, `.y`, `.z` (coordenadas normalizadas 0.0-1.0)

### Indices de landmarks
```
0: WRIST (muñeca) - usado para posicionar la nave
1-4: THUMB (pulgar)
5-8: INDEX (indice) - 8=tip, 6=PIP
9-12: MIDDLE (medio) - 12=tip, 10=PIP
13-16: RING (anular) - 16=tip, 14=PIP
17-20: PINKY (meñique) - 20=tip, 18=PIP
```

### Deteccion de puño (fist)
Se verifica que las puntas de los 4 dedos (8, 12, 16, 20) esten por encima de sus respectivas articulaciones PIP (6, 10, 14, 18). Si `tip.y < pip.y` para todos los dedos, la mano esta cerrada -> se dispara.

### Por que MediaPipe Tasks en vez de MediaPipe Solutions
- MediaPipe `solutions` fue deprecado en versiones 0.10+
- La API de `tasks` es la unica disponible en versiones modernas
- `detect_for_video()` usa timestamps para tracking temporal, reduciendo latencia
- Modelo float16 optimizado para rendimiento en tiempo real

---

## Sistema de Juego

### Nave del Jugador
- Forma de poligono tipo flecha con cockpit
- Glow cyan debajo de la nave
- Animacion de llama del motor (3 capas, pulsante)
- Wing accents en cyan claro
- Invencibilidad temporal al tomar damage (parpadea cada 3 frames)
- 3 vidas al inicio, max 5
- Sistema de buffs visuales (iconos sobre la nave)

### Asteroides
- Poligonos irregulares (7-12 vertices) generados proceduralmente
- Tres capas de color (base, dark, light) para efecto rocoso
- 3-6 crateres decorativos por asteroide
- Destellos blancos al ser destruidos (`flash_timer`)
- Diversos tamanos (18-38 pixeles)
- Velocidad y rotacion aleatorias

### Balas del Jugador
- 1 o 3 balas segun triple_shot (disparo en rafaga)
- Amarillas con borde blanco
- Velocidad: 9 pixels/frame hacia arriba

### Balas Alienigenas
- Balas pequeas (radius 3) disparadas por AlienShip
- Naranjas con borde blanco
- Velocidad: 4 pixels/frame

### Balas del Boss
- Balas grandes (radius 4) despues de la barra
- Rotacion
- Color ROJO
- Barra de vida mostrable

### Oleadas
- Cada 250 frames(~4 segundos) aumenta la oleada
- Mas asteroides por oleada (`spawn_rate = max(15, 70 - wave * 5)`)
- Naves alienigenas aparecen desde oleada 2
- Boss aparece en oleada 10

### Colisiones
- Balas ↔ Asteroides: distancia < size + radius
- Balas ↔ Naves alienigenas: distancia < ship_size + radius
- Balas del boss ↔ Nave: distancia < radius + SHIP_WIDTH/2
- Asteroids ↔ Nave: distancia < size + SHIP_WIDTH/2
- Power-ups ↔ Nave: distancia < radius + SHIP_WIDTH/2

---

## Control por Mano

### Flujo de deteccion
1. OpenCV captura frame de la camara web (640x480)
2. Frame volteado horizontalmente (espejo)
3. Convertido de BGR a RGB
4. Creado `mediapipe.Image` desde el array NumPy RGB
5. `detect_for_video()` procesa el frame con timestamp
6. Se extrae el landmark de la muñeca (WRIST, indice 0)
7. Se mapea de coordenadas normalizadas (0-1) a coordenadas del juego
8. Se verifica si es puño comparando tips vs PIPs de los 4 dedos
9. Si es puño → se dispara rafaga de 3 balas

### Interpolacion suave
La posicion destino del jugador se interpola gradualmente usando:
```
x += (target_x - x) * speed
speed = 0.18
```
Esto evita movimientos bruscos.

---

## API de OpenCV usada

| Funcion | Uso |
|---------|-----|
| `cv2.VideoCapture(0)` | Abre la camara web |
| `cap.read()` | Lee un frame |
| `cv2.flip(frame, 1)` | Volteo horizontal (espejo) |
| `cv2.cvtColor(frame, COLOR_BGR2RGB)` | Conversion de color |
| `cv2.resize(frame, (w, h))` | Redimensionar para preview |
| `frame.shape[:2]` | Obtener alto y ancho del frame |

---

## API de Pygame (pygame-ce 2.5.7) usada

| Funcion/Metodo | Uso |
|----------------|-----|
| `pygame.init()` | Inicializa todos los sub-modulos |
| `pygame.display.set_mode(size, FULLSCREEN)` | Crea ventana pantalla completa |
| `pygame.display.flip()` | Actualiza toda la pantalla |
| `pygame.Surface((w, h))` | Crea superficie off-screen para doble buffer |
| `pygame.image.frombuffer(data, size, fmt)` | Crea superficie pygame desde array numpy (sin copia) |
| `pygame.font.SysFont(name, size)` | Crea fuente de texto renderizable |
| `surface.blit(source, pos)` | Dibuja una superficie sobre otra |
| `pygame.draw.polygon/surface/circle/rect/ellipse()` | Dibuja formas geometricas |
| `pygame.draw.circle(screen, color, pos, radius)` | Dibuja circulos para balas y efectos |
| `pygame.time.Clock().tick(FPS)` | Controla FPS y retorna milisegundos transcurridos |
| `pygame.event.get()` | Obtiene eventos de entrada del sistema |
| `pygame.KEYDOWN` | Evento de tecla presionada |
| `pygame.K_ESCAPE`, `pygame.K_r` | Constantes de teclas |
| `pygame.image.frombuffer()` | Creacion directa desde buffer numpy sin copia |

---

## Framework y Modelos de ML adicionales

| Tecnologia | Version | Uso |
|-----------|---------|-----|
| MediaPipe Tasks Python | incluido en mediapipe 0.10.35 | SDK para ML inference |
| Hand Landmarker model | float16 v1 | Deteccion de 21 landmarks por mano |
| BaseOptions | incluido | Configuracion de carga de modelo |
| RunningMode | enum | Modo VIDEO para latencia baja |

---

## Desarrollo y herramientas

| Herramienta | Uso |
|------------|-----|
| pip | Gestion de paquetes Python |
| PowerShell | Terminal de comandos en Windows |
| Python -m py_compile | Verificacion de sintaxis sin ejecutar |
| AST (ast.parse) | Analisis estatico de codigo Python |
| importlib | Importacion dinamica de modulos |

---

## Optimizaciones

1. **detect_for_video() con timestamps:** En lugar de procesar cada frame como imagen estatica, MediaPipe usa el timestamp para tracking temporal entre frames, reduciendo latencia perceptible.

2. **Off-screen rendering:** Se renderiza en una superficie `game_surface` de tamaño `GAME_WIDTH x GAME_HEIGHT` y luego se blit a la pantalla principal. Esto permite agregar el preview de camara sin afectar el area de juego.

3. **List cleanup pattern:** Se itera sobre copias de listas (`for b in bullets[:]`) y se remueven elementos inactivos dentro del bucle, evitando modificar la lista durante la iteracion.

4. **Early exit en colisiones:** Al detectar la primera colision de una bala con un asteroide, se rompe el bucle interno (`break`), evitando comprobar colisiones ya resueltas.

5. **Particulas efimeras:** Se remueven particles con `life <= 0` cada frame para mantener la lista limpia y evitar renders innecesarios.

6. **thrust particles limit:** Se limita a 30/40 particulas de motor para evitar acumulacion excesiva.

7. **Buff timer cleanup:** Se iteran y eliminan buffs expirados al inicio de cada update, limpiando automaticamente el diccionario.
---

# Sistema de Sprites y Personalizacion

> Capitulo agregado junto con los graficos del juego. Las rutas indicadas aqui
> son las vigentes (los modulos viven en `modules/entities/`, `modules/systems/`
> y `modules/core/`).

## 1. Por que sprites por capas

El objetivo era doble: que las naves, asteroides y enemigos tuvieran graficos
propios, y que el color elegido por el jugador se aplicara a la nave sin
multiplicar los archivos. La solucion fue separar cada nave en tres capas PNG:

| Archivo              | Contenido                          | Tintado en runtime |
|----------------------|------------------------------------|--------------------|
| `<clase>_body.png`   | Casco, en escala de grises         | Si (color de casco)|
| `<clase>_wing.png`   | Alas y aletas, en escala de grises | Si (color de alas) |
| `<clase>_detail.png` | Cabina, toberas, luces, contorno   | No                 |

El tintado se hace multiplicando la capa gris por el color:

```python
superficie.fill((r, g, b, 255), special_flags=pygame.BLEND_RGBA_MULT)
```

Un pixel gris 255 devuelve el color puro y los grises mas oscuros producen el
sombreado. Con 3 archivos por nave se cubren infinitas combinaciones de color.

## 2. Generacion de los graficos (`tools/generate_sprites.py`)

Los PNG no se dibujaron a mano: se generan de forma procedural con Pillow y
NumPy. El proceso por sprite es:

1. **Silueta**: se dibujan los poligonos de la pieza a 4x de resolucion
   (supersampling) y se reducen con LANCZOS para obtener bordes suaves.
2. **Mapa de luz**: un campo NumPy con un brillo especular, caida cilindrica
   hacia los costados y oscurecimiento hacia los motores.
3. **Detalles restados/sumados**: lineas de panel, crateres, grietas y motas se
   aplican como deltas de luminancia sobre ese mapa.
4. **Composicion**: `RGBA = (luz, luz, luz, silueta)` para las capas tintables;
   la capa de detalle se dibuja aparte a color.
5. **Contorno**: se obtiene por dilatacion/erosion de la silueta (`ImageFilter`)
   y se le suma una luz de borde superior izquierda.

Se generan 38 archivos: 4 naves x 3 capas, 14 asteroides (un PNG cada uno, con
"familias" de forma distintas: redonda/alargada/irregular/fragmento/afilada),
3 enemigos x 3 capas y el jefe final (`boss/mothership_*.png`) x 3 capas
(casco, anillo de nodos y detalle). Pillow solo hace falta para regenerarlos;
el juego en si solo necesita pygame.

## 3. Carga y cache (`modules/systems/sprites.py`)

| Funcion                     | Que hace                                            |
|-----------------------------|-----------------------------------------------------|
| `load_raw(*partes)`         | Carga un PNG con cache; devuelve `None` si falta    |
| `tint(surface, color)`      | Copia la superficie multiplicada por un color       |
| `get_ship_surface(...)`     | Compone alas + casco + detalle, tinta y escala      |
| `get_enemy_surface(...)`    | Igual para las naves enemigas                       |
| `get_asteroid_surface(...)` | Tinta y escala una de las 14 rocas                  |
| `get_boss_surface(...)`     | Compone anillo + casco + detalle del jefe final     |
| `get_rotated(...)`          | Rotacion cacheada en pasos de 6 grados              |
| `blit_centered(...)`        | Dibuja centrado; devuelve `False` si no habia sprite|

Tres decisiones de rendimiento:

- **Cuantizacion de color**: las claves de cache redondean el color a multiplos
  de 8 para que arrastrar el selector no genere cientos de superficies.
- **Rotaciones en pasos de 6 grados**: 60 rotaciones posibles por sprite en vez
  de una por frame.
- **Caches con tope** (`_MAX_COMPOSED`, `_MAX_ROTATIONS`) con desalojo FIFO, para
  que la memoria no crezca sin limite durante partidas largas.

Si falta `assets/sprites/`, todas las funciones devuelven `None` y cada entidad
dibuja su version vectorial de respaldo: el juego nunca se cae por un PNG.

## 4. Aspectos y color personalizado (`modules/skins.py`)

Un aspecto es un diccionario con cuatro colores: `body_color`, `wing_color`,
`glow_color` y `flame_color`. Hay 4 aspectos predefinidos por clase mas el
aspecto `custom`, cuyo color lo elige el jugador.

- `set_custom_color(tipo, rgb, persist=False)`: fija el color. Mientras se
  arrastra el selector se llama sin persistir (solo memoria); al confirmar se
  llama con `persist=True` y se escribe `custom_skins.json`.
- `get_skin_colors(tipo, aspecto)`: devuelve la tupla de 4 colores que consumen
  tanto el menu como la nave, garantizando que se vea igual en ambos lados.
- `apply_skin_to_ship(nave, aspecto)`: aplica los colores y llama a
  `nave.invalidate_sprite()` para que el sprite cacheado se recomponga.
- `normalize_skin(...)`: completa los colores que falten derivandolos del casco.

## 5. Selector de color (`modules/systems/menu.py`)

`ColorPicker` mantiene el color en HSV y expone tres barras arrastrables mas 12
colores rapidos. Detalles de implementacion:

- `_layout()` calcula un `pygame.Rect` por barra y por preset; `handle_event()`
  prueba primero los presets y luego cada barra, y guarda cual se esta
  arrastrando en `self.dragging`.
- `_exact_rgb` guarda el color exacto cuando viene de un preset, porque el viaje
  RGB -> HSV -> RGB introduce una diferencia de una unidad por redondeo.
- `consume_changed()` es una bandera de un solo uso: la escena la lee cada frame
  para saber si debe repintar las tarjetas y la vista previa.

La escena de seleccion muestra, ademas, un panel con la nave en grande, sus
estadisticas y la ventaja de su clase, dibujada con el mismo sprite tintado que
se usara en la partida.

## 6. Como se traslada el diseno a la partida

1. El menu devuelve `START_GAME:<clase>:<aspecto>`.
2. `main.py` construye `Ship(x, y, clase, aspecto)`.
3. `Ship._apply_type_stats()` fija estadisticas y `apply_skin_to_ship()` los colores.
4. `Ship._get_sprite()` compone y cachea el sprite con esos colores.
5. La llama del motor usa `flame_color` y las balas se crean con `glow_color`,
   de modo que el color elegido tambien se ve en el disparo.

## 7. Correcciones incluidas

- `asteroid.py`: al rotar los crateres se usaba una variable (`vy`) de otro
  bucle, lo que los dibujaba fuera de lugar. El dibujado ahora es por sprite.
- `ship.py`: el buff de velocidad permanente sumaba a `permanent_speed_bonus`
  pero `update()` nunca lo usaba, asi que no tenia efecto.
- `menu.py`: en el selector de color solo respondia la barra de tono y los
  colores rapidos no eran clicables.
- `menu.py` / `ui.py`: se creaban fuentes con `SysFont` dentro de los bucles de
  dibujo; ahora se cachean en `_FONT_CACHE`.

---

# Sistema de Audio

> Capitulo agregado junto con la musica y los efectos de sonido. Igual que los
> graficos, el audio es 100% procedural (no hay archivos de sonido de terceros
> ni descargados de internet).

## 1. Generacion (`tools/generate_audio.py`)

Los WAV se sintetizan con NumPy (ondas seno/cuadrada/sierra + ruido blanco) y
se guardan con el modulo estandar `wave`, sin ninguna libreria de audio
externa. El generador produce:

- **8 efectos** (`assets/audio/sfx/*.wav`): disparo, explosion, impacto,
  powerup, boton, alerta_jefe, victoria y game_over.
- **2 pistas de musica en loop** (`assets/audio/music/*.wav`): `musica_menu`
  (calma, con pads) y `musica_juego` (bajo + arpegio + percusion simple).

Las pistas de musica se arman pegando notas de duracion fija (nunca un
oscilador continuo de principio a fin) y se les aplica un fundido de 25ms al
inicio y al final (`fundido_de_bucle`) para que el loop no suene con un
"clic" al reiniciar.

## 2. Reproduccion (`modules/systems/audio.py`)

Sigue la misma filosofia que `sprites.py`: si `pygame.mixer` no puede
inicializarse (sin tarjeta de sonido) o faltan los WAV, todas las funciones
fallan en silencio y el juego sigue funcionando sin sonido.

| Funcion                        | Que hace                                        |
|---------------------------------|--------------------------------------------------|
| `inicializar()`                 | Inicia el mixer y precarga los efectos          |
| `sonido_*()`                    | Reproduce un efecto (disparo, explosion, etc.)  |
| `reproducir_musica("menu"/"juego")` | Cambia de pista solo si no es ya la actual  |
| `pausar_musica()` / `reanudar_musica()` | Usadas por la tecla de pausa (P)        |
| `alternar_silencio()`           | Tecla M: silencia musica y efectos              |

## 3. Progreso guardado (`modules/progress.py`)

Mismo patron que `modules/skins.py`: un JSON en la raiz (`progreso.json`) con
el puntaje maximo y la oleada mas alta alcanzada, tolerante a archivo
ausente/corrupto. `registrar_partida(puntaje, oleada)` se llama una sola vez,
al terminar la partida (`terminar_partida()` en `main.py`), y devuelve si se
establecio un record nuevo para mostrarlo en la pantalla final.

## 4. Controles agregados

| Tecla | Accion |
|-------|--------|
| P     | Pausa / reanuda la partida (congela movimiento, disparo y musica) |
| F11   | Alterna pantalla completa / ventana |
| M     | Silencia / reactiva musica y efectos |

## 5. El jefe final ya esta conectado

`FinalBoss` (`modules/entities/boss.py`) tiene sprites propios, 3 fases y 5
patrones de ataque, pero no se usaba en ninguna partida: los 4 jefes de
oleada (5/10/15/20) pasaban siempre por `WaveBoss` (`modules/core/boss_system.py`),
dibujado con vectores. Se conecto especificamente para la oleada 20 (coincide
en nombre con `BossDefinition(boss_id="anomalia", name="La Anomalía Final", ...)`,
asi que claramente era la intencion original). Al crearlo se le asigna
`jefe_final.definition = boss_def` (la definicion real de la oleada 20), asi
el codigo de recompensas y de victoria de `main.py` funciona igual para
`WaveBoss` y `FinalBoss` sin necesitar casos especiales.

## 6. Otras correcciones de esta sesion (en `main.py`)

- `reset_game()` reasignaba `start_time`/`start_countdown` sin declararlos
  `nonlocal`: creaba variables locales que se descartaban, asi que la cuenta
  regresiva no volvia a arrancar bien al reintentar partida.
- La camara se leia dos veces por frame (`cap.read()` una vez para la mano y
  otra para el preview); ahora se lee una sola vez y se reutiliza.
- `process_camera_frame()` puede devolver `None` cuando el frame-skip
  descarta un frame; `main.py` accedia a `result.hand_landmarks` sin
  comprobar `None` primero, lo que podia tronar el juego de forma
  intermitente.
- Los clics del menu principal nunca pasaban por `MenuButton.handle_event()`
  (se comprobaba `.hovered` directo), asi que el efecto de "ripple" al hacer
  clic nunca se veia.

