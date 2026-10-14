# Cambios en la arena de la fábrica (SceneRobot)

26/09/2026: por pedido se quitaron las cuatro barreras que rodean el círculo amarillo del centro
(NE/NW/SE/SW, con sus cajas y bidones: 196 piezas y 12 colisiones; quedan 70 UCX).

- `Scripts/author_arena_edit.py` (Blender) rehace `SourceAssets/SceneRobot/scene_unreal.fbx`
  desde `scene.glb` + `collision.glb`, igual que el generador de image-to-3d. Informe:
  `SourceAssets/SceneRobot/arena_edit.json`. Respaldo del FBX anterior en
  `SourceAssets/SceneRobot/respaldo_2026-09-26`.
- `Scripts/reimport_arena_mesh.py` (editor) borra y vuelve a crear `SM_SceneRobot` sin tocar el
  nivel; comprueba colisiones y que las medidas no cambien.

30/09/2026: se cerró el **vano oeste** (frente al ascensor de la fábrica). `author_arena_edit.py` copia el tramo de muro
vecino (entre los contrafuertes de y −7,36 y −3,04 del GLB: blindaje, rieles, franja naranja, tapa, panel de
mantenimiento y remaches, 22 piezas, y su colisión) 4,28 m hasta el otro contrafuerte, y saca las franjas amarillas
del umbral (6). Se borró `Bloqueo_PuertaFabrica`, el bloque oscuro que tapaba el vano. 73 colisiones UCX.
Aplicar con el editor abierto: `Scripts/apply_west_gate_closed.py` (reimporta la malla, comprueba con rayos que el muro
choca y que el pozo del ascensor sigue abierto, guarda el nivel; informe `Docs/west_gate_closed.json`).
Respaldos: `SourceAssets/SceneRobot/respaldo_2026-09-30_vano_oeste` y `Saved/Respaldos/2026-09-30_ascensor_cintas`
(`*_antes_vano_oeste`). Ojo: `respaldo_2026-09-30_ascensor` quedó con la versión con el pozo ya movido; la malla
anterior al cambio del ascensor está en `Saved/Respaldos/2026-09-30_ascensor_cintas/SM_SceneRobot.uasset`.

07/10/2026: **astillas en el aire, vano norte cerrado y pared arriba del ascensor.**
- Las "astillas" flotando cerca del horno y del centro eran de las mallas de desgaste que cubren toda la arena
  (`Armour edge oxidation`, `Armour edge paint losses`, `Cover chipped orange enamel`): seguían dibujando sus manchitas
  donde estaban las cuatro barreras quitadas el 26/09. `author_arena_edit.py` borra sus caras dentro de esas zonas
  (726 + 1953 + 288).
- **Vano norte** (detrás de la trituradora, x 340..940 en Unreal): se copian las piezas largas del muro vecino
  ("Front fortified wall …", estiradas al ancho del vano) y dos de sus paneles, con una colisión UCX nueva; se quitan
  sus 8 franjas amarillas y la pintura de advertencia del umbral (740 caras). 74 colisiones.
- Reimportar: `Scripts/reimport_arena_mesh.py` (editor abierto). Respaldos: `SourceAssets/SceneRobot/respaldo_2026-10-07_vano_norte`
  y `Saved/Respaldos/2026-10-07_vano_norte` (nivel y `SM_SceneRobot`).
- **Pared alta**: los dinteles de `apply_techos.py` dejaban ranuras (pasos a 2,60 m; arriba del ascensor recién desde
  4,14 m, se veía afuera). `Scripts/apply_techo_huecos.py` los baja hasta el muro (2,15 m) y, sobre `Ascensor_Fabrica`,
  hasta el techo de su cabina (2,22 m). Correrlo después de `apply_techos.py`. Informe `Docs/techo_huecos.json`.
- Quedan las franjas amarillas del vano este (frente al ascensor) y, a los costados de la cabina, dos pasos angostos
  bajos del vano este (≈0,5 y 0,8 m): no se pidieron.
- **Extractor de Silicio** de vuelta (el actor ya no estaba; sí sus accesorios): `Scripts/apply_restaurar_extractor.py`
  lo pone en (1885, −1530, 20), giro 180°, escala (2, 2, 1,5), con los accesorios enganchados e interruptor conectado.
