"""Editor Python (con L_FactoryDemo abierto): los camiones van a los muelles de carga (03/10).

- Se quita la garita con la barrera (`Cabina_Barrera`) del despacho, y la calle que `Camion_Recorrido` dibujaba a lo
  largo de su linea (RoadMesh vacio).
- La linea de `Camion_Recorrido` (y la de `Camion_Recorrido2`, que la sigue) pasa por el patio de `Muelles_Carga`, de
  oeste a este por delante de los tres cajones (sobre la linea amarilla del patio), entrando y saliendo desde afuera.
  Cruza los muros del patio: se abren despues, donde el usuario deje la linea.
- Tres `Cajon_Muelle_1..3` (AFactoryTruckBay, carpeta Muelles), uno por cajon: el eje trasero del camion estacionado
  queda junto al tope de ruedas, mirando al patio. Su maniobra se engancha sola a la linea, 12 m mas adelante: el
  camion pasa el cajon, frena ahi y entra marcha atras. Se queda estacionado (ParkSeconds 0): la carga en el muelle se
  hace a mano mas adelante.
Medidas del GLB de los muelles (author_muelles.py): cajones en x -12,0 / -3,8 / 4,55, tope de ruedas en y 10,6 y
linea amarilla del patio en y -10,5 (en Unreal la Y se invierte).
Informe: Docs/muelles_camiones.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
BAY_X = (-12.0, -3.8, 4.55)    # m, GLB
WHEEL_STOP_Y = 10.6           # m, GLB (Unreal: -10.6)
LANE_Y = -10.5                # m, GLB (Unreal: +10.5)
REAR_AXLE_PAST_STOP = 40.0    # cm: the rear wheels rest against the stop
YARD_HALF_X = 24.6            # m

try:
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    docks = by["Muelles_Carga"]
    d = docks.get_actor_location()
    xf = docks.get_actor_transform()
    local = lambda x_m, y_m, z=0.0: xf.transform_location(unreal.Vector(x_m * 100, -y_m * 100, z))

    # garita y calle
    removed = []
    for label in ("Cabina_Barrera",):
        if label in by:
            actors.destroy_actor(by[label])
            removed.append(label)
    truck = by["Camion_Recorrido"]
    truck.set_editor_property("road_mesh", None)

    # la linea por el patio de los muelles (afuera, al piso exterior: -55)
    outside_z = -55.0
    yard_z = d.z
    lane = [(-YARD_HALF_X - 16, outside_z), (-YARD_HALF_X - 3, outside_z), (-YARD_HALF_X + 3, None),
            (YARD_HALF_X - 3, None), (YARD_HALF_X + 3, outside_z), (YARD_HALF_X + 16, outside_z)]
    path = truck.get_component_by_class(unreal.SplineComponent)
    path.clear_spline_points(False)
    for x_m, z in lane:
        p = local(x_m, LANE_Y)
        path.add_spline_point(unreal.Vector(p.x, p.y, yard_z if z is None else z), unreal.SplineCoordinateSpace.WORLD, False)
    for i in range(path.get_number_of_spline_points()):
        path.set_spline_point_type(i, unreal.SplinePointType.LINEAR, False)
    path.update_spline()
    truck.rerun_construction_scripts() if hasattr(truck, "rerun_construction_scripts") else None
    report["linea"] = [[round(c) for c in (path.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD).x,
                                           path.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD).y,
                                           path.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD).z)]
                       for i in range(path.get_number_of_spline_points())]

    # los tres cajones
    bays = []
    for i, x_m in enumerate(BAY_X, start=1):
        label = f"Cajon_Muelle_{i}"
        bay = by.get(label)
        spot = local(x_m, WHEEL_STOP_Y, 0.0)
        spot = unreal.Vector(spot.x, spot.y, yard_z)
        # el eje trasero, del tope hacia el patio
        out = xf.transform_direction(unreal.Vector(0, 1, 0))
        spot = spot + out * REAR_AXLE_PAST_STOP
        yaw = docks.get_actor_rotation().yaw + 90.0
        if bay is None:
            bay = actors.spawn_actor_from_class(unreal.FactoryTruckBay, spot, unreal.Rotator(0, 0, yaw))
            bay.set_actor_label(label)
            bay.set_folder_path("Muelles")
        else:
            bay.set_actor_location_and_rotation(spot, unreal.Rotator(0, 0, yaw), False, False)
        bay.set_editor_property("line", truck)
        bay.reconnect()
        join = bay.join_point()
        bays.append({"cajon": label, "lugar": [round(spot.x), round(spot.y), round(spot.z)], "yaw": round(yaw, 1),
                     "maniobra_cm": round(bay.length()), "enganche": [round(join.x), round(join.y), round(join.z)]})
    report.update(quitados=removed, cajones=bays)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = len(bays) == 3 and all(b["maniobra_cm"] > 500 for b in bays)
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[MUELLES_CAMIONES] " + report["error"])
(project / "Docs/muelles_camiones.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
