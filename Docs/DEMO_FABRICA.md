# Demo de reciclaje

Mapa: `/Game/FactoryCtyco/Maps/L_FactoryDemo`.
Abrí [`ABRIR_DEMO.cmd`](../ABRIR_DEMO.cmd) y pulsá **Play**.
La iteración actual vuelve a esta fábrica: el escenario se amplía al alcanzar
logros de producción y entregas. El mapa anterior, `L_Recoleccion`, y el experimento
GROW en `L_GrowRobots` se conservan por separado.

## Primer recorrido

1. Acercate a los montones de chatarra y recogé con **E**. Hay siete montones
   de 30 unidades; la mochila admite 200 unidades en total.
2. En el centro hay cuatro máquinas de ejemplo: depósito de entrada,
   trituradora, fundición y depósito de placas. Empiezan vacías.
3. Pulsá **B** y **4**. Colocá una cinta recta sobre cada uno de los tres
   contornos turquesa entre las máquinas. Cuestan 2 de chatarra cada una.
   Las flechas deben apuntar del depósito de entrada hacia el depósito final.
   **R** gira la vista previa; **clic** construye; **clic derecho** o **B** cancela.
4. Cerrá construcción, acercate al depósito de entrada y pulsá **E** para
   cargar la chatarra de la mochila. Reuní al menos 46 de chatarra en total:
   6 para las tres cintas y 40 para producir 20 placas.
5. Observá cómo la chatarra pasa por la trituradora, la fundición y la última
   cinta. El objetivo exige **20 placas en depósitos y 20 entregadas por cinta**.

También podés cargar directamente las máquinas con **E** y retirar su salida
con **F** para probar el procesamiento manual. Una salida llena pausa la receta.

## El patio cambia con tus logros

El panel de objetivo muestra también tres hitos permanentes. Se activan en orden
y cada transformación del escenario tarda **dos segundos**. La interfaz indica
el requisito del próximo hito o los segundos restantes de su aparición.

| Hito | Requisito acumulado | Cambio en el escenario |
| --- | --- | --- |
| Taller | Producir 5 placas | Aparece un taller junto a la fábrica. |
| Estación de carga | Entregar 10 placas por cinta | Aparece una estación con su iluminación. |
| Sector de expansión | Entregar 20 placas por cinta | Se habilita un área adicional donde podés construir. |

**Producir** cuenta placas terminadas por la fundición. **Entregar por cinta**
cuenta las placas transportadas hasta un depósito; cargarlas a mano no cumple
ese requisito. El taller y la estación son cambios de escenario en esta pasada:
no reparan, no recargan una batería ni dan ventajas de producción. El sector de
expansión sí cambia la construcción: sus 36 celdas quedan disponibles al completar
el hito y su animación. El anexo está cruzando el portón frontal. También se
habilitan tres celdas centrales en el acceso para conectar ambos patios por cintas.
El suelo y el acceso peatonal están disponibles desde el inicio; lo que se
desbloquea es la construcción. Los hitos no gastan ni entregan materiales.

Los hitos no sustituyen el objetivo de la línea. El panel mantiene separados el
contenido actual de los depósitos y las entregas acumuladas por cinta. Desbloquear
la expansión no evita que tengas que conservar 20 placas almacenadas para
completar el objetivo. El avance del patio se incluye en el guardado manual.

## Construcción libre

| Selección | Construcción | Costo en chatarra |
| --- | --- | --- |
| B, luego 1 | Trituradora | 20 |
| B, luego 2 | Fundición | 25 |
| B, luego 3 | Depósito | 10 |
| B, luego 4 | Cinta recta | 2 |

La cuadrícula mide 2 metros por celda. Cada construcción ocupa una celda;
no se puede construir sobre el robot, chatarra, otras máquinas, obstáculos
ni fuera del patio habilitado. El sector adicional admite construcciones después
del tercer hito. Verde indica una colocación válida y rojo explica el problema.

Las conexiones son rectas: colocá las piezas en celdas vecinas, con la misma
orientación. La entrada está detrás y la salida delante, según la flecha.
Debe haber una cinta entre dos máquinas. Todavía no hay curvas ni ramificaciones.

Los depósitos nuevos reciben chatarra. Acercate y pulsá **G** para cambiar el
filtro entre chatarra, triturado y placas; el depósito debe estar vacío.
El depósito final de la línea de ejemplo ya está configurado para placas.

**X** desmonta la construcción cercana. Devuelve el costo pagado y todo el
contenido, incluido el material de una receta en curso. Si la mochila no tiene
espacio suficiente, no desmonta. Las cuatro máquinas de ejemplo son gratuitas:
devuelven sus materiales, pero no dan chatarra por su construcción.

## Recetas

| Máquina | Entrada | Salida | Duración |
| --- | --- | --- | --- |
| Trituradora | 2 chatarra | 2 triturado | 3 segundos |
| Fundición | 2 triturado | 1 placa | 4 segundos |

Cada procesadora tiene una entrada de 20 unidades y una salida de 20.
Cada depósito admite 100 unidades del recurso seleccionado. Cada cinta
transporta una unidad por vez y tarda 0,8 segundos en recorrer su tramo.

