# Estacionamiento unido a la fábrica — 23 de septiembre de 2026

Escena del usuario `3D assets/GLBs/sceneStacionamiento.glb`, colocada en
`L_FactoryDemo` al **oeste** de la fábrica. La abertura lateral oeste de la fábrica
(3,4 m) se une con la abertura este del estacionamiento (3,3 m). Por ahora es
**solo decorado**: se recorre, pero no se puede construir ahí ni tiene función de juego.
El portón frontal sigue reservado para la ampliación del tercer hito.

- Actor: `Parking_Estacionamiento`, carpeta `Environment`. Desde el 26/09 está separado de la fábrica, en (-3803, -410, 0); ver [ASCENSORES.md](ASCENSORES.md).
- Malla: `/Game/FactoryCtyco/Environments/Parking/SM_Parking`: 1422 piezas unidas,
  71 196 triángulos, 12 materiales y 253 colisiones UCX.
- Umbral de acero enrasado sobre la junta de la puerta: cubre la ranura de unos 17 cm
  que dejaban los bordes biselados de los dos pisos.
- Colisiones: los muros y columnas se rasterizaron a la altura del robot y se unieron
  en cajas; el piso y la terraza tienen cajas propias y la rampa usa su envolvente convexa.

26/09: se quitó el pilar de la arcada más cercano a la puerta sur (`Arcade free pier -4`) y la
viga que lo unía a la pared (lista en `author_parking_scene.py`); las paredes quedan como el
original. Se corrigió además la altura de las cajas de colisión (la terraza quedaba a 1,83 m).
27/09: se abrió el vano 3 del muro oeste (y 4–8 m en el GLB) detrás de `Despacho_Machine`: sin
ladrillo bajo, ventana, jambas ni alféizar (83 piezas, `WEST_OPENING` en `author_parking_scene.py`);
quedan los pilares y el ladrillo de arriba como dintel. Hueco de 3,1 × 2,5 m; la máquina lo tapa
a lo ancho y parece venir de afuera. Respaldo previo en `SourceAssets/Parking/respaldo_2026-09-27`.
27/09: los dos pilares libres de la arcada que quedaban (y 0 y 4 en el GLB), con sus vigas, ya no son
parte de SM_Parking: son los actores `Columna_Arcada_1` y `Columna_Arcada_2` (carpeta Environment,
enganchados al estacionamiento), para moverlos a mano. Malla `SM_ParkingColumna` (una sola para las dos,
origen al centro del pie, viga de 3,7 m hacia -X, colisión solo en el fuste, materiales de SM_Parking).
Se colocaron 1 m más cerca del carril del auto que en el original, a 4 m entre sí.
Regenerar: `blender -b --factory-startup -P Scripts/author_parking_columns.py` y, en el editor,
`Scripts/apply_parking_columns.py` después de `reimport_parking_mesh.py` (conserva la posición de los
actores que ya existen; informe `Docs/parking_columns.json`).
27/09: para `Despacho_Machine2` (metida en el muro oeste, y −1,96 a 1,80 en el GLB): las ventanas de los
vanos 1 y 2 (y −4 a 4) pasan a ladrillo (copias recortadas del ladrillo bajo; se notan juntas horizontales)
y se abre el muro detrás de la máquina, del piso al ladrillo superior (2,48 m), con marco de acero
(`WINDOW_BAYS`, `OPENING2`, `cut_opening` en `author_parking_scene.py`). El ancho sale de
`SourceAssets/Parking/wall_openings.json`: si se mueve la máquina, correr en el editor
`Scripts/export_wall_openings.py`, después `author_parking_scene.py` y `reimport_parking_mesh.py`.
Siguen quitadas del nivel las máquinas y guías de cinta de la demo que estaban adentro.
Reimportar sólo la malla: `Scripts/reimport_parking_mesh.py` (borra y vuelve a crear el asset:
reimportar encima lo dejaba al 1%). Respaldo del original en `SourceAssets/Parking/respaldo_2026-09-26`.

**Desde el 28/09 el auto se reemplazó por el camión del usuario** (ver más abajo). Historia del auto:
Auto en loop (`Scripts/author_vehicle_loop.py` + `Scripts/apply_parking_loop.py`): `Auto_Loop`
(`/Game/FactoryCtyco/Environments/AutoBasico/SK_AutoBasico`, enganchado al estacionamiento) entra desde
afuera por las líneas amarillas de la puerta sur, cruza por donde estaba el pilar y sale por las
líneas amarillas de la puerta este (la vieja unión con la fábrica): 35 m en 10 s. Es un
marcador: para un camión, cambiar `build_car()` (ruedas `Rueda_*`) y volver a correr ambos.

Fuentes en `SourceAssets/Parking`: GLB original, `Parking.blend`, `parking_unreal.fbx`
y `parking_build.json`.

Regenerar:
1. `blender -b --factory-startup -P Scripts/author_parking_scene.py`
2. En el editor, con `L_FactoryDemo` abierto: ejecutar `Scripts/import_parking_scene.py`
   (informe: `Docs/parking_import.json`).
3. Comprobar: `Scripts/verify_parking_link.py` (informe: `Docs/parking_link_check.json`).

Comprobaciones pasadas (barridos con la cápsula del robot, 35 × 90 cm): paso de la
fábrica al estacionamiento y vuelta, llegada al centro del estacionamiento, muros a
ambos lados de la puerta y muro exterior bloquean, y piso enrasado en la puerta (±1 cm).
No se probó todavía caminando en Play.

Nota: dentro de la fábrica, un depósito de la demo queda cerca de esta puerta; el
robot pasa por su lado norte.

Captura: [parking_union_editor.png](parking_union_editor.png).

## Camión en loop (28/09)

