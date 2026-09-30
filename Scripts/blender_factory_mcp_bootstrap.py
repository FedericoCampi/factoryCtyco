"""Load the upstream bundled Blender addon for this GUI session only.

Example (launch hidden with Start-Process, without --background):
blender.exe --factory-startup --python Scripts/blender_factory_mcp_bootstrap.py

Does not install addons, save preferences, or modify global MCP configuration.
"""
import importlib.util
import json
from pathlib import Path
import sys

import bpy


PROJECT = Path(__file__).resolve().parents[1]
WORK = PROJECT / "Saved" / "VisualPolishWork" / "BlenderMCP"
ADDON = WORK / "runtime" / "blender_mcp" / "bundled" / "addon.py"

if bpy.app.background:
    raise RuntimeError("The upstream Blender MCP addon needs the GUI event loop; omit --background.")
if bpy.data.filepath:
    raise RuntimeError("Use a fresh --factory-startup session, not an existing .blend document.")
if not ADDON.is_file():
    raise RuntimeError("Missing verified upstream bundled addon: " + str(ADDON))

WORK.mkdir(parents=True, exist_ok=True)
scratch = WORK / "scratch"
scratch.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory = str(scratch)
bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
bpy.context.preferences.filepaths.save_version = 0

name = "factory_visuals_blender_mcp"
spec = importlib.util.spec_from_file_location(name, ADDON)
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)
module.register()
# Pin this temporary bridge to loopback, and do not enable remote asset services.
bpy.context.scene.blendermcp_auto_start_server = False
bpy.context.scene.blendermcp_port = 9876
server = module.BlenderMCPServer(host="127.0.0.1", port=9876)
bpy.types.blendermcp_server = server
server.start()
bpy.context.scene.blendermcp_server_running = server.running
if not server.running:
    raise RuntimeError("The Blender MCP addon failed to bind 127.0.0.1:9876")

report = {
    "running": True,
    "blender_version": bpy.app.version_string,
    "host": "127.0.0.1",
    "port": 9876,
    "addon": str(ADDON),
    "addon_protocol": getattr(module, "ADDON_PROTOCOL_VERSION", None),
    "persistent_install": False,
}
(WORK / "bootstrap.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("[FACTORY_BLENDER_MCP] " + json.dumps(report))
