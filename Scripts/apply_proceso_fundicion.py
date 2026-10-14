"""Editor Python (con L_FactoryDemo abierto): proceso de fundicion del horno (02/10).

Cuarzo por una linea de cintas que sube suave hasta la boca del horno; el horno lo funde y cuela silicio por la canaleta
abierta (Tubo_Descarga + Codo_Metalico) hasta Container_Producto, donde se enfria y queda un lingote.
1. Cuarzo: importa SM_Cuarzo (author_cuarzo.py) con M_Cuarzo y crea los recursos DA_Quartz y DA_SiliconIngot, que se
   suman a los recursos de FactoryDemo_Simulation.
2. M_SilicioFundido: parametro Heat (1 naranja que brilla y se mueve, 0 gris silicio frio).
3. Linea corta (desde que el horno esta mas bajo, 02/10): Cinta_Fabrica_2 sube desde el piso, Cinta_Fabrica_Esquina
   da la vuelta y Cinta_Fabrica_1 sigue subiendo hasta la boca del horno; las dos rectas con la misma pendiente
   (~10 grados). Cada pieza va de su entrada a su salida en LINE (x, y medidos el 02/10; las alturas se calculan).
   La vuelta larga por las paredes (Cinta_Fabrica_5, Esquina3, Esquina2, Cinta_4) y la subida a 30 grados
   (Cinta_Cuarzo_Subida) ya no hacen falta y se borran (REMOVED).
4. En el piso, antes de Cinta_Fabrica_2 y en la misma direccion: Deposito_Cuarzo (100 de cuarzo) ->
   Cinta_Cuarzo_Triturar (un deposito no le pasa material a una maquina sin cinta en el medio) -> Trituradora_Cuarzo
   (DB_QuartzCrusher: cada cuarzo sale como arena de cuarzo, SM_ArenaCuarzo / DA_QuartzSand). El horno funde la arena.
5. Con FactoryCtycoRuntime compilado con AFactoryMeltProcess: el actor Proceso_Fundicion en el horno, con la cinta
   que lo alimenta, el camino del liquido por la canaleta y el contenedor. Si ya existe solo se actualiza. La canaleta
   sigue del codo al contenedor con caños rectos (Cano_Recto_N, author_cano_recto.py).
6. Para probar solo esto: la guia (intro y mision) en pausa (Guia_Mision.bPaused) y el personaje empieza en la
   fabrica (PlayerStart_Robot1 a PLAYER_START; antes estaba en (-3830, 9220, 500)).
Se puede correr de nuevo: deja todo igual si ya estaba. Informe: Docs/proceso_fundicion.json.
"""
import json
import math
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
MODELS = "/Game/FactoryCtyco/Factory/Models/Cuarzo"
DEFS = "/Game/FactoryCtyco/Factory/Definitions"
MATS = "/Game/FactoryCtyco/Factory/Materials"
DEPOT_START = 100
# Puntos de entrega de la linea (cm), en el sentido del cuarzo: entrada y salida de cada pieza.
# (las alturas de aca se reemplazan: la 2 arranca en la salida de la trituradora y la 1 entrega en la boca del horno)
LINE = [("Cinta_Fabrica_2", (456, 701, 0), (-534, 701, 0)),
        ("Cinta_Fabrica_Esquina", (-528, 697, 0), (-730, 495, 0)),
        ("Cinta_Fabrica_1", (-730, 496, 0), (-730, -496, 0))]
REMOVED = ["Cinta_Fabrica_5", "Cinta_Fabrica_Esquina3", "Cinta_Fabrica_Esquina2", "Cinta_Fabrica_4", "Cinta_Cuarzo_Subida"]
FLOOR = 4.0
# Desde el 02/10 (noche) el usuario ubica la linea a mano: los pasos 3-4 ya no mueven ni borran cintas, solo conectan
# (apply_lavadora_cuarzo.py). True vuelve a armar la linea corta de abajo.
MANAGE_LAYOUT = False
MOUTH_ABOVE_HORNO = 298.0   # borde de la boca sobre el actor del horno (cm; a ojo, su colision es una caja)
BELT_ABOVE_MOUTH = -9.0     # Cinta_Fabrica_1 entrega apenas abajo del borde, adentro de la boca
CRUSHER_SCALE = 1.25
PLAYER_START = (-250, -380, 110)   # al lado del horno, mirando hacia el
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"passed": False}


