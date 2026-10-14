"""Editor Python (07/10): el techo de la fabrica solo en Play, no mientras se edita.

Pone la losa y las lamparas del techo de la fabrica (Techo_Fabrica_Losa, Techo_Fabrica_Lampara_*, de apply_techos.py)
en la capa LAYER y la oculta en el editor. Las capas solo ocultan en los visores del editor: en Play el techo esta (y en
isometrica tambien: desde el 07/10 sus piezas no llevan la etiqueta "Techo"). Las paredes subidas, los dinteles y las luces quedan a la vista.
Para verlo mientras se edita: Window -> Layers, el ojo de "Techo Fabrica". Correr de nuevo despues de apply_techos.py
(que rehace los actores). Guarda el nivel. Informe: Docs/techo_solo_play.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
LAYER = "Techo Fabrica"
PREFIXES = ("Techo_Fabrica_Losa", "Techo_Fabrica_Lampara_")
report = {"passed": False}

try:
    layers = unreal.get_editor_subsystem(unreal.LayersSubsystem)
    actors = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
              if a.get_actor_label().startswith(PREFIXES)]
    if not any(a.get_actor_label() == "Techo_Fabrica_Losa" for a in actors):
        raise RuntimeError("No esta Techo_Fabrica_Losa (correr apply_techos.py)")
    layers.create_layer(LAYER)
    for a in actors:
        a.modify()
        layers.add_actor_to_layer(a, LAYER)
    layers.set_layer_visibility(LAYER, False)
    # en Play el techo de la fabrica se ve siempre, tambien en isometrica: sin la etiqueta "Techo" (que lo ocultaba fuera
    # de la primera persona) en ninguna de sus piezas; sigue en la escena Fabrica
    untagged = 0
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label().startswith("Techo_Fabrica_") and "Techo" in [str(t) for t in a.tags]:
            a.modify()
            a.tags = [t for t in a.tags if str(t) != "Techo"]
            untagged += 1
    report["sin_etiqueta_techo"] = untagged
    hidden = [a.get_actor_label() for a in actors if a.is_hidden_ed()]
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=len(hidden) == len(actors), capa=LAYER, actores=len(actors), ocultos_en_editor=len(hidden))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[TECHO_SOLO_PLAY] " + report["error"])
finally:
    (project / "Docs/techo_solo_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
