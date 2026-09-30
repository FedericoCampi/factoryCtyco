"""Sin editor abierto: instala el ascensor2 (cabina que baja por un pozo) en L_FactoryDemo.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/apply_elevator2.py -unattended -nosound

Antes: blender -b --factory-startup -P Scripts/author_elevator2.py, python Scripts/make_elevator_sounds.py,
author_arena_edit.py y author_parking_scene.py (cortan el piso con floor_holes.py), y FactoryCtycoRuntime instalado.
1. Importa cabina, techo, puerta, tubo y sonidos en /Game/FactoryCtyco/Environments/Ascensor2.
2. Rehace SM_SceneRobot y SM_Parking con el agujero (reimport_arena_mesh.py, reimport_parking_mesh.py).
3. Configura los dos AFactoryElevator (mallas, medidas, sonidos) con la entrada mirando a -X
   (hacia la fabrica y hacia la terraza) y guarda el nivel. Informe: Docs/elevator2_apply.json.
"""
import json
import runpy
import sys
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
scripts = project / "Scripts"
SRC = project / "SourceAssets/Ascensor2"
sys.path.insert(0, str(scripts))
from elevator_holes import HOLES  # noqa: E402
DEST = "/Game/FactoryCtyco/Environments/Ascensor2"
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_task(filename, name, options=None):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {name}")
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    if options:
        task.factory = unreal.FbxFactory()
        task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset = unreal.load_asset(path)
    if not asset:
        raise RuntimeError(f"No se importo {name}")
    return asset


def mesh_options():
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
    data.generate_lightmap_u_vs = False
    data.build_nanite = False
    return options


try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    elevators = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryElevator)]
    if len(elevators) != 2:
        raise RuntimeError(f"Se esperaban 2 ascensores, hay {len(elevators)}")
    build = json.loads((SRC / "elevator2_build.json").read_text())

    for e in elevators:  # soltar referencias antes de borrar y reimportar
        for comp in e.get_components_by_class(unreal.StaticMeshComponent):
            comp.set_static_mesh(None)
    meshes = {n: import_task(SRC / f"SM_Ascensor2{n}.fbx", f"SM_Ascensor2{n}", mesh_options())
              for n in ("Cabina", "Techo", "Puerta", "Tubo")}
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(meshes["Cabina"])
    if hulls < 6:
        raise RuntimeError(f"La cabina tiene {hulls} colisiones (se esperaban 6)")
    sounds = {n: import_task(SRC / f"ascensor_{n}.wav", f"S_Ascensor_{n.capitalize()}")
              for n in ("motor", "golpe", "puerta")}
    sounds["motor"].set_editor_property("looping", True)
    lib.save_directory(DEST, only_if_is_dirty=False, recursive=True)

    runpy.run_path(str(scripts / "reimport_arena_mesh.py"), run_name="__main__")
    runpy.run_path(str(scripts / "reimport_parking_mesh.py"), run_name="__main__")
    for name in ("arena_reimport.json", "parking_reimport.json"):
        result = json.loads((project / "Docs" / name).read_text(encoding="utf-8"))
        if not result.get("passed"):
            raise RuntimeError(f"{name}: {result.get('error')}")

    cabin, door = build["cabin"], build["door"]
    done = []
    for e in elevators:
        by_name = {c.get_name(): c for c in e.get_components_by_class(unreal.StaticMeshComponent)}
        by_name["Tube"].set_static_mesh(meshes["Tubo"])
        by_name["Cabin"].set_static_mesh(meshes["Cabina"])
        by_name["Roof"].set_static_mesh(meshes["Techo"])
        for n in ("DoorRightOuter", "DoorRightInner", "DoorLeftOuter", "DoorLeftInner"):
            by_name[n].set_static_mesh(meshes["Puerta"])
        e.set_editor_property("travel_depth", round(build["travel_m"] * 100, 1))
        e.set_editor_property("cabin_half_extent", unreal.Vector2D(cabin["cabin_front_x_m"] * 100 - 10,
                                                                   cabin["opening_half_m"] * 100 + 30))
        e.set_editor_property("door_panel_width", door["panel_width_m"] * 100)
        e.set_editor_property("door_opening_half", cabin["opening_half_m"] * 100)
        e.set_editor_property("door_inner_x", door["inner_plane_x_m"] * 100)
        e.set_editor_property("door_outer_x", door["outer_plane_x_m"] * 100)
        e.set_editor_property("motor_sound", sounds["motor"])
        e.set_editor_property("clunk_sound", sounds["golpe"])
        e.set_editor_property("door_sound", sounds["puerta"])
        e.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=180), False)  # entrada hacia -X
        # Justo sobre su agujero (floor_holes.HOLES, en m de Blender de la malla del padre).
        parent = e.get_attach_parent_actor()
        key = {"SceneRobot_Fabrica": "arena", "Parking_Estacionamiento": "parking"}[parent.get_actor_label()]
        hx, hy, hz = HOLES[key][0]
        before = e.get_actor_location()
        e.set_actor_location(parent.get_actor_transform().transform_location(unreal.Vector(hx * 100, -hy * 100, hz * 100)), False, False)
        loc = e.get_actor_location()
        done.append({"label": e.get_actor_label(), "location": [loc.x, loc.y, loc.z],
                     "moved_from": [before.x, before.y, before.z], "parent": parent.get_actor_label(),
                     "parent_location": list(parent.get_actor_location().to_tuple()),
                     "yaw": e.get_actor_rotation().yaw, "travel_depth": e.get_editor_property("travel_depth")})
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, elevators=done, cabin_collisions=hulls,
                  meshes={k: v.get_path_name() for k, v in meshes.items()},
                  sounds={k: v.get_path_name() for k, v in sounds.items()})
except Exception as error:
    report["error"] = repr(error)
    unreal.log_error(f"[ELEVATOR2] {error}")
finally:
    (project / "Docs/elevator2_apply.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    unreal.SystemLibrary.quit_editor()
