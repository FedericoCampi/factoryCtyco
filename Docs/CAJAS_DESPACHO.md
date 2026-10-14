# Cintas de despacho — 27 de septiembre de 2026

Cada `Despacho_Machine*` tiene un `Despacho_Cajas*` enganchado (clase C++ `AFactoryDispatchBelt`,
FactoryCtycoRuntime) con su botonera al costado de la cinta.

En Play:
- Las cintas arrancan **apagadas**. Junto a la botonera aparece «[E] ENCENDER CINTA n»; E la prende
  (el hongo pasa de rojo a verde y los rodillos giran). Si hay dos botoneras a tiro, E usa la más cercana.
- Salen cajas cada 2,5 s, cada una desde un lugar distinto a lo ancho (hasta 55 a cada lado), y se
  encolan al final. Con 4 esperando la cinta **se detiene sola** y aparece encima un **cartel rojo
  «CINTA LLENA»** (con un pequeño rebote; siempre mira a la cámara).
- **Clic en el cartel**: abre arriba a la derecha el detalle (cajas 4/4, estado detenida, por qué).
  Otro clic lo cierra. No hay mensajes en el HUD al prender ni al llenarse.
- Todavía nadie retira las cajas.

Piezas: caja `SM_CajaDespacho` (`author_dispatch_box.py`), botonera `SM_BotoneraDespacho` + `M_BotonDespacho`
(parámetro `Encendido`, `author_dispatch_panel.py`), cartel `SM_CartelLleno` + `M_CartelLleno`
(`author_sign_and_wall.py`), todo en `/Game/FactoryCtyco/Environments/DispatchBox`. En la máquina: barrera
(postes y pasamanos naranja) y rodillos `M_DespachoRodillo` (parámetro `Velocidad`), ver DESPACHO_MACHINE.md.

Propiedades: `Start`/`End` (espacio de la máquina sin escalar: entra en y −70, se para en y 300),
`MaxBoxes` 4, `Speed` 70, `SecondsBetweenBoxes` 2,5, `BoxSpacing` 50, `MaxYawJitter` 8°, `LateralSpread` 55,
`RollerSpeed` 1,5, `InteractionRadius` 170, `SignLocation` (0, 150, 200), `BeltName`.
La botonera es un actor aparte desde el 28/09 (ver abajo).

Instalar y colocar (con el editor cerrado):
1. `Scripts/build_runtime_visuals.ps1 -Install`
2. `UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/apply_dispatch_belts.py -unattended -nosound`
   (informe `Docs/dispatch_belts.json`; idempotente; borra y reimporta caja, botonera y cartel: reimportar
   encima deja las mallas al 1 %).

Prueba en Play: `Scripts/playtest_dispatch_belts.py` (18 comprobaciones; informe `Docs/dispatch_belts_play.json`,
captura `Docs/dispatch_belts_play.png`). Lanzarla con `-ExecCmds="py <lanzador sin espacios en la ruta>"`:
en UE 5.6 `-ExecutePythonScript` cierra el editor al terminar el script. Pasó el 27/09.

## Cajas en mano, capacidad y sonidos (28/09)

- **Capacidad**: ya no hay un máximo fijo (`MaxBoxes` se quitó). Las cajas ocupan su lugar real, como piezas
  de tetris: cada una sale en una columna libre al azar y avanza hasta el fondo o hasta la caja de adelante en
  su columna. La cinta se llena cuando ninguna columna tiene lugar en la entrada. Columnas: las que entran en
  `BedHalfWidth` (90 cm a cada lado, hasta las barandas) cada `BoxSpacing` (44 cm = caja + luz): hoy 4
  columnas × 9 filas = 36 cajas (`GetCapacity()`). Al sacar una caja, las de atrás en su columna avanzan.
- **Agarrar**: E junto a una caja de la cinta (más cerca que la botonera) la toma; aparece «[E] AGARRAR CAJA».
  Si la cinta se había detenido por llena, vuelve a arrancar y sale una caja nueva. Con la caja en mano,
  E la deja en el piso adelante (`AFactoryLooseBox`) y se puede volver a agarrar. Los ascensores funcionan
  con la caja en mano.
- **Personaje**: `UFactoryCarryComponent` (se agrega solo) pone la caja entre los huesos `hand_l`/`hand_r`
  cada cuadro; `RobotLocomotion` usa `BS_TecJunior_Carry` (reposo, caminata y carrera con los brazos
  sosteniendo la caja, generadas en `author_tecjunior_rig.py`) mientras `bCarrying`.
