"""Editor Python (con L_FactoryDemo abierto): cintas fijas en la linea de la fabrica.

Pedido del 30/09: las cintas de la fabrica ya no se construyen en juego (B > 4) sobre los contornos
turquesa; quedan puestas en el nivel como actores (Cinta_Fabrica_N, clase AFactoryBuilding con la
definicion DB_Belt) para moverlas, girarlas o duplicarlas en el editor. Quita los contornos
FactoryGuide_Belt_*. No toca las cintas de despacho ni las de carga.
Idempotente: si ya hay Cinta_Fabrica_*, no las mueve ni crea otras. No guarda el nivel.
Informe: Docs/factory_belts.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
try:
    level = actors.get_all_level_actors()
    factory = next(a for a in level if isinstance(a, unreal.FactoryDemoWorld))
    belt = next(c for c in factory.get_editor_property("catalog") if c and str(c.get_editor_property("building_id")) == "Belt")
    guides = sorted((a for a in level if a.get_actor_label().startswith("FactoryGuide_Belt_")), key=lambda a: a.get_actor_label())
    placed = [a for a in level if a.get_actor_label().startswith("Cinta_Fabrica_")]
    created = []
    if not placed:
        floor_z = factory.get_editor_property("floor_z")
        for number, guide in enumerate(guides, 1):
            spot = guide.get_actor_location()
            b = actors.spawn_actor_from_class(unreal.FactoryBuilding, unreal.Vector(spot.x, spot.y, floor_z), unreal.Rotator())
            b.set_actor_label(f"Cinta_Fabrica_{number}")
            b.set_editor_property("persistent_id", f"Cinta_Fabrica_{number}")
            b.set_editor_property("definition", belt)
            b.set_editor_property("paid_scrap", 0)
            b.refresh_visuals()
            placed.append(b)
            created.append(b.get_actor_label())
    for guide in guides:
        actors.destroy_actor(guide)
    if not placed:
        raise RuntimeError("No habia contornos FactoryGuide_Belt_* ni cintas Cinta_Fabrica_*")
    report.update(passed=True, created=created, removed_guides=len(guides),
                  belts=[[a.get_actor_label(), *[round(v, 1) for v in a.get_actor_location().to_tuple()], round(a.get_actor_rotation().yaw, 1)] for a in placed])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[FACTORY_BELTS] {error}")
(project / "Docs/factory_belts.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
