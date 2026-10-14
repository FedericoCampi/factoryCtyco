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

Desde el 02/10 el horno **funde cuarzo**: la línea de cintas en altura lo lleva hasta la boca, E lo enciende y E
abre la colada; el silicio corre por la canaleta abierta (tubo + codo) hasta `Container_Producto`, se enfría y queda
un lingote que se retira con E. Ver «Proceso de fundición» en [HORNO_Y_LAB.md](Docs/HORNO_Y_LAB.md).

Desde el 03/10: **Espacio salta**; dos **pasarelas caminables** (`Pasarela_Recta`, `Pasarela_L`) junto a la plataforma
con escalera, para acomodar; la primera curva del cuarzo ya conecta.
Ver [PASARELAS.md](Docs/PASARELAS.md). La pasarela en L se arma a medida: sus cuatro barandas y las puntas se
arrastran en el viewport. Detrás del muro norte del estacionamiento están los **muelles de carga** nuevos
(`Muelles_Carga`), unidos al despacho sin paredes. Los camiones ya no pasan por el despacho (sin calle ni garita):
cruzan el patio de los muelles y entran marcha atrás a sus tres cajones. Las pasarelas rectas también se arman a medida.
Ver [MUELLES.md](Docs/MUELLES.md).

Desde el 04/10 hay **cielo de día** alrededor de todas las escenas (carpeta `Cielo`): atmósfera con nubes, bruma desde
los 50 m y un piso de 4 km hasta el horizonte, así detrás de los muros ya no se ve negro. `SkyFill` toma la luz del cielo.
Lo arma `Scripts/apply_cielo.py` (con el editor abierto) → `Docs/cielo.json`, que guarda la luz de ambiente anterior.

También desde el 04/10, **solo se ve la escena donde está el personaje** (primera persona e isométrica): Fábrica,
Despacho (con los muelles), Laboratorio y Empleados son zonas (`Escena_*`, carpeta `Escenas`, `AFactorySceneZone`).
Las demás se ocultan solo para la cámara del jugador y siguen funcionando; a 3 m del borde de otra escena se ven las
dos. El cielo, las luces, los pisos de afuera y el horizonte se ven siempre; los camiones y personajes, según dónde
estén. Etiquetas: `SiempreVisible` (siempre se ve) y `Escena:<nombre>` (lo pone en esa escena). Zonas:
`Scripts/apply_escenas.py` → `Docs/escenas.json` (qué actor quedó en cada escena). Prueba: `Scripts/playtest_escenas.py`
→ `Docs/escenas_play.json` (6/6, con los techos).

Desde el 05/10 la **Fábrica, el Laboratorio y la Recepción tienen techo** (el estacionamiento y el muelle de camiones
no): losa a 8 m, 5 m y 3,7 m sobre el piso, paredes levantadas hasta la losa (del color de cada edificio), dinteles
sobre las puertas y los ascensores, y lámparas en grilla de 7 m (placa que brilla, foco hacia abajo y una luz de relleno
sin sombra). Todo va en la carpeta `Techos/<edificio>`, sin colisión, con la etiqueta `Techo`: **solo se ve en primera
persona**; en isométrica se oculta para la cámara del jugador (las luces quedan, así que adentro se ve igual).
El 07/10 las lámparas de la fábrica se bajaron al 50 % (`light` en `apply_techos.py`; sin rehacer los techos:
`Scripts/apply_luz_fabrica.py` → `Docs/luz_fabrica.json`, con los valores de antes).
Desde el 07/10 el techo de la fábrica (losa y lámparas) **no se ve en el editor, y en Play se ve siempre** (también en isométrica, sin la etiqueta `Techo`; el
sol ya no entra): está en la capa
«Techo Fabrica», oculta (Window → Layers, el ojo, para verlo). `Scripts/apply_techo_solo_play.py`; correrlo de nuevo
después de `apply_techos.py`. Unreal no guarda si una capa está oculta: `Content/Python/init_unreal.py` la vuelve a
ocultar al abrir el editor y cada vez que se abre un mapa.
También el 07/10: **flejadora, escáner de rayos X y dos pasarelas** sueltos en el despacho para acomodar (ver «Equipos
del despacho» en [MUELLES.md](Docs/MUELLES.md)).
Más del 07/10: la **oficina de administración** es un piso nuevo (ascensor «ADMINISTRACIÓN»): [OFICINA.md](Docs/OFICINA.md).
En la fábrica: sin astillas en el aire, vano norte cerrado (sin franjas amarillas), pared arriba del ascensor y el
**Extractor de Silicio** de vuelta: [ARENA_CAMBIOS.md](Docs/ARENA_CAMBIOS.md). Plataforma industrial a medida y barandas
sueltas: [PASARELAS.md](Docs/PASARELAS.md).
`Scripts/apply_techos.py` (mide las paredes con rayos y rehace todo; se puede correr de nuevo) → `Docs/techos.json`.

Desde el 08/10: **tolvas de cuarzo y arena** en el patio de los muelles, con una **rampa y plataforma** a la que sube marcha
atrás un **camión volcador** que levanta la caja y descarga cuarzo en la tolva; los camiones llevan **camionero** y la
garita choca. Ver «Rampa de las tolvas» y «Camionero y garita» en [MUELLES.md](Docs/MUELLES.md).

Más del 04/10: **música y sonidos por separado** (dos botones junto al dinero: nota y parlante; teclas **M** música y
**N** sonidos; el panel I silencia todo): clases `SC_Musica` y `SC_Sonidos` (`Scripts/apply_sonidos.py`,
`playtest_sonidos.py`). El **techo del ascensor** se va solo en vista isométrica; en primera persona queda
(`playtest_ascensor_techo.py`). La **puerta de recepción** abre hacia el lado contrario de donde viene el personaje
(`playtest_puerta_recepcion.py`). El **horno** tiene tapa y lote de 3: ver [HORNO_Y_LAB.md](Docs/HORNO_Y_LAB.md).

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
caminar rápido. Espacio salta, unos 90 cm (desde el 03/10; `bCanJump` y `JumpSpeed` en `RobotLocomotion`).
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
