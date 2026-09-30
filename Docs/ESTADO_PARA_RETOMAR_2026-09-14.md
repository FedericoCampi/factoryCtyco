# Estado para retomar

**Documento histórico.** Para continuar, leer primero el
[checkpoint del 19 de septiembre](ESTADO_PARA_RETOMAR_2026-09-19.md), que
actualiza el estado, las verificaciones y la dirección del proyecto.

## Cierre de jornada — 14 de septiembre de 2026

El usuario pidió actualizar el estado y continuar mañana. El desarrollo queda
en pausa con la demo 0.6.0 implementada y verificada. Todavía no recibimos
comentarios del usuario sobre su prueba: no dar por aprobada la jugabilidad.
Esta sección y «Estado actual» prevalecen sobre los antecedentes de abajo.

Al cerrar esta jornada se comprobó que no había un proceso `UnrealEditor`
abierto. La demo se había abierto correctamente en `L_FactoryDemo` al entregarla.
No quedan compilaciones ni pruebas del agente en ejecución.

### Retomar mañana

1. Partir de `C:\Users\Usuario\Desktop\unreal Projects\FactoryCtyco`.
   Abrir `ABRIR_DEMO.cmd` o `FactoryCtyco.uproject`; el mapa inicial ya es
   `L_FactoryDemo`. Pulsar Play. No regenerar ni reimportar la demo desde cero.
2. Continuar con las observaciones del usuario al jugar. El alcance acordado
   sigue siendo una demo de reciclaje con cintas rectas básicas; las curvas
   todavía no fueron entregadas ni implementadas.
3. Resolver la identificación pendiente de los GLB antes de sustituir los
   visuales provisionales. El usuario corrigió: «el 9 es la placa metálica»;
   falta asociar ese número al nombre exacto de archivo, porque en el listado
   inspeccionado figuraba `robot1.glb` en esa posición. No reinterpretar el
   robot como placa. Mantener las asignaciones funcionales aclaradas por el
   usuario y contrastarlas con las vistas de `Docs/factory_asset_review`.
4. Reemplazar los visuales confirmados mediante las definiciones de la fábrica;
   el registro actual está en `Docs/factory_demo_bindings.json`. Cinta,
   triturado transportado y placa usan por ahora `BeltBasic`, `FragmentsBasic`
   y `PlateBasic`. Trituradora, fundición, depósito y chatarra ya usan modelos
   entregados, optimizados e importados con materiales.

### Guardado y verificación al pausar

- Los archivos de desarrollo y el mapa están guardados en disco. Este
  checkpoint documenta el proyecto; no crea una partida del jugador.
- Solo se encontró `Saved/SaveGames/FactoryCtycoDemo_AcceptanceOnly.sav`,
  generado por las pruebas. No se encontró aún `FactoryCtycoDemo_v1.sav`.
  En el juego, F5 crea ese guardado del usuario y F9 lo carga; no hay autoguardado.
- Se volvió a leer `Docs/factory_demo_playtest.json`: `passed: true`, nueve
  grupos aprobados, 20 placas almacenadas y 20 entregadas, masa equivalente
  conservada en 210 unidades. No hace falta repetir la aceptación completa
  sin cambios o un problema nuevo.
- Punto de entrada del código: `Plugins/FactoryCtycoRuntime/Source/FactoryCtycoRuntime/`;
  `Public/FactoryDemo.h`, `Private/FactoryDemo.cpp` y
  `Private/FactoryDemoHUD.cpp`. `Private/FactoryGathering.cpp` integra la
  interacción E con las máquinas. Guía de juego: `Docs/DEMO_FABRICA.md`.
- `Scripts/run_factory_editor.ps1 -Mode Ready` abre la demo;
  `-Mode Test` ejecuta la aceptación. No ejecutar `-Mode Build` para simplemente
  retomar: vuelve a importar y construir el contenido generado.
