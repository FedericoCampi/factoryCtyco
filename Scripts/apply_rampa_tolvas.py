"""Editor Python (con L_FactoryDemo abierto): rampa con plataforma frente a las tolvas y el camion volcador (08/10).

1. Importa SourceAssets/RampaTolvas/SM_RampaTolvas.fbx (author_rampa_tolvas.py) en Environments/RampaTolvas (choca con su
   propia malla) y SourceAssets/Camion/camion_volcador.fbx (author_truck_dump.py) como SK_CamionVolcador en
   Environments/Camion/Volcador, con los materiales de SK_Camion. Borra los assets antes (reimportar encima achicaba).
2. `Rampa_Tolvas` (carpeta Muelles): pegada al lado largo de Tolvas_Gemelas que da al patio (+Y del actor), frente a la
   tolva HOPPER (-1 oeste, +1 este), apoyada en el piso; la rampa baja alejandose de la tolva.
3. `Cajon_Volcado` (AFactoryTruckBay, bDump): el eje trasero del camion estacionado a 60 cm del borde (la caja asoma
   40 cm sobre la boca). Su maniobra a mano (bAutoManeuver apagado): recta por la plataforma y la rampa (tramos lineales,
   asi el camion sube por la superficie) y un cuarto de circulo hasta la linea de Camion_Recorrido, al este.
4. `Camion_Volcador` (AFactoryVehiclePath, bDumpTruck): copia los ajustes de Camion_Recorrido y recorre su linea
   (LeadPath), con SK_CamionVolcador y una carga de SM_Cuarzo; sale StartDelay segundos despues.
Si ya existen, la rampa y el cajon se rehacen en su lugar calculado; el camion conserva sus ajustes de volcado.
Informe: Docs/rampa_tolvas.json.
"""
import json
import math
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RAMP_DIR = "/Game/FactoryCtyco/Environments/RampaTolvas"
TRUCK_DIR = "/Game/FactoryCtyco/Environments/Camion/Volcador"
HOPPER = 1              # tolva del este (+X del actor de las tolvas)
HOPPER_X = 150.0        # centro de cada tolva desde el centro del actor (cm)
HOPPER_FACE = 136.0     # su lado largo (cara +Y, con el borde de la boca)
HOPPER_RIM = 360.0      # alto de la boca sobre la base del actor
GAP = 10.0              # entre la tolva y la plataforma
AXLE_FROM_EDGE = 60.0   # eje trasero del camion estacionado desde el borde de la plataforma
APPROACH = 50.0         # recta en el piso antes de la rampa, y el radio de la curva hasta la linea (cm)
START_DELAY = 14.0
build = json.loads((project / "SourceAssets/RampaTolvas/rampa_tolvas_build.json").read_text(encoding="utf-8"))
HEIGHT, PLATFORM, RAMP = build["height_m"] * 100, build["platform_m"] * 100, build["ramp_m"] * 100
report = {"passed": False}


def clear_dir(dest):
    if lib.does_directory_exist(dest):
        for old in lib.list_assets(dest, recursive=False, include_folder=False):
            if not lib.delete_asset(old.split(".")[0]):
                raise RuntimeError(f"No se pudo borrar {old}")


def import_fbx(filename, dest, name, skeletal):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = skeletal
    options.import_materials = not skeletal       # el volcador usa los materiales del camion
    options.import_textures = False
    options.import_animations = False
    options.create_physics_asset = skeletal   # el personaje choca con el camion (08/10)
    if skeletal:
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        data = options.skeletal_mesh_import_data
    else:
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        data = options.static_mesh_import_data
        data.combine_meshes, data.auto_generate_collision = True, False
        data.generate_lightmap_u_vs = data.build_nanite = False
    options.original_import_type = options.mesh_type_to_import
    data.convert_scene = data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path, task.destination_name = dest, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(dest, only_if_is_dirty=True, recursive=True)
    asset = unreal.load_asset(f"{dest}/{name}")
    if asset is None:
        raise RuntimeError(f"No se importo {name}")
    return asset


def find(label, cls=None):
    return next((a for a in actors.get_all_level_actors() if a.get_actor_label() == label and (cls is None or isinstance(a, cls))), None)


