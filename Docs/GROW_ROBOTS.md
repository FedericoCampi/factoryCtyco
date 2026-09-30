# GROW: robots que aprenden del mundo

La iteración actual desarrolla la idea elegida: los robots interpretan lo que
encuentran al despertar. El orden de tus decisiones determina su oficio, los
niveles que alcanzan y las construcciones que aparecen en el mapa. Los seis
sistemas forman una red: todos aportan a otros y necesitan sus contribuciones
para evolucionar. Cada subida de nivel tarda **dos segundos** y las mejoras se
resuelven una detrás de otra. Es una partida corta de seis decisiones, inspirada
en la evolución por decisiones de los juegos GROW.

Abrí [`ABRIR_GROW.cmd`](../ABRIR_GROW.cmd) y pulsá **Play**. El mapa es
`/Game/FactoryCtyco/Maps/L_GrowRobots`. El escenario completo se genera al iniciar Play;
el editor muestra una plataforma de referencia antes de jugar.

La fábrica anterior sigue disponible en `/Game/FactoryCtyco/Maps/L_FactoryDemo` mediante
[`ABRIR_DEMO.cmd`](../ABRIR_DEMO.cmd). Conserva sus máquinas, recursos y guardado.

## Cómo jugar

Elegí una tarjeta con el mouse o su tecla. Cada sistema puede elegirse una sola
vez y consume un turno. La elección puede iniciar una reacción en cadena: esperá
a que terminen las mejoras y su animación antes de tomar otra decisión.

La interfaz muestra el origen y el destino de la reacción, el aporte que recibe
el sistema, los segundos que faltan y las mejoras pendientes. La tarjeta que
está por subir de nivel se destaca con una barra de progreso. Pasá el cursor
por cualquier tarjeta para ver sus conexiones y requisitos. La fila sobre las
tarjetas registra el orden elegido; el panel derecho también muestra el oficio
previsto o actual y el nivel de la colonia.

| Tecla | Decisión | Efecto principal |
| --- | --- | --- |
| **1** | Reciclaje | Aporta piezas recuperadas y un ejemplo de construcción. |
| **2** | Agua | Aporta refrigeración y riego; ofrece un ejemplo de cuidado. |
| **3** | Transporte | Distribuye suministros y ofrece un ejemplo de reparto. |
| **4** | Energía | Suministra electricidad. |
| **5** | Hábitat | Aporta filtrado natural, refugio y mantenimiento. |
| **6** | Despertar | Activa los robots y fija su oficio. |

**Retroceso / Backspace** deshace la última decisión; **R** reinicia la secuencia.
También hay botones para ambas acciones y funcionan incluso mientras hay
mejoras pendientes. Deshacer cancela la cola actual y restaura el estado completo
que corresponde a las decisiones anteriores, con sus mejoras ya resueltas: no
repite las esperas antiguas. También permite volver hasta antes de despertar a
los robots. Reiniciar cancela todas las mejoras pendientes y vuelve al comienzo.

La **rueda** acerca o aleja la cámara. Mantené el **botón central** y arrastrá para
desplazar el encuadre; mantené **Ctrl + botón derecho** y arrastrá horizontalmente
para orbitar. **Inicio / Home** restaura la vista. El jugador observa el diorama:
los robots se mueven y trabajan automáticamente.

## El orden importa

Al elegir **Despertar**, se toma la decisión más reciente entre **Reciclaje**,
**Agua** y **Transporte**. Energía y Hábitat no reemplazan ese contexto.

| Último ejemplo antes de despertar | Oficio | Apoyo para completar su evolución | Obra final |
| --- | --- | --- | --- |
| Reciclaje | Constructores | Transporte | Taller para la colonia. |
| Agua | Cuidadores | Hábitat | Jardín y refugio verde. |
| Transporte | Transportistas | Reciclaje | Red de reparto. |

El oficio queda fijado durante esa secuencia. Si despertás sin ninguno de esos
tres ejemplos, aparecen aprendices: agregar los ejemplos después no les asigna
un oficio. Podés deshacer hasta antes del despertar y cambiar el orden.

