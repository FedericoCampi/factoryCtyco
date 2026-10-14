"""Editor Python (05/10): cajas de despacho con etiqueta A, B, C o D al azar.

Importa SM_CajaDespacho_A .. _D (author_dispatch_box_labels.py) en /Game/FactoryCtyco/Environments/DispatchBox/Etiquetas,
con el carton y la cinta de SM_CajaDespacho (se ven igual) y el papel y la tinta de la etiqueta, y se las pone a cada
AFactoryDispatchBelt (BoxVariants): cada caja nueva sale con una letra al azar. Requiere FactoryCtycoRuntime con
BoxVariants. Guarda el nivel. Informe: Docs/cajas_etiquetas.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/DispatchBox"
DEST = "/Game/FactoryCtyco/Environments/DispatchBox/Etiquetas"
PLAIN = "/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho"
lib = unreal.EditorAssetLibrary
report = {"passed": False}

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    belts = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryDispatchBelt)]
    for belt in belts:
        belt.set_editor_property("box_variants", [])
    plain = unreal.load_asset(PLAIN)
    by_slot = {str(m.material_slot_name): m.material_interface for m in plain.static_materials}
    meshes = []
    for i, letter in enumerate("ABCD"):
        name = f"SM_CajaDespacho_{letter}"
        path = f"{DEST}/{name}"
        if lib.does_asset_exist(path) and not lib.delete_asset(path):
            raise RuntimeError(f"No se pudo borrar {path}")
        options = unreal.FbxImportUI()
        options.import_mesh, options.import_as_skeletal = True, False
        options.import_materials, options.import_textures = i == 0, False   # papel y tinta, con la primera
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        options.automated_import_should_detect_type = False
        data = options.static_mesh_import_data
        data.combine_meshes, data.auto_generate_collision = True, False
        data.convert_scene = data.convert_scene_unit = True
        task = unreal.AssetImportTask()
        task.filename = str(SRC / f"{name}.fbx")
        task.destination_path, task.destination_name = DEST, name
        task.automated = task.save = task.replace_existing = True
        task.factory, task.options = unreal.FbxFactory(), options
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError(f"No se importo {name}")
        b = mesh.get_bounding_box()
        if abs((b.max.x - b.min.x) - 40.5) > 2:
            raise RuntimeError(f"{name} mide {b.max.x - b.min.x:.1f} cm")
        meshes.append(mesh)
    # carton y cinta como la caja lisa; papel y tinta los importados con la primera
    labels = {str(m.material_slot_name): m.material_interface for m in meshes[0].static_materials}
    for mesh in meshes:
        mesh.modify()
        for index, slot in enumerate(mesh.static_materials):
            name = str(slot.material_slot_name)
            material = by_slot.get(name) or labels.get(name)
            if material:
                mesh.set_material(index, material)
        lib.save_loaded_asset(mesh, False)
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=False)   # tambien el papel y la tinta importados
    for belt in belts:
        belt.modify()
        belt.set_editor_property("box_variants", meshes)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, belts=[b.get_actor_label() for b in belts], variants=[m.get_name() for m in meshes],
                  slots=[[str(s.material_slot_name), s.material_interface.get_name() if s.material_interface else None]
                         for s in meshes[0].static_materials])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[CAJAS_ETIQUETAS] " + report["error"])
finally:
    (project / "Docs/cajas_etiquetas.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
