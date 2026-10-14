# Horno de fundición y laboratorio — 30 de septiembre de 2026

Modelos del usuario, puestos en `L_FactoryDemo` para que él los ubique. Por ahora son decorado: no tienen función de juego.

## Horno de fundición
- Fuente: `3D assets/GLBs/hornoFundicion.glb` (1 m, ~690 000 triángulos, 4 texturas).
- `Scripts/author_horno_fundicion.py` (Blender) lo lleva a **2 m de alto** (1,96 × 1,61 m: entra en una celda),
  origen al centro del piso, ~152 000 triángulos y una colisión de caja. Salida en `SourceAssets/HornoFundicion`.
- Malla `/Game/FactoryCtyco/Environments/HornoFundicion/SM_HornoFundicion`; actor `Horno_Fundicion` (carpeta Fabrica),
  en (0, −500, 0), dentro de la fábrica.
- El FBX solo lleva color y relieve (normal): los mapas de metal/rugosidad del GLB no pasan. Si se ve apagado, se le
  puede armar un material con esas dos texturas.
- Altura: `HEIGHT_M` al principio del script.

### Horno elevable (01/10)
- `Horno_Fundicion` pasa a ser un `FactoryRaisedProp` (mismo lugar, carpeta y escala 2,25). Al **subirlo con el gizmo**,
  el cuerpo y su placa de abajo quedan iguales (la placa **no se estira**) y debajo aparece un **bloque macizo de
  cemento** desde la primera superficie que tenga debajo (traza hacia abajo, ignorándose) hasta la placa, con el
  contorno de la placa (un poco adentro). El bloque es opaco y tiene colisión (el personaje choca). **Elevation** (cm)
  muestra esa altura; escribirla mueve el actor. Estirar el actor en Z más que en X también lo eleva; escalarlo parejo
  solo lo agranda. (Antes se estiraba la placa: se veía deformada y con huecos.)
- El bloque es el cubo del motor (`PedestalMesh`, con su caja de colisión) con `M_HornoPedestal_Cemento`
  (`PedestalMaterial`): textura de cemento alineada al mundo (un mosaico cada 1,5 m), así no se deforma al estirarse.
  `Scripts/apply_horno_pedestal.py` crea el material, se lo pone al horno y lo prueba (informe `Docs/horno_pedestal.json`).
- `Scripts/author_horno_base.py` (Blender) separa el modelo: base = la placa de abajo (caras por debajo de 10 cm,
  `CUT_M`), cuerpo = el resto (`SM_HornoFundicion_Base`, `SM_HornoFundicion_Cuerpo`, mismo material `Material_0`,
  una caja de colisión cada una). `Scripts/apply_horno_elevable.py` las importa y cambia el actor (informe
  `Docs/horno_elevable.json`). `SM_HornoFundicion` queda sin usar en el mapa.

### Tubo de descarga con tolva (01/10)
- Fuente: `3D assets/GLBs/Tubo de descarga con tolva industrial-complete.glb` (1 m de largo, ~700 000 triángulos,
  4 texturas). `Scripts/author_tubo_descarga.py` (Blender) lo lleva a **2 m de largo** (2 × 0,62 × 0,91 m; `LENGTH_M`),
  origen al centro del piso, ~154 000 triángulos y una colisión de caja. Salida en `SourceAssets/TuboDescarga`.
- `Scripts/import_tubo_descarga.py` (con o sin editor) importa `/Game/FactoryCtyco/Environments/TuboDescarga/SM_TuboDescarga`
  y pone el actor `Tubo_Descarga` (carpeta Fabrica) al lado del horno, en (−302, −688, 0), para que el usuario lo
  ubique; si ya existe solo le cambia la malla. De paso sube el horno 100 cm y comprueba que la base llegue al piso.
  Informe: `Docs/tubo_descarga_import.json`.

## Laboratorio (escenaLab1)
- Fuente: `3D assets/GLBs/scenes/escenaLab1-complete.glb` (20,6 × 18,6 m, 4,8 m de alto, 1139 piezas, sin colisiones).
- `Scripts/author_lab_scene.py` une las piezas en `SM_Lab1` (143 000 triángulos, 26 materiales), en escala real.
  Salida en `SourceAssets/Lab1`.