- **Sonidos**: `S_CintaEncender` / `S_CintaApagar` (`Scripts/make_belt_sounds.py`) al prender y apagar,
  también cuando se detiene sola por llena.
- **Música**: `Musica_Fondo` (AmbientSound, carpeta Audio) toca `S_MusicaFabrica` en loop al 35 %
  (`Scripts/make_music.py`, 80 s, la menor, 96 BPM). Para usar otro tema: reemplazar
  `SourceAssets/Audio/musica_fabrica.wav` y volver a aplicar.
- Instalar (editor cerrado): `Scripts/apply_music_and_boxes.py`. Informe: `Docs/music_and_boxes.json`.
  Respaldo previo: `Saved/Respaldos/2026-09-28_cajas`.

- **Acomodo (28/09)**: al chocar con la caja de adelante o con el fondo, la caja se inclina hacia adelante,
  gira y se corre un poco, y vuelve con un resorte amortiguado; la golpeada también se mueve. Cada choque la
  deja con un giro algo distinto. Andando sobre los rodillos vibra levemente. Es una simulación visual
  (no física de Unreal): `BumpStrength` (1) regula la fuerza; 0 lo apaga.

## Botonera suelta (28/09)

La botonera ya no es un componente de la cinta: es el actor `Botonera_CintaN` (clase C++
`AFactoryBeltButton`, carpeta Environment), que se mueve, gira y escala como cualquier actor. Su
propiedad **`Belt`** dice qué cinta prende (se elige en el panel de detalles). Al empezar el juego
cada cinta busca la botonera que la apunta; sin botonera la cinta no se puede prender.
E, el texto «[E] ENCENDER CINTA n», el hongo rojo/verde y los sonidos funcionan igual.
El texto ya no aparece como «Texto» en el editor (queda vacío hasta el Play).

- Crear las botoneras donde estaban las viejas: `Scripts/apply_belt_buttons.py` en el editor
  (posiciones guardadas en `SourceAssets/DispatchBox/panel_positions.json`; informe `Docs/belt_buttons.json`).
- `apply_dispatch_belts.py` crea una al costado de la máquina si la cinta no tiene, y conserva las que existen.
- Para otra botonera de una cinta nueva: duplicar una y cambiar `Belt`.
- Respaldo del código anterior: `Saved/Respaldos/2026-09-28_botonera`.

## Cajas desordenadas (28/09)

Las cajas ya no salen en 4 columnas fijas: cada una sale en un lugar al azar a lo ancho de la entrada,
donde no se encime con otra, con un giro de hasta `MaxYawJitter` (9°) y deja una separación extra al azar
de hasta `GapJitter` (10 cm) con la de adelante. Avanzan hasta el fondo o hasta una caja de adelante que
se les cruce a lo ancho. La cinta se llena cuando no queda lugar en la entrada: por los huecos entran unas
23 o 24 cajas (antes 36). `GetCapacity()` queda como referencia (filas × columnas), y el detalle del
cartel muestra solo cuántas cajas hay. Se quitó `LaneJitter`.
Prueba: `Scripts/playtest_messy_belt.py` (pasó el 28/09: ~22 posiciones distintas a lo ancho por cinta,
sin cajas encimadas; captura `Docs/messy_belt_play.png`).
Nota: al hacer el respaldo de esta versión se pisó la copia previa a la botonera suelta de
`FactoryDispatchBelt.h/.cpp` en `Saved/Respaldos/2026-09-28_botonera`; esa carpeta tiene ahora la versión con botonera suelta.

## Esquina, cintas inclinadas y en altura (30/09)

Todo esto vale para las cintas de carga (`AFactoryLoadingBelt`, las `Cinta_Carga*`):
- **Esquina**: `Cinta_Esquina`, con el modelo del usuario `3D assets/GLBs/esquinaCinta-complete.glb`
  (`Scripts/author_belt_corner.py`: 0,8 m de ancho como las otras, rodillos a 0,88 m, cuatro patas, ~126 000
  triángulos, 8 colisiones). Es una cinta curva: `TurnDegrees` −90 y `Length` 241,7 cm (el eje de la curva). Está
  suelta en el estacionamiento (−3500, −1250) para ubicarla. **Dobla hacia el otro lado con escala Y = −1**; para
  agrandarla, escalar X e Y por igual.
