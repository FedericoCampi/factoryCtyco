"""Editor Python (con L_FactoryDemo abierto; sirve con el editor abierto): vano oeste de la fabrica cerrado (30/09).

Antes: blender -b --factory-startup -P Scripts/author_arena_edit.py (copia el tramo de muro vecino en el vano).
Rehace SM_SceneRobot (reimport_arena_mesh.py), borra Bloqueo_PuertaFabrica (el bloque oscuro que tapaba el vano)
y comprueba con rayos que el muro nuevo choca y que el pozo del ascensor sigue abierto. Guarda el nivel.
Informe: Docs/west_gate_closed.json.
"""
import json
import runpy
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
try:
    report["dirty_before"] = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    runpy.run_path(str(project / "Scripts/reimport_arena_mesh.py"), run_name="__main__")
    report["reimport"] = json.loads((project / "Docs/arena_reimport.json").read_text(encoding="utf-8"))
    if not report["reimport"].get("passed"):
        raise RuntimeError("No se pudo rehacer SM_SceneRobot")
    level = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    if "Bloqueo_PuertaFabrica" in level:
        actors.destroy_actor(level.pop("Bloqueo_PuertaFabrica"))
        report["removed"] = "Bloqueo_PuertaFabrica"
    arena = level["SceneRobot_Fabrica"]
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    def blocked(y_local):
        """Rayo horizontal de adentro hacia afuera a 1 m de alto por el vano (Blender y -> Unreal -y)."""
        a = arena.get_actor_transform().transform_location(unreal.Vector(-900, y_local, 100))
        b = arena.get_actor_transform().transform_location(unreal.Vector(-1300, y_local, 100))
        hit = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                     unreal.DrawDebugTrace.NONE, False)
        return (round(hit.to_tuple()[4].x, 1), hit.to_tuple()[9].get_actor_label()) if hit else None
    report["wall_hits"] = {str(y): blocked(y) for y in (-150, 90, 250)}   # Blender y 1,5 / -0,9 / -2,5
    if not all(h and h[1] == "SceneRobot_Fabrica" for h in report["wall_hits"].values()):
        raise RuntimeError("El vano oeste no quedo cerrado")
    lift = level["Ascensor_Fabrica"].get_actor_location()
    hit = unreal.SystemLibrary.line_trace_single(world, lift + unreal.Vector(-50, 0, 200), lift + unreal.Vector(-50, 0, -250),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [level["Ascensor_Fabrica"]],
                                                 unreal.DrawDebugTrace.NONE, False)
    report["elevator_pit_open"] = not hit
    if hit:
        raise RuntimeError("El pozo del ascensor quedo tapado")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[WEST_GATE] " + report["error"])
(project / "Docs/west_gate_closed.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
