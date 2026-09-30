# Horno de fundición y laboratorio — 30 de septiembre de 2026

Modelos del usuario, puestos en `L_FactoryDemo` para que él los ubique. Por ahora son decorado: no tienen función de juego.

## Horno de fundición
- Fuente: `3D assets/GLBs/hornoFundicion.glb` (1 m, ~690 000 triángulos, 4 texturas).
- `Scripts/author_horno_fundicion.py` (Blender) lo lleva a **2 m de alto** (1,96 × 1,61 m: entra en una celda),
  origen al centro del piso, ~152 000 triángulos y una colisión de caja. Salida en `SourceAssets/HornoFundicion`.
- Malla `/Game/FactoryCtyco/Environments/HornoFundicion/SM_HornoFundicion`; actor `Horno_Fundicion` (carpeta Fabrica),
  en (0, −500, 0), dentro de la fábrica.
- El FBX solo lleva color y relieve (normal): los mapas de metal/rugosidad del GLB no pasan. Si se ve apagado, se le
  puede armar un material con esas dos texturas.
- Altura: `HEIGHT_M` al principio del script.

## Laboratorio (escenaLab1)
- Fuente: `3D assets/GLBs/scenes/escenaLab1-complete.glb` (20,6 × 18,6 m, 4,8 m de alto, 1139 piezas, sin colisiones).
- `Scripts/author_lab_scene.py` une las piezas en `SM_Lab1` (143 000 triángulos, 26 materiales), en escala real.
  Salida en `SourceAssets/Lab1`.
- En Unreal choca con la propia malla (*complex as simple*): se pisa y se choca con lo que se ve.
- Actor `Lab1_Escena` (carpeta Lab1) en (3800, 0, 0), al este de la fábrica, sobre el piso de afuera. Todavía no hay
  cómo llegar caminando ni ascensor, y tiene techo (con la cámara de arriba no se ve adentro).

Importar los dos (editor abierto con `L_FactoryDemo`): `Scripts/import_horno_y_lab.py`. Si los actores ya existen,
solo cambia la malla y conserva su lugar. Informe: `Docs/horno_y_lab_import.json`.

## Carpetas de `3D assets/GLBs` (reorganizadas por el usuario el 30/09)
Las escenas pasaron a `GLBs/scenes` (`sceneStacionamiento.glb`, `esceneStacionamientoOriginal.glb`,
`recepcion/recepcion`, `escenaLab1-complete.glb`) y los modelos de la demo de reciclaje están en `GLBs/robotAutomation`.
Se corrigieron las rutas de `author_parking_scene.py`, `author_parking_columns.py`, `author_employee_scene.py` y
`author_reception_room.py`. Los demás modelos siguen en `GLBs` y sus scripts no cambiaron.
