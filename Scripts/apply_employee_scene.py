"""Editor Python: la escena del usuario reemplaza al estacionamiento de empleados (piso 3) en L_FactoryDemo (29/09).

Importa SourceAssets/EmpleadosEscena/empleados_escena.fbx (author_employee_scene.py) como
/Game/FactoryCtyco/Environments/EmpleadosEscena/SM_EmpleadosEscena (borra el asset antes: reimportar encima lo dejaba al 1 %) y:
- saca del nivel el piso anterior: Empleados_Piso, Empleados_Decor, los autos Empleados_Auto_* y Empleados_Cartel
  (las mallas viejas quedan en /Game/FactoryCtyco/Environments/Empleados);
- coloca Empleados_Escena en ORIGIN (el mismo lugar y altura que el piso anterior) con cinco autos estacionados (el auto del usuario en colores);
- la sala de recepcion del usuario, Recepcion_Sala (SourceAssets/Recepcion, author_reception_room.py), contra la
  fachada con su puerta de entrada sobre la plataforma (Puerta_Recepcion, AFactoryAutoDoor: se abre sola hacia afuera); pone Ascensor_Empleados detras de la puerta doble de la sala;
  crea Guia_PuertaAscensor (donde apunta la flecha de la guia: sobre la puerta de la sala); mueve Punto_Contratacion y
  su CarRoute (entra por la
  calle y la barrera levantada y estaciona en el cajón F4, junto al ascensor), Nav_Empleados y PlayerStart_Robot1.
El estacionamiento de despacho (Parking_Estacionamiento) no se toca.
Con -unattended abre el mapa, guarda y cierra. Informe: Docs/employee_scene.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/EmpleadosEscena"
NAME = "SM_EmpleadosEscena"
CAR_SRC = project / "SourceAssets/AutoEmpleado"   # autos del usuario en colores (author_employee_cars.py)
COLORS = ("Azul", "Rojo", "Blanco", "Gris", "Verde")
SRC = project / "SourceAssets/EmpleadosEscena"
ORIGIN = unreal.Vector(-3800, 9000, 400)
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
build = json.loads((SRC / "empleados_escena_build.json").read_text(encoding="utf-8"))
report = {"passed": False}
PARKED = [("F0", "Azul"), ("F1", "Blanco"), ("F3", "Rojo"), ("R0", "Gris"), ("R3", "Verde")]
ARRIVAL = "F4"
START = (-0.3, -2.2)          # donde aparece el gerente: en la calle entre las dos filas, mirando al ascensor


def local(x_m, y_m, z_m):
    """Blender metres of the scene -> world."""
    return ORIGIN + unreal.Vector(x_m * 100, -y_m * 100, z_m * 100)


def rounded(v):
    return [round(v.x), round(v.y), round(v.z)]


def import_scene(name=NAME, filename="empleados_escena.fbx", folder=None):
    path = f"{DEST}/{name}"
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
    task.filename = str((folder or SRC) / filename)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    if name != NAME:
        return mesh
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    extent = mesh.get_bounds().box_extent
    report["mesh"] = {"hulls": hulls, "expected_hulls": build["ucx"], "size_m": [round(extent.x / 50, 1), round(extent.y / 50, 1), round(extent.z / 50, 1)]}
    if hulls != build["ucx"]:
        raise RuntimeError(f"Se esperaban {build['ucx']} colisiones; hay {hulls}")
    if extent.x < 1500:   # el pasto de alrededor mide 66 m
        raise RuntimeError(f"La escena quedo chica: {report['mesh']}")
    return mesh


try:
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if HEADLESS and not levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir el mapa")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}

    # fuera el piso anterior (y una escena aplicada antes, para que sea idempotente)
    gone = [label for label in by_label if label.startswith(("Empleados_", "Recepcion", "Puerta_Recepcion"))]
    for label in gone:
        actors.destroy_actor(by_label.pop(label))
    report["removed"] = sorted(gone)
    mesh = import_scene()

    def place(static_mesh, label, where, yaw=0.0, parent=None):
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, where, unreal.Rotator(0, 0, yaw))
        actor.set_actor_label(label)
        actor.static_mesh_component.set_static_mesh(static_mesh)
        actor.set_folder_path("Empleados")
        if parent:
            actor.attach_to_actor(parent, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                                  unreal.AttachmentRule.KEEP_WORLD, False)
        return actor

    scene = place(mesh, "Empleados_Escena", ORIGIN)
    scene.static_mesh_component.set_collision_profile_name("BlockAll")
    stalls = {s["id"]: s for s in build["stalls"]}
    cars = {c: import_scene(f"SM_Auto_{c}", f"SM_Auto_{c}.fbx", CAR_SRC) for c in COLORS}
    for stall_id, color in PARKED:
        s = stalls[stall_id]
        # los autos miran a +X; la trompa va hacia el tope del cajon
        place(cars[color], f"Empleados_Auto_{color}_{stall_id}", local(s["x"], s["y"], 0.02), 90.0 if s["nose"] < 0 else -90.0, scene)
    report["parked"] = [p[0] for p in PARKED]

    # recepcion: la sala del usuario contra la fachada, con su puerta de entrada sobre la plataforma
    rec = build["reception"]
    room_mesh = import_scene("SM_RecepcionSala", "recepcion_sala.fbx", project / "SourceAssets/Recepcion")
    room_build = json.loads((project / "SourceAssets/Recepcion/recepcion_build.json").read_text(encoding="utf-8"))
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(room_mesh)
    if hulls != room_build["ucx"]:
        raise RuntimeError(f"La sala tiene {hulls} colisiones; se esperaban {room_build['ucx']}")
    hall_room = place(room_mesh, "Recepcion_Sala", local(*rec["room_m"]), rec["room_yaw_unreal"], scene)
    hall_room.static_mesh_component.set_collision_profile_name("BlockAll")
    # su puerta de entrada: la hoja del usuario, que se abre sola hacia afuera (hacia la plataforma)
    leaf_info = room_build["entry_leaf"]
    hx, hy, _ = leaf_info["hinge_m"]
    rx0, ry0, rz0 = rec["room_m"]
    door = actors.spawn_actor_from_class(unreal.FactoryAutoDoor, local(rx0 + hy, ry0 - hx, rz0), unreal.Rotator(0, 0, 0))
    door.set_actor_label("Puerta_Recepcion")
    door.set_folder_path("Empleados")
    door.get_editor_property("leaf").set_static_mesh(import_scene("SM_PuertaRecepcionSala", "puerta_recepcion_sala.fbx", project / "SourceAssets/Recepcion"))
    door.set_editor_property("width", leaf_info["width_m"] * 100)
    door.set_editor_property("open_yaw", 60.0)   # 30/09: hacia adentro (-Y); a mas de ~70 la hoja cruza la maceta
    door.attach_to_actor(scene, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    for old in ("SM_PuertaRecepcion", "SM_RecepcionTecho"):   # de la version con pasillo
        if lib.does_asset_exist(f"{DEST}/{old}"):
            lib.delete_asset(f"{DEST}/{old}")
    report["reception"] = {"sala": rounded(hall_room.get_actor_location()), "sala_hulls": hulls, "puerta": rounded(door.get_actor_location()),
                           "entrada": rounded(local(*rec["entry_door_m"]))}

    # ascensor a un costado de la recepcion, con la entrada hacia la sala
    elevator = by_label["Ascensor_Empleados"]
    ex, ey, ez = build["elevator"]["centre_m"]
    elevator.set_actor_location_and_rotation(local(ex, ey, ez), unreal.Rotator(0, 0, build["elevator"]["yaw_unreal"]), False, False)
    # los empleados entran a la sala por la ruta del usuario (build.json de la recepcion): la navegacion no cruza
    # entre los muebles de la entrada. Puntos en metros de la sala: (x hacia la puerta de entrada, y hacia la puerta doble).
    rx0, ry0, rz0 = rec["room_m"]
    room_point = lambda x, y: local(rx0 + y, ry0 - x, rz0 + .02)
    approach = [room_point(4.4, 2.3), room_point(4.4, 0.5), room_point(0.4, 0.5)]
    elevator.set_editor_property("approach", [elevator.get_actor_transform().inverse_transform_location(w) for w in approach])
    report["elevator"] = {"world": rounded(elevator.get_actor_location()), "yaw": round(elevator.get_actor_rotation().yaw),
                          "approach": [rounded(w) for w in approach]}
    # la flecha de la guia apunta a la puerta (el ascensor queda bajo el techo de la nave)
    marker = by_label.get("Guia_PuertaAscensor") or actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(0, 0, 0))
    marker.set_actor_label("Guia_PuertaAscensor")
    marker.set_folder_path("Gameplay")
    door_x, door_y, door_z = rec["entry_door_m"]
    marker.set_actor_location(local(door_x, door_y - .4, door_z + 2.4), False, False)   # sobre la puerta de la sala
    report["door_marker"] = rounded(marker.get_actor_location())

    # llegada de los contratados: por la calle, la barrera levantada y el pasillo, hasta el cajon F4
    spawn = by_label["Punto_Contratacion"]
    road_y = sum(build["road_y_m"]) / 2
    gate_x = sum(build["entrance_x_m"]) / 2
    arrival = stalls[ARRIVAL]
    spawn.set_actor_location(local(-32.0, road_y, 0.0), False, False)
    spawn.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    spawn.set_editor_property("car_meshes", [cars[c] for c in COLORS])   # el contratado llega en uno de estos
    route = spawn.get_editor_property("car_route")
    route.clear_spline_points(False)
    for x, y in ((-32.0, road_y), (-14.0, road_y), (gate_x, road_y + 2.5), (gate_x, -11.5), (gate_x, -5.0),
                 (gate_x + 2.5, -2.2), (arrival["x"] - 3.0, -2.2), (arrival["x"], -4.6), (arrival["x"], arrival["y"])):
        route.add_spline_point(local(x, y, 0.02), unreal.SplineCoordinateSpace.WORLD, False)
    route.update_spline()
    report["arrival"] = {"stall": ARRIVAL, "world": rounded(local(arrival["x"], arrival["y"], 0))}

    # navegacion: el patio entero con la plataforma y la recepcion
    nav = by_label.get("Nav_Empleados")
    if nav:
        nav.set_actor_location(local(0.0, 4.7, 2.0), False, False)
        nav.set_actor_scale3d(unreal.Vector(13.0, 17.2, 4.0))   # 26 x 34 x 8 m: el patio y la recepcion de atras
        origin, extent = nav.get_actor_bounds(False)
        report["nav"] = {"centre": rounded(origin), "size_m": [round(extent.x / 50, 1), round(extent.y / 50, 1), round(extent.z / 50, 1)]}

    # el gerente aparece en el patio, mirando al ascensor
    start = by_label.get("PlayerStart_Robot1")
    if start:
        start.set_actor_location(local(START[0], START[1], 1.0), False, False)
        start.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
        report["player_start"] = rounded(start.get_actor_location())

    lib.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
finally:
    (project / "Docs/employee_scene.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
