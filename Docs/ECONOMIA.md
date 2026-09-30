# Dinero y botón de silencio — 29 de septiembre de 2026

## Dinero
- **Arriba a la izquierda**, siempre visible: una pastilla con una moneda y el dinero de la fábrica («$ 1.200»). Cuando
  cambia, la pastilla rebota y el número se pinta un momento de verde (ganancia) o de rojo (gasto). Al lado aparece un
  «+$ 1.200» o un «−$ 800» que sube y se desvanece.
- **Se empieza con $ 0.**
- **Ingresos**: cada paquete entregado paga **$ 60**. Se cobra cuando el camión sale por la barrera, igual que cuenta la misión.
- **Contratar cuesta** según el puesto. Hoy hay un solo puesto: el encargado de barrera, a **$ 800**.
  - El botón dice «CONTRATAR · $ 800».
  - Si no alcanza la plata, queda gris y dice «Te faltan $ X para contratarlo».
  - Se paga al contratar, en el panel de la cabina o en la pestaña de contratar del panel de información (tecla I).
- Todavía no hay nada para comprar. El botón «MEJORAR CABINA» sigue diciendo «Las mejoras llegan pronto».
- **Precios**: Edit → Project Settings → Game → **Economía de la fábrica**. Ahí se cambian el dinero inicial
  (`StartingMoney`), el pago por paquete (`PricePerPackage`) y el costo de cada puesto (`HireCosts`, por nombre de puesto
  como en el punto de contratación). Se guardan en `Config/DefaultGame.ini`.
- Código: `UFactoryEconomySubsystem` y `UFactoryEconomySettings` (`FactoryEconomy.h`). `Spend` no cobra si no alcanza.
  Las entregas llaman a `Earn` desde `UFactoryMissionSubsystem::AddDelivered`, y `UFactoryStaffSubsystem::Hire` cobra el
  puesto. El HUD lo dibuja en `DrawMoney` (`Private/FactoryGuideHUD.cpp`).
- El dinero no se guarda con F5/F9: ese guardado sigue siendo el de la demo de reciclaje vieja.

## Botón de silencio
Está al lado del dinero y siempre visible: una pegatina redonda con un parlante. Un clic silencia todo el juego, y el
botón se pone rojo con el parlante tachado. Otro clic devuelve el sonido. Hace lo mismo que la tecla **M** y la opción
del panel de información.

El cartel de eventos y la tarjeta de la misión bajaron para dejarle arriba el lugar al dinero.

Pruebas en Play: `playtest_employee_scene.py` verifica que se empiece con $ 0, que sin plata no se pueda contratar y que
contratar cueste $ 800. `playtest_mission_guide.py` verifica que 20 paquetes paguen $ 1.200.
