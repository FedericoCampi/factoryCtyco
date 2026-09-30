"""Editor Python (con L_FactoryDemo abierto): separa estacionamiento y fabrica y los une con ascensores.

1. Engancha al estacionamiento lo que esta adentro (extractor, PlayerStart) y lo aleja 15 m al
   oeste de la fabrica (solo si sigue pegado, en x = -2303).
2. Tapa con bloqueos invisibles las dos puertas que antes los unian.
3. Ascensor_Estacionamiento (terraza, 1,35 m) y Ascensor_Fabrica (lado oeste de la fabrica),
   AFactoryElevator enlazados entre si: parado encima, E lleva al otro.
Cada ascensor va enganchado a su escena: al mover la escena se mueve con ella. Idempotente.
No guarda el nivel (run_elevator_setup.py lo corre sin editor y guarda).
Informe: Docs/elevators.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Ascensor"
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
report = {"passed": False}

SEPARATION = unreal.Vector(-1500, 0, 0)
PARKING_JOINED_X = -2303.0
TERRACE = unreal.Vector(900, -1000, 135)      # relativo al estacionamiento (terraza x 3..11, y 8..12 en Blender)
FACTORY_SPOT = unreal.Vector(-850, 90, 0)     # dentro de la fabrica, frente a la vieja puerta oeste
DOOR_Y = 90.0                                  # centro de las puertas que unian las escenas
LABELS = ("Ascensor_Estacionamiento", "Ascensor_Fabrica", "Bloqueo_PuertaFabrica", "Bloqueo_PuertaEstacionamiento")


def find(label):
    return next((a for a in actors.get_all_level_actors() if a.get_actor_label() == label), None)


def material(name, color, emissive=0.0):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path):
        mat = unreal.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -500, 0)
    c.set_editor_property("constant", color)
    if emissive:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        m = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -250, 0)
        m.set_editor_property("const_b", emissive)
        mel.connect_material_expressions(c, "", m, "A")
        mel.connect_material_property(m, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    else:
        mel.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
        for prop, value, y in ((unreal.MaterialProperty.MP_METALLIC, 0.8, 150), (unreal.MaterialProperty.MP_ROUGHNESS, 0.35, 250)):
            k = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -250, y)
            k.set_editor_property("r", value)
            mel.connect_material_property(k, "", prop)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    return mat


def floor_z(x, y, above):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, above), unreal.Vector(x, y, -500),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    t = hit.to_tuple() if hit else None
    return float(t[4].z) if t and t[0] else None


def attach(child, parent):
    child.attach_to_actor(parent, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                          unreal.AttachmentRule.KEEP_WORLD, False)


def blocker(label, location, parent):
    b = actors.spawn_actor_from_class(unreal.StaticMeshActor, location, unreal.Rotator())
    b.set_actor_label(label)
    sm = b.static_mesh_component
    sm.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    sm.set_collision_profile_name("BlockAll")
    b.set_actor_scale3d(unreal.Vector(0.3, 3.8, 3.2))
    b.set_actor_hidden_in_game(True)
    b.set_folder_path("Environment")
    attach(b, parent)
    return b


def elevator(cls, label, location, stop, parent, metal, light):
    e = actors.spawn_actor_from_class(cls, location, unreal.Rotator())
    e.set_actor_label(label)
    e.set_editor_property("stop_name", stop)
    for comp in e.get_components_by_class(unreal.StaticMeshComponent):
        comp.set_material(0, light if comp.get_name() == "GlowRing" else metal)
    e.set_folder_path("Environment")
    attach(e, parent)
    return e


try:
    cls = unreal.load_class(None, "/Script/FactoryCtycoRuntime.FactoryElevator")
    if cls is None:
        raise RuntimeError("Falta AFactoryElevator: instalar FactoryCtycoRuntime (build_runtime_visuals.ps1 -Install)")
    parking, factory = find("Parking_Estacionamiento"), find("SceneRobot_Fabrica")
    if not parking or not factory:
        raise RuntimeError("Faltan Parking_Estacionamiento o SceneRobot_Fabrica")
    for label in LABELS:
        old = find(label)
        if old:
            actors.destroy_actor(old)

    moved = []
    for label in ("Extractor_Silicio", "PlayerStart_Robot1"):
        a = find(label)
        if a and a.get_attach_parent_actor() != parking:
            attach(a, parking)
            moved.append(label)
    if abs(parking.get_actor_location().x - PARKING_JOINED_X) < 1:
        parking.set_actor_location(parking.get_actor_location() + SEPARATION, False, False)
    p = parking.get_actor_location()

    blocker("Bloqueo_PuertaFabrica", unreal.Vector(-1135, DOOR_Y, 150), factory)
    blocker("Bloqueo_PuertaEstacionamiento", unreal.Vector(p.x + 1120, DOOR_Y, 150), parking)

    metal = material("M_AscensorMetal", unreal.LinearColor(0.08, 0.09, 0.1, 1))
    light = material("M_AscensorLuz", unreal.LinearColor(0.1, 0.85, 1.0, 1), 6.0)
    top = unreal.Vector(p.x + TERRACE.x, p.y + TERRACE.y, 0)
    top.z = floor_z(top.x, top.y, 400) or TERRACE.z
    low = unreal.Vector(FACTORY_SPOT.x, FACTORY_SPOT.y, floor_z(FACTORY_SPOT.x, FACTORY_SPOT.y, 150) or 0.0)
    up = elevator(cls, "Ascensor_Estacionamiento", top, "DESPACHO", parking, metal, light)
    down = elevator(cls, "Ascensor_Fabrica", low, "FÁBRICA", factory, metal, light)
    up.set_editor_property("destination", down)
    down.set_editor_property("destination", up)
    report.update(passed=True, parking=[p.x, p.y, p.z], attached_to_parking=moved,
                  elevator_parking=[round(v, 1) for v in top.to_tuple()],
                  elevator_factory=[round(v, 1) for v in low.to_tuple()])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ELEVATORS] {error}")
(project / "Docs/elevators.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