`Camion_Loop` (SkeletalMeshActor, carpeta Environment, enganchado a `Parking_Estacionamiento`)
reemplaza a `Auto_Loop`. Modelo del usuario `3D assets/GLBs/truck.glb`, llevado a **5,2 m** de largo
(2,1 m de ancho con espejos, 2,3 m de alto; a 6,5 m quedaba grande) y reducido de 699 000 a 154 000 caras.
Malla y animación en `/Game/FactoryCtyco/Environments/Camion` (`SK_Camion`, `SK_Camion_Anim`, 15 s en loop).

- **Ruedas que giran**: el GLB es una sola malla; `Scripts/author_truck_loop.py` recorta cada rueda
  (cilindro medido alrededor de cada eje) y la pone en su hueso (`Rueda_DI/DD/TI/TD`). Giran según la
  distancia que recorre cada eje. Las delanteras además doblan en las curvas (hasta 38°).
  La llanta del modelo es casi simétrica, así que se agregaron 6 tuercas oscuras por maza (`M_CamionTuerca`)
  para que el giro se note.
- **Recorrido (28/09, a pedido)**: derecho de oeste a este por y −5,5 (GLB). Entra por la **entrada
  nueva del muro oeste** y sale por la puerta este. Pasa por las dos con unos 20 cm de margen por lado;
  se revisó cuadro a cuadro contra `Parking.blend` y las columnas, sin choques de carrocería ni espejos.
- Tamaño: `LENGTH_M` al principio del script. Velocidad: `SPEED` (3 m/s).

Regenerar: `blender -b --factory-startup -P Scripts/author_truck_loop.py` y, en el editor,
`Scripts/apply_truck_loop.py` (borra `Auto_Loop`/`Camion_Loop` y lo vuelve a poner; no guarda el nivel;
informe `Docs/truck_loop.json`). Los assets del auto quedan en `/Game/FactoryCtyco/Environments/AutoBasico` sin uso.

## Entrada del camión en el muro oeste (28/09)

A pedido del usuario, en `author_parking_scene.py`:
- **Puerta sur cerrada**: el hueco se completó con una copia del tramo de murete vecino (`Perimeter 01`,
  corrido 3,5 m al oeste). Se quitaron sus franjas amarillas.
- **Vano 0 del muro oeste abierto** (`TRUCK_OPENING`, y −7,69 a −4,31 en el GLB, justo a la izquierda de la
  puerta sur vieja vista desde el camión que entraba). Va del piso al ladrillo superior (2,48 m), con marco de acero
  y un umbral en el espesor del muro. Una colisión invisible en el vano no deja salir al personaje.
- **Calzada** afuera (`DRIVEWAY`): 6 m a nivel y 4 m de rampa hasta el piso de afuera, que está 65 cm más
  abajo. Sin colisión: la usa solo el camión. Si subía directo desde el piso, la cabina tocaba el dintel.
- `Piso_Exterior_Oeste`: copia del piso de afuera, 100 m al oeste. `Piso_Exterior` terminaba en el muro oeste.

Aplicar (editor cerrado): `Scripts/run_truck_entrance_setup.py` (reimporta SM_Parking, el camión, el piso y las
botoneras, y guarda el nivel; informe `Docs/truck_entrance_setup.json`).
Respaldo previo: `SourceAssets/Parking/respaldo_2026-09-28_entrada`.

## Camino editable del camión (28/09)

El camión ya no usa una animación fija: es `Camion_Recorrido` (clase C++ `AFactoryVehiclePath`, carpeta
Environment, enganchado al estacionamiento). Tiene una línea (spline `Path`) que se edita en el viewport:
seleccionar el actor, hacer clic en un punto de la línea y moverlo. Alt+arrastrar un punto agrega otro;
clic derecho sobre un punto da más opciones (borrar, tipo de curva).

- **Dónde empieza**: el primer punto. El camión aparece con el eje trasero ahí y recorre la línea hasta
  que el eje trasero pasa el último punto; después vuelve a empezar. Si la spline se marca como
  *Closed Loop*, da vueltas sin cortar.
- **La altura de cada punto es la del piso** por donde pasa: adentro del estacionamiento 0; afuera,
  en el piso de abajo, −65 cm. La calzada del oeste está a 0 hasta 6 m afuera del muro.
- Los dos ejes van sobre la línea, así dobla como un vehículo. Las ruedas giran según lo que avanza
  y las delanteras doblan en las curvas (hasta `MaxSteer`).
- Detalles: `Speed` (cm/s, 300), `PauseBetweenTrips` (s entre vueltas), `EditorPreviewDistance`
  (en qué parte de la línea se ve el camión en el editor, para revisar un lugar), medidas de las ruedas.
- **No revisa choques**: si la línea pasa por una pared, el camión la atraviesa.

Crear (reemplaza `Camion_Loop`; si ya existe `Camion_Recorrido` no le toca la línea):
`Scripts/apply_vehicle_path.py`. Prueba en Play: `Scripts/playtest_vehicle_path.py`
(informe `Docs/vehicle_path_play.json`).
`author_truck_loop.py` sigue haciendo la malla `SK_Camion`; su animación ya no se usa.

## Cabina con barrera antes de la salida (28/09)

`Cabina_Barrera` (clase C++ `AFactoryGateBarrier`, carpeta Environment, enganchada al estacionamiento):
cabina de 1,6 × 1,6 m al norte del carril, 2,3 m antes de la puerta este, con la puerta hacia el
estacionamiento, y una barrera (poste amarillo y negro, brazo rojo y blanco de 3,1 m) que cruza el carril.
- Se mueve como un actor. El componente `Post` (con el brazo) también se puede mover o girar solo.
- Adentro de la cabina aparece «[E] LEVANTAR BARRERA»: E la levanta en 1,6 s; otra vez E la baja. El techo
  se oculta con el personaje adentro.