Los robots empiezan en **nivel 1** al despertar. Su sistema principal es el que
definió el oficio: Reciclaje, Agua o Transporte. Para llegar al **nivel 2** necesitan
un oficio, Energía en nivel 1 y ese sistema principal en nivel 2. Para llegar al
**nivel 3** necesitan Energía en nivel 2, su sistema principal en nivel 2, el apoyo
de su oficio en nivel 2 y Hábitat instalado. El máximo es 3 y hacen falta, como
mínimo, **dos decisiones después de Despertar**.

Cada decisión instala el sistema nuevo en nivel 1 y ofrece **una oportunidad de
subir un nivel a cada sistema elegido anteriormente**. El sistema recién elegido
queda en nivel 1 durante ese turno. Si una mejora habilita a otro sistema, ese
sistema puede continuar la reacción; ninguno puede subir dos niveles en el mismo
turno. Cuando no quedan mejoras posibles, hace falta otra decisión: esperar
indefinidamente no genera oportunidades adicionales.

## Red de requisitos

Los números indican el **nivel mínimo** requerido. Para alcanzar un nivel hace
falta cumplir todos los requisitos de su celda. La tarjeta **Despertar** muestra
el nivel de los robots.

| Sistema | Para llegar al nivel 2 | Para llegar al nivel 3 |
| --- | --- | --- |
| Reciclaje | Energía 2 + Agua 1 | Transporte 2 + Robots 2 |
| Agua | Energía 1 | Hábitat 2 + Transporte 1 |
| Transporte | Energía 1 + Reciclaje 1 | Robots 2 + Hábitat 1 |
| Energía | Agua 1 + Reciclaje 1 | Transporte 2 + Robots 2 |
| Hábitat | Agua 2 + Reciclaje 1 | Robots 2 + Transporte 2 |
| Robots | Energía 1 + sistema principal 2 | Energía 2 + sistema principal 2 + apoyo del oficio 2 + Hábitat 1 |

Por ejemplo, Agua permite que Hábitat se desarrolle; un Hábitat desarrollado
puede aportar filtrado para mejorar el Agua, junto con Transporte. Son relaciones
de ida y vuelta entre sistemas con distintos requisitos de nivel, de modo que
el orden sigue siendo decisivo.

Cada mejora de la cola tiene su propia espera de **2,0 segundos**. Primero se
completa una, cambia el nivel visible y después comienza la siguiente. Durante
la espera se identifica el aporte y el sistema destinatario. Por ejemplo, si
primero instalás Energía y Reciclaje en nivel 1 y luego elegís Agua, el agua
permite que Energía llegue a nivel 2 tras dos segundos. Esa mejora habilita
Reciclaje 2, que llega después de otros dos segundos.

Para ajustar el ritmo del prototipo, el actor `Grow_Evolution` expone
`UpgradeDelaySeconds`.

La secuencia termina después de las seis decisiones y de resolver sus mejoras
y animaciones. El resultado depende de
haber llevado la colonia al nivel 3, no de maximizar necesariamente todas las
tarjetas. Si queda incompleta, el panel muestra una pista para revisar el orden.

<details>
<summary>Ver tres secuencias de ejemplo que completan un oficio (soluciones)</summary>

Todas usan los mismos seis sistemas una sola vez:

- **Constructores:** Energía → Reciclaje → Despertar → Agua → Transporte → Hábitat.
  Teclas: **4, 1, 6, 2, 3, 5**.
- **Cuidadores:** Energía → Agua → Despertar → Reciclaje → Hábitat → Transporte.
  Teclas: **4, 2, 6, 1, 5, 3**.
- **Transportistas:** Energía → Transporte → Despertar → Reciclaje → Agua → Hábitat.
  Teclas: **4, 3, 6, 1, 2, 5**.

Como comparación, empezar por Despertar deja una colonia de aprendices aunque
después elijas el resto de los sistemas. Estas rutas son ejemplos, no las únicas
combinaciones posibles.

</details>

## Alcance de esta iteración

Incluye una colonia de robots, tres oficios, evoluciones visibles del escenario,
animaciones de trabajo y accesorios propios creados en Blender. Los accesorios
editables están en
[`SourceAssets/GrowRobots/GrowRobotAccessories.blend`](../SourceAssets/GrowRobots/GrowRobotAccessories.blend);
sus exportaciones se importan en `/Game/FactoryCtyco/Grow/Models`.

