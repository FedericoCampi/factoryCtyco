"""Editor Python: el nivel arranca como juego (28/09).

1. Respaldo: lo hace Scripts/make_complete_backup.py (L_FactoryDemo_Completo, todo construido).
2. Bloqueados (siguen en el nivel, en la carpeta "Bloqueado"; en juego no se ven ni funcionan hasta que se
   desbloquean con UFactoryUnlockSubsystem::Unlock(Grupo)):
   - Despacho2: Despacho_Machine2, Despacho_Cajas2, Botonera_Cinta2 (la cinta de despacho 2; la 1 queda activa).
   - Camion2: Camion_Recorrido2 y Cinta_Carga4 (se vuelve a crear donde estaba: la habian borrado).
3. Relleno del grupo Despacho2 (se va cuando se construye el despacho): el rincon de basura de
   author_junk_corner.py (tablones en la abertura del muro, volquete, pallet con cajas y bolsas).
4. Ploteo de los camiones: T_PloteoCamion + M_PloteoCamion en SM_PloteoLado, puesto como WrapMesh.
5. Punto de contratacion (AFactoryWorkerSpawn "Punto_Contratacion", puesto "Barrera"): de ahi sale el
   encargado de barrera y camina por su linea hasta adentro de la cabina (se crea una sola vez; despues se
   mueve a mano).
Con -unattended abre el mapa, guarda y cierra. Informe: Docs/game_start.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP, BACKUP = "/Game/FactoryCtyco/Maps/L_FactoryDemo", "/Game/FactoryCtyco/Maps/L_FactoryDemo_Completo"
RINCON, PLOTEO = "/Game/FactoryCtyco/Environments/Rincon", "/Game/FactoryCtyco/Environments/Ploteo"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"passed": False}
LOCKED = {"Despacho2": ["Despacho_Machine2", "Despacho_Cajas2", "Botonera_Cinta2"], "Camion2": ["Camion_Recorrido2", "Cinta_Carga2", "Cinta_Carga"]}   # 30/09: el camion 1 carga en Cinta_Carga4
# Primero se habia bloqueado el despacho 1: vuelve a estar activo.
UNLOCKED = {"Despacho1": ["Despacho_Machine", "Despacho_Cajas", "Botonera_Cinta1"]}
FILLER_GROUP = "Despacho2"
# Rincon: pieza, posicion relativa al estacionamiento (cm), giro (yaw), escala Y. La abertura del muro del
# despacho 2 va de y 166 a -210 (3,75 m; los tablones miden 3,4 m).
JUNK = [("SM_TablonesAbertura", "Rincon_Tablones", (-1092, -22, 0), 0, 1.11),
        ("SM_Volquete", "Rincon_Volquete", (-985, -70, 0), 90, 1.0),
        ("SM_PalletCajas", "Rincon_Pallet", (-930, 125, 0), 12, 1.0),
        ("SM_BolsasBasura", "Rincon_Bolsas", (-905, -185, 0), -20, 1.0)]


def import_mesh(folder, name, dest, compute_normals=False):
    # Siempre importacion nueva: reimportar encima de la malla existente la dejaba a 1/100 de su tamano.
    if lib.does_asset_exist(f"{dest}/{name}") and not lib.delete_asset(f"{dest}/{name}"):
        raise RuntimeError(f"No se pudo borrar {name} (algo la sigue usando)")
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
    data.convert_scene = True
    data.convert_scene_unit = True
    if compute_normals:   # el panel de una sola cara: la normal sigue al lado que se dibuja
        data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS
    task = unreal.AssetImportTask()
    task.filename = str(project / folder / f"{name}.fbx")
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(f"{dest}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


def wrap_material():
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/Ploteo/T_PloteoCamion.png")
    task.destination_path = PLOTEO
    task.destination_name = "T_PloteoCamion"
    task.automated = True
    task.save = True
    task.replace_existing = True
    tools.import_asset_tasks([task])
    texture = unreal.load_asset(f"{PLOTEO}/T_PloteoCamion")
    if lib.does_asset_exist(f"{PLOTEO}/M_PloteoCamion"):
        lib.delete_asset(f"{PLOTEO}/M_PloteoCamion")
    material = tools.create_asset("M_PloteoCamion", PLOTEO, unreal.Material, unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    sample = mel.create_material_expression(material, unreal.MaterialExpressionTextureSample, -400, 0)
    sample.texture = texture
    mel.connect_material_property(sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop, y in ((0.35, unreal.MaterialProperty.MP_ROUGHNESS, 250), (0.25, unreal.MaterialProperty.MP_METALLIC, 350)):
        const = mel.create_material_expression(material, unreal.MaterialExpressionConstant, -400, y)
        const.r = value
        mel.connect_material_property(const, "", prop)
    mel.recompile_material(material)
    lib.save_loaded_asset(material)
    return material


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError("No se pudo abrir el mapa")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    parking = by_label["Parking_Estacionamiento"]

    # Cinta_Carga4 otra vez donde estaba: copia de Cinta_Carga (misma escala y giro) movida a su lugar.
    if "Cinta_Carga4" not in by_label:
        source = by_label["Cinta_Carga"]
        belt = actors.duplicate_actor(source)
        belt.set_actor_label("Cinta_Carga4")
        belt.attach_to_actor(parking, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                             unreal.AttachmentRule.KEEP_WORLD, False)
        z = source.root_component.get_editor_property("relative_location").z
        belt.root_component.set_editor_property("relative_location", unreal.Vector(-318, -15, z))
        belt.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 90))
        by_label["Cinta_Carga4"] = belt
        report["recreated"] = {"Cinta_Carga4": [round(v) for v in (belt.get_actor_location().x, belt.get_actor_location().y)]}

    for group, labels in UNLOCKED.items():
        for label in labels:
            actor = by_label[label]
            actor.modify()
            actor.tags = [t for t in actor.tags if str(t) not in ("Bloqueado", group)]
            actor.set_folder_path("Despacho")
    report["locked"] = {}
    for group, labels in LOCKED.items():
        for label in labels:
            actor = by_label[label]
            actor.modify()
            actor.tags = [t for t in actor.tags if str(t) not in ("Bloqueado", group)] + [unreal.Name("Bloqueado"), unreal.Name(group)]
            actor.set_folder_path(f"Bloqueado/{group}")
            report["locked"].setdefault(group, []).append(label)

    # Rincon de basura (relleno de Despacho1)
    report["filler"] = []
    for _, label, _, _, _ in JUNK:
        if label in by_label:
            actors.destroy_actor(by_label.pop(label))
    for mesh_name, label, (x, y, z), yaw, scale_y in JUNK:
        mesh = import_mesh("SourceAssets/Rincon", mesh_name, RINCON)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, parking.get_actor_location())
        actor.set_actor_label(label)
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.attach_to_actor(parking, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD, False)
        actor.root_component.set_editor_property("relative_location", unreal.Vector(x, y, z))
        actor.root_component.set_editor_property("relative_rotation", unreal.Rotator(0, 0, yaw))
        actor.root_component.set_editor_property("relative_scale3d", unreal.Vector(1, scale_y, 1))
        actor.tags = [unreal.Name("Relleno"), unreal.Name(FILLER_GROUP)]
        actor.set_folder_path(f"Relleno/{FILLER_GROUP}")
        loc = actor.get_actor_location()
        extent = mesh.get_bounds().box_extent
        report["filler"].append({"label": label, "world": [round(loc.x), round(loc.y), round(loc.z)],
                                 "size_cm": [round(extent.x * 2), round(extent.y * 2), round(extent.z * 2)]})
    lib.save_directory(RINCON, only_if_is_dirty=False, recursive=True)

    # Ploteo (los camiones sueltan el panel mientras se importa de nuevo)
    for label in ("Camion_Recorrido", "Camion_Recorrido2"):
        by_label[label].set_editor_property("wrap_mesh", None)
    material = wrap_material()
    panel = import_mesh("SourceAssets/Ploteo", "SM_PloteoLado", PLOTEO, compute_normals=True)
    panel.set_material(0, material)
    lib.save_loaded_asset(panel)
    extent = panel.get_bounds().box_extent
    report["wrap_panel_cm"] = [round(extent.x * 2), round(extent.z * 2)]
    if extent.x < 100:
        raise RuntimeError(f"El panel del ploteo quedo chico: {report['wrap_panel_cm']}")
    for label in ("Camion_Recorrido", "Camion_Recorrido2"):
        truck = by_label[label]
        truck.modify()
        truck.set_editor_property("wrap_mesh", panel)
    lib.save_directory(PLOTEO, only_if_is_dirty=False, recursive=True)

    # Punto de contratacion: a 4,5 m de la puerta de la cabina (lado -X de la cabina), con la linea
    # afuera de la puerta -> adentro de la cabina.
    if "Punto_Contratacion" not in by_label:
        booth = by_label["Cabina_Barrera"]
        frame = booth.get_actor_transform()
        start = frame.transform_location(unreal.Vector(-530, 0, 0))
        door = frame.transform_location(unreal.Vector(-150, 0, 0))
        inside = frame.transform_location(unreal.Vector(0, 0, 0))
        spawn = actors.spawn_actor_from_class(unreal.FactoryWorkerSpawn, start)
        spawn.set_actor_label("Punto_Contratacion")
        spawn.set_folder_path("Personal")
        spawn.set_editor_property("workplace", booth)
        route = spawn.get_editor_property("route")
        route.clear_spline_points(False)
        for point in (start, door, inside):
            route.add_spline_point(point, unreal.SplineCoordinateSpace.WORLD, False)
        for i in range(3):
            route.set_spline_point_type(i, unreal.SplinePointType.LINEAR, False)
        route.update_spline()
        report["hire_point"] = {"start": [round(start.x), round(start.y), round(start.z)],
                                "inside": [round(inside.x), round(inside.y), round(inside.z)]}

    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception as error:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error(f"[GAME_START] {error}")
finally:
    (project / "Docs/game_start.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
