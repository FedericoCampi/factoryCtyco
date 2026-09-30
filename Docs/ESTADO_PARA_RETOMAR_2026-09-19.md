# Estado para retomar — 19 de septiembre de 2026

El usuario pidió actualizar el estado y las ideas para continuar después.
El desarrollo queda pausado por su pedido. Este documento prevalece sobre el
checkpoint del 14 de septiembre. Las ideas del plan son propuestas, no trabajo
autorizado para ejecutar durante la pausa.

## Dirección confirmada

Continuar mejorando poco a poco la **fábrica original con el robot**. El
experimento GROW se conserva aparte: no sustituir el juego principal por él.
Interesa que los sistemas se relacionen, que el escenario evolucione y que las
mejoras se vean mediante animaciones con unos segundos de demora. Habrá otras
criaturas más adelante, pero todavía no tienen un papel acordado en la fábrica.

El usuario eligió la opción de transformar el escenario con los logros de
producción. Esa primera iteración está implementada. Aún falta su devolución
después de jugarla; la validación técnica no equivale a aprobación de la experiencia.

## Cómo abrir lo que existe

- Proyecto: `C:\Users\Usuario\Desktop\unreal Projects\FactoryCtyco`.
- Unreal Engine 5.6.1; entrada: [`ABRIR_DEMO.cmd`](../ABRIR_DEMO.cmd), luego Play.
- Mapa principal y de inicio: `/Game/FactoryCtyco/Maps/L_FactoryDemo`.
- La partida arranca de cero hasta cargar explícitamente con F9; F5 guarda.
- Slot del jugador: `Saved/SaveGames/FactoryCtycoDemo_v1.sav`. Al comprobar este
  cierre no existía ese archivo. Las pruebas usaron slots separados. Este
  checkpoint documenta el proyecto y no crea una partida completada del jugador.

No regenerar la demo para simplemente retomarla. `build_factory_demo.py` vuelve
a construir contenido de la preparación original; no es el iniciador de la versión actual.

## Estado jugable

El robot se controla con WASD y Shift, recoge con E y tiene mochila de 200
unidades. La cámara permite zoom, desplazamiento y giro. B abre construcción;
1–4 seleccionan, R gira, clic coloca y clic derecho cancela. E carga, F retira,
G cambia el filtro del depósito vacío y X desmonta devolviendo costo y contenido.

La línea funciona con depósitos, trituradora, fundición y cintas rectas:
2 chatarra → 2 fragmentos en 3 segundos; 2 fragmentos → 1 placa en 4 segundos.
Las cintas transportan una unidad por tramo en 0,8 segundos. El objetivo sigue
exigiendo 20 placas almacenadas y 20 entregas por cinta.

La automatización actual corresponde a máquinas y cintas. **El robot todavía
no recoge, navega ni abastece depósitos por su cuenta.** No hay sistema de
batería, reparación, combate, cintas curvas ni divisores.

La mejora estética anterior añadió cintas y piezas biseladas creadas en Blender,
animaciones de maquinaria, indicadores de actividad, materiales, iluminación y HUD.

## Última iteración terminada

| Hito | Requisito | Resultado |
| --- | --- | --- |
| Taller | 5 placas producidas | Aparece el banco de mantenimiento. |
| Estación de carga | 10 placas entregadas por cinta | Aparece la estación iluminada. |
| Ampliación | 20 placas entregadas por cinta | Se habilitan 36 celdas y 3 celdas de conexión. |

Los hitos se resuelven en orden, con una aparición animada de dos segundos cada
uno. Sus huellas cambian de color y muestran un barrido durante la construcción.
No consumen ni conceden materiales, y no retroceden al retirar placas.

El taller y la estación son decorativos en esta versión. La ampliación es
funcional: se puede construir en ella y conectarla con el patio original por
cintas. Está cruzando el portón frontal; el suelo y el acceso peatonal existen
desde el inicio. Si el robot ocupa la huella del taller durante su aparición,
la colisión espera hasta que salga.

