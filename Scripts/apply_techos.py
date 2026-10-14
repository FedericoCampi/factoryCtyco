"""Editor Python (05/10): techo para la fabrica, el laboratorio y la recepcion de empleados (no para el estacionamiento
ni el muelle de camiones), y sus paredes subidas hasta el techo.

Por cada edificio mide (trazando rayos en el nivel) cada lado de su contorno cada STEP cm: donde esta la cara de afuera
de la pared y hasta que altura llega. Donde hay pared mas baja que el techo la sube hasta el techo (un panel de
WALL_THICK cm, del lado de adentro); donde no hay pared (un paso, el ascensor) deja libre hasta DOOR_CLEAR sobre el piso
y pone un dintel de ahi al techo. El techo es una losa sobre las paredes. Todo lleva la etiqueta "Techo" (en el juego
solo se ve en primera persona: la camara isometrica mira desde arriba; UFactorySceneSubsystem) y la de su escena, va en
la carpeta Techos/<edificio> y no tiene colision (no tapa los clics ni la camara, y no se alcanza).
Si ya existen, los vuelve a hacer. Con el editor abierto. Guarda el nivel. Informe: Docs/techos.json.
"""
import json
import statistics
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
STEP = 25.0
WALL_THICK = 20.0
ROOF_THICK = 25.0
DOOR_CLEAR = 260.0
LAMP_SPACING = 700.0      # cm entre lamparas
FILL_INTENSITY = 12.0     # candelas de la luz de relleno (sin sombra) por lampara, para que las paredes no queden negras
LAMP_INTENSITY = 90.0     # candelas por foco con el techo a 3,7 m (la recepcion); mas alto, a escala con la altura al cuadrado
MATS = "/Game/FactoryCtyco/Factory/Materials"
# nombre: rect (x0, y0, x1, y1) de afuera de las paredes, piso, techo (z del lado de abajo de la losa), escena, color de
# las paredes nuevas (lineal) y, si hace falta, light: cuanto de la intensidad de las lamparas (1 si no esta) y siempre:
# el techo se ve en Play con cualquier camara (si no, solo en primera persona)
BUILDINGS = {
    "Fabrica": dict(rect=(-1100, -2580, 2380, 1020), floor=0.0, roof=800.0, scene="Fabrica", wall=(0.06, 0.065, 0.07),
                    light=0.5, siempre=True),   # (07/10) muy iluminada: lamparas al 50 %; techo siempre en Play
    "Laboratorio": dict(rect=(3352, -928, 5408, 928), floor=0.0, roof=500.0, scene="Laboratorio", wall=(0.42, 0.40, 0.37)),
    "Recepcion": dict(rect=(-3712, 7110, -2852, 8280), floor=650.0, roof=1021.0, scene="Empleados", wall=(0.16, 0.05, 0.035)),
}
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
report = {"passed": False}


