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
- Jefes en las oleadas 10, 20, 30 y 40, y el Coloso en la oleada 50.
- Despues del Coloso viene la fase bonus de los gatos o, a veces (un brazo de
  zombi rompe la cinematica), la ruta de Halloween: Rey Calabaza, Bruja Neon y La Parca.

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