- En Unreal choca con la propia malla (*complex as simple*): se pisa y se choca con lo que se ve.
- Actor `Lab1_Escena` (carpeta Lab1) en (3800, 0, 0), al este de la fábrica, sobre el piso de afuera. Todavía no hay
  cómo llegar caminando ni ascensor, y tiene techo (con la cámara de arriba no se ve adentro).

Importar los dos (editor abierto con `L_FactoryDemo`): `Scripts/import_horno_y_lab.py`. Si los actores ya existen,
solo cambia la malla y conserva su lugar. Informe: `Docs/horno_y_lab_import.json`.

## Carpetas de `3D assets/GLBs` (reorganizadas por el usuario el 30/09)
Las escenas pasaron a `GLBs/scenes` (`sceneStacionamiento.glb`, `esceneStacionamientoOriginal.glb`,
`recepcion/recepcion`, `escenaLab1-complete.glb`) y los modelos de la demo de reciclaje están en `GLBs/robotAutomation`.
Se corrigieron las rutas de `author_parking_scene.py`, `author_parking_columns.py`, `author_employee_scene.py` y
`author_reception_room.py`. Los demás modelos siguen en `GLBs` y sus scripts no cambiaron.

## Codo metálico (02/10)

`Codo_Metalico` (StaticMeshActor, carpeta Fabrica) es el codo reforzado con pernos del usuario
(`3D assets/GLBs/Codo metálico reforzado con pernos-complete.glb`), suelto al lado del horno para ubicarlo a mano.
Mide 91 × 100 × 35 cm (1 m en su lado mayor, apoyado plano), ~154 000 triángulos y colisión de caja.
Malla: `/Game/FactoryCtyco/Environments/CodoMetalico/SM_CodoMetalico`.
Se rehace con `Scripts/author_codo_metalico.py` (Blender) e `Scripts/import_codo_metalico.py` (editor); si el actor
ya existe solo se le cambia la malla y se conserva su posición. Informe: `Docs/codo_metalico_import.json`.

## Línea de descarga: tubo → codo → contenedor (02/10)

`Tubo_Descarga` y `Codo_Metalico` van **abiertos arriba** (se les sacó la mitad de arriba por el eje del caño) para
que se vea bajar el líquido; la tolva del tubo queda entera. El caño del tubo baja ~5,4° hacia la boca y el corte
sigue esa inclinación.

`Scripts/apply_linea_descarga.py` (editor, con `L_FactoryDemo` abierto) encaja el codo en la boca del tubo: mismo
centro, mismo diámetro (escala 1,035) y mismo eje. El tubo no se mueve: si lo movés, volvé a correr el script y el
codo lo sigue. La salida del codo mira a -Y y desemboca en `Container_Producto` (1,5 × 0,7 × 0,56 m, carpeta
Fabrica, `SourceAssets/ContainerProducto`, `author_container_producto.py`), que se puso en el piso debajo de esa boca;
si ya existe, el script no lo mueve. Informe: `Docs/linea_descarga.json`.

Para rehacer las mallas: `author_tubo_descarga.py`, `author_codo_metalico.py` y `author_container_producto.py`
(Blender), después `apply_linea_descarga.py`. Todavía no hay líquido.

## Proceso de fundición: cuarzo → silicio → lingote (02/10)

**Cómo se juega** (en `L_FactoryDemo`):
1. `Deposito_Cuarzo` (piso, 100 de cuarzo) manda el cuarzo a `Cinta_Cuarzo_Subida` (sube a 30°), que lo deja en la
   línea en altura: `Cinta_Fabrica_5` → `Esquina3` → `Esquina2` → `Cinta_4` → `Cinta_2` → `Esquina` → `Cinta_1`, que lo
   tira en la boca del horno. Cada cinta lleva una pieza a la vez.
2. El horno junta una tanda de 4 (arriba dice «HORNO · CARGANDO CUARZO 2/4»).
3. Parado al lado del horno, **[E] ENCENDER HORNO**: se calienta y brilla cada vez más («FUNDIENDO 63 %», 10 s).
4. **[E] ABRIR COLADA**: el silicio fundido cae del borde del horno a la tolva, corre por la canaleta abierta del tubo
   y del codo y sale en un chorro curvo hasta `Container_Producto`, que se llena (6 s).
