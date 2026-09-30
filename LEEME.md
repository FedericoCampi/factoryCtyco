# FactoryCtyco

Estado al cerrar la sesión y próximos pasos:
[checkpoint del 19 de septiembre](Docs/ESTADO_PARA_RETOMAR_2026-09-19.md).
Desarrollo pausado por pedido del usuario; seguimos cuando lo retome.

Iteración actual: **la fábrica original cambia con tus logros**.
La entrada principal es [`ABRIR_DEMO.cmd`](ABRIR_DEMO.cmd): abrí `L_FactoryDemo`
y pulsá **Play**. Conserva el robot controlable, la recolección, la construcción
y la línea de reciclaje.

Al producir **5 placas** aparece el taller; al entregar **10 por cinta** aparece
la estación de carga; al entregar **20 por cinta** se habilita un sector adicional
construible. Cada transformación tarda **dos segundos**. El taller y la estación
son elementos de escenario e iluminación; todavía no hay batería ni bonificaciones.
Los hitos y las transformaciones en curso se guardan con **F5** y se cargan con **F9**.

Guía: [DEMO_FABRICA.md](Docs/DEMO_FABRICA.md).
Verificado en Play con 20 grupos de comprobaciones: producción con tiempos
nativos, hitos, 36 celdas nuevas y tres de conexión, conservación de materiales
y guardado. [Detalles y evidencia](Docs/EVOLUCION_FABRICA_2026-09-19.md).
GROW queda como experimento separado, accesible con `ABRIR_GROW.cmd`.

Desde el 23 de septiembre, un **estacionamiento** decorativo se une a la fábrica
por su puerta oeste. Ver [ESTACIONAMIENTO.md](Docs/ESTACIONAMIENTO.md).
El personaje jugable de la demo ahora es **TecJunior** (1,70 m, riggeado y animado);
Robot1 se conserva. Ver [TECJUNIOR.md](Docs/TECJUNIOR.md).
Desde el 27 de septiembre hay una **máquina de despacho** decorativa (`Despacho_Machine`).
Ver [DESPACHO_MACHINE.md](Docs/DESPACHO_MACHINE.md). Hay dos, metidas en el muro oeste del estacionamiento;
cada cinta se prende con E en su botonera y se detiene al llenarse con 4 cajas: [CAJAS_DESPACHO.md](Docs/CAJAS_DESPACHO.md).
Desde el 28/09 un **camión** (modelo del usuario, ruedas que giran) cruza el estacionamiento en lugar del auto,
por una línea que se edita en el viewport (`Camion_Recorrido`);
las botoneras de las cintas son actores sueltos (`Botonera_CintaN`). Ver ESTACIONAMIENTO.md y CAJAS_DESPACHO.md.
Desde el 27/09 el HUD ya no muestra la demo de reciclaje (mochila, objetivo, avisos): `bShowRecyclingHUD`
de `AFactoryDemoHUD` la vuelve a mostrar. Pared de ladrillos suelta: [PARED_LADRILLO.md](Docs/PARED_LADRILLO.md).

Desde el 29/09 el juego arranca con una **intro** (sos el gerente de una fábrica que reabre tras la pandemia) y la
**misión 1 guiada** con una flecha grande; lo clickeable se **remarca** al pasar el mouse. Ver [INTRO_Y_GUIA.md](Docs/INTRO_Y_GUIA.md).
Arriba a la izquierda están el **dinero** (se empieza con $ 0, cada paquete paga $ 60 y contratar cuesta) y un botón
para **silenciar**. Ver [ECONOMIA.md](Docs/ECONOMIA.md).

Desde el 30/09 `Ascensor_Fabrica` está en el vano este, con su pozo ([ASCENSORES.md](Docs/ASCENSORES.md)), y las tres
cintas de la línea de la fábrica son actores fijos del nivel (`Cinta_Fabrica_1` a `3`, `Scripts/apply_factory_belts.py`)
en lugar de contornos para construir: se mueven, giran o duplican en el editor. Una cinta pasa material a la pieza
que está justo una celda (200 cm) adelante y mirando para el mismo lado.
También desde el 30/09 las cintas de la fábrica van sobre una **plataforma de 50 cm** (`SM_FactoryBeltPlatform`,
`Scripts/author_belt_platform.py` y `run_belt_platform_setup.py`). La altura es `BaseHeight` en `DB_Belt` y vale para
toda cinta de ese tipo, también las que se construyen jugando; la malla se estira a esa altura. El actor sigue en el
piso (cuadrícula y paso de material no cambian): sube lo que se ve. Probado en Play: `Docs/belt_platform_play.json`.
Respaldo de antes del cambio: `Saved/Respaldos/2026-09-30_cintas_plataforma`.

Desde el 30/09 hay un **horno de fundición** en la fábrica (`Horno_Fundicion`) y la escena del **laboratorio** al este
(`Lab1_Escena`), los dos para ubicar y todavía sin función: [HORNO_Y_LAB.md](Docs/HORNO_Y_LAB.md).

## Fábrica de reciclaje

Demo de reciclaje **0.6.0** para Unreal Engine **5.6.1**, con cámara isométrica,
robot animado, construcción, máquinas, cintas rectas y guardado manual.

Antecedentes históricos:
[checkpoint del 14 de septiembre](Docs/ESTADO_PARA_RETOMAR_2026-09-14.md).
El checkpoint del 19 registra el estado vigente.

