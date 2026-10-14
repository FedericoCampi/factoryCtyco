"""Editor Python (con L_FactoryDemo abierto): linea de descarga del horno (02/10).

Tubo_Descarga -> Codo_Metalico -> Container_Producto. Los dos caños van abiertos arriba (author_tubo_descarga.py y
author_codo_metalico.py les sacan la mitad de arriba) para que se vea bajar el liquido.
- Reimporta SM_TuboDescarga y SM_CodoMetalico e importa SM_ContainerProducto (author_container_producto.py) en
  /Game/FactoryCtyco/Environments/ContainerProducto. Borra los assets antes: reimportar encima los dejaba al 1 %.
- El tubo no se mueve (lo ubica el usuario). El codo se encaja en su boca de salida: mismo centro, mismo diametro
  (escala uniforme) y mismo eje, que baja unos 5 grados como el caño. De las dos bocas del codo se usa como entrada la
  que lo deja girado mas parecido a como estaba; se vuelve a encajar cada vez que se corre el script.
- `Container_Producto` (carpeta Fabrica) va al piso, bajo la boca de salida del codo y a lo largo de ella. Si ya
  existe no se mueve.
Informe: Docs/linea_descarga.json.
"""
import json
import math
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
ENV = "/Game/FactoryCtyco/Environments"
CONTAINER_AHEAD_CM = 35   # el centro del contenedor queda un poco adelante de la boca, donde cae el chorro
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def import_fbx(fbx, dest, name, users):
    path = f"{dest}/{name}"
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.one_convex_hull_per_ucx = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.generate_lightmap_u_vs = False
    data.build_nanite = False
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path, task.destination_name = dest, name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(dest, only_if_is_dirty=True, recursive=True)   # materiales y texturas
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != 1:
        raise RuntimeError(f"{name}: {hulls} colisiones")
    for a in users:
        a.modify()
        a.static_mesh_component.set_static_mesh(mesh)
    return mesh


def vec(v):
    return unreal.Vector(*v)


def rnd(v, n=1):
    return [round(v.x, n), round(v.y, n), round(v.z, n)]


def floor_z(world, x, y, top, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, top), unreal.Vector(x, y, -300),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore, unreal.DrawDebugTrace.NONE, True)
    return (hit.to_tuple()[4].z, hit.to_tuple()[9].get_actor_label()) if hit else (0.0, None)


def fit_elbow(port, flow, up):
    """Rotacion que deja la boca `port` del codo mirando a -flow (contra el caño) con su arriba en `up`."""
    f = vec(port["facing"])
    face, z = flow * -1.0, up
    if f.y > 0.5:                      # boca +Y: X = Y x Z
        x = face.cross(z)
    elif f.x < -0.5:                   # boca -X
        x = flow
    else:
        raise RuntimeError(f"Boca del codo inesperada: {port['facing']}")
    return unreal.MathLibrary.make_rot_from_xz(x, z)