- El camión frena suave y espera ~70 cm antes de la barrera baja (`StopGap`, `Braking`, `Acceleration`
  en `Camion_Recorrido`). Con la barrera arriba pasa; cuando termina de pasar la barrera baja sola.
  Nunca baja sobre el camión. El camión detecta cualquier barrera cuyo brazo cruce su línea.
- Piezas: `Scripts/author_gate_booth.py` (Blender) → `/Game/FactoryCtyco/Environments/CabinaBarrera`;
  colocar: `Scripts/apply_gate_booth.py` (conserva el lugar si ya existe). Sonido: `S_Ascensor_Puerta`.
- Prueba en Play: `Scripts/playtest_gate_booth.py` (11 comprobaciones, pasó el 28/09; captura
  `Docs/gate_booth_play.png`).

## Carga de cajas en el camión (28/09)

- **Punto de carga**: el camión para con el centro de su puerta frente a `Cinta_Carga` (clase C++
  `AFactoryLoadingBelt`, carpeta Environment), 2,5 m antes de la barrera. Detecta solo cualquier cinta de
  carga cuya punta de entrega esté a menos de `DockReach` (250 cm) de su línea. Mover la cinta mueve el
  lugar donde para.
- **Puerta**: la pared izquierda de la caja (la que da al estacionamiento) se rebate hacia afuera hasta
  quedar horizontal, como plataforma de carga (bisagra abajo, `DoorOpenAngle` −90, `DoorSeconds` 1,3).
  El techo de la caja desaparece apenas se abre la tapa y vuelve cuando está cerrada del todo, así la
  cámara de arriba ve la carga.
  Abriendo hacia arriba la pared tapaba parte de las cajas.
- **Cargar**: con una caja en mano, en la punta amarilla de la cinta aparece «[E] CARGAR CAJA». E la
  apoya en la cinta, que la lleva hasta el camión; la caja salta adentro y queda acomodada en dos filas
  (primero la del fondo, de adelante hacia atrás). Si el camión no está o no tiene lugar, el cartel dice
  «ESPERANDO CAMIÓN» o «CAMIÓN LLENO» y la caja sigue en las manos.
- **Contador**: con la primera caja aparece «1/10» sobre el camión; lleno, «10/10 LLENO» en rojo. Ahí la
  puerta se cierra y el camión sigue hasta la barrera. Cada vuelta nueva llega vacío.
- Ajustes en `Camion_Recorrido` › Cargo: `CargoCapacity` (10), `CargoRows`, `HopSeconds`, etc.
  En `Cinta_Carga`: `Speed`, `BoxSpacing`, `InteractionRadius`.

Piezas: `Scripts/author_truck_loop.py` (puerta con hueso `Puerta`, techo con hueso `Techo`, interior de la
caja; el modelo es una cáscara hueca y el techo tiene dos capas) y `Scripts/author_loading_belt.py`
(`SM_CintaCarga`, rodillos con `M_DespachoRodillo`). Aplicar: `Scripts/apply_truck_loading.py`
(reimporta el camión sin tocar su línea; conserva el lugar de la cinta).
Prueba en Play: `Scripts/playtest_truck_loading.py` (pasó el 28/09; capturas `Docs/truck_loading_play.png`
con 7 cajas y `Docs/truck_loading_full.png` lleno).

## Dos camiones, cadena de cintas y cinta suelta (28/09)

- **Cintas encadenadas**: una cinta de carga le pasa sus cajas a la que empieza donde ella termina
  (a menos de `LinkReach`, 120 cm; o la que se elija en `NextBelt`). Hoy: `Cinta_Carga3` → `Cinta_Carga2`
  → `Cinta_Carga` → camión. Solo la última cinta de una cadena recibe camiones.
- **Apoyar en cualquier parte**: con una caja en mano, E junto a cualquier punto de cualquier cinta
  (a menos de `InteractionRadius`, 130 cm) apoya la caja ahí; el cartel aparece sobre ese punto.
  La cadena acepta cajas mientras el camión de su última cinta tenga la puerta abierta y lugar para
  todas las que van en camino.
- **Cintas estiradas**: se pueden escalar a lo largo (escala X); las cajas mantienen su tamaño y separación.
- **Segundo camión**: `Camion_Recorrido2` recorre la línea de `Camion_Recorrido` (`LeadPath`: editar solo
  la del primero), sale 8 s después (`StartDelay`) y en el editor se ve 9 m detrás (`EditorPreviewDistance` −900).
  Los camiones mantienen `FollowGap` (30 cm) con el de adelante y no empiezan una vuelta si hay otro en la salida.
- **Reparto**: cada camión va a la cinta libre más adelantada (`Cinta_Carga`). Si está ocupada, o si otro
  camión está parado donde él tendría que frenar, carga en la anterior (`Cinta_Carga4`). Cuando la de adelante
  se libera, cierra la puerta y se pasa, con la carga que ya tenía. Si ya está lleno, va directo a la barrera.
  Como las dos cintas están a 5,7 m, con un camión en cada una quedan unos 45 cm entre ellos.
- **Barrera**: sabe si hay uno o dos camiones debajo; no baja hasta que pasa el último que tiene debajo.
  Adentro de la cabina E maneja la barrera aunque se tenga una caja en la mano.
- Aplicar: `Scripts/apply_second_truck.py`. Prueba: `Scripts/playtest_two_trucks.py` (12 comprobaciones, pasó
  el 28/09). `playtest_truck_loading.py` y `playtest_gate_booth.py` suponen un solo camión y ya no aplican tal cual.

Techo (corregido el 28/09): se ocultaba siempre porque el código reescribía la transformación del hueso `Techo`
(escala), y eso lo perdía aunque la escala fuera 1. Ahora se oculta con `HideBoneByName` al abrirse la tapa y se
muestra con `UnHideBoneByName` al cerrarse. Prueba: `Scripts/playtest_truck_roof.py` (capturas
`Docs/truck_roof_closed.png` con techo y `Docs/truck_roof_open.png` sin techo).

