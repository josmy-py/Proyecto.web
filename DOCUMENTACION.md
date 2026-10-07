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
Hand Landmarker. El jugador mueve la nave con la mano; cada vez que cierra el
puño (flanco de cierre, no mientras lo mantiene cerrado) dispara un unico
disparo (`FIST_BURST_SHOTS`), sin fuego automatico. Con el buff `triple_shot`
ese disparo sale como abanico de 3 balas. Cada 5 asteroides
destruidos aparece un power-up. Una oleada exige destruir una cuota
minima de asteroides/naves alienigenas para pasar a la siguiente (ver
[Oleadas y dificultad](#oleadas-y-dificultad)); hay un jefe de oleada cada
10 oleadas si o si (10, 20, 30, 40), hasta el mega-jefe unico de la oleada
50 con dos fases propias (crucero de asalto -> esfera de combate con laser
cargable y lluvia de meteoritos) — derrotarlo es la unica forma de ganar
la partida.

Antes de jugar el menu deja elegir el modo de control (camara con gestos de
mano, o mando/joystick si hay uno conectado) y la dificultad (facil/normal/
dificil), y tiene una pantalla de ajustes (volumen, sensibilidad de mano,
camara). Al
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
│   │   └── powerups/              # 11 insignias pixel-art (x body/detail)
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
    │   ├── boss.py               # FinalBoss (oleada 40) + AnomalyLanza y demas ataques propios
    │   ├── dragon_boss.py        # DragonBoss (oleada 20, dragon organico que se destruye por fase)
    │   ├── titan_boss.py         # TitanBoss (oleada 30)
    │   └── mega_boss.py          # MegaBoss (oleada 50, jefe final unico)
    ├── core/
    │   └── boss_system.py       # BossDefinition, BossReward, WaveBoss (oleadas 10/20) + WaveBossBullet
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
tras un golpe), `buffs` (diccionario de buffs activos, cada uno
`{"timer": ..., "max_timer": ..., "permanent"?: True}`),
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

`_extender_buff(tipo, duracion)` es como se cargan los buffs con tiempo
(fast_shoot/triple_shot/shield/piercing/attract/lightning, todos con
`duracion` = 20s = `20 * FPS`): agarrar el mismo power-up de nuevo
mientras sigue activo no resetea el timer, sigue esta curva de apilado
segun cuantas veces se agarro ya (`self.buffs[tipo]["stacks"]`):

| Vez que se agarra | Duracion resultante |
|---|---|
| 1ra | `duracion` (20s) |
| 2da | se DUPLICA lo que quedaba (40s) |
| 3ra en adelante | +`BUFF_STACK_BONUS` (10s) cada vez |

El total (sea cual sea) se guarda tambien como `max_timer`, asi el HUD
(`BuffChip` en `ui.py`) puede mostrar que fraccion de tiempo queda con una
simple `timer / max_timer` sin conocer la duracion base ni el conteo de
stacks. `stacks` se resetea solo (vuelve a 1) cuando el buff termina de
vencer y se borra de `self.buffs`.
Los buffs "permanentes" (damage_up/speed_up/max_life_up/rapid_fire, y
cualquiera que coincida con el buff de clase de la nave — `class_buffs`,
ver `_apply_type_stats`) nunca vencen de verdad aunque el timer siga
bajando, asi que el HUD los muestra siempre a barra llena en vez de
vaciarse.

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

El icono es una **insignia pixel-art** (marco biselado caqui/negro tipo
boton de 16 bits + un ICONO propio por habilidad — no una letra generica
sobre el mismo cuadrado repetido, ver `_POWERUP_ICONOS`/
`build_powerup_body`/`build_powerup_detail` en `tools/generate_sprites.py`)
en vez de la vieja capsula metalica de recreativa: se genera a resolucion
nativa baja (`POWERUP_BADGE_PX = 24`) sin pasar por el
supersampling+LANCZOS que usa el resto de sprites (las formas se dibujan
directo con `ImageDraw` a resolucion final, sin antialiasing, para que
las aristas queden en bloque de verdad), y se escala en tiempo real con
`sprites._scaled_pixelado` (`pygame.transform.scale`, sin suavizar) en vez
de `smoothscale` — asi se ve en pixeles grandes de verdad. Por eso
`PowerUp.draw()` ya no rota el icono con el "wobble" que tenia antes
(rotar difuminaria los bordes en bloque); solo el pulso de tamaño lo hace
sentir vivo. El marco va siempre en los mismos tonos caqui/negro y cada
icono tiene su propio contorno/brillo fijo (capa `detail`, sin tintar,
con algun acento de color puntual como las puntas del iman); solo la
SILUETA del icono (capa `body`) se tiñe en tiempo real con el color propio
del bonus — cada tipo tiene su propia silueta, ya no comparten un mismo
cuadrado de fondo.

| Tipo | Icono | Etiqueta | Efecto |
|------|-------|----------|--------|
| `extra_life` | corazon | +1 | Vida extra instantanea |
| `fast_shoot` | dardo + estela | FAST | Cadencia de disparo mejorada (temporal) |
| `triple_shot` | tres disparos en abanico | 3X | Rafaga de 3 balas |
| `shield` | escudo | DEF | Absorbe 3 golpes |
| `piercing` | flecha atravesando un anillo | PEN | Las balas atraviesan varios objetivos |
| `attract` | iman de herradura (puntas rojo/azul) | MAG | Imanta los power-ups cercanos |
| `lightning_field` | rayo | RAYO | Campo electrico: zapea lo mas cercano cada ~0.2s (ver mas abajo) |
| `damage_up` | espada | DMG+ | Permanente, solo lo reparten los jefes |
| `speed_up` | doble flecha hacia arriba | SPD+ | Permanente, solo lo reparten los jefes |
| `max_life_up` | corazon con cruz | MAX+ | Permanente, solo lo reparten los jefes |
| `rapid_fire` | pistola de perfil | RAPID | Permanente, solo lo reparten los jefes |

**Bonus "Rayo" (campo electrico):** mientras esta activo, cada
`LIGHTNING_ZAP_INTERVAL` frames la nave descarga un rayo sobre el
asteroide/alien/jefe mas cercano dentro de `LIGHTNING_RADIUS` (ver
`Ship.puede_descargar_rayo()`/`reiniciar_descarga_rayo()` en `ship.py` y el
bloque que arma el rayo en el bucle principal de `main.py`). El rayo se
dibuja como una linea quebrada (`dibujar_rayo()` en `main.py`) que se
desvanece en unos pocos frames. Asteroides y naves alien mueren de un
zap; los jefes reciben daño normal (`take_damage`).

### `modules/entities/boss.py`
Clase `FinalBoss` (oleada `FINAL_BOSS_SPAWN_WAVE` = 40, "La Anomalia
Final") + `AnomalyLanza` + `AnomalyEmbestidaImpacto`. Es una **calavera
glicheada morada** (silueta propia — craneo redondeado, sienes anchas,
pomulos/quijada quebrados en punta, ver `_silueta_casco`/`_paneles_casco`/
`_detalle_extra_casco` en `tools/generate_sprites.py` — sin el anillo de
luces/cupula/piloto que comparten saucer/dragon; escalado
`sprites.ANOMALY_DISPLAY_SCALE` un poco mayor que un jefe de oleada
normal) con **dos cuencas vacias horneadas en el sprite** y dos pupilas
100% dinamicas dibujadas encima (`_dibujar_ojo`, llamado dos veces) que
seleccionan hacia la nave con la mirada en tiempo real, igual que
`TitanBoss._dibujar_ojo` pero duplicado.

Tiene 3 fases (sube al pasar 66% y 33% de vida, siempre dentro de la misma
familia morada — cada vez mas saturada/corrupta, no cambia de paleta) y
cada fase agrega patrones de ataque (`SPREAD`, `AIMED`, `CIRCULAR`,
`SPIRAL`, `RAIN`). **No dispara balas comunes**: todos sus patrones —
incluida la descarga del tether — usan `AnomalyLanza`, su propia masa
glicheada disparada en forma de esquirla/lanza alargada orientada segun su
velocidad (no un circulo), con el mismo fleco cromatico permanente rojo/
cian que antes tenia `FinalBossBullet` (la clase vieja ya no existe).

Ademas de esa rotacion tiene varios ataques propios independientes. Tres de
ellos ("primarios": comprometen el cuerpo del jefe, se turnan de a uno —
`primario_libre` en `update()`) y dos ("secundarios": no mueven el cuerpo,
pueden caer en paralelo a cualquiera de los primarios):

- **Tether** (primario — `_iniciar_tether`/`_actualizar_tether`): un hilo
  de energia violeta que rastrea la posicion de la nave durante ~0.8s (la
  animacion del hilo siguiendola en tiempo real *es* el aviso) y despues
  se congela y dispara un abanico de `AnomalyLanza` hacia ese punto ya
  fijo, no hacia la nave en tiempo real — asi que moverse durante o
  despues del rastreo esquiva el disparo.
- **Embestida** (primario — `_iniciar_embestida`/`_actualizar_embestida`,
  estados aviso→cargando→retiro): se queda temblando in situ mientras una
  linea punteada pulsante (`_dibujar_embestida_aviso`) marca el rumbo
  exacto hacia donde estaba la nave en ese instante (fijo, no persigue
  durante la carga), y despues se lanza en linea recta a gran velocidad —
  aceleracion cuadratica, no pareja, para que se sienta una embestida
  real — dejando una estela de siluetas fantasma (`embestida_trail`) y una
  zona de contacto que la sigue sola (`AnomalyEmbestidaImpacto`, duck-typed
  igual que las lanzas para sumarse a `boss_bullets` sin tocar `main.py`).
- **Salto/grieta** (primario — `_iniciar_salto`/`_actualizar_salto`): abre
  una grieta glicheada pulsante (`_dibujar_salto_aviso`) en un punto al
  azar de la mitad superior de la pantalla y, al cerrarse, la Anomalia
  reaparece ahi de un salto instantaneo (rompe el patron de atacar siempre
  desde donde ya estaba) y dispara de inmediato tres `AnomalyLanza` hacia
  la nave desde el nuevo angulo; tambien fuerza un glitch y clones
  fantasma en el punto de llegada.
- **Lluvia de esquirlas** (secundario — `_iniciar_lluvia`/
  `_actualizar_lluvia`): fractura un pedazo de su propio casco
  (particulas) y marca con un circulo pulsante (`_dibujar_lluvia_aviso`)
  una zona amplia alrededor de donde estaba la nave; al cerrarse, la zona
  entera "estalla" de golpe en `AnomalyEsquirlaSuelo` (fragmentos
  estaticos, no viajan) — hay que salir caminando de la zona marcada, no
  esquivar proyectil por proyectil.
- **Grito glicheado** (secundario, solo fase 3 — `_iniciar_grito`/
  `_actualizar_grito`): un anillo de `AnomalyLanza` lentas se expande
  cubriendo todo el ancho de pantalla, pero con un hueco angular fijo
  marcado durante el aviso con dos lineas (`_dibujar_grito_aviso`) por
  donde si se puede escapar.

Ademas, cada rafaga de glitch (y cada cambio de fase) puede dejar 1-2
**clones fantasma** (`_generar_clones`): copias que se dibujan con
exactamente la misma corrupcion que la real (`_dibujar_glitch`, llamado
tambien para cada clon) y disparan lanzas igual que ella, asi que no hay
ninguna diferencia visual fija que delate cual es la real.

Ademas es la unica nave del juego que "glitchea" visualmente, y ahora en
dos capas (`glitch_timer`/`glitch_cooldown`, mas frecuente y mas evidente
cuanto mas avanzada la fase — se "rompe" mas al recibir daño, y siempre se
fuerza una rafaga en cada cambio de fase):

- **El propio sprite** (`_dibujar_glitch`): franjas horizontales cortadas
  y desplazadas en X al azar (datamosh, alguna incluso invertida),
  aberracion cromatica (fantasmas rojo/cian corridos a los costados con
  mezcla aditiva vía `sprites.tint()` + `pygame.BLEND_RGBA_ADD`) y franjas
  de "ruido" blanco semitransparente.
- **El campo de batalla a su alrededor** (`_dibujar_glitch_campo`,
  llamado antes de dibujar el sprite): recorta con `screen.subsurface()`
  la region de pantalla ya dibujada (estrellas, balas, la nave...)
  alrededor del jefe y le aplica el mismo datamosh + aberracion cromatica,
  como si la corrupcion se filtrara fuera de la propia calavera en vez de
  quedarse contenida en su silueta.

### `modules/entities/titan_boss.py`
Clase `TitanBoss` (oleada 30, "Titan del Vacío"): jefe unico igual que
`FinalBoss`/`MegaBoss`, ya no un `WaveBoss` generico armado solo con
`BossDefinition`. Es un **pulpo mecanico** grande y corpulento (silueta
angular con hombros/pauldrones redondeados bien anchos a los costados —
no una cresta flaca — ver `_silueta_casco` en `tools/generate_sprites.py`
— y escalado `sprites.TITAN_DISPLAY_SCALE` mas grande que cualquier otro
jefe de oleada), sin el anillo de luces/cupula/piloto que comparten
saucer/dragon/anomaly. **No dispara ni un solo proyectil**: pelea
puramente cuerpo a cuerpo con tentaculos que son sprites articulados
(`titan_tentaculo_*.png`, varias copias rotadas/escaladas y encadenadas en
tiempo real via `_dibujar_tentaculo_sprite` — no lineas vectoriales) y se
queda en la mitad superior de la pantalla en vez de recorrerla entera
(`_update_movement` acota `target_y` a 90-160).

**Todos** los tentaculos —idle y de ataque/guardia— salen de anclajes
fijos sobre el propio cuerpo (hombros, flancos, vientre, cresta; ver las
constantes `_ANCLA_*` y `TitanBoss._ancla_mundo`, que ubica cada anclaje
en coordenadas de mundo a partir de una fraccion del rectangulo del
sprite ya escalado), nunca desde afuera de pantalla: se ve claramente que
son parte del pulpo. Los tentaculos "idle" (`_dibujar_tentaculos_idle`)
son 6, gruesos y largos (`grosor=2.1`, pocos segmentos grandes en vez de
muchos chicos para que se lean como miembros solidos), uno por cada
anclaje, cada uno con su propio angulo base y balanceo — la firma visual
de "pulpo vivo" intimidante incluso en reposo.

Tiene cinco piezas independientes, todas corriendo en paralelo:

- **Sismo** (`_iniciar_sismo`/`_actualizar_sismo`, estados
  aviso→golpe→retiro): un tentaculo baja desde la **cresta** del propio
  cuerpo (`_ANCLA_CRESTA`) hasta el punto marcado (la posicion de la nave
  al arrancar el aviso), tardando ~1.8s en estirarse del todo
  (`_sismo_dur_aviso = 110` frames) — lento y muy telegrafiado a proposito
  —, golpea una vez (aparece un `TentaculoImpacto` ahi mismo) y se retira
  despacio.
- **Brazo lateral** (`_iniciar_brazo`/`_actualizar_brazo`, mismos tres
  estados): un tentaculo sale del **hombro** izquierdo o derecho del
  propio cuerpo (al azar, `_ANCLA_HOMBRO_IZQ`/`_DER`) siguiendo la altura
  de la nave durante ~1.8s y despues lanza un golpe corto y decisivo mas
  alla de donde llego arrastrandose.
- **Emboscada** (`_iniciar_emboscada`/`_actualizar_emboscada`, mismos tres
  estados pero mucho mas cortos): una puñalada rapida desde el
  **vientre** (`_ANCLA_VIENTRE_CENTRO`) con bastante menos aviso que las
  otras dos — otro ritmo, para que los golpes no vengan siempre del mismo
  punto del cuerpo ni con el mismo tiempo de reaccion.
- **Enjambre** (`_iniciar_enjambre`/`_actualizar_enjambre`, mismos tres
  estados): el ataque "definitivo" — los **6 anclajes idle a la vez**
  (`_ANCLAS_IDLE`, los mismos puntos que se mecen solos en reposo) se
  estiran juntos hacia un blanco cada uno, repartidos en abanico parejo
  por casi todo el ancho de pantalla a la altura de la nave. Cooldown
  bien mas largo que el resto (`_iniciar_enjambre`: 360-440 frames /
  dificultad, contra 200-360 de los demas) y el aviso mas extendido de
  todos (130 frames) para poder leer los huecos entre un tentaculo y el
  siguiente antes de que golpeen los 6 juntos.
- **Guardia** (`_iniciar_guardia`/`_actualizar_guardia`,
  subida→activa→bajada): **cruza dos tentaculos, uno por hombro, en X
  delante del cuerpo** (`_guardia_puntas`) — como brazos cruzados
  bloqueando un golpe, no un unico tentaculo alzado — que **bloquean los
  disparos del jugador que caigan cerca de donde se cruzan**
  (`bloquea_disparo(x, y)`, prueba las dos zonas de `_guardia_zonas_bloqueo`;
  consultado desde `main.py` antes de aplicar cualquier golpe a un jefe —
  no afecta a los demas jefes porque se consulta con `hasattr`); las
  balas piercing lo atraviesan igual que todo, las demas se descartan ahi
  (parry) sin llegar a tocar el ojo.

`TentaculoImpacto` (mismo modulo): no es un disparo — aparece ya en el
lugar exacto donde el tentaculo golpea, en el instante en que golpea, dura
unos pocos frames y no viaja; comparte la interfaz de `WaveBossBullet`
(`x`/`y`/`radius`/`active`/`update`/`draw`) para poder ir directo a la
lista `boss_bullets` de `main.py` sin tocar nada ahi.

El ojo (`_dibujar_ojo`) sigue a la nave con la mirada en tiempo real: el
aro/iris mecanico viene horneado en el sprite, pero la pupila es 100%
dinamica y se desplaza cada frame hacia la nave, clampeada dentro del
zocalo (`sprites.TITAN_OJO_*_FRAC`).

### `modules/entities/dragon_boss.py`
Clase `DragonBoss` (oleada 20, "Dragon Espacial"): jefe unico igual que
`FinalBoss`/`TitanBoss`/`MegaBoss`, ya no un `WaveBoss` generico. Es un
**dragon de verdad** — craneo con dos cuernos, alas de murcielago bien
abiertas a los costados, brazos musculosos con garra que se separan bien
del torso (el codo llega hasta afuera del ancho del cuerpo, no un bulto
pegado que solo se nota por la punta de la garra) y piernas con garras y
una cola larga que se curva hacia un lado (ver `build_dragon_robot()` en
`tools/generate_sprites.py`, construido desde varios poligonos simples
unidos con `mask_from_shapes(polys=[...])` en vez de un unico contorno
espejado, la tecnica usada en el resto de los jefes) — con **dos ojos**
(cuencas horneadas vacias, pupilas 100% dinamicas en tiempo real via
`_dibujar_ojos`/`_dibujar_ojo`, mismo criterio que `TitanBoss`/`FinalBoss`
duplicado — ver `sprites.DRAGON_OJO_IZQ_X_FRAC`/`DRAGON_OJO_DER_X_FRAC`),
boca abierta con colmillos arriba y abajo, textura de escamas en el
pecho/torso y venas resaltadas en la membrana de cada ala. Los nombres
`DRAGON_ROBOT_*`/`build_dragon_robot()`/`get_dragon_robot_surface()` se
mantienen por compatibilidad aunque ya no hay nada robotico en el diseño
(mismo criterio que `BOSS_SPRITE_PREFIX` guardando `"saucer"` como
`"mothership"`).

El PNG final es **pixel art de verdad**, a pedido explicito -bloques de
color solidos y un contorno negro marcado, no una silueta suave escalada.
Toda la geometria se sigue autorando a la escala grande de siempre (mas
facil de dibujar a mano), y `build_dragon_robot()` la baja al final a una
grilla nativa chica (`DRAGON_PIXEL_W/H` = 80x75, ver `_dragon_pixelar`)
con la luminancia **posterizada en bandas planas** (`Image.BOX` para bajar
de escala + redondeo a un puñado de niveles de gris, no un degrade
continuo) y el contorno RECALCULADO en esa misma grilla chica (silueta
binaria menos su erosion, no el antialiasing del hi-res que se veria
borroso). `sprites.get_dragon_robot_surface` la escala de vuelta arriba
sin suavizar (`_compose_layers(..., pixelado=True)` → `_scaled_pixelado`,
`pygame.transform.scale` en vez de `smoothscale`, mismo criterio que las
insignias de power-up) para que los "pixeles" se vean como bloques solidos
de verdad.

`apertura` (0.0 a 1.0) sigue sin ser "un iris abriendose": es cuanto
**DAÑO/heridas** tiene encima, y anima cuadro a cuadro sobre un flipbook
real de 11 sprites (`DRAGON_ROBOT_FRAMES`, ver
`sprites.get_dragon_robot_surface()`) — 5 puntos de herida fijos
(`_DRAGON_DAÑOS` en `generate_sprites.py`, repartidos en punta de ala
derecha, cadera izquierda, pecho, punta de ala izquierda y mejilla
derecha, no simetricos a proposito) pasan de piel intacta a marcas de
quemadura solidas (un circulo relleno oscuro con borde naranja, dibujado
DESPUES de bajar a la grilla nativa -una grieta fina de un par de pixeles
de ancho se emborronaba/desaparecia al posterizar, asi que ahora son
manchas solidas, no lineas) cada una en su propio rango de `apertura`, asi
que cada cambio de fase lo deja notablemente **mas lastimado** que el
anterior en vez de solo cambiarle el color. El daño no se queda quieto una
vez horneado: cada herida **titila con brasas animadas** en tiempo real,
con una fase propia por punto para que no parpadeen todas sincronizadas
(`_dibujar_daños_dinamicos`, usa `sprites.DRAGON_DAÑOS_FRAC` — debe
coincidir con `_DRAGON_DAÑOS`), y ademas **escupe chispas de verdad** hacia
arriba con probabilidad proporcional a su severidad actual
(`_emitir_chispas_daño`, reutiliza `self.chispas`) — se ve un daño vivo, no
un dibujo estatico.

Ademas tiene una **garganta que resplandece 100% en tiempo real**
(`_dibujar_garganta`, nada horneado en el PNG): brasas tenues en reposo,
que se intensifican mientras carga el aliento de fuego y estallan
brillantes en el instante del disparo — el equivalente organico de las
luces de nave que otros jefes llevan horneadas/dinamicas por partes.

Cada fase es un modo de combate distinto (`_crear_ataque`), todo tematica
de fuego, nada de disparos genericos de nave:

- **Modo Acecho** (fase 1, apertura 0.0, casi intacto): dardos de fuego
  dirigidos y rapidos, se reposiciona seguido — la version agil.
- **Modo Envite** (fase 2, apertura 0.5, ya con heridas visibles): cono
  de fuego frontal denso mas dos zarpazos incendiarios a los costados.
- **Modo Furia** (fase 3, apertura 1.0, cubierto de heridas al rojo
  vivo): barrida circular pesada de fuego mas un **Aliento de Fuego**
  propio (`_iniciar_rayo`/`_actualizar_rayo`/`_dibujar_rayo`): telegrafiado
  con una linea de mira que sigue apuntando a la nave mientras carga en la
  garganta (~1s, ver `_dibujar_garganta`) y despues dispara un chorro
  ancho por esa trayectoria — el ataque mas lento y letal, reservado para
  el modo mas pesado. Es la misma mecanica de "rayo de sobrecarga" de
  jefes anteriores, reubicada en la boca en vez del ojo: un dragon
  respira fuego, no dispara laseres con la mirada.

Al cruzar cada umbral de vida (`_transformar`) se queda quieto
(`phase_transition`, ~1.7s) mientras `apertura` avanza hacia el objetivo
de la fase nueva y se ven los cuadros intermedios del flipbook en
pantalla junto con chispas y un destello pulsante — la transformacion en
si es la animacion de transicion (y de deterioro), no un simple flash de
color encima del mismo dibujo.

Al llegar a 0 de vida **no desaparece de golpe**: `take_damage` dispara
`_iniciar_muerte` en vez de poner `active = False` directo, y sigue con
`active = True` a proposito durante toda la secuencia (para que `main.py`
no lo recompense/remueva a mitad de camino):

- **`death_state = "riendo"`** (~1.3s): un ultimo gesto desafiante, con un
  rebote vertical rítmico (se lee como un rugido, no como ruido al azar)
  y los dos ojos puestos en estroboscopico blanco/rojo a toda velocidad
  (`_dibujar_ojo` corre mas rapido cuando `death_state == "riendo"`); la
  barra de vida se oculta, ya no aporta nada verla en 0%.
- **`death_state = "explotando"`** (`_iniciar_explosion`/
  `_actualizar_explosion`): recorta su PROPIO sprite (ya en el peor
  estado de daño) en una grilla de pedazos reales — misma tecnica de
  fragmentacion que `MegaBoss` (`subsurface().copy()` por pieza, cada una
  con su propia direccion de salida y giro) — que salen disparados hacia
  afuera girando y se van desvaneciendo (`set_alpha`); a diferencia de
  `MegaBoss` no implosiona de vuelta, esta vez muere de verdad. Al
  terminar recien pone `active = False`, momento en el que el bucle
  principal de `main.py` dispara la recompensa/remocion normal, igual que
  con cualquier otro jefe.

### `modules/core/boss_system.py`
- **BossDefinition**: datos fijos de un jefe de oleada (vida, velocidad,
  patrones, colores, `body_type` para elegir sprite, `rewards`).
- **BossReward**: un buff que el jefe reparte al morir.
- **BOSS_DEFINITIONS**: la lista de jefes, uno cada 10 oleadas si o si:
  `sentinel` oleada 10 (el unico que hoy se instancia como `WaveBoss`
  generico), `dragon` oleada 20 (se instancia como `DragonBoss`, ver
  `modules/entities/dragon_boss.py`), `titan` oleada 30 (se instancia como
  `TitanBoss`) y `anomalia` oleada 40 (`FINAL_BOSS_SPAWN_WAVE`, se
  instancia como `FinalBoss`), mas el mega-jefe unico de la oleada 50
  (`constants.MEGA_BOSS_SPAWN_WAVE`, ver `modules/entities/mega_boss.py`).
  Los 4 siguen guardando su `BossDefinition` (rewards, nombre) en
  `.definition` aunque ya no la usen para el sprite.
- **WaveBoss** / **WaveBossBullet**: instancia jugable de un jefe de oleada
  construida a partir de una `BossDefinition` (hoy solo Centinela la usa
  para su sprite/comportamiento; los demas son jefes unicos con clase
  propia). Mismo esquema de fases que `FinalBoss`. `WaveBossBullet`
  tambien la reutilizan `TitanBoss`, `DragonBoss` y `MegaBoss` en vez de
  definir una bala propia cada uno.

Ningun jefe (ni siquiera el mega-jefe) entrega puntaje directo al morir:
solo los power-ups de recompensa. El puntaje sigue viniendo de destruir
asteroides y naves alienigenas (ver `main.py` / `_recompensar_jefe` y
[Oleadas y dificultad](#oleadas-y-dificultad)).

### `modules/entities/mega_boss.py`
`MegaBoss`: el jefe unico de la oleada `MEGA_BOSS_SPAWN_WAVE` (50). A
diferencia de `WaveBoss`/`FinalBoss` no usa el molde "platillo con anillo
de luces" (silueta y sprites propios, ver
[Sistema de Sprites](#sistema-de-sprites)), es notablemente mas grande
(`self.width` = 300/230 segun fase, contra ~140-176 de los demas jefes) y
tiene su propia aura de amenaza — un pulso oscuro permanente detras del
casco que ningun otro jefe dibuja — para que se note de un vistazo que es
el jefe final y no otro mas. Tambien recibe `dificultad` en el
constructor: en DIFICIL se mueve y ataca mas rapido y aguanta mas vida
(igual que `WaveBoss`/`FinalBoss`, ver mas abajo).

El movimiento tiene animacion propia ligada a la velocidad REAL de cada
frame (`_mover`, ya no un `rotation`/`rot_speed` decorativo que no se
llegaba a dibujar en ningun lado): `bank_angle` banquea el casco hacia el
lado que se desplaza (rotando el sprite ya compuesto, `pygame.transform.
rotate`) y `motor_intensidad` estira una estela de destellos desde las
toberas (`_dibujar_estela_motor`) que crece con la velocidad real y se
apaga del todo cuando esta quieto — se siente maniobrando, no
"planeando" a velocidad constante. Tiene dos fases con ataques distintos:

- **Fase 1 "cruiser"** (acorazado estelar de casco escalonado — hombros
  anchos a la mitad, popa partida en dos semi-cascos con motor propio
  cada uno, espina dorsal elevada, torre de mando de dos niveles con
  radar, bahia de hangar y una hilera de cañones de punto a cada flanco
  ademas de las 2 torretas principales — silueta tipo "destructor
  estelar" mucho mas detallada que un simple casco en cuña, hasta el 50%
  de vida): patrones de bala `BROADSIDE` (andanada desde todo
  el casco), `MISSILES` (dirigidos a la nave) y `SPREAD`; lanza cada tanto
  2 `AlienShip` variante "fighter" retintadas gris metalico
  (`CAZA_ESCOLTA_COLOR`) como cazas de escolta propios; y ademas, en
  paralelo a esa rotacion de patrones, un **cañon railgun** independiente
  (`_iniciar_carga_railgun`/`_actualizar_railgun`): marca una linea de mira
  roja intermitente sobre la nave durante ~0.8s (aviso para esquivar) y
  despues dispara un unico proyectil pesado y muy rapido (radio 10,
  velocidad 11) por esa trayectoria. Ademas tiene luces de navegacion que
  parpadean de verdad (`_dibujar_luces_crucero`: blanca en la proa,
  rojo/verde en la popa, baliza ambar en el radar) y la largada de cazas
  tiene su propia animacion (`_dibujar_hangar`): la bahia de hangar
  destella y los cazas nuevos aparecen ahi (`_lanzar_cazas` les reubica
  x/y) en vez de materializarse en el borde de la pantalla.
- **Fase 2 "sphere"** (esfera de combate blindada con grilla de paneles,
  banda ecuatorial, plataforma hexagonal con el zocalo del cañon y
  cañones secundarios en el borde — silueta tipo "estacion de combate",
  desde el 50% de vida): sigue lanzando cazas y bala de relleno
  (`SPREAD`/`CIRCULAR`/`MINEFIELD` — minas estaticas repartidas por el
  area de juego), y suma dos ataques propios independientes de esa
  rotacion — **meteoritos**: suelta `Asteroid` comunes desde arriba
  (reutiliza toda su colision/puntaje ya existente) y **laser**: fija el
  corredor sobre la posicion de la nave, lo advierte ~1.2s (linea naranja
  pulsante) y despues dispara una rafaga densa de proyectiles por ese
  corredor durante otro medio segundo.

La transformacion entre fases (`_iniciar_fragmentacion`/
`_actualizar_fragmentos`) tampoco es un simple destello de color: recorta
el sprite ACTUAL del crucero en una grilla de pedazos (sprites reales, no
formas vectoriales) que explotan hacia afuera y despues implosionan de
vuelta al centro — recien cuando termina de implosionar aparece la
esfera, con un destello final (`reform_flash`). Mientras dura, ni el
sprite normal ni el destello generico de fase se dibujan: se ven los
pedazos.

`update(ship)` **no** devuelve una lista plana de balas como los demas
jefes: devuelve `{"bullets": [...], "asteroides": [...], "alien_ships":
[...]}`, porque tambien suelta meteoritos y naves. `main.py` distribuye
cada lista a `boss_bullets`/`asteroids`/`alien_ships` respectivamente (ver
el `isinstance(b, MegaBoss)` en el loop de jefes). Derrotarlo es la
**unica** forma de terminar la partida con "victoria" (ver
`_recompensar_jefe` en `main.py`); la Anomalia Final de la oleada 40 ya no
termina el juego, queda como un jefe intermedio mas.

Al derrotarlo, `_recompensar_jefe` llama a `_cinematica_victoria(boss)`
**antes** de `terminar_partida(True)`: un cutscene final en dos tiempos,
con su propio mini-bucle (pump de eventos/`clock.tick`/`flip` propios, no
un estado mas del bucle principal) —

- **Explosion** (~2.2s): recorta el sprite ACTUAL del mega-jefe
  (`sprites.get_mega_boss_surface`) en una grilla de 10x8 pedazos reales
  que salen disparados hacia afuera girando, con miles de destellos
  acumulados cuadro a cuadro (14-22 nuevos por frame) mas explosiones
  encadenadas y sacudida de camara.
- **Escape** (~3.7s): la nave del jugador -mas dos naves escolta que se
  le suman (sprite "scout" reciclado con otro tinte)- acelera
  disparandose hacia **arriba** (alejandose de donde quedo la explosion),
  dejando su propio **rastro de explosiones chicas** detras (una cada
  9-16 frames, en la posicion actual de cada nave — como ya no se mueven,
  quedan marcando el camino recorrido) entre estelas de hiperespacio
  (lineas que nacen arriba y bajan, como el fondo corriendo hacia atras).
  La "camara" (`camera_y`, un desplazamiento vertical que se le resta a
  todo lo que esta en el mundo — nave, escoltas, pedazos, estelas,
  explosiones — al dibujarlos) persigue a la nave con un suavizado fuerte
  (`camera_y += (objetivo - camera_y) * 0.22`) MAS un clamp duro
  (`MAX_LAG_CAM = 130`) que nunca deja que la nave quede a mas de esos
  130px del ancla en pantalla — con una ganancia mas debil (0.06, sin
  clamp) el retraso en regimen permanente crecia sin limite junto con la
  velocidad de la nave y terminaba saliendose de cuadro por arriba.

Termina con un fundido a blanco en los ultimos ~30 frames del escape, y
recien ahi se llama a `terminar_partida(True)`, que dispara la pantalla de
victoria normal.

### `modules/systems/input.py`
Integracion con MediaPipe para deteccion de mano.

- `init_hand_landmarker(model_path)`: crea el detector en modo VIDEO.
- `process_camera_frame(detector, frame, timestamp_ms)`: detecta la mano,
  o devuelve `None` si el frame-skip descarta ese frame.
- `is_fist(hand_lm)`: puño cerrado = punta de los 4 dedos por debajo de su
  propia articulacion PIP.
- `find_hand_position(hand_lm, game_w, game_h, sensibilidad=1.0)`: posicion
  de la muñeca mapeada al area de juego; `sensibilidad` amplifica (>1.0) o
  atenua (<1.0) el desplazamiento respecto del centro (ver
  [Menu, Dificultad y Ajustes](#menu-dificultad-y-ajustes)).

### `modules/systems/menu.py`
Ver la seccion [Menu, Dificultad y Ajustes](#menu-dificultad-y-ajustes).

### `modules/systems/ui.py`
HUD y pantallas del juego en si (no del menu): `draw_countdown`,
`draw_hud` (con las clases `ModernHUD`, `HealthBar`), `draw_camera_preview`,
`draw_boss_rewards`, y `draw_game_over`/`draw_victory_screen` con las
estadisticas de la partida (ver [Estadisticas de Partida](#estadisticas-de-partida)).

`draw_buff_hud` (clases `BuffChip`/`BuffHUD`) y `draw_ship_status_bar` se
dibujan en los margenes fuera del area de juego (por eso reciben `screen`,
no `game_surface`, y se llaman en `main.py` recien despues de
`draw_viewport_frame`, o cualquier cosa que dibujen quedaria tapada por el
`screen.fill` posterior). Estilo "panel de nave":

- **`BuffChip`**: un panel vertical por buff activo (insignia con icono
  arriba, barra de carga vertical, etiqueta abajo), alternado entre el
  margen izquierdo y el derecho por `BuffHUD.draw`. La barra se vacia de
  arriba hacia abajo con `timer / max_timer`; los buffs "eternos"
  (permanentes o de clase, ver `Ship._extender_buff`) se muestran siempre
  a full con un brillo lento en vez de vaciarse.
- **`draw_ship_status_bar`**: consola de "CASCO" en el margen inferior, un
  segmento iluminado por vida restante (no una barra continua, mas legible
  con pocas vidas) — la ultima vida parpadea como alarma. Es aparte de la
  barra de vida chica que ya tiene el panel de SCORE (`ModernHUD`).

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
Se verifica que las puntas de los 4 dedos (8, 12, 16, 20) esten por debajo
de sus respectivas articulaciones PIP (6, 10, 14, 18) — en coordenadas de
imagen "y" crece hacia abajo, asi que un dedo curvado hacia la palma tiene
la punta con mayor "y" que su PIP. Si se cumple para los 4, la mano esta
cerrada. `Ship.trigger_fist_burst(fist_now)` compara
ese estado contra el del frame anterior (`hand_was_fist`) y solo dispara
`FIST_BURST_SHOTS` (1) disparo en el instante en que la mano pasa de
abierta a cerrada; mantener el puño cerrado no sigue disparando, y hace
falta abrir la mano y volver a cerrarla para el siguiente disparo. El
disparo pendiente se efectiviza en `Ship.update_burst_fire()`, llamado una
vez por frame, en cuanto el `shoot_cooldown` lo permite.

### Por que MediaPipe Tasks en vez de MediaPipe Solutions
`solutions` esta deprecado desde las versiones 0.10+; `tasks` es la API
vigente, y `detect_for_video()` con timestamps reduce la latencia
perceptible frente a procesar cada frame como imagen suelta.

---

## Sistema de Juego

### Nave del jugador
Siempre clase Scout (la seleccion de clase de nave se elimino; `ship_type`
sigue existiendo como parametro pero solo se usa "scout"). Sprite propio,
glow, animacion de llama del motor, parpadeo de invencibilidad tras un
golpe, barra de vida propia y las auras visuales de cada buff activo
(escudo, perforante, iman, campo electrico). Los sprites de
tank/interceptor/bomber que quedaron sin uso se reciclaron como la nave
bonus infrecuente (ver `BONUS_SHIP_VARIANTS` en `modules/entities/enemy.py`
y la seccion de abajo).

### Oleadas y dificultad
La oleada YA NO sube por tiempo: sube al destruir una cuota minima de
objetivos (asteroides + naves alienigenas, no cuentan los jefes).
`constants.cuota_de_oleada(N)`: las oleadas 1 a 30
(`WAVE_OBJETIVOS_HASTA_OLEADA`) exigen 10 destruidos
(`WAVE_OBJETIVOS_INICIAL`) y de la 31 en adelante 15
(`WAVE_OBJETIVOS_AVANZADO`). Esto reemplaza el viejo
avance por tiempo para que el juego no "salte" oleadas sin que el jugador
haya hecho nada; el HUD muestra el progreso (`X/Y`) con una barrita, o
"¡JEFE!" mientras hay un jefe en pantalla (ver `ModernHUD` en
`modules/systems/ui.py`).

Mas asteroides y naves alien por oleada segun `dificultad` (multiplicador
elegido al empezar mas un incremento fijo cada jefe derrotado). Naves
alien desde la oleada 2 (con una nave bonus infrecuente reciclando los
sprites de tank/interceptor/bomber desde la oleada `BONUS_SHIP_MIN_WAVE`);
jefe cada 10 oleadas si o si (10, 20, 30, 40) y el mega-jefe unico en la
oleada `MEGA_BOSS_SPAWN_WAVE` (50, ver `modules/entities/mega_boss.py`).
Mientras hay un jefe activo no aparecen asteroides/naves nuevas
(`len(bosses) == 0` en las condiciones de spawn), asi que en la practica
la oleada se "congela" en el numero del jefe hasta derrotarlo.

Las naves bonus (`modules/entities/enemy.py`) ya no mueren de un solo
golpe: cada variante tiene su propio `hp` (`BONUS_SHIP_VARIANTS`) mostrado
como una fila de pips sobre la nave, y cada una dispara distinto
(`AlienShip._crear_disparo`) — `tank` una trebolada de tres disparos
amplios, `interceptor` un solo tiro rapido apuntado a la nave,
`bomber` un proyectil pesado y lento. Sueltan menos power-ups que antes al
morir (`BONUS_SHIP_POWERUP_COUNT`, bajado para que no se sienta gratuito)
y ya no hay doble recompensa por el mismo kill (antes `_soltar_recompensa_bonus`
se llamaba tanto en el golpe letal como, al frame siguiente, al notar la
nave inactiva — ver el historial de `main.py`; ahora la recompensa se
otorga una sola vez, en el golpe que de verdad la destruye vía
`AlienShip.take_damage`, y una nave que sale volando de pantalla sin que
la maten no suelta nada). De vez en cuando (`BONUS_SHIP_MINIBOSS_CHANCE`)
la bonus que le toca aparecer se activa como **mini-jefe**
(`AlienShip.is_miniboss`): mas grande (`MINIBOSS_SIZE_MULT`), mucho mas
resistente (`MINIBOSS_HP_MULT`) y ademas de su disparo normal larga salvas
de `AlienMissile` — misiles con homing suave (el giro esta acotado,
moverse de verdad todavia sirve para esquivarlos) y estela de propulsion —
a cambio de una recompensa proporcionalmente mayor
(`BONUS_SHIP_MINIBOSS_POWERUP_MULT`/`_SCORE_MULT`).

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
5. Se revisa si es puño (4 dedos cerrados); si la mano se acaba de cerrar
   (no estaba cerrada en el frame anterior) se dispara un unico disparo, en
   cuanto el cooldown de disparo lo permite. Mantener el puño cerrado no
   dispara de nuevo hasta abrir la mano y volver a cerrarla.

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
- **4 naves** (scout/tank/interceptor/bomber) x 3 capas. Solo `scout` es
  jugable (la seleccion de clase de nave se elimino); `tank`/`interceptor`/
  `bomber` se reciclan como la nave bonus infrecuente de
  `modules/entities/enemy.py` (ver `BONUS_SHIP_VARIANTS`).
- **14 asteroides**, un PNG cada uno, con "familias" de forma distintas
  (redonda/alargada/irregular/fragmento/afilada). Cada crater tiene sombra
  interior + un labio con brillo (no un circulo de relleno plano), mas
  grano de roca real -`grain_noise()`, ruido multi-octava- y motas
  minerales brillantes ademas del moteado oscuro y las grietas que ya
  tenia, para que la superficie se lea rugosa y no lisa.
- **3 enemigos comunes** (fighter/drone/gunner) x 3 capas.
- **4 siluetas de jefe** via `build_boss(kind=...)`: `saucer` (platillo
  clasico, se guarda como `mothership_*.png` por compatibilidad — lo usa
  el jefe Centinela Corrupto) comparte la posicion del anillo de nodos y
  la plataforma de la cupula que `boss.py`/`boss_system.py` dibujan encima
  en tiempo real (cupula animada, piloto, luces parpadeantes); a
  diferencia de los otros tres SI usaba la elipse lisa por defecto sin
  detalle propio (`_detalle_extra_casco` no tenia rama para "saucer") —
  ahora tiene costuras radiales entre los anillos de blindaje, dos
  rejillas de ventilacion con lamas, una franja de peligro amarillo/negro
  y un par de "grietas" de corrupcion digital (desgarros con franja
  cromatica cyan/magenta, no huesos rotos como Anomaly) para que se lea
  como un sentinel fallando y no un disco liso con puntos. `dragon`
  (casco alargado con colmillos y ojo luminoso) sigue existiendo en
  `generate_sprites.py` pero es legado/huerfano: `DragonBoss` (jefe de la
  oleada 20) ya no usa `build_boss(kind="dragon")`, dibuja su propio
  robot-nave transformable con `build_dragon_robot()`/
  `get_dragon_robot_surface()` (ver mas abajo). `titan` y `anomaly` son
  las dos excepciones que **saltan** el anillo/cupula/piloto compartido
  (`build_boss()` los excluye explicitamente): `titan` es una cresta
  angular blindada (caja `TITAN_CASCO_RX/RY`, mas grande que la de los
  demas) con un ojo-camara mecanico grande grabado (aro/iris fijo, sin
  pupila — ver `TITAN_OJO_*`) y anclajes triangulares afilados en el
  borde inferior (base de los tentaculos); `anomaly` es una **calavera
  glicheada morada** (caja `ANOMALY_CASCO_RX/RY`, silueta propia de 14
  puntos — craneo redondeado, sienes anchas, pomulos/quijada quebrados en
  punta — ver `_silueta_casco`) con **dos cuencas vacias** grabadas (sin
  pupila, ver `ANOMALY_OJO_*`), cavidad nasal, marcas de dientes en la
  quijada y esquirlas de cristal en algunas puntas afiladas del craneo
  (`_detalle_extra_casco`), sin remaches mecanicos (`_remaches_casco`
  devuelve un no-op para este kind: es hueso fracturado, no chapa
  blindada). Las pupilas de ambos son 100% dinamicas, dibujadas en tiempo
  real por `boss.py`/`titan_boss.py` encima de esas cuencas fijas. Los
  tentaculos de Titan en si no son parte de este PNG: son sprites propios
  (`titan_tentaculo_*.png`,
  ver `build_titan_tentaculo()`) encadenados y rotados en tiempo real, ver
  `modules/entities/titan_boss.py`.
- **11 tipos de power-up**: insignia pixel-art (marco biselado caqui/negro
  comun, se genera a resolucion nativa baja sin antialiasing y se escala
  sin suavizar en tiempo real, ver `sprites._scaled_pixelado`) con un
  ICONO y silueta propios por tipo (corazon, escudo, pistola, espada,
  iman, rayo... ver `_POWERUP_ICONOS` en `tools/generate_sprites.py`) mas
  una etiqueta de texto debajo para que se entienda de un vistazo que hace
  cada uno.
- **2 sprites del mega-jefe** (`mega_cruiser.png`, `mega_sphere.png`,
  `build_mega_cruiser`/`build_mega_sphere`): a diferencia de todo lo
  anterior **no son tintables**, son colores finales ya horneados en el
  PNG (es un jefe unico, no una nave de skin variable) y tienen silueta
  propia en vez de reusar el molde ring+cupula de `build_boss`. Son
  siluetas originales inspiradas en los arquetipos clasicos de "cuña
  militar" y "estacion esferica con cañon" (no calcan ningun diseño
  existente, ni usan sus nombres): el crucero es un casco en cuña con proa
  afilada, nervadura central, densa grilla de paneles, torre de mando
  escalonada con dos platos sensores y 3 motores con resplandor en la popa
  recta; la esfera tiene grilla de paneles tipo "gofre" en toda la
  superficie, banda ecuatorial con lineas transversales y una plataforma
  hexagonal elevada alrededor del zocalo hundido del cañon (el nucleo
  brillante que carga/dispara se dibuja en tiempo real en `mega_boss.py`,
  encima de ese zocalo).

### Carga y cache (`modules/systems/sprites.py`)
`load_raw` cachea cada PNG (devuelve `None` si falta); `get_ship_surface`,
`get_enemy_surface`, `get_asteroid_surface`, `get_boss_surface` y
`get_powerup_surface` componen+tiñen+escalan y cachean el resultado;
`get_mega_boss_surface(phase, w, h)` hace lo mismo para el mega-jefe pero
sin tiñe (ver arriba); `get_rotated` cachea rotaciones en pasos de 6
grados. Los colores de cache se cuantizan a multiplos de 8 para no generar
cientos de superficies al arrastrar un selector. Si falta
`assets/sprites/` entero, todas las funciones devuelven `None` y cada
entidad dibuja su version vectorial de respaldo: el juego nunca se cae por
un PNG faltante.

Regenerar todo: `python tools/generate_sprites.py`.

---

## Sistema de Audio

Los WAV se sintetizan con NumPy (ondas seno/cuadrada/sierra + ruido
blanco) y se guardan con el modulo estandar `wave`, sin libreria de audio
externa (`tools/generate_audio.py`). Produce 7 efectos
(`assets/audio/sfx/*.wav`: disparo, explosion, impacto, powerup, boton,
alerta_jefe, victoria) y 8 pistas de musica en loop
(`assets/audio/music/*.wav`: menu, juego, muerte, mas un tema propio por
jefe).

`modules/systems/audio.py` sigue la misma filosofia que `sprites.py`: si
`pygame.mixer` no puede inicializarse o faltan los WAV, todas las
funciones fallan en silencio.

### Musica por jefe
Cada jefe tiene su propio tema (`generar_musica_jefe_*` en
`tools/generate_audio.py`) en vez de que siga sonando `musica_juego`
durante toda la pelea: `main.py` llama a `audio.reproducir_musica(f"jefe_{boss_def.boss_id}")`
(o `"jefe_mega"` para el mega-jefe) justo al spawnearlo, junto al
`sonido_alerta_jefe()` de siempre, y vuelve a `"juego"` apenas
`bosses` queda vacio (derrota) — salvo que la partida ya haya terminado
(`game_over`), para no pisar el tema de derrota ni la cinematica de
victoria del mega-jefe. Las cinco pistas comparten el mismo esqueleto
ritmico que `generar_musica_juego` (bajo de 8 notas x 4 slots + capa
melodica de 32 notas x 1 slot + percusion de 32 pasos x 1 slot, todos con
la misma duracion total para que el loop no corte a mitad de compas) pero
cada una varia tempo/timbre/acordes/percusion segun el caracter del jefe:

- **Centinela Corrupto** (oleada 10): mecanico con corrupcion digital —
  el lead se corta a silencio al azar como interferencia, mas una capa de
  estatica de fondo muy tenue.
- **Dragon Espacial** (oleada 20): militar y contundente — bajo pesado en
  sierra y acordes en bloque tipo "stab" marcando el compas como una
  fanfarria de guerra.
- **Titan del Vacio** (oleada 30): lento y pesadisimo — el tempo mas
  lento de todos (`slot = 0.5`, el doble de largo que el resto), drone
  grave sostenido, golpes de percusion muy espaciados (pisadas/latigazos)
  y un lamento agudo disonante de fondo.
- **La Anomalia Final** (oleada 40): disonante e inestable — voces con
  una leve deriva de tono que "tiemblan" en vez de sonar limpias, notas
  del lead que se cortan al azar y bloques cortos de silencio al azar en
  toda la mezcla, imitando el glitch visual del propio jefe.
- **Mega-jefe** (oleada 50): el tema mas grande e intenso — el tempo mas
  rapido (`slot = 0.16`) y la percusion mas densa del juego, para la
  batalla final.

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
- **`"control_mode"`**: se entra al elegir JUGAR. Botones CAMARA (MANO) /
  MANDO (JOYSTICK). El boton MANDO se deshabilita (`MenuButton.enabled =
  False`) si `pygame.joystick.get_count() == 0`, chequeado en cada
  `update()` mientras esta pantalla esta activa, asi que se habilita solo
  con conectar el control sin reiniciar el juego. La eleccion queda en
  `self.modo_control` ("camara"/"mando").
- **`"dificultad"`**: se entra tras elegir el modo de control. Botones
  FACIL / NORMAL / DIFICIL (multiplicadores en `constants.DIFICULTADES`,
  ver mas abajo). Elegir uno arranca la partida devolviendo
  `"START_GAME:<nave>:<skin>:<dificultad>:<modo_control>"`, que `main.py`
  interpreta para activar la camara o el mando (segun corresponda) y
  llamar a `reset_game()`.
- **`"settings"`**: sliders de volumen de musica y efectos
  (`modules/systems/audio.py`), slider de sensibilidad de mano (0.5x-2.0x),
  y botones de silencio, pantalla completa y camara. Estos ultimos dos
  devuelven las señales `"TOGGLE_FULLSCREEN"` / `"CHANGE_CAMERA"`, que
  `main.py` resuelve recreando la ventana o reabriendo `cv2.VideoCapture`
  con el indice nuevo (solo si la camara ya esta activa; ver mas abajo).
  Todo se persiste al toque via `modules/settings.py`.

### Modo Mando (Joystick)
`main.py` no abre la camara web ni carga el modelo de MediaPipe hasta que
hace falta: `cap` y `hand_detector` arrancan en `None` y solo se crean
dentro de `activar_modo_camara()`, llamada al procesar un `START_GAME` con
`modo_control == "camara"`. Si se elige `"mando"` se llama a
`activar_modo_mando()` en su lugar, que libera `cap` si ya estaba abierta
(de una partida anterior en camara, dentro de la misma sesion) y busca un
joystick con `pygame.joystick.get_count()`/`Joystick(0)` — la camara queda
apagada mientras se juega en este modo.

Con el mando activo, cada frame el stick izquierdo (ejes 0/1, con zona
muerta `GAMEPAD_DEADZONE`) desplaza `ship.target_x`/`target_y` a razon de
`GAMEPAD_MOVE_SPEED` px por frame (a diferencia de la mano, que fija una
posicion absoluta, el stick empuja la posicion objetivo, como un joystick
de doble palanca). Cualquier boton del mando (evento `JOYBUTTONDOWN`)
dispara un unico tiro llamando a `ship.queue_shot()` — el mismo metodo que
usa el cierre de puño en camara, asi que respeta igual el `shoot_cooldown`
y no permite fuego automatico manteniendo el boton apretado (los eventos
de pygame solo laten en el instante de presionar, no mientras se mantiene).

> Nota: la version anterior del menu tenia una pantalla de "PERSONALIZAR"
> para elegir nave/color con un selector HSV (`ColorPicker`, `ShipCard`,
> `SkinCard`). Se removio a pedido (junto con las clases correspondientes,
> que quedaban sin usar) y en su lugar esta la pantalla de Ajustes.

### Dificultad
```python
DIFICULTADES = {"facil": 0.75, "normal": 1.0, "dificil": 1.8}
```
El multiplicador elegido es el valor inicial de la variable `dificultad`
en `main.py`, que ademas sube +0.2 cada vez que se derrota un jefe de
oleada. Afecta la velocidad de aparicion y la velocidad de asteroides y
naves alien (mas alto = mas dificil), y tambien a los jefes: `WaveBoss`,
`FinalBoss` y `MegaBoss` reciben `dificultad` en el constructor y escalan
su velocidad de movimiento y de disparo en proporcion directa (`shoot_rate
= base / dificultad`, mas bajo = dispara mas seguido) y su vida maxima con
`1.0 + (dificultad - 1.0) * 0.5` (mas amortiguado, para no volverlos
esponjas de balas). En NORMAL (1.0) da exactamente los valores base de
siempre; en DIFICIL pegan y se mueven bastante mas rapido y aguantan mas;
en FACIL, menos.

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
