"""Editor Python (04/10): curva de la cinta de despacho.

Importa SourceAssets/CintaCargaCurva/SM_CintaCargaCurva.fbx (author_loading_belt_curve.py: la cinta de rodillos de
SM_CintaCarga doblada 90 grados, con el radio de SM_CintaEsquina) en /Game/FactoryCtyco/Environments/CintaCargaCurva,
con los materiales de SM_CintaCarga (rodillos con M_DespachoRodillo, que giran), y se la pone a todas las cintas de
carga curvas (AFactoryLoadingBelt con TurnDegrees): reemplaza a la esquina negra (SM_CintaEsquina, que queda sin uso).
Avisa de las curvas cuyo giro o largo no coinciden con la malla (90 grados, 241,6 cm).
Con el editor abierto: en la consola (Output Log, modo Cmd)
    py "C:/Users/Usuario/Desktop/unreal Projects/FactoryCtyco/Scripts/apply_cinta_curva.py"
y despues guardar el nivel. Con -unattended abre el mapa, guarda y cierra. Informe: Docs/cinta_curva.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/CintaCargaCurva"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
DEST, NAME = "/Game/FactoryCtyco/Environments/CintaCargaCurva", "SM_CintaCargaCurva"
STRAIGHT = "/Game/FactoryCtyco/Environments/CintaCarga/SM_CintaCarga"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
build = json.loads((SRC / "cinta_curva_build.json").read_text(encoding="utf-8"))
report = {"passed": False}

try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    curves = [a for a in actors.get_all_level_actors()
              if isinstance(a, unreal.FactoryLoadingBelt) and abs(a.get_editor_property("turn_degrees")) > 0.5]
    path = f"{DEST}/{NAME}"
    # import limpio (reimportar encima lo dejaba al 1 %): primero se suelta la malla
    for a in curves:
        if a.get_editor_property("belt").static_mesh and a.get_editor_property("belt").static_mesh.get_path_name().startswith(path):
            a.get_editor_property("belt").set_static_mesh(None)
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = False     # los de SM_CintaCarga
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision, data.one_convex_hull_per_ucx = True, False, True
    data.convert_scene = data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    box = mesh.get_bounding_box()
    exit_x = build["exit_unreal_cm"][0]
    if abs(box.max.x - (exit_x + build["width_m"] * 50)) > 10 or abs(box.max.z - (build["deck_m"] * 100 + 7)) > 3:
        raise RuntimeError(f"Medidas inesperadas: {box.min} .. {box.max}")
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != build["ucx"]:
        raise RuntimeError(f"Se esperaban {build['ucx']} colisiones; hay {hulls}")
    straight = unreal.load_asset(STRAIGHT)
    by_slot = {str(m.material_slot_name): m.material_interface for m in straight.static_materials}
    slots = mesh.static_materials
    matched = []
    # set_material: cambiar la lista static_materials y guardar no quedaba (seguia WorldGridMaterial)
    mesh.modify()
    for index, slot in enumerate(slots):
        material = by_slot.get(str(slot.material_slot_name))
        if material:
            mesh.set_material(index, material)
            matched.append(str(slot.material_slot_name))
    lib.save_loaded_asset(mesh, False)
    if len(matched) != len(slots):
        raise RuntimeError(f"Materiales sin par en SM_CintaCarga: {[str(s.material_slot_name) for s in slots]}")

    changed, mismatched = [], []
    for a in curves:
        a.modify()
        a.get_editor_property("belt").set_static_mesh(mesh)
        turn, length = a.get_editor_property("turn_degrees"), a.get_editor_property("length")
        changed.append(a.get_actor_label())
        if abs(abs(turn) - 90) > 0.5 or abs(length - build["length_cm"]) > 2:
            mismatched.append([a.get_actor_label(), round(turn, 1), round(length, 1)])
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, mesh=path, slots=matched, collisions=hulls, curves=changed,
                  turn_or_length_differs=mismatched)
    unreal.log(f"[CINTA_CURVA] {len(changed)} curvas con {NAME}: {changed}; distintas: {mismatched}. Guardar el nivel.")
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[CINTA_CURVA] " + report["error"])
finally:
    (project / "Docs/cinta_curva.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
