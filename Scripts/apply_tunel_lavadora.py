"""Editor Python (con L_FactoryDemo abierto): prepara la caja gris como tunel para la cinta (02/10).

Desde que el usuario ubica la linea (MOVE_LAYOUT = False) solo hace el paso 4, con la cinta como este.
1. Lavadora_Cuarzo (la caja gris, 2,5 x) se corre a BOX_Y para que la cinta pase por adentro sin asomar por el costado
   (en 561 la cinta, en Y 701, se salia 19 cm; la pared norte esta en 835).
2. Deposito_Cuarzo (100 de cuarzo) va del otro lado de la caja (DEPOT_AT), entregando hacia la trituradora.
3. Cinta_Cuarzo_Triturar se alarga: del deposito, atraviesa la caja y sube hasta arriba de la tolva (la punta que dejo
   el usuario no se mueve).
4. Calcula donde la cinta cruza las dos paredes de la caja y escribe los huecos en el espacio de la malla
   (SourceAssets/LavadoraTunel/tunel_holes.json) y exporta SM_Deposito (SM_Deposito_export.fbx) para
   author_lavadora_tunel.py. Despues: Blender y apply_proceso_fundicion.py (que cambia la caja por el tunel y pone la
   tapa de salida de la trituradora, apply_lavadora_cuarzo.py).
Informe: Docs/tunel_lavadora.json.
"""
import json
import math
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
BOX_Y = 661.0
MOVE_LAYOUT = False          # desde el 02/10 (noche) la caja, el deposito y la cinta los ubica el usuario
DEPOT_AT = (1966.0, 701.0)   # su salida mira a -X, a la caja
FLOOR = 4.0
HOLE_HALF_WIDTH = 65.0       # cm a cada lado del centro de la cinta (la cinta mide 105)
HOLE_BELOW, HOLE_ABOVE = 45.0, 50.0   # cm abajo y arriba del punto por donde viaja la carga
OUT = project / "SourceAssets/LavadoraTunel"
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def rnd(v):
    return [round(v.x), round(v.y), round(v.z)]


try:
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    box, feeder, depot = by["Lavadora_Cuarzo"], by["Cinta_Cuarzo_Triturar"], by["Deposito_Cuarzo"]
    if MOVE_LAYOUT:
        box.modify()
        loc = box.get_actor_location()
        box.set_actor_location(unreal.Vector(loc.x, BOX_Y, loc.z), False, False)
    a, b = feeder.input_point(), feeder.output_point()     # la cinta como este (la ubica el usuario)
    slope = feeder.get_editor_property("slope")
    flat = math.hypot(b.x - a.x, b.y - a.y)
    d = b - a

    # huecos: donde la carga cruza cada pared de la caja, en el espacio de la malla
    # la caja es un StaticMeshActor con SM_LavadoraTunel (mismas coordenadas que SM_Deposito); antes, un FactoryBuilding
    if isinstance(box, unreal.FactoryBuilding):
        mesh = box.get_editor_property("definition").get_editor_property("mesh")
        vt = box.get_editor_property("visual").get_world_transform()
    else:
        mesh = unreal.load_asset("/Game/FactoryCtyco/Factory/Models/Deposito/SM_Deposito")
        vt = box.static_mesh_component.get_world_transform()
    bb = mesh.get_bounding_box()
    scale = vt.scale3d.z
    la, lb = vt.inverse_transform_location(a), vt.inverse_transform_location(b)
    holes = []
    for wall_y in (bb.min.y, bb.max.y):
        t = (wall_y - la.y) / (lb.y - la.y)
        if not 0 < t < 1:
            raise RuntimeError(f"La cinta no cruza la pared Y={wall_y:.1f} de la caja (t={t:.2f})")
        p = la + (lb - la) * t
        holes.append({"wall_y": wall_y, "x": p.x, "half_width": HOLE_HALF_WIDTH / scale,
                      "z0": p.z - HOLE_BELOW / scale, "z1": p.z + HOLE_ABOVE / scale,
                      "world": rnd(vt.transform_location(p))})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tunel_holes.json").write_text(json.dumps({"mesh": mesh.get_path_name(), "bounds_min": [bb.min.x, bb.min.y, bb.min.z],
                                                      "bounds_max": [bb.max.x, bb.max.y, bb.max.z], "holes": holes}, indent=1), encoding="utf-8")
    task = unreal.AssetExportTask()
    task.object = mesh
    task.filename = str(OUT / "SM_Deposito_export.fbx")
    task.automated = task.replace_identical = True
    task.prompt = False
    task.exporter = unreal.StaticMeshExporterFBX()
    if not unreal.Exporter.run_asset_export_task(task):
        raise RuntimeError("No se pudo exportar SM_Deposito")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, caja=rnd(box.get_actor_location()), deposito=rnd(depot.get_actor_location()),
                  cinta={"in": rnd(feeder.input_point()), "out": rnd(feeder.output_point()), "slope": round(slope, 1),
                         "largo_cm": round(math.hypot(flat, d.z))}, huecos=[h["world"] for h in holes])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[TUNEL_LAVADORA] " + report["error"])
(project / "Docs/tunel_lavadora.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
