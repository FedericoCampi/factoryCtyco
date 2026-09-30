"""Run the gameplay check for the current isometric version of the arena."""
from pathlib import Path
import unreal

script = Path(unreal.Paths.project_dir()).resolve() / 'Scripts/playtest_gathering.py'
# Keep callbacks in Unreal's persistent Python globals until the test ends.
exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), globals())
