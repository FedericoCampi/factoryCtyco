"""Editor Python: cajas que salen de cada maquina de despacho y se juntan al final de su cinta.

Importa SourceAssets/DispatchBox/SM_CajaDespacho.fbx (author_dispatch_box.py) y, por cada actor
`Despacho_Machine*`, pone un AFactoryDispatchBelt (FactoryCtycoRuntime) enganchado a la maquina con
transform relativo cero: sus Start/End estan en el espacio sin escalar de SM_DespachoMachine
(entra por la camara, se para al final de la cinta) y heredan la escala del actor.
Cada cinta tiene su botonera (SM_BotoneraDespacho, author_dispatch_panel.py) al costado: E la
prende; se apaga sola al llenarse y aparece encima un cartel rojo (SM_CartelLleno,
author_sign_and_wall.py) que al hacer clic muestra el detalle. Maximo 4 cajas por cinta. Idempotente: si el emisor existe solo actualiza la malla.
Sin editor: guarda el nivel y cierra. Con editor abierto: no guarda el nivel. Informe: Docs/dispatch_belts.json.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/apply_dispatch_belts.py -unattended -nosound
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/DispatchBox"
NAME = "SM_CajaDespacho"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_mesh(name, collision):
    # reimportar encima de un asset existente lo deja al 1% (metros tomados como cm): borrar antes
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
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
    data.auto_generate_collision = collision
    data.convert_scene = True
    data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/DispatchBox/{name}.fbx")
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(f"{DEST}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    box = mesh.get_bounding_box()
    if max(box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z) < 20:
        raise RuntimeError(f"{name} quedo diminuto ({box.max.z - box.min.z:.2f} cm de alto)")
    return mesh


def sign_material(sign):
    """Tablero del cartel: rojo emisivo que late despacio para llamar la atencion."""
    mel = unreal.MaterialEditingLibrary
    path = f"{DEST}/M_CartelLleno"
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_CartelLleno", DEST, unreal.Material, unreal.MaterialFactoryNew())
    red = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -700, 0)
    red.set_editor_property("constant", unreal.LinearColor(0.85, 0.03, 0.02, 1))
    mel.connect_material_property(red, "", unreal.MaterialProperty.MP_BASE_COLOR)
    time = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -900, 250)
    wave = mel.create_material_expression(mat, unreal.MaterialExpressionSine, -700, 250)
    wave.set_editor_property("period", 1.2)
    mel.connect_material_expressions(time, "", wave, "")
    pulse = mel.create_material_expression(mat, unreal.MaterialExpressionConstantBiasScale, -500, 250)
    pulse.set_editor_property("bias", 2.0)
    pulse.set_editor_property("scale", 1.2)  # emisivo entre 1,2 y 3,6
    mel.connect_material_expressions(wave, "", pulse, "")
    glow = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 100)
    mel.connect_material_expressions(red, "", glow, "A")
    mel.connect_material_expressions(pulse, "", glow, "B")
    mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    materials = sign.static_materials
    for m in materials:
        if str(m.material_slot_name) == "M_CartelRojo":
            m.set_editor_property("material_interface", mat)
    sign.set_editor_property("static_materials", materials)
    if not lib.save_loaded_asset(sign, False):
        raise RuntimeError("No se pudo guardar el cartel")
    return mat


def button_material(panel):
    """Hongo de la botonera: rojo apagado, verde brillante encendido (parametro Encendido 0-1)."""
    mel = unreal.MaterialEditingLibrary
    path = f"{DEST}/M_BotonDespacho"
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_BotonDespacho", DEST, unreal.Material, unreal.MaterialFactoryNew())
    on = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 200)
    on.set_editor_property("parameter_name", "Encendido")
    off_c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -700, -100)
    off_c.set_editor_property("constant", unreal.LinearColor(0.7, 0.05, 0.03, 1))
    on_c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -700, 0)
    on_c.set_editor_property("constant", unreal.LinearColor(0.1, 0.9, 0.15, 1))
    color = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -400, 0)
    mel.connect_material_expressions(off_c, "", color, "A")
    mel.connect_material_expressions(on_c, "", color, "B")
    mel.connect_material_expressions(on, "", color, "Alpha")
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    glow = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 150)
    mel.connect_material_expressions(color, "", glow, "A")
    strength = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -400, 250)
    strength.set_editor_property("const_a", 0.6)
    strength.set_editor_property("const_b", 6.0)
    mel.connect_material_expressions(on, "", strength, "Alpha")
    mel.connect_material_expressions(strength, "", glow, "B")
    mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    materials = panel.static_materials
    for m in materials:
        if str(m.material_slot_name) == "M_Boton":
            m.set_editor_property("material_interface", mat)
    panel.set_editor_property("static_materials", materials)
    if not lib.save_loaded_asset(panel, False):
        raise RuntimeError("No se pudo guardar la botonera")
    return mat


try:
    belt_class = getattr(unreal, "FactoryDispatchBelt", None)
    if belt_class is None:
        raise RuntimeError("Falta AFactoryDispatchBelt: instalar FactoryCtycoRuntime (build_runtime_visuals.ps1 -Install)")
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    for belt in unreal.GameplayStatics.get_all_actors_of_class(
            unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), belt_class):
        belt.modify()  # soltar referencias para poder borrar y reimportar
        belt.set_editor_property("box_mesh", None)
        belt.sign.set_static_mesh(None)
    button_class = unreal.FactoryBeltButton
    for b in unreal.GameplayStatics.get_all_actors_of_class(
            unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), button_class):
        b.modify()
        b.panel.set_static_mesh(None)
    box = import_mesh(NAME, False)
    panel = import_mesh("SM_BotoneraDespacho", True)
    button = button_material(panel)
    sign = import_mesh("SM_CartelLleno", True)  # colision simple: el clic del mouse lo encuentra
    sign_mat = sign_material(sign)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level_actors = actors.get_all_level_actors()
    machines = [a for a in level_actors if isinstance(a, unreal.StaticMeshActor)
                and a.get_actor_label().startswith("Despacho_Machine")]
    done = {}
    for machine in machines:
        label = machine.get_actor_label().replace("Despacho_Machine", "Despacho_Cajas")
        belt = next((a for a in level_actors if a.get_actor_label() == label), None)
        if belt is None:
            belt = actors.spawn_actor_from_class(belt_class, machine.get_actor_location(), machine.get_actor_rotation())
            belt.set_actor_label(label)
            belt.set_folder_path("Environment")
            belt.attach_to_actor(machine, "", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                                 unreal.AttachmentRule.SNAP_TO_TARGET, False)
        belt.modify()
        belt.set_editor_property("box_mesh", box)
        number = machine.get_actor_label()[len("Despacho_Machine"):] or "1"
        belt.set_editor_property("belt_name", f"CINTA {number}")
        # botonera: actor aparte (AFactoryBeltButton) que apunta a la cinta; si no tiene, va al costado
        # de la maquina. Las que existen conservan la posicion ajustada a mano.
        knob = next((a for a in actors.get_all_level_actors() if isinstance(a, button_class)
                     and a.get_editor_property("belt") == belt), None)
        if knob is None:
            spot = machine.get_actor_transform().transform_location(unreal.Vector(-128, 40, 0))
            knob = actors.spawn_actor_from_class(button_class, spot, machine.get_actor_rotation().combine(unreal.Rotator(0, 0, 90)))
            knob.set_actor_label(f"Botonera_Cinta{number}")
            knob.set_folder_path("Environment")
            knob.panel.set_relative_scale3d(unreal.Vector(1.25, 1.25, 1.25))
            knob.set_editor_property("belt", belt)
        knob.modify()
        knob.panel.modify()
        knob.panel.set_static_mesh(panel)
        belt.sign.modify()
        belt.sign.set_static_mesh(sign)
        done[label] = machine.get_actor_label()
    if not done:
        raise RuntimeError("No hay actores Despacho_Machine*")
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, box=box.get_path_name(), panel=panel.get_path_name(),
                      button=button.get_path_name(), sign=sign.get_path_name(),
                      sign_material=sign_mat.get_path_name(), belts=done)
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[DISPATCH_BELTS] {error}")
finally:
    (project / "Docs/dispatch_belts.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
