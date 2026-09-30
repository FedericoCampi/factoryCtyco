"""Editor Python (con L_FactoryDemo abierto): botoneras de las cintas de despacho como actores sueltos.

Desde el 28/09 la botonera no es un componente de la cinta sino un actor aparte
(`AFactoryBeltButton`, propiedad `Belt`), para moverlo sin tocar la cinta. Este script pone una
`Botonera_CintaN` (carpeta Environment) por cada `Despacho_Cajas*` que todavia no tenga, donde estaba
la botonera vieja (SourceAssets/DispatchBox/panel_positions.json, guardado antes de recompilar),
con su malla, materiales y escala. Las que ya existen no se tocan. No guarda el nivel.
Requiere FactoryCtycoRuntime con AFactoryBeltButton instalado. Informe: Docs/belt_buttons.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
saved = json.loads((project / "SourceAssets/DispatchBox/panel_positions.json").read_text(encoding="utf-8"))
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "created": {}, "kept": {}}

try:
    button_class = getattr(unreal, "FactoryBeltButton", None)
    if button_class is None:
        raise RuntimeError("Falta AFactoryBeltButton: instalar FactoryCtycoRuntime (build_runtime_visuals.ps1 -Install)")
    level = actors.get_all_level_actors()
    belts = {a.get_actor_label(): a for a in level if isinstance(a, unreal.FactoryDispatchBelt)}
    buttons = [a for a in level if isinstance(a, button_class)]
    for entry in saved:
        belt = belts.get(entry["belt"])
        if belt is None:
            raise RuntimeError(f"No esta la cinta {entry['belt']}")
        existing = next((b for b in buttons if b.get_editor_property("belt") == belt), None)
        if existing:
            report["kept"][existing.get_actor_label()] = entry["belt"]
            continue
        roll, pitch, yaw = entry["rot"]
        knob = actors.spawn_actor_from_class(button_class, unreal.Vector(*entry["loc"]), unreal.Rotator(roll, pitch, yaw))
        label = "Botonera_Cinta" + entry["name"].split()[-1]
        knob.set_actor_label(label)
        knob.set_folder_path(entry["folder"] or "Environment")
        knob.set_editor_property("belt", belt)
        knob.panel.set_static_mesh(unreal.load_asset(entry["mesh"]))
        for slot, path in enumerate(entry["materials"]):
            if path:
                knob.panel.set_material(slot, unreal.load_asset(path))
        knob.panel.set_relative_scale3d(unreal.Vector(*entry["scale"]))
        report["created"][label] = entry["belt"]
    report["passed"] = True
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[BELT_BUTTONS] {error}")
(project / "Docs/belt_buttons.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
