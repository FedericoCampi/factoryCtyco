"""Blender: agujeros en el piso para los pozos de AFactoryElevator (ascensor2).

Lo usan author_arena_edit.py (SceneRobot) y author_parking_scene.py (Parking) antes de unir las piezas.
El tamano sale de SourceAssets/Ascensor2/elevator2_build.json (medio exterior del tubo); el centro de
cada agujero esta en coordenadas Blender (m) de la malla correspondiente: Unreal local (x, y, z) cm =
Blender (x, -y, z) m * 100. El agujero es simetrico, asi el ascensor se puede girar 180 grados.
Si se mueve un ascensor, actualizar HOLES y regenerar esa malla.
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from elevator_holes import HOLES  # noqa: E402
DEPTH = 2.0   # cuanto piso se corta por debajo de la superficie
ABOVE = 0.05  # y por encima (juntas, tornillos, desgaste)


def half_extent():
    build = json.loads((PROJECT / "SourceAssets/Ascensor2/elevator2_build.json").read_text())
    return build["tube"]["hole_half_m"]


def boxes(scene_key):
    hx, hy = half_extent()
    return [(Vector((x - hx, y - hy, z - DEPTH)), Vector((x + hx, y + hy, z + ABOVE))) for x, y, z in HOLES[scene_key]]


def world_box(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def overlaps(lo, hi, clo, chi):
    return all(lo[i] < chi[i] and hi[i] > clo[i] for i in range(3))


def inside(lo, hi, clo, chi):
    return all(lo[i] >= clo[i] - 1e-4 and hi[i] <= chi[i] + 1e-4 for i in range(3))


def cut_visuals(objects, scene_key):
    """Corta el agujero en las piezas visibles; devuelve la lista sin las que quedaron vacias."""
    removed = cut = 0
    alive = {o.name: o for o in objects}
    for clo, chi in boxes(scene_key):
        cutter = bpy.data.objects.new("hole_cutter", bpy.data.meshes.new("hole_cutter"))
        b = bmesh.new()
        vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
        for v in vs:
            v.co = Vector((v.co.x * (chi.x - clo.x), v.co.y * (chi.y - clo.y), v.co.z * (chi.z - clo.z))) + (clo + chi) / 2
        b.to_mesh(cutter.data)
        b.free()
        bpy.context.scene.collection.objects.link(cutter)
        for o in [o for o in alive.values() if o.type == "MESH"]:
            lo, hi = world_box(o)
            if not overlaps(lo, hi, clo, chi):
                continue
            if inside(lo, hi, clo, chi):
                del alive[o.name]
                bpy.data.objects.remove(o)
                removed += 1
                continue
            o.data = o.data.copy()  # las piezas del GLB comparten malla: cortar solo esta
            mod = o.modifiers.new("hole", "BOOLEAN")
            mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", cutter
            mod.use_hole_tolerant = True
            # las caras del corte toman el primer material de la pieza: sin ranuras vacias
            cutter.data.materials.clear()
            if o.data.materials and o.data.materials[0]:
                cutter.data.materials.append(o.data.materials[0])
            mod.material_mode = "TRANSFER"
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)
            # respaldo por si el booleano deja caras sueltas adentro (piezas abiertas o planas)
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bm.transform(o.matrix_world)
            stray = [f for f in bm.faces if (lambda c: clo.x < c.x < chi.x and clo.y < c.y < chi.y and clo.z < c.z < chi.z)(f.calc_center_median())]
            bmesh.ops.delete(bm, geom=stray, context="FACES")
            bm.transform(o.matrix_world.inverted())
            bm.to_mesh(o.data)
            bm.free()
            if not o.data.polygons:
                del alive[o.name]
                bpy.data.objects.remove(o)
                removed += 1
            cut += 1
        bpy.data.objects.remove(cutter)
    print(f"FLOOR_HOLES {scene_key}: {cut} piezas cortadas, {removed} quitadas")
    return list(alive.values()), {"cut": cut, "removed": removed}


def is_box(o, lo, hi):
    w = o.matrix_world
    return all(min(abs((w @ v.co)[i] - lo[i]), abs((w @ v.co)[i] - hi[i])) < 2e-3 for v in o.data.vertices for i in range(3))


def split_collisions(objects, scene_key, make_box):
    """Reemplaza las cajas UCX que tapan el agujero por hasta 4 cajas alrededor.

    make_box(lo, hi) crea la caja nueva y la devuelve. Devuelve la lista actualizada de colisiones."""
    result, split, skipped = [], 0, []
    for o in objects:
        lo, hi = world_box(o)
        hit = next(((clo, chi) for clo, chi in boxes(scene_key) if overlaps(lo, hi, clo, chi)), None)
        if not hit:
            result.append(o)
            continue
        if not is_box(o, lo, hi):
            skipped.append(o.name)
            result.append(o)
            continue
        clo, chi = hit
        pieces = [((lo.x, lo.y), (clo.x, hi.y)), ((chi.x, lo.y), (hi.x, hi.y)),
                  ((max(lo.x, clo.x), lo.y), (min(hi.x, chi.x), clo.y)),
                  ((max(lo.x, clo.x), chi.y), (min(hi.x, chi.x), hi.y))]
        for (x0, y0), (x1, y1) in pieces:
            if x1 - x0 > 0.01 and y1 - y0 > 0.01:
                result.append(make_box(Vector((x0, y0, lo.z)), Vector((x1, y1, hi.z))))
        bpy.data.objects.remove(o)
        split += 1
    if skipped:
        print(f"FLOOR_HOLES {scene_key}: colisiones no rectangulares sobre el agujero (sin cortar): {skipped}")
    print(f"FLOOR_HOLES {scene_key}: {split} colisiones divididas")
    return result, {"split": split, "not_box": skipped}