5. El contenedor se enfría de naranja a gris («ENFRIANDO 40 %», 12 s) y queda el lingote. Al costado del contenedor,
   **[E] RETIRAR LINGOTE**: va al inventario (`SiliconIngot`). Mientras se enfría, el horno ya carga la tanda siguiente;
   solo cuela si el contenedor está vacío.

**Código**: `AFactoryMeltProcess` (`FactoryMeltProcess.h/.cpp`), actor `Proceso_Fundicion` puesto en el horno. En el
panel (Melt): `FeedBelt` (la cinta que entrega en la boca), `Container`, `BatchSize`, `MeltSeconds`, `FillSeconds`,
`CoolSeconds`, `FlowSpeed` y `bAutomatic` (hace todo solo, para cuando se contraten operarios). Los puntos se
arrastran en el visor: `MouthPoint` (boca), `ControlPoint` (dónde pararse para E) y `PourPath` (por dónde corre el
líquido; en el editor se ve el chorro entero para ubicarlo). `FillMin`/`FillMax`: la caja que se llena, en el espacio
del contenedor. Una cinta que entrega a un proceso ya no dice «Salida sin conectar» (`bFeedsProcess`). E pasa por
`UFactoryGatheringComponent::Interact`.

**Assets**: `SM_Cuarzo` (`Scripts/author_cuarzo.py`) con `M_Cuarzo`; recursos `DA_Quartz` y `DA_SiliconIngot`;
`M_SilicioFundido` (parámetro `Heat`: 1 naranja que brilla con vetas que corren, 0 gris silicio).

**Scripts**: `Scripts/apply_proceso_fundicion.py` arma todo y se puede volver a correr (deja la línea en el sentido
del horno, crea el depósito y la subida si faltan, y actualiza `Proceso_Fundicion`, con el paso 5 en
`apply_proceso_fundicion_horno.py`). Si movés el contenedor, el chorro lo sigue solo; si movés el tubo o el codo,
corré `apply_linea_descarga.py` y después `apply_proceso_fundicion.py`. Informe: `Docs/proceso_fundicion.json`.
Respaldo del nivel de antes: `Saved/Respaldos/2026-10-02_proceso_fundicion`.

**Prueba**: `Scripts/playtest_proceso_fundicion.py` (con el editor abierto, en Play y con el tiempo ×4): el cuarzo
llega, la tanda, encender, colar, enfriar y retirar el lingote al inventario. Pasó el 02/10
(`Docs/proceso_fundicion_play.json`, capturas `Saved/Screenshots/fundicion_*.png`).

**Pendiente**: F5/F9 no guarda el estado del horno ni del contenedor; no hay sonidos; el lingote todavía no se usa.

### Trituradora, caños y modo de prueba (02/10, más tarde)
- **Paso nuevo**: `Deposito_Cuarzo` → `Cinta_Cuarzo_Triturar` → **`Trituradora_Cuarzo`** (`DB_QuartzCrusher`, copia de
  la trituradora: 1 cuarzo → 1 arena de cuarzo cada 2,5 s) → `Cinta_Cuarzo_Subida` → línea en altura → horno. Lo que
  viaja por la línea es **arena de cuarzo** (`DA_QuartzSand`, `SM_ArenaCuarzo` de `Scripts/author_arena_cuarzo.py`,
  `M_ArenaCuarzo`) y el horno funde arena («CARGANDO ARENA DE CUARZO», `InputLabel`). Un depósito no le pasa material
  a una máquina sin una cinta en el medio: por eso la cinta corta. La trituradora no está en el catálogo de
  construcción (B).
- **Caños**: `SM_CanoRecto` (`Scripts/author_cano_recto.py`) es el caño del tubo de descarga sin el pie ni la tolva,
  enderezado y abierto arriba; origen en la entrada, hacia +X, 1,27 m (se estira en X). `Cano_Recto_1` a `4` siguen
  del codo hasta arriba del centro de `Container_Producto`, bajando 3°, y de ahí el silicio cae. Se rehacen cada vez
  que se corre `apply_proceso_fundicion.py` (si movés el contenedor, volvé a correrlo).
- **Modo de prueba**: `Guia_Mision` tiene **Paused** (nuevo, `AFactoryGuide::bPaused`): sin intro, sin tarjeta de
  misión y sin flecha; desmarcarlo vuelve a las misiones. `PlayerStart_Robot1` pasó al lado del horno (−250, −380, 110);
  antes estaba en (−3830, 9220, 500).
