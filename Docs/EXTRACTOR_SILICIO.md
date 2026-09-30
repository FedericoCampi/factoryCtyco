# Extractor de Silicio — 26 de septiembre de 2026

Máquina decorativa animada (extractor de cristal tipo Czochralski), generada con TRELLIS
desde una imagen y animada en Blender. Colocada en `L_FactoryDemo`, en el centro del
estacionamiento, para que el usuario la reubique.

- Actor: `Extractor_Silicio` (SkeletalMeshActor), carpeta `Environment`, (-2303, -410, 0) cm.
- Assets: `/Game/FactoryCtyco/Environments/ExtractorSilicio/` — `SK_ExtractorSilicio` (2,5 m,
  ~154 000 triángulos, 3 huesos), `SK_ExtractorSilicio_Anim` (loop de 8 s),
  `M_ExtractorMirilla_Glow` (emisivo naranja que pulsa cada 4 s), física autogenerada.
- Movimiento: el tambor de arriba oscila ±35° y la varilla central gira ±30°. No dan la
  vuelta completa porque TRELLIS no modeló sus caras ocultas.

Fuentes en `SourceAssets/ExtractorSilicio`: GLB original, `Extractor_Silicio_v1.blend`
(piezas por objeto), `ExtractorSilicio_unreal.blend` y `extractor_unreal.fbx`.

Regenerar:
1. `blender -b --factory-startup -P Scripts/animate_extractor_silicio.py -- SourceAssets/ExtractorSilicio/extractor_original.glb SourceAssets/ExtractorSilicio`
2. `blender -b --factory-startup -P Scripts/author_extractor_silicio.py` (altura y reducción al inicio).
3. Con el editor cerrado: `UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/import_extractor_silicio.py -unattended -nosound`
   (informe: `Docs/extractor_import.json`; reemplaza el actor, así que se pierde la posición ajustada a mano).

Encendido con E (26/09): `Extractor_Interruptor` (clase C++ `AFactoryMachineSwitch` de FactoryCtycoRuntime),
junto a la pantalla del gabinete trasero. A menos de 2,2 m aparece "[E] ENCENDER EXTRACTOR".
Apagada: animación detenida y luces, mirilla, baliza y pantalla oscuras (parámetro `Power` de
sus materiales). Al encender, todo sube en 1,5 s. `UFactoryGatheringComponent::Interact`
consulta los interruptores antes que las máquinas y la chatarra.

Accesorios (`Scripts/add_extractor_lights.py`, idempotente; `Scripts/run_extractor_setup.py` lo
corre sin editor, junto con `reimport_parking_mesh.py`, y guarda el nivel):
- `Extractor_LuzMirilla` (12 cd) y `Extractor_LuzBaliza` (20 cd) + esfera `Extractor_Baliza`.
- `Extractor_Pantalla`: texto ilegible verde (`T_ExtractorPantalla`, generado por
  `Scripts/make_screen_glyphs.py`) que sube despacio.
Todo va enganchado a `Extractor_Silicio`. Requiere FactoryCtycoRuntime compilado e instalado
(`Scripts/build_runtime_visuals.ps1 -Install`, con el editor cerrado).

No se probó todavía en Play.
