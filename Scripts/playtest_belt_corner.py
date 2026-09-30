"""PIE: cinta de esquina, cinta inclinada y postes (30/09). Abre L_FactoryDemo, no guarda nada y cierra el editor.

En el piso de la fabrica pone (solo para la prueba) una esquina (SM_CintaEsquina, TurnDegrees -90) y, en su salida,
una cinta recta que sube 12 grados. En Play:
1. La esquina se engancha sola con la recta (su salida esta en la entrada de la otra).
2. La recta inclinada tiene postes debajo (la punta alta queda en el aire); la esquina, apoyada en el piso, no.
3. Con una caja en mano, E junto a la mitad de la curva la apoya ahi; la caja sigue la curva (sale girada 90 grados),
   pasa a la recta y sube por la pendiente.
4. Las cintas de carga de siempre siguen igual: Cinta_Carga3 -> Cinta_Carga4.
Lanzar con -ExecCmds="py <lanzador sin espacios>" (ver ESTACIONAMIENTO.md). Informe: Docs/belt_corner_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "checks": {}, "samples": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
BOX = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho")
build = json.loads((project / "SourceAssets/CintaEsquina/cinta_esquina_build.json").read_text(encoding="utf-8"))
ORIGIN = unreal.Vector(-600, 700, 0)   # piso de la fabrica
PITCH = 12.0

# --- armado en el nivel del editor (no se guarda) ---
corner = actors.spawn_actor_from_class(unreal.FactoryLoadingBelt, ORIGIN, unreal.Rotator(0, 0, 0))
corner.set_actor_label("Prueba_Esquina")
corner.belt.set_static_mesh(unreal.load_asset("/Game/FactoryCtyco/Environments/CintaEsquina/SM_CintaEsquina"))
corner.set_editor_property("length", build["length_cm"])
corner.set_editor_property("turn_degrees", -90.0)
exit_point = corner.get_actor_transform().transform_location(unreal.Vector(build["exit_unreal_cm"][0], build["exit_unreal_cm"][1], 0))
ramp = actors.spawn_actor_from_class(unreal.FactoryLoadingBelt, exit_point, unreal.Rotator(roll=0, pitch=PITCH, yaw=-90))
ramp.set_actor_label("Prueba_Rampa")
ramp.belt.set_static_mesh(unreal.load_asset("/Game/FactoryCtyco/Environments/CintaCarga/SM_CintaCarga"))
TEST = [corner, ramp]


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/belt_corner_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def tick(delta):
    if state.get("busy"):
        return
    state["busy"] = True
    try:
        step()
    except Exception:
        report["error"] = traceback.format_exc()
        finish()
    finally:
        state["busy"] = False


def step():
    age = time.monotonic() - state["t"]
    name = state["phase"]
    if time.monotonic() - state["start"] > 200 and name != "quit":
        raise RuntimeError("La prueba no termino a tiempo")
    if name == "warmup" and age > 8:
        levels.editor_request_begin_play()
        phase("spawn")
    elif name == "spawn":
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn is None or age < 2:
            return
        belts = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryLoadingBelt)}
        guide = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryGuide)
        if guide:
            guide[0].call_method("SkipIntro")
        c, r = belts["Prueba_Esquina"], belts["Prueba_Rampa"]
        state.update(pawn=pawn, c=c, r=r)
        outs = {k: sorted(o.get_actor_label() for o in v.get_outputs()) for k, v in belts.items() if not v.tags}
        check("esquina_se_engancha", outs["Prueba_Esquina"] == ["Prueba_Rampa"], outputs=outs)
        check("cintas_de_siempre_igual", outs.get("Cinta_Carga3") == ["Cinta_Carga4"], outputs=outs)
        count = lambda b: b.get_component_by_class(unreal.InstancedStaticMeshComponent).get_instance_count()
        check("postes_bajo_la_rampa", count(r) >= 1 and count(c) == 0, rampa=count(r), esquina=count(c),
              punta_alta_cm=round(r.get_delivery_point().z))
        # la caja: a mano, junto a la mitad de la curva (del lado de afuera)
        carry = pawn.get_component_by_class(unreal.FactoryCarryComponent)
        carry.take(BOX)
        # a la altura del primer cuarto de la curva, del lado de adentro (el centro del arco esta en local (0, -radio))
        first = c.world_at(c.get_editor_property("length") * 0.25)
        centre = c.get_actor_transform().transform_location(unreal.Vector(0, -c.get_editor_property("length") / 1.5708, 0))
        inward = centre - first
        inward.z = 0
        spot = first + inward.normal() * 90
        pawn.set_actor_location(unreal.Vector(spot.x, spot.y, c.get_actor_location().z + 100), False, True)   # el gerente arranca en otro piso
        pawn.get_component_by_class(unreal.FactoryGatheringComponent).interact()
        check("caja_en_la_curva", c.get_box_count() == 1, count=c.get_box_count())
        phase("ride")
    elif name == "ride":
        c, r = state["c"], state["r"]
        boxes = [comp for b in (c, r) for comp in b.get_components_by_class(unreal.StaticMeshComponent)
                 if comp.static_mesh == BOX]
        if boxes:
            t = boxes[0].get_world_transform()
            report["samples"].append({"t": round(age, 1), "on": boxes[0].get_owner().get_actor_label(),
                                      "loc": [round(v) for v in t.translation.to_tuple()], "yaw": round(t.rotation.rotator().yaw),
                                      "pitch": round(t.rotation.rotator().pitch)})
        if r.get_box_count() == 1 and boxes and boxes[0].get_owner() == r:
            state.setdefault("on_ramp", age)
            if age - state["on_ramp"] > 2.5:
                on_corner = [s for s in report["samples"] if s["on"] == "Prueba_Esquina"]
                on_ramp = [s for s in report["samples"] if s["on"] == "Prueba_Rampa"]
                turned = abs(((on_corner[-1]["yaw"] - on_corner[0]["yaw"]) + 180) % 360 - 180)
                check("sigue_la_curva", turned > 45, giro=turned, desde=on_corner[0], hasta=on_corner[-1])
                check("sube_la_rampa", on_ramp[-1]["loc"][2] > on_ramp[0]["loc"][2] + 20 and on_ramp[-1]["pitch"] > 5,
                      desde=on_ramp[0], hasta=on_ramp[-1])
                report["passed"] = True
                finish()
        elif age > 30:
            check("pasa_a_la_rampa", False, esquina=c.get_box_count(), rampa=r.get_box_count())
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        for a in TEST:
            actors.destroy_actor(a)
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
