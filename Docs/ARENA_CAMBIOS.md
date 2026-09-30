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
