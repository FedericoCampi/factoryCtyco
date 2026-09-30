# Materiales del juego

Modelos de fábrica importados el 14 de septiembre de 2026:
ver `Docs/FACTORY_ASSETS.md`, `Docs/factory_import.json` y `Docs/DEMO_FABRICA.md`.
La trituradora, fundición, depósito general y chatarra ya se usan en la demo.
Los archivos de nombres ambiguos se importaron con identificadores neutros.

Carpeta de entrada: `C:\Users\Usuario\Desktop\3D assets`.

Para la escena de la arena, descargar **Escena editable y colisiones · ZIP**.
Se importó `scenes/sceneRobot.zip` en `/Game/FactoryCtyco/Environments/SceneRobot`
y se colocó en `/Game/FactoryCtyco/Maps/L_Recoleccion` a escala real, sin escalado adicional.
Sus 82 colisiones UCX se conservaron. PlayerStart se obtuvo de `build.json`
mediante los sockets de calibración del FBX; el suelo está a Z=0 cm.

El exportador actual incluye:
- `scene_unreal.fbx`: visual combinado y colisiones UCX para Unreal 5.6.
- `scene.blend`: escena editable por piezas en Blender.
- `scene.glb`: representación visual y `collision.glb`: colisiones auxiliares.
- `build.json`, `unreal_review.json` y `LEEME.txt`: escala, inicio y comprobaciones.

Al integrar la escena, verificar materiales, escala, colisiones y PlayerStart,
y probar el recorrido usando el personaje en Play. Conservar los archivos fuente.
El FBX combina el visual; para modificar piezas individuales se usa el archivo Blender.

Se importó `GLBs/robot1.glb` mediante una copia FBX que conserva geometría y textura.
El original tiene 697.531 triángulos y no incluía esqueleto ni animaciones.
La versión de juego tiene 181.353 triángulos, un rig de 22 huesos y ciclos
de reposo y caminata. `BP_Robot1` mide 1,80 m y usa una cámara isométrica fija.
La cápsula de movimiento mide 90 cm de semialtura y 35 cm de radio.
El rig editable y los FBX están en `SourceAssets/Robot1/Rigged`.

Organización de contenido propio: `Content/FactoryCtyco/Maps`, `Environments`,
`Characters`, `Materials`, `Textures`, `Audio` y `Blueprints`.
El contenido de la plantilla conserva sus rutas para mantener sus referencias.
