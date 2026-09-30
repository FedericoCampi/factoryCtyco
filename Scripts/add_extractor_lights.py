"""Editor Python (con L_FactoryDemo abierto): luces, pantalla e interruptor de Extractor_Silicio.

- Mirilla: emisivo naranja que pulsa cada 4 s + luz puntual suave delante.
- Baliza cian sobre el cabezal (esfera + luz) que parpadea cada 1,2 s.
- Pantalla del gabinete trasero con texto ilegible que se desplaza.
- Extractor_Interruptor (AFactoryMachineSwitch): con E cerca de la pantalla enciende o apaga
  todo. Apagada, la animacion se detiene y luces, mirilla, baliza y pantalla quedan oscuras.
Todos los materiales tienen el parametro "Power" que maneja el interruptor.
Todo va enganchado a la maquina (sigue su posicion, giro y escala). Es idempotente.
No guarda el nivel; run_extractor_setup.py lo corre sin editor y guarda.
Informe: Docs/extractor_lights.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/ExtractorSilicio"
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

# posiciones en el espacio de la malla (cm, antes de la escala del actor; frente = +Y)
PORTHOLE_LIGHT = unreal.Vector(1, 80, 102)
BEACON = unreal.Vector(5, 0, 252)
SCREEN = unreal.Vector(-44.1, -52.3, 118.1)   # rectangulo oscuro del gabinete, mira a -Y
SCREEN_SIZE = (17.5, 17.0)
ORANGE = unreal.LinearColor(1.0, 0.35, 0.06, 1.0)
CYAN = unreal.LinearColor(0.1, 0.85, 1.0, 1.0)
GREEN = unreal.LinearColor(0.25, 1.0, 0.7, 1.0)
LABELS = ("Extractor_LuzMirilla", "Extractor_LuzBaliza", "Extractor_Baliza",
          "Extractor_Pantalla", "Extractor_Interruptor")


def expr(mat, cls, x, y, **props):
    node = mel.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        node.set_editor_property(k, v)
    return node


def link(a, b, pin_b="", pin_a=""):
    mel.connect_material_expressions(a, pin_a, b, pin_b)


def pulse(mat, period, low, high, x=-900, y=400):
    """Nodo que oscila entre low y high con el periodo dado (s)."""
    time = expr(mat, unreal.MaterialExpressionTime, x - 400, y)
    sine = expr(mat, unreal.MaterialExpressionSine, x - 200, y, period=period)
    link(time, sine)
    mul = expr(mat, unreal.MaterialExpressionMultiply, x, y, const_b=(high - low) / 2)
    link(sine, mul, "A")
    add = expr(mat, unreal.MaterialExpressionAdd, x + 200, y, const_b=(high + low) / 2)
    link(mul, add, "A")
    return add


def times(mat, a, b, x, y, pin_a=""):
    node = expr(mat, unreal.MaterialExpressionMultiply, x, y)
    link(a, node, "A", pin_a)
    link(b, node, "B")
    return node


def power(mat, x=-500, y=700):
    return expr(mat, unreal.MaterialExpressionScalarParameter, x, y, parameter_name="Power", default_value=1.0)


def material(name, domain=None):
    """Reutiliza el asset (hay actores que lo referencian) y rehace su grafo."""
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path):
        mat = unreal.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    if domain:
        mat.set_editor_property("material_domain", domain)
    return mat


def finish(mat):
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    return mat


def glow_material():
    """Mirilla: textura base; emisivo naranja de 1 a 12 que pulsa cada 4 s, por Power."""
    source = unreal.load_asset(f"{DEST}/M_Mirilla")
    tex_node = mel.get_material_property_input_node(source, unreal.MaterialProperty.MP_BASE_COLOR)
    texture = tex_node.get_editor_property("texture")
    mat = material("M_ExtractorMirilla_Glow")
    tex = expr(mat, unreal.MaterialExpressionTextureSample, -1100, 0, texture=texture)
    mel.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = expr(mat, unreal.MaterialExpressionConstant, -300, 200, r=0.25)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    orange = expr(mat, unreal.MaterialExpressionConstant3Vector, -1100, 300, constant=ORANGE)
    tint = times(mat, tex, orange, -800, 250, "RGB")
    lit = times(mat, tint, pulse(mat, 4.0, 1.0, 12.0), -500, 350)
    mel.connect_material_property(times(mat, lit, power(mat), -250, 450), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(mat)


def beacon_material():
    mat = material("M_ExtractorBaliza")
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    color = expr(mat, unreal.MaterialExpressionConstant3Vector, -800, 0, constant=CYAN)
    lit = times(mat, color, pulse(mat, 1.2, 0.2, 10.0), -500, 100)
    mel.connect_material_property(times(mat, lit, power(mat), -250, 300), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(mat)


def screen_texture():
    path = f"{DEST}/T_ExtractorPantalla"
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/ExtractorSilicio/pantalla_glifos.png")
    task.destination_path = DEST
    task.destination_name = "T_ExtractorPantalla"
    task.automated = True
    task.save = True
    task.replace_existing = True
    tools.import_asset_tasks([task])
    return unreal.load_asset(path)


def screen_material(texture):
    """Pantalla: fondo casi negro; texto verde que sube despacio y titila apenas, por Power."""
    mat = material("M_ExtractorPantalla")
    base = expr(mat, unreal.MaterialExpressionConstant3Vector, -300, -200,
                constant=unreal.LinearColor(0.01, 0.012, 0.014, 1))
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = expr(mat, unreal.MaterialExpressionConstant, -300, -100, r=0.15)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1500, 0)
    pan = expr(mat, unreal.MaterialExpressionPanner, -1300, 0, speed_x=0.0, speed_y=0.035)
    link(uv, pan, "Coordinate")
    tex = expr(mat, unreal.MaterialExpressionTextureSample, -1100, 0, texture=texture)
    link(pan, tex, "UVs")
    green = expr(mat, unreal.MaterialExpressionConstant3Vector, -1100, 300, constant=GREEN)
    tint = times(mat, tex, green, -800, 150, "RGB")
    lit = times(mat, tint, pulse(mat, 0.11, 2.6, 3.0), -500, 250)
    mel.connect_material_property(times(mat, lit, power(mat), -250, 350), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(mat)


def light_function(name, period, low):
    mat = material(name, unreal.MaterialDomain.MD_LIGHT_FUNCTION)
    mel.connect_material_property(pulse(mat, period, low, 1.0), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(mat)


def attach(child, parent, rel, scale=unreal.Vector(1, 1, 1)):
    child.attach_to_actor(parent, "", unreal.AttachmentRule.KEEP_RELATIVE,
                          unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
    child.set_actor_relative_location(rel, False, False)
    child.set_actor_relative_rotation(unreal.Rotator(), False, False)
    child.set_actor_relative_scale3d(scale)
    child.set_folder_path("Environment")
    return child


def point_light(label, parent, rel, color, candelas, radius, function):
    light = actors.spawn_actor_from_class(unreal.PointLight, parent.get_actor_location(), unreal.Rotator())
    light.set_actor_label(label)
    comp = light.point_light_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    comp.set_editor_property("intensity", candelas)
    comp.set_light_color(color)
    comp.set_editor_property("attenuation_radius", radius)
    comp.set_editor_property("cast_shadows", False)
    comp.set_editor_property("light_function_material", function)
    return attach(light, parent, rel)


def mesh_actor(label, parent, mesh, mat, rel, scale):
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, parent.get_actor_location(), unreal.Rotator())
    actor.set_actor_label(label)
    sm = actor.static_mesh_component
    sm.set_mobility(unreal.ComponentMobility.MOVABLE)
    sm.set_static_mesh(unreal.load_asset(mesh))
    sm.set_material(0, mat)
    sm.set_collision_profile_name("NoCollision")
    sm.set_editor_property("cast_shadow", False)
    return attach(actor, parent, rel, scale)


try:
    machine = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == "Extractor_Silicio"), None)
    if machine is None:
        raise RuntimeError("No esta Extractor_Silicio en el nivel abierto")
    for old in actors.get_all_level_actors():
        if old.get_actor_label() in LABELS:
            actors.destroy_actor(old)

    glow_material()
    screen_mat = screen_material(screen_texture())
    bulb_mat = beacon_material()
    lf_orange = light_function("LF_ExtractorMirilla", 4.0, 0.3)
    lf_cyan = light_function("LF_ExtractorBaliza", 1.2, 0.1)

    powered = [
        point_light("Extractor_LuzMirilla", machine, PORTHOLE_LIGHT, ORANGE, 12.0, 280.0, lf_orange),
        point_light("Extractor_LuzBaliza", machine, BEACON + unreal.Vector(0, 0, 12), CYAN, 20.0, 300.0, lf_cyan),
        mesh_actor("Extractor_Baliza", machine, "/Engine/BasicShapes/Sphere", bulb_mat, BEACON,
                   unreal.Vector(0.1, 0.1, 0.1)),
        mesh_actor("Extractor_Pantalla", machine, "/Engine/BasicShapes/Cube", screen_mat, SCREEN,
                   unreal.Vector(SCREEN_SIZE[0] / 100, 0.004, SCREEN_SIZE[1] / 100)),
    ]
    switch_class = unreal.load_class(None, "/Script/FactoryCtycoRuntime.FactoryMachineSwitch")
    if switch_class is None:
        raise RuntimeError("Falta AFactoryMachineSwitch: instalar FactoryCtycoRuntime (build_runtime_visuals.ps1 -Install)")
    switch = actors.spawn_actor_from_class(switch_class, machine.get_actor_location(), unreal.Rotator())
    switch.set_actor_label("Extractor_Interruptor")
    switch.set_editor_property("machine", machine)
    switch.set_editor_property("powered_actors", powered)
    switch.set_editor_property("machine_name", "EXTRACTOR")
    switch.set_editor_property("interaction_radius", 220.0)
    attach(switch, machine, SCREEN + unreal.Vector(0, -20, 0))

    report.update(passed=True, attached_to=machine.get_actor_label(), actors=list(LABELS),
                  switch_world=[round(v, 1) for v in switch.get_actor_location().to_tuple()],
                  screen_world=[round(v, 1) for v in powered[3].get_actor_location().to_tuple()])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[EXTRACTOR_LIGHTS] {error}")
(project / "Docs/extractor_lights.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