## Controles y guardado

| Tecla / gesto | Acción |
| --- | --- |
| WASD / Shift | Mover / caminar rápido |
| E / F | Recoger o cargar / retirar salida |
| I | Inventario |
| B / 1–4 / R | Construcción / selección / giro |
| Clic / clic derecho | Colocar / cancelar construcción |
| G / X | Filtro del depósito vacío / desmontar |
| Rueda / botón central y arrastrar | Zoom / desplazar cámara |
| Ctrl + clic derecho y arrastrar horizontalmente | Girar cámara alrededor del robot |
| Inicio | Restaurar encuadre, zoom y orientación |
| F5 / F9 | Guardar / cargar partida |
| Esc | Detener Play, según el control del editor |

F5 guarda la mochila, posición del robot, montones agotados, construcciones,
filtros, orientaciones, contenidos, progreso de las recetas y de las cintas,
y avance del objetivo. También guarda los hitos del patio y el tiempo restante
de una transformación en curso. F9 recupera ese guardado. El archivo queda en
`Saved/SaveGames/FactoryCtycoDemo_v1.sav`. No se carga automáticamente al
iniciar Play ni se guarda automáticamente al salir.

## Arte y límites de esta versión

La trituradora, fundición, depósito y chatarra usan los modelos entregados,
con geometría reducida para el juego y sus materiales de color, normales,
metal y rugosidad. Los originales están conservados en `SourceAssets/Factory/Originals`.

Hay una discrepancia entre algunos nombres y el contenido real de los GLB.
Mientras se confirma esa identificación, la cinta, el triturado que circula
y la placa mantienen una presentación independiente de esos archivos ambiguos.
La cinta ya utiliza el modelo biselado creado en Blender durante la primera
mejora estética; el triturado y la placa usan piezas simples. Las definiciones
editables de `/Game/FactoryCtyco/Factory` contienen las asignaciones actuales.
`Docs/factory_demo_bindings.json` conserva las asignaciones de la preparación
inicial. El robot y la arena anteriores no se sustituyeron por los GLB ambiguos.

Demo para un jugador, sin combate, simulación de energía, curvas de cinta ni
divisores. El nuevo sector construible pertenece a esta iteración de hitos.
La iteración pasó 20 grupos de comprobaciones jugables y de persistencia,
con procesamiento y transporte a velocidad nativa. El informe está en
`Docs/factory_site_playtest.json`: incluye conservación, conexión por cintas,
guardado durante una aparición, carga de formato v1, rechazo de datos inválidos
y salida segura del taller si el robot ocupa su huella durante la construcción.

Los resultados de la aceptación de la línea de producción se registran en
`Docs/factory_demo_playtest.json`; la prueba usa un guardado separado,
`FactoryCtycoDemo_AcceptanceOnly`, sin sobrescribir el del jugador.

## Cintas de la fábrica: esquina, largo, inclinación y altura (30/09)

- **Esquina**: `Cinta_Fabrica_Esquina` (definición `DB_BeltCorner`, modelo del usuario `esquinaCinta-complete.glb`
  adaptado por `Scripts/author_factory_belt_corner.py`: 140 cm de ancho, 30 de alto, entra en una celda). Entra por el
  medio del borde de atrás y sale por el medio del borde del costado, 90° a la derecha; **escala Y = −1 la hace doblar
  a la izquierda**. Está en (−600, 600) para ubicarla. También se construye en juego: modo construir, tecla 5.
- **Enganches**: ya no se mira la cuadrícula sino los bordes: una pieza le pasa material a la que tiene su entrada a
  menos de 50 cm de su salida (y a menos de 60 cm de altura). En la cuadrícula es lo mismo que antes (la celda de
  adelante, mirando para el mismo lado).
- **Largo**: escala X. Una cinta más larga tarda más (0,8 s cada 2 m).
- **Inclinación**: girarla en *pitch*; la carga sube o baja por ella.
- **Altura**: subirla. Debajo aparecen postes solos hasta el piso (`Supports`; `SupportMesh`, `SupportMaterial` —en las
  cintas de la fábrica, el acero de las cintas de carga—, `SupportWidth`, `SupportSpacing`), así se puede pasar por debajo.
- F5/F9 guarda también el giro completo y la escala de cada pieza (guardado versión 3; los viejos se siguen cargando).
- Código: `TurnDegrees` en `UFactoryBuildingDefinition`; `BeltLocalAt`, `InputPoint`/`OutputPoint`, `TravelSeconds`,
  `PlaceCargo`, `BuildSupports` en `AFactoryBuilding`; los postes los arma `Private/FactoryBeltSupports.h` (compartido
  con las cintas de carga). Respaldo: `Saved/Respaldos/2026-09-30_cinta_fabrica`.
- Colocar: `Scripts/apply_factory_belt_corner.py` (informe `Docs/factory_belt_corner.json`). Prueba en Play:
  `Scripts/playtest_factory_belts.py`: depósito → cinta estirada que sube 10° → esquina → cinta en altura → depósito
  (armada solo para la prueba en el piso del laboratorio). Pasó las 5 comprobaciones el 30/09
  (`Docs/factory_belts_play.json`).