def vec(p):
    return p if isinstance(p, unreal.Vector) else unreal.Vector(*p)


def rnd(v):
    return [round(v.x), round(v.y), round(v.z)]


# ---------------------------------------------------------------- 1. cuarzo
def material(name, build):
    path = f"{MATS}/{name}"
    if lib.does_asset_exist(path):
        m = unreal.load_asset(path)
        mel.delete_all_material_expressions(m)
    else:
        m = tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    build(m)
    mel.recompile_material(m)
    lib.save_loaded_asset(m)
    return m


def quartz_material(m):
    color = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    color.set_editor_property("constant", unreal.LinearColor(0.93, 0.86, 0.91))
    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 150)
    rough.set_editor_property("r", 0.18)
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)


def molten_material(m):
    """Heat 1: naranja que brilla con vetas que corren; Heat 0: silicio gris metalico."""
    heat = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -1400, 0)
    heat.set_editor_property("parameter_name", "Heat")
    heat.set_editor_property("default_value", 1.0)
    pos = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -1400, 300)
    time = mel.create_material_expression(m, unreal.MaterialExpressionTime, -1400, 450)
    drift = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -1400, 550)
    drift.set_editor_property("constant", unreal.LinearColor(35, 25, -60))
    moved = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -1200, 450)
    mel.connect_material_expressions(time, "", moved, "A")
    mel.connect_material_expressions(drift, "", moved, "B")
    at = mel.create_material_expression(m, unreal.MaterialExpressionAdd, -1050, 350)
    mel.connect_material_expressions(pos, "", at, "A")
    mel.connect_material_expressions(moved, "", at, "B")
    noise = mel.create_material_expression(m, unreal.MaterialExpressionNoise, -900, 350)
    noise.set_editor_property("scale", 0.03)
    noise.set_editor_property("output_min", 0.0)
    noise.set_editor_property("output_max", 1.0)
    mel.connect_material_expressions(at, "", noise, "Position")
    veins = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -650, 350)
    veins.set_editor_property("const_a", 0.5)
    veins.set_editor_property("const_b", 1.0)
    mel.connect_material_expressions(noise, "", veins, "Alpha")
    heat2 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -1150, 0)
    mel.connect_material_expressions(heat, "", heat2, "A")
    mel.connect_material_expressions(heat, "", heat2, "B")
    hot = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -900, 100)
    hot.set_editor_property("constant", unreal.LinearColor(8.0, 2.6, 0.32))
    glow = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -650, 100)
    mel.connect_material_expressions(hot, "", glow, "A")
    mel.connect_material_expressions(heat2, "", glow, "B")
    emissive = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -400, 150)
    mel.connect_material_expressions(glow, "", emissive, "A")
    mel.connect_material_expressions(veins, "", emissive, "B")
    mel.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    cold = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -900, -250)
    cold.set_editor_property("constant", unreal.LinearColor(0.42, 0.43, 0.46))
    ember = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -900, -150)
    ember.set_editor_property("constant", unreal.LinearColor(0.25, 0.06, 0.0))
    base = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -400, -200)
    mel.connect_material_expressions(cold, "", base, "A")
    mel.connect_material_expressions(ember, "", base, "B")
    mel.connect_material_expressions(heat, "", base, "Alpha")
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    metal = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -400, -50)
    metal.set_editor_property("const_a", 0.75)
    metal.set_editor_property("const_b", 0.0)
    mel.connect_material_expressions(heat, "", metal, "Alpha")
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    rough = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -400, 50)
    rough.set_editor_property("const_a", 0.3)
    rough.set_editor_property("const_b", 0.55)
    mel.connect_material_expressions(heat, "", rough, "Alpha")
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)


def import_quartz_mesh(mat, name="SM_Cuarzo"):
    path = f"{MODELS}/{name}"
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.convert_scene = True
    data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Cuarzo/{name}.fbx")
    task.destination_path, task.destination_name = MODELS, name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    mesh.set_material(0, mat)
    lib.save_loaded_asset(mesh)
    return mesh


