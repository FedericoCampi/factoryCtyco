# Recolección e inventario

Primer sistema jugable de recursos, integrado en `L_Recoleccion`.

- E recoge el montón cercano que aparece marcado en el suelo.
- I abre y cierra el inventario sin detener el movimiento.
- El robot puede llevar 200 unidades en total.
- Hay siete montones de 30 unidades de chatarra en el patio.
- El primer objetivo visible es reunir 30 unidades.
- El alcance es de 2 metros y los obstáculos bloquean la interacción.
- Si solo cabe una parte, el resto queda en el montón. Los montones agotados
  desaparecen durante esa partida y no vuelven a dar recursos.

WASD, Shift y los controles de cámara siguen disponibles. No hay salto.
Hacer clic dentro de Play para capturar las entradas del juego.

El inventario y el estado de los montones duran esta sesión de juego. Todavía
no hay guardado entre partidas; detener Play y volver a iniciarlo reinicia los recursos.
La construcción y el procesamiento son los siguientes sistemas pendientes.

Los montones actuales usan piezas de metal provisionales. Se podrán reemplazar
por el modelo final sin cambiar las cantidades ni las reglas de recolección.

## Contenido editable

- `/Game/FactoryCtyco/Resources/DA_Scrap`: nombre, identificador, color y futuro modelo
  del recurso. Si se asigna un `PickupMesh`, reemplaza las piezas provisionales.
- `FactoryInventory` en `BP_Robot1`: capacidad y operaciones reutilizables
  para agregar, consultar y retirar cantidades.
- `FactoryGathering` en `BP_Robot1`: alcance e interacción.
- Actores `Scrap_01` a `Scrap_07` en el nivel: cantidad y un identificador estable.
- `FactoryGatheringHUD`: contador, objetivo, panel de inventario y mensajes.

`gathering_build.json` y `gathering_playtest.json` registran la integración y
la prueba en Play, incluida la conservación de recursos al llenar el inventario.
`Scripts/playtest_gathering.py` reproduce la verificación.
