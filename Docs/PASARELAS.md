# Pasarelas caminables y arreglos de cintas — 3 de octubre de 2026

## Pasarelas
Dos modelos del usuario (`3D assets/GLBs`), caminables como `Escalera_Plataforma` (chocan con su propia malla,
*complex as simple*):
- `Pasarela_Recta` (`SM_PasarelaRecta`, de «Pasarela industrial modular con barandillas de malla»): 9,9 × 2,5 m.
- `Pasarela_L` (`SM_PasarelaL`, de «Pasarela en L con barandillas interiores»): 5,3 × 5,4 m.

Escala: la baranda queda a 1 m sobre el piso de la pasarela; el piso está a ~0,4 m sobre la base del modelo. Se
pusieron al lado de la plataforma, con el piso a la altura del de ella (204 cm), en la carpeta Fabrica, para que el
usuario las acomode. Assets: `/Game/FactoryCtyco/Environments/Pasarelas/Recta` y `/L` (una carpeta cada una: las dos
traen `Image_0..3` y `Material_0` y se pisarían).
Regenerar: `blender -b --factory-startup -P Scripts/author_pasarelas.py`, después `Scripts/import_pasarelas.py` en el
editor (o `Scripts/run_pasarelas_y_cintas.py` sin editor abierto). Si ya existen, solo se cambia la malla.

## Pasarela en L a medida (`AFactoryWalkwayL`)
Desde el 03/10 `Pasarela_L` no es una malla fija: es un `AFactoryWalkwayL` (C++, `FactoryWalkway.h`) armado con tres
piezas cortadas del modelo (`SM_PasarelaPiso`, `SM_PasarelaBaranda`, `SM_PasarelaPoste`, en `Pasarelas/Modular`, con
colisión de caja). Brazo A a lo largo de +X y brazo B a lo largo de +Y desde la esquina de afuera.
- **Manijas** (rombos en el viewport): una en el medio de cada una de las cuatro barandas (arrastrarla de costado mueve
  esa baranda y el piso se ensancha o angosta) y una en la punta de cada brazo (lo alarga o acorta). Mínimo 60 cm entre
  barandas de un brazo.
- En Detalles: `OuterA`/`InnerA` (Y de las barandas del brazo A), `OuterB`/`InnerB` (X de las del brazo B), `EndA`,
  `EndB`, y `bOuterRailA`… para apagar una baranda (unirla a una plataforma). Postes cada ~1,5 m, en puntas y esquinas.
- Piezas: `Scripts/author_pasarela_modular.py` (Blender); en Unreal `Scripts/import_pasarela_modular.py`.
- Prueba: `Scripts/playtest_pasarela_modular.py` → `Docs/pasarela_modular_play.json` (manijas, apoyarse en el codo y
  en el brazo B, la baranda frena; pasó 7/7).

## Pasarelas rectas a medida (`AFactoryWalkwayStraight`)
Todas las `Pasarela_Recta*` (antes malla fija) se arman con piezas de su propio modelo (`Pasarelas/Modular/Recta`):
`LeftRailY` / `RightRailY` (Y de las barandas), `StartX` / `EndX` (puntas), `bLeftRail` / `bRightRail`; manijas en el
medio de cada baranda y en cada punta. Clase base común con la L: `AFactoryWalkway` (`FactoryWalkway.h`).

## Cintas
- `Cinta_Fabrica_Esquina2` (primera curva de la línea del cuarzo) tenía el sentido al revés: la piedra quedaba al
  final de `Cinta_Cuarzo_Triturar3`. Ahora recorre la misma curva al revés (girada 90° y espejada), en el mismo lugar.
- `Cinta_Puente1` y `Cinta_Puente1_Curva` siguen bloqueadas (`Bloqueado` + `Camion2`): son la mejora del camión 2.
  (El 03/10 se desbloquearon por error y se volvieron a bloquear.)
Script: `Scripts/apply_fix_cintas_curva_y_puente.py` (informe `Docs/fix_cintas_curva_y_puente.json`).

## Salto
Espacio salta unos 90 cm (`bCanJump`, `JumpSpeed` en `RobotLocomotion`). No salta mientras se muestra la intro.

