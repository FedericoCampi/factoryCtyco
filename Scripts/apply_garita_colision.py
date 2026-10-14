"""Editor Python (08/10): la garita de la barrera (Cabina_Barrera) y su poste chocan.

SM_Cabina y SM_BarreraPoste no tenian colision simple (0 formas) y usaban la simple: se los atravesaba caminando. Pasan
a chocar con su propia malla (complex as simple): las paredes frenan y por la puerta se sigue entrando a la garita.
Comprueba con esferas (colision simple, la del personaje): de afuera hacia el centro de la garita choca con la pared y de afuera hacia el poste, con el poste.
Informe: Docs/garita_colision.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
report = {"passed": False, "mallas": {}}
try:
    for path in ("/Game/FactoryCtyco/Environments/CabinaBarrera/SM_Cabina", "/Game/FactoryCtyco/Environments/CabinaBarrera/SM_BarreraPoste"):
        mesh = unreal.load_asset(path)
        body = mesh.get_editor_property("body_setup")
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        mesh.set_editor_property("body_setup", body)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        report["mallas"][path.rsplit("/", 1)[1]] = str(body.get_editor_property("collision_trace_flag"))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    gate = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                if isinstance(a, unreal.FactoryGateBarrier))
    hits = {}
    for name in ("booth", "post"):
        comp = gate.get_editor_property(name)
        o, e, _ = unreal.SystemLibrary.get_component_bounds(comp)
        sides = {}
        for label, d in (("oeste", unreal.Vector(-1, 0, 0)), ("este", unreal.Vector(1, 0, 0)), ("sur", unreal.Vector(0, -1, 0)), ("norte", unreal.Vector(0, 1, 0))):
            start = unreal.Vector(o.x + d.x * (e.x + 200), o.y + d.y * (e.y + 200), gate.get_actor_location().z + 100)
            end = unreal.Vector(o.x, o.y, start.z)
            # una esfera con la colision simple (la que usa el personaje), no la de la malla
            hit = unreal.SystemLibrary.sphere_trace_single(world, start, end, 20.0, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                           unreal.DrawDebugTrace.NONE, True)
            t = hit.to_tuple() if hit else None
            sides[label] = (t[10].get_name() if t and t[10] else None)
        hits[name] = sides
    report["choques"] = hits
    # la garita frena por lo menos de un lado (por la puerta se entra) y el poste tambien
    report["passed"] = "Booth" in hits["booth"].values() and "Post" in hits["post"].values()
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
(project / "Docs/garita_colision.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