F5/F9 conserva los hitos y el tiempo pendiente. El formato interno del guardado
es versión 2, manteniendo el nombre del slot. Los guardados de versión 1
reproducen los hitos que les corresponden por sus contadores.

## Segundo escenario: decisión visual pendiente

El usuario pidió un escenario diferente que después se conectará con este.
Se propuso una instalación botánica futurista. El primer resultado generado
tenía invernaderos, agua, plantas y robot; el usuario lo corrigió porque necesita
**una imagen de la arquitectura base para convertir a 3D**, con la presentación
de su escena actual y sin objetos que puedan añadirse después.

Usar una captura del escenario actual como referencia. Pedir una maqueta
aislada, completa, con cámara ortográfica elevada, fondo neutro, piso plano,
paredes bajas y acceso conectable. Sin techo que oculte el interior, máquinas,
robot, criaturas, vegetación, agua, utilería ni entorno de fondo.
El [prompt corregido](PROMPT_INVERNADERO.md) está guardado. La temática y la
imagen definitiva aún deben revisarse; **no hay segundo mapa importado ni conexión creada**.
El anexo implementado pertenece a la fábrica original, no es ese segundo mapa.

## Verificación y archivos de referencia

- [Prueba actual](factory_site_playtest.json): `passed: true`, 20 grupos, 138,8
  segundos combinados, procesamiento y transporte a velocidad nativa. Incluye
  conservación, construcción y reembolso, entrega por el corredor, guardado
  durante una aparición, migración v1, rechazo de datos inválidos y taller ocupado.
- Se comprobaron 198 puntos de suelo y el recorrido físico por el portón.
- La prueba continuó en una segunda sesión corta después de corregir el acceso
  del script a campos protegidos del SaveGame; el informe conserva `prior_runs`.
- [Vista general](factory_site_completed.png) y [detalle de la iteración](EVOLUCION_FABRICA_2026-09-19.md).
- Compilación Editor instalada: `Saved/VisualPolishWork/Build-20260919-214332-319`.
  Es la compilación verificada de estos cambios; no se verificó un nuevo paquete Shipping.
- Código principal: `FactoryDemo.h/.cpp`, `FactoryDemoHUD.cpp`,
  `FactorySiteLandmark.h/.cpp` en `Plugins/FactoryCtycoRuntime/Source/FactoryCtycoRuntime`.
- Fuentes Blender: `SourceAssets/Factory/SiteProgress`; importación y mapa:
  `Scripts/import_factory_site_assets.py` y `Scripts/build_factory_site.py`.
- El informe `factory_site_build.json` identifica el respaldo de la última
  aplicación del anexo. El respaldo anterior a la primera aplicación está en
  `Saved/VisualPolishWork/20260920-004023-413390Z`.
- GROW sigue disponible con `ABRIR_GROW.cmd` y su [documentación separada](GROW_ROBOTS.md).

No hay Unreal Editor, compilación ni prueba del agente en ejecución al cierre.
La sesión dedicada de Blender MCP seguía abierta (PID 31628 al comprobarla;
verificar el proceso al retomar, no asumir que ese PID siga siendo válido).
Conexión local y reinicio documentados en [BLENDER_MCP_LOCAL.md](BLENDER_MCP_LOCAL.md).
No se modificó esa sesión durante esta actualización documental.

## Próxima sesión

1. Leer este checkpoint y abrir la fábrica existente. Recoger las observaciones
   del usuario sobre la última iteración antes de ampliar el alcance.
2. Elegir una sola mejora pequeña del [plan actualizado](PLAN_DEL_JUEGO.md).
   Recomendación: usar el taller para ordenar una entrega única de chatarra
   entre dos depósitos; convertirla en rutina repetible en una iteración posterior.
3. Continuar con Unreal y Blender MCP cuando se necesite código, escena o arte.
4. Mantener separados el avance jugable de la fábrica y la preparación de la
   arquitectura del segundo escenario hasta disponer de una base 3D aprobada.

No hace falta recompilar ni repetir las pruebas sin nuevos cambios o un problema concreto.
