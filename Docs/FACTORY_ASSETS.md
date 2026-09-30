# Modelos de la fábrica recibidos

## Iteración visual del 19 de septiembre

La demo usa ahora una cinta propia modelada mediante Blender MCP, con estructura
biselada y materiales de grafito, acero y naranja. Su referencia actual está en
`DB_Belt`; los mecanismos añadidos usan las mallas de detalle de la misma biblioteca.
Fuente: `SourceAssets/Factory/VisualPolish/FactoryDetails.blend`.
Importación verificada: `factory_detail_import.json`.
Las asignaciones descritas abajo son antecedentes; no se reinterpretaron los
archivos originales ambiguos. Triturado y placa mantienen sus mallas básicas,
con materiales actualizados.

## Actualización de integración

Se importaron los ocho modelos como versiones de juego en
`/Game/FactoryCtyco/Factory/Models`, preservando los originales. Las mallas preparadas
tienen entre 14.000 y 100.000 triángulos; la geometría original no cambió.
La demo usa los modelos inequívocos de trituradora, fundición, depósito y chatarra.

La revisión visual encontró nombres cruzados: `cinta_recta.glb` contiene
fragmentos sueltos y `frag_triturado_almacenamiento.glb` contiene una cinta.
`frag_triturado.glb` representa una tolva con material y un pequeño tramo de
salida; `deposito_triturado.glb` se ve como una bandeja con una placa.
Se preguntó al usuario cómo asignarlos. También corrigió que el «9» es la
placa, pero ese número correspondía a `robot1.glb` en la enumeración anterior:
no se reasignó el robot sin confirmar el archivo exacto.

Mientras se aclaran esos nombres, la demo usa visuales procedurales básicos
para cinta, triturado y placa. Las asignaciones activas están en
`factory_demo_bindings.json`. La tabla siguiente conserva la identificación
verbal anterior; las cuatro filas ambiguas todavía no se aplican al juego.

## Identificación verbal inicial

Identificación acordada con el usuario el 14 de septiembre de 2026.

Carpeta de originales: `C:\Users\Usuario\Desktop\3D assets\GLBs\robotAutomation`.

| Archivo | Uso |
| --- | --- |
| `trituradora-optimizada-complete.glb` | Trituradora de chatarra. |
| `fundicion.glb` | Fundición. |
| `deposito.glb` | Depósito general. |
| `cinta_recta.glb` | Cinta transportadora recta. |
| `frag_metalicos.glb` | Montón de chatarra recogible sin procesar. El usuario confirmó que corresponde al prompt de chatarra, aunque el nombre diga fragmentos. |
| `frag_triturado.glb` | Material triturado, resultado del procesamiento de chatarra. |
| `frag_triturado_almacenamiento.glb` | Representación del material triturado almacenado temporalmente; es el material, no el depósito. |
| `deposito_triturado.glb` | Depósito para guardar y almacenar material triturado. |
| `robot1.glb` | Robot anterior. Ya existe una versión preparada y animada en el proyecto; conservarla. |
| `scene1.glb` | Archivo de escena anterior; no sustituye automáticamente la arena actual importada desde `sceneRobot.zip`. |

Los dos modelos de almacenamiento de triturado amplían el conjunto solicitado:
son un visual de material almacenado y su depósito, respectivamente. No son
la placa metálica final ni tipos adicionales de recurso por sí mismos.

## Pendientes

- Cinta curva de 90°: el usuario confirmó que todavía no la creó.
- Placa metálica: no se recibió un archivo identificado como tal.

## Revisión de archivos

Los ocho modelos nuevos se pudieron abrir y renderizar en Blender 5.2.1.
Las vistas están en `factory_asset_review/` y las medidas originales, texturas
y cantidades de triángulos en `factory_asset_review/audit.json`.

Cada uno contiene una malla estática, un material y cuatro imágenes incluidas;
no tienen esqueleto ni animaciones. Las mallas rondan los 687.000–700.000
triángulos. Están normalizadas a una dimensión máxima de 1 unidad: requieren
ajustar escala para el juego, preparar colisiones y evaluar una versión de
menor detalle para recursos repetidos y cintas.

La revisión inicial solo produjo vistas. La integración posterior está documentada
arriba y en `factory_import.json`. `L_Recoleccion` conserva la etapa anterior;
`L_FactoryDemo` usa el modelo real de chatarra entregado.
