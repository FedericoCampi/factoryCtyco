"""Editor Python (con L_FactoryDemo abierto, sirve con el editor abierto): pedidos del 30/09.

1. SM_EmpleadosEscena de nuevo desde empleados_escena.fbx (author_employee_scene.py): "Dock wall fill" ya no se pisa
   con "Nave cut wall", que parpadeaba detras de los asientos de la recepcion. Borra el asset y lo importa limpio
   (reimportar encima lo dejaba al 1 %), con las mismas opciones que apply_employee_scene.py.
2. Puerta_Recepcion se abre hacia adentro de la sala (OpenYaw positivo). No llega a 90 grados: la maceta de la
   entrada esta pegada a la bisagra y la hoja la atravesaria.
3. Guia_Mision, paso 1: la flecha va sobre Ascensor_Empleados en vez de sobre la puerta de la sala.
4. Cintas de carga: el camion carga en la cinta que sigue derecho desde Cinta_Carga3 (Cinta_Carga4). Cinta_Carga2 y
   Cinta_Carga (el tramo en L) pasan al grupo bloqueado Camion2, junto con el segundo camion.
Guarda el nivel. Informe: Docs/fixes_2026_09_30.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MESH = "/Game/FactoryCtyco/Environments/EmpleadosEscena/SM_EmpleadosEscena"
DOOR_OPEN_YAW = 60.0
LOCKED, FILLER = "Bloqueado", "Relleno"
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def import_scene_mesh():
    build = json.loads((project / "SourceAssets/EmpleadosEscena/empleados_escena_build.json").read_text(encoding="utf-8"))
    users = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)
             and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_path_name().split(".")[0] == MESH]
    if not users:
        raise RuntimeError("Ningun actor usa SM_EmpleadosEscena")
    old = unreal.load_asset(MESH).get_bounding_box()
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    if not lib.delete_asset(MESH):
        raise RuntimeError("No se pudo borrar SM_EmpleadosEscena")
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
    task.filename = str(project / "SourceAssets/EmpleadosEscena/empleados_escena.fbx")
    task.destination_path, task.destination_name = MESH.rsplit("/", 1)
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(MESH)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo SM_EmpleadosEscena")
    for a in users:
        a.static_mesh_component.set_static_mesh(mesh)
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    new = mesh.get_bounding_box()
    got = [new.min.x, new.min.y, new.min.z, new.max.x, new.max.y, new.max.z]
    was = [old.min.x, old.min.y, old.min.z, old.max.x, old.max.y, old.max.z]
    if hulls != build["ucx"] or any(abs(a - b) > 2 for a, b in zip(got, was)):
        raise RuntimeError(f"Malla distinta: {hulls} colisiones (se esperaban {build['ucx']}), medidas {got} vs {was}")
    return {"actors": [a.get_actor_label() for a in users], "hulls": hulls, "triangles": mesh.get_num_triangles(0)}


def set_group(actor, group, locked):
    """Pone o saca un actor de un grupo bloqueado (UFactoryUnlockSubsystem) y lo cambia de carpeta."""
    tags = [t for t in actor.tags if str(t) not in (LOCKED, group)]
    if locked:
        tags += [unreal.Name(LOCKED), unreal.Name(group)]
    actor.tags = tags
    actor.set_folder_path(f"Bloqueado/{group}" if locked else "Environment")


try:
    report["dirty_before"] = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    report["scene_mesh"] = import_scene_mesh()

    door = by_label["Puerta_Recepcion"]
    door.set_editor_property("open_yaw", DOOR_OPEN_YAW)
    report["door_open_yaw"] = door.get_editor_property("open_yaw")

    guide, lift = by_label["Guia_Mision"], by_label["Ascensor_Empleados"]
    steps = list(guide.get_editor_property("steps"))
    steps[0].set_editor_property("arrow_target", lift)
    guide.set_editor_property("steps", steps)
    report["guide_step1_arrow"] = guide.get_editor_property("steps")[0].get_editor_property("arrow_target").get_actor_label()

    set_group(by_label["Cinta_Carga4"], "Camion2", False)
    for label in ("Cinta_Carga2", "Cinta_Carga"):
        set_group(by_label[label], "Camion2", True)
    report["belts"] = {l: [str(t) for t in by_label[l].tags] for l in ("Cinta_Carga", "Cinta_Carga2", "Cinta_Carga3", "Cinta_Carga4")}

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception as error:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error(f"[FIXES_0930] {error}")
(project / "Docs/fixes_2026_09_30.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
