"""Blender: camion volcador (08/10), el camion del usuario con la caja que se levanta.

Parte de SourceAssets/Camion/Camion.blend (author_truck_loop.py: ruedas, puerta y techo en huesos propios, origen en el
eje trasero, al piso, frente a +X) y agrega el hueso Caja, hijo de Camion, con la cabeza en la bisagra: abajo y atras de
la caja. Las caras de la caja (adelante de la cabina y desde el piso de la caja para arriba) pasan del hueso Camion a
Caja; Puerta y Techo pasan a ser hijos de Caja. AFactoryVehiclePath (bDumpTruck) gira Caja para volcar.
Sin animacion (la pone Unreal). Salida: SourceAssets/Camion/camion_volcador.fbx y camion_volcador_build.json.

blender -b --factory-startup -P Scripts/author_truck_dump.py
"""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Camion"
# en metros, desde el eje trasero al piso (medido el 08/10): la caja va de x -1,0 a 2,95 (ahi empieza la cabina, mas
# baja) y su piso por debajo esta a 0,80; abajo quedan el chasis y las ruedas
BOX_FRONT_X = 2.96
BOX_BOTTOM_Z = 0.795
HINGE = (-0.95, 0.0, 0.80)

bpy.ops.wm.open_mainfile(filepath=str(OUT / "Camion.blend"))
arm = bpy.data.objects["Camion"]
body = bpy.data.objects["SK_Camion_Mesh"]
arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)

# hueso Caja (como los demas: cola +Y, sin giro); Puerta y Techo cuelgan de el
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
caja = eb.new("Caja")
caja.head = HINGE
caja.tail = Vector(HINGE) + Vector((0, 0.3, 0))
caja.roll = 0
caja.parent = eb["Camion"]
for name in ("Puerta", "Techo"):
    eb[name].parent = caja
bpy.ops.object.mode_set(mode="OBJECT")

# caras de la caja: su centro atras de la cabina y arriba del piso de la caja (de la carroceria, no ruedas ni puerta)
def box_faces():
    n = len(body.data.polygons)
    centers = np.empty(n * 3); body.data.polygons.foreach_get("center", centers); centers = centers.reshape(-1, 3)
    truck_group = body.vertex_groups["Camion"].index
    in_truck = np.zeros(len(body.data.vertices), dtype=bool)
    for v in body.data.vertices:
        in_truck[v.index] = any(g.group == truck_group and g.weight > 0.5 for g in v.groups)
    inside = (centers[:, 0] < BOX_FRONT_X) & (centers[:, 2] >= BOX_BOTTOM_Z)
    return np.array([inside[p.index] and all(in_truck[i] for i in p.vertices) for p in body.data.polygons])


# se separan del resto (split: los vertices del borde se duplican), si no las caras vecinas se estiran al volcar
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.context.tool_settings.mesh_select_mode = (False, False, True)
body.data.vertices.foreach_set("select", np.zeros(len(body.data.vertices), dtype=bool))
body.data.edges.foreach_set("select", np.zeros(len(body.data.edges), dtype=bool))
body.data.polygons.foreach_set("select", box_faces())
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_mode(type="FACE")
bpy.ops.mesh.split()
bpy.ops.object.mode_set(mode="OBJECT")
verts = set()
for p, is_box in zip(body.data.polygons, box_faces()):
    if is_box:
        verts.update(p.vertices)
verts = sorted(verts)
body.vertex_groups["Camion"].remove(verts)
body.vertex_groups.new(name="Caja").add(verts, 1.0, "REPLACE")

bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); body.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "camion_volcador.fbx"), use_selection=True,
                         object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=False,
                         mesh_smooth_type="FACE", primary_bone_axis="Y", secondary_bone_axis="X",
                         path_mode="COPY", embed_textures=True)
report = {"source": "Camion.blend", "bones": [b.name for b in arm.data.bones], "hinge_cm": [HINGE[0] * 100, 0, HINGE[2] * 100],
          "box_vertices": len(verts), "box_front_m": BOX_FRONT_X, "box_bottom_m": BOX_BOTTOM_Z}
(OUT / "camion_volcador_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("CAMION_VOLCADOR_OK", json.dumps(report))