## Reparto en cruces y carga sin camión (28/09)

- Una cinta puede tener varias salidas: todas las cintas que empiezan a menos de `LinkReach` de su final
  (hoy `Cinta_Carga3` → `Cinta_Carga2` y `Cinta_Carga4`). En el cruce las ramas se prueban en orden: primero
  la que lleva a la parada más adelantada en la línea del camión (la más cerca de la barrera; desde el cruce,
  doblar a la izquierda). La caja va a la primera rama con un camión esperando con lugar para ella (contando
  las que ya van en camino); si no hay ninguno, espera en la primera rama con lugar en su fila.
- Las cintas aceptan cajas aunque no haya camión o esté lleno: esperan al final y las carga el próximo camión
  que estacione ahí. Si no hay lugar justo donde se apoya, el cartel dice «SIN LUGAR AQUÍ».
- Los camiones ya no pueden pasarse de una parada (cinta, barrera o camión de adelante) aunque el juego vaya
  a pocos cuadros por segundo: cada paso se corta en el punto de parada. Antes, con cuadros lentos, podían
  pasar de largo la cinta.
- Prueba: `Scripts/playtest_belt_routing.py` (8 comprobaciones, pasó el 28/09, incluye M para silenciar). `playtest_two_trucks.py`
  suponía que todo lo de `Cinta_Carga3` iba al primer camión; con el cruce ya no aplica.

## Panel de información (tecla I, 28/09)

Base de la interfaz de información (se irá ampliando). I abre en el centro: bienvenida con el retrato de TecJunior (`/Game/FactoryCtyco/UI/T_RetratoTecJunior`, render de su
modelo: `Scripts/author_portrait.py` + `Scripts/apply_character_panel.py`) y la introducción: objetivo
«Entregar 20 paquetes», y OPCIONES con «Silenciar juego» (clic o tecla M: silencia todo el juego o devuelve
el sonido). I lo cierra. Reemplaza al inventario del demo de reciclaje (oculto).
Captura: `Docs/character_panel.png`.

## Misión, sonidos de cajas y comienzo de rama (28/09)

- **Misión** (`UFactoryMissionSubsystem`, meta `Goal` 20): un paquete cuenta como entregado cuando el camión que
  lo lleva pasa la barrera (o llega al final de su línea si no hay barrera). Como los camiones salen llenos, sube
  de a 10. El panel (I) muestra «Entregar 20 paquetes · n / 20» con barra; al llegar a 20 suena
  `S_MisionCompleta` y aparece arriba «¡MISIÓN CUMPLIDA! Entregaste 20 paquetes» por 7 s, y el panel dice
  «OBJETIVO CUMPLIDO». No se guarda con F5 (todavía).
- **Sonidos de cajas**: `S_CajaAgarrar` al agarrar una caja (de una cinta o del piso) y `S_CajaSoltar` al soltarla
  o apoyarla en una cinta (`Scripts/make_ui_sounds.py` + `Scripts/apply_mission.py`; se cambian reemplazando los WAV
  en `SourceAssets/Audio`).
- **Comienzo de una rama**: una caja apoyada a menos de `CrossingZone` (70 cm) del comienzo de una cinta que sale
  de un cruce (hoy el comienzo de `Cinta_Carga2`, la larga) va a donde la mandaría el cruce: con el camión 1 lleno
  o yéndose, derecho al camión 2 por `Cinta_Carga4`.
- Prueba: `Scripts/playtest_mission.py` (7 comprobaciones, pasó el 28/09; capturas `Docs/mission_panel.png` con
  10 / 20 y `Docs/mission_complete.png` con el aviso).

## Portón en la entrada de los camiones (28/09)

`Porton_Camiones` (clase C++ `AFactoryRollDoor`, carpeta Environment, enganchado al estacionamiento): portón
enrollable de tablillas en la abertura oeste (dentro del espesor del muro), con caja del rollo sobre la abertura
(del lado de adentro) y botonera en la cara de adentro de la columna a su derecha (vista desde el estacionamiento).
Arranca cerrado. Con E junto a la botonera («[E] ABRIR/CERRAR PORTÓN») se enrolla hacia arriba en 2,2 s o baja; el
hongo de la botonera pasa de rojo a verde. Cerrado, los camiones frenan ~70 cm antes y esperan. Nunca baja sobre un
camión. No se cierra solo. El portón y la barrera comparten la clase base `AFactoryTruckGate` (lo que el camión
respeta); solo la barrera cuenta la entrega. Piezas: `Scripts/author_roll_door.py`; colocar: `Scripts/apply_roll_door.py`
(conserva el lugar si ya existe; `Button` y `Housing` se pueden mover aparte). Prueba: `Scripts/playtest_door_and_panel.py`
(10 comprobaciones, pasó el 28/09; captura `Docs/roll_door_closed.png`).

## Panel de información: 3 estilos para elegir (28/09)

Investigación de estilos de interfaz actuales (Balatro, Metaphor: ReFantazio, Splatoon 3, Zenless Zone Zero, Persona)
y "juice" de menús. Con I abierto, 1 · 2 · 3 (o las pestañas de arriba) cambian el estilo; cada cambio repite su entrada.
Mismo contenido en los tres (retrato, bienvenida, objetivo con n / 20 y silenciar). Código: `Private/FactoryInfoPanel.cpp`.
1. **Pegatina Pop** (cartoon): tarjeta crema con borde de tinta y sombra dura; entra con rebote (0,35 s) y cada parte
   aparece escalonada (60 ms); retrato en círculo que sobresale y se balancea; globo de diálogo que se escribe solo;
   20 casilleros-caja que aparecen en cadena; botón azul que "se hunde" bajo el mouse.