Primera iteración estética integrada: cintas y máquinas animadas, señales de
actividad, materiales y HUD revisados, y piezas biseladas creadas en Blender.
Verificada con ocho grupos visuales y nueve funcionales en Play.
Ver [mejora visual del 19 de septiembre](Docs/MEJORA_VISUAL_2026-09-19.md) y
[conexión MCP local de Blender](Docs/BLENDER_MCP_LOCAL.md).

Abrir `ABRIR_DEMO.cmd` y pulsar **Play** en `L_FactoryDemo`.
Hay una línea de ejemplo vacía: recogé chatarra con E, pulsá B y 4 para colocar
las tres cintas en los contornos turquesa y cargá el depósito de entrada con E.
El objetivo exige 20 placas almacenadas y 20 entregadas por cinta.
Guía completa: `Docs/DEMO_FABRICA.md`.

Construcción: B abre, 1–4 seleccionan, R gira, clic coloca y clic derecho cancela.
E carga máquinas, F retira su salida, G cambia el recurso de un depósito vacío
y X desmonta devolviendo el costo pagado y el contenido. F5 guarda; F9 carga.
Controles: WASD para moverse en relación con la cámara y Shift mantenido para
caminar rápido. El salto está desactivado.
E recoge chatarra cercana; I abre y cierra el inventario.
La cámara sigue al personaje y conserva su inclinación isométrica.
Rueda para acercar/alejar; botón central y arrastrar para desplazar el encuadre;
clic derecho y arrastrar a izquierda/derecha para girar alrededor del personaje.
Inicio/Home restaura encuadre, zoom y orientación. Ver `Docs/CAMERA_CONTROLS.md`.

Incluye la arena `sceneRobot`, sus 13 materiales y 82 colisiones UCX,
y `robot1` de 1,80 m con un rig de 22 huesos, animaciones propias de reposo,
caminata y una pose aérea. La caminata se mezcla con reposo según la velocidad.
La iluminación usa sol, cielo de día y luz de relleno suave.
Los controles proceden de la plantilla Third Person; su nivel original se conserva.
La carpeta de materiales fuente es `C:\Users\Usuario\Desktop\3D assets`.
Ver `Docs/ASSETS.md` para el formato de descarga y la organización del contenido.

Los plugins Python y Editor Scripting Utilities están habilitados para facilitar
la importación y las verificaciones dentro del editor.
`Plugins/FactoryCtycoRuntime` contiene el componente de locomoción, sus fuentes y
los binarios compilados para Unreal 5.6.1 en Windows.

Dirección inicial de la fábrica: `Docs/PLAN_DEL_JUEGO.md`.
Primera meta: una fábrica de reciclaje sin combate que automatice placas metálicas.
La demo incluye recolección, mochila de 200 unidades, construcción sobre
cuadrícula, trituradora, fundición, depósitos con filtro y cintas rectas.
F5/F9 guarda y recupera inventarios, construcciones y procesamiento en curso.
Al iniciar Play se empieza de nuevo hasta cargar explícitamente con F9.
Pendientes: identificar los visuales ambiguos, curvas y divisores.
Ver `Docs/RECOLECCION_E_INVENTARIO.md` y `Docs/ASSETS_PARA_FABRICA.md`.

Contenido principal:
- `/Game/FactoryCtyco/Maps/L_FactoryDemo`: fábrica original e iteración actual de hitos.
- `/Game/FactoryCtyco/Factory`: modelos preparados, definiciones editables y personaje de la demo.
- `/Game/FactoryCtyco/Maps/L_GrowRobots`: experimento separado de decisiones y evolución.
- `/Game/FactoryCtyco/Grow/DA_RobotSpecies`: apariencia y animaciones de la colonia GROW.
- `/Game/FactoryCtyco/Maps/L_Recoleccion`: nivel anterior de recolección, conservado.
- `/Game/FactoryCtyco/Blueprints/BP_Robot1`: personaje controlable con cámara isométrica.
- `/Game/FactoryCtyco/Blueprints/BP_FactoryGameMode`: modo de juego.
- `/Game/FactoryCtyco/Environments/SceneRobot`: arena, materiales y texturas.
- `/Game/FactoryCtyco/Characters/Robot1/Rigged`: malla esquelética, esqueleto,
  animaciones `A_Robot1_Idle`, `A_Robot1_Walk`, `A_Robot1_Airborne`
  y mezclador `BS_Robot1_Locomotion`.

Los originales se conservan en `SourceAssets`. El rig editable está en
`SourceAssets/Robot1/Rigged/Robot1_Rig.blend` y sus exportaciones FBX al lado.
Los informes de preparación de la fábrica son `Docs/factory_import.json`,
`Docs/factory_demo_build.json` y `Docs/factory_demo_playtest.json`.
La aceptación anterior de la línea en Play pasó nueve grupos, incluida la entrega
automática de 20 placas y el guardado/carga con materiales en circulación.
`factory_demo_completed.png` muestra el objetivo completado.
Los informes anteriores documentan etapas previas.

## Experimento GROW conservado

[`ABRIR_GROW.cmd`](ABRIR_GROW.cmd) abre `L_GrowRobots`, un diorama de seis
decisiones cuyo orden cambia el oficio de los robots, sus niveles y el mapa.
Los sistemas se conectan y las mejoras se resuelven en cadena, con dos segundos
por nivel. **1–6** o clic elige; **Retroceso** deshace y **R** reinicia. No guarda
la sesión.

Ese experimento pasó 17 grupos de comprobaciones en Unreal. Sus resultados no
validan los nuevos hitos de la fábrica original.
Guía: [GROW_ROBOTS.md](Docs/GROW_ROBOTS.md).
Capturas: [reacción en curso](Docs/grow_reaction.png) y
[red de la colonia](Docs/grow_connected_courier.png).
