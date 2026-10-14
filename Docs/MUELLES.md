# Muelles de carga — 3 de octubre de 2026

Escena del usuario (`3D assets/GLBs/scenes/Muelles de carga en patio industrial-complete.glb`, pedida con
[PROMPT_PLAYA_CARGA.md](PROMPT_PLAYA_CARGA.md)): edificio con muelle a 1,2 m, tres bahías con portón, escaleras y
puertas de personal, y un patio de asfalto con tres cajones, rodeado de muro de ladrillo de 2,25 m. 49 × 46 m, techo
a 5 m. Ya venía en metros: se unió en una malla sin reducir (9 276 triángulos, 12 materiales). Choca con su propia
malla (*complex as simple*): se camina el muelle, las escaleras y el patio.

- Actor `Muelles_Carga` (carpeta Muelles) en (-4273, 2953, 10): detrás del muro norte del estacionamiento (el paralelo
  a la calle de los camiones), con el edificio del muelle pegado a ese muro y el patio hacia +Y (norte). El patio está
  a la altura del piso del estacionamiento. Para acomodar.
- **Unión con el despacho**: se quitaron la pared de atrás del edificio del muelle (ladrillo, rejillas, caños, pilares
  y luces; el bloque del edificio quedó abierto atrás y con su interior visible) y los muros bajos del norte del
  estacionamiento (`Perimeter*`); una losa (`North join slab`, en `author_parking_scene.py`) tapa la franja más baja que
  quedaba entre los dos. Se pasa caminando del despacho al interior del muelle.
- **Camiones al muelle**: la línea de `Camion_Recorrido` (y de `Camion_Recorrido2`) cruza el patio de oeste a este sobre
  la línea amarilla, entrando y saliendo desde afuera. Todavía atraviesa los muros del patio: se abren donde quede la
  línea definitiva (la dibuja el usuario).
- **Cajones** `Cajon_Muelle_1..3` (`AFactoryTruckBay`, carpeta Muelles): el actor está donde queda el eje trasero del
  camión estacionado, mirando al patio. Su `Maneuver` va de ahí a la línea del camión, `JoinAhead` (12 m) más adelante,
  y se engancha sola al mover el cajón o la línea (`bAutoManeuver`; apagado, se dibuja a mano). El camión va al cajón
  libre más lejano, frena con el eje trasero en el enganche, entra marcha atrás por la maniobra (`ManeuverSpeed`) y se
  queda (`ParkSeconds` 0; con otro valor sale después de ese tiempo y sigue). Estacionado no ocupa la línea.
- Al empezar hay un solo camión activo (el 2 es la mejora `Camion2`). La carga en el muelle es a mano, más adelante:
  por ahora la misión 1 (20 paquetes) no se puede completar, y el puesto de encargado de barrera no tiene garita.
- Scripts: `author_muelles.py` y `author_parking_scene.py` (Blender), `import_muelles.py`, `reimport_parking_mesh.py`,
  `apply_muelles_camiones.py`. Prueba: `playtest_muelles.py` → `Docs/muelles_play.json` (6/6: sin garita ni calle, los
  dos camiones en dos cajones, paso al muelle, pasarela recta).
- Regenerar: `blender -b --factory-startup -P Scripts/author_muelles.py`, después `Scripts/import_muelles.py`.

## Carga en el muelle, pasos, calle y garita (03/10, sobre la escena como la dejó el usuario)
El usuario dejó `Muelles_Carga` en (-3503, 2043, -10) a escala 0,75 y acomodó los cajones (`Cajon_Muelle_1` en el del
este) y la línea, que entra al patio por el muro oeste y sale por el este. `Scripts/apply_muelles_conexion.py`:
- **Cintas al muelle**: desde la punta de `Cinta_Carga4` siguen `Cinta_Muelle_1..5` (carpeta Muelles): recta subiendo a
  1,25 m (para pasar sobre el andén), curva, recta por dentro del edificio, curva y recta hasta el borde del andén,
  detrás de `Cajon_Muelle_1`.