2. **Taller Holográfico** (sci-fi amable): apertura tipo pantalla vieja (línea que se abre), borde que brilla y late,
   barrido de escaneo cada 3 s, texto que se "descifra", retrato hexagonal con líneas y un parpadeo cada 4 s, barra
   segmentada tipo orden de trabajo, interruptor de dos estados.
3. **Cartel de Almacén** (cómic industrial): franjas diagonales que barren desde la izquierda, rayas de peligro que
   avanzan, retrato grande inclinado que entra girando con rebote, albarán de cartón, número gigante que "respira" y
   salta al subir, barra de cinta de embalaje.
Al subir el contador (entrega), el número salta y la última celda/segmento reacciona. Capturas: `Docs/info_style_1.png`,
`_2`, `_3` y `Docs/info_style_N_entrada.png` (a mitad de la animación). Prueba: `Scripts/playtest_info_styles.py`.

Elegido (28/09): **Pegatina Pop**. Se quitaron los estilos 2 y 3, las pestañas y el cambio con 1 · 2 · 3; su código
queda en `Saved/Respaldos/2026-09-28_interfaz_3_estilos`. La I abre directamente la tarjeta Pegatina Pop.

## Señal de eventos, aviso de misión y ajustes de cintas (28/09)

- **Señal de eventos** (arriba a la izquierda, estilo Pegatina Pop): sticker redondo con «!». En calma (crema) sin
  eventos; con eventos, naranja con un globito rojo con la cantidad, se balancea y salta cuando aparece uno nuevo.
  Clic en la señal: tarjeta con la lista (otro clic la cierra). Eventos de hoy: camión esperando en el portón
  («Abrilo con E en la botonera de la columna»), camión en la barrera (con cuántos paquetes lleva; «Entrá a la cabina
  y levantala con E») y cinta de despacho llena («Sacá cajas para que vuelva a andar»). El camión informa qué portón
  o barrera lo tiene esperando (`GetWaitingGate`). Captura: `Docs/events_panel.png`.
- **Misión cumplida** al estilo Pegatina Pop: tarjeta crema con borde de tinta, retrato en círculo verde, cinta verde
  «¡MISIÓN CUMPLIDA!», «Entregaste 20 paquetes. ¡Gran trabajo!», entrada con rebote, confeti en los colores del
  personaje; a los 7 s se achica y se va. Captura: `Docs/mission_notice.png`.
- **Cintas de carga**: en un cruce la caja ya no salta por encima de una cinta llena: si la rama que le toca tiene la
  fila llena al principio, espera. Solo pasa a la otra rama cuando el camión de adelante no tiene lugar. Separación
  entre cajas 58 cm (antes 50).
- Prueba: `Scripts/playtest_events.py` (pasó el 28/09). `playtest_belt_routing.py` y `playtest_mission.py` ahora abren
  el portón al empezar (se escribieron antes de que existiera); routing volvió a pasar 8/8.

## Unión de cintas y barrera del otro lado (28/09)

- En la unión de dos cintas, la caja que espera al final de la primera frena antes si la primera caja de la
  siguiente está a menos de una caja (`BoxSpacing`) de ese final: ya no se enciman. Prueba:
  `Scripts/playtest_junction_barrier.py` (separación mínima medida 82 cm; captura `Docs/junction_boxes.png`).
- La garita (`Cabina_Barrera`) quedó al sur del carril (movida por el usuario). El poste de la barrera pasó a su
  lado norte, relativo (−40, −130), y el brazo apunta hacia el carril (yaw −90) y lo cruza entero (del poste en
  y 670 a la punta en y 360, en cm del estacionamiento; el camión ocupa ~421–633): `Scripts/fix_barrier_side.py`.
  El camión lleno frena ahí (misma prueba).

## Calle del recorrido (28/09)

`Camion_Recorrido` tiende una calle a lo largo de su línea (`RoadMesh` = `SM_CalleTramo`, repetido cada ~2 m con
SplineMeshComponents que se curvan con la línea): asfalto de 3,8 m con banquina oscura, líneas blancas de borde y
línea central amarilla punteada, 0,5 cm sobre los puntos, sin colisión ni sombra. Si se mueven los puntos de la línea,
la calle se rehace sola. El segundo camión (que usa la línea del primero) no dibuja otra. Hoy son 27 tramos en 53 m.
Pieza: `Scripts/author_road.py`; aplicar: `Scripts/apply_road.py`. Capturas: `Docs/road_1.png` a `road_3.png`
(`Scripts/playtest_road_shots.py`).

## Arranque como juego: piezas bloqueadas, rincón de basura y ploteo (28/09)

- **Respaldo**: `L_FactoryDemo_Completo` es el mapa con todo construido (sin bloqueos ni relleno), hecho con
  `Scripts/make_complete_backup.py` a partir del mapa actual.
- **Bloqueado** (`UFactoryUnlockSubsystem`, en `FactoryMission.h/.cpp`): un actor con las etiquetas `Bloqueado` + un
  grupo sigue en el nivel (carpeta `Bloqueado/<Grupo>` del Outliner, visible en el editor) pero en juego no se ve, no
  choca, no hace tick y todo lo ignora (cintas, camiones, botoneras, eventos). Grupos de hoy:
  - `Despacho2`: `Despacho_Machine2`, `Despacho_Cajas2`, `Botonera_Cinta2` (la cinta de despacho 2; la 1 arranca activa).
  - `Camion2`: `Camion_Recorrido2` y `Cinta_Carga4` (se volvió a crear donde estaba, relativa (-318,-15) al estacionamiento).
