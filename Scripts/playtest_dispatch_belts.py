"""PIE: cintas de despacho que se prenden con E en su botonera y se detienen al llenarse.

1. Al empezar las cintas estan apagadas: no sale ninguna caja.
2. El robot se para frente a cada botonera y usa E (UFactoryGatheringComponent.interact, el mismo
   camino que la tecla): la cinta se prende.
3. Salen cajas (desde distintos lugares a lo ancho) hasta que no entran mas en fila (GetCapacity); la
   cinta se apaga sola y aparece el cartel rojo encima. Prender la cinta no deja mensajes en el HUD.
4. Clic en el cartel (ClickSign, lo que llama el clic del mouse) abre el detalle; E con la cinta
   llena no agrega cajas.
Captura: Docs/dispatch_belts_play.png. Informe: Docs/dispatch_belts_play.json. Cierra el editor.
Lanzar con -ExecCmds="py <lanzador>" (ver Docs/CAJAS_DESPACHO.md).
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "samples": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")


def phase(name):
    unreal.log(f"[DISPATCH_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def sample():
    row = {"t": round(time.monotonic() - state["play"], 1)}
    for b in state["belts"]:
        boxes = [c for c in b.get_components_by_class(unreal.StaticMeshComponent)
                 if c.static_mesh and c.static_mesh.get_name() == "SM_CajaDespacho"]
        row[b.get_actor_label()] = {"count": b.get_box_count(), "on": b.active, "full": b.full,
                                    "x": [round(c.get_editor_property("relative_location").x, 1) for c in boxes],
                                    "y": sorted((round(c.get_editor_property("relative_location").y, 1) for c in boxes), reverse=True)}
    report["samples"].append(row)
    return row


def press_at(belt):
    """Para al robot 80 cm frente a la botonera (su frente es el +Y de la malla) y usa E."""
    pawn = state["pawn"]
    knob = belt.get_editor_property("button").panel  # botonera: actor aparte (AFactoryBeltButton)
    spot = knob.get_world_location()
    front = knob.get_right_vector() * 80.0
    pawn.set_actor_location(unreal.Vector(spot.x + front.x, spot.y + front.y, pawn.get_actor_location().z), False, True)
    state["gathering"].interact()


def finish():
    (project / "Docs/dispatch_belts_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def tick(delta):
    # take_high_res_screenshot procesa Slate y vuelve a llamar este callback desde adentro: sin reentrar.
    if state.get("busy"):
        return
    state["busy"] = True
    try:
        step()
    finally:
        state["busy"] = False


def step():
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 170:
            raise RuntimeError("La prueba no termino a tiempo")
        name = state["phase"]
        if name == "warmup" and age > 8:
            levels.editor_request_begin_play()
            phase("spawn")
        elif name == "spawn":
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            state.update(world=worlds[0], pawn=pawn, play=time.monotonic(),
                         gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
            state["belts"] = sorted(unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryDispatchBelt),
                                    key=lambda b: b.get_actor_label())
            check("dos_cintas", len(state["belts"]) == 2, found=len(state["belts"]))
            phase("idle")
        elif name == "idle" and age > 4:
            row = sample()
            check("apagadas_al_empezar", all(row[b.get_actor_label()]["count"] == 0 and not b.active for b in state["belts"]),
                  row=row)
            for b in state["belts"]:
                press_at(b)
            check("e_prende_las_cintas", all(b.active for b in state["belts"]))
            check("sin_aviso_al_prender", state["gathering"].notification == "", notice=state["gathering"].notification)
            phase("running")
        elif name == "running":
            if age - state.get("last", -10) >= 2:
                state["last"] = age
                sample()
            if all(b.full for b in state["belts"]) or age > 40:
                row = sample()
                for b in state["belts"]:
                    r = row[b.get_actor_label()]
                    check(f"{b.get_actor_label()}_llena", b.full and not b.active and r["count"] == b.get_capacity(), row=r)
                    check(f"{b.get_actor_label()}_primera_al_final", abs(r["y"][0] - b.end.y) < 1, y=r["y"])
                    check(f"{b.get_actor_label()}_distintos_lugares", max(r["x"]) - min(r["x"]) >= 10, x=r["x"])
                    # las cajas tienen que estar de verdad sobre la cinta de su maquina (en el mundo)
                    machine = b.get_attach_parent_actor().get_actor_location()
                    boxes = [c for c in b.get_components_by_class(unreal.StaticMeshComponent)
                             if c.static_mesh and c.static_mesh.get_name() == "SM_CajaDespacho"]
                    far = [round((c.get_world_location() - machine).length()) for c in boxes]
                    check(f"{b.get_actor_label()}_cajas_sobre_la_maquina", max(far) < 500, cm_from_machine=far)
                    c0 = boxes[0]
                    report.setdefault("debug", {})[b.get_actor_label()] = {
                        "box_world": [round(v) for v in c0.get_world_location().to_tuple()],
                        "box_scale": [round(v, 2) for v in c0.get_world_scale().to_tuple()],
                        "box_visible": c0.is_visible(), "box_hidden": c0.get_editor_property("hidden_in_game"),
                        "box_parent": str(c0.get_attach_parent().get_name() if c0.get_attach_parent() else None),
                        "box_mesh": c0.static_mesh.get_path_name(),
                        "sign_world": [round(v) for v in b.sign.get_world_location().to_tuple()],
                        "machine": [round(v) for v in machine.to_tuple()]}
                phase("sign")
        elif name == "sign" and age > 1.5:
            for b in state["belts"]:
                scale = b.sign.get_editor_property("relative_scale3d").x
                check(f"{b.get_actor_label()}_cartel_visible", not b.sign.get_editor_property("hidden_in_game") and abs(scale - 1) < 0.05,
                      scale=round(scale, 3), text=str(b.sign_text.get_editor_property("text")))
            first = state["belts"][0]
            check("clic_en_cartel_abre_detalle", first.click_sign(first.sign) and first.detail_open)
            check("clic_en_otra_cosa_no", not first.click_sign(first.get_editor_property("button").panel))
            print("[captura desactivada]", 1440, 900, str(project / "Docs/dispatch_belts_play.png"))
            phase("full_press")
        elif name == "full_press" and age > 3:
            state["before"] = [b.get_box_count() for b in state["belts"]]
            press_at(state["belts"][0])
            check("e_con_cinta_llena_no_prende", not state["belts"][0].active and state["gathering"].notification == "")
            phase("full_wait")
        elif name == "full_wait" and age > 4:
            check("llena_no_agrega", [b.get_box_count() for b in state["belts"]] == state["before"])
            report["passed"] = True
            finish()
        elif name == "quit" and age > 2:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            unreal.SystemLibrary.quit_editor()
    except Exception:
        report["error"] = traceback.format_exc()
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[DISPATCH_PLAY] registrado")
