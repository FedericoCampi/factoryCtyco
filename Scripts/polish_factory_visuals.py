"""First reversible material and lighting pass for the existing factory.

Run in the full UE editor with -ExecutePythonScript, or import and call apply().
Executing as __main__ closes the editor after writing the build report. This
script does not regenerate the map, models, resource definitions or recipes.
"""
import hashlib
import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
ROOT = "/Game/FactoryCtyco/Factory"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
DETAIL = ROOT + "/Materials/M_FactoryDetail"
GUIDE = ROOT + "/Materials/M_BeltSlot"
DEFINITIONS = [ROOT + "/Definitions/DB_" + name
               for name in ("Crusher", "Smelter", "Storage", "Belt")]
# Linear color values, authored for the arena's existing manual exposure.
SURFACES = {
    "BeltBasic": {"color": (.035, .052, .065, 1), "roughness": .62, "metallic": .18},
    "PlateBasic": {"color": (.56, .61, .65, 1), "roughness": .28, "metallic": .86},
    "FragmentsBasic": {"color": (.29, .36, .40, 1), "roughness": .44, "metallic": .80},
}
LIB = unreal.EditorAssetLibrary
ML = unreal.MaterialEditingLibrary


def _package_file(package, extension):
    if not package.startswith("/Game/") or ".." in package:
        raise ValueError("Expected a project content package: " + package)
    return PROJECT / "Content" / (package[len("/Game/"):] + extension)