## Prueba en Play
`Scripts/playtest_pasarelas_y_cintas.py` (con el editor abierto): sube la escalera hasta arriba (206 cm), se para sobre
cada pasarela, salta (90 cm) y una piedra cruza la curva del cuarzo en ~5 s.
Pasó 8 de 8: `Docs/pasarelas_y_cintas_play.json`.

Pendiente: `Deposito_Cuarzo` no entrega a `Cinta_Cuarzo_Triturar3` (su salida queda ~12 m de la entrada de la cinta).

## Pasarela_L2 por piezas (04/10)
`Pasarela_L2` era una copia de la malla fija vieja (estirada 0,75 en Y) y no tenía manijas. Ahora es un
`AFactoryWalkwayL` como `Pasarela_L` (mismo lugar y giro; el estiramiento pasó a sus medidas): sus cuatro barandas y las
dos puntas se arrastran y el piso las sigue. `Scripts/apply_pasarela_l2.py` → `Docs/pasarela_l2.json`.
- **Por qué no se veían las L** (04/10): desde el import del 03/10 las piezas de la L (`Modular/SM_PasarelaPiso`,
  `_Baranda`, `_Poste`) estaban al 1 % (1,3 cm): importar sobre un nombre que ya existió deja la malla a 1/100. Se
  importaron de nuevo con nombres nuevos en `Modular/L` (`SM_PasarelaLPiso`, `SM_PasarelaLBaranda`, `SM_PasarelaLPoste`,
  tamaño comprobado) y las usan `Pasarela_L` y `Pasarela_L2`: `Scripts/fix_pasarela_l_escala.py` →
  `Docs/pasarela_l_escala.json`. Ojo: `import_pasarela_modular.py` todavía importa la L con los nombres viejos; no
  volver a correrlo sin cambiar eso.

## Pasarelas nuevas por piezas (07/10)
El usuario borró las pasarelas viejas y puso en la fábrica las dos nuevas (`3D assets/GLBs`, ver «Equipos del
despacho» en MUELLES.md). Ahora también se arman a medida, con piezas cortadas de su propio modelo:
- `Pasarela_Verde`: `AFactoryWalkwayStraight` (giro 90°: el modelo corría a lo largo de Y). Barandas a ±51,5 cm, de
  −297 a 297 cm; piso a 65 cm del suelo, postes cada 1,89 m, patas en cada tramo de piso (1,89 m).
- `Pasarela_L_Elevada`: `AFactoryWalkwayL` (giro 180°: la esquina de afuera del modelo estaba en +X+Y). `OuterA` −321,5,
  `InnerA` −210, `OuterB` −325, `InnerB` −212, `EndA` 341,5, `EndB` 340,7; piso a 1 m, postes cada 1,54 m.
- Igual que las viejas: manijas (rombos) en el medio de cada baranda y en cada punta; el piso sigue a las barandas; en
  Detalles las medidas y `bLeftRail`/`bOuterRailA`… para apagar una baranda.
- Piezas: `Scripts/author_pasarelas_nuevas_modular.py` (Blender; tramos limpios entre postes y patas, medidos en el
  modelo) → `SourceAssets/Pasarelas/ModularNuevas`; en Unreal `Scripts/apply_pasarelas_nuevas_modular.py` (piezas en
  `Pasarelas/ModularNuevas/<Verde|LElevada>`, tamaño comprobado; si los actores ya son por piezas conserva sus
  medidas). Informe `Docs/pasarelas_nuevas_modular.json`. Colisión comprobada con rayos sobre los dos pisos (135 y 140
  cm). Respaldo: `Saved/Respaldos/2026-10-07_puertas_y_luz/L_FactoryDemo_antes_pasarelas_modulares.umap`.

### Altura del piso: las patas se estiran (07/10)
- `AFactoryWalkway` tiene una pieza de **patas** (`LegMesh`, de 0 a `PieceLegTop`) aparte del piso (la losa con sus
  vigas, de `PieceLegTop` a la altura del piso `PieceDeckTop`). **`DeckHeight`** (Detalles) o el **rombo de altura**
  (sobre el medio de la recta / la esquina de la L; arrastrarlo para arriba o abajo) suben o bajan el piso y las
  barandas; las patas se estiran del suelo al piso. Mínimo: 5 cm de patas; máximo 20 m. El actor queda en el suelo.
