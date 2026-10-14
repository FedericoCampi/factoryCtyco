"""Editor Python (04/10): Pasarela_L2 armada por piezas, como Pasarela_L.

Pasarela_L2 era una copia de la malla fija vieja (SM_PasarelaL), estirada: no tenia manijas. La cambia por un
AFactoryWalkwayL (mismo lugar, giro, nombre y carpeta, escala 1) con las piezas de Pasarela_L; el estiramiento de la
malla fija pasa a las medidas (lo que corre en Y del actor: las barandas del brazo A y el extremo del brazo B; lo que
corre en X: las del brazo B y el extremo del A). Sus cuatro barandas y las dos puntas se arrastran en el viewport y el
piso las sigue. Con el editor abierto no guarda el nivel (guardar a mano). Informe: Docs/pasarela_l2.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
LABEL, MODEL = "Pasarela_L2", "Pasarela_L"
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

try:
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    old, model = by[LABEL], by[MODEL]
    if isinstance(old, unreal.FactoryWalkwayL):
        report.update(passed=True, ya_era_por_piezas=True)
    else:
        t = old.get_actor_transform()
        scale = t.scale3d
        folder = str(old.get_folder_path())
        actors.destroy_actor(old)
        new = actors.spawn_actor_from_class(unreal.FactoryWalkwayL, t.translation, t.rotation.rotator())
        new.set_actor_label(LABEL)
        new.set_folder_path(folder)
        # las medidas de la L sin estirar (las de la clase, que calzan con SM_PasarelaL a escala 1) por el estiramiento
        base = unreal.get_default_object(unreal.FactoryWalkwayL)
        for prop, factor in (("outer_a", scale.y), ("inner_a", scale.y), ("end_b", scale.y),
                             ("outer_b", scale.x), ("inner_b", scale.x), ("end_a", scale.x)):
            new.set_editor_property(prop, base.get_editor_property(prop) * factor)
        for prop in ("deck_mesh", "rail_mesh", "post_mesh"):
            new.set_editor_property(prop, model.get_editor_property(prop))
        new.rebuild()
        loc = new.get_actor_location()
        report.update(passed=new.deck.get_instance_count() > 0, estiramiento=[round(scale.x, 2), round(scale.y, 2)],
                      lugar=[round(loc.x), round(loc.y), round(loc.z)], yaw=round(new.get_actor_rotation().yaw, 1),
                      medidas={p: round(new.get_editor_property(p), 1) for p in ("outer_a", "inner_a", "end_a", "outer_b", "inner_b", "end_b")},
                      piezas=[new.deck.get_instance_count(), new.rails.get_instance_count(), new.posts.get_instance_count()])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PASARELA_L2] " + report["error"])
(project / "Docs/pasarela_l2.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
