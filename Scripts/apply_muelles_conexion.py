"""Editor Python (con L_FactoryDemo abierto): las cintas llegan al muelle, pasos de camion en los muros, calle y garita
en el patio de los muelles (03/10). Sobre la escena como la dejo el usuario (muelles a escala 0,75, cajones y linea
acomodados).

1. Pasos en los muros: donde la linea de `Camion_Recorrido` cruza el muro del patio de `Muelles_Carga` (oeste, este o
   el del frente) se anota el lugar en SourceAssets/Muelles/truck_openings.json (metros del GLB) para que
   author_muelles.py abra ahi un paso de OPENING_M de ancho (despues: Blender + import_muelles.py). Los puntos de la
   linea que caen dentro del patio bajan al piso del patio.
2. Cintas al muelle: desde la punta de `Cinta_Carga4` siguen `Cinta_Muelle_1..5` (copias de Cinta_Carga4 y de
   Cinta_Esquina, carpeta Muelles): recta hacia el muelle subiendo a TOP_Z (para pasar sobre el anden de 1,2 m), curva,
   recta de costado por dentro del edificio, curva y recta hasta el borde del anden detras de `Cajon_Muelle_1`. El
   camion estacionado ahi carga de esa cinta (AFactoryVehiclePath, BayLoadReach) y sale lleno.
3. Garita y calle: `Cabina_Barrera` (AFactoryGateBarrier, piezas de /Game/FactoryCtyco/Environments/CabinaBarrera)
   dentro del patio, junto a la entrada (BOOTH_PAST_WALL despues del muro que cruza la linea al entrar), con el brazo
   cruzando la linea; y la calle vuelve a dibujarse a lo largo de la linea (RoadMesh = SM_CalleTramo).
   La garita va en la entrada y no en la salida: el cajon del este se engancha a la linea casi en el muro de salida y
   un camion yendo hacia alla frenaria en la barrera antes de llegar.
Informe: Docs/muelles_conexion.json.
"""
import json
import math
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
YARD_X, YARD_FRONT_Y, YARD_BACK_Y = 24.0, -22.0, 16.5   # GLB m: side walls at x +-24, front wall at y -22
OPENING_M = 5.0          # ancho del paso (m, en el mundo)
TOP_Z = 125.0            # alto de las cintas nuevas (arriba de la cinta, cm): el anden esta a 1,2 m del patio
BELT_TOP = 88.0          # de la base del actor de Cinta_Carga4 a la cinta
BOOTH_PAST_WALL = 600.0  # cm despues del muro de entrada, a lo largo de la linea
ARM_REACH = 160.0        # el poste a esta distancia de la linea; el brazo (310) la cruza
END_BEHIND_AXLE = 90.0   # la cinta termina a esto del eje trasero del camion estacionado (hacia el anden)


def rnd(v):
    return [round(v.x), round(v.y), round(v.z)]


