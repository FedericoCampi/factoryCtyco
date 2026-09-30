# Intro, primera misión guiada y contorno de lo clickeable — 29 de septiembre de 2026

## Intro y misión 1
Al pulsar Play en `L_FactoryDemo`, la pantalla oscurecida muestra la historia en tres tarjetas: la fábrica cerró en la
pandemia, hoy vuelve a abrir y vos sos el gerente. Después aparece el briefing «MISIÓN 1 · Reabrir el despacho» con
los pasos. **Espacio, Enter o clic** avanza; **Tab** salta la intro. Mientras se muestra, el personaje no se mueve.

Después, arriba a la izquierda (al lado del cartel de eventos), una tarjeta muestra el paso actual. Una **flecha naranja
grande** rebota sobre el objetivo. Si el objetivo queda fuera de pantalla, una flecha en el borde lo señala con la
distancia. Cada paso cumplido muestra un tilde verde y aparece el siguiente:

1. **Andá al despacho**: la flecha está sobre el ascensor de la recepción (`Ascensor_Empleados`; hasta el 30/09 iba sobre la puerta, `Guia_PuertaAscensor`).
   El ascensor (`Ascensor_Empleados`) está detrás de la puerta doble de la sala. En el panel del ascensor titila el piso **DESPACHO** (antes
   «ESTACIONAMIENTO»). Se cumple al llegar a `Ascensor_Estacionamiento`.
2. **Abrí el portón de camiones**: flecha sobre la botonera de la columna de `Porton_Camiones`. Se cumple cuando el
   portón quedó del todo arriba y los camiones pueden entrar (agregado el 29/09 a pedido).
3. **Encendé la cinta de despacho** (flecha en `Botonera_Cinta1`).
4. **Agarrá una caja** (flecha en `Despacho_Cajas`).
5. **Cargá la caja en la cinta del camión** (flecha en `Cinta_Carga3`).
6. **Despachá 20 paquetes**: sin flecha; la tarjeta muestra una barra de progreso.

Actor: `Guia_Mision` (clase C++ `AFactoryGuide`, carpeta Gameplay). Los textos de las tarjetas (`Slides`), la misión
(`MissionKicker`, `MissionTitle`, `MissionBody`) y los pasos (`Steps`: título, pista, `ArrowTarget`, `Goal`,
`GoalActor`, `Radius`, `ElevatorStop`; `Goal` puede ser Reach, OpenGate, SwitchOnBelt, CarryBox, LoadBox o Deliver) se editan en el panel de detalles. `bSkipIntro` salta la intro para probar.
Flecha: `ArrowHeight`, `ArrowScale`, `ArrowColor`; material `/Game/FactoryCtyco/UI/M_FlechaGuia`.
Dibujo en el HUD: `Private/FactoryGuideHUD.cpp`, con los ayudantes de `Private/FactoryHudDraw.h` (antes estaban
dentro de FactoryInfoPanel.cpp).

## Contorno de lo clickeable
Al pasar el mouse por algo que responde al clic, se remarca su contorno en naranja y el cursor pasa a ser una mano:
- los personajes (clic: la cámara los sigue);
- la cabina de la barrera (clic: su panel);
- el cartel rojo «CINTA LLENA» (clic: su detalle).

`UFactoryHoverComponent` (lo agrega `UFactoryGatheringComponent` al jugador) activa el custom depth de las mallas bajo
el mouse. El post-proceso `/Game/FactoryCtyco/UI/M_ContornoClic` (parámetros `Color` y `Ancho` en px), puesto en la cámara del
jugador, dibuja el borde y un leve tinte encima. Para sumar algo clickeable nuevo, agregarlo en
`UFactoryHoverComponent::FindClickable`, con el mismo orden que `UFactoryDemoComponent::Click`.

## Regenerar y probar
- Sin editor: `Scripts/build_runtime_visuals.ps1 -Install` y después `Scripts/run_mission_guide_setup.py` con
  `-ExecutePythonScript` (materiales: `make_guide_materials.py`; actor y pasos: `apply_mission_guide.py`,
  idempotente; informes `Docs/guide_materials.json` y `Docs/mission_guide.json`).
- Prueba en Play: `Scripts/playtest_mission_guide.py` (lanzador con `-ExecCmds="py …"`, ruta sin espacios).
  Pasó las 14 comprobaciones el 29/09: `Docs/mission_guide_play.json`.
  Sin capturas: el contorno se verificó por su configuración (componente y post-proceso en la cámara), no a la vista.