- **Carga estacionado**: un camión estacionado con su eje trasero a menos de `BayLoadReach` (2,5 m) de la punta de la
  última cinta de una cadena se amarra a ella, abre y carga; lleno, cierra, sale del cajón y sigue. Al final de su
  línea la misión cuenta los paquetes (la misión 1 vuelve a poder completarse).
- **Pasos en los muros**: donde la línea cruza un muro del patio se abre un paso de 5 m (anotados en
  `SourceAssets/Muelles/truck_openings.json`; los corta `author_muelles.py`). Hoy: muro oeste y muro este. Si se mueve
  la línea: correr el script, Blender y `import_muelles.py` de nuevo. Los puntos de la línea dentro del patio bajan a su piso.
- **Garita y calle**: `Cabina_Barrera` volvió, adentro del patio, 6 m después del paso de entrada, con el brazo
  cruzando la línea (en la salida no: el cajón del este se engancha casi en el muro de salida y el camión frenaría en la
  barrera antes de llegar). La calle se dibuja otra vez a lo largo de la línea.
- Prueba: `Scripts/playtest_muelles_carga.py` → `Docs/muelles_carga_play.json` (7/7: garita en los muelles, calle,
  cintas encadenadas, el camión se estaciona en el cajón 1, carga las 10 cajas de la cinta, sale lleno y la misión
  cuenta 10 paquetes).

## Toyota
`Toyota` (carpeta Estacionamiento): camioneta del usuario (`3D assets/GLBs/toyota.glb`), 4,9 × 2,5 × 1,96 m, 80 000
triángulos, texturas a 2K, caja de colisión. Puesta en el estacionamiento en (-3300, 160), donde antes pasaba la calle,
para acomodar. Scripts: `author_toyota.py` (Blender) e `import_toyota.py`.

## Pasillo en L desde la puerta del muelle (04/10)
La puerta de personal del bloque de ladrillo del este (`Man door 1`, sobre el andén, junto al primer cajón) ahora se
abre a un pasillo en L dentro del bloque (que era macizo): el tramo 1 entra desde la puerta y baja en rampa del andén
(1,18 m) al piso del edificio; el tramo 2 dobla al oeste y sale por la cara interior del bloque, adentro del edificio,
detrás y al costado del portón del primer cajón. Sin hoja de puerta (vano abierto); el "marco" original era un bloque
macizo y se cambió por dos jambas y un dintel. 1,2 m de ancho en el juego. Lo hace `author_muelles.py`
(`PASSAGE_*`), después `import_muelles.py`. Prueba: `Scripts/playtest_pasillo_muelle.py` →
`Docs/pasillo_muelle_play.json` (entra, baja y sale adentro del edificio).

## Curva de los cajones y persiana trasera (04/10)
- **Curva editable**: cada `Cajon_Muelle_N` muestra dos rombos en el viewport. `BendHandle` (en el medio de la curva):
  se arrastra y la curva pasa por ahí (`bBend` / `BendPoint`; el botón `StraightenCurve` la vuelve a la forma simple).
  `JoinHandle` (donde la curva toca la línea): se arrastra y el enganche se corre sobre la línea (cambia `JoinAhead`).
  `ExitStraight` y `JoinStraight` (0,1 a 3) hacen más recta o más cerrada la salida del cajón y la entrada a la línea.
  Con `bAutoManeuver` apagado se siguen editando los puntos del spline a mano.
- **Persiana**: estacionado en un cajón, el camión abre la parte de atrás (una persiana que se enrolla hacia arriba) en
  lugar de la puerta del costado; en las cintas a lo largo de la línea sigue abriendo el costado. La persiana es
  `SM_CamionPersiana` (`RearDoorMesh`, `RearDoorTop`, `RearDoorRolled` en el camión), separada del modelo en
  `author_truck_loop.py`; el forro de la caja quedó abierto atrás. Reimporte: `Scripts/apply_persiana_camion.py`
  (→ `Docs/persiana_camion.json`). Prueba: `playtest_muelles_carga.py` → `Docs/muelles_carga_play.json` (9/9, con
  `abre_la_persiana` y `persiana_cerrada_al_salir`).

