"""Paso 5 de apply_proceso_fundicion.py (se corre desde ahi, con sus nombres): el actor Proceso_Fundicion.

Va en el lugar del horno. Recibe el cuarzo de Cinta_Fabrica_1 en la boca del horno (MOUTH_Z, del script principal: la
colision del horno es una caja, asi que la altura del borde se tomo a ojo de las capturas), y el liquido baja por:
borde del horno -> tolva del tubo -> canaleta del tubo -> codo (curva) -> boca del codo -> cae en Container_Producto.
Los puntos de la canaleta salen de tubo_build.json y codo_build.json (los mismos que usa apply_linea_descarga.py),
un poco por debajo del eje del caño (la superficie del liquido). Todos se pueden arrastrar despues en el visor.
Del codo al contenedor la canaleta sigue con caños rectos (Cano_Recto_1..N, SM_CanoRecto estirado en X), bajando
RUN_SLOPE grados, hasta quedar arriba del centro del contenedor; de ahi el silicio cae. Se rehacen cada vez.
"""
LIQUID_DEPTH = 7.0        # la superficie del liquido va asi de abajo del eje del caño
CONTROL = (-450, -470)    # donde pararse para encender y colar (piso, al lado del horno)
RUN_SLOPE = 3.0           # grados que bajan los caños rectos hacia el contenedor
CANO = "/Game/FactoryCtyco/Environments/CanoRecto"

horno = by_label["Horno_Fundicion"]
tubo, codo, container = by_label["Tubo_Descarga"], by_label["Codo_Metalico"], by_label["Container_Producto"]
tubo_build = json.loads((project / "SourceAssets/TuboDescarga/tubo_build.json").read_text(encoding="utf-8"))
codo_build = json.loads((project / "SourceAssets/CodoMetalico/codo_build.json").read_text(encoding="utf-8"))
linea = json.loads((project / "Docs/linea_descarga.json").read_text(encoding="utf-8"))

t = tubo.get_actor_transform()
tan = math.tan(math.radians(tubo_build["outlet_slope_deg"]))
ox, _, oz = tubo_build["outlet_cm"]
axis_z = lambda x: oz + tan * (x - ox)                  # eje del caño, en el espacio del tubo
down = unreal.Vector(0, 0, -LIQUID_DEPTH)
hopper = t.transform_location(unreal.Vector(-80, 0, 0))
path = [unreal.Vector(hopper.x + 20, hopper.y, MOUTH_Z),          # cae del borde del horno
        t.transform_location(unreal.Vector(-80, 0, 55)),          # fondo de la tolva
        t.transform_location(unreal.Vector(-56, 0, axis_z(-56))) + down,
        t.transform_location(unreal.Vector(ox, 0, axis_z(ox))) + down]
# el codo: curva de la boca del tubo a la del codo, con el vertice donde se cruzan los dos ejes
c = codo.get_actor_transform()
inlet = codo_build["ports"][linea["codo"]["inlet_port"]]
outlet = codo_build["ports"][1 - linea["codo"]["inlet_port"]]
joint = c.transform_location(vec(inlet["center_cm"]))
spout = c.transform_location(vec(outlet["center_cm"]))
flow_in = c.transform_direction(vec(inlet["facing"])) * -1.0
flow_out = c.transform_direction(vec(outlet["facing"]))
den = flow_in.x * flow_out.y - flow_in.y * flow_out.x
k = ((spout.x - joint.x) * flow_out.y - (spout.y - joint.y) * flow_out.x) / den
corner = unreal.Vector(joint.x + flow_in.x * k, joint.y + flow_in.y * k, (joint.z + spout.z) / 2)
for f in (0.25, 0.5, 0.75):
    p = joint * (1 - f) ** 2 + corner * (2 * f * (1 - f)) + spout * f ** 2
    path.append(p + down)
path.append(spout + down)

# caños rectos del codo hasta arriba del contenedor
cano_build = json.loads((project / "SourceAssets/CanoRecto/cano_build.json").read_text(encoding="utf-8"))
for old in [a for a in actors.get_all_level_actors() if a.get_actor_label().startswith("Cano_Recto_")]:
    actors.destroy_actor(old)
if lib.does_asset_exist(f"{CANO}/SM_CanoRecto") and not lib.delete_asset(f"{CANO}/SM_CanoRecto"):
    raise RuntimeError("No se pudo borrar SM_CanoRecto")   # reimportar encima dejaba la malla al 1 %