def color_material(name, color, rough):
    path = f"{MATS}/{name}"
    if lib.does_asset_exist(path):
        mat = unreal.load_asset(path)
    else:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
        base = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -400, 0)
        base.set_editor_property("parameter_name", "Color")
        base.set_editor_property("default_value", unreal.LinearColor(*color, 1.0))
        r = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 200)
        r.set_editor_property("r", rough)
        mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
        mel.recompile_material(mat)
        lib.save_loaded_asset(mat, False)
    return mat


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    roof_mat = color_material("M_Techo", (0.32, 0.32, 0.31), 0.8)
    lamp_mat = unreal.load_asset(f"{MATS}/M_TechoLampara") if lib.does_asset_exist(f"{MATS}/M_TechoLampara") else None
    if lamp_mat is None:
        lamp_mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_TechoLampara", MATS, unreal.Material, unreal.MaterialFactoryNew())
        glow = mel.create_material_expression(lamp_mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
        glow.set_editor_property("constant", unreal.LinearColor(4.0, 3.7, 3.3, 1.0))
        mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.recompile_material(lamp_mat)
        lib.save_loaded_asset(lamp_mat, False)
    # lo que se hizo antes se borra primero (los rayos no deben chocar con eso)
    for x in actors.get_all_level_actors():
        if str(x.get_folder_path()).startswith("Techos"):
            actors.destroy_actor(x)

    def trace(start, end):
        hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                      unreal.DrawDebugTrace.NONE, True)
        if not hit:
            return None
        t = hit.to_tuple()
        return t[5] if t[0] else None

    def block(name, folder, tags, lo, hi, material):
        center = unreal.Vector((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
        a = actors.spawn_actor_from_class(unreal.StaticMeshActor, center, unreal.Rotator(0, 0, 0))
        a.set_actor_label(name)
        a.set_folder_path(folder)
        a.set_actor_scale3d(unreal.Vector(max(hi[0] - lo[0], 1) / 100, max(hi[1] - lo[1], 1) / 100, max(hi[2] - lo[2], 1) / 100))
        c = a.static_mesh_component
        c.set_static_mesh(cube)
        c.set_material(0, material)
        c.set_collision_profile_name("NoCollision")
        a.tags = tags
        return a

    # ascensores: su planta y hasta donde llega su techo cuando sube (alli el dintel arranca mas arriba)
    lifts = []
    for x in actors.get_all_level_actors():
        if isinstance(x, unreal.FactoryElevator):
            o, e, _ = unreal.SystemLibrary.get_component_bounds(x.get_editor_property("cabin"))
            lifts.append({"x": (o.x - e.x, o.x + e.x), "y": (o.y - e.y, o.y + e.y),
                          "top": o.z + e.z + x.get_editor_property("rise_height") + 30.0})
    for bname, b in BUILDINGS.items():
        x0, y0, x1, y1 = b["rect"]
        fz, rz = b["floor"], b["roof"]
        folder = f"Techos/{bname}"
        # siempre: el techo se ve en Play tambien en isometrica (sin la etiqueta Techo), como pidio el usuario el 07/10
        tags = ([] if b.get("siempre") else ["Techo"]) + [f"Escena:{b['scene']}"]
        wall_mat = color_material(f"M_ParedTecho{bname}", b["wall"], 0.7)
        made = {"paredes": 0, "dinteles": 0}
        sides = {"-Y": ("x", y0, 1, x0, x1), "+Y": ("x", y1, -1, x0, x1), "-X": ("y", x0, 1, y0, y1), "+X": ("y", x1, -1, y0, y1)}

        def P(axis, along, across, z):
            return unreal.Vector(along, across, z) if axis == "x" else unreal.Vector(across, along, z)

        # 1) la cara de afuera de cada pared
        lines = {}
        for side, (axis, fixed, inward, lo, hi) in sides.items():
            found = []
            u = lo + STEP / 2
            while u < hi:
                hit = trace(P(axis, u, fixed - inward * 150, fz + 80), P(axis, u, fixed + inward * 250, fz + 80))
                if hit is not None:
                    found.append(hit.y if axis == "x" else hit.x)
                u += STEP
            lines[side] = statistics.median(found) if found else fixed
        # 2) cada lado, entre las caras de los lados de al lado: altura de la pared y tramos
        for side, (axis, fixed, inward, lo, hi) in sides.items():
            line = lines[side]
            lo, hi = sorted((lines["-X"], lines["+X"])) if axis == "x" else sorted((lines["-Y"], lines["+Y"]))
            count = max(1, int(round((hi - lo) / STEP)))
            step = (hi - lo) / count
            runs = []
            for i in range(count):
                u = lo + step * (i + 0.5)
                hit = trace(P(axis, u, line + inward * 12, fz + 1500), P(axis, u, line + inward * 12, fz - 100))
                top = hit.z if hit else fz
                kind = "pared" if top > fz + 60 else "hueco"
                bottom = top if kind == "pared" else fz + DOOR_CLEAR
                # sobre un ascensor, por encima de su techo cuando sube
                here = P(axis, u, line + inward * 30, fz)
                for lift in lifts:
                    if lift["x"][0] <= here.x <= lift["x"][1] and lift["y"][0] <= here.y <= lift["y"][1]:
                        kind, bottom = "hueco", max(bottom, lift["top"])
                if bottom >= rz - 2:
                    kind = "nada"
                if runs and runs[-1]["kind"] == kind and abs(runs[-1]["bottom"] - bottom) < 12:
                    runs[-1]["u1"] = u + step / 2
                    runs[-1]["bottom"] = min(runs[-1]["bottom"], bottom) if kind == "pared" else max(runs[-1]["bottom"], bottom)
                else:
                    runs.append({"kind": kind, "u0": u - step / 2, "u1": u + step / 2, "bottom": bottom})
            a0, a1 = sorted((line, line + inward * WALL_THICK))
            for k, r in enumerate(runs):
                if r["kind"] == "nada":
                    continue
                lo3 = [r["u0"], a0, r["bottom"]] if axis == "x" else [a0, r["u0"], r["bottom"]]
                hi3 = [r["u1"], a1, rz] if axis == "x" else [a1, r["u1"], rz]
                block(f"Techo_{bname}_{side}_{r['kind']}_{k}", folder, tags, lo3, hi3, wall_mat)
                made["paredes" if r["kind"] == "pared" else "dinteles"] += 1
        # la losa, de cara de afuera a cara de afuera
        roof_lo = [min(lines["-X"], lines["+X"]), min(lines["-Y"], lines["+Y"]), rz]
        roof_hi = [max(lines["-X"], lines["+X"]), max(lines["-Y"], lines["+Y"]), rz + ROOF_THICK]
        block(f"Techo_{bname}_Losa", folder, tags, roof_lo, roof_hi, roof_mat)
        # lamparas colgadas bajo la losa (la placa que brilla solo se ve en primera persona, como el techo; la luz
        # alumbra siempre), en una grilla de LAMP_SPACING
        nx = max(1, int(round((roof_hi[0] - roof_lo[0]) / LAMP_SPACING)))
        ny = max(1, int(round((roof_hi[1] - roof_lo[1]) / LAMP_SPACING)))
        lamps = 0
        for i in range(nx):
            for j in range(ny):
                cx = roof_lo[0] + (roof_hi[0] - roof_lo[0]) * (i + 0.5) / nx
                cy = roof_lo[1] + (roof_hi[1] - roof_lo[1]) * (j + 0.5) / ny
                block(f"Techo_{bname}_Lampara_{i}_{j}", folder, tags, [cx - 60, cy - 20, rz - 12], [cx + 60, cy + 20, rz], lamp_mat)
                # un foco hacia abajo (alumbra el piso, no el techo); mas fuerte cuanto mas alto esta el techo
                light = actors.spawn_actor_from_class(unreal.SpotLight, unreal.Vector(cx, cy, rz - 20), unreal.Rotator(0, -90, 0))
                light.set_actor_label(f"Techo_{bname}_Luz_{i}_{j}")
                light.set_folder_path(folder)
                lc = light.get_component_by_class(unreal.SpotLightComponent)
                height = rz - fz
                lc.set_editor_property("intensity", LAMP_INTENSITY * (height / 370.0) ** 2 * b.get("light", 1.0))
                lc.set_editor_property("attenuation_radius", height * 2.5)
                lc.set_editor_property("inner_cone_angle", 40.0)
                lc.set_editor_property("outer_cone_angle", 80.0)
                lc.set_editor_property("cast_shadows", False)
                lc.set_editor_property("light_color", unreal.Color(255, 236, 214, 255))
                light.tags = [f"Escena:{b['scene']}"]
                # relleno: una luz puntual a media altura que alumbra paredes y maquinas de costado
                fill = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(cx, cy, fz + height * 0.55), unreal.Rotator(0, 0, 0))
                fill.set_actor_label(f"Techo_{bname}_Relleno_{i}_{j}")
                fill.set_folder_path(folder)
                fc = fill.get_component_by_class(unreal.PointLightComponent)
                fc.set_editor_property("intensity", FILL_INTENSITY * (height / 370.0) ** 2 * b.get("light", 1.0))
                fc.set_editor_property("attenuation_radius", max(LAMP_SPACING * 1.4, height * 1.5))
                fc.set_editor_property("cast_shadows", False)
                fc.set_editor_property("light_color", unreal.Color(255, 236, 214, 255))
                fill.tags = [f"Escena:{b['scene']}"]
                lamps += 1
        made["lamparas"] = lamps
        made["lineas"] = {k: round(v, 1) for k, v in lines.items()}
        made["techo_z"] = rz
        report[bname] = made
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[TECHOS] " + report["error"])
finally:
    (project / "Docs/techos.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