def yaw_gap(a, b):
    return abs((a - b + 180) % 360 - 180)


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != MAP:
        raise RuntimeError("Abrir L_FactoryDemo en el editor antes de correr el script")
    level = actors.get_all_level_actors()
    users = lambda label: [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == label]
    tubo_build = json.loads((project / "SourceAssets/TuboDescarga/tubo_build.json").read_text(encoding="utf-8"))
    codo_build = json.loads((project / "SourceAssets/CodoMetalico/codo_build.json").read_text(encoding="utf-8"))
    cont_build = json.loads((project / "SourceAssets/ContainerProducto/container_build.json").read_text(encoding="utf-8"))
    if len(users("Tubo_Descarga")) != 1 or len(users("Codo_Metalico")) != 1:
        raise RuntimeError("Se esperaba un Tubo_Descarga y un Codo_Metalico en el nivel")
    tubo, codo = users("Tubo_Descarga")[0], users("Codo_Metalico")[0]

    import_fbx(project / "SourceAssets/TuboDescarga/SM_TuboDescarga.fbx", f"{ENV}/TuboDescarga", "SM_TuboDescarga", users("Tubo_Descarga"))
    import_fbx(project / "SourceAssets/CodoMetalico/SM_CodoMetalico.fbx", f"{ENV}/CodoMetalico", "SM_CodoMetalico", users("Codo_Metalico"))
    cont_mesh = import_fbx(project / "SourceAssets/ContainerProducto/SM_ContainerProducto.fbx", f"{ENV}/ContainerProducto",
                           "SM_ContainerProducto", users("Container_Producto"))

    # boca de salida del tubo y eje del caño en el mundo
    t = tubo.get_actor_transform()
    slope = math.radians(tubo_build["outlet_slope_deg"])
    outlet = t.transform_location(vec(tubo_build["outlet_cm"]))
    flow = t.transform_direction(unreal.Vector(math.cos(slope), 0, math.sin(slope))).normal()
    up = t.transform_direction(unreal.Vector(-math.sin(slope), 0, math.cos(slope))).normal()
    radius = tubo_build["outlet_radius_cm"] * tubo.get_actor_scale3d().x

    # el codo: la boca de entrada que lo deja girado mas parecido a como estaba
    before = codo.get_actor_rotation().yaw
    options = []
    for i, port in enumerate(codo_build["ports"]):
        rot = fit_elbow(port, flow, up)
        options.append((yaw_gap(rot.yaw, before), i, rot))
    _, inlet_i, rot = min(options, key=lambda o: o[0])
    inlet, out_port = codo_build["ports"][inlet_i], codo_build["ports"][1 - inlet_i]
    scale = radius / inlet["radius_cm"]
    loc = outlet - rot.quaternion().rotate_vector(vec(inlet["center_cm"]) * scale)
    codo.modify()
    codo.set_actor_location_and_rotation(loc, rot, False, False)
    codo.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    c = codo.get_actor_transform()
    joint = c.transform_location(vec(inlet["center_cm"]))
    spout = c.transform_location(vec(out_port["center_cm"]))
    spout_dir = c.transform_direction(vec(out_port["facing"])).normal()

    # el contenedor, en el piso bajo la boca del codo y a lo largo de ella
    cont = users("Container_Producto")
    placed = not cont
    if placed:
        spot = spout + unreal.Vector(spout_dir.x, spout_dir.y, 0).normal() * CONTAINER_AHEAD_CM
        z, floor = floor_z(world, spot.x, spot.y, spout.z - radius - 5, [tubo, codo])
        yaw = math.degrees(math.atan2(spout_dir.y, spout_dir.x))
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(spot.x, spot.y, z), unreal.Rotator(0, 0, yaw))
        actor.set_actor_label("Container_Producto")
        actor.set_folder_path("Fabrica")
        actor.static_mesh_component.set_static_mesh(cont_mesh)
        actor.static_mesh_component.set_collision_profile_name("BlockAll")
        report["container_floor"] = [round(z, 1), floor]
    else:
        actor = cont[0]
    co, ce = actor.get_actor_bounds(False)
    inside = abs(spout.x - co.x) < ce.x and abs(spout.y - co.y) < ce.y

    report.update(
        tubo={"location": rnd(tubo.get_actor_location(), 0), "outlet": rnd(outlet), "radius_cm": round(radius, 1),
              "slope_deg": tubo_build["outlet_slope_deg"]},
        codo={"location": rnd(loc), "rotation": [round(rot.roll, 2), round(rot.pitch, 2), round(rot.yaw, 2)],
              "yaw_before": round(before, 1), "scale": round(scale, 4), "inlet_port": inlet_i,
              "joint_gap_cm": round((joint - outlet).length(), 2), "spout": rnd(spout), "spout_dir": rnd(spout_dir, 3)},
        container={"placed_now": placed, "location": rnd(actor.get_actor_location(), 0),
                   "yaw": round(actor.get_actor_rotation().yaw, 1), "size_cm": [round(v * 100) for v in cont_build["size_m"]],
                   "top_z": round(co.z + ce.z, 1), "spout_over_container": inside})
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = report["codo"]["joint_gap_cm"] < 0.5 and inside
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[LINEA_DESCARGA] " + report["error"])
(project / "Docs/linea_descarga.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
