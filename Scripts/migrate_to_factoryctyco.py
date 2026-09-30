"""Editor Python (una sola vez, 30/09/2026): pasa el contenido de ArenaProject a FactoryCtyco. Se corre dos veces.

Con el modulo ya renombrado (FactoryCtycoRuntime; las [CoreRedirects] de DefaultEngine.ini llevan las clases viejas
/Script/ArenaRuntime.* a las nuevas).

Fase 1 (queda algo en /Game/Arena fuera de los mapas):
- anota cuantos actores de cada clase tiene cada mapa (Docs/migracion_antes.json);
- con un mapa en blanco abierto, mueve todos los assets de /Game/Arena (menos los mapas) a /Game/FactoryCtyco, con
  BP_ArenaGameMode -> BP_FactoryGameMode; el editor corrige y guarda lo que los usa (tambien los mapas).
  Los mapas no se mueven desde el editor: al renombrar un mapa pide confirmacion en una ventana.
Entre fases, a mano: mover los .umap de Content/Arena/Maps a Content/FactoryCtyco/Maps (L_Arena -> L_Recoleccion).
Fase 2 (ya no hay nada en /Game/Arena):
- en los Blueprints, los componentes ArenaCamera / ArenaCameraControls pasan a FactoryCamera / FactoryCameraControls;
- vuelve a guardar todo el contenido (las referencias quedan escritas con los nombres nuevos);
- en cada mapa cambia las etiquetas con Arena (SceneRobot_Arena, Arena_Backdrop*, Arena_SoftFill) y lo guarda;
- compara los actores de cada mapa con los de la fase 1: los mismos, de las mismas clases, ninguno sin clase.
Informes: Docs/migracion_fase1.json y Docs/migracion_fase2.json. Con -unattended cierra al terminar.
"""
import json
import traceback
from collections import Counter
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
lib = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OLD, NEW = "/Game/Arena", "/Game/FactoryCtyco"
ASSET_RENAMES = {"BP_ArenaGameMode": "BP_FactoryGameMode"}
MAP_RENAMES = {"L_Arena": "L_Recoleccion"}
LABELS = [("SceneRobot_Arena", "SceneRobot_Fabrica"), ("Arena_Backdrop", "Piso_Exterior"), ("Arena_SoftFill", "Luz_Relleno")]
COMPONENTS = {"ArenaCamera": "FactoryCamera", "ArenaCameraControls": "FactoryCameraControls"}
registry = unreal.AssetRegistryHelpers.get_asset_registry()
report = {"passed": False}


def assets_in(root):
    return [a for a in registry.get_assets_by_path(root, recursive=True)]


def is_map(data):
    return str(data.asset_class_path.asset_name) == "World"


def census(path):
    if not levels.load_level(path):
        raise RuntimeError(f"No se pudo abrir {path}")
    found = actors.get_all_level_actors()
    return {"actors": len(found), "classes": dict(Counter(a.get_class().get_name() for a in found))}


def phase1():
    maps = sorted(str(a.package_name) for a in assets_in(OLD) if is_map(a))
    before = {m: census(m) for m in maps}
    (project / "Docs/migracion_antes.json").write_text(json.dumps(before, indent=1), encoding="utf-8")
    unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    moves = []
    for a in assets_in(OLD):
        if is_map(a):
            continue
        old_path = str(a.package_path)
        name = str(a.asset_name)
        moves.append(unreal.AssetRenameData(asset=a.get_asset(), new_package_path=NEW + old_path[len(OLD):],
                                            new_name=ASSET_RENAMES.get(name, name)))
    ok = unreal.AssetToolsHelpers.get_asset_tools().rename_assets(moves)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    left = [str(a.package_name) for a in assets_in(OLD) if not is_map(a)]
    report.update(maps=maps, moved=len(moves), rename_ok=ok, not_moved=left[:20])
    report["passed"] = ok and not left


def phase2():
    before = json.loads((project / "Docs/migracion_antes.json").read_text(encoding="utf-8"))
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    redirectors = [a for a in assets_in("/Game") if str(a.asset_class_path.asset_name) == "ObjectRedirector"]
    if redirectors:
        tools.fixup_referencers([lib.load_asset(str(a.package_name)) for a in redirectors])
    left = [str(a.package_name) for a in assets_in("/Game") if str(a.asset_class_path.asset_name) == "ObjectRedirector"]
    for p in left:
        lib.delete_asset(p)
    report["redirectors"] = {"fixed": len(redirectors), "deleted": len(left)}

    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs = unreal.SubobjectDataBlueprintFunctionLibrary
    renamed = []
    for a in assets_in(NEW):
        if str(a.asset_class_path.asset_name) != "Blueprint":
            continue
        bp = a.get_asset()
        touched = False
        for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
            name = str(funcs.get_variable_name(subsystem.k2_find_subobject_data_from_handle(handle)))
            if name in COMPONENTS:
                subsystem.rename_subobject(handle, COMPONENTS[name])
                renamed.append(f"{bp.get_name()}.{name}")
                touched = True
        if touched:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    report["components"] = renamed

    saved = 0
    for a in assets_in(NEW):
        if is_map(a):
            continue
        asset = a.get_asset()
        if asset and lib.save_loaded_asset(asset, False):
            saved += 1
    report["resaved"] = saved

    problems, maps = [], {}
    for old_map, info in before.items():
        name = old_map.rsplit("/", 1)[1]
        new_map = f"{NEW}/Maps/{MAP_RENAMES.get(name, name)}"
        if not levels.load_level(new_map):
            problems.append(f"no abre {new_map}")
            continue
        relabeled = []
        for actor in actors.get_all_level_actors():
            label = actor.get_actor_label()
            for old, new in LABELS:
                if label.startswith(old):
                    actor.set_actor_label(new + label[len(old):])
                    relabeled.append(label)
        if not unreal.EditorLoadingAndSavingUtils.save_current_level():
            problems.append(f"no guarda {new_map}")
        got = census(new_map)
        maps[new_map] = {"actors": got["actors"], "relabeled": relabeled}
        if got != info:
            problems.append({"mapa": new_map, "antes": info["actors"], "despues": got["actors"],
                             "clases": {k: [info["classes"].get(k), got["classes"].get(k)] for k in set(info["classes"]) | set(got["classes"])
                                        if info["classes"].get(k) != got["classes"].get(k)}})
    report.update(maps=maps, problems=problems, left_in_old=[str(a.package_name) for a in assets_in(OLD)])
    report["passed"] = not problems and not report["left_in_old"]


PHASE = 1 if any(not is_map(a) for a in assets_in(OLD)) else 2
try:
    report["phase"] = PHASE
    phase1() if PHASE == 1 else phase2()
except Exception:
    report["error"] = traceback.format_exc()
finally:
    (project / f"Docs/migracion_fase{PHASE}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if "-unattended" in unreal.SystemLibrary.get_command_line().lower():
        unreal.SystemLibrary.quit_editor()