## Portones de los cajones (04/10)
- Los tres portones seccionales del edificio del muelle ya no son parte de `SM_Muelles`: son `Porton_Muelle_1..3`
  (StaticMeshActor movible con `SM_PortonMuelle`, enganchados a `Muelles_Carga`), y la pared de hormigón detrás de cada
  uno tiene un hueco (`author_muelles.py`).
- Cada `Cajon_Muelle_N` tiene su portón en `DockDoor` (hoy: cajón 1 → portón 3, cajón 2 → portón 1, cajón 3 → portón 2,
  el más cercano). El portón **sube cuando el camión que va a ese cajón pasa la garita** de entrada (o apenas elige el
  cajón si no hay barrera antes), sigue arriba mientras entra marcha atrás y carga, y **baja cuando el camión sale**.
  Se enrolla hacia su borde de arriba (`DoorSeconds` 2 s, `DoorRolled` 0,08).
- Arreglo: el camión estacionado medía la distancia a la cinta desde donde lo había dejado el cuadro anterior; con pocos
  cuadros por segundo quedaba a más de `BayLoadReach` y no cargaba. Ahora mide desde el punto del cajón.
- Scripts: `author_muelles.py` (Blender) y `apply_portones_muelle.py` (corre `import_muelles.py`, importa el portón, pone
  los actores y los asigna; correrlo con el editor abierto: headless se cae al crear actores) → `Docs/portones_muelle.json`.
  Prueba: `playtest_muelles_carga.py` → `Docs/muelles_carga_play.json` (13/13, con `porton_cerrado_en_la_garita`,
  `porton_abierto_al_estacionar`, `porton_sube_estacionado` y `porton_baja_al_irse`).
- **Las cajas esperan el portón** (04/10): una cinta de carga que cruza el plano del portón de un cajón lo encuentra sola
  al empezar el juego (`bHoldAtDockDoors`) y frena sus cajas `DoorHoldGap` (45 cm) antes de él mientras el portón no
  esté arriba del todo; las que ya lo pasaron siguen. Hoy: `Cinta_Muelle_5` espera a 159,5 cm de su punta de carga
  por `Porton_Muelle_3` (cajón 1).
- `Cinta_Muelle_1` quedó estirada a 1,75 y pasaba por encima de la primera curva (las cajas seguían derecho): se acortó
  a 0,919 e inclinó 3° para terminar justo en la entrada de `Cinta_Muelle_2`. `Cinta_Muelle_6` está encima de
  `Cinta_Muelle_3` (copia; no está en la cadena).
- Prueba: `playtest_muelles_carga.py` (15/15) retiene el camión en la barrera hasta que hay cajas esperando ante el
  portón y comprueba que ninguna lo cruza cerrado.

## Persiana de tablillas, techo fijo y sin puerta de costado (04/10)
- La parte de atrás del camión es una **persiana de tablillas** (`Scripts/author_truck_shutter.py`, colores medidos en
  la textura del camión): 17 tablillas crema como los paneles de la caja, con ranura y bisagra gris; zócalo con goma y
  manija; guías y dintel del gris del marco. Al abrir (estacionado en un cajón) suben y se esconden tras el dintel;
  bajan al cerrar. `AFactoryVehiclePath`: `RearSlatMesh`, `RearBottomMesh`, `RearDoorMesh` (marco), `RearDoorTop`,
  `RearDoorHeight`, `RearHeader`. Importar: `Scripts/apply_persiana_tablillas.py` → `Docs/persiana_tablillas.json`.
  `SM_CamionPersiana` (la pared que se achicaba) se borró.
- El **techo** de la caja ya no se esconde al abrir, y la **puerta del costado** ya no se mueve (se quitaron `RoofBone`
  y `DoorOpenAngle`). Las pruebas viejas que los usaban (`playtest_truck_roof.py`, `playtest_truck_loading.py`,
  `playtest_two_trucks.py`) quedaron desactualizadas.