def sand_material(m):
    color = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    color.set_editor_property("constant", unreal.LinearColor(0.86, 0.80, 0.70))
    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 150)
    rough.set_editor_property("r", 0.92)
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)


def resource(name, item_id, display, color, mesh):
    path = f"{DEFS}/{name}"
    res = unreal.load_asset(path) if lib.does_asset_exist(path) else None
    if res is None:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.FactoryResourceDefinition)
        res = tools.create_asset(name, DEFS, unreal.FactoryResourceDefinition, factory)
    res.set_editor_property("item_id", item_id)
    res.set_editor_property("display_name", display)
    res.set_editor_property("color", color)
    res.set_editor_property("pickup_mesh", mesh)
    lib.save_loaded_asset(res)
    return res


# ---------------------------------------------------------------- 3. cintas
def fit_straight(belt, a, b):
    """Cinta recta de a a b (puntos de entrega): rumbo, largo (escala X), pendiente y lugar."""
    a, b = vec(a), vec(b)
    d = b - a
    flat = math.hypot(d.x, d.y)
    slope = math.degrees(math.atan2(d.z, flat))
    belt.modify()
    belt.set_editor_property("slope", slope)
    s = belt.get_actor_scale3d()
    belt.set_actor_scale3d(unreal.Vector(math.hypot(flat, d.z) / 200.0, s.y, 1.0))
    belt.set_actor_rotation(unreal.Rotator(0, slope, math.degrees(math.atan2(d.y, d.x))), False)
    belt.set_actor_location(belt.get_actor_location() + a - belt.input_point(), False, False)
    belt.refresh_visuals()


def fit_corner(belt, a, b):
    """Esquina de a a b: de los 4 rumbos y las 2 manos (escala Y +/-), la que mejor une los dos puntos."""
    a, b = vec(a), vec(b)
    s = belt.get_actor_scale3d()
    best = None
    belt.modify()
    for yaw in (0, 90, 180, -90):
        for hand in (1, -1):
            belt.set_actor_scale3d(unreal.Vector(s.x, abs(s.y) * hand, s.z))
            belt.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            belt.set_actor_location(belt.get_actor_location() + a - belt.input_point(), False, False)
            gap = (belt.output_point() - b).length()
            if best is None or gap < best[0]:
                best = (gap, yaw, hand)
    gap, yaw, hand = best
    belt.set_actor_scale3d(unreal.Vector(s.x, abs(s.y) * hand, s.z))
    belt.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    belt.set_actor_location(belt.get_actor_location() + a - belt.input_point(), False, False)
    belt.refresh_visuals()
    return gap


def is_corner(belt):
    return abs(belt.get_editor_property("definition").get_editor_property("turn_degrees")) >= 0.5


