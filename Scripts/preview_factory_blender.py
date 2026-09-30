"""Frame the isolated asset scene in the project's managed Blender session."""
import bpy
from mathutils import Quaternion

scene = bpy.data.scenes.get("FactoryVisualPolish")
if scene is None:
    raise RuntimeError("Generate the isolated factory detail scene first")
bpy.context.window.scene = scene
belt = next(obj for obj in scene.objects if obj.name.startswith("SM_FactoryBeltFrame"))
bpy.context.view_layer.objects.active = belt
belt.select_set(True)
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces.active
        space.overlay.show_overlays = False
        space.shading.type = "MATERIAL"
        space.shading.studiolight_rotate_z = .6
        space.region_3d.view_distance = 3.1
        space.region_3d.view_location = (0, 0, .16)
        space.region_3d.view_rotation = Quaternion((.820, .425, .176, .339)).normalized()
        space.region_3d.view_perspective = "PERSP"
        area.tag_redraw()
print("FactoryVisualPolish framed for MCP viewport review")
