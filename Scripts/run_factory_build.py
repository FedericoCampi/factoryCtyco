"""Run both preparation stages in the full editor (editor subsystems are required)."""
import runpy
from pathlib import Path
import unreal

folder=Path(__file__).resolve().parent
try:
    runpy.run_path(str(folder/"import_factory_models.py"),run_name="__main__")
    runpy.run_path(str(folder/"build_factory_demo.py"),run_name="__main__")
finally:
    unreal.SystemLibrary.quit_editor()
