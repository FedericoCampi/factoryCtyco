"""Editor Python (con L_FactoryDemo abierto): abre el piso de afuera bajo Ascensor_Fabrica.

El ascensor de la fabrica quedo en el vano este (30/09), con 1,7 m afuera de la losa. El agujero de la
losa lo corta author_arena_edit.py (elevator_holes.py); afuera el piso es Piso_Exterior, un plano del
motor que no se puede agujerear: se reparte en cuatro planos alrededor del pozo (Piso_Exterior al oeste,
Piso_Exterior_Este, Piso_Exterior_PozoSur y Piso_Exterior_PozoNorte), con el mismo material.
Idempotente: si el ascensor se mueve de nuevo, actualizar elevator_holes.py y volver a correr.
Comprueba con rayos que el pozo quedo abierto y que el agujero viejo se cerro. No guarda el nivel.
Informe: Docs/elevator_move.json.
"""
import json
import sys
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(project / "Scripts"))
from elevator_holes import HOLES  # noqa: E402

PIECES = ("Piso_Exterior", "Piso_Exterior_Este", "Piso_Exterior_PozoSur", "Piso_Exterior_PozoNorte")
OLD_HOLE = (800.0, -370.0)  # local en SceneRobot_Fabrica: donde estaba el pozo antes
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
try:
    level = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    arena, elevator, base = level["SceneRobot_Fabrica"], level["Ascensor_Fabrica"], level["Piso_Exterior"]
    hx, hy = json.loads((project / "SourceAssets/Ascensor2/elevator2_build.json").read_text())["tube"]["hole_half_m"]
    x, y, z = HOLES["arena"][0]
    centre = arena.get_actor_transform().transform_location(unreal.Vector(x * 100, -y * 100, z * 100))
    off = elevator.get_actor_location() - centre
    if abs(off.x) > 1 or abs(off.y) > 1:
        raise RuntimeError(f"Ascensor_Fabrica no esta sobre el agujero de elevator_holes.py (diferencia {off.x:.0f}, {off.y:.0f} cm)")
    yaw = elevator.get_actor_rotation().yaw % 180
    if min(yaw, 180 - yaw) > 1:
        raise RuntimeError("El agujero es recto: el ascensor tiene que estar girado 0 o 180 grados")
    x0, x1, y0, y1 = centre.x - hx * 100, centre.x + hx * 100, centre.y - hy * 100, centre.y + hy * 100

    # Todo el piso de afuera: lo que cubren hoy las piezas (la primera vez, solo Piso_Exterior).
    have = [level[n] for n in PIECES if n in level]
    lo = [min(a.get_actor_bounds(False)[0].to_tuple()[i] - a.get_actor_bounds(False)[1].to_tuple()[i] for a in have) for i in (0, 1)]
    hi = [max(a.get_actor_bounds(False)[0].to_tuple()[i] + a.get_actor_bounds(False)[1].to_tuple()[i] for a in have) for i in (0, 1)]
    height = base.get_actor_location().z
    src = base.static_mesh_component
    rects = {"Piso_Exterior": (lo[0], lo[1], x0, hi[1]), "Piso_Exterior_Este": (x1, lo[1], hi[0], hi[1]),
             "Piso_Exterior_PozoSur": (x0, lo[1], x1, y0), "Piso_Exterior_PozoNorte": (x0, y1, x1, hi[1])}
    for name, (ax, ay, bx, by) in rects.items():
        spot = unreal.Vector((ax + bx) / 2, (ay + by) / 2, height)
        piece = level.get(name)
        if piece is None:
            piece = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, base.get_actor_rotation())
            piece.set_actor_label(name)
            piece.set_folder_path(str(base.get_folder_path()))
            dst = piece.static_mesh_component
            dst.set_static_mesh(src.static_mesh)
            for slot, material in enumerate(src.get_materials()):
                dst.set_material(slot, material)
            dst.set_collision_profile_name(src.get_collision_profile_name())
            dst.set_cast_shadow(src.get_editor_property("cast_shadow"))
        piece.set_actor_location(spot, False, False)
        piece.set_actor_scale3d(unreal.Vector((bx - ax) / 100, (by - ay) / 100, 1))  # el plano del motor mide 1 m
    report["backdrop_cm"] = {n: [round(v) for v in r] for n, r in rects.items()}
    report["backdrop_material"] = [m.get_name() if m else None for m in src.get_materials()]

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    def floor(px, py, complex_trace):
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(px, py, 200), unreal.Vector(px, py, -250),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, complex_trace, [elevator], unreal.DrawDebugTrace.NONE, False)
        return round(hit.to_tuple()[4].z, 1) if hit else None

    old = arena.get_actor_transform().transform_location(unreal.Vector(OLD_HOLE[0], OLD_HOLE[1], 0))
    edge = arena.get_actor_bounds(False)[0].x + arena.get_actor_bounds(False)[1].x  # borde este de la losa
    inside = [(px, py) for px in (x0 + 15, (x0 + edge) / 2, edge - 15, edge + 40, x1 - 15) for py in (centre.y - 60, centre.y, y1 - 15)]  # del lado de y0 esta el contrafuerte
    checks = {
        "pozo_abierto_visual": all(floor(px, py, True) is None for px, py in inside),
        "pozo_abierto_colision": all(floor(px, py, False) is None for px, py in inside),
        "piso_frente_a_la_puerta": [floor(x0 - 25, centre.y, c) for c in (True, False)],
        "agujero_viejo_cerrado": [floor(old.x, old.y, c) for c in (True, False)],
    }
    report["checks"] = checks
    solid = lambda pair: all(v is not None and abs(v - centre.z) < 3 for v in pair)
    if not (checks["pozo_abierto_visual"] and checks["pozo_abierto_colision"] and solid(checks["piso_frente_a_la_puerta"]) and solid(checks["agujero_viejo_cerrado"])):
        raise RuntimeError("El pozo no quedo bien: ver checks")
    report.update(passed=True, hole_world_cm=[round(v) for v in (x0, y0, x1, y1)])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ELEVATOR_MOVE] {error}")
(project / "Docs/elevator_move.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
