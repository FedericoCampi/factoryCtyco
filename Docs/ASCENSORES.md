# Ascensores entre estacionamiento y fábrica — 26 de septiembre de 2026

El estacionamiento ya no está pegado a la fábrica: se movió 15 m al oeste
(`Parking_Estacionamiento` en (-3803, -410, 0)). Las dos puertas que los unían quedaron tapadas
con bloqueos invisibles (`Bloqueo_PuertaFabrica`, `Bloqueo_PuertaEstacionamiento`).
El extractor y `PlayerStart_Robot1` van enganchados al estacionamiento: moverlo los mueve.

- `Ascensor_Estacionamiento`: en la terraza (1,35 m), enganchado al estacionamiento.
- `Ascensor_Fabrica`: lado oeste de la fábrica (-850, 90, 0), enganchado a `SceneRobot_Fabrica`.

Clase C++ `AFactoryElevator` (FactoryCtycoRuntime). Parado sobre la plataforma aparece
"[E] IR A …"; con E toda la cabina (piso y jaula con su techo) sube a la vista con el personaje, arriba
hay un fundido corto a negro, el personaje pasa a lo alto de la otra cabina, vuelve la imagen y esa cabina
baja hasta el piso. Propiedades: `Destination`, `StopName`, `InteractionRadius` (75), `TravelDepth`
(-200: negativo sube), `TravelSeconds` (2,2: subida y bajada visibles), `FadeSeconds` (0,3).
La plataforma tiene su propia colisión (`PlatformCollision`, cara superior a 12 cm): se pisa encima.
Para otra parada: duplicar un ascensor y apuntar los `Destination`.

Regenerar: `Scripts/run_elevator_setup.py` (sin editor; reimporta SM_Parking y corre
`apply_elevators.py`, que es idempotente y no vuelve a mover el estacionamiento).
También se corrigió la colisión de la terraza (quedaba a 1,83 m en vez de 1,35 m por un
redondeo en `author_parking_scene.py`).

No se probó todavía en Play.

## Modelo del usuario (26/09)

`3D assets/GLBs/ascensorEstructura.glb` y `ascensorPiso.glb`, preparados por
`Scripts/author_elevator_meshes.py` (reducción de caras, escala 4,4: jaula de 2,43 × 2,43 × 4,41 m,
hueco de 1,45 m; plataforma de 1,4 m; UCX solo en los 4 postes) y colocados por
`Scripts/apply_elevator_meshes.py`: `Crown` = estructura fija con colisión, `Platform` = piso que
baja y sube, sin los postes ni el anillo básicos; `InteractionRadius` 75.
El travesaño inferior de la jaula no tiene colisión: el personaje lo atraviesa al entrar.

Resuelto el 27/09 (FactoryCtycoRuntime reinstalado con las cajas de despacho). Antes: el binario instalado de FactoryCtycoRuntime todavía tiene `TravelDepth` >= 0 como límite del
panel de detalles (los actores ya tienen -180 y funciona). El código nuevo compila; instalar con
`Scripts/build_runtime_visuals.ps1 -Install` la próxima vez que el editor esté cerrado.

## Jaula hundida y viaje visible (27/09)

El personaje atravesaba el travesaño inferior de la jaula (de 17 a 57 cm, en los cuatro lados).
`Scripts/apply_elevator_sink.py` baja la estructura (`Crown`) 57 cm para dejarlo al ras del piso:
se entra por cualquier lado. La jaula sube junto con el piso (se guarda su altura de reposo en
BeginPlay), así que el techo acompaña al personaje. El piso de la plataforma queda a 12 cm (a 1 cm lo
tapaba la malla del suelo) y ahora tiene colisión, así los pies no se hunden. Informe: `Docs/elevator_sink.json`. Requiere el FactoryCtycoRuntime compilado el 27/09
instalado (`FadeSeconds` es nuevo).

## Ascensor2: cabina que baja por un pozo (27/09, reemplaza lo anterior)

Modelo del usuario `3D assets/GLBs/ascensor2.glb` (una cabina). Los dos ascensores son ahora una cabina de
2,38 × 3,03 m (2,26 m libres por dentro) apoyada al ras en un **agujero del piso**, sobre un **tubo** de 3,3 m.
Con E: se cierra la puerta (0,9 s), golpe y motor, la cabina **baja** 2,6 m por el tubo con el personaje,
fundido abajo, el personaje aparece abajo en el otro ascensor, que **sube**, golpe, y se abre la puerta.
La cabina de salida vuelve a subir vacía. El techo se esconde mientras el jugador está adentro (cámara
isométrica) y la cámara deja de chocar durante el viaje. Las entradas miran a -X: hacia la fábrica y
hacia la terraza. Se pueden girar 180° sin tocar el agujero; otro giro o moverlos exige recortar el piso.

- Piezas (`Scripts/author_elevator2.py`, Blender): `SM_Ascensor2Cabina` (6 UCX), `SM_Ascensor2Techo`,
  `SM_Ascensor2Puerta` (4 hojas telescópicas, 2 por lado) y `SM_Ascensor2Tubo`, en
  `/Game/FactoryCtyco/Environments/Ascensor2`. Medidas en `SourceAssets/Ascensor2/elevator2_build.json`.
- Sonidos provisorios (`Scripts/make_elevator_sounds.py`): `S_Ascensor_Motor` (loop), `S_Ascensor_Golpe`,
  `S_Ascensor_Puerta`. Para cambiarlos, reemplazar los WAV en `SourceAssets/Ascensor2` y volver a aplicar.
