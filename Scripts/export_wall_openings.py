"""Editor Python (con L_FactoryDemo abierto): anota donde cortar el muro del estacionamiento.

Para cada actor de OPENING_ACTORS toma su caja envolvente en coordenadas del estacionamiento y
la guarda en SourceAssets/Parking/wall_openings.json, en metros del GLB (x, -y). Despues
author_parking_scene.py abre el muro oeste a ese ancho. Correr cada vez que se mueva la maquina.
"""
import json
from pathlib import Path
import unreal

OPENING_ACTORS = ["Despacho_Machine2"]
project = Path(unreal.Paths.project_dir()).resolve()
level_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
parking = next(a for a in level_actors if a.get_actor_label() == "Parking_Estacionamiento")
inverse = parking.get_actor_transform().inverse()
openings = []
for label in OPENING_ACTORS:
    actor = next(a for a in level_actors if a.get_actor_label() == label)
    origin, extent = actor.get_actor_bounds(False)
    corners = [inverse.transform_location(origin + unreal.Vector(sx * extent.x, sy * extent.y, sz * extent.z))
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    ys = [-c.y / 100 for c in corners]
    openings.append({"actor": label, "y": [round(min(ys), 3), round(max(ys), 3)],
                     "x": [round(min(c.x for c in corners) / 100, 3), round(max(c.x for c in corners) / 100, 3)],
                     "top": round(max(c.z for c in corners) / 100, 3)})
(project / "SourceAssets/Parking/wall_openings.json").write_text(json.dumps(openings, indent=1), encoding="utf-8")
