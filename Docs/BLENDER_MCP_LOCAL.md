# Blender MCP local para FactoryCtyco

Conexión instalada y usada el 19 de septiembre de 2026 para modelar la nueva
cinta y las piezas biseladas de la fábrica. Blender 5.2.1 LTS recibe las
operaciones en `127.0.0.1:9876`; el servidor MCP se comunica por stdio.

Se utiliza el proyecto comunitario
[mcp-for-blender](https://github.com/ahujasid/mcp-for-blender), distribución
[2.0.0](https://pypi.org/project/mcp-for-blender/2.0.0/). Su código, dependencias,
configuración de Blender y archivos temporales están en
`Saved/VisualPolishWork/BlenderMCP`. No se modificó la configuración global de
Codex ni las preferencias de la sesión habitual de Blender. La telemetría está
desactivada para esta conexión.

Desde la raíz del proyecto, iniciar o comprobar la sesión dedicada:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./Scripts/start_blender_factory_mcp.ps1
& 'C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe' Scripts/blender_factory_mcp.py inspect
```

El iniciador abre Blender oculto y reutiliza su propia sesión si sigue viva.
La conexión usa el protocolo MCP real: `initialize`, `tools/list` y `tools/call`.
El cliente conserva las respuestas en subcarpetas `Call-<fecha>`.

Para ejecutar un archivo revisado del proyecto o obtener una captura:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe' Scripts/blender_factory_mcp.py execute --code-file Scripts/author_factory_detail_meshes.py --timeout 180
& 'C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe' Scripts/blender_factory_mcp.py screenshot
```

El primer comando regenera únicamente la biblioteca de detalles y respalda
sus resultados anteriores. Los originales del proyecto permanecen en sus
carpetas. La fuente editable está en
`SourceAssets/Factory/VisualPolish/FactoryDetails.blend`; su manifiesto incluye
dimensiones, materiales, triángulos y hashes de los FBX.

En Unreal se usó el MCP nativo de `McpAutomationBridge`, limitado al proyecto
FactoryCtyco. `Scripts/unreal_factory_mcp.py` lee el token local sin imprimirlo,
descubre los contratos y envía operaciones. Las rutas de scripts pasadas al
servidor son relativas al proyecto. El importador es
`Scripts/import_factory_details.py` y no regenera el mapa.

Evidencia: `installation.json` y `launch.json` dentro de `BlenderMCP`,
`SourceAssets/Factory/VisualPolish/manifest.json`,
`Docs/factory_detail_import.json` y `Docs/factory_belt_blender.png`.
