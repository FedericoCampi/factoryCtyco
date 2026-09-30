"""Sin editor: mide el suelo bajo cada ascensor (trazas hacia abajo, ignorando el ascensor).

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/probe_elevator_floor.py -unattended -nosound
Informe: Docs/elevator_floor_probe.json
"""
import json
from pathlib import Path
import unreal

report = {"passed": False}
try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    elevators = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                 if a.get_class().get_name() == "FactoryElevator"]
    for e in elevators:
        loc = e.get_actor_location()
        samples = []
        for dx, dy in ((0, 0), (50, 50), (-50, -50), (170, 0), (0, 170), (-170, 0), (0, -170)):
            start = unreal.Vector(loc.x + dx, loc.y + dy, loc.z + 250)
            end = unreal.Vector(loc.x + dx, loc.y + dy, loc.z - 250)
            hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                         True, elevators, unreal.DrawDebugTrace.NONE, True)
            t = hit.to_tuple() if hit else None
            samples.append([dx, dy, round(t[4].z - loc.z, 1) if t and t[0] else None,
                            t[9].get_actor_label() if t and t[0] and t[9] else None])
        comps = {c.get_name(): round(c.get_editor_property("relative_location").z, 1)
                 for c in e.get_components_by_class(unreal.StaticMeshComponent)}
        report[e.get_actor_label()] = {"loc": [loc.x, loc.y, loc.z], "yaw": e.get_actor_rotation().yaw,
                                       "comps": comps, "ground_rel_z": samples}
    report["passed"] = True
except Exception as error:
    report["error"] = repr(error)
finally:
    (Path(__file__).resolve().parent.parent / "Docs/elevator_floor_probe.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    unreal.SystemLibrary.quit_editor()
