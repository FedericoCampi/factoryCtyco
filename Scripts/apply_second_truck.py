"""Editor Python: segundo camion sobre la misma linea que Camion_Recorrido (28/09).

Pone `Camion_Recorrido2` (AFactoryVehiclePath, carpeta Environment, enganchado al estacionamiento) con
LeadPath = Camion_Recorrido: recorre esa misma linea (editar solo la del primero). Sale StartDelay
segundos despues y en el editor se ve 9 m detras del primero (EditorPreviewDistance -900).
Si ya existe solo le vuelve a poner la malla. Con -unattended abre el mapa, guarda y cierra.
Informe: Docs/second_truck.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
LEAD, LABEL = "Camion_Recorrido", "Camion_Recorrido2"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
report = {"passed": False}

try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    lead = next(a for a in level if a.get_actor_label() == LEAD)
    park = next(a for a in level if a.get_actor_label() == "Parking_Estacionamiento")
    truck = next((a for a in level if a.get_actor_label() == LABEL), None)
    created = truck is None
    if created:
        truck = actors.spawn_actor_from_class(unreal.FactoryVehiclePath, lead.get_actor_location(), lead.get_actor_rotation())
        truck.set_actor_label(LABEL)
        truck.set_folder_path("Environment")
        truck.attach_to_actor(park, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD, False)
        truck.set_editor_property("start_delay", 8.0)
        truck.set_editor_property("editor_preview_distance", -900.0)
    truck.modify()
    truck.set_editor_property("lead_path", lead)
    mesh = lead.get_editor_property("vehicle_mesh")
    truck.set_editor_property("vehicle_mesh", mesh)
    truck.get_editor_property("vehicle").set_skinned_asset_and_update(mesh)
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, created=created, lead=LEAD, mesh=mesh.get_path_name() if mesh else None)
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[SECOND_TRUCK] {error}")
finally:
    (project / "Docs/second_truck.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
