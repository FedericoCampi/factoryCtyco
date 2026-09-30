"""Editor Python: camion que recorre una linea editable (AFactoryVehiclePath, 28/09).

Borra `Camion_Loop` (camion con animacion fija de author_truck_loop.py) y pone `Camion_Recorrido`
(carpeta Environment, enganchado a Parking_Estacionamiento en su origen) con SK_Camion y la linea
inicial igual al recorrido de antes: derecho de oeste a este por la entrada del muro oeste, con la
calzada (a nivel 6 m afuera del muro, rampa de 4 m) y la bajada despues de la puerta este.
Si `Camion_Recorrido` ya existe no se toca: la linea es del usuario.
Con -unattended abre el mapa, guarda y cierra; con el editor abierto no guarda el nivel.
Informe: Docs/vehicle_path.json. Requiere FactoryCtycoRuntime con AFactoryVehiclePath instalado.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
LABEL, OLD = "Camion_Recorrido", "Camion_Loop"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
# Puntos en metros del estacionamiento (Blender x, y, altura del piso); en Unreal (100x, -100y, 100z).
LANE_Y, LOW = -5.5, -0.65   # afuera el piso (Piso_Exterior) esta 65 cm mas abajo
POINTS = [(-30.0, LANE_Y, LOW), (-21.3, LANE_Y, LOW), (-17.3, LANE_Y, 0.0), (-11.3, LANE_Y, 0.0),
          (0.0, LANE_Y, 0.0), (11.3, LANE_Y, 0.0), (12.8, LANE_Y, LOW), (23.0, LANE_Y, LOW)]
report = {"passed": False}

try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    cls = getattr(unreal, "FactoryVehiclePath", None)
    if cls is None:
        raise RuntimeError("Falta AFactoryVehiclePath: instalar FactoryCtycoRuntime (build_runtime_visuals.ps1 -Install)")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    park = next(a for a in level if a.get_actor_label() == "Parking_Estacionamiento")
    removed = []
    for old in level:
        if old.get_actor_label() == OLD:
            removed.append(OLD)
            actors.destroy_actor(old)
    truck = next((a for a in level if a.get_actor_label() == LABEL), None)
    created = truck is None
    if created:
        truck = actors.spawn_actor_from_class(cls, park.get_actor_location(), park.get_actor_rotation())
        truck.set_actor_label(LABEL)
        truck.set_folder_path("Environment")
        truck.attach_to_actor(park, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD, False)
        path = truck.get_editor_property("path")
        path.clear_spline_points(False)
        for x, y, z in POINTS:
            path.add_spline_point(unreal.Vector(x * 100, -y * 100, z * 100), unreal.SplineCoordinateSpace.LOCAL, False)
        for i in range(len(POINTS)):
            path.set_spline_point_type(i, unreal.SplinePointType.CURVE_CLAMPED, False)
        path.update_spline()
    truck.set_editor_property("vehicle_mesh", unreal.load_asset("/Game/FactoryCtyco/Environments/Camion/SK_Camion"))
    path = truck.get_editor_property("path")
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, created=created, removed=removed, points=path.get_number_of_spline_points(),
                  length_cm=round(path.get_spline_length(), 1))
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[VEHICLE_PATH] {error}")
finally:
    (project / "Docs/vehicle_path.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
