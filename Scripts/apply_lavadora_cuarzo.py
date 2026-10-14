"""Pasos 3-4 de apply_proceso_fundicion.py cuando la linea la ubica el usuario (MANAGE_LAYOUT = False), 02/10.

Se corre desde ahi, con sus nombres (by_label, quartz, sim, report, receiver_of, material, mel, lib...). No mueve lo
que ubico el usuario; la caja, el deposito y el largo de la cinta los deja apply_tunel_lavadora.py:
- Lavadora_Cuarzo: la caja gris pasa a ser un tunel (SM_LavadoraTunel, author_lavadora_tunel.py: dos huecos
  enfrentados) por donde pasa Cinta_Cuarzo_Triturar. Es un StaticMeshActor (adorno): por ahora no le hace nada al
  material. Choca con su propia malla, asi que los huecos quedan abiertos.
- Deposito_Cuarzo (100 de cuarzo; entrega arriba, a la altura de la cinta: MachineOutput) -> Cinta_Cuarzo_Triturar
  (plana, como la dejo el usuario: atraviesa la caja) -> Plataforma_Elevadora_1 (al lado de la trituradora: sube la
  carga de la altura de la cinta a la de la tolva; la cinta se acorta para que entre) -> Trituradora_Cuarzo (cuarzo ->
  arena; recibe por arriba y entrega abajo, MachineInput / MachineOutput) -> Cinta_Fabrica_2 -> ... -> horno.
- Trituradora_Tapa: la tapa de salida (SM_TapaSalida, author_tapa_salida.py) sobre la punta de Cinta_Fabrica_2, pegada
  a la trituradora (se mueve con ella).
"""
TUNNEL = "/Game/FactoryCtyco/Factory/Models/Deposito/SM_LavadoraTunel"
TAPA = "/Game/FactoryCtyco/Factory/Models/Trituradora/SM_TapaSalida"
TAPA_SCALE = 1.4          # la campana mide 80 cm de ancho; la cinta, 105
TAPA_BACK = 25.0          # cm de la boca de la trituradora hacia adentro donde va la placa de atras
TAPA_Z = 40.0             # cm sobre el piso de la cinta: abajo de la campana pasa la carga
LIFT = "Plataforma_Elevadora_1"
HOPPER_Z = 237.0          # cm: donde la carga entra en la tolva (arriba de la trituradora)


def import_plain(fbx, path, mat, complex_collision):
    """Malla sin materiales del FBX (se le pone mat); borra la vieja antes (reimportar encima la dejaba al 1 %)."""
    folder, name = path.rsplit("/", 1)
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path, task.destination_name = folder, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    mesh.set_material(0, mat)
    if complex_collision:
        body = mesh.get_editor_property("body_setup")
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(mesh)
    return mesh


def tapa_material(m):
    color = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    color.set_editor_property("constant", unreal.LinearColor(0.16, 0.17, 0.18))
    metal = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 120)
    metal.set_editor_property("r", 0.85)
    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 240)
    rough.set_editor_property("r", 0.45)
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)


# la trituradora: de cada bloque (lo corta la sierra de la caja, Sierra_Estacion) saca 2 piedras trituradas (apply_piedras.py)
crusher_def = unreal.load_asset(f"{DEFS}/DB_QuartzCrusher")
for prop, value in (("input_item", "StoneBlock"), ("output_item", "CrushedStone"), ("output_quantity", 2)):
    crusher_def.set_editor_property(prop, value)
lib.save_loaded_asset(crusher_def)

# la caja gris: tunel (si ya lo es, solo se le reimporta la malla, por si cambiaron los huecos)
box = by_label["Lavadora_Cuarzo"]
if isinstance(box, unreal.StaticMeshActor):
    box.static_mesh_component.set_static_mesh(None)
    box.static_mesh_component.set_static_mesh(import_plain(project / "SourceAssets/LavadoraTunel/SM_LavadoraTunel.fbx", TUNNEL,
                                                           unreal.load_asset("/Game/FactoryCtyco/Factory/Models/Deposito/M_Deposito"), True))
if isinstance(box, unreal.FactoryBuilding):
    look = box.get_editor_property("visual").get_world_transform()
    folder = str(box.get_folder_path())
    tunnel = import_plain(project / "SourceAssets/LavadoraTunel/SM_LavadoraTunel.fbx", TUNNEL,
                          unreal.load_asset("/Game/FactoryCtyco/Factory/Models/Deposito/M_Deposito"), True)
    actors.destroy_actor(box)
    box = actors.spawn_actor_from_class(unreal.StaticMeshActor, look.translation, look.rotation.rotator())
    box.set_actor_label("Lavadora_Cuarzo")
    box.set_folder_path(folder)
    box.set_actor_scale3d(look.scale3d)
    box.static_mesh_component.set_static_mesh(tunnel)
    box.static_mesh_component.set_collision_profile_name("BlockAll")
    by_label["Lavadora_Cuarzo"] = box
report["tunel"] = {"actor": box.get_class().get_name(), "malla": box.static_mesh_component.static_mesh.get_name()}

