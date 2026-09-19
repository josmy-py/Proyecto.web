# Nave vs Asteroides - Control por Mano

Juego de nave espacial contra asteroides y naves alienigenas controlado por gestos de mano usando la camara web y MediaPipe.

## Requisitos

- Python 3.10+
- Camara web conectada

## Instalacion

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
python main.py
```

## Controles

| Gesto | Accion |
|-------|--------|
| Mueve la mano | Mueve la nave |
| Cierra el puño (fist) | Dispara rafaga de 3 balas |
| ESC | Salir |
| R (en Game Over) | Reiniciar |

## Estructura del Proyecto

```
Proyecto/
├── main.py                       # Punto de entrada / bucle principal
├── requirements.txt              # Dependencias
├── README.md                     # Este archivo
├── DOCUMENTACION.md              # Documentacion tecnica detallada
├── custom_skins.json             # (se crea solo) colores personalizados guardados
├── models/
│   └── hand_landmarker.task      # Modelo MediaPipe para deteccion de mano
├── assets/
│   └── sprites/                  # Graficos del juego (PNG generados)
│       ├── ships/                # 4 naves x 3 capas (casco, alas, detalle)
│       ├── asteroids/            # 6 variantes de roca
│       └── enemies/              # 3 naves enemigas x 3 capas
├── tools/
│   ├── generate_sprites.py       # Genera los PNG de assets/sprites
│   └── preview_sprites.py        # Hoja de contacto para revisarlos
└── modules/
    ├── constants.py              # Constantes globales (colores, dimensiones, indices)
    ├── skins.py                  # Aspectos, color personalizado y persistencia
    ├── entities/
    │   ├── ship.py               # Nave del jugador (clases, buffs, sprite)
    │   ├── bullet.py             # Balas del jugador
    │   ├── asteroid.py           # Asteroides, particulas y explosiones
    │   ├── enemy.py              # Naves enemigas y sus balas
    │   ├── powerup.py            # Power-ups y tipos de buff
    │   └── boss.py               # Jefe final (version antigua, sin uso)
    ├── core/
    │   └── boss_system.py        # Definiciones y logica de jefes por oleada
    └── systems/
        ├── sprites.py            # Carga, tintado y cache de sprites
        ├── menu.py               # Menu, seleccion de nave y selector de color
        ├── ui.py                 # HUD, barras de vida y pantallas
        └── input.py              # Deteccion de mano con MediaPipe
```

## Sprites

Los graficos son PNG generados de forma procedural y viven en `assets/sprites/`.
Cada nave y cada enemigo se guarda en **tres capas**:

| Capa       | Contenido                        | Se tinta |
|------------|----------------------------------|----------|
| `_body`    | Casco, en escala de grises       | Si, con el color de casco |
| `_wing`    | Alas y aletas, escala de grises  | Si, con el color de alas |
| `_detail`  | Cabina, toberas, luces, contorno | No |

Al multiplicar una capa gris por un color se obtiene esa pieza pintada de ese
color conservando el sombreado. Por eso **cualquier** color elegido en el menu
funciona sin necesidad de tener un PNG por combinacion.

Para regenerar o modificar los graficos:

```bash
pip install pillow numpy
python tools/generate_sprites.py     # reescribe assets/sprites/
python tools/preview_sprites.py      # genera una hoja de contacto para revisarlos
```

Si la carpeta `assets/` no existe, el juego sigue funcionando: cada entidad
dibuja su version vectorial de respaldo.

## Personalizacion de la nave

En el menu (boton INICIAR JUEGO) se elige clase de nave y aspecto:

- **4 clases**: Scout, Tanque, Interceptor y Bombardero, cada una con estadisticas
  y una ventaja de clase distinta.
- **4 aspectos predefinidos** por clase, mas el aspecto **Personalizado**.
- En Personalizado se abre un selector HSV con barras de **tono, saturacion y
  brillo** (las tres se arrastran) y 12 colores rapidos.
- El color se aplica **en vivo**: las tarjetas y la vista previa grande cambian
  mientras se mueve la barra.
- Al confirmar, el color se guarda en `custom_skins.json` y se recupera la
  proxima vez que se abre el juego.

Lo elegido se traslada a la partida: la nave usa el mismo sprite tintado, la
llama del motor y las balas heredan el color del aspecto.

## Caracteristicas

- **Pantalla completa** a 1280x720
- **Preview de camara** en esquina superior derecha
- **Deteccion de mano** con MediaPipe Hand Landmarker (sin colores)
- **Rafaga de 3 disparos** cada vez que cierras el puño
- **Sistema de power-ups**: cada 5 asteroides destruidos obtienes un buff aleatorio
- **Naves alienigenas** que aparecen a partir de la oleada 2 y disparan al jugador
- **Buffs aleatorios** al destruir asteroides y naves alienigenas:

| Buff | Efecto |
|------|--------|
| +1 vida | Aumenta vidas (max 5) |
| RAPIDO | Disparo rapido por 10 segundos |
| TRIPLE | Rafaga de 4 balas por 8 segundos |

- **Baja latencia** usando detect_for_video() con timestamps
- **Oleadas progresivas** de asteroides con dificultad creciente
- **Sistema de puntuacion** y Game Over con reinicio
- **Particulas de explosion** y efectos visuales
- **Sprites propios** para naves, asteroides y enemigos, con tintado por color
- **Personalizacion de la nave** con selector de color y guardado en disco

## Como funciona

1. MediaPipe detecta tu mano a traves de la camara
2. La muñeca (wrist) controla la posicion de la nave
3. Al cerrar el puño, la nave dispara una rafaga de 3 balas
4. Los asteroides aparecen en oleadas progresivas
5. Cada 5 asteroides destruidos aparece un power-up aleatorio
6. A partir de la oleada 2, naves alienigenas aparecen y disparan
7. Destruir naves alienigenas da un buff aleatorio
8. Cada asteroide/power-up destruido otorga puntos
9. Si un asteroide o bala alienigena colisiona con la nave, pierdes una vida
10. Si las vidas llegan a 0, Game Over
11. Presiona R para reiniciar tras Game Over