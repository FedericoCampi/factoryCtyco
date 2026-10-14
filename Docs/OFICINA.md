# Oficina de administración (piso 4) — 7 de octubre de 2026

Escena del usuario (`3D assets/GLBs/scenes/Oficina industrial minimalista en 3D-complete.glb`): salón de 9 × 10 m con
escritorios, sala de reuniones y dos anexos; paredes del frente bajas (1,2 m, para la vista isométrica) y las de atrás de
3,3 m con ventanas. Sin techo.

- `Oficina_Administracion` (StaticMeshActor, carpeta Oficina) en (1000, 6500, 1100): un **piso alto** (11 m) en un lugar
  libre del mapa. Los ascensores llevan con un fundido, así que no está encima de otro edificio (apilada sobre la
  Recepción, el pozo de su ascensor se metía en la cabina del de abajo). Choca con su propia malla. 11,8 × 12,8 m.
- Se quitaron del modelo el suelo de 49 × 50 m, la puerta doble con su marco y el felpudo: en ese vano está
  **`Ascensor_Oficina`** (copia de `Ascensor_Empleados`, puerta hacia adentro), parada **«ADMINISTRACIÓN»**: aparece sola
  en el panel de todos los ascensores (piso 4, el más alto).
- **`Escena_Oficina`** (escena "Oficina", carpeta Escenas): solo se ve con el personaje adentro.
- Scripts: `Scripts/author_oficina.py` (Blender) → `SourceAssets/Oficina/SM_Oficina.fbx`; `Scripts/apply_oficina.py`
  (editor: importa, coloca oficina, ascensor y escena; si existen, la oficina conserva su lugar). Informe `Docs/oficina.json`.
- Prueba en Play: `Scripts/playtest_oficina.py` → `Docs/oficina_play.json` (6/6: está en el panel, el viaje desde la
  fábrica llega a la oficina, se ve solo la oficina y se camina hacia adentro).
- Pendiente: no tiene luces propias ni techo (la ilumina el cielo); todavía sin función (pedidos, proveedores).
- Respaldo del nivel de antes: `Saved/Respaldos/2026-10-07_vano_norte/L_FactoryDemo_antes_oficina.umap`.
