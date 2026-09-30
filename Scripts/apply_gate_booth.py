"""Editor Python: cabina con barrera antes de la salida este del estacionamiento (28/09).

Importa SM_Cabina, SM_CabinaTecho, SM_BarreraPoste y SM_BarreraBrazo (SourceAssets/CabinaBarrera, de
author_gate_booth.py) en /Game/FactoryCtyco/Environments/CabinaBarrera y, si no existe, pone `Cabina_Barrera`
(AFactoryGateBarrier, carpeta Environment, enganchada a Parking_Estacionamiento): la cabina al norte
del carril del camion, 2,3 m antes de la puerta este, con la puerta hacia el estacionamiento; la
barrera cruza el carril. Si ya existe solo cambia las mallas y conserva su lugar.
Con -unattended abre el mapa, guarda y cierra; con el editor abierto no guarda el nivel.
Informe: Docs/gate_booth.json. Requiere FactoryCtycoRuntime con AFactoryGateBarrier instalado.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SOURCE = project / "SourceAssets/CabinaBarrera"
DEST = "/Game/FactoryCtyco/Environments/CabinaBarrera"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
LABEL = "Cabina_Barrera"
PIECES = ("SM_Cabina", "SM_CabinaTecho", "SM_BarreraPoste", "SM_BarreraBrazo")
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
# En cm, espacio del estacionamiento (Blender x, y -> Unreal 100x, -100y): cabina en (9, -2.5) m,
# poste en (8.6, -4.0) m con el brazo hacia el sur (+Y de Unreal) cruzando el carril (y -5.5).
BOOTH_AT = unreal.Vector(900, 250, 0)
POST_OFFSET, POST_YAW = unreal.Vector(-40, 150, 0), 90.0
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_mesh(name):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):  # reimportar encima deja colision vieja
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
    data.one_convex_hull_per_ucx = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / f"{name}.fbx")
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
    return mesh


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    cls = getattr(unreal, "FactoryGateBarrier", None)
    if cls is None:
        raise RuntimeError("Falta AFactoryGateBarrier: instalar FactoryCtycoRuntime (build_runtime_visuals.ps1 -Install)")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    gate = next((a for a in level if a.get_actor_label() == LABEL), None)
    if gate:
        for comp in ("booth", "roof", "post", "arm"):
            gate.get_editor_property(comp).set_static_mesh(None)
    meshes = {n: import_mesh(n) for n in PIECES}
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    created = gate is None
    if created:
        park = next(a for a in level if a.get_actor_label() == "Parking_Estacionamiento")
        spot = park.get_actor_transform().transform_location(BOOTH_AT)
        gate = actors.spawn_actor_from_class(cls, spot, park.get_actor_rotation())
        gate.set_actor_label(LABEL)
        gate.set_folder_path("Environment")
        gate.attach_to_actor(park, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                             unreal.AttachmentRule.KEEP_WORLD, False)
        post = gate.get_editor_property("post")
        post.set_relative_location_and_rotation(POST_OFFSET, unreal.Rotator(0, 0, POST_YAW), False, False)
    gate.modify()
    gate.get_editor_property("booth").set_static_mesh(meshes["SM_Cabina"])
    gate.get_editor_property("roof").set_static_mesh(meshes["SM_CabinaTecho"])
    gate.get_editor_property("post").set_static_mesh(meshes["SM_BarreraPoste"])
    gate.get_editor_property("arm").set_static_mesh(meshes["SM_BarreraBrazo"])
    sound = unreal.load_asset("/Game/FactoryCtyco/Environments/Ascensor2/S_Ascensor_Puerta")
    if sound:
        gate.set_editor_property("move_sound", sound)
    hulls = {n: unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(m)
             for n, m in meshes.items()}
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = gate.get_actor_location()
    report.update(passed=True, created=created, collisions=hulls, sound=bool(sound),
                  location=[round(loc.x), round(loc.y), round(loc.z)])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[GATE_BOOTH] {error}")
finally:
    (project / "Docs/gate_booth.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
