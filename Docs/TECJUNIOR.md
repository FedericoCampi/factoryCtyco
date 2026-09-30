# TecJunior, nuevo personaje jugable — 23 de septiembre de 2026

Reemplaza a Robot1 en la demo de la fábrica (`BP_FactoryRobot`). Los controles,
la cámara, la recolección y la construcción no cambian.

- Fuente: `3D assets/GLBs/tecJunior.glb`, en pose T, copiada a `SourceAssets/TecJunior`.
- Malla de juego: 83 897 triángulos, reducida desde 699 149, con 1,70 m de altura y los 4 mapas de textura originales.
- Esqueleto de 22 huesos, igual que Robot1: raíz, pelvis, columna, pecho, cuello,
  cabeza, clavículas, brazos, antebrazos, manos, muslos, piernas, pies y dedos del pie.
  Las articulaciones se midieron sobre la malla.
- Pesos automáticos: se calcularon sobre una copia cerrada (voxel) y se transfirieron
  al modelo, porque el original tiene 3861 piezas sueltas. Ningún vértice quedó sin peso.
- Animaciones con mecánica de paso humano (versión 2, pedida porque la primera se movía como robot):
  - reposo de 4 s, con respiración y cambio de peso;
  - caminata de 0,67 s: talón, pie plano, despegue con la punta, cadera que gira y
    cae del lado libre, hombros que compensan y brazos con un leve retraso;
  - carrera de 0,6 s, con fase en el aire y codos doblados;
  - pose en el aire.
  `BS_TecJunior_Locomotion` mezcla reposo (0), caminata (140 cm/s) y carrera (268 cm/s).
- Velocidades del juego ajustadas al paso para que los pies no patinen: caminar
  140 cm/s (antes 190) y Shift 268 cm/s (antes 300). Se cambian en `RobotLocomotion`
  (`WalkSpeed` y `FastWalkSpeed`) dentro de `BP_FactoryRobot`.
- Cápsula: 35 cm de radio y 85 cm de semialtura.

Assets: `/Game/FactoryCtyco/Characters/TecJunior`. Robot1 se conserva intacto y
`/Game/FactoryCtyco/Factory/BP_FactoryRobot_Robot1Backup` guarda el Blueprint anterior.

Regenerar:
1. `blender -b --factory-startup -P Scripts/author_tecjunior_rig.py`
   (genera los FBX, `TecJunior_Rig.blend`, `rig_report.json` y las vistas previas `preview_*.png`)
2. En el editor: ejecutar `Scripts/import_tecjunior.py` (informe: `Docs/tecjunior_import.json`).

Verificado en Play: camina a 140 cm/s, corre hasta 268 cm/s con Shift y se detiene al soltar. Dedos, cara, pelo y ropa no tienen huesos propios.

28/09: tres animaciones más para cargar una caja con las dos manos (`A_TecJunior_CarryIdle/Walk/Run`, `BS_TecJunior_Carry`),
con los brazos por IK sobre los costados de la caja. Ver [CAJAS_DESPACHO.md](CAJAS_DESPACHO.md).

Velocidades (28/09, a pedido): +100 cm/s cada una. Caminar 240 cm/s (antes 140) y Shift 368 cm/s (antes 268),
en `RobotLocomotion` de `BP_FactoryRobot` (`Scripts/set_player_speed.py`, informe `Docs/player_speed.json`).
Por encima de 268 cm/s la animación de carrera se acelera para acompañar el paso.
