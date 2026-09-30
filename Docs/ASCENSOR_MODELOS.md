# Ascensor "de verdad": piezas a modelar — 27 de septiembre de 2026

Idea: una **estructura fija** anclada al piso y una **cabina** que sube por dentro con el personaje.
Detalles elegidos: **reja/puerta** que se cierra antes de salir y se abre al llegar, y **sacudón + sonido**
al arrancar y frenar. Sin cables ni contrapeso por ahora.

Formato: un GLB por pieza en `3D assets/GLBs`, escala real en metros, Z hacia arriba.
Cada pieza con su **pivote** donde se indica. El **frente** (por donde se entra) mira a **+X**.
No hace falta colisión: la agrego yo.

## 1. Estructura fija — `ascensorHueco.glb`

| Medida | Valor |
| --- | --- |
| Planta exterior | 2,4 × 2,4 m (como la jaula actual) |
| Hueco interior libre | al menos 1,7 × 1,7 m |
| Alto total | unos 5,2 m (2 m de recorrido + 2,5 m de cabina + 0,7 m para polea/máquina arriba) |
| Pivote | abajo al centro, al nivel del piso (z = 0) |

- **Sin travesaño abajo en el frente (+X)**: el personaje entra caminando. En los otros lados sí puede haber.
- Puede llevar guías o rieles verticales por dentro, donde "corre" la cabina.

## 2. Cabina — `ascensorCabina.glb`

| Medida | Valor |
| --- | --- |
| Planta exterior | como máximo 1,6 × 1,6 m (tiene que entrar en el hueco) |
| Alto interior | 2,3 m (el personaje mide 1,70 m) |
| Grosor del piso | hasta 15 cm |
| Pivote | centro de la **cara de arriba del piso** (donde se paran los pies) |

- Piso, 4 parantes en las esquinas y techo. Los lados pueden ser abiertos, con barandas o con vidrio.
- **El techo como objeto separado** dentro del GLB (nombre `Techo`): la cámara es isométrica desde
  arriba y el techo taparía al personaje. Lo voy a hacer semitransparente mientras viajás.

## 3. Reja o puerta — `ascensorReja.glb`

- Va en el frente de la cabina (+X). Hueco de paso: 1,2 m de ancho × 2,1 m de alto.
- Elegí un tipo:
  - **Dos hojas corredizas** hacia los costados: exportá **una sola hoja** (0,6 × 2,1 m) y yo la espejo.
    Pivote: el borde que queda en el centro cuando está cerrada, abajo.
  - **Reja plegable** tipo tijera: exportala **cerrada** y extendida (1,2 × 2,1 m). La animo yo
    comprimiéndola hacia un costado. Pivote: el borde fijo, abajo.
- Grosor: hasta 5 cm.

## 4. Sonidos (opcional) — WAV

- `ascensor_motor.wav`: zumbido que se pueda repetir en loop, de 2 a 4 s.
- `ascensor_golpe.wav`: "clunk" corto del arranque y la frenada.
- `ascensor_reja.wav`: reja o puerta que se desliza, de alrededor de 1 s.

Si no tenés sonidos, genero unos provisorios.

## Cómo va a funcionar

Parado en la cabina con **E**: la reja se cierra (1 s), hay un sacudón y arranca el motor, la cabina sube
2 m por dentro de la estructura fija, fundido corto arriba, aparecés arriba en el otro ascensor, la cabina
baja, frena con otro sacudón y la reja se abre.
