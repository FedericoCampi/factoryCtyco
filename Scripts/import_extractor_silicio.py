"""Editor Python: importa el Extractor de Silicio animado y lo coloca en el estacionamiento.

Fuente: SourceAssets/ExtractorSilicio/extractor_unreal.fbx (author_extractor_silicio.py).
Crea el material de la mirilla con pulso emisivo, abre L_FactoryDemo, coloca el actor
`Extractor_Silicio` sobre el piso del estacionamiento con la animacion en loop y guarda.
Informe: Docs/extractor_import.json. Cierra el editor al terminar.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/import_extractor_silicio.py
    -unattended -nosound
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SOURCE = project / "SourceAssets/ExtractorSilicio"
DEST = "/Game/FactoryCtyco/Environments/ExtractorSilicio"
NAME = "SK_ExtractorSilicio"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
LABEL = "Extractor_Silicio"
SPOT = (-2303.0, -410.0)  # centro del estacionamiento; el usuario lo reubica
build = json.loads((SOURCE / "extractor_build.json").read_text())
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"passed": False}


def import_fbx():
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.original_import_type = options.mesh_type_to_import
    options.import_animations = True
    options.import_materials = True
    options.import_textures = True
    options.create_physics_asset = True
    data = options.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    anim = options.anim_sequence_import_data
    anim.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    anim.set_editor_property("remove_redundant_keys", False)
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / "extractor_unreal.fbx")
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    tools.import_asset_tasks([task])
    # task.save solo guarda la malla: esqueleto, animacion, materiales y texturas van aca
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(f"{DEST}/{NAME}")
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("No se importo la malla con esqueleto")
    anims = [a for a in map(unreal.load_asset, lib.list_assets(DEST, recursive=False))
             if isinstance(a, unreal.AnimSequence)]
    if len(anims) != 1:
        raise RuntimeError(f"Se esperaba 1 animacion; hay {len(anims)}")
    return mesh, anims[0]


def glow_material(mesh):
    """Mirilla: textura base + emisivo naranja que pulsa cada 4 s (dos pulsos por loop)."""
    slot = next(m for m in mesh.materials if "Mirilla" in str(m.material_slot_name))
    source = slot.material_interface
    tex_node = mel.get_material_property_input_node(source, unreal.MaterialProperty.MP_BASE_COLOR)
    if not isinstance(tex_node, unreal.MaterialExpressionTextureSample):
        raise RuntimeError("La mirilla importada no tiene textura base")
    texture = tex_node.get_editor_property("texture")
    path = f"{DEST}/M_ExtractorMirilla_Glow"
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    mat = tools.create_asset("M_ExtractorMirilla_Glow", DEST, unreal.Material, unreal.MaterialFactoryNew())
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -900, 0)
    tex.set_editor_property("texture", texture)
    mel.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, 200)
    rough.set_editor_property("r", 0.25)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    orange = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -900, 300)
    orange.set_editor_property("constant", unreal.LinearColor(1.0, 0.35, 0.06, 1.0))
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -600, 250)
    mel.connect_material_expressions(tex, "RGB", tint, "A")
    mel.connect_material_expressions(orange, "", tint, "B")
    time = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1200, 500)
    sine = mel.create_material_expression(mat, unreal.MaterialExpressionSine, -1000, 500)
    sine.set_editor_property("period", 4.0)
    mel.connect_material_expressions(time, "", sine, "")
    amp = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -800, 500)
    amp.set_editor_property("const_b", 3.5)
    mel.connect_material_expressions(sine, "", amp, "A")
    base = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -600, 500)
    base.set_editor_property("const_b", 4.5)  # emisivo entre 1 y 8
    mel.connect_material_expressions(amp, "", base, "A")
    glow = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 350)
    mel.connect_material_expressions(tint, "", glow, "A")
    mel.connect_material_expressions(base, "", glow, "B")
    mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)

    materials = mesh.materials
    for m in materials:
        if "Mirilla" in str(m.material_slot_name):
            m.set_editor_property("material_interface", mat)
    mesh.set_editor_property("materials", materials)
    lib.save_loaded_asset(mesh, False)
    return mat


def floor_z(world):
    start = unreal.Vector(SPOT[0], SPOT[1], 1000.0)
    end = unreal.Vector(SPOT[0], SPOT[1], -500.0)
    hit = unreal.SystemLibrary.line_trace_single(
        world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
        unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = next((h for h in hit if isinstance(h, unreal.HitResult)), None)
    if hit is None:
        return 0.0
    parts = hit.to_tuple()
    if not parts[0]:  # blocking_hit
        return 0.0
    return float(parts[4].z)  # impact_point


try:
    mesh, anim = import_fbx()
    glow = glow_material(mesh)
    height = mesh.get_bounds().box_extent.z * 2
    if abs(height - build["height_m"] * 100) > 10:
        raise RuntimeError(f"Altura inesperada {height:.1f} cm")
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)

    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_editor.load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for old in actors.get_all_level_actors():
        if old.get_actor_label() == LABEL:
            actors.destroy_actor(old)
    z = floor_z(world)
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor,
                                          unreal.Vector(SPOT[0], SPOT[1], z), unreal.Rotator())
    actor.set_actor_label(LABEL)
    actor.set_folder_path("Environment")
    comp = actor.skeletal_mesh_component
    comp.set_skinned_asset_and_update(mesh)
    comp.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data = comp.get_editor_property("animation_data")
    data.set_editor_property("anim_to_play", anim)
    data.set_editor_property("saved_looping", True)
    data.set_editor_property("saved_playing", True)
    comp.set_editor_property("animation_data", data)
    comp.set_editor_property("visibility_based_anim_tick_option",
                             unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    comp.set_collision_profile_name("BlockAll")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = actor.get_actor_location()
    report.update(passed=True, mesh=mesh.get_path_name(), animation=anim.get_path_name(),
                  anim_seconds=round(anim.get_play_length(), 3), glow_material=glow.get_path_name(),
                  physics_asset=str(mesh.get_editor_property("physics_asset")),
                  height_cm=round(height, 1), actor=LABEL, location=[loc.x, loc.y, loc.z],
                  materials=[str(m.material_slot_name) for m in mesh.materials])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[EXTRACTOR_IMPORT] {error}")
finally:
    (project / "Docs/extractor_import.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    unreal.SystemLibrary.quit_editor()