- Las patas chocan con su propia malla: entre ellas se camina por debajo (comprobado con rayos a 1 m y 1,70 m bajo la L).
- Verde: losa de 45 a 70 cm, patas de 0 a 45. L: losa de 70 a 104 cm, patas de 0 a 70.
- `Pasarela_L_Elevada` estaba subida entera (actor a z 150, patas en el aire): se bajó al suelo con `DeckHeight` 254,7
  (piso a 2,50 m, donde estaba).
- Las pasarelas sin pieza de patas (las viejas) no cambian: `DeckHeight` no hace nada.
- Código: `FactoryWalkway.h/.cpp` (`Legs`, `Lift`, `ApplyHeight`, `HeightHandleAt`); piezas: `author_pasarelas_nuevas_modular.py`
  (`leg_top`) y `apply_pasarelas_nuevas_modular.py` (las patas con colisión compleja; conserva la altura).

## Plataforma industrial a medida y barandas sueltas (07/10)
**`Plataforma_Industrial`** (`AFactoryPlatform`, carpeta Fabrica, en (1000, −1300)): la plataforma de acero del usuario
(`3D assets/GLBs/Plataforma industrial de acero en 3D (1)`, sin barandas), 2,48 × 2,49 m, piso a 97,5 cm.
- Se arma con piezas: en cada **esquina** la pata con sus diagonales y el remate (fijas, siempre en las esquinas), las
  **vigas de los costados** entre ellas y la **placa del piso** en el medio (las dos se estiran).
- **Rombos**: uno en cada costado (arrastrarlo agranda o achica la plataforma de ese lado; mínimo 1,44 m) y el de
  **altura** en el medio (sube o baja el piso; las columnas de las patas se estiran, el pie no). En Detalles: `MinX`,
  `MaxX`, `MinY`, `MaxY`, `DeckHeight`.
- **Barandas en los costados**: `bRailMinX` / `bRailMaxX` / `bRailMinY` / `bRailMaxY` (apagadas), estilo `RailStyle` (verde, la de las pasarelas nuevas).
- Probado con rayos: con el piso a 3 m y un costado estirado a 4 m, se pisa arriba y se pasa por debajo (1 m y 1,80 m);
  la baranda del costado puso 4 tramos y 5 postes. Se dejó como estaba.

**Baranda suelta** (`AFactoryRailing`; la de ejemplo, `Baranda_1`, la borró el usuario): una baranda que sigue una línea.
- Seleccionarla y en el viewport mover los **puntos de la línea** (`Path`); **Alt + arrastrar** un punto agrega otro
  (una esquina). Cada tramo va recto y a nivel (a la altura de su primer punto). Copiar y pegar para hacer más.
- `Style`: **Pasarela verde** (por defecto: la de las pasarelas nuevas, pedido del usuario), **Escalera (paneles)**,
  **Pasarela L elevada** o **Propia** (piezas y medidas a mano en `Pieces`). `bFlip` da vuelta el lado de afuera; `bClosed` cierra
  la línea. Chocan (caja), así que frenan al personaje.
- Baranda de la escalera: un panel entre dos postes de la baranda de atrás de `Escalera_Plataforma` (postes cada 1,14 m,
  0,8 m de alto).

Piezas: `Scripts/author_plataforma_y_barandas.py` (Blender) → `SourceAssets/Plataformas`; en Unreal
`Scripts/apply_plataforma_y_barandas.py` (`Plataformas/Industrial` y `Plataformas/Barandas`; si los actores ya existen
solo les pone las piezas). Informe `Docs/plataforma_y_barandas.json`. Código: `FactoryPlatform.h/.cpp`
(`AFactoryPlatform`, `AFactoryRailing`, `FFactoryRailPieces`, `EFactoryRailStyle`). El modelo entero escalado está en
`SourceAssets/DespachoEquipos/SM_PlataformaIndustrial.fbx` (`author_despacho_equipos.py`). Respaldo del nivel:
`Saved/Respaldos/2026-10-07_puertas_y_luz/L_FactoryDemo_antes_plataforma.umap`.