- **Enganches**: igual que antes, una cinta le pasa sus cajas a la que empieza a menos de `LinkReach` (120 cm) de su
  salida y a menos de 60 cm de altura. Antes se comparaba mal la altura (salida con salida); ahora es salida con entrada,
  así se pueden encadenar cintas a distinta altura.
- **Inclinación**: girar la cinta en *pitch*. Las cajas suben o bajan por la pendiente, inclinadas con ella.
- **En altura**: subir la cinta. Debajo aparecen postes solos hasta el piso (`Supports`: uno cerca de cada punta y
  uno cada `SupportSpacing`, 250 cm; se rehacen al moverla en el editor). Por debajo se puede pasar. Una cinta a más
  de ~2,5 m sobre el personaje no se puede cargar a mano. El poste es un cubo de acero (`SupportMesh`,
  `SupportMaterial`, `SupportWidth`): se cambia por un modelo propio en el panel de detalles.
- Código: `TurnDegrees`, `LocalAt`/`WorldAt` (punto de la cinta a tantos cm), `BuildSupports` en `FactoryLoadingBelt`.
  La distancia para cargar se mide contra la curva o la pendiente. Respaldo del código anterior:
  `Saved/Respaldos/2026-09-30_cinta_esquina`.
- Colocar la esquina: `Scripts/apply_belt_corner.py` (informe `Docs/belt_corner.json`). Prueba en Play:
  `Scripts/playtest_belt_corner.py` (esquina + rampa de 12° de prueba en el piso de la fábrica, que no se guardan;
  7 comprobaciones, pasó el 30/09; `Docs/belt_corner_play.json`).

## Circuito sin cortes (03/10)
Las cintas de cajas de las máquinas terminaban en su tope y las cintas de carga empezaban ~3 m más allá (con la
rejilla del piso en el medio). `Scripts/apply_puentes_despacho.py` las une con tramos de cinta de carga (copias de
`Cinta_Carga2` y `Cinta_Esquina`, mismo aspecto y altura): `Cinta_Puente2` (recta, de `Despacho_Cajas2` a
`Cinta_Carga2`) y `Cinta_Puente1` + `Cinta_Puente1_Curva` (recta y cuarto de vuelta espejado y agrandado, de
`Despacho_Cajas` a `Cinta_Carga3`). Una caja dejada en un puente sigue sola a la carga; las de la cinta de despacho
todavía se agarran con E. Informe: `Docs/puentes_despacho.json`.

## Curva de la cinta de despacho (04/10)
`SM_CintaCargaCurva` (`Scripts/author_loading_belt_curve.py`): la cinta de rodillos de `SM_CintaCarga` doblada 90°, con
el radio de la esquina negra (1,538 m; `Length` 241,6, `TurnDegrees` -90; escala Y -1 para doblar al otro lado). Rodillos
radiales con `M_DespachoRodillo` (giran), barandas naranjas, patas. `Scripts/apply_cinta_curva.py` la importa y se la
pone a todas las cintas de carga curvas (reemplaza a `SM_CintaEsquina`) → `Docs/cinta_curva.json`.

## Inclinar las cintas de despacho y ver el recorrido (04/10)
- **Inclinar** (rectas): `Slope` en Detalles (grados; positivo sube la punta de salida) o los dos rombos de las puntas
  (`InputEndHandle`, `OutputEndHandle`): arrastrar uno hacia arriba o abajo inclina la cinta sobre la **otra** punta, así
  la cinta enganchada ahí no se suelta. Girarla en pitch con el gizmo también cambia `Slope`. Las curvas no se inclinan.
- **Recorrido**: cada cinta de carga dibuja en el editor una línea blanca 3 cm sobre los rodillos (`Route`), de la punta
  de carga a la de salida, y una flecha blanca en la salida (`RouteArrow`): sigue la línea y la flecha para ver a dónde
  van las cajas. No se ve en el juego.
- **Invertir sentido**: botón en Detalles de cada cinta de carga (`ReverseDirection`). Da vuelta hacia dónde van las cajas
  sin mover la cinta (el actor pasa a la otra punta, mira al revés y, en una curva, se espeja). Se usó en `Cinta_Esquina`
  (04/10): el recorrido es `Cinta_Carga2` → `Cinta_Esquina` → `Cinta_Carga4` → `Cinta_Carga` → `Cinta_Carga3` →
  `Cinta_Muelle_5` → camión (`playtest_muelles_carga.py`, 15/15).