- **Cajas entre cintas**: al pasar de una cinta a otra la caja sigue desde donde estaba y se acomoda a la nueva en sus
  primeros `HandoffBlend` cm (40), sin el saltito que hacía en los empalmes con hueco o en las curvas.
- **Cajas que giraban al salir de la curva** (04/10): `Cinta_Esquina` está espejada (escala Y -1) y las cajas, hijas de
  la cinta, heredaban el espejo en su giro; el acomodo al pasar de cinta las hacía rotar. Ahora las cajas (y la flecha
  blanca) se ubican en coordenadas del mundo, con la dirección real de la cinta. La prueba lo mide
  (`cajas_miran_hacia_la_cinta`: peor desvío 5,2°, el giro al azar de cada caja es ±4°).
- **Interior del camión**: el forro de la caja quedó cerrado del costado (ya no se abre) y sin el dorso de la puerta vieja,
  que se veía como una tabla suelta. Reimportar el camión: `author_truck_loop.py` y `apply_persiana_camion.py` (que ahora
  solo reemplaza SK_Camion y deja la persiana de tablillas).
- Prueba: `playtest_muelles_carga.py` → 16/16.

## Pasajes por las dos puertas de personal, puertas que se abren solas y carteles (05/10)
- Las dos puertas de personal del andén tienen su pasaje en L hasta adentro del edificio (la derecha ya lo tenía; la
  izquierda, espejado por el ala oeste). Cada salida interior tiene marco de acero y un cartel **«MUELLE DE CAMIONES»**.
- Las hojas salieron del edificio: `Puerta_Muelle_Personal_0` y `_1` (`AFactoryAutoDoor`, `SM_MuellePuertaPersonal`) se
  abren solas hacia el lado contrario del que llega el personaje. `Scripts/author_muelles.py` (PASSAGES) y
  `Scripts/apply_muelles_puertas.py`; prueba `playtest_puerta_recepcion.py` (9/9, las tres puertas automáticas).
- El portón de los cajones trae su propio material (`Sectional_door`, que ya no usa el edificio).
- Cintas: el cajón 1 recibe por `Cinta_Carga3` → `Cinta_Muelle_5`; los cajones 2 y 3 tienen una copia
  (`Cinta_Carga3_Cajon2/3`, `Cinta_Muelle_5_Cajon2/3`, `Scripts/apply_cintas_cajones.py`). Las cintas del despacho
  (`Cinta_Carga2`, `Cinta_Carga`) acumulan y las cajas se llevan a mano.
- Cajas de despacho con etiqueta **A, B, C o D** al azar (`author_dispatch_box_labels.py`, `apply_cajas_etiquetas.py`).
- Estacionamiento: la vieja puerta este (hacia la fábrica) es una pared baja igual a la de al lado
  (`author_parking_scene.py`, EAST_GATE); `Bloqueo_PuertaEstacionamiento` ya no se ve en el editor.

## Puertas de personal que llenan el vano (07/10)
- La hoja (0,96 × 2,10 m en Blender) quedaba chica en el vano del marco (1,60 × 2,30 m): se veía hueco a los costados y
  arriba. `apply_muelles_puertas.py` la estira al vano (`opening_m` de cada puerta en `muelles_build.json`, que ahora
  escribe `author_muelles.py`) con 1 cm de luz por lado, y corre la bisagra al borde. En el juego: 1,18 × 2,28 m.
  Prueba `playtest_puerta_recepcion.py`: 9/9. Respaldo: `Saved/Respaldos/2026-10-07_puertas_y_luz`.

## Equipos del despacho: flejadora, escáner y dos pasarelas (07/10)
Cuatro modelos del usuario (`3D assets/GLBs`, 07/10), sueltos en el estacionamiento (la flejadora en (-3800, -100): primero quedó
adentro de una pieza del estacionamiento; ahora el script busca lugar con rayos al piso) (dentro de `Escena_Despacho`),
carpeta Despacho, para acomodar. Todavía sin función. Chocan con su propia malla (las pasarelas se caminan).

