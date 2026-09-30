# Máquina de despacho — 27 de septiembre de 2026

Modelo del usuario (`3D assets/GLBs/despachoMachine.glb`), decorativo y estático.
Colocado en `L_FactoryDemo` como `Despacho_Machine` (StaticMeshActor, carpeta `Environment`),
4 m al este de `PlayerStart_Robot1`, para que el usuario lo ubique.

- Asset: `/Game/FactoryCtyco/Environments/DespachoMachine/SM_DespachoMachine`: 3 × 4,52 × 1,73 m,
  ~238 000 caras (de 698 000). Dos colisiones UCX: el cuerpo (alto completo) y la cinta
  (hasta las barandas, 77 cm).
- Cinta alargada 2,03 m (`EXTEND_M` en el script de Blender): se corta entre dos rodillos y se
  repite cuatro veces un tramo de 7 rodillos, sin estirar la textura. El origen queda en el centro de
  la máquina sin alargar, así cambiar el largo no mueve el cuerpo.

- Hay una segunda copia puesta por el usuario, `Despacho_Machine2`; el import reasigna la malla a
  todos los actores `Despacho_Machine*`.

- Rodillos que giran: los del modelo vienen pegados a la malla, así que se les pusieron encima 41 tubos
  reales (`find_rollers`/`add_rollers` en el script de Blender) con la ranura `M_Rodillo`. En Unreal usa
  `M_DespachoRodillo`: franjas claras/oscuras que dan la vuelta al tubo; el parámetro `Velocidad`
  (1,5 vueltas/s, negativo invierte) ajusta el giro. Dentro de la cámara el piso son tablones fijos.

Detrás, el muro oeste del estacionamiento tiene una abertura para que la máquina parezca
incrustada y alimentada desde afuera: ver [ESTACIONAMIENTO.md](ESTACIONAMIENTO.md).

Regenerar:
1. `blender -b --factory-startup -P Scripts/author_despacho_machine.py` (ancho y reducción al inicio).
2. Con el editor cerrado: `UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/import_despacho_machine.py -unattended -nosound`
   (informe: `Docs/despacho_import.json`). Si el actor ya existe solo cambia la malla y conserva la posición.
   Borra el asset antes de importar: reimportar encima dejaba la colisión vieja.
   Con el editor abierto no lanzar otro: correr el mismo script por MCP (`execute_python` con
   `runpy.run_path`); usa el nivel abierto, guarda los assets y deja el nivel para guardar a mano.

No se probó todavía en Play.