- Agujeros: centros en `Scripts/elevator_holes.py`; `Scripts/floor_holes.py` los corta (visual y UCX)
  dentro de `author_arena_edit.py` y `author_parking_scene.py`. Respaldos en
  `SourceAssets/*/respaldo_2026-09-27_ascensor` y `Saved/Respaldos/2026-09-27_ascensor2`.
- Instalar (editor cerrado): `Scripts/apply_elevator2.py` importa todo, rehace SM_SceneRobot y SM_Parking,
  configura los ascensores sobre su agujero y guarda el nivel. Informe: `Docs/elevator2_apply.json`.
- Clase `AFactoryElevator`: `TravelDepth` (259), `TravelSeconds` (2,4), `FadeSeconds` (0,3),
  `DoorSeconds` (0,9), medidas de puerta y cabina, y los tres sonidos.

## Cabina fija, piso que se mueve y panel de pisos (28/09, reemplaza lo anterior)

- **La cabina y sus puertas corredizas quedan en su piso**. Las puertas están cerradas por defecto y se abren
  cuando el personaje se acerca (`DoorNearRadius`, 300 cm); al alejarse se cierran. Al subir o bajar se cierran
  antes de moverse y en el destino se abren al llegar. Solo se mueve el piso de adentro
  (`Platform`, malla `SM_Ascensor2Piso`, separada de `SM_Ascensor2Cabina` en `author_elevator2.py`) con el personaje.
- **Panel**: parado en la cabina aparece «[E] ASCENSOR»; E abre a la derecha el panel con todos los pisos
  (todos los `AFactoryElevator` del nivel, del más bajo al más alto: hoy 1 FÁBRICA y 2 ESTACIONAMIENTO), en cuál
  estás y si cada uno es «▲ SUBIR» o «▼ BAJAR». Se elige con clic o con su número (1, 2…); E lo cierra, y
  salir de la cabina también. Para otro piso: duplicar un ascensor y darle su `StopName`; aparece solo en el panel.
- **Viaje**: bajando, el piso se hunde en el pozo (`TravelDepth`, 259 cm); subiendo, sube dentro de la cabina
  (`RiseHeight`, 150 cm). Fundido a negro y el personaje aparece en el otro ascensor: si subió, su piso viene
  subiendo desde el pozo; si bajó, viene bajando desde arriba. `Destination` ya no se usa.
- Aplicar: `Scripts/apply_elevator_platform.py` (reimporta cabina y piso; no toca lo demás).
  Prueba en Play: `Scripts/playtest_elevator_panel.py` (19 comprobaciones, incluye puertas cerradas por defecto, que se abren al acercarse y se cierran al viajar y al alejarse; pasó el 28/09; capturas
  `Docs/elevator_panel.png` y `Docs/elevator_ride.png`). Respaldo del código anterior:
  `Saved/Respaldos/2026-09-28_ascensor_panel`; fuentes previas del ascensor en `Saved/Respaldos/2026-09-28_dos_camiones/Ascensor2_fuentes`.

## Tercer piso (28/09)

`Ascensor_Empleados` en el estacionamiento de empleados (piso 3, "EMPLEADOS", Z 414), copia de
`Ascensor_Estacionamiento`: el panel muestra 1 FÁBRICA, 2 ESTACIONAMIENTO y 3 EMPLEADOS. Su pozo es el agujero de la
vereda de `SM_EmpleadosPiso`. Ver `Docs/ESTACIONAMIENTO.md` (Piso 3). Las puertas se abren también cuando se acerca un
empleado contratado.

## Ascensor de la fábrica en el vano este (30/09)

El usuario movió `Ascensor_Fabrica` al vano este de la fábrica: local (1190, 80, 0) en `SceneRobot_Fabrica`, con la
puerta hacia adentro. Queda 1,7 m afuera del borde de la losa, pegado al contrafuerte.

- El pozo se mudó con él: centro nuevo en `Scripts/elevator_holes.py`, y `author_arena_edit.py` rehízo la malla
  (el agujero viejo, en local (800, −370), quedó cerrado; 72 colisiones UCX).
- Afuera de la losa el piso es `Piso_Exterior`, un plano del motor que no se puede agujerear. Se repartió en cuatro
  planos alrededor del pozo: `Piso_Exterior` (al oeste), `Piso_Exterior_Este`, `Piso_Exterior_PozoSur` y
  `Piso_Exterior_PozoNorte` (`Scripts/apply_elevator_move.py`, idempotente). `Piso_Exterior` ya no mide 100 × 100 m:
  `run_truck_entrance_setup.py` lo usaba para ubicar `Piso_Exterior_Oeste`, no volver a correrlo sin revisar eso.
- Si se vuelve a mover: cambiar el centro en `elevator_holes.py`, correr `author_arena_edit.py` en Blender y, con el
  editor cerrado, `Scripts/run_elevator_move_setup.py`. El ascensor tiene que estar girado 0° o 180°.
- Comprobado con rayos en el editor (`Docs/elevator_move.json`): pozo abierto, piso firme frente a la puerta y
  agujero viejo cerrado. No se probó el viaje en Play.
- Respaldos: `SourceAssets/SceneRobot/respaldo_2026-09-30_ascensor` y `Saved/Respaldos/2026-09-30_ascensor_cintas`
  (nivel y `SM_SceneRobot` anteriores).
