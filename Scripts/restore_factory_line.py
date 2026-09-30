"""Editor Python (con L_FactoryDemo abierto): vuelve a poner la linea inicial de la demo.

Igual que build_factory_demo.py: fila en y = 0 dentro de la fabrica (zona construible
-950..950), deposito de chatarra (-600), trituradora (-200), fundicion (200) y deposito de placas
(600), con guias de cinta en -400, 0 y 400. Las cintas se construyen con B > 4.
Comprueba cada lugar con AFactoryDemoWorld.placement_problem antes de colocar. No guarda el
nivel. Informe: Docs/factory_line_restore.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
Y = 0
LINE = [(0, "Storage", "Scrap"), (2, "Crusher", "Scrap"), (4, "Smelter", "Scrap"), (6, "Storage", "Plate")]
GUIDES = [1, 3, 5]
try:
    factory = next(a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryDemoWorld))
    catalog = {str(c.get_editor_property("building_id")): c for c in factory.get_editor_property("catalog") if c}
    for old in actors.get_all_level_actors():
        if isinstance(old, unreal.FactoryBuilding) or old.get_actor_label().startswith("FactoryGuide_"):
            actors.destroy_actor(old)
    positions = [unreal.Vector(x, Y, 4) for x in range(-600, 601, 200)]
    problems = {i: str(factory.placement_problem(positions[i], None)) for i, _, _ in LINE}
    blocked = {i: p for i, p in problems.items() if p}
    if blocked:
        raise RuntimeError(f"Lugares ocupados: {blocked}")
    placed = []
    for index, kind, item in LINE:
        b = actors.spawn_actor_from_class(unreal.FactoryBuilding, positions[index], unreal.Rotator())
        b.set_actor_label(f"Factory_{index}_{kind}")
        b.set_editor_property("persistent_id", f"Starter_{index}")
        b.set_editor_property("definition", catalog[kind])
        b.set_editor_property("storage_item", item)
        b.set_editor_property("paid_scrap", 0)
        b.refresh_visuals()
        placed.append([b.get_actor_label(), positions[index].x, Y])
    guide = unreal.load_asset(next(p for p in unreal.EditorAssetLibrary.list_assets("/Game/FactoryCtyco", recursive=True)
                                   if p.split(".")[0].endswith("/M_BeltSlot")))
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    for index in GUIDES:
        g = actors.spawn_actor_from_class(unreal.StaticMeshActor, positions[index] - unreal.Vector(0, 0, 2), unreal.Rotator())
        g.set_actor_label(f"FactoryGuide_Belt_{index}")
        sm = g.static_mesh_component
        sm.set_static_mesh(cube)
        sm.set_material(0, guide)
        sm.set_collision_profile_name("NoCollision")
        sm.set_cast_shadow(False)
        g.set_actor_scale3d(unreal.Vector(1.8, 1.8, 0.01))
    report.update(passed=True, buildings=placed, belt_guides=[[positions[i].x, Y] for i in GUIDES])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[FACTORY_LINE] {error}")
(project / "Docs/factory_line_restore.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
