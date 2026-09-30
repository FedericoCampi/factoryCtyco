# Controles de cámara

- Rueda hacia adelante: acercar.
- Rueda hacia atrás: alejar.
- Mantener el botón central (rueda) y arrastrar: desplazar el encuadre.
- Mantener clic derecho y arrastrar a izquierda/derecha: girar alrededor
  del eje vertical del personaje (desde el 27/09 ya no hace falta Ctrl).
- Inicio/Home: volver a centrar la cámara y restaurar el zoom y orientación iniciales.
- WASD: mover el robot. Shift mantenido: caminar rápido. Salto desactivado.

En Play, hacer clic dentro de la vista del juego para capturar el mouse.
Shift+F1 libera el mouse para volver a usar el editor.

La cámara conserva su inclinación isométrica al orbitar; el movimiento vertical
del mouse no cambia su altura. Durante la construcción, arrastrar con clic derecho gira
la cámara sin cancelar; un clic derecho corto, sin arrastrar, cancela (al soltar el botón).
WASD se adapta a la orientación actual de la cámara.

La cámara acompaña al robot con el desplazamiento elegido. El giro, el zoom y
el regreso al centro son suaves. La distancia de cámara va de
1100 a 9000 cm (antes 3800; ampliado el 27/09) y el desplazamiento se limita a 1250 cm alrededor del personaje.

Los valores se pueden editar en el componente `FactoryCameraControls` de
`/Game/FactoryCtyco/Blueprints/BP_Robot1`. El código está en `Plugins/FactoryCtycoRuntime`.

`camera_build.json` y `camera_playtest.json` registran la integración inicial de
la cámara. `factory_controls_playtest.json` verifica los controles actuales con
Shift y sin salto, junto con el zoom y el regreso al encuadre inicial.
`camera_orbit_playtest.json` registra la prueba de órbita en `L_FactoryDemo`.
El 18 de septiembre se verificaron diez grupos de comprobaciones en Play con
eventos simulados de mouse y teclado: ambos Ctrl, giro horizontal, pivote en el
personaje incluso después de desplazar la cámara, construcción, WASD, zoom y
restauración. El plugin compiló para Editor, Development y Shipping.
