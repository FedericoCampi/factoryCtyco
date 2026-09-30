"""Editor Python: piso 3, estacionamiento de empleados al aire libre (28/09).

Importa las piezas de author_employee_parking.py en /Game/FactoryCtyco/Environments/Empleados y arma:
- Empleados_Piso en ORIGIN (lejos del resto, y mas alto que el estacionamiento: el panel del ascensor ordena los
  pisos por altura, asi queda 3), con Empleados_Decor y cinco autos estacionados enganchados.
- Ascensor_Empleados: copia de Ascensor_Estacionamiento sobre el agujero de la vereda, parada "EMPLEADOS".
- Empleados_Cartel: "EMPLEADOS" pintado en el piso delante del ascensor.
- Punto_Contratacion (AFactoryWorkerSpawn): llega aca. CarRoute entra por la calle del oeste y estaciona en un
  cajon libre de la fila norte; CarMeshes = los cuatro autos; trabaja en Cabina_Barrera.
- Nav_Empleados y Nav_Estacionamiento (NavMeshBoundsVolume): el contratado camina con navegacion (la malla de
  navegacion se genera al jugar: RuntimeGeneration=Dynamic en DefaultEngine.ini).
Idempotente. Con -unattended abre el mapa, guarda y cierra. Informe: Docs/employee_parking.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Empleados"
SRC = project / "SourceAssets/Empleados"
ORIGIN = unreal.Vector(-3800, 9000, 400)
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
report = {"passed": False}
build = json.loads((SRC / "empleados_build.json").read_text(encoding="utf-8"))
COLORS = ["Rojo", "Azul", "Blanco", "Gris"]
PARKED = [(0, 1, "Azul"), (2, 1, "Blanco"), (3, 1, "Rojo"), (7, 1, "Gris"), (1, -1, "Rojo"), (5, -1, "Blanco"), (6, -1, "Azul")]
ARRIVAL_STALL = 5   # fila norte (Blender y +): el contratado estaciona aca


def local(x_m, y_m, z_m):
    """Blender metres of the floor -> world."""
    return ORIGIN + unreal.Vector(x_m * 100, -y_m * 100, z_m * 100)


def import_mesh(name):
    if lib.does_asset_exist(f"{DEST}/{name}") and not lib.delete_asset(f"{DEST}/{name}"):
        raise RuntimeError(f"No se pudo borrar {name}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.convert_scene = True
    data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{name}.fbx")
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(f"{DEST}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


try:
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if HEADLESS and not levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir el mapa")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    # fuera lo anterior (las mallas se borran y se importan de nuevo)
    for label, actor in list(by_label.items()):
        if label.startswith("Empleados_") or label in ("Ascensor_Empleados", "Nav_Empleados", "Nav_Estacionamiento"):
            actors.destroy_actor(actor)
            by_label.pop(label)
    spawn_point = by_label.get("Punto_Contratacion")
    if spawn_point:
        spawn_point.set_editor_property("car_meshes", [])
    meshes = {n: import_mesh(n) for n in ["SM_EmpleadosPiso", "SM_EmpleadosDecor"] + [f"SM_AutoEmpleado_{c}" for c in COLORS]}
    report["sizes_m"] = {n: [round(m.get_bounds().box_extent.x / 50, 1), round(m.get_bounds().box_extent.y / 50, 1)] for n, m in meshes.items()}
    if report["sizes_m"]["SM_EmpleadosPiso"][0] < 30:
        raise RuntimeError(f"El piso quedo chico: {report['sizes_m']}")

    def place(mesh, label, where, yaw=0.0, parent=None):
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, where, unreal.Rotator(0, 0, yaw))
        actor.set_actor_label(label)
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.set_folder_path("Empleados")
        if parent:
            actor.attach_to_actor(parent, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                                  unreal.AttachmentRule.KEEP_WORLD, False)
        return actor

    floor = place(meshes["SM_EmpleadosPiso"], "Empleados_Piso", ORIGIN)
    place(meshes["SM_EmpleadosDecor"], "Empleados_Decor", ORIGIN, parent=floor)
    stalls = build["stalls"]
    north = [s for s in stalls if s["side"] == 1]
    south = [s for s in stalls if s["side"] == -1]
    for index, side, color in PARKED:
        stall = (north if side == 1 else south)[index]
        # la trompa hacia adentro del cajon: fila norte (Blender +y) mira a -Y de Unreal
        place(meshes[f"SM_AutoEmpleado_{color}"], f"Empleados_Auto_{color}_{index}{'N' if side == 1 else 'S'}",
              local(stall["x"], stall["y"], 0.02), -90.0 if side == 1 else 90.0, parent=floor)

    # ascensor del piso 3
    source = by_label["Ascensor_Estacionamiento"]
    elevator = actors.duplicate_actor(source)
    elevator.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
    elevator.set_actor_label("Ascensor_Empleados")
    ex, ey, ez = build["elevator_m"]
    elevator.set_actor_location_and_rotation(local(ex, ey, ez), source.get_actor_rotation(), False, False)
    elevator.set_editor_property("stop_name", "EMPLEADOS")
    elevator.set_folder_path("Empleados")
    report["elevator"] = {"world": [round(v) for v in (elevator.get_actor_location().x, elevator.get_actor_location().y, elevator.get_actor_location().z)],
                          "yaw": round(elevator.get_actor_rotation().yaw), "source_z": round(source.get_actor_location().z)}

    # cartel pintado en el piso
    sign = actors.spawn_actor_from_class(unreal.TextRenderActor, local(5.1, 0.0, 0.03), unreal.Rotator(0, 90, 180))
    sign.set_actor_label("Empleados_Cartel")
    sign.set_folder_path("Empleados")
    text = sign.text_render
    text.set_text("EMPLEADOS")
    text.set_editor_property("world_size", 55.0)
    text.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    text.set_editor_property("vertical_alignment", unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    text.set_text_render_color(unreal.Color(r=240, g=240, b=235, a=255))
    sign.attach_to_actor(floor, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)

    # punto de llegada de los contratados
    if not spawn_point:
        spawn_point = actors.spawn_actor_from_class(unreal.FactoryWorkerSpawn, local(-29, 0, 0.02))
        spawn_point.set_actor_label("Punto_Contratacion")
    spawn_point.set_actor_location(local(-29, 0, 0.02), False, False)
    spawn_point.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    spawn_point.set_folder_path("Empleados")
    spawn_point.set_editor_property("car_meshes", [meshes[f"SM_AutoEmpleado_{c}"] for c in COLORS])
    booth = by_label.get("Cabina_Barrera")
    if booth:
        spawn_point.set_editor_property("workplace", booth)
    stall = north[ARRIVAL_STALL]
    route = spawn_point.get_editor_property("car_route")
    route.clear_spline_points(False)
    sx, sy = stall["x"], stall["y"]
    for x, y in ((-29, 0), (-18, 0), (sx - 5.0, -0.2), (sx - 1.2, 1.2), (sx - 0.1, sy - 1.2), (sx, sy)):
        route.add_spline_point(local(x, -y if False else y, 0.02), unreal.SplineCoordinateSpace.WORLD, False)
    route.update_spline()
    report["arrival_stall_world"] = [round(v) for v in (local(sx, sy, 0).x, local(sx, sy, 0).y)]

    # volumenes de navegacion
    def nav_volume(label, centre, size_m):
        vol = actors.spawn_actor_from_object(unreal.NavMeshBoundsVolume.static_class(), centre)
        if vol is None:
            raise RuntimeError("No se pudo crear el volumen de navegacion")
        vol.set_actor_label(label)
        vol.set_folder_path("Navegacion")
        vol.set_actor_scale3d(unreal.Vector(size_m[0] / 2.0, size_m[1] / 2.0, size_m[2] / 2.0))
        origin, extent = vol.get_actor_bounds(False)
        report[label] = {"centre": [round(origin.x), round(origin.y), round(origin.z)], "size_m": [round(extent.x / 50, 1), round(extent.y / 50, 1), round(extent.z / 50, 1)]}
        return vol

    nav_volume("Nav_Empleados", ORIGIN + unreal.Vector(0, 0, 150), (38, 30, 6))
    parking = by_label["Parking_Estacionamiento"]
    nav_volume("Nav_Estacionamiento", parking.get_actor_location() + unreal.Vector(0, 0, 200), (26, 32, 8))

    lib.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
finally:
    (project / "Docs/employee_parking.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
