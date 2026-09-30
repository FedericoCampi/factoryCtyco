"""Blender, sin ventana: la plataforma que levanta las cintas de la fabrica.

Pedido del 30/09: las cintas (DB_Belt) quedaban al ras del piso; van sobre una plataforma de 50 cm.
Misma paleta, biseles y exportacion que author_factory_detail_meshes.py, del que toma las funciones.
Escribe SourceAssets/Factory/VisualPolish/SM_FactoryBeltPlatform.fbx y belt_platform_manifest.json.

    blender -b --factory-startup -P Scripts/author_belt_platform.py

Despues: Scripts/run_belt_platform_setup.py (importa, la pone en DB_Belt y refresca el nivel).
"""
import json
import runpy
from pathlib import Path

import bpy

PROJECT = Path(__file__).resolve().parents[1]
NAME = "SM_FactoryBeltPlatform"
HEIGHT = 50
# El marco de la cinta mide 200 x 140: la plataforma ocupa lo mismo, para que dos seguidas se toquen.
SIZE = (200, 140, HEIGHT)

helpers = runpy.run_path(str(PROJECT / "Scripts" / "author_factory_detail_meshes.py"), run_name="belt_platform_helpers")
box, activate = helpers["_box"], helpers["_activate"]
report = {"passed": False, "blender_version": bpy.app.version_string}
try:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    graphite, steel, orange = 0, 1, 2
    materials = helpers["_materials"]()
    parts = [
        # Zocalo y cuerpo, metidos hacia adentro para que se lean las patas.
        box("Platform_Plinth", (0, 0, 3), (184, 124, 6), 1.2, materials, graphite),
        box("Platform_Body", (0, 0, 26), (176, 116, 40), 1.5, materials, graphite),
        # Tapa: donde apoya el chasis de la cinta.
        box("Platform_Top", (0, 0, 47.5), (200, 140, 5), 1.2, materials, steel),
    ]
    for y in (-63, 63):
        parts.append(box("Platform_SideRail", (0, y, 24), (172, 6, 8), 1.0, materials, steel))
        for x in (-93, 93):
            parts.append(box("Platform_Leg", (x, y, 27.5), (14, 14, 35), 1.4, materials, steel))
            parts.append(box("Platform_Foot", (x, y, 5), (14, 14, 10), 1.4, materials, orange))
    for x in (-93, 93):
        parts.append(box("Platform_EndRail", (x, 0, 24), (6, 112, 8), 1.0, materials, steel))
    activate(parts[0])
    for part in parts:
        part.select_set(True)
    bpy.ops.object.join()
    platform = bpy.context.object
    platform.name = NAME
    platform.data.name = NAME + "_Geometry"
    report["asset"] = helpers["_bounds_and_export"](platform, NAME, SIZE, 0)
    report["height_cm"] = HEIGHT
    report["passed"] = True
except Exception as error:
    report["error"] = repr(error)
    raise
finally:
    (helpers["DEST"] / "belt_platform_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("[BELT_PLATFORM_AUTHORING] " + json.dumps(report), flush=True)