- Prueba: `playtest_proceso_fundicion.py` comprueba además la pausa, el arranque en la fábrica y la trituradora.
  Pasó el 02/10.

### Horno más bajo (02/10)
- `Scripts/apply_bajar_horno.py` bajó 150 cm (`DELTA`) el horno (z 237 → 87; su bloque de cemento se acortó solo),
  `Tubo_Descarga` y `Codo_Metalico`, y después corre `apply_proceso_fundicion.py`, que rehace lo que depende de esa
  altura: `Cinta_Fabrica_1` ahora baja ~15° y entrega en la boca a 376 cm, los caños rectos van de 248 a 214 cm (el
  contenedor no se movió; su borde está a 168 cm) y el camino del líquido. La boca del horno y la entrega de la cinta
  ahora se calculan desde la altura del horno (`MOUTH_ABOVE_HORNO`, `BELT_ABOVE_MOUTH`). Informe:
  `Docs/bajar_horno.json`. Prueba en Play repetida: pasó.

### Línea corta (02/10)
Con el horno más bajo ya no hace falta la vuelta larga por las paredes para subir de a poco. La línea quedó:
`Deposito_Cuarzo` → `Cinta_Cuarzo_Triturar` → `Trituradora_Cuarzo` (en el piso, junto a la pared, x 1006 → 581) →
`Cinta_Fabrica_2` (sube 9,5°, de 45 a 210 cm) → `Cinta_Fabrica_Esquina` (210 cm) → `Cinta_Fabrica_1` (sube 9,5°
hasta la boca, 376 cm). Se **borraron** `Cinta_Fabrica_5`, `Esquina3`, `Esquina2`, `Cinta_Fabrica_4` y
`Cinta_Cuarzo_Subida` (respaldo del nivel de antes: `Saved/Respaldos/2026-10-02_linea_corta`). Las alturas se
calculan desde el horno (la vuelta queda donde las dos rectas suben igual), así que si se vuelve a bajar o subir el
horno, `apply_proceso_fundicion.py` reajusta la pendiente sola. Prueba en Play repetida: pasó.

### Lavadora y trituradora que recibe por arriba (02/10, noche)
La línea ahora la acomoda el usuario a mano; `apply_proceso_fundicion.py` ya no mueve ni borra cintas
(`MANAGE_LAYOUT = False`), solo conecta (`Scripts/apply_lavadora_cuarzo.py`):
`Lavadora_Cuarzo` (la caja gris, antes `Deposito_Cuarzo`; `DB_QuartzWasher`: máquina con el aspecto del depósito,
100 de cuarzo en bruto → **cuarzo lavado**, `DA_WashedQuartz` / `SM_CuarzoLavado` / `M_CuarzoLavado`, 3 s) →
`Cinta_Cuarzo_Triturar` (sube 8,9° sobre patas hasta arriba de la tolva) → `Trituradora_Cuarzo` (cuarzo lavado →
arena; **recibe por arriba**, donde termina la cinta, y **entrega abajo, adelante**) → `Cinta_Fabrica_2` →
`Cinta_Fabrica_Esquina` → `Cinta_Fabrica_1` → horno.
- **Nuevo en el código**: `AFactoryBuilding::MachineInput` / `MachineOutput` (Factory Demo › Machine): por dónde una
  máquina o depósito recibe y entrega, en el espacio del actor; se arrastran en el visor. Cero: los bordes de siempre.
- Respaldo del nivel de antes: `Saved/Respaldos/2026-10-02_linea_corta/L_FactoryDemo_antes_lavadora.umap`.
- Prueba en Play (`playtest_proceso_fundicion.py`): pasó.

### La caja es un túnel y la trituradora tiene tapa de salida (02/10, noche)
- **Túnel**: `Lavadora_Cuarzo` ya no procesa: es la caja gris (`StaticMeshActor`) con **dos huecos enfrentados** por
  donde pasa la cinta (`SM_LavadoraTunel`: `Scripts/apply_tunel_lavadora.py` calcula dónde la cinta cruza cada pared y
  exporta `SM_Deposito`; `Scripts/author_lavadora_tunel.py` corta los huecos en Blender). A futuro el material va a
  cambiar al pasar; por ahora no (`DB_QuartzWasher`, `DA_WashedQuartz` y `SM_CuarzoLavado` quedan sin usar). La caja
  se corrió de Y 561 a 661 para que la cinta pase por adentro (la pared norte está en 835).