- **Relleno**: actores con `Relleno` + grupo ocupan el lugar mientras tanto; hoy el rincón de basura del grupo
  `Despacho2` (carpeta `Relleno/Despacho2`): tablones tapando la abertura del muro, volquete verde lleno de bolsas,
  pallet con cajas y bolsas sueltas (`Scripts/author_junk_corner.py`, en `/Game/FactoryCtyco/Environments/Rincon`).
- **Desbloquear** (para las mejoras): `UFactoryUnlockSubsystem::Get(this)->Unlock("Despacho2")` (también desde
  Blueprint): aparecen las piezas del grupo, se borra su relleno, las cintas se vuelven a enlazar y los camiones
  buscan sus paradas de nuevo. Cada grupo se desbloquea por separado. Para una mejora nueva basta con etiquetar sus piezas.
- **Ploteo del camión** inspirado en League of Legends (diseño propio, sin logos oficiales): `T_PloteoCamion`
  (`Scripts/author_truck_wrap.py`) en `M_PloteoCamion`, sobre el panel de una cara `SM_PloteoLado`
  (`Scripts/author_truck_wrap_mesh.py`), en `/Game/FactoryCtyco/Environments/Ploteo`. `AFactoryVehiclePath` pone uno a cada
  lado de la caja (`WrapMesh`, `WrapCenter` = (107, 86, 158)); el de la puerta la acompaña al abrirse. A menos de ~85 cm
  del centro queda tapado por la chapa.
- Ojo al importar: reimportar un FBX encima de una malla existente la dejó a 1/100 de su tamaño; los scripts
  borran la malla y la importan de nuevo.
- Aplicar: `Scripts/apply_game_start.py`. Prueba: `Scripts/playtest_game_start.py` → `Docs/game_start_play.json`.

## Contratar personal: encargado de barrera (28/09)

- **Tecla I**: el panel tiene dos pestañas, `INICIO` (lo de antes) y `CONTRATAR` (tarjeta del encargado de barrera con
  su estado y el botón CONTRATAR). Captura: `Docs/contratar_panel.png`.
- **Clic izquierdo en la cabina**: panel a la derecha con los datos (barrera arriba/abajo, camiones esperando, camiones
  que salieron, encargado), la misma tarjeta para contratar y `MEJORAR CABINA` (por ahora solo dice "pronto"). Se cierra
  con la X o con un clic en otro lado. Captura: `Docs/cabina_panel.png`.
- **Llegada** (`AFactoryWorkerSpawn` "Punto_Contratacion", carpeta `Empleados`, puesto `Barrera`): en el piso 3
  (estacionamiento de empleados). El contratado llega en auto por `CarRoute` (primer punto: donde aparece el auto;
  último: el cajón donde estaciona, con la trompa hacia donde apunta la línea), en uno de `CarMeshes` al azar. Se baja
  por detrás del auto, camina al ascensor, viaja (`RideSeconds`, 3 s) al piso de su lugar de trabajo y camina hasta la
  puerta de la cabina y adentro. Las caminatas usan la malla de navegación (volúmenes `Nav_Empleados` y
  `Nav_Estacionamiento`, generada al jugar: `RuntimeGeneration=Dynamic` en `DefaultEngine.ini`); si algo lo traba
  2,5 s salta al punto siguiente (`Skips`, `LastHeldAt` dicen dónde). El auto queda estacionado.
  Para otro lugar de trabajo en otro piso agregar un volumen de navegación ahí.
- **El encargado** (`AFactoryWorker`) es una copia del personaje (misma malla, animaciones y velocidad, copiadas del
  jugador al contratarlo). En la cabina, cuando un camión frena en la barrera, la levanta a los 0,8 s; la barrera
  baja sola cuando el camión pasó. Contratados: `UFactoryStaffSubsystem` (`Hire`, `IsHired`, `GetWorker`). Las
  puertas de los ascensores también se abren para él.
- Capturas: `Docs/encargado_cabina.png`, `ploteo_cerrado.png` (barrera levantada por él) y las del piso 3.

## Piso 3 con la escena del usuario (29/09, reemplaza lo de abajo)

A pedido, el estacionamiento de empleados es ahora la escena del usuario `3D assets/GLBs/esceneStacionamientoOriginal.glb`:
un patio de 24 × 22 m con dos filas de cajones, cerco, barrera de entrada, nave con portón, muelle con cinta y cajas, y una
plataforma con escalera. El estacionamiento de despacho (`Parking_Estacionamiento`) no cambió.

- Actor `Empleados_Escena` en (-3800, 9000, 400), el mismo lugar y la misma altura que el piso anterior. Malla
  `/Game/FactoryCtyco/Environments/EmpleadosEscena/SM_EmpleadosEscena` (284 colisiones UCX). Alrededor hay pasto y
  una calle de acceso; esas dos piezas no tienen colisión, y paredes invisibles en el borde de la losa no dejan salir del patio.
- Cambios sobre el GLB (`Scripts/author_employee_scene.py`):
  - Se quitó el montacargas decorativo de la plataforma.
  - La barrera de la entrada queda levantada.
  - La escalera tiene colisión de rampa. La plataforma es un bloque macizo con barandas que no dejan caer.
