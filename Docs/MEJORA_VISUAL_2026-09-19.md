# Primera iteración visual de la fábrica

Se mantiene la dirección industrial del patio, con metal oscuro, naranja y
turquesa. El trabajo busca que se entienda la actividad de las máquinas desde
la cámara isométrica y que el HUD deje más espacio para ver la línea.

**Primera iteración integrada y verificada en Play.** Pasaron ocho grupos de
pruebas visuales y nueve de aceptación funcional. Queda la revisión estética
del usuario para decidir la siguiente iteración.

Cambios de esta iteración:

- Cintas con tablillas móviles, guías laterales y flechas físicas. La carga se
  interpola entre pasos de simulación para desplazarse con suavidad.
- Trituradora con rueda de radios animados, arranque/parada gradual y una
  vibración pequeña mientras procesa.
- Fundición con ranuras incandescentes, variación del brillo y una luz cálida
  local sin sombras. Trituradora y fundición emiten pequeñas chispas al trabajar.
- Balizas que distinguen reposo, actividad y bloqueo. Las máquinas incorporan
  un indicador segmentado de progreso; los depósitos muestran su ocupación.
- Materiales de las piezas provisionales revisados e iluminación del patio
  más cálida, con relleno frío. Las posiciones sugeridas de cinta usan un
  contorno turquesa que permite ver el piso original.
- HUD con paneles más contenidos, cifras alineadas, barras de capacidad y
  producción, y un objetivo más visible. Las etiquetas sobre máquinas aparecen
  al enfocarlas o al construir. El aviso de E coincide con la prioridad real
  entre recoger chatarra cercana y cargar una máquina; F/X siguen disponibles.

`UFactoryPresentationComponent` es una capa visual separada: consulta el estado
de `AFactoryBuilding` y crea sus detalles al iniciar **Play**, también para las
máquinas construidas o recuperadas desde una partida. Las piezas decorativas no
tienen colisión ni simulan física. Las recetas, costos, capacidades y formato de
guardado conservan su comportamiento. El material editable de estos detalles
se asigna mediante `PresentationMaterial` en las definiciones de edificio.

Se modelaron mediante el MCP de Blender una caja biselada, un cilindro mecanizado
y una estructura de cinta de 200 × 140 × 30 cm, con acero, grafito y piezas naranja.
Se importaron por el MCP de Unreal y quedaron referenciados por las definiciones
de edificio (`DetailBoxMesh`, `DetailCylinderMesh`, y la malla de `DB_Belt`).
La fuente editable es `SourceAssets/Factory/VisualPolish/FactoryDetails.blend`.
Todavía no se añadieron sonido industrial ni vapor; los mecanismos de las
máquinas son elementos añadidos, no un despiece de sus mallas originales.

Evidencia y recuperación:

- Materiales y mapa: [factory_visual_polish_build.json](factory_visual_polish_build.json).
- [Prueba visual](factory_visual_playtest.json): ocho grupos aprobados con las
  mallas nuevas, incluyendo reposo/actividad/bloqueo, ausencia de colisiones,
  animación sin alterar simulación, construcción, conservación y carga de partida.
- [Línea activa](factory_visual_active.png), [máquinas trabajando](factory_visual_processing.png)
  y [cinta en Blender](factory_belt_blender.png).
- [Importación de mallas](factory_detail_import.json): dimensiones, materiales
  y referencias verificadas. [Conexión local de Blender](BLENDER_MCP_LOCAL.md).
- [Aceptación funcional repetida con esta versión](factory_demo_playtest.json):
  nueve grupos aprobados en 117,1 segundos, 20 placas almacenadas y entregadas,
  conservación de 210 unidades equivalentes y guardado/carga en circulación.
  El informe y las capturas anteriores están respaldados bajo
  `Saved/VisualPolishWork/Regression-before-20260919-200408`.
- Respaldos de fuentes, binarios y assets: `Saved/VisualPolishWork`. Los paquetes
  de assets respaldados incluyen un `manifest.json`; el HUD original está en
  `FactoryDemoHUD.cpp.before` y las fuentes base en `source-before`.

La revisión visual del agente comprobó la línea completa y los detalles de las
máquinas desde la cámara del juego. El usuario todavía no ha evaluado esta pasada.
El mapa sigue empezando con los tres espacios vacíos para construir las cintas;
las capturas con una línea alimentada provienen de la sesión de prueba.

Para abrir y jugar, usar `ABRIR_DEMO.cmd`. El flujo anterior `-Mode Build`
regenera la demo base; si se utiliza, reaplicar `polish_factory_visuals.py` e
`import_factory_details.py`. `factory_demo_bindings.json` conserva las entradas
de ese generador anterior; las referencias visuales actuales están en `DB_*`.
