"""Editor Python: cinta de esquina en L_FactoryDemo (30/09). Requiere FactoryCtycoRuntime con TurnDegrees (instalado).

Importa SourceAssets/CintaEsquina/SM_CintaEsquina.fbx (author_belt_corner.py) en /Game/FactoryCtyco/Environments/CintaEsquina
(borra el asset antes: reimportar encima lo dejaba al 1 %) y crea, si no existe, `Cinta_Esquina` (AFactoryLoadingBelt,
carpeta Environment, enganchada al estacionamiento) con la curva: Length = largo del eje de la curva, TurnDegrees -90,
y la velocidad, separacion y alcance de Cinta_Carga3. Queda suelta, lejos de las otras cintas, para que el usuario
la ubique: se engancha sola cuando su punta de entrada queda en la salida de otra cinta (y al reves).
Si ya existe solo le cambia la malla y el largo. Sin editor abre el mapa, guarda y cierra; con el editor abierto no
guarda el nivel. Informe: Docs/belt_corner.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/CintaEsquina"
DEST, NAME, LABEL = "/Game/FactoryCtyco/Environments/CintaEsquina", "SM_CintaEsquina", "Cinta_Esquina"
SPOT = unreal.Vector(-3500, -1250, 10)   # estacionamiento de despacho, lejos de las cintas de carga
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
build = json.loads((SRC / "cinta_esquina_build.json").read_text(encoding="utf-8"))
report = {"passed": False}


def import_mesh(users):
    path = f"{DEST}/{NAME}"
    for a in users:
        a.belt.set_static_mesh(None)
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
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo la esquina")
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != build["ucx"]:
        raise RuntimeError(f"Se esperaban {build['ucx']} colisiones; hay {hulls}")
    return mesh


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    corner = level.get(LABEL)
    mesh = import_mesh([corner] if corner else [])
    if corner is None:
        model = level["Cinta_Carga3"]
        corner = actors.spawn_actor_from_class(unreal.FactoryLoadingBelt, SPOT, unreal.Rotator(0, 0, 0))
        corner.set_actor_label(LABEL)
        corner.set_folder_path("Environment")
        corner.attach_to_actor(level["Parking_Estacionamiento"], "", unreal.AttachmentRule.KEEP_WORLD,
                               unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
        for prop in ("speed", "box_spacing", "interaction_radius", "roller_speed", "link_reach", "crossing_zone"):
            corner.set_editor_property(prop, model.get_editor_property(prop))
    corner.modify()
    corner.belt.set_static_mesh(mesh)
    corner.set_editor_property("length", build["length_cm"])
    corner.set_editor_property("turn_degrees", float(build["turn_degrees_unreal"]))
    corner.set_editor_property("deck_height", build["deck_m"] * 100)
    # suelta: lejos de las puntas de las otras cintas (si no, se enlazaria sola)
    belts = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryLoadingBelt) and a != corner]
    ends = [corner.get_actor_location(), corner.get_actor_transform().transform_location(
        unreal.Vector(build["exit_unreal_cm"][0], build["exit_unreal_cm"][1], 0))]
    near = min(((e.x - b.get_actor_location().x) ** 2 + (e.y - b.get_actor_location().y) ** 2) ** 0.5 for e in ends for b in belts)
    loc = corner.get_actor_location()
    report.update(mesh=mesh.get_path_name(), actor=LABEL, location=[round(loc.x), round(loc.y), round(loc.z)],
                  length_cm=build["length_cm"], turn_degrees=corner.get_editor_property("turn_degrees"),
                  nearest_other_belt_cm=round(near), triangles=mesh.get_num_triangles(0),
                  materials=[str(m.material_slot_name) for m in mesh.static_materials])
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[BELT_CORNER] " + report["error"])
finally:
    (project / "Docs/belt_corner.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