- **Recepción** (pedido del 29/09, versión final): **la sala de recepción del usuario** (`3D assets/GLBs/recepcion`) va
  contra la fachada de la nave, con su puerta de entrada sobre la plataforma de la escalera. Es la única puerta: se
  quitaron la puerta de personal «03», el pasillo y la puerta automática y el techo ocultable que se usaban antes.
  - Actor `Recepcion_Sala`, malla `/Game/FactoryCtyco/Environments/EmpleadosEscena/SM_RecepcionSala`. `Scripts/author_reception_room.py`
    la prepara: usa las colisiones del usuario, saca las hojas de la puerta doble, deja sin colisión la hoja abierta de
    la entrada y la maceta de al lado, y pasa los asientos de espera y la mesita al frente de la sala (del lado de la
    baranda), dados vuelta: el respaldo contra la baranda y la mesita delante, mirando hacia el mostrador.
  - El tramo de la nave que ocupa la sala se recortó (`NAVE_CUT`). También se sacó lo que colgaba de esa fachada:
    lámparas, caños, tableros y la puerta 03 con su número. Un muro de ladrillo cierra el corte del lado de la nave.
  - El lado de la puerta de entrada, que da al patio, era un muro bajo: ahora es **muro completo** de 3,5 m (hileras de
    ladrillo copiadas del muro bajo, remate y columna de la esquina subidos, colisión hasta arriba).
  - **La puerta de entrada** venía fija y abierta en el modelo. Se separó y se cerró: es `Puerta_Recepcion`
    (`AFactoryAutoDoor`, hoja `SM_PuertaRecepcionSala`, sin colisión). Se abre sola hacia afuera, sobre la plataforma,
    cuando alguien se acerca, y después se cierra.
  - La sala no tiene techo: el lado bajo con baranda que queda es para la cámara isométrica. Lleva un zócalo de hormigón
    debajo, con colisión, porque está a la altura de la plataforma (2,5 m).
  - **Detrás de su puerta doble está `Ascensor_Empleados`**, el mismo de antes, dentro de un hueco de ladrillo abierto
    arriba. Los empleados entran por sus puntos de acceso (`Approach`: entrada, bajando por la pared y por delante del
    mostrador; se mueven en el viewport), porque la navegación no pasaba entre los muebles de la entrada.
  - La flecha de la guía apunta a la puerta de la sala (`Guia_PuertaAscensor`).
- **Muelles de carga** (29/09): se quitaron los dos muelles de la nave: rampas con rodillos, aleros, burletes, barandas
  naranjas, balizas y las cajas que tenían encima. Su hueco quedó como pared de ladrillo (`DOCK_WALL`). Los pallets
  con cajas del patio siguen.
- **Autos** (29/09): el auto del usuario (`3D assets/GLBs/autoAzul1.glb`, hatchback de 3,9 m) en cinco colores (azul, rojo,
  blanco, gris y verde). `Scripts/author_employee_cars.py` lo reduce a 50k triángulos y recolorea solo la chapa.
  - Mallas `SM_Auto_<Color>` en `/Game/FactoryCtyco/Environments/EmpleadosEscena`.
  - Cinco estacionados en los cajones F0, F1, F3, R0 y R3.
  - Los contratados llegan en uno de esos colores al azar: entran por la calle y la barrera, estacionan en F4, suben la
    escalera y cruzan la puerta y la sala hasta el ascensor (`Punto_Contratacion` y su `CarRoute`).
- `PlayerStart_Robot1`: el gerente aparece en el pasillo entre las dos filas. `Nav_Empleados` cubre el patio y la recepción.
- Navegación: `bForceRebuildOnLoad=True` en `Config/DefaultEngine.ini`. Al cargar el nivel se rehace entera; si no, quedaba
  la de antes de la sala. Si un empleado se traba, primero busca el camino de nuevo desde donde está, y recién si no lo
  encuentra salta al punto siguiente.
- Se sacaron del nivel `Empleados_Piso`, `Empleados_Decor`, los siete autos y `Empleados_Cartel`. Las mallas viejas siguen
  en `/Game/FactoryCtyco/Environments/Empleados`. Respaldo del nivel anterior: `Saved/Respaldos/2026-09-29_empleados/L_FactoryDemo.umap`.
- **Vagabundo** (29/09): modelo del usuario `vagabundo1.glb`. `Scripts/author_vagabundo.py` lo reduce a 60k triángulos,
  aclara su textura (se veía muy oscuro) y le arma un esqueleto. Está **acostado boca arriba** en el piso, con la cabeza
  algo alta, la rodilla izquierda levantada y los brazos al costado, con una **botella** de vidrio verde junto a la mano
  izquierda (`Vagabundo_Botella`, malla `SM_Botella` hecha en el script).
  - Clips: `A_Vagabundo_Idle` (8 s en bucle: respira, mueve apenas la cabeza y los dedos) y `A_Vagabundo_LevantaBrazo`
    (3 s: sube el brazo derecho hacia el cielo, lo sacude y lo baja).
  - Assets en `/Game/FactoryCtyco/Characters/Vagabundo`: `SK_Vagabundo`, los dos clips, `SM_Botella` y su voz `S_Vagabundo_YElla`.
  - La voz es la **grabación del usuario** `3D assets/Voces/vagabundo_y_ella.m4a`. `Scripts/prepare_voice.py` la pasa a
    `SourceAssets/Vagabundo/vagabundo_y_ella.wav`, con el silencio recortado y el volumen nivelado. La voz sintética
    anterior quedó como `vagabundo_y_ella_sintetica.wav`. Las voces nuevas se guardan en `3D assets/Voces`.
  - Actor `Vagabundo` (clase C++ `AFactoryNpc`) acostado a lo largo del cerco, en la esquina del fondo a la izquierda,
    con la cabeza hacia la nave. Al acercarse el jugador (`TalkRadius` 280 cm) dice «¿Y ella?» con su voz, **levanta el
    brazo** (`TalkAnimation`) y sobre él aparece el globo con su nombre y la frase, letra por letra. Después vuelve al
    reposo. Frases en `Lines` y voces en `LineSounds`, en orden; una caja invisible (`Blocker`) no deja pisarlo.
  - Colocarlo: con el editor cerrado, `Scripts/apply_vagabundo.py` (informe `Docs/vagabundo.json`).

Regenerar:
1. `blender -b --factory-startup -P Scripts/author_employee_scene.py`. Genera `SourceAssets/EmpleadosEscena`.
   Antes, si cambiaron, `author_reception_room.py` (la sala) y `author_employee_cars.py` (los autos).
