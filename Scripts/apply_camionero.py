"""Editor Python (08/10, con L_FactoryDemo abierto): camionero en los camiones y cabina con ventanillas abiertas.

Antes, en Blender: author_truck_cab.py (cabina abierta en Camion.blend y camion_loop.fbx), author_truck_dump.py
(camion_volcador.fbx) y author_tecjunior_sit.py (TecJunior_Sit.fbx).
1. Suelta el volcador (usa los materiales de SK_Camion, que se rehacen) y reimporta SK_Camion con apply_persiana_camion.py.
2. Reimporta el volcador, su rampa y su cajon con apply_rampa_tolvas.py (conserva los ajustes del camion).
3. Importa A_TecJunior_Sit (esqueleto de SK_TecJunior) y lo pone, con SK_TecJunior, de camionero en cada
   AFactoryVehiclePath (Camion_Recorrido, Camion_Recorrido2, Camion_Volcador), sentado en el asiento de la cabina.
4. (08/10) Vidrio translucido en las cabinas, colision del brazo de la barrera, RearLength 105 (la caja asoma 1 m
   detras del eje) y la linea propia de cada camion apoyada en el piso (SnapLineToGround).
Guarda el nivel. Informe: Docs/camionero.json (donde quedo la cabeza del camionero, en el espacio del camion).
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TJ = "/Game/FactoryCtyco/Characters/TecJunior"
report = {"passed": False}


def make_glass():
    """M_CamionVidrioTranslucido: vidrio oscuro translucido (se ve el camionero)."""
    path = "/Game/FactoryCtyco/Environments/Camion/M_CamionVidrioTranslucido"
    if lib.does_asset_exist(path):
        return unreal.load_asset(path)
    mel = unreal.MaterialEditingLibrary
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_CamionVidrioTranslucido", "/Game/FactoryCtyco/Environments/Camion",
                                                                   unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    color = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    color.set_editor_property("constant", unreal.LinearColor(0.05, 0.07, 0.08, 1))
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop, y in ((0.05, unreal.MaterialProperty.MP_ROUGHNESS, 150), (0.9, unreal.MaterialProperty.MP_SPECULAR, 250),
                           (0.3, unreal.MaterialProperty.MP_OPACITY, 350)):
        node = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, y)
        node.set_editor_property("r", value)
        mel.connect_material_property(node, "", prop)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat)
    return mat


def run(script):
    """Corre otro script del proyecto y devuelve su informe."""
    exec(compile((project / "Scripts" / script).read_text(encoding="utf-8"), script, "exec"), {"__name__": "__main__"})


try:
    trucks = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryVehiclePath)]
    # 1. el volcador se suelta y se borra (se importa de nuevo en el paso 2, con los materiales nuevos)
    for t in trucks:
        if t.get_editor_property("dump_truck"):
            t.set_editor_property("vehicle_mesh", None)
    volcador = "/Game/FactoryCtyco/Environments/Camion/Volcador"
    for path in lib.list_assets(volcador, recursive=False) if lib.does_directory_exist(volcador) else []:
        lib.delete_asset(path.split(".")[0])
    run("apply_persiana_camion.py")
    report["sk_camion"] = json.loads((project / "Docs/persiana_camion.json").read_text(encoding="utf-8"))
    if not report["sk_camion"].get("passed"):
        raise RuntimeError("No se reimporto SK_Camion")
    # 2. volcador, rampa y cajon
    run("apply_rampa_tolvas.py")
    report["volcador"] = json.loads((project / "Docs/rampa_tolvas.json").read_text(encoding="utf-8")).get("passed")
    # 3. la pose sentada y el camionero
    mesh = unreal.load_asset(f"{TJ}/SK_TecJunior")
    if lib.does_asset_exist(f"{TJ}/A_TecJunior_Sit"):
        lib.delete_asset(f"{TJ}/A_TecJunior_Sit")
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh, options.import_as_skeletal = False, True
    options.mesh_type_to_import = options.original_import_type = unreal.FBXImportType.FBXIT_ANIMATION
    options.import_animations, options.import_materials, options.import_textures = True, False, False
    options.skeleton = mesh.skeleton
    data = options.anim_sequence_import_data
    data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property("use_default_sample_rate", True)
    data.set_editor_property("preserve_local_transform", True)
    data.set_editor_property("convert_scene", True)
    data.set_editor_property("convert_scene_unit", True)
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/TecJunior/TecJunior_Sit.fbx")
    task.destination_path, task.destination_name = TJ, "A_TecJunior_Sit"
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sit = next((a for a in map(unreal.load_asset, task.imported_object_paths) if isinstance(a, unreal.AnimSequence)), None)
    if sit is None:
        raise RuntimeError("No se importo A_TecJunior_Sit")
    if sit.get_name() != "A_TecJunior_Sit":
        unreal.EditorAssetLibrary.rename_asset(sit.get_path_name().split(".")[0], f"{TJ}/A_TecJunior_Sit")
        sit = unreal.load_asset(f"{TJ}/A_TecJunior_Sit")
    lib.save_loaded_asset(sit)
    # 4. vidrio translucido en las cabinas (el slot M_CamionVidrio de author_truck_cab.py)
    glass = make_glass()
    for path in ("/Game/FactoryCtyco/Environments/Camion/SK_Camion", "/Game/FactoryCtyco/Environments/Camion/Volcador/SK_CamionVolcador"):
        sk = unreal.load_asset(path)
        mats = sk.materials
        for i, m in enumerate(mats):   # cada elemento es una copia: se vuelve a poner en la lista
            if str(m.get_editor_property("material_slot_name")) == "M_CamionVidrio":
                m.set_editor_property("material_interface", glass)
                mats[i] = m
        sk.set_editor_property("materials", mats)
        lib.save_loaded_asset(sk)
    # 5. el brazo de la barrera choca (con su malla)
    arm = unreal.load_asset("/Game/FactoryCtyco/Environments/CabinaBarrera/SM_BarreraBrazo")
    body = arm.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    arm.set_editor_property("body_setup", body)
    lib.save_loaded_asset(arm)
    rows = []
    for t in [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryVehiclePath)]:
        t.modify()
        t.set_editor_property("driver_mesh", mesh)
        t.set_editor_property("driver_anim", sit)
        # sentado en el asiento de author_truck_cab.py (DRIVER: 3,35 / 0,38 / 0,16 m en Blender)
        t.set_editor_property("driver_transform", unreal.Transform(unreal.Vector(335, -38, 16), unreal.Rotator(0, 0, -90), unreal.Vector(1, 1, 1)))
        # la caja termina 1 m detras del eje trasero (con 60 la barrera bajaba sobre ella)
        t.set_editor_property("rear_length", 105.0)
        if not t.get_editor_property("lead_path"):
            t.snap_line_to_ground()
        driver = t.get_editor_property("driver")
        rows.append({"camion": t.get_actor_label(), "malla": str(driver.get_skeletal_mesh_asset().get_name() if driver.get_skeletal_mesh_asset() else None),
                     "lugar_cm": [round(v) for v in t.get_editor_property("driver_transform").translation.to_tuple()]})
    report["camioneros"] = rows
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = bool(report["volcador"]) and all(r["malla"] == "SK_TecJunior" for r in rows) and len(rows) >= 3
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[CAMIONERO] " + report["error"])
(project / "Docs/camionero.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
