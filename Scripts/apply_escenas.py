"""Editor Python (04/10): zonas de escena (AFactorySceneZone), para que en el juego solo se vea la escena donde esta el
personaje (primera persona e isometrica); las demas se ocultan para la camara del jugador pero siguen funcionando.

Cuatro escenas (Despacho y Muelles son una sola, se pasa sin puerta), carpeta Escenas:
- Escena_Fabrica      (Fabrica)      el galpon de la fabrica y su ampliacion al norte.
- Escena_Despacho     (Despacho)     estacionamiento, despacho, cintas de carga y los muelles con su patio.
- Escena_Laboratorio  (Laboratorio)  el laboratorio al este.
- Escena_Empleados    (Empleados)    el edificio de empleados al norte (por ascensor).
Lo que no cae en ninguna (pisos de afuera, el horizonte, el cielo, las luces) se ve siempre. Si ya estan, solo ajusta
sus cajas. Guarda el nivel. Informe con que actor quedo en cada escena: Docs/escenas.json.
Hay que correrlo con el editor abierto (crear actores sin ventana se cae).
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
FOLDER = "Escenas"
# etiqueta, escena, (x0, y0, z0), (x1, y1, z1) en cm del mundo, medidos sobre las piezas de cada escena (04/10)
ZONES = [
    ("Escena_Fabrica", "Fabrica", (-1150, -2650, -500), (2450, 3250, 2500)),
    ("Escena_Despacho", "Despacho", (-6000, -1700, -500), (-1600, 3800, 2500)),
    ("Escena_Laboratorio", "Laboratorio", (3300, -1000, -500), (5450, 1000, 2500)),
    ("Escena_Empleados", "Empleados", (-7450, 6550, -500), (-750, 12050, 3000)),
]
report = {"passed": False}

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    for label, scene, lo, hi in ZONES:
        center = unreal.Vector(*[(a + b) / 2 for a, b in zip(lo, hi)])
        half = unreal.Vector(*[(b - a) / 2 for a, b in zip(lo, hi)])
        zone = by.get(label)
        if zone is None:
            zone = actors.spawn_actor_from_class(unreal.FactorySceneZone, center, unreal.Rotator(0, 0, 0))
            zone.set_actor_label(label)
        zone.modify()
        zone.set_folder_path(FOLDER)
        zone.set_actor_location(center, False, False)
        zone.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
        zone.set_actor_scale3d(unreal.Vector(1, 1, 1))
        zone.set_editor_property("scene", scene)
        zone.get_editor_property("box").set_box_extent(half)
    # los pisos de afuera se ven siempre (dos franjas angostas caen dentro de la fabrica)
    for a in actors.get_all_level_actors():
        if a.get_actor_label().startswith("Piso_Exterior") and "SiempreVisible" not in [str(t) for t in a.tags]:
            a.modify()
            a.tags = list(a.tags) + ["SiempreVisible"]
    scenes = {}
    for a in actors.get_all_level_actors():
        scene = str(unreal.FactorySceneZone.scene_of(a))
        scenes.setdefault(scene, []).append(a.get_actor_label())
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, counts={k: len(v) for k, v in scenes.items()},
                  scenes={k: sorted(v) for k, v in scenes.items()})
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[ESCENAS] " + report["error"])
finally:
    (project / "Docs/escenas.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