- **Línea**: `Deposito_Cuarzo` (nuevo, 100 de cuarzo, en (1966, 701), del otro lado de la caja) → `Cinta_Cuarzo_Triturar`
  (alargada a 11,5 m: atraviesa la caja y sube 10° hasta arriba de la tolva) → `Trituradora_Cuarzo` (cuarzo → arena,
  recibe por arriba) → `Cinta_Fabrica_2` → esquina → `Cinta_Fabrica_1` → horno.
- **Tapa de salida**: `Trituradora_Tapa` (`SM_TapaSalida`, `Scripts/author_tapa_salida.py`, `M_TapaSalida`): campana de
  chapa abajo, adelante de la trituradora, sobre la punta de `Cinta_Fabrica_2`; pegada a la trituradora.
- Si se mueve la caja o el depósito: `apply_tunel_lavadora.py`, Blender (`author_lavadora_tunel.py`) y
  `apply_proceso_fundicion.py`. Respaldo: `Saved/Respaldos/2026-10-02_linea_corta/L_FactoryDemo_antes_tunel.umap`.
- Prueba en Play: pasó.

### Plataforma elevadora y primera persona (02/10, noche)
- **Plataforma elevadora** (`DB_Lift`, `SM_PlataformaElevadora` de `Scripts/author_plataforma_elevadora.py`,
  `Scripts/apply_plataforma_elevadora.py`): es una cinta (`AFactoryBuilding`) con **LiftHeight** > 0. Lo que llega a su
  borde de atrás sube con la plataforma LiftHeight cm (a `LiftSpeed`, 120 cm/s) y sale por el de adelante arriba; después
  baja vacía y recién ahí acepta la carga siguiente. Cuatro columnas guía en las esquinas (las patas). LiftHeight se
  cambia en el panel o arrastrando el rombo de adelante. Recibe a la altura de las cintas (33 cm + `Elevation`).
- **En la línea**: el usuario dejó `Cinta_Cuarzo_Triturar` plana a 1,06 m. Ahora `Deposito_Cuarzo` entrega arriba, a esa
  altura (`MachineOutput`); la cinta atraviesa la caja (huecos recortados de nuevo a esa altura) y se acortó hasta
  x 959; `Plataforma_Elevadora_1` sube 1,31 m al lado de la trituradora y entrega en la tolva (2,37 m).
- **Primera persona**: botón con un ojo al lado de silenciar (naranja cuando está activa) o tecla **V**: la cámara va a
  los ojos del personaje (su cuerpo se le oculta), **el mouse mira** sin apretar nada (el puntero se oculta y queda en la
  ventana; un punto de mira en el centro; `LookSensitivity`), WASD camina hacia donde mira. V o Inicio salen.
  Inicio o el botón vuelven a la isométrica (`UFactoryCameraComponent::SetFirstPerson`, `EyeHeight`, `FirstPersonFov`).
- Pruebas en Play: `playtest_plataforma_y_camara.py` (plataforma y primera persona) y `playtest_proceso_fundicion.py`:
  pasaron. Respaldo: `Saved/Respaldos/2026-10-02_linea_corta/L_FactoryDemo_antes_plataforma.umap`.
- **Avisos de E** (`AFactoryDemoHUD::DrawInteraction`, 03/10): en primera persona, el aviso más cercano de los que las
  cosas muestran en el mundo («[E] ENCENDER HORNO», ascensor, barrera, cintas de despacho, portones…; flotan arriba de
  las máquinas o de la cabeza del personaje, fuera de la vista desde los ojos) aparece bajo el punto de mira. En las dos
  vistas: «[E] JUNTAR …» al lado de algo para juntar (los lingotes) y «[E] CARGAR … EN LA CINTA / EN LA MÁQUINA» al lado
  de lo que acepta algo del inventario (en la isométrica, abajo, sobre la barra de ayuda). Dinero, silencio, ojo,
  eventos y barra de ayuda se ven igual y en el mismo lugar en las dos vistas (captura
  `Saved/Screenshots/primera_persona_lingote.png`).