depot, feeder, crusher = by_label["Deposito_Cuarzo"], by_label["Cinta_Cuarzo_Triturar"], by_label["Trituradora_Cuarzo"]
line = [by_label[label] for label, _, _ in LINE]
stock = depot.get_editor_property("input")
if stock.get_quantity("Quartz") == 0:
    stock.add_item(quartz, DEPOT_START)
# la plataforma: pegada a la trituradora del lado de la cinta; recibe a la altura de la cinta y sube hasta la tolva
lift = by_label[LIFT]
along = feeder.output_point() - feeder.input_point()
along = unreal.Vector(along.x, along.y, 0).normal()          # hacia la trituradora
ct = crusher.get_actor_transform()
cdef = crusher.get_editor_property("definition")
cb, cs = cdef.get_editor_property("mesh").get_bounding_box(), cdef.get_editor_property("mesh_scale")
corners = [ct.transform_location(unreal.Vector(x * cs.x, y * cs.y, 0)) for x in (cb.min.x, cb.max.x) for y in (cb.min.y, cb.max.y)]
centre = crusher.get_actor_location()
edge = max((c.x - centre.x) * -along.x + (c.y - centre.y) * -along.y for c in corners)   # borde de la trituradora hacia la cinta
belt_z = feeder.input_point().z
top_out = unreal.Vector(centre.x - along.x * edge, centre.y - along.y * edge, HOPPER_Z)
bottom_in = unreal.Vector(top_out.x - along.x * 200, top_out.y - along.y * 200, belt_z)
lift.modify()
lift.set_editor_property("elevation", belt_z - 33 - FLOOR)
lift.set_editor_property("lift_height", HOPPER_Z - belt_z)
lift.set_actor_rotation(unreal.Rotator(0, 0, math.degrees(math.atan2(along.y, along.x))), False)
lift.set_actor_location(unreal.Vector(bottom_in.x, bottom_in.y, FLOOR), False, False)
lift.set_actor_location(lift.get_actor_location() + bottom_in - lift.input_point(), False, False)
lift.refresh_visuals()
lift.build_supports()
feeder.modify()
fit_straight(feeder, feeder.input_point(), bottom_in)          # se acorta hasta la plataforma
feeder.build_supports()
# el deposito entrega arriba, a la altura de la cinta
d_out = depot.output_point()
depot.modify()
depot.set_editor_property("machine_output", depot.get_actor_transform().inverse_transform_location(unreal.Vector(d_out.x, d_out.y, belt_z)))
depot.refresh_visuals()

crusher.modify()
crusher.set_editor_property("machine_input", ct.inverse_transform_location(lift.output_point()))
# lo que llega se ve caer en la tolva (en el medio de la trituradora, un poco abajo del borde)
crusher.set_editor_property("machine_drop_point", ct.inverse_transform_location(unreal.Vector(centre.x, centre.y, HOPPER_Z - 30)))
crusher.set_editor_property("machine_output", ct.inverse_transform_location(line[0].input_point()))
crusher.refresh_visuals()

# la tapa de salida, sobre la punta de la cinta que va al horno, mirando hacia donde va la cinta
tapa_mesh = import_plain(project / "SourceAssets/TapaSalida/SM_TapaSalida.fbx", TAPA, material("M_TapaSalida", tapa_material), False)
for a in [a for a in actors.get_all_level_actors() if a.get_actor_label() == "Trituradora_Tapa"]:
    actors.destroy_actor(a)
spout = crusher.output_point()
ahead = line[0].output_point() - line[0].input_point()
ahead = unreal.Vector(ahead.x, ahead.y, 0).normal()
tapa = actors.spawn_actor_from_class(unreal.StaticMeshActor, spout - ahead * TAPA_BACK + unreal.Vector(0, 0, TAPA_Z - 33),
                                     unreal.Rotator(0, 0, math.degrees(math.atan2(ahead.y, ahead.x))))
tapa.set_actor_label("Trituradora_Tapa")
tapa.set_folder_path(str(crusher.get_folder_path()))
tapa.set_actor_scale3d(unreal.Vector(TAPA_SCALE, TAPA_SCALE, TAPA_SCALE))
tapa.static_mesh_component.set_static_mesh(tapa_mesh)
tapa.static_mesh_component.set_collision_profile_name("NoCollision")
tapa.attach_to_actor(crusher, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)

chain = [depot, feeder, lift, crusher] + line
report["chain"] = [{"from": b.get_actor_label(), "to": receiver_of(b, chain)} for b in chain]
report["deposito"] = {"cuarzo": stock.get_quantity("Quartz"), "salida": rnd(depot.output_point())}
report["cinta_a_trituradora"] = {"in": rnd(feeder.input_point()), "out": rnd(feeder.output_point()),
                                 "slope": round(feeder.get_editor_property("slope"), 1)}
report["trituradora"] = {"entra": rnd(crusher.input_point()), "sale": rnd(crusher.output_point()),
                         "tapa": rnd(tapa.get_actor_location())}
report["plataforma"] = {"recibe": rnd(lift.input_point()), "entrega": rnd(lift.output_point()),
                        "sube_cm": round(lift.get_editor_property("lift_height"))}
report["riser_overlaps"] = []
