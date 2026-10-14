"""Editor Python (07/10): vuelve a poner el Extractor de Silicio en la fabrica, donde estaba.

El actor `Extractor_Silicio` (SkeletalMeshActor, SK_ExtractorSilicio con su animacion en loop) ya no estaba en el
nivel, pero si sus accesorios (Extractor_Baliza, _Pantalla, _Interruptor, _LuzBaliza, _LuzMirilla). Su lugar sale de
ellos (add_extractor_lights.py los ponia enganchados en posiciones fijas de la maquina): (1885, -1530, 20), girado 180 y
con escala (2, 2, 1,5). Se crea ahi, se le vuelven a enganchar los accesorios (sin moverlos) y el interruptor la vuelve a
encender. Si ya existe, no hace nada. Guarda el nivel. Informe: Docs/extractor_restaurado.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/ExtractorSilicio"
LABEL = "Extractor_Silicio"
SPOT, YAW, SCALE = unreal.Vector(1885, -1530, 20), 180.0, unreal.Vector(2.0, 2.0, 1.5)
ACCESSORIES = ("Extractor_Baliza", "Extractor_Pantalla", "Extractor_Interruptor", "Extractor_LuzBaliza", "Extractor_LuzMirilla")
report = {"passed": False}

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    machine = by.get(LABEL)
    if machine is None:
        mesh = unreal.load_asset(f"{DEST}/SK_ExtractorSilicio")
        anim = unreal.load_asset(f"{DEST}/SK_ExtractorSilicio_Anim")
        if not mesh or not anim:
            raise RuntimeError("Faltan SK_ExtractorSilicio o su animacion")
        machine = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, SPOT, unreal.Rotator(0, 0, YAW))
        machine.set_actor_label(LABEL)
        machine.set_folder_path("Environment")
        machine.set_actor_scale3d(SCALE)
        comp = machine.skeletal_mesh_component
        comp.set_skinned_asset_and_update(mesh)
        comp.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        data = comp.get_editor_property("animation_data")
        data.set_editor_property("anim_to_play", anim)
        data.set_editor_property("saved_looping", True)
        data.set_editor_property("saved_playing", True)
        comp.set_editor_property("animation_data", data)
        comp.set_editor_property("visibility_based_anim_tick_option",
                                 unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        comp.set_collision_profile_name("BlockAll")
        report["creado"] = True
    attached = []
    for label in ACCESSORIES:
        a = by.get(label)
        if a and a.get_attach_parent_actor() != machine:
            a.attach_to_actor(machine, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD, False)
            attached.append(label)
    switch = by.get("Extractor_Interruptor")
    if switch:
        switch.set_editor_property("machine", machine)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = machine.get_actor_location()
    o, e = machine.get_actor_bounds(False)
    report.update(passed=True, lugar=[round(loc.x), round(loc.y), round(loc.z)], alto_cm=round(2 * e.z),
                  caja=[round(o.x - e.x), round(o.y - e.y), round(o.x + e.x), round(o.y + e.y)],
                  enganchados=attached, escena=str(unreal.FactorySceneZone.scene_of(machine)))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[EXTRACTOR] " + report["error"])
finally:
    (project / "Docs/extractor_restaurado.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