def _backup(packages):
    """Keep a complete on-disk checkpoint before changing any package."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    folder = PROJECT / "Saved" / "VisualPolishWork" / stamp
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"created_utc": stamp, "files": [], "new_packages": []}
    for package in packages:
        found = False
        for extension in (".uasset", ".umap", ".uexp", ".ubulk", ".uptnl"):
            source = _package_file(package, extension)
            if not source.is_file():
                continue
            found = True
            relative = source.relative_to(PROJECT)
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError("Backup verification failed: " + str(source))
            manifest["files"].append({"path": relative.as_posix(), "sha256": digest})
        if not found:
            manifest["new_packages"].append(package)
    manifest["restore"] = (
        "With Unreal Editor closed, copy the backed-up Content files over the "
        "same project-relative files. The old definitions no longer reference "
        "new_packages; remove those new assets through the Content Browser if desired."
    )
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder


def _save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + asset.get_path_name())


def _expression(material, cls, x, y):
    node = ML.create_material_expression(material, cls, x, y)
    if node is None:
        raise RuntimeError("Could not create " + str(cls))
    return node


def _connect(node, output, destination, input_name):
    if not ML.connect_material_expressions(node, output, destination, input_name):
        raise RuntimeError("Could not connect material input " + input_name)


def _property(node, output, prop):
    if not ML.connect_material_property(node, output, prop):
        raise RuntimeError("Could not connect material property " + str(prop))


def _material(package, color, roughness, metallic, fragment_variation=False):
    folder, name = package.rsplit("/", 1)
    LIB.make_directory(folder)
    material = unreal.load_asset(package) if LIB.does_asset_exist(package) else None
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if not isinstance(material, unreal.Material):
        raise RuntimeError("Expected Material: " + package)
    material.modify()
    ML.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property("two_sided", False)
    base = _expression(material, unreal.MaterialExpressionVectorParameter, -650, 0)
    base.set_editor_property("parameter_name", "BaseColor")
    base.set_editor_property("default_value", unreal.LinearColor(*color))
    emission = _expression(material, unreal.MaterialExpressionVectorParameter, -650, 220)
    emission.set_editor_property("parameter_name", "Emission")
    emission.set_editor_property("default_value", unreal.LinearColor(0, 0, 0, 1))
    _property(emission, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    for index, (name, value, prop) in enumerate((
            ("Roughness", roughness, unreal.MaterialProperty.MP_ROUGHNESS),
            ("Metallic", metallic, unreal.MaterialProperty.MP_METALLIC))):
        node = _expression(material, unreal.MaterialExpressionScalarParameter, -650, 400 + index * 160)
        node.set_editor_property("parameter_name", name)
        node.set_editor_property("default_value", value)
        node.set_editor_property("slider_min", 0.0)
        node.set_editor_property("slider_max", 1.0)
        _property(node, "", prop)
    if fragment_variation:
        # A small orientation-based tint separates the fragment facets without
        # textures, UV requirements, time animation or changes to their geometry.
        normal = _expression(material, unreal.MaterialExpressionVertexNormalWS, -1100, -460)
        axis = _expression(material, unreal.MaterialExpressionConstant3Vector, -1100, -300)
        axis.set_editor_property("constant", unreal.LinearColor(.267, .535, .802, 1))
        dot = _expression(material, unreal.MaterialExpressionDotProduct, -870, -450)
        _connect(normal, "", dot, "A")
        _connect(axis, "", dot, "B")
        absolute = _expression(material, unreal.MaterialExpressionAbs, -700, -450)
        _connect(dot, "", absolute, "")
        strength = _expression(material, unreal.MaterialExpressionMultiply, -520, -450)
        strength.set_editor_property("const_b", .28)
        _connect(absolute, "", strength, "A")
        bias = _expression(material, unreal.MaterialExpressionAdd, -340, -450)
        bias.set_editor_property("const_b", .72)
        _connect(strength, "", bias, "A")
        tint = _expression(material, unreal.MaterialExpressionMultiply, -150, 0)
        _connect(base, "", tint, "A")
        _connect(bias, "", tint, "B")
        _property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
    else:
        _property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    ML.recompile_material(material)
    _save(material)
    return material


def _lighting(actors):
    changes = []
    for actor in actors:
        label = actor.get_actor_label()
        if isinstance(actor, unreal.DirectionalLight) and label in ("Sun", "Luz_Relleno"):
            light = actor.light_component
            light.modify()
            old = {"intensity": light.get_editor_property("intensity"),
                   "color": str(light.get_editor_property("light_color"))}
            if label == "Sun":
                intensity, color = 4.6, unreal.Color(r=255, g=239, b=218, a=255)
            else:
                intensity, color = .95, unreal.Color(r=200, g=233, b=245, a=255)
            light.set_editor_property("intensity", intensity)
            light.set_editor_property("light_color", color)
            changes.append({"actor": label, "before": old,
                            "after": {"intensity": intensity, "color": str(color)}})
        elif isinstance(actor, unreal.SkyLight) and label == "SkyFill":
            light = actor.light_component
            light.modify()
            old = light.get_editor_property("intensity")
            light.set_editor_property("intensity", .55)
            changes.append({"actor": label, "before_intensity": old, "intensity": .55})
        elif isinstance(actor, unreal.PostProcessVolume) and actor.get_editor_property("unbound"):
            actor.modify()
            settings = actor.get_editor_property("settings")
            old = str(settings.get_editor_property("color_saturation"))
            settings.set_editor_property("override_color_saturation", True)
            settings.set_editor_property("color_saturation", unreal.Vector4(1.04, 1.04, 1.04, 1.0))
            actor.set_editor_property("settings", settings)
            changes.append({"actor": label, "before_saturation": old, "saturation": 1.04})
    return changes


def _guide_material():
    """Outline the empty belt positions without covering the authored floor."""
    material = unreal.load_asset(GUIDE)
    if not material:
        return
    material.modify()
    ML.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    color = _expression(material, unreal.MaterialExpressionConstant3Vector, -300, 300)
    color.set_editor_property("constant", unreal.LinearColor(.025, .34, .27, 1))
    _property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    uv = _expression(material, unreal.MaterialExpressionTextureCoordinate, -1200, 0)
    centre = _expression(material, unreal.MaterialExpressionSubtract, -1020, 0)
    centre.set_editor_property("const_b", .5)
    _connect(uv, "", centre, "A")
    absolute = _expression(material, unreal.MaterialExpressionAbs, -840, 0)
    _connect(centre, "", absolute, "")
    channels = []
    for index in range(2):
        channel = _expression(material, unreal.MaterialExpressionComponentMask, -660, index * 150)
        for name, enabled in (("r", index == 0), ("g", index == 1), ("b", False), ("a", False)):
            channel.set_editor_property(name, enabled)
        _connect(absolute, "", channel, "")
        channels.append(channel)
    maximum = _expression(material, unreal.MaterialExpressionMax, -470, 0)
    _connect(channels[0], "", maximum, "A")
    _connect(channels[1], "", maximum, "B")
    border = _expression(material, unreal.MaterialExpressionSubtract, -300, 0)
    border.set_editor_property("const_b", .46)
    _connect(maximum, "", border, "A")
    strength = _expression(material, unreal.MaterialExpressionMultiply, -120, 0)
    strength.set_editor_property("const_b", 50.0)
    _connect(border, "", strength, "A")
    _property(strength, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    ML.recompile_material(material)
    _save(material)


def apply(tune_lighting=True):
    """Author materials and cook references; optionally tune existing lights."""
    report = {"passed": False, "map": MAP, "materials": [], "definitions": []}
    try:
        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if levels.is_in_play_in_editor():
            raise RuntimeError("Stop Play in Editor before applying the material pass")
        surface_paths = [ROOT + "/Models/" + name + "/M_" + name for name in SURFACES]
        for path in [MAP] + DEFINITIONS + surface_paths:
            if not LIB.does_asset_exist(path):
                raise RuntimeError("Required factory asset is missing: " + path)
        # Validate the newly compiled runtime property before writing anything.
        definitions = [unreal.load_asset(path) for path in DEFINITIONS]
        for definition in definitions:
            definition.get_editor_property("presentation_material")
        touched = [DETAIL, GUIDE] + surface_paths + DEFINITIONS + ([MAP] if tune_lighting else [])
        report["backup"] = str(_backup(touched))
        detail = _material(DETAIL, (.07, .10, .12, 1), .42, .65)
        report["materials"].append({"path": DETAIL, "parameters": {
            "BaseColor": [.07, .10, .12, 1], "Emission": [0, 0, 0, 1],
            "Roughness": .42, "Metallic": .65}})
        for name, values in SURFACES.items():
            path = ROOT + "/Models/" + name + "/M_" + name
            _material(path, values["color"], values["roughness"], values["metallic"],
                      fragment_variation=name == "FragmentsBasic")
            report["materials"].append({"path": path, **values})
        for definition in definitions:
            definition.modify()
            definition.set_editor_property("presentation_material", detail)
            _save(definition)
            report["definitions"].append(definition.get_path_name())
        _guide_material()
        report["belt_slot_marking"] = "Thin turquoise outline with visible original floor"
        if tune_lighting:
            if not levels.load_level(MAP):
                raise RuntimeError("Cannot open existing factory map")
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            count_before = len(actors)
            report["lighting"] = _lighting(actors)
            count_after = len(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
            if count_before != count_after:
                raise RuntimeError("The material pass must not change the level actor count")
            if not levels.save_current_level():
                raise RuntimeError("Could not save the factory lighting pass")
            report["actor_count"] = count_after
        report["passed"] = True
        return report
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
        raise
    finally:
        destination = PROJECT / "Docs" / "factory_visual_polish_build.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        unreal.log("[FACTORY_VISUAL_POLISH] " + json.dumps(report))


if __name__ == "__main__":
    try:
        apply()
    finally:
        unreal.SystemLibrary.quit_editor()
