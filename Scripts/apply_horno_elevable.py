"""Editor Python: horno de fundicion elevable (01/10). Requiere FactoryCtycoRuntime con AFactoryRaisedProp.

- Importa SourceAssets/HornoFundicion/SM_HornoFundicion_Base.fbx y _Cuerpo.fbx (author_horno_base.py) en
  /Game/FactoryCtyco/Environments/HornoFundicion (borra los assets antes: reimportar encima los dejaba al 1 %), con el
  material del horno (Material_0) y una caja de colision cada una.
- Cambia el actor `Horno_Fundicion` (StaticMeshActor) por un FactoryRaisedProp con el mismo nombre, carpeta y
  transformacion: Elevation sube el cuerpo y estira la base, sin patas. Se puede volver a correr (lo deja igual).
Sin editor abre el mapa, guarda y cierra. Informe: Docs/horno_elevable.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/HornoFundicion"
DEST = "/Game/FactoryCtyco/Environments/HornoFundicion"
MATERIAL = f"{DEST}/Material_0"
LABEL = "Horno_Fundicion"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_mesh(name):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{name}.fbx")
    task.destination_path, task.destination_name = DEST, name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    material = unreal.load_asset(MATERIAL)
    for i in range(len(mesh.static_materials)):
        mesh.set_material(i, material)
    meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    meshes.remove_collisions(mesh)
    meshes.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
    lib.save_loaded_asset(mesh, False)
    box = mesh.get_bounding_box()
    report[name] = {"min_cm": [round(v, 1) for v in box.min.to_tuple()], "max_cm": [round(v, 1) for v in box.max.to_tuple()]}
    return mesh


try:
    if HEADLESS:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
    base = import_mesh("SM_HornoFundicion_Base")
    body = import_mesh("SM_HornoFundicion_Cuerpo")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = [a for a in actors.get_all_level_actors() if a.get_actor_label() == LABEL]
    if len(old) != 1:
        raise RuntimeError(f"Se esperaba un {LABEL}, hay {len(old)}")
    old = old[0]
    if isinstance(old, unreal.FactoryRaisedProp):
        prop = old
    else:
        transform, folder = old.get_actor_transform(), old.get_folder_path()
        prop = actors.spawn_actor_from_class(unreal.FactoryRaisedProp, transform.translation, transform.rotation.rotator())
        prop.set_actor_scale3d(transform.scale3d)
        prop.set_folder_path(folder)
        actors.destroy_actor(old)
        prop.set_actor_label(LABEL)
    prop.set_editor_property("body_mesh", body)
    prop.set_editor_property("base_mesh", base)
    prop.refresh()
    loc = prop.get_actor_location()
    report.update(passed=True, actor=prop.get_actor_label(), cls=prop.get_class().get_name(), folder=str(prop.get_folder_path()),
                  location=[round(v, 1) for v in loc.to_tuple()], scale=[round(v, 3) for v in prop.get_actor_scale3d().to_tuple()],
                  elevation=prop.get_editor_property("elevation"))
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[HORNO_ELEVABLE] " + report["error"])
finally:
    (project / "Docs/horno_elevable.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