def receiver_of(belt, others):
    out = belt.output_point()
    for o in others:
        i = o.input_point()
        if o != belt and math.hypot(out.x - i.x, out.y - i.y) <= 50 and abs(out.z - i.z) <= 60:
            return o.get_actor_label()
    return None


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != MAP:
        raise RuntimeError("Abrir L_FactoryDemo en el editor antes de correr el script")
    level = actors.get_all_level_actors()
    by_label = {a.get_actor_label(): a for a in level}
    sim = [a for a in level if isinstance(a, unreal.FactoryDemoWorld)][0]
    # la ultima cinta entrega en la boca del horno, a la altura que tenga el horno
    MOUTH_Z = by_label["Horno_Fundicion"].get_actor_location().z + MOUTH_ABOVE_HORNO
    # la 2 arranca a la altura de la salida de la trituradora; la vuelta queda donde las dos rectas suben igual
    low, high = FLOOR + 33 * CRUSHER_SCALE, MOUTH_Z + BELT_ABOVE_MOUTH
    span = [math.dist(a[:2], b[:2]) for _, a, b in LINE]
    turn = low + (high - low) * span[0] / (span[0] + span[2])
    LINE = [(LINE[0][0], (*LINE[0][1][:2], low), (*LINE[0][2][:2], turn)),
            (LINE[1][0], (*LINE[1][1][:2], turn), (*LINE[1][2][:2], turn)),
            (LINE[2][0], (*LINE[2][1][:2], turn), (*LINE[2][2][:2], high))]

    # 1-2. cuarzo, recursos y material del liquido
    quartz_mat = material("M_Cuarzo", quartz_material)
    molten = material("M_SilicioFundido", molten_material)
    quartz_mesh = import_quartz_mesh(quartz_mat)
    quartz = resource("DA_Quartz", "Quartz", "Cuarzo", unreal.LinearColor(0.93, 0.86, 0.91), quartz_mesh)
    sand = resource("DA_QuartzSand", "QuartzSand", "Arena de cuarzo", unreal.LinearColor(0.86, 0.80, 0.70),
                    import_quartz_mesh(material("M_ArenaCuarzo", sand_material), "SM_ArenaCuarzo"))
    ingot = resource("DA_SiliconIngot", "SiliconIngot", "Lingote de silicio", unreal.LinearColor(0.45, 0.47, 0.52),
                     unreal.load_asset("/Engine/BasicShapes/Cube"))
    resources = list(sim.get_editor_property("resources"))
    for r in (quartz, sand, ingot):
        if r not in resources:
            resources.append(r)
    sim.modify()
    sim.set_editor_property("resources", resources)
    report["resources"] = [r.get_name() for r in resources]

    if MANAGE_LAYOUT:
        # 3. linea corta y suave hacia el horno (lo que sobra de la vuelta larga se borra)
        for label in REMOVED:
            if label in by_label:
                actors.destroy_actor(by_label.pop(label))
                report.setdefault("borradas", []).append(label)
        line = []
        for label, a, b in LINE:
            belt = by_label.get(label)
            if not isinstance(belt, unreal.FactoryBuilding):
                raise RuntimeError(f"No esta la cinta {label}")
            belt.modify()
            # sobre patas: la cinta a la altura del medio de su tramo, el actor en el piso
            belt.set_editor_property("elevation", (a[2] + b[2]) / 2 - 33 - FLOOR)
            gap = fit_corner(belt, a, b) if is_corner(belt) else (fit_straight(belt, a, b) or 0.0)
            belt.build_supports()
            line.append(belt)
            report.setdefault("line", []).append({"belt": label, "in": rnd(belt.input_point()), "out": rnd(belt.output_point()),
                                                  "slope": round(belt.get_editor_property("slope"), 1), "fit_gap_cm": round(gap, 1)})

        # 4. en el piso, antes de la linea y en su misma direccion: deposito -> cinta corta -> trituradora
        first_in, first_out = vec(LINE[0][1]), vec(LINE[0][2])
        back = unreal.Vector(first_in.x - first_out.x, first_in.y - first_out.y, 0).normal()
        yaw = math.degrees(math.atan2(-back.y, -back.x))
        ground = lambda along, z=FLOOR: unreal.Vector(first_in.x + back.x * along, first_in.y + back.y * along, z)
        crusher_def = unreal.load_asset(f"{DEFS}/DB_QuartzCrusher") if lib.does_asset_exist(f"{DEFS}/DB_QuartzCrusher") else None
        if crusher_def is None:
            crusher_def = lib.duplicate_asset(f"{DEFS}/DB_Crusher", f"{DEFS}/DB_QuartzCrusher")
        for prop, value in (("building_id", "QuartzCrusher"), ("display_name", "Trituradora de cuarzo"), ("input_item", "Quartz"),
                            ("output_item", "QuartzSand"), ("input_quantity", 1), ("output_quantity", 1), ("cycle_seconds", 2.5)):
            crusher_def.set_editor_property(prop, value)
        lib.save_loaded_asset(crusher_def)
        storage_def = unreal.load_asset(f"{DEFS}/DB_Storage")
        belt_def = unreal.load_asset(f"{DEFS}/DB_Belt")
        folder = line[0].get_folder_path()

        def piece(label, definition, location, scale):
            a = by_label.get(label)
            if a is None:
                a = actors.spawn_actor_from_class(unreal.FactoryBuilding, location, unreal.Rotator(0, 0, yaw))
                a.set_actor_label(label)
                a.set_folder_path(folder)
                a.set_editor_property("definition", definition)
                a.set_editor_property("persistent_id", label)
            a.modify()
            a.set_actor_location(location, False, False)
            a.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            a.set_actor_scale3d(scale)
            a.refresh_visuals()
            return a

        crusher_len = 200 * CRUSHER_SCALE                         # su salida es la entrada de Cinta_Fabrica_2
        crusher = piece("Trituradora_Cuarzo", crusher_def, ground(crusher_len / 2), unreal.Vector(CRUSHER_SCALE, CRUSHER_SCALE, CRUSHER_SCALE))
        feeder = piece("Cinta_Cuarzo_Triturar", belt_def, ground(crusher_len + 100), unreal.Vector(1, 0.75, 1))
        fit_straight(feeder, ground(crusher_len + 200, FLOOR + 33), ground(crusher_len, FLOOR + 33))
        depot = piece("Deposito_Cuarzo", storage_def, ground(crusher_len + 300), unreal.Vector(1, 1, 1))
        depot.set_editor_property("storage_item", "Quartz")
        stock = depot.get_editor_property("input")
        if stock.get_quantity("Quartz") == 0:
            for item, n in list(stock.get_editor_property("items").items()):
                stock.remove_item(item, n)
            stock.add_item(quartz, DEPOT_START)

        chain = [depot, feeder, crusher] + line
        report["chain"] = [{"from": b.get_actor_label(), "to": receiver_of(b, chain)} for b in chain]
        report["depot"] = {"location": rnd(depot.get_actor_location()), "quartz": stock.get_quantity("Quartz")}
        # que no haya nada en el camino: el tramo del piso y la parte baja de Cinta_Fabrica_2
        ignore = chain + [a for a in level if a.get_actor_label().startswith("SceneRobot")]
        far = ground(crusher_len + 400)
        mid = unreal.Vector((far.x + first_out.x) / 2, (far.y + first_out.y) / 2, 90)
        half = unreal.Vector(abs(far.x - first_out.x) / 2 + abs(back.y) * 80, abs(far.y - first_out.y) / 2 + abs(back.x) * 80, 50)
        hits = unreal.SystemLibrary.box_overlap_actors(world, mid, half,
                                                       [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, ignore)
        if isinstance(hits, tuple):
            hits = hits[-1]
        report["riser_overlaps"] = sorted({h.get_actor_label() for h in hits or []})
    else:
        # 3-4. la linea la arma el usuario en el editor: solo se conecta (lavadora -> trituradora -> horno)
        exec(open(project / "Scripts/apply_lavadora_cuarzo.py", encoding="utf-8").read())

    # 5. el proceso del horno (cuando el modulo ya tiene la clase)
    if hasattr(unreal, "FactoryMeltProcess"):
        exec(open(project / "Scripts/apply_proceso_fundicion_horno.py", encoding="utf-8").read())
    else:
        report["process"] = "falta compilar FactoryCtycoRuntime con AFactoryMeltProcess"

    # 6. solo el proceso: guia en pausa y el personaje empieza en la fabrica
    guide = [a for a in level if isinstance(a, unreal.FactoryGuide)]
    for g in guide:
        try:
            g.modify()
            g.set_editor_property("paused", True)
            report["guia_en_pausa"] = True
        except Exception as error:
            report["guia_en_pausa"] = f"falta compilar: {error}"
    for start_actor in [a for a in level if isinstance(a, unreal.PlayerStart)]:
        start_actor.modify()
        start_actor.set_actor_location(vec(PLAYER_START), False, False)
        start_actor.set_actor_rotation(unreal.Rotator(0, 0, -150), False)
        report["player_start"] = [start_actor.get_actor_label(), rnd(start_actor.get_actor_location())]

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    # el deposito ya no esta en la linea (se carga a mano desde el 03/10): no cuenta
    links = [c["to"] for c in report["chain"][:-1] if c["from"] != "Deposito_Cuarzo"]
    report["passed"] = all(links) and not report["riser_overlaps"]
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PROCESO_FUNDICION] " + report["error"])
(project / "Docs/proceso_fundicion.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