try:
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    docks = by["Muelles_Carga"]
    dxf = docks.get_actor_transform()
    scale = docks.get_actor_scale3d()
    yard_z = docks.get_actor_location().z
    to_glb = lambda w: (lambda l: (l.x / 100, -l.y / 100, l.z / 100))(dxf.inverse_transform_location(w))
    truck = by["Camion_Recorrido"]
    line = truck.get_component_by_class(unreal.SplineComponent)

    # 1. pasos donde la linea cruza los muros del patio, y la linea al piso del patio
    openings, prev = [], None
    length = line.get_spline_length()
    steps = int(length / 20)
    for i in range(steps + 1):
        w = line.get_location_at_distance_along_spline(length * i / steps, unreal.SplineCoordinateSpace.WORLD)
        g = to_glb(w)
        if prev is not None:
            for side, axis, wall in (("Left", 0, -YARD_X), ("Right", 0, YARD_X), ("Front", 1, YARD_FRONT_Y)):
                a, b = prev[axis], g[axis]
                if (a - wall) * (b - wall) < 0:
                    t = (wall - a) / (b - a)
                    other = 1 - axis
                    at = prev[other] + (g[other] - prev[other]) * t
                    inside = (YARD_FRONT_Y <= at <= YARD_BACK_Y) if axis == 0 else (-YARD_X <= at <= YARD_X)
                    if inside:
                        across = scale.y if axis == 0 else scale.x
                        openings.append({"wall": side, "at": round(at, 3), "half": round(OPENING_M / 2 / across, 3),
                                         "world": rnd(w), "distance": round(length * i / steps)})
        prev = g
    (project / "SourceAssets/Muelles/truck_openings.json").write_text(json.dumps(openings, indent=1), encoding="utf-8")
    lowered = []
    for i in range(line.get_number_of_spline_points()):
        w = line.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
        g = to_glb(w)
        if abs(g[0]) < YARD_X and YARD_FRONT_Y < g[1] < YARD_BACK_Y and abs(w.z - yard_z) > 1:
            line.set_location_at_spline_point(i, unreal.Vector(w.x, w.y, yard_z), unreal.SplineCoordinateSpace.WORLD, False)
            lowered.append(i)
    line.update_spline()
    report.update(pasos=openings, puntos_bajados=lowered)

    # 2. cintas hasta el cajon 1
    straight_t, corner_t = by["Cinta_Carga4"], by["Cinta_Esquina"]
    for old in [a for a in by.values() if a.get_actor_label().startswith("Cinta_Muelle_")]:
        actors.destroy_actor(old)
    bay = by["Cajon_Muelle_1"]
    fwd = bay.get_actor_forward_vector()
    target = bay.get_actor_location() - fwd * END_BEHIND_AXLE
    s = straight_t.get_delivery_point()
    heading = (straight_t.world_at(50) - straight_t.world_at(0))
    heading = unreal.Vector(heading.x, heading.y, 0).normal()
    radius = corner_t.get_editor_property("length") / math.radians(abs(corner_t.get_editor_property("turn_degrees")))
    # en ejes de la cinta: u a lo largo (heading), v de costado
    side = unreal.Vector(-heading.y, heading.x, 0)
    du, dv = (target - s).dot(heading), (target - s).dot(side)
    cross_u = du - 2 * radius - 280.0   # la recta de costado queda 2,8 m antes del final
    actor_z = TOP_Z - BELT_TOP + 0.0
    made = []

    def straight(label, a, b, z_from, z_to):
        belt = actors.duplicate_actor(straight_t)
        belt.set_actor_label(label)
        flat = unreal.Vector(b.x - a.x, b.y - a.y, 0)
        run = flat.length()
        pitch = math.degrees(math.atan2(z_to - z_from, run))
        belt.set_actor_scale3d(unreal.Vector(1, 1, 1))
        belt.set_actor_rotation(unreal.Rotator(0, pitch, math.degrees(math.atan2(flat.y, flat.x))), False)
        belt.set_actor_location(unreal.Vector(a.x, a.y, z_from - BELT_TOP), False, False)
        belt.set_editor_property("length", math.hypot(run, z_to - z_from))
        belt.set_editor_property("next_belt", None)
        belt.tags = []
        belt.set_folder_path("Muelles")
        belt.build_supports()
        made.append(belt)
        return belt

    def corner(label, a, yaw, expected_end):
        """Cuarto de vuelta desde a mirando a yaw; se espeja si hace falta para terminar en expected_end."""
        belt = actors.duplicate_actor(corner_t)
        belt.set_actor_label(label)
        belt.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        belt.set_actor_location(unreal.Vector(a.x, a.y, TOP_Z - BELT_TOP), False, False)
        for mirror in (1, -1):
            belt.set_actor_scale3d(unreal.Vector(1, mirror, 1))
            e = belt.get_delivery_point()
            if unreal.Vector(e.x - expected_end.x, e.y - expected_end.y, 0).length() < 30:
                break
        belt.set_editor_property("next_belt", None)
        belt.tags = []
        belt.set_folder_path("Muelles")
        belt.build_supports()
        made.append(belt)
        return belt

    toward = side if dv > 0 else side * -1   # de costado, hacia el cajon
    cross_u = du - 2 * radius - 280.0       # la ultima recta queda de 2,8 m
    if cross_u < 50:
        raise RuntimeError("El cajon esta demasiado cerca de Cinta_Carga4 para dar las dos curvas")
    flat = lambda v: unreal.Vector(v.x, v.y, 0)
    yaw_h = math.degrees(math.atan2(heading.y, heading.x))
    yaw_s = math.degrees(math.atan2(toward.y, toward.x))
    p1 = flat(s) + heading * cross_u
    straight("Cinta_Muelle_1", s, p1, s.z, TOP_Z)
    c1_end = p1 + heading * radius + toward * radius
    corner("Cinta_Muelle_2", p1, yaw_h, c1_end)
    p3 = p1 + heading * radius + toward * (abs(dv) - radius)
    straight("Cinta_Muelle_3", c1_end, p3, TOP_Z, TOP_Z)
    c2_end = p3 + toward * radius + heading * radius
    corner("Cinta_Muelle_4", p3, yaw_s, c2_end)
    straight("Cinta_Muelle_5", c2_end, flat(target), TOP_Z, TOP_Z)
    rows = []
    for belt in made:
        rows.append({"cinta": belt.get_actor_label(), "desde": rnd(belt.world_at(0)), "hasta": rnd(belt.get_delivery_point())})
    gaps = [round((made[i + 1].world_at(0) - made[i].get_delivery_point()).length(), 1) for i in range(len(made) - 1)]
    gaps.insert(0, round((made[0].world_at(0) - straight_t.get_delivery_point()).length(), 1))
    end_gap = round(unreal.Vector(made[-1].get_delivery_point().x - target.x, made[-1].get_delivery_point().y - target.y, 0).length(), 1)
    report.update(cintas=rows, uniones_cm=gaps, final_al_objetivo_cm=end_gap, objetivo=rnd(target))

    # 3. garita en la entrada del patio y calle
    lib = unreal.EditorAssetLibrary
    entry = next((o for o in openings if o["distance"] < length / 2), None)
    if entry is None:
        raise RuntimeError("La linea no cruza un muro del patio al entrar")
    at = entry["distance"] + BOOTH_PAST_WALL
    on = line.get_location_at_distance_along_spline(at, unreal.SplineCoordinateSpace.WORLD)
    d = line.get_direction_at_distance_along_spline(at, unreal.SplineCoordinateSpace.WORLD)
    d = unreal.Vector(d.x, d.y, 0).normal()
    left = unreal.Vector(-d.y, d.x, 0)
    # del lado del frente del patio (lejos de los cajones)
    bay_side = (bay.get_actor_location() - on).dot(left)
    out = left * (-1 if bay_side > 0 else 1)
    gate = by.get("Cabina_Barrera")
    if gate is None:
        gate = actors.spawn_actor_from_class(unreal.FactoryGateBarrier, on, unreal.Rotator())
        gate.set_actor_label("Cabina_Barrera")
    gate.set_folder_path("Muelles")
    booth_at = on + out * (ARM_REACH + 170.0)
    gate.set_actor_location(unreal.Vector(booth_at.x, booth_at.y, yard_z), False, False)
    yaw = math.degrees(math.atan2(d.y, d.x))
    gate.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    folder = "/Game/FactoryCtyco/Environments/CabinaBarrera"
    for comp, mesh in (("booth", "SM_Cabina"), ("roof", "SM_CabinaTecho"), ("post", "SM_BarreraPoste"), ("arm", "SM_BarreraBrazo")):
        gate.get_editor_property(comp).set_static_mesh(unreal.load_asset(f"{folder}/{mesh}"))
    # poste entre la cabina y la linea; el brazo baja hacia la linea y la cruza
    post = gate.get_editor_property("post")
    post.set_relative_location_and_rotation(unreal.Vector(0, 170.0 if (out.dot(left) < 0) else -170.0, 0),
                                            unreal.Rotator(0, 0, 90.0 if (out.dot(left) < 0) else -90.0), False, False)
    sound = unreal.load_asset("/Game/FactoryCtyco/Environments/Ascensor2/S_Ascensor_Puerta")
    if sound:
        gate.set_editor_property("move_sound", sound)
    pivot, tip = gate.get_arm_line() if hasattr(gate, "get_arm_line") else (None, None)
    truck.set_editor_property("road_mesh", unreal.load_asset("/Game/FactoryCtyco/Environments/Calle/SM_CalleTramo"))
    truck.rerun_construction_scripts() if hasattr(truck, "rerun_construction_scripts") else None
    report["garita"] = {"lugar": rnd(gate.get_actor_location()), "yaw": round(yaw, 1), "linea_en": rnd(on),
                        "brazo": [rnd(pivot), rnd(tip)] if pivot else None}

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = len(openings) >= 2 and all(g < 20 for g in gaps) and end_gap < 30
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[MUELLES_CONEXION] " + report["error"])
(project / "Docs/muelles_conexion.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