Los robots recorren conexiones entre sistemas y representan el traslado de sus
aportes. Estas contribuciones habilitan mejoras; todavía no son un inventario
que se produzca, almacene o consuma. Los recorridos tampoco usan navegación
autónoma para evitar obstáculos y pueden atravesar piezas del escenario en esta
iteración.

Todavía no hay otras criaturas. `UGrowSpeciesDefinition` separa la apariencia de
las reglas: `/Game/FactoryCtyco/Grow/DA_RobotSpecies` define malla, animaciones de reposo y
caminata, escala, orientación y accesorios por oficio. Esa definición permite
preparar otra apariencia y animaciones sin reescribir el ciclo de decisiones.
Las reglas de oficio y evolución son compartidas actualmente; no hay habilidades
o reglas propias de otras especies implementadas.

Esta partida de seis turnos **no guarda la sesión**. Salir de Play y volver a
entrar empieza una secuencia nueva. Deshacer funciona dentro de la sesión. El
guardado F5/F9 de la fábrica anterior pertenece a aquella demo.

## Estado de verificación

La nueva iteración pasó **14 grupos en 63,1 segundos** dentro de Unreal Engine
5.6.1. Se comprobaron los aportes entre los seis sistemas, la cadena real
Agua → Energía 2 → Reciclaje 2, ausencia de subidas instantáneas y una espera
medida de **2,0 segundos para cada mejora**. También se verificaron deshacer y
reiniciar durante una reacción, entradas por mouse y teclado, las tres profesiones,
reproducción determinista y que el resultado espere hasta terminar la cola.

Informe actual: [`grow_interactions_playtest.json`](grow_interactions_playtest.json).
Capturas: [reacción en curso](grow_reaction.png),
[constructores conectados](grow_connected_builder.png),
[cuidadores conectados](grow_connected_caretaker.png) y
[transportistas conectados](grow_connected_courier.png).

Otras **3 comprobaciones de actividad visual** verificaron movimiento real del
pulso durante la espera, viajes completos de los tres robots entre estaciones
y carga visible durante el traslado. La captura de reacción se revisó con
las instalaciones ya formadas y 1,4 segundos restantes para la mejora.
Informe: [`grow_activity_playtest.json`](grow_activity_playtest.json).
En total, esta iteración pasó **17 grupos de comprobaciones**.

Como antecedente, la versión anterior pasó **13 grupos en 55,5 segundos** dentro
de Unreal Engine 5.6.1: clics y teclado, bloqueo durante animaciones, decisiones
únicas, secuencias con distintos resultados, movimiento, deshacer y reinicio.
Ese resultado no valida por sí solo las reglas y los tiempos nuevos.

Informe publicado de la versión anterior:
[`grow_evolution_playtest.json`](grow_evolution_playtest.json).
Capturas de esa versión: [constructores](grow_builder.png),
[cuidadores](grow_caretaker.png), [transportistas](grow_courier.png) y
[vista a 1280×720](grow_1280x720.png).

Es un prototipo para iterar sobre las reglas y la presentación. Los hitos del
mundo dependen de las decisiones, los niveles y sus conexiones.

Informes de preparación:
[`grow_evolution_build.json`](grow_evolution_build.json) y
[`grow_robot_accessory_import.json`](grow_robot_accessory_import.json).
La verificación de tiempos e interacciones se ejecuta con
[`Scripts/playtest_grow_interactions.py`](../Scripts/playtest_grow_interactions.py).
Los viajes y pulsos se comprueban con
[`Scripts/playtest_grow_activity.py`](../Scripts/playtest_grow_activity.py).
La prueba original general está en
[`Scripts/playtest_grow_evolution.py`](../Scripts/playtest_grow_evolution.py).
El mapa se prepara con [`Scripts/build_grow_robots.py`](../Scripts/build_grow_robots.py);
este guarda una copia previa del mapa GROW antes de reconstruirlo. Las piezas
se crearon por el MCP local de Blender y se importaron mediante el MCP de Unreal.
