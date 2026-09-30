# El escenario responde a la producción

La iteración continúa en `/Game/FactoryCtyco/Maps/L_FactoryDemo`, que vuelve a ser el
mapa de inicio del proyecto. `ABRIR_DEMO.cmd` abre la fábrica original; el
experimento GROW se conserva por separado.

## Hitos y espacio jugable

1. Cinco placas producidas materializan el taller.
2. Diez placas entregadas por cinta materializan la estación de carga.
3. Veinte entregas habilitan 36 celdas en el anexo y tres celdas de acceso para
   unir ambos patios mediante cintas.

Cada hito se revela durante dos segundos y se completa antes del siguiente.
Un barrido luminoso recorre su huella durante la aparición; los bordes cambian
de ámbar a turquesa. El HUD muestra requisitos, entregas, almacenamiento y
tiempo restante. Los hitos no consumen ni crean recursos y no retroceden al
retirar placas. El objetivo original sigue exigiendo 20 placas almacenadas y
20 entregas por cinta.

El anexo está fuera del portón frontal, con piso a la misma altura y barandas.
Se puede recorrer desde el inicio. La restricción previa al tercer hito es de
construcción. El taller y la estación son mejoras de escenario; todavía no
existe una batería ni una mecánica de reparación.

## Fuentes y guardado

Los dos nuevos modelos se crearon con Blender MCP y se importaron con Unreal
MCP. Sus fuentes están en `SourceAssets/Factory/SiteProgress`, incluyendo FBX,
`.blend`, vista previa y manifiesto. Las superficies reutilizan los materiales
de la fábrica. `FactorySiteLandmark` controla las apariciones y evita activar
la colisión del taller alrededor de un robot que esté ocupando su huella.

F5/F9 conserva el slot manual existente `FactoryCtycoDemo_v1`. El formato
interno pasa a versión2, incluyendo hito y tiempo restante. La carga de
versión1 reproduce los hitos ganados a partir de sus contadores. Los datos se
validan antes de reemplazar el estado actual.

`Scripts/build_factory_site.py` añade exclusivamente el anexo y conserva las
cuatro máquinas y siete montones iniciales. Guarda una copia previa del mapa
bajo `Saved/VisualPolishWork`; `Docs/factory_site_build.json` señala esa ruta.

## Evidencia

Veinte grupos aprobados en 138,8 segundos combinados. La producción completa
y el transporte se verificaron con ciclos nativos. Una segunda sesión corta
completó los casos de persistencia después de corregir el acceso del harness
a los datos protegidos del SaveGame; `prior_runs` conserva ese antecedente.
Las revelaciones completas observadas duraron dos segundos. Se comprobó el
suelo en 198 puntos y el robot recorrió el acceso sin salir del piso.

- `Docs/factory_site_asset_import.json`: importación, medidas y colisiones.
- `Docs/factory_site_playtest.json`: pruebas jugables y de persistencia.
- `Docs/factory_site_completed.png`: vista general del anexo desbloqueado.
- `Scripts/playtest_factory_site.py`: prueba con ciclos nativos y slots aislados.

La captura general utiliza una cámara temporal de verificación y una partida
de prueba. La cámara del jugador y su guardado no se modifican.

El segundo escenario continúa como una propuesta independiente: el prompt
actualizado para generar únicamente su base arquitectónica está en
`Docs/PROMPT_INVERNADERO.md`. Ese mapa y su conexión todavía no se implementaron.