options = unreal.FbxImportUI()
options.import_mesh, options.import_as_skeletal = True, False
options.import_materials = options.import_textures = True
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
options.automated_import_should_detect_type = False
data = options.static_mesh_import_data
data.combine_meshes, data.auto_generate_collision, data.one_convex_hull_per_ucx = True, False, True
data.convert_scene = data.convert_scene_unit = True
data.generate_lightmap_u_vs = data.build_nanite = False
task = unreal.AssetImportTask()
task.filename = str(project / "SourceAssets/CanoRecto/SM_CanoRecto.fbx")
task.destination_path, task.destination_name = CANO, "SM_CanoRecto"
task.automated = task.save = task.replace_existing = True
task.factory, task.options = unreal.FbxFactory(), options
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
lib.save_directory(CANO, only_if_is_dirty=True, recursive=True)
cano_mesh = unreal.load_asset(f"{CANO}/SM_CanoRecto")
if not isinstance(cano_mesh, unreal.StaticMesh):
    raise RuntimeError("No se importo SM_CanoRecto")
ahead = unreal.Vector(flow_out.x, flow_out.y, 0).normal()
centre = container.get_actor_location()
run = (centre.x - spout.x) * ahead.x + (centre.y - spout.y) * ahead.y   # hasta arriba del centro del contenedor
pieces = max(1, math.ceil(run / cano_build["length_cm"]))
step = run / pieces
drop = math.tan(math.radians(RUN_SLOPE)) * step
yaw = math.degrees(math.atan2(ahead.y, ahead.x))
for i in range(pieces):
    inlet_at = spout + ahead * (step * i) - unreal.Vector(0, 0, drop * i)
    pipe = actors.spawn_actor_from_class(unreal.StaticMeshActor, inlet_at, unreal.Rotator(0, -RUN_SLOPE, yaw))
    pipe.set_actor_label(f"Cano_Recto_{i + 1}")
    pipe.set_folder_path(str(tubo.get_folder_path()))
    pipe.static_mesh_component.set_static_mesh(cano_mesh)
    pipe.static_mesh_component.set_collision_profile_name("BlockAll")
    pipe.set_actor_scale3d(unreal.Vector(math.hypot(step, drop) / cano_build["length_cm"], 1, 1))
    path.append(inlet_at + ahead * step - unreal.Vector(0, 0, drop) + down)
report["canos"] = {"tramos": pieces, "largo_cm": round(step, 1), "desde": rnd(spout), "hasta": rnd(path[-1])}

melt = by_label.get("Proceso_Fundicion")
if melt is None:
    melt = actors.spawn_actor_from_class(unreal.FactoryMeltProcess, horno.get_actor_location(), unreal.Rotator())
    melt.set_actor_label("Proceso_Fundicion")
    melt.set_folder_path(str(horno.get_folder_path()))
melt.modify()
melt.set_actor_location(horno.get_actor_location(), False, False)
melt.set_actor_rotation(unreal.Rotator(), False)
inv = melt.get_actor_transform()
local = lambda p: inv.inverse_transform_location(p)
melt.set_editor_property("feed_belt", by_label["Cinta_Fabrica_1"])
melt.set_editor_property("container", container)
melt.set_editor_property("input_item", "CrushedStone")       # desde el 03/10: piedra triturada (apply_piedras.py)
try:
    melt.set_editor_property("input_label", "PIEDRA TRITURADA")
except Exception:
    pass
melt.set_editor_property("ingot_resource", ingot)
melt.set_editor_property("molten_material", molten)
melt.set_editor_property("glow_intensity", 8000.0)
melt.set_editor_property("mouth_point", local(unreal.Vector(horno.get_actor_location().x, horno.get_actor_location().y, MOUTH_Z)))
melt.set_editor_property("control_point", local(unreal.Vector(CONTROL[0], CONTROL[1], 4)))
melt.set_editor_property("pour_path", [local(p) for p in path])
# el contenedor mide 150 x 70 x 56: el lingote llena el interior hasta un poco abajo del borde
melt.set_editor_property("fill_min", unreal.Vector(-62, -26, 12))
melt.set_editor_property("fill_max", unreal.Vector(62, 26, 48))
report["process"] = {"actor": melt.get_actor_label(), "path": [rnd(p) for p in melt.world_pour_path()],
                     "feed": melt.get_editor_property("feed_belt").get_actor_label()}
