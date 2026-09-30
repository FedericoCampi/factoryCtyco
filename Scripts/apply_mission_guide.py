"""Intro y guía de la primera misión en L_FactoryDemo (29/09).

Coloca (o actualiza) el actor `Guia_Mision` (AFactoryGuide, FactoryCtycoRuntime) con los pasos de la misión 1 apuntando
a los actores del nivel, y renombra la parada del ascensor del estacionamiento viejo a "DESPACHO".
Idempotente: correrlo de nuevo reescribe los pasos. Guarda el nivel. Informe: Docs/mission_guide.json.
Correr en el editor con L_FactoryDemo abierto (o sin editor: -ExecutePythonScript=Scripts/apply_mission_guide.py).
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_name() != "L_FactoryDemo":
    assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")

by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}


def need(label):
    actor = by_label.get(label)
    if not actor:
        raise RuntimeError(f"Falta {label} en L_FactoryDemo")
    return actor


Goal = unreal.FactoryGuideGoal
STEPS = [
    # (título, pista, flecha, objetivo, actor del objetivo, radio, piso a resaltar en el ascensor)
    ("Andá al despacho", "Subí a la plataforma y entrá: el ascensor está en la recepción. Bajá al DESPACHO.",
     "Ascensor_Empleados", Goal.REACH, "Ascensor_Estacionamiento", 450.0, "DESPACHO"),   # 30/09: flecha sobre el ascensor
    ("Abrí el portón de camiones", "Pulsá E en la botonera de la columna para que entren los camiones.",
     "Porton_Camiones", Goal.OPEN_GATE, "Porton_Camiones", 450.0, ""),
    ("Encendé la cinta de despacho", "Acercate a la botonera y pulsá E.",
     "Botonera_Cinta1", Goal.SWITCH_ON_BELT, "Despacho_Cajas", 450.0, ""),
    ("Agarrá una caja", "Parate junto a la cinta y pulsá E para levantarla.",
     "Despacho_Cajas", Goal.CARRY_BOX, None, 450.0, ""),
    ("Cargá la caja en la cinta del camión", "Llevala a la punta amarilla y pulsá E.",
     "Cinta_Carga3", Goal.LOAD_BOX, None, 450.0, ""),
    ("Despachá 20 paquetes", "Llená el camión y abrí la barrera para que salga.",
     None, Goal.DELIVER, None, 450.0, ""),
]

# The old parking is the dispatch area now: its elevator stop says so.
parking_elevator = need("Ascensor_Estacionamiento")
parking_elevator.set_editor_property("stop_name", "DESPACHO")

guide = by_label.get("Guia_Mision")
if not guide:
    guide = actors.spawn_actor_from_class(unreal.FactoryGuide, unreal.Vector(0, 0, 0))
    guide.set_actor_label("Guia_Mision")
guide.set_folder_path("Gameplay")

steps = []
for title, hint, arrow, goal, goal_actor, radius, stop in STEPS:
    step = unreal.FactoryGuideStep()
    step.set_editor_property("title", title)
    step.set_editor_property("hint", hint)
    step.set_editor_property("arrow_target", need(arrow) if arrow else None)
    step.set_editor_property("goal", goal)
    step.set_editor_property("goal_actor", need(goal_actor) if goal_actor else None)
    step.set_editor_property("radius", radius)
    step.set_editor_property("elevator_stop", stop)
    steps.append(step)
guide.set_editor_property("steps", steps)
guide.set_editor_property("skip_intro", False)

saved = levels.save_current_level()
report = {
    "guide": guide.get_actor_label(),
    "slides": [s.get_editor_property("title") for s in guide.get_editor_property("slides")],
    "steps": [{"title": s.get_editor_property("title"),
               "arrow": s.get_editor_property("arrow_target").get_actor_label() if s.get_editor_property("arrow_target") else None,
               "goal": str(s.get_editor_property("goal"))} for s in guide.get_editor_property("steps")],
    "parking_stop": parking_elevator.get_editor_property("stop_name"),
    "saved": bool(saved),
}
(project / "Docs/mission_guide.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
unreal.log(f"[MISSION_GUIDE] {report}")