| Actor | Modelo | Tamaño (cm) |
|---|---|---|
| `Flejadora` | Máquina de flejado amarilla y gris (1,75 m de alto) | 311 × 120 × 175 |
| `Escaner_RayosX` | Escáner de rayos X con túnel rojo (1,6 m de alto) | 209 × 297 × 161 |
| `Pasarela_Verde` | Pasarela con barandillas verdes (baranda a 1 m del piso, piso a 65 cm) | 129 × 594 × 165 |
| `Pasarela_L_Elevada` | Pasarela elevada en L (piso a 1 m) | 683 × 681 × 200 |
| `Tunel_Rechazo` | Túnel de rechazo galvanizado (07/10, 2,4 m de alto), para las cajas defectuosas | 497 × 133 × 240 |
| `Tolvas_Gemelas` | Sistema de tolvas gemelas CUARZO y ARENA (08/10, 4 m de alto). Carpeta **Muelles**, en el patio de los muelles al este de los cajones, (-2200, 1900, -10) | 600 × 271 × 401 |

Scripts: `author_despacho_equipos.py` (Blender: escala, reduce a 100 000/150 000 triángulos, texturas a 2K) e
`import_despacho_equipos.py` (contenido en `Environments/DespachoEquipos/<carpeta>`; si los actores ya existen solo
les cambia la malla). Informe: `Docs/despacho_equipos.json`. Para cambiar un tamaño: `HEIGHT_M`/`RAIL_M` en el script de
Blender y correr los dos de nuevo. Para uno solo: `blender ... -- SM_Nombre` y `ONLY = ["SM_Nombre"]` antes del
import (las pasarelas ya son por piezas, ver PASARELAS.md: no reimportarlas con este script).

## Rampa de las tolvas y camión volcador (08/10)
Frente a `Tolvas_Gemelas` (el usuario las dejó en (-2070, 990, -80), hundidas 90 cm: la boca queda a 2,90 m del piso del
patio) hay una **rampa con plataforma** y un **camión volcador** que retrocede, sube y descarga cuarzo en la tolva del este.
- `Rampa_Tolvas` (carpeta Muelles), en (-1920, 1136, -10), giro 90°: plataforma de 4,6 m a **2,20 m** (el borde de la
  caja queda 10 cm sobre la boca) y rampa de 10,5 m (21 %), muretes de 80 cm y un tope amarillo y negro en el borde.
  Choca con su propia malla (se camina). `Scripts/author_rampa_tolvas.py` (Blender; las medidas arriba del script).
- `Cajon_Volcado` (`AFactoryTruckBay` con **Dump**): el eje trasero queda a 60 cm del borde; la caja asoma 40 cm sobre la
  boca. Maniobra a mano (Auto Maneuver apagado): recta por la plataforma y la rampa y un cuarto de círculo (radio 4,8 m)
  hasta la línea de `Camion_Recorrido`, al este, antes del vano. Solo lo usan los volcadores; los camiones de cajas nunca.
- `Camion_Volcador` (`AFactoryVehiclePath` con **Dump Truck**, carpeta Environment): va por la línea de los camiones
  (Lead Path) 14 s después del primero, con `SK_CamionVolcador` (el camión del usuario con el hueso `Caja`, bisagra abajo
  y atrás: `Scripts/author_truck_dump.py`) y 48 trozos de `SM_Cuarzo` en la caja. Estacionado abre la persiana, levanta la
  caja a 50° (4 s), los trozos se deslizan y caen en la boca, la mantiene 2,5 s, la baja (3 s), cierra y sigue. Cada
  vuelta viene cargado. Ajustes en Vehicle Path → Dump (ángulo, tiempos, malla y cantidad de la carga).
- Script del editor: `Scripts/apply_rampa_tolvas.py` (importa, coloca contra la tolva `HOPPER`, arma la maniobra y el
  camión; informe `Docs/rampa_tolvas.json`). Si se mueven las tolvas, correrlo de nuevo.
