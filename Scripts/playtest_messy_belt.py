"""PIE: las cajas de las cintas de despacho salen desordenadas (28/09).

Prende las dos cintas (con una caja cada 0,3 s para no esperar) hasta que se llenan y comprueba:
- las cajas quedan en muchas posiciones distintas a lo ancho (no en 4 columnas);
- ninguna se encima con otra (las que se cruzan a lo ancho quedan separadas a lo largo);
- giros distintos; la cinta se llena, se detiene y muestra el cartel como antes.
Informe: Docs/messy_belt_play.json; captura Docs/messy_belt_play.png. Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "belts": {}}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")


def phase(name):
    unreal.log(f"[MESSY_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def boxes_of(belt):
    """(a lo largo, a lo ancho, giro) de cada caja, en el espacio de la cinta."""
    start, end = belt.get_editor_property("start"), belt.get_editor_property("end")
    along = (end - start).normal()
    side = along.cross(unreal.Vector(0, 0, 1)).normal()
    rows = []
    for c in belt.get_components_by_class(unreal.StaticMeshComponent):
        if c.static_mesh and c.static_mesh.get_name() == "SM_CajaDespacho":
            rel = c.get_editor_property("relative_location") - start
            rows.append((rel.dot(along), rel.dot(side), c.get_editor_property("relative_rotation").yaw))
    return rows


def finish():
    (project / "Docs/messy_belt_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
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
    if time.monotonic() - state["start"] > 170 and state["phase"] != "quit":
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
        belts = sorted(unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryDispatchBelt),
                       key=lambda b: b.get_actor_label())
        check("dos_cintas", len(belts) == 2, found=len(belts))
        for b in belts:
            b.set_editor_property("seconds_between_boxes", 0.3)
            b.set_belt_on(True)
        state.update(belts=belts, pawn=pawn)
        phase("fill")
    elif name == "fill":
        if all(b.get_editor_property("full") for b in state["belts"]):
            for b in state["belts"]:
                rows = boxes_of(b)
                spacing = b.get_editor_property("box_spacing")
                same = spacing * 0.95
                sides = sorted({round(r[1]) for r in rows})
                yaws = sorted({round(r[2]) for r in rows})
                overlaps = [(round(a[0]), round(a[1]), round(c[0]), round(c[1])) for i, a in enumerate(rows) for c in rows[i + 1:]
                            if abs(a[1] - c[1]) < same - 4 and abs(a[0] - c[0]) < spacing - 4]  # 4 cm: el bamboleo
                label = b.get_actor_label()
                report["belts"][label] = {"boxes": len(rows), "capacity_hint": b.get_capacity(),
                                          "distinct_sides_cm": len(sides), "distinct_yaws": len(yaws)}
                check(f"{label}_desordenadas", len(sides) > 8, distinct=len(sides), sample=sides[:12])
                check(f"{label}_sin_encimarse", not overlaps, overlaps=overlaps[:5])
                check(f"{label}_giros_distintos", len(yaws) > 6, distinct=len(yaws))
                check(f"{label}_llena_y_detenida", not b.get_editor_property("active") and len(rows) > 10, boxes=len(rows))
            belt = state["belts"][0]
            spot = belt.get_actor_transform().transform_location(unreal.Vector(0, 430, 100))  # delante del final de la cinta
            state["pawn"].set_actor_location(spot, False, True)
            phase("aim")
        elif age > 120:
            check("se_llenan", False, full=[b.get_editor_property("full") for b in state["belts"]],
                  boxes=[b.get_box_count() for b in state["belts"]])
    elif name == "aim" and age > 1.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/messy_belt_play.png"))
        phase("shot")
    elif name == "shot" and age > 1.5:
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[MESSY_PLAY] registrado")
