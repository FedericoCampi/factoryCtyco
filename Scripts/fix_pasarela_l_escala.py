"""Editor Python (04/10): las piezas de la pasarela en L estaban al 1 % (1,3 cm en vez de 1,3 m) y las L no se veian.

Desde el import del 03/10 (import_pasarela_modular.py) SM_PasarelaPiso, _Baranda y _Poste de
/Game/FactoryCtyco/Environments/Pasarelas/Modular quedaron a 1/100: importar sobre un nombre que ya existio deja la
malla a escala 1/100 (ver la nota de memoria del proyecto). Las importa de nuevo con nombres nuevos, en una carpeta
propia (Modular/L: SM_PasarelaLPiso, SM_PasarelaLBaranda, SM_PasarelaLPoste), comprueba su tamaño y se las pone a cada
AFactoryWalkwayL (Pasarela_L, Pasarela_L2). Con el editor abierto no guarda el nivel (guardar a mano).
Informe: Docs/pasarela_l_escala.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/Pasarelas/Modular"
DEST = "/Game/FactoryCtyco/Environments/Pasarelas/Modular/L"
PIECES = {"deck_mesh": ("SM_PasarelaPiso", "SM_PasarelaLPiso"), "rail_mesh": ("SM_PasarelaBaranda", "SM_PasarelaLBaranda"),
          "post_mesh": ("SM_PasarelaPoste", "SM_PasarelaLPoste")}
lib = unreal.EditorAssetLibrary
report = {"passed": False, "piezas": {}}

try:
    build = json.loads((SRC / "modular_build.json").read_text(encoding="utf-8"))
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    walks = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryWalkwayL)]
    meshes = {}
    for i, (prop, (fbx, name)) in enumerate(PIECES.items()):
        path = f"{DEST}/{name}"
        if lib.does_asset_exist(path):
            for w in walks:
                w.set_editor_property(prop, None)
            lib.delete_asset(path)
        options = unreal.FbxImportUI()
        options.import_mesh, options.import_as_skeletal = True, False
        options.import_materials = options.import_textures = i == 0   # el material viene con la primera
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        options.automated_import_should_detect_type = False
        data = options.static_mesh_import_data
        data.combine_meshes, data.auto_generate_collision, data.one_convex_hull_per_ucx = True, False, True
        data.convert_scene = data.convert_scene_unit = True
        data.import_uniform_scale = 1.0
        task = unreal.AssetImportTask()
        task.filename = str(SRC / f"{fbx}.fbx")
        task.destination_path, task.destination_name = DEST, name
        task.automated = task.save = task.replace_existing = True
        task.factory, task.options = unreal.FbxFactory(), options
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError(f"No se importo {name}")
        b = mesh.get_bounding_box()
        size = [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)]
        want = build["L"]["pieces"][fbx]["size_cm"]
        if abs(size[0] - want[0]) > 2 or abs(size[2] - want[2]) > 2:
            raise RuntimeError(f"{name} mide {size} cm, se esperaba {want}")
        meshes[prop] = mesh
        report["piezas"][name] = size
    material = meshes["deck_mesh"].get_material(0)
    for mesh in meshes.values():
        if mesh.get_material(0) != material:
            mesh.set_material(0, material)
        lib.save_loaded_asset(mesh, False)
    for w in walks:
        w.modify()
        for prop, mesh in meshes.items():
            w.set_editor_property(prop, mesh)
        w.rebuild()
    o, e = walks[0].get_actor_bounds(False) if walks else (None, None)
    report.update(passed=True, pasarelas=[w.get_actor_label() for w in walks],
                  alto_cm=round(e.z * 2, 1) if e else None)
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PASARELA_L_ESCALA] " + report["error"])
(project / "Docs/pasarela_l_escala.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
