"""Editor Python (con L_FactoryDemo abierto): la oficina del usuario como piso nuevo, ADMINISTRACION (07/10).

- Importa SourceAssets/Oficina/SM_Oficina.fbx (author_oficina.py) en /Game/FactoryCtyco/Environments/Oficina, con sus
  materiales; choca con su propia malla (complex as simple). Borra el asset antes (reimportar encima lo dejaba al 1 %).
- `Oficina_Administracion` (StaticMeshActor, carpeta Oficina) en ORIGIN: un piso alto (11 m) en un lugar libre del
  mapa; los ascensores llevan con un fundido, asi que no hace falta que este encima de nada.
- `Ascensor_Oficina`: copia de Ascensor_Empleados (mismas piezas y sonidos) en el vano de la puerta de la oficina, con
  la puerta mirando adentro; aparece solo en el panel de los ascensores como ADMINISTRACION.
- `Escena_Oficina` (AFactorySceneZone, escena "Oficina"): solo se ve con el personaje adentro.
Si ya existen, la oficina conserva su lugar (solo se le cambia la malla) y no se tocan el ascensor ni la zona.
Guarda el nivel. Informe: Docs/oficina.json.
"""
import json
import math
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Oficina"
NAME = "SM_Oficina"
ORIGIN = unreal.Vector(1000, 6500, 1100)   # esquina del salon (origen del modelo), piso a z 1100
STOP = "ADMINISTRACIÓN"
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

try:
    build = json.loads((project / "SourceAssets/Oficina/oficina_build.json").read_text(encoding="utf-8"))
    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}
    office = by.get("Oficina_Administracion")
    if office:
        office.static_mesh_component.set_static_mesh(None)
    if lib.does_directory_exist(DEST):
        for old in lib.list_assets(DEST, recursive=False, include_folder=False):
            lib.delete_asset(old.split(".")[0])
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    data.generate_lightmap_u_vs = data.build_nanite = False
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Oficina/{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(f"{DEST}/{NAME}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    b = mesh.get_bounding_box()
    size = [round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)]
    want = [round((build["max_m"][i] - build["min_m"][i]) * 100) for i in range(3)]
    if abs(size[0] - want[0]) > 5:
        raise RuntimeError(f"La oficina mide {size} cm (se esperaba {want})")
    body = mesh.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(mesh)

    if office is None:
        office = actors.spawn_actor_from_class(unreal.StaticMeshActor, ORIGIN, unreal.Rotator())
        office.set_actor_label("Oficina_Administracion")
        office.set_folder_path("Oficina")
    office.static_mesh_component.set_static_mesh(mesh)
    office.static_mesh_component.set_collision_profile_name("BlockAll")
    base = office.get_actor_location()
    yaw = office.get_actor_rotation().yaw

    # el ascensor: afuera del vano de la puerta (pared del frente: y 0 .. 0,3 m en Unreal), puerta mirando a -Y
    gap = build["door_gap_x_m"]
    lift = by.get("Ascensor_Oficina")
    if lift is None or lift.get_editor_property("stop_name") != STOP:   # nuevo, o copia que quedo sin acomodar
        src = by["Ascensor_Empleados"]
        if lift is None:
            lift = actors.duplicate_actor(src, None, unreal.Vector(0, 0, 0))
        lift.set_actor_label("Ascensor_Oficina")
        lift.set_folder_path("Oficina")
        door_out = src.get_editor_property("door_outer_x")
        lx, ly = (gap[0] + gap[1]) / 2 * 100, 30 + door_out + 3
        c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        lift.set_actor_location(base + unreal.Vector(lx * c - ly * s_, lx * s_ + ly * c, 0), False, False)
        lift.set_actor_rotation(unreal.Rotator(0, 0, yaw - 90), False)
        lift.set_editor_property("stop_name", STOP)
        lift.set_editor_property("destination", src)

    # la escena: la oficina, sus anexos y el ascensor (con su pozo, que cuelga abajo)
    zone = by.get("Escena_Oficina")
    if zone is None:
        zone = actors.duplicate_actor(by["Escena_Laboratorio"], None, unreal.Vector(0, 0, 0))
        zone.set_actor_label("Escena_Oficina")
        zone.set_folder_path("Escenas")
        zone.set_editor_property("scene", "Oficina")
        o, e = office.get_actor_bounds(False)
        lo_, le_ = lift.get_actor_bounds(False)
        x0, x1 = min(o.x - e.x, lo_.x - le_.x) - 100, max(o.x + e.x, lo_.x + le_.x) + 100
        y0, y1 = min(o.y - e.y, lo_.y - le_.y) - 100, max(o.y + e.y, lo_.y + le_.y) + 100
        z0, z1 = base.z - 450, base.z + 500
        zone.set_actor_location(unreal.Vector((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), False, False)
        zone.box.set_box_extent(unreal.Vector((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2))

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    ll = lift.get_actor_location()
    zl = zone.get_actor_location()
    report.update(passed=True, oficina=[round(v) for v in base.to_tuple()], tamano_cm=size, triangulos=mesh.get_num_triangles(0),
                  materiales=len(mesh.static_materials),
                  ascensor={"lugar": [round(v) for v in ll.to_tuple()], "yaw": round(lift.get_actor_rotation().yaw),
                            "parada": lift.get_editor_property("stop_name")},
                  escena={"centro": [round(v) for v in zl.to_tuple()], "medio": [round(v) for v in zone.box.get_unscaled_box_extent().to_tuple()],
                          "oficina": str(unreal.FactorySceneZone.scene_of(office)), "ascensor": str(unreal.FactorySceneZone.scene_of(lift))})
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[OFICINA] " + report["error"])
finally:
    (project / "Docs/oficina.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
