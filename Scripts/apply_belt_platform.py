"""Editor Python (con L_FactoryDemo abierto): las cintas de la fabrica sobre una plataforma.

Pedido del 30/09: las cintas quedaban al ras del piso. Importa SM_FactoryBeltPlatform (hecha por
author_belt_platform.py), la pone en DB_Belt con su altura y refresca todas las construcciones del nivel.
Vale para toda cinta de la fabrica, tambien las que se construyen jugando. La cinta sigue en el piso para la
cuadricula y para pasar material; sube lo que se ve (marco, listones, carga). No toca las de despacho ni de carga.
Necesita el plugin FactoryCtycoRuntime con BaseMesh/BaseHeight (Scripts/build_runtime_visuals.ps1 -Install).
Para otra altura: BaseHeight en DB_Belt (la malla se estira) y volver a correr esto, o Refresh en cada cinta.
Idempotente. No guarda el nivel. Informe: Docs/belt_platform.json.
"""
import json
import runpy
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
NAME = "SM_FactoryBeltPlatform"
report = {"passed": False}
try:
    manifest = json.loads((project / "SourceAssets/Factory/VisualPolish/belt_platform_manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("passed"):
        raise RuntimeError("author_belt_platform.py no termino bien")
    height = float(manifest["height_cm"])
    helpers = runpy.run_path(str(project / "Scripts/import_factory_details.py"), run_name="belt_platform_helpers")
    lib = unreal.EditorAssetLibrary
    path = helpers["DEST"] + "/" + NAME
    definition = unreal.load_asset(helpers["ROOT"] + "/Definitions/DB_Belt")
    definition.get_editor_property("base_height")   # falla aca si el plugin es el viejo

    # Reimportar encima de un asset existente lo deja al 1%: se borra antes.
    if lib.does_asset_exist(path):
        definition.set_editor_property("base_mesh", None)
        if not lib.delete_asset(path):
            raise RuntimeError("No se pudo borrar la plataforma anterior")
    mesh = helpers["_import"](NAME)
    bounds = helpers["_bounds"](mesh)
    yaw = 0
    if helpers["_near"](bounds["dimensions_cm"], (140, 200, height)):   # X/Y cambiados, como el marco
        lib.delete_asset(path)
        yaw = 90
        mesh = helpers["_import"](NAME, yaw=yaw)
        bounds = helpers["_bounds"](mesh)
    if not helpers["_near"](bounds["dimensions_cm"], (200, 140, height)) or abs(bounds["min_cm"][2]) > .05:
        raise RuntimeError(f"La plataforma llego con otro tamano: {bounds}")
    mesh.modify()
    slots = []
    for index, slot in enumerate(mesh.static_materials):
        slot_name = str(slot.get_editor_property("material_slot_name"))
        surface = next(key for key in helpers["SURFACES"] if key.lower() in slot_name.lower())
        material = unreal.load_asset(helpers["MATERIAL_FOLDER"] + "/MI_Factory" + surface)
        mesh.set_material(index, material)
        slots.append([slot_name, material.get_path_name()])
    unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).remove_collisions(mesh)
    helpers["_save"](mesh)

    definition.modify()
    definition.set_editor_property("base_mesh", mesh)
    definition.set_editor_property("base_height", height)
    helpers["_save"](definition)

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    buildings = []
    for actor in actors:
        if not isinstance(actor, unreal.FactoryBuilding):
            continue
        actor.modify()
        actor.refresh_visuals()
        belt = actor.get_editor_property("definition") == definition
        visual, base = actor.get_editor_property("visual"), actor.get_editor_property("base")
        entry = [actor.get_actor_label(), round(actor.get_actor_location().z, 1), round(actor.lift(), 1),
                 round(visual.get_editor_property("relative_location").z, 1),
                 base.get_editor_property("static_mesh").get_name() if base.get_editor_property("static_mesh") else None]
        buildings.append(entry)
        if belt and (entry[2] != height or entry[3] != height or entry[4] != NAME):
            raise RuntimeError(f"La cinta no quedo sobre la plataforma: {entry}")
        if not belt and (entry[2] != 0 or entry[4] is not None):
            raise RuntimeError(f"Una maquina quedo levantada: {entry}")
    if not any(b[4] for b in buildings):
        raise RuntimeError("No hay cintas de la fabrica en el nivel")
    report.update(passed=True, mesh=mesh.get_path_name(), import_yaw=yaw, bounds=bounds, materials=slots,
                  height_cm=height, triangles=mesh.get_num_triangles(0),
                  buildings=sorted(buildings), columns=["actor", "z", "lift", "visual_z", "base"])
except Exception as error:
    report["error"] = repr(error)
    unreal.log_error(f"[BELT_PLATFORM] {error}")
(project / "Docs/belt_platform.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
