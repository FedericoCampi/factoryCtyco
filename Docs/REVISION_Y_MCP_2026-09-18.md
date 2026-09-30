# Revisión y conexión MCP — 18 de septiembre de 2026

## Resultado de la reparación

El servidor `unreal-engine` estaba configurado en Codex, pero FactoryCtyco no
tenía instalado McpAutomationBridge. El servidor HTTP nativo vive dentro del
editor: abrir un proyecto sin ese plugin no inicia el puerto 3000.

- Instalado McpAutomationBridge 0.5.30 desde la copia local de McpDemo.
  La DLL copiada conserva su SHA-256 y su BuildId 43139311 coincide con el motor.
- Habilitados McpAutomationBridge, MovieRenderPipeline y
  MoviePipelineMaskRenderPass solo para Editor. Los dos últimos resuelven las
  dependencias DLL que impidieron el primer arranque.
- Activado el transporte MCP nativo en el puerto 3000, limitado a loopback,
  con autenticación por token. El plugin generó el token del proyecto en
  `Saved/MCP/capability-token`; no se incluye en este documento.
- Actualizado el encabezado de Unreal en la configuración global de Codex.

## Verificación realizada

`Scripts/verify_mcp_connections.py` comprobó la configuración guardada:

| Conexión | Resultado |
| --- | --- |
| Unreal initialize | Correcto; servidor unreal-mcp 0.5.30 |
| Unreal tools/list | Herramienta `unreal` disponible |
| Unreal resources/read, ue://project | Correcto; identifica FactoryCtyco |
| Codex mcp list | Unreal habilitado |

La indicación `unsupported` de autenticación de Unreal en `codex mcp list`
no contradice la prueba: se usa el encabezado propio X-MCP-Capability-Token.

Reiniciar la sesión de Codex para volver a cargar las herramientas MCP.
Mantener FactoryCtyco abierto en Unreal cuando se utilice su conexión.
No hace falta ejecutar la regeneración de contenido para iniciar MCP.

Por decisión del usuario, FactoryCtyco usa únicamente la integración de Unreal.
Runpod está deshabilitado para este proyecto mediante `.codex/config.toml`,
tanto su servidor MCP como su plugin. Los scripts de configuración y diagnóstico
solo trabajan con Unreal y no leen credenciales de otros proyectos.

Respaldos: archivos del proyecto antes del cambio en
`Saved/MCPSetupBackup/20260917-235658/`; configuración de Codex en
`C:\Users\Usuario\.codex\config.toml.arena-mcp-20260918-000049.bak`.
Los respaldos de configuración pueden contener credenciales: no publicarlos.

## Revisión del proyecto

Se revisaron la documentación, configuración, fuentes C++ de FactoryCtycoRuntime,
scripts de preparación y pruebas, y registros del editor. No se recompiló
el juego ni se repitió la aceptación en Play durante esta revisión.

La demo es la versión 0.6.0 para Unreal 5.6.1. Incluye robot, cámara isométrica,
recolección, inventario, construcción, máquinas, cintas rectas y guardado manual.
El mapa inicial es `L_FactoryDemo`. El informe de aceptación existente registra
nueve grupos aprobados, 20 placas almacenadas y conservación de recursos;
es evidencia de la prueba anterior, no una ejecución nueva.

Observaciones pendientes, sin modificar la jugabilidad:

1. `Scripts/run_factory_editor.ps1:1` usa `Build` por defecto. Ejecutarlo sin
   argumentos vuelve a preparar contenido; `build_factory_demo.py:139` carga
   el mapa, elimina sus edificios y simulador de fábrica y guarda la línea
   inicial. Puede sobrescribir modificaciones manuales. Para abrir, usar
   `ABRIR_DEMO.cmd` o `-Mode Ready`; conviene que Ready sea el valor por defecto.
2. `FactoryDemoHUD.cpp:109` muestra la interacción de una máquina siempre que
   exista una enfocada, mientras `FactoryDemo.cpp:529` da prioridad con E a un
   montón más cercano. Cuando ambos están al alcance, el texto puede anunciar
   cargar una máquina y la acción real recoger chatarra. Conviene compartir la
   selección de objetivo entre HUD e interacción. Hallazgo por lectura de código,
   pendiente de reproducción en Play.
3. Esta carpeta no es un repositorio Git, aunque contiene `.gitignore`.
   Actualmente no hay historial local de cambios gestionado por Git.

Los visuales de cinta, triturado y placa siguen siendo provisionales según el
checkpoint anterior. Curvas, divisores y nuevas zonas siguen pendientes.
Esta reparación no cambió mapas, modelos, recetas ni partidas guardadas.
