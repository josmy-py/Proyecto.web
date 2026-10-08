# Nave vs Asteroides

Juego de naves en pixel art neon hecho con Python y pygame-ce. Se juega con
la mano frente a la camara web (MediaPipe) o con un mando.

## Requisitos

- Python 3.10+
- Camara web (modo Camara) o un mando conectado (modo Mando)

## Instalacion y ejecucion

```bash
pip install -r requirements.txt
python main.py
```

En Windows tambien se puede abrir con doble clic en `run.bat`.

## Controles

| Modo | Mover | Disparar | Pausa |
|------|-------|----------|-------|
| Camara | Mueve la mano | Cierra el puño | P |
| Mando | Palanca izquierda | Cualquier boton | START |

ESC sale del juego.

## Como se juega

- Antes de empezar elegis la nave: Explorador, Interceptor, Acorazado o
  Bombardero, cada una con su velocidad, cadencia y vidas.
- Las mejoras salen solo de las **cartas de mejora**: una al empezar, otra
  cada 5 oleadas, despues de cada jefe y al destruir una nave bonus. Cada
  carta ofrece tres opciones (potencia, cadencia, turbo, escudo, triple
  cañon, dron escolta, el Zorrito Espacial, etc.).
- Cartas con habilidades: Misiles (salen solos y persiguen al enemigo), Critico
  (balas doradas que pegan triple a los jefes), Nova (una onda borra las balas
  que se acercan), Orbita (esferas que giran alrededor de la nave), Recolector
  (una vida cada tantas bajas) y Fenix (renaces una vez al caer), ver
  modules/systems/habilidades.py.
- Jefes en las oleadas 10, 20, 30 y 40, y el Coloso en la oleada 50.
- "Intentar de Nuevo" sigue desde donde perdiste (la misma oleada o el mismo
  jefe), con la vida llena y todas tus mejoras. Si perdiste contra un jefe,
  antes de volver a pelear eliges una carta de mejora.
- Cada jefe tiene una cinematica al llegar (alerta, su entrada y su frase) y
  otra al caer (sus ultimas palabras y su pagina del grimorio tachada), ver
  modules/entities/cine_jefes.py. Enter, Espacio, click o un boton del mando
  las adelantan.
- Despues del Coloso sale al azar una de las tres rutas bonus, nunca la misma
  que en la partida anterior: la de los gatos, la de Halloween (un brazo de
  zombi rompe la cinematica): Rey Calabaza, Bruja Neon y La Parca.
  A mitad de su pelea, la Bruja Neon se toma una pocion y se vuelve gigante:
  ataca con los brazos (pociones, manotazos y barridos).
- O la hackean y sale la ruta cyberpunk: Netrunner Fantasma, Tarantula-9 y
  Kaiser Cromado, cada uno con su cinematica de entrada. Al final la nave
  viaja a la Luna, Lucy baja y mira la Tierra, y la victoria sale al costado.
  Para que en ese final suene una cancion propia, deja el archivo (.mp3, .ogg
  o .wav) en assets/audio/music con "stay at your house" o "edgerunners" en
  el nombre; si no hay ninguno suena el tema generado (musica_luna).
- Si perdes dos veces seguidas aparece una calavera en "Intentar de Nuevo": al
  elegirlo, la Parca te lleva a su dimension para un duelo a muerte. Si te
  gana, conquista la galaxia.

## Estructura

```
main.py                     bucle principal
modules/constants.py        constantes globales
modules/progress.py         record y progreso (progreso.json)
modules/settings.py         ajustes (ajustes.json)
modules/skins.py            colores de las naves
modules/core/boss_system.py jefes por oleada
modules/entities/           nave, enemigos, jefes, dron, mascota, tripulante
modules/systems/            menu, HUD, cartas de mejora, estilo neon, sprites, audio, entrada
assets/sprites/             PNG de naves, enemigos y jefes (los asteroides se dibujan por codigo)
assets/audio/               musica y efectos
models/hand_landmarker.task modelo de MediaPipe para la mano
tools/                      generadores de sprites y audio
```

## Regenerar recursos

```bash
pip install pillow numpy
python tools/generate_pixel_sprites.py  # pixel art de naves, enemigos y jefes
python tools/generate_audio.py          # efectos y musica
```