- La solicitud anterior del botón «Reintentar» en la web de generación 3D
  no se implementó en esta etapa; el trabajo pasó a los assets y a la demo.

## Estado actual: demo 0.6.0 lista para Play

El usuario pidió implementar una demo con cintas rectas. Se creó
`/Game/FactoryCtyco/Maps/L_FactoryDemo`, configurado como mapa inicial.
`L_Recoleccion` y su personaje anteriores se conservan. Guía: `Docs/DEMO_FABRICA.md`.

- Construcción B/1–4/R/clic; clic derecho o B cancela. Cuadrícula de 200 cm,
  validación de espacio, costo en chatarra y desmontaje con X sin pérdidas.
- Trituradora 2 chatarra → 2 triturado en 3 s; fundición 2 triturado → 1 placa
  en 4 s. E carga; F retira. Salidas llenas pausan sin consumir recursos.
- Depósitos de 100 unidades con filtro; G cambia el recurso si están vacíos.
- Cintas rectas de una unidad por tramo, conexiones por orientación y carga
  visible. Hay cuatro máquinas de ejemplo y tres espacios para agregar cintas.
- Objetivo: 20 placas almacenadas con entrega por cinta.
- F5 guarda y F9 carga inventarios, montones, edificios, filtros, orientación,
  posición del jugador y progreso de máquinas y cintas. No es guardado automático.
- Nueve grupos de aceptación pasaron en Play en 116,9 s: construcción, controles,
  recetas, pausa por salida llena, transporte, conservación de recursos,
  colocación por mouse, objetivo y guardado/carga real. Informe:
  `Docs/factory_demo_playtest.json`; captura `Docs/factory_demo_completed.png`.
- El plugin pasó compilación Editor, Development y Shipping; los binarios
  instalados corresponden a las fuentes actuales.

Se importaron los ocho GLB nuevos y se preservaron sus originales. Cuatro
funciones usan modelos entregados: trituradora, fundición, depósito y chatarra.
Para cinta, triturado y placa hay visuales básicos mientras se confirman
los nombres cruzados encontrados en las vistas. Consultas pendientes y
asignaciones: `Docs/FACTORY_ASSETS.md` y `Docs/factory_demo_bindings.json`.
No confundir `robot1.glb` con la placa a partir del número «9».

Respaldo previo: `C:\Users\Usuario\Desktop\unreal Projects\_factory_demo_work\backup_before_demo`.
Compilación y logs: carpeta vecina `CompiledPlugin` y archivos `build.log`,
`test.log`. El test guarda en `FactoryCtycoDemo_AcceptanceOnly`, separado del
slot de usuario `FactoryCtycoDemo_v1`.

Los apartados siguientes son antecedentes de la misma jornada.

## Actualización: modelos de fábrica recibidos el 14 de septiembre

Se retomó la revisión de assets. El usuario entregó ocho modelos nuevos en
`C:\Users\Usuario\Desktop\3D assets\GLBs\robotAutomation` y aclaró sus usos.
La correspondencia está en `Docs/FACTORY_ASSETS.md`; esa identificación
prevalece sobre las solicitudes de modelos de las secciones anteriores.
Se abrieron y renderizaron los ocho GLB, sin modificar originales ni importar
todavía a Unreal. No quedan procesos de revisión ejecutándose.

`frag_metalicos.glb` es chatarra; `frag_triturado.glb` es triturado;
`frag_triturado_almacenamiento.glb` representa triturado almacenado
temporalmente; `deposito_triturado.glb` es su depósito. La curva de cinta
sigue pendiente y no se recibió una placa metálica identificada.

## Checkpoint de desarrollo previo a recibir los modelos

Pausa solicitada por el usuario el 14 de septiembre de 2026.
Continuar cuando vuelva a pedirlo; no hay tareas pendientes ejecutándose.

## Proyecto actual