### Piedras, sierra y tamaños en porcentaje (03/10)
- Se cargan **piedras** a mano (10 `Piedra_Prueba_N` junto a la pared este, E para juntar y E para cargar en
  `Cinta_Cuarzo_Triturar3`). Al pasar por la caja, la **sierra** (`AFactoryBeltStation` `Sierra_Estacion`, clase nueva:
  convierte lo que la cinta lleva dentro de su caja, con chispas) la corta en un **bloque**; la plataforma lo sube y se
  ve **caer en la tolva** (`AFactoryBuilding::MachineDropPoint`); la trituradora saca 2 de **piedra triturada** por bloque,
  que salen por la tapa a `Cinta_Fabrica_2` y llegan al horno, que funde piedra triturada.
- La sierra también corta **lingotes** a la mitad (`Sierra_Estacion_Lingotes`, `DA_SiliconIngotCut`); la trituradora no
  los acepta.
- **Tamaños**: `UFactoryResourceDefinition::CargoSize`, `SizeFrom`, `SizePercent`: piedra 32 cm, bloque 75 % de la
  piedra, triturada 60 % del bloque, lingote cortado 50 % del lingote; cambiar el de origen ajusta los demás.
- Arreglos de la línea del usuario (`Scripts/fix_cinta_lingotes.py`): cinta corta y su esquina daban vuelta al revés,
  una cinta duplicada encima, la esquina hacia el horno al revés e identificadores repetidos.
- Scripts: `author_piedras.py`, `apply_piedras.py`. Prueba en Play (`playtest_proceso_fundicion.py`, ahora cargando
  piedras): pasó.

## Escalera industrial con plataforma (03/10)
`Escalera_Plataforma` (StaticMeshActor, carpeta Fabrica), suelta en (0, −300) para que el usuario la ubique. Modelo del
usuario (`3D assets/GLBs/Escalera industrial con plataforma elevada-complete.glb`) llevado a 7 m de largo (3,66 × 7 ×
2,86 m: la plataforma a ~1,9 m y la baranda a ~1 m), ~154 000 triángulos, choca con su propia malla (*complex as
simple*) para poder subir los escalones y caminar arriba. Malla:
`/Game/FactoryCtyco/Environments/EscaleraPlataforma/SM_EscaleraPlataforma`. Se rehace con
`Scripts/author_escalera_plataforma.py` (Blender) e `Scripts/import_escalera_plataforma.py` (editor; si el actor ya
existe solo le cambia la malla). Informe: `Docs/escalera_plataforma.json`.
- (03/10, más tarde) La plataforma quedó **sin las barandas de los costados** (el usuario la va a alargar) y con una
  **baranda adelante**, en el borde opuesto a la escalera (el que mira al horno): es la baranda del costado girada y
  llevada al ancho, mismo estilo (`author_escalera_plataforma.py`: `DECK_TOP`, `SIDE_X`, `PLATFORM_FROM_Y`). Las
  barandas de la escalera siguen.

## Horno con tapa, lote de 3 y líquido del color del material (04/10)
- **Tapa**: `Horno_Tapa` (separada del cuerpo en `Scripts/author_horno_tapa.py`; cuelga de `Horno_Fundicion` en la
  bisagra). Apagado queda en su reposo (38°); **prendido (E en los controles) se abre más (75°)** y toma de la cinta de
  la boca hasta juntar **3**; entonces **se cierra** y funde **30 s** mientras lo que llega **espera en la cinta**.
  Fundido, **cuela solo** al contenedor (si está vacío) y la tapa vuelve a abrirse para el lote siguiente. E con el
  horno cargando lo apaga. Propiedades de `Proceso_Fundicion`: `LidActor`, `LidRestAngle`, `LidLoadingAngle`,
  `LidSign`, `LidSeconds`, `BatchSize`, `MeltSeconds`, `bAutoPour`.
- **Color del líquido**: el del material que entra (`Color` de su definición; la piedra triturada es gris). Material
  `M_LiquidoFundido` (parámetros `Color`, `Heat`, `Brillo`).
- **Piedra triturada más grande**: 80 % del bloque (antes 60 %): 19 cm en vez de 14.
- Scripts: `author_horno_tapa.py` (Blender) y `apply_horno_tapa.py` (con el editor abierto) → `Docs/horno_tapa.json`.
  Prueba: `Scripts/playtest_horno.py` → `Docs/horno_play.json` (9/9).
- (04/10, después) Fundido de **5 s**. El líquido usa `MI_LiquidoFundido` (`Brillo` 1,2: con 6 el gris se veía blanco).