def floor_z(world, x, y, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 1500), unreal.Vector(x, y, -500),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
    return hit.to_tuple()[4].z if hit else None


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    hoppers = find("Tolvas_Gemelas")
    line_owner = find("Camion_Recorrido", unreal.FactoryVehiclePath)
    model = find("Camion_Recorrido", unreal.FactoryVehiclePath)
    if not hoppers or not line_owner:
        raise RuntimeError("Faltan Tolvas_Gemelas o Camion_Recorrido")
    old_ramp, old_bay, truck = find("Rampa_Tolvas"), find("Cajon_Volcado"), find("Camion_Volcador")

    # 1. assets (sin actores que los usen mientras se borran)
    if old_ramp:
        old_ramp.static_mesh_component.set_static_mesh(None)
    if truck:
        truck.set_editor_property("vehicle_mesh", None)
    clear_dir(RAMP_DIR)
    ramp_mesh = import_fbx(project / "SourceAssets/RampaTolvas/SM_RampaTolvas.fbx", RAMP_DIR, "SM_RampaTolvas", False)
    body = ramp_mesh.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    ramp_mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(ramp_mesh)
    clear_dir(TRUCK_DIR)
    dump_mesh = import_fbx(project / "SourceAssets/Camion/camion_volcador.fbx", TRUCK_DIR, "SK_CamionVolcador", True)
    base = unreal.load_asset("/Game/FactoryCtyco/Environments/Camion/SK_Camion")
    by_slot = {m.get_editor_property("material_slot_name"): m.get_editor_property("material_interface") for m in base.materials}
    mats = dump_mesh.materials
    for i, m in enumerate(mats):   # cada elemento es una copia: se vuelve a poner en la lista
        slot = m.get_editor_property("material_slot_name")
        if slot in by_slot:
            m.set_editor_property("material_interface", by_slot[slot])
            mats[i] = m
    dump_mesh.set_editor_property("materials", mats)
    lib.save_loaded_asset(dump_mesh)

    # 2. rampa: el borde de la plataforma contra la cara +Y de la tolva, la rampa hacia +Y del actor de las tolvas
    xf = hoppers.get_actor_transform()
    edge = xf.transform_location(unreal.Vector(HOPPER * HOPPER_X, HOPPER_FACE + GAP, 0))
    yaw = hoppers.get_actor_rotation().yaw + 90.0
    ground = floor_z(world, edge.x + 300 * math.cos(math.radians(yaw)), edge.y + 300 * math.sin(math.radians(yaw)),
                     [hoppers] + ([old_ramp] if old_ramp else []))
    rim = hoppers.get_actor_location().z + HOPPER_RIM * hoppers.get_actor_scale3d().z
    if old_ramp:
        actors.destroy_actor(old_ramp)
    ramp = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(edge.x, edge.y, ground), unreal.Rotator(0, 0, yaw))
    ramp.set_actor_label("Rampa_Tolvas")
    ramp.set_folder_path("Muelles")
    ramp.static_mesh_component.set_static_mesh(ramp_mesh)
    ramp.static_mesh_component.set_collision_profile_name("BlockAll")
    rxf = ramp.get_actor_transform()
    report["rampa"] = {"lugar": [round(v) for v in ramp.get_actor_location().to_tuple()], "giro": round(yaw, 1),
                       "piso_z": round(ground, 1), "plataforma_z": round(ground + HEIGHT, 1), "boca_tolva_z": round(rim, 1),
                       "borde_caja_sobre_boca_cm": round(ground + HEIGHT + 80 - rim, 1)}

    # 3. cajon de volcado y su maniobra
    if old_bay:
        actors.destroy_actor(old_bay)
    bay_loc = rxf.transform_location(unreal.Vector(AXLE_FROM_EDGE, 0, HEIGHT))
    bay = actors.spawn_actor_from_class(unreal.FactoryTruckBay, bay_loc, unreal.Rotator(0, 0, yaw))
    bay.set_actor_label("Cajon_Volcado")
    bay.set_folder_path("Muelles")
    bay.set_editor_property("auto_maneuver", False)
    bay.set_editor_property("dump", True)
    bay.set_editor_property("line", line_owner)
    end = PLATFORM + RAMP
    pts = [rxf.transform_location(unreal.Vector(x, 0, z)) for x, z in
           ((AXLE_FROM_EDGE, HEIGHT), (PLATFORM, HEIGHT), (end, 0.0), (end + APPROACH, 0.0))]
    # cuarto de circulo: desde A (mirando a +X de la rampa) hasta un punto J de la linea donde la linea va de costado
    # (+-Y de la rampa); J tiene que quedar a R hacia adelante y R de costado de A
    road = line_owner.get_editor_property("path")
    length = road.get_spline_length()
    A = pts[-1]
    best = None
    for i in range(int(length / 5)):
        d = i * 5.0
        J = road.get_location_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
        local = rxf.inverse_transform_location(J)
        fwd, side = local.x - (end + APPROACH), local.y
        # el final de la curva va de costado hacia el lado de J: la linea tiene que ir para ese mismo lado (el camion
        # llega por la linea, pasa y retrocede por la curva)
        along = unreal.MathLibrary.inverse_transform_direction(rxf, road.get_direction_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD))
        if fwd > 300 and abs(side) > 300 and along.y * side > 0.9 * abs(side):
            err = abs(fwd - abs(side))
            if best is None or err < best[0]:
                best = (err, d, J, fwd, side)
    if best is None or best[0] > 40:
        raise RuntimeError(f"La curva no llega a la linea (mejor: {best})")
    _, join_d, J, fwd, side = best
    R = (fwd + abs(side)) / 2
    sgn = 1 if side > 0 else -1
    arc = []
    for k in range(1, 7):
        phi = math.radians(15 * k)
        lx = end + APPROACH + R * math.sin(phi)
        ly = sgn * R * (1 - math.cos(phi))
        z = rxf.inverse_transform_location(J).z * (k / 6)
        arc.append(rxf.transform_location(unreal.Vector(lx, ly, z)))
    arc[-1] = J
    spline = bay.get_editor_property("maneuver")
    spline.clear_spline_points(False)
    for p in pts + arc:
        spline.add_spline_point(p, unreal.SplineCoordinateSpace.WORLD, False)
    for i in range(3):
        spline.set_spline_point_type(i, unreal.SplinePointType.LINEAR, False)
    step = R * math.radians(15)
    fwd_dir = unreal.MathLibrary.transform_direction(rxf, unreal.Vector(1, 0, 0))
    spline.set_tangent_at_spline_point(3, fwd_dir * step, unreal.SplineCoordinateSpace.WORLD, False)
    for k in range(1, 7):
        phi = math.radians(15 * k)
        t = unreal.MathLibrary.transform_direction(rxf, unreal.Vector(math.cos(phi), sgn * math.sin(phi), 0)) * step
        if k == 6:
            t = road.get_direction_at_distance_along_spline(join_d, unreal.SplineCoordinateSpace.WORLD) * step
        spline.set_spline_point_type(3 + k, unreal.SplinePointType.CURVE_CUSTOM_TANGENT, False)
        spline.set_tangent_at_spline_point(3 + k, t, unreal.SplineCoordinateSpace.WORLD, False)
    spline.update_spline()
    report["cajon"] = {"lugar": [round(v) for v in bay_loc.to_tuple()], "maniobra_cm": round(spline.get_spline_length()),
                       "radio_curva_cm": round(R), "union_linea": [round(v) for v in J.to_tuple()],
                       "union_a_cm_de_la_linea": round(best[0], 1)}

    # 4. camion volcador: los ajustes de Camion_Recorrido, en su linea
    if truck is None:
        truck = actors.spawn_actor_from_class(unreal.FactoryVehiclePath, line_owner.get_actor_location(), unreal.Rotator())
        truck.set_actor_label("Camion_Volcador")
        truck.set_folder_path("Environment")
        for prop in ("rear_door_mesh", "rear_slat_mesh", "rear_bottom_mesh", "rear_door_top", "rear_door_height", "rear_header",
                     "wrap_mesh", "wrap_center", "cargo_floor", "cargo_front_x", "cargo_back_x", "speed", "front_length",
                     "rear_length", "wheelbase", "front_wheel_radius", "rear_wheel_radius", "max_steer", "follow_gap",
                     "stop_gap", "braking", "acceleration", "door_seconds"):
            truck.set_editor_property(prop, model.get_editor_property(prop))
        for comp in ("wrap_door", "wrap_side"):
            src, dst = model.get_editor_property(comp), truck.get_editor_property(comp)
            for i in range(src.get_num_materials()):
                dst.set_material(i, src.get_material(i))
        truck.set_editor_property("start_delay", START_DELAY)
    truck.set_editor_property("lead_path", line_owner)
    truck.set_editor_property("dump_truck", True)
    truck.set_editor_property("load_mesh", unreal.load_asset("/Game/FactoryCtyco/Factory/Models/Cuarzo/SM_Cuarzo"))
    truck.set_editor_property("vehicle_mesh", dump_mesh)
    report["camion"] = {"actor": truck.get_actor_label(), "malla": dump_mesh.get_path_name().split(".")[0],
                        "huesos": dump_mesh.skeleton.get_path_name() if dump_mesh.skeleton else None,
                        "carga": truck.get_editor_property("load_pieces"), "sale_a_los_s": truck.get_editor_property("start_delay"),
                        "escena": str(unreal.FactorySceneZone.scene_of(ramp))}
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = abs(report["rampa"]["borde_caja_sobre_boca_cm"] - 10) < 15 and report["camion"]["escena"] == "Despacho"
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[RAMPA_TOLVAS] " + report["error"])
(project / "Docs/rampa_tolvas.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
