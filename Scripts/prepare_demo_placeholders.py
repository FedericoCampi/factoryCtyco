"""Small procedural fallback pieces while ambiguous source names are identified."""
import json
from pathlib import Path
import bpy

DEST = Path(__file__).resolve().parents[1] / "SourceAssets/Factory"
report = json.loads((DEST / "manifest.json").read_text())


def box(name, location, scale):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj=bpy.context.object
    obj.name=name
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel=obj.modifiers.new("RoundedEdges","BEVEL")
    bevel.width=.01
    bevel.segments=2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return obj


for name in ["BeltBasic","PlateBasic","FragmentsBasic"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if name=="BeltBasic":
        box("Belt",(0,0,.11),(.62,1,.08))
        for x in [-.34,.34]: box("Rail",(x,0,.12),(.05,1,.1))
        for y in [-.43,.43]: box("Roller",(0,y,.07),(.72,.1,.12))
    elif name=="PlateBasic":
        box("Plate",(0,0,.04),(.55,1,.08))
    else:
        for i in range(4):
            obj=box("Fragment",(((i%2)-.5)*.4,((i//2)-.5)*.5,.16+(.06 if i%2 else 0)),(.5,.5,.3))
            obj.rotation_euler.z=i*.4
    objects=list(bpy.context.scene.objects)
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
    obj=bpy.context.object
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    obj.name="SM_"+name
    max_size=max(obj.dimensions)
    obj.scale=(1/max_size,)*3
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    floor=min(v.co.z for v in obj.data.vertices)
    for vertex in obj.data.vertices: vertex.co.z-=floor
    folder=DEST/name
    folder.mkdir(exist_ok=True)
    filename=folder/(obj.name+".fbx")
    bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={"MESH"},axis_forward="-Y",axis_up="Z",apply_unit_scale=True,add_leaf_bones=False)
    obj.data.calc_loop_triangles()
    entry={"id":name,"source":"procedural fallback","fbx":str(filename.relative_to(DEST)).replace("\\","/"),"textures":{},"triangles_game":len(obj.data.loop_triangles),"base_color_factor":[.10,.17,.22,1] if name=="BeltBasic" else [.48,.53,.57,1],"roughness_factor":.55,"metallic_factor":.65}
    report["assets"]=[row for row in report["assets"] if row["id"]!=name]+[entry]
(DEST/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
