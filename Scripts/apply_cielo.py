"""Editor Python (04/10): cielo de dia sin fin alrededor de las escenas.

Detras de los muros se veia negro: el nivel tenia sol (Sun) y luces de relleno pero nada que dibujara el cielo. Pone,
en la carpeta Cielo (si ya estan, solo los ajusta):
- `Cielo_Atmosfera` (SkyAtmosphere): cielo celeste con horizonte, iluminado por Sun (que ya es el sol de la atmosfera).
- `Cielo_Bruma` (ExponentialHeightFog): bruma desde los 50 m, que funde lo lejano con el horizonte; las escenas de
  cerca quedan nitidas.
- `Cielo_Nubes` (VolumetricCloud): nubes con el material simple del motor.
- `Cielo_Horizonte`: una losa de 4 km con M_Backdrop (el material de Piso_Exterior), 5 cm debajo de los pisos de
  afuera, para que por encima o entre los muros se vea terreno hasta perderse en la bruma.
- `SkyFill` (SkyLight) pasa a capturar el cielo en tiempo real en lugar de su cubemap fijo (el anterior queda en el
  informe para volver atras).
Hay que correrlo con el editor abierto (crear actores sin ventana se cae) y guarda el nivel.
Informe: Docs/cielo.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
FOLDER = "Cielo"
GROUND_Z = -60.0            # los pisos de afuera estan en -55
GROUND_SIZE = 400000.0      # cm de lado (4 km)
GROUND_CENTER = (-5000.0, 3500.0)
FOG_START = 5000.0          # cm: la bruma empieza a los 50 m
report = {"passed": False}

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}

    def ensure(label, cls, location=unreal.Vector(0, 0, 0)):
        actor = by.get(label)
        if actor is None:
            actor = actors.spawn_actor_from_class(cls, location, unreal.Rotator(0, 0, 0))
            actor.set_actor_label(label)
            report.setdefault("created", []).append(label)
        actor.set_folder_path(FOLDER)
        actor.modify()
        return actor

    ensure("Cielo_Atmosfera", unreal.SkyAtmosphere)

    fog = ensure("Cielo_Bruma", unreal.ExponentialHeightFog, unreal.Vector(GROUND_CENTER[0], GROUND_CENTER[1], 0))
    fog_comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog_comp.set_editor_property("fog_density", 0.02)
    fog_comp.set_editor_property("fog_height_falloff", 0.2)
    fog_comp.set_editor_property("start_distance", FOG_START)
    fog_comp.set_editor_property("fog_max_opacity", 1.0)

    clouds = ensure("Cielo_Nubes", unreal.VolumetricCloud)
    cloud_comp = clouds.get_component_by_class(unreal.VolumetricCloudComponent)
    if cloud_comp.get_editor_property("material") is None:
        material = unreal.load_asset("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst")
        if material:
            cloud_comp.set_editor_property("material", material)

    ground = ensure("Cielo_Horizonte", unreal.StaticMeshActor,
                    unreal.Vector(GROUND_CENTER[0], GROUND_CENTER[1], GROUND_Z))
    ground.set_actor_location(unreal.Vector(GROUND_CENTER[0], GROUND_CENTER[1], GROUND_Z), False, False)
    plane = unreal.load_asset("/Engine/BasicShapes/Plane")
    comp = ground.static_mesh_component
    comp.set_static_mesh(plane)
    ground.set_actor_scale3d(unreal.Vector(GROUND_SIZE / 100.0, GROUND_SIZE / 100.0, 1.0))
    backdrop = unreal.load_asset("/Game/FactoryCtyco/Materials/M_Backdrop")
    if backdrop:
        comp.set_material(0, backdrop)
    comp.set_collision_profile_name("BlockAll")
    comp.set_editor_property("cast_shadow", False)

    sky = next(a for a in level if isinstance(a, unreal.SkyLight))
    sky_comp = sky.get_component_by_class(unreal.SkyLightComponent)
    cubemap = sky_comp.get_editor_property("cubemap")
    report["skylight_before"] = dict(label=sky.get_actor_label(), source=str(sky_comp.get_editor_property("source_type")),
                                     cubemap=cubemap.get_path_name() if cubemap else None,
                                     intensity=sky_comp.get_editor_property("intensity"),
                                     real_time=sky_comp.get_editor_property("real_time_capture"))
    sky.modify()
    sky_comp.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    sky_comp.set_editor_property("real_time_capture", True)
    sky_comp.set_editor_property("intensity", 1.0)

    sun = by.get("Sun")
    if sun:
        report["sun_is_atmosphere_light"] = sun.get_component_by_class(unreal.DirectionalLightComponent).get_editor_property("atmosphere_sun_light")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, folder=FOLDER, ground=dict(z=GROUND_Z, size_cm=GROUND_SIZE, material=backdrop.get_path_name() if backdrop else None),
                  fog_start_cm=FOG_START, clouds_material=str(cloud_comp.get_editor_property("material").get_path_name()
                                                              if cloud_comp.get_editor_property("material") else None))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[CIELO] " + report["error"])
finally:
    (project / "Docs/cielo.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