2. Con el editor cerrado, correr `Scripts/apply_employee_scene.py` con `-ExecutePythonScript` (es idempotente). Informe:
   `Docs/employee_scene.json`. Después, `apply_mission_guide.py` y `apply_vagabundo.py`.

Prueba en Play: `Scripts/playtest_employee_scene.py` → `Docs/employee_scene_play.json`. Pasó las 18 comprobaciones el 29/09:
- el gerente aparece parado;
- el vagabundo está acostado y animado, habla con su voz, levanta el brazo y se calla;
- la puerta de la sala está cerrada, se abre sola hacia afuera al acercarse, y adentro se queda parado en su piso;
- se baja al DESPACHO por el ascensor de la sala;
- dinero: se empieza con $ 0, sin plata no se contrata y contratar cuesta $ 800;
- el contratado estaciona en F4, sube la escalera, cruza la sala y llega a la cabina en 35 s, sin trabarse.

## Piso 3: estacionamiento de empleados (28/09)

Playa al aire libre, lejos del resto del nivel y más alta (Z 400), así el panel del ascensor la muestra como piso 3
("EMPLEADOS"; los pisos se ordenan por altura). Piezas (`Scripts/author_employee_parking.py`, en
`/Game/FactoryCtyco/Environments/Empleados`): `SM_EmpleadosPiso` (pasto de 62 × 48 m, playa de asfalto con 18 cajones en dos
filas, flechas, senda peatonal, calle de entrada por el oeste, vereda con el agujero del pozo del ascensor; paredes
invisibles alrededor de la playa), `SM_EmpleadosDecor` (cerco de arbustos, faroles, árboles, banco) y
`SM_AutoEmpleado_Rojo/Azul/Blanco/Gris`. Colocado por `Scripts/apply_employee_parking.py` (idempotente):
`Empleados_Piso` en (-3800, 9000, 400) con la decoración y 7 autos estacionados, `Ascensor_Empleados` (copia del
ascensor del estacionamiento), el cartel pintado "EMPLEADOS", el punto de llegada de los contratados y los volúmenes de
navegación. Prueba: `Scripts/playtest_employee_floor.py` → `Docs/employee_floor_play.json` (sube al piso 3 con el
ascensor; el encargado llega en auto y va hasta la cabina: auto 8 s, a pie al ascensor 9 s, ascensor 3 s, a pie a la
cabina 11 s, sin trabarse). Capturas `Docs/piso3_*.png`.

## Cámara libre y seguir personajes (29/09)

- La cámara arranca **libre** (`bStartFree` en el componente `FactoryCamera` de `BP_FactoryRobot`,
  `Scripts/set_free_camera.py`): no sigue al personaje. Botón central arrastrando la mueve, sin límite de distancia.
- **Clic sobre un personaje** (TecJunior o un contratado): la cámara lo sigue. Un contratado que maneja se sigue a
  través de su auto; mientras viaja en el ascensor la cámara espera y salta cuando sale.
- **Flechas**: mueven la cámara según la pantalla (más rápido con más zoom afuera; si seguía a alguien, lo suelta).
  Las flechas ya no mueven al personaje: se sacaron de `IA_Move` en `IMC_Default` (`Scripts/free_arrow_keys.py`,
  respaldo en `Saved/Respaldos/2026-09-29_flechas`); el personaje camina con WASD.
- Deja de seguir: arrastrar con el botón central, flechas o clic en el piso. **Inicio**: vuelve a seguir a TecJunior.
- Si TecJunior viaja en ascensor con la cámara libre, la cámara va con él al otro piso (salto de más de 10 m en un cuadro).
- Abajo a la derecha: "CÁMARA LIBRE" (azul) o "SIGUIENDO: …" (naranja).
- El otro modo de juego (GrowEvolution) usa la misma cámara con `bStartFree` apagado: no cambia.
- Prueba: `Scripts/playtest_free_camera.py` → `Docs/free_camera_play.json` (11 comprobaciones), capturas
  `Docs/camara_libre.png`, `camara_sigue.png`, `camara_sigue_auto.png`.

## Ajustes del 30/09

- **Puerta de la recepción**: `Puerta_Recepcion` se abre hacia adentro de la sala (`OpenYaw` 60). No llega a 90°: la
  maceta de la entrada está pegada a la bisagra y la hoja la cruzaría. Para abrirla más, correr la maceta en
  `author_reception_room.py`.
- **Parpadeo detrás de los asientos**: el relleno del hueco de los muelles (`Dock wall fill`) se pisaba con el muro que
  cierra el corte de la nave (`Nave cut wall`): sus caras coincidían y alternaban texturas. `DOCK_WALL` ahora termina
  donde empieza ese muro (`author_employee_scene.py`); se reimportó `SM_EmpleadosEscena` (214 colisiones, igual que antes).
- **Flecha de la misión 1**: sobre `Ascensor_Empleados`, no sobre la puerta.
- **Cintas de carga**: el camión carga en `Cinta_Carga4`, que sigue derecho desde `Cinta_Carga3`, y para ahí (a 5,7 m de
  la parada anterior). El tramo en L (`Cinta_Carga2` → `Cinta_Carga`) pasó al grupo bloqueado `Camion2`, junto con el
  segundo camión: en juego no se ve y aparece con esa mejora.
- Todo junto: `Scripts/apply_fixes_2026_09_30.py` (editor abierto; informe `Docs/fixes_2026_09_30.json`). Prueba en Play:
  `Scripts/playtest_fixes_2026_09_30.py` (6 comprobaciones, pasó; `Docs/fixes_2026_09_30_play.json`).
  Respaldos: `Saved/Respaldos/2026-09-30_ascensor_cintas` y `SourceAssets/EmpleadosEscena/respaldo_2026-09-30_parpadeo`.
