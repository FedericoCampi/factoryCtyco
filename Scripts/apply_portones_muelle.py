"""Editor Python (04/10): portones de los muelles que se abren.

1. Reimporta SM_Muelles (import_muelles.py: author_muelles.py ahora saca los tres portones y abre la pared de
   hormigon detras de cada uno) e importa SM_PortonMuelle (un porton con su burlete, origen en el medio de su borde de
   arriba) con los materiales de SM_Muelles.
2. Pone `Porton_Muelle_1..3` (StaticMeshActor movible, carpeta Muelles) enganchados a `Muelles_Carga` donde estaban
   los portones (muelles_build.json, "doors"), y a cada `Cajon_Muelle_N` (AFactoryTruckBay) le asigna el porton mas
   cercano como DockDoor: sube mientras hay un camion estacionado en el cajon.
Necesita FactoryCtycoRuntime con DockDoor (build_runtime_visuals.ps1 -Install, con el editor cerrado).
Con -unattended abre el mapa, guarda y cierra; con el editor abierto tambien guarda el nivel (como import_muelles.py).
Informe: Docs/portones_muelle.json.
"""
import json
import runpy
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
DEST = "/Game/FactoryCtyco/Environments/Muelles"
NAME = "SM_PortonMuelle"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def key(name):
    return str(name).lower().replace(" ", "").replace("_", "")


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # los portones sueltan su malla antes de que import_muelles.py borre los assets de la carpeta
    for a in actors.get_all_level_actors():
        if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label().startswith("Porton_Muelle_"):
            a.static_mesh_component.set_static_mesh(None)
    runpy.run_path(str(project / "Scripts/import_muelles.py"))
    imported = json.loads((project / "Docs/muelles_import.json").read_text(encoding="utf-8"))
    if not imported.get("passed"):
        raise RuntimeError("import_muelles.py fallo: " + str(imported.get("error")))
    build = json.loads((project / "SourceAssets/Muelles/muelles_build.json").read_text(encoding="utf-8"))

    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    # con sus materiales: el del porton (Sectional door) ya no esta en SM_Muelles; los demas se cambian por los de SM_Muelles
    options.import_materials = options.import_textures = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    data.generate_lightmap_u_vs = data.build_nanite = False
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Muelles/{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=False)   # tambien el material que trajo (Sectional_door)
    door = unreal.load_asset(f"{DEST}/{NAME}")
    if not isinstance(door, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    box = door.get_bounding_box()
    size = [round(box.max.x - box.min.x), round(box.max.y - box.min.y), round(box.max.z - box.min.z)]
    expected = build["doors"][0]["size_m"]
    if abs(size[0] - expected[0] * 100) > 5 or abs(size[2] - expected[2] * 100) > 5:
        raise RuntimeError(f"{NAME} mide {size} cm")
    dock = unreal.load_asset(f"{DEST}/SM_Muelles")
    by_name = {key(m.material_slot_name): m.material_interface for m in dock.static_materials}
    slots = door.static_materials
    matched = []
    for slot in slots:
        material = by_name.get(key(slot.material_slot_name))
        if material:
            slot.set_editor_property("material_interface", material)
            matched.append(str(slot.material_slot_name))
    door.set_editor_property("static_materials", slots)
    body = door.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    door.set_editor_property("body_setup", body)
    lib.save_loaded_asset(door, False)

    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}
    building = by["Muelles_Carga"]
    doors = []
    for i, info in enumerate(build["doors"], start=1):
        label = f"Porton_Muelle_{i}"
        actor = by.get(label)
        if actor is None:
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, building.get_actor_location(), building.get_actor_rotation())
            actor.set_actor_label(label)
            actor.set_folder_path("Muelles")
        actor.modify()
        comp = actor.static_mesh_component
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_static_mesh(door)
        comp.set_collision_profile_name("BlockAll")
        actor.attach_to_actor(building, "", unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE,
                              unreal.AttachmentRule.KEEP_RELATIVE, False)
        x, y, z = info["top_m"]   # Blender (x, y, z) m -> Unreal (100x, -100y, 100z) cm, en el espacio del edificio
        comp.set_editor_property("relative_location", unreal.Vector(x * 100, -y * 100, z * 100))
        comp.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
        comp.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
        doors.append(actor)
    # cada cajon con el porton mas cercano (en planta), uno por cajon
    bays = [a for a in level if isinstance(a, unreal.FactoryTruckBay)]
    pairs = sorted(((unreal.Vector(b.get_actor_location().x - d.get_actor_location().x,
                                   b.get_actor_location().y - d.get_actor_location().y, 0).length(), b, d)
                    for b in bays for d in doors), key=lambda t: t[0])
    linked, used = {}, set()
    for dist, bay, d in pairs:
        if bay.get_actor_label() in linked or d.get_actor_label() in used:
            continue
        bay.modify()
        bay.set_editor_property("dock_door", d)
        linked[bay.get_actor_label()] = [d.get_actor_label(), round(dist)]
        used.add(d.get_actor_label())
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, door_size_cm=size, materials=[str(s.material_slot_name) for s in slots], matched=matched,
                  doors={d.get_actor_label(): [round(v) for v in (d.get_actor_location().x, d.get_actor_location().y,
                                                                    d.get_actor_location().z)] for d in doors},
                  bays=linked)
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PORTONES_MUELLE] " + report["error"])
finally:
    (project / "Docs/portones_muelle.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