- Proyecto: `C:\Users\Usuario\Desktop\unreal Projects\FactoryCtyco\FactoryCtyco.uproject`.
- Unreal Engine 5.6.1, Windows; versión del proyecto 0.5.0.
- Mapa de inicio: `/Game/FactoryCtyco/Maps/L_Recoleccion`.
- La carpeta anterior es la copia de trabajo principal; las carpetas en
  `image-to-3d\storage` son copias de preparación y respaldos.

## Funciona y está guardado

- Arena industrial importada, con materiales, iluminación y colisiones.
- Robot1 humanoide, con rig editable, reposo y caminata animada.
- WASD mueve; mantener cualquiera de los Shift permite caminar rápido.
  Velocidades: 190 y 300 cm/s. Salto desactivado.
- Cámara isométrica: rueda para zoom, botón central y arrastre para desplazar,
  Inicio/Home para centrar y restaurar el zoom.
- E recoge el montón cercano; I abre y cierra el inventario.
- Siete montones provisionales de 30 unidades de chatarra; capacidad total 200.
- Alcance de recolección de 2 metros, bloqueado por obstáculos.
- Los montones agotados se ocultan. Si no cabe todo, el resto queda en el suelo.
- Interfaz con contador, capacidad, panel de inventario, mensajes y objetivo
  inicial de recoger 30 unidades de chatarra.

Las pruebas en Play pasaron: cantidades, agotamiento, distancia, obstáculos,
recogida parcial, inventario lleno, movimiento con el inventario abierto y cámara.
Evidencia: `Docs/gathering_build.json`, `Docs/gathering_playtest.json` y
`Docs/gathering_inventory.png`.

## Límites actuales

El inventario y el estado de los montones solo duran la sesión. Al comenzar
otra partida se reinician. Este checkpoint guarda el estado del desarrollo,
no agrega todavía un sistema de guardado de partidas.

Todavía no existen construcción, máquinas funcionales, cintas, procesamiento,
desbloqueo de zonas, enemigos ni combate. La chatarra visible usa piezas provisionales.

## Próximo paso acordado

Construir las primeras máquinas sobre una cuadrícula: catálogo pequeño,
vista previa de colocación, giro, validación de espacio y consumo de chatarra.
Controles propuestos: B abrir construcción, R girar, clic confirmar y Esc cancelar.
Empezar con una trituradora provisional si el modelo definitivo no está listo.

Después: trituradora, fundición y depósito cargados manualmente; luego cintas
para automatizar la cadena. Primera meta de producción propuesta: 20 placas
en el depósito final, sin transportar materiales intermedios a mano.
Defensa y enemigos quedan para una etapa posterior.

## Qué puede aportar el usuario

Modelos GLB con color, un archivo por objeto, en
`C:\Users\Usuario\Desktop\3D assets\GLBs`.
La trituradora es la más útil para el siguiente sistema. También hacen falta
un montón de chatarra definitivo y, después, fundición y depósito.
Se puede continuar con modelos provisionales sin esperar los definitivos.

## Referencias para continuar

- `Docs/PLAN_DEL_JUEGO.md`: dirección, etapas y propuestas del prototipo.
- `Docs/ASSETS_PARA_FABRICA.md`: indicaciones para los próximos modelos.
- `Docs/RECOLECCION_E_INVENTARIO.md`: funcionamiento y contenido editable.
- `Plugins/FactoryCtycoRuntime/Source/FactoryCtycoRuntime`: cámara, locomoción, inventario,
  recolección y HUD nativos. Se incluyen los binarios compilados.
- `Scripts/add_gathering.py`: integración de la última etapa.
- `Scripts/playtest_gathering.py`: prueba funcional actual.
- Última preparación y respaldo:
  `C:\Users\Usuario\Desktop\FullStack\image-to-3d\storage\arena-gathering-20260914`.

Al retomar, partir de los archivos actuales del proyecto principal y revisar
los modelos nuevos que haya dejado el usuario. Guardar y cerrar ese proyecto
en el editor antes de reemplazar binarios que estén cargados.
