"""Editor Python: physics checks for the factory <-> parking doorway. Writes Docs/parking_link_check.json."""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
CHANNEL = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1  # Visibility; both scenes use BlockAll
RADIUS, HALF = 35.0, 90.0                          # BP_Robot1 capsule

def sweep(a, b):
    hit = unreal.SystemLibrary.capsule_trace_single(world, unreal.Vector(*a), unreal.Vector(*b), RADIUS, HALF,
        CHANNEL, False, [], unreal.DrawDebugTrace.NONE, True)
    return None if hit is None else hit.to_tuple()[4].x  # impact point X (None when clear)

def floor(x, y):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 300), unreal.Vector(x, y, -200),
        CHANNEL, False, [], unreal.DrawDebugTrace.NONE, True)
    return None if hit is None else round(hit.to_tuple()[4].z, 1)

checks = {}
z = HALF + 3
# Factory west opening spans Unreal Y -80..260; the parking's spans -75..255.
# Y=150 passes north of the demo storage that sits inside the factory near this door.
checks["walk_factory_to_parking"] = sweep((-700, 150, z), (-1900, 150, z)) is None
checks["walk_into_parking_centre"] = sweep((-1900, 150, z), (-2303, -410, z)) is None
checks["walk_back_to_factory_centre"] = sweep((-1900, 150, z), (-700, 150, z)) is None and sweep((-700, 150, z), (0, 300, z)) is None
checks["factory_wall_blocks_north_of_door"] = sweep((-700, 600, z), (-1900, 600, z)) is not None
checks["factory_wall_blocks_south_of_door"] = sweep((-700, -400, z), (-1900, -400, z)) is not None
checks["parking_outer_wall_blocks"] = sweep((-2303, -410, z), (-3700, -410, z)) is not None
profile = {x: floor(x, 90) for x in (-1400, -1250, -1190, -1175, -1160, -1145, -1125, -1100, -1000)}
checks["doorway_floor_flush"] = all(v is not None and abs(v) <= 2 for v in profile.values())
report = {"passed": all(checks.values()), "checks": checks, "doorway_floor_z_cm": profile}
(project / "Docs/parking_link_check.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