- Prueba: `Scripts/playtest_volcador.py` → `Docs/volcador_play.json` (8/8: sube la rampa con 11,8° de inclinación,
  estaciona arriba, levanta la caja, los 48 trozos caen dentro de la boca, sale; con el camionero y la garita).
- Ojo: la curva del volcador cruza la del `Cajon_Muelle_1`; si los dos maniobran a la vez se atraviesan un momento.

## Camionero y garita (08/10)
- Cada camión lleva un **camionero**: TecJunior sentado al volante (`A_TecJunior_Sit`, `Scripts/author_tecjunior_sit.py`),
  componente `Driver` de `AFactoryVehiclePath` (Vehicle Path → Driver: malla, animación y lugar). Para verlo, la cabina
  tiene las **ventanillas y el parabrisas abiertos** y un forro oscuro adentro (`Scripts/author_truck_cab.py`, sobre
  `Camion.blend`; respaldo `Camion_antes_cabina.blend`). Aplicar todo: `Scripts/apply_camionero.py` (reimporta
  `SK_Camion` y el volcador; informe `Docs/camionero.json`).
- La **garita** (`Cabina_Barrera`) y su poste no tenían colisión (se los atravesaba): ahora chocan con su propia malla y se
  entra por la puerta. `Scripts/apply_garita_colision.py` → `Docs/garita_colision.json`. Los camiones siguen esperando
  en la barrera hasta que la levanta el jugador (E adentro de la garita) o el encargado de barrera contratado.

## Tráfico, barrera, cabina y líneas (08/10, segunda tanda)
- **La barrera bajaba sobre los camiones**: el camión creía terminar 60 cm detrás del eje trasero (`RearLength`) y la caja
  sigue 1 m. Ahora `RearLength` = 105 en los tres camiones. El **brazo choca** (con su malla): el personaje no lo cruza.
- **Los camiones no se atraviesan**: cada camión ocupa un rectángulo (Vehicle Path → Traffic: `HalfWidth`, `TrafficGap`)
  y no avanza si el próximo paso lo mete en otro camión que tiene adelante (en la línea, maniobrando o estacionado). Si
  queda trabado `StuckSeconds` (2,5 s), el de atrás en la línea retrocede `BackOffDistance` (2 m) despacio.
- **El personaje choca con los camiones**: caja `Body` del tamaño del camión (la malla posada no tiene colisión).
  El volcador tiene además su physics asset.
- **Cabina**: ventanillas y parabrisas cortados derecho, con vidrio translúcido (`M_CamionVidrioTranslucido`), tablero,
  volante y asiento; el camionero un poco más adentro (335, −38, 16) y con los codos pegados (no sale por la puerta).
  `Scripts/author_truck_cab.py` (parte siempre de `Camion_antes_cabina.blend`), `author_tecjunior_sit.py`,
  `author_truck_dump.py` y en el editor `apply_camionero.py`.
- **Líneas de recorrido**: la línea de `Camion_Recorrido` se dibuja siempre en el viewport (blanca). Sus puntos se
  suben o bajan arrastrándolos; el botón **Snap Line To Ground** (Vehicle Path → Ground) **solo sube** los tramos que
  quedan bajo el piso (a 5 cm sobre él, `LineLift`), agregando puntos ahí sin cambiar la forma de la curva; los tramos
  sobre el piso no se tocan (las calles en rampa de las puertas del patio son solo calle: bajarlas las quebraba y los
  camiones saltaban, 08/10). En las maniobras de los cajones, el rombo del medio (`BendHandle`) también sube o baja la
  curva. Los camiones apoyan cada eje en el piso que tienen debajo o en la calle de su línea si está más alta
  (`Follow Ground`): no se hunden aunque la línea quede bajo el piso.
- Prueba: `Scripts/playtest_trafico.py` → `Docs/trafico_play.json` (9/9, con tres camiones: línea sin escalones y movimiento suave: nunca encimados, se esperan
  y se destraban, la barrera nunca baja sobre uno, ruedas en el piso, el personaje choca contra el brazo y los camiones).
