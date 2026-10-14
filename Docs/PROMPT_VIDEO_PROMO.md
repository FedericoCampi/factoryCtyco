# Tráiler para Steam — llegada de camiones y despacho (4 de octubre de 2026)

Tráiler corto (~45 s) para la página de Steam, armado con el editor `video-editor-ai`:
**gameplay real** (los recortes de `Videos\gameplay_recortes`) + algunos **planos generados con Wan 2.2**
a partir de capturas del juego (`Videos\gameplay_recortes\capturas`) + **carteles de texto**.

## Reglas de Steam que importan acá

- **Mostrar gameplay real, y rápido.** El tráiler se reproduce solo y **sin sonido** en la página: en los primeros
  5 s tiene que verse el juego, y todo lo importante tiene que entenderse con los carteles, sin voz.
- **Declarar la IA.** Steam pide indicar en el *Content Survey* (sección «AI Generated Content») el contenido generado
  con IA, también el de marketing. Si el tráiler lleva planos de Wan, hay que declararlo. Por eso conviene que la
  mayor parte sea gameplay real y la IA quede para transiciones.
- **Nada que el juego no haga.** Los planos de IA solo para cosas que el juego ya tiene (barrera, camión, cintas, cajas).
- **Sin marcas de terceros.** El camión tiene ploteado *League of Legends* (`T_PloteoCamion`): cambiarlo por el logo
  de FactoryCtyco **antes de grabar**, o Steam puede rechazar el tráiler.
- Formato: MP4 H.264, 1920×1080, 30 o 60 fps.

## Antes de volver a grabar (recomendado)

1. Ploteo del camión con la marca del juego.
2. **Cielo**: hoy el fondo es negro (sin *Sky Atmosphere*), y en un tráiler se ve sin terminar.
3. Cámara **lenta y estable** (los movimientos rápidos salen borrosos y no se pueden usar), sin el editor alrededor
   (*Play* en ventana nueva o `F11`) y a 1080p.

## Guion (≈45 s)

| # | Tiempo | Plano | Fuente | Cartel en pantalla |
|---|---|---|---|---|
| 1 | 0–3 s | Camión llegando a la garita | Gameplay `01_camion_llega_garita` | **REABRÍ LA FÁBRICA** |
| 2 | 3–8 s | La barrera sube y el camión entra | **IA** · prompt 1 · `B_barrera_garita.png` | Controlá la garita |
| 3 | 8–9 s | Botón rojo de la garita | Gameplay `02_boton_garita` | — |
| 4 | 9–19 s | El camión entra marcha atrás al cajón | Gameplay `03_camion_entra_cajon` | Asigná cada camión a su muelle |
| 5 | 19–24 s | Vista aérea del despacho, cintas en marcha | **IA** · prompt 2 · `E_despacho_aereo.png` | Prendé las cintas |
| 6 | 24–34 s | TecJunior en el despacho entre cajas | Gameplay `04_despacho_tecjunior` | Cargá cada caja en su línea |
| 7 | 34–39 s | Plano heroico de TecJunior con una caja | **IA** · prompt 3 · `D_despacho_tecjunior.png` | Revisá el etiquetado |
| 8 | 39–40 s | Cinta cargando el camión | Gameplay `05_carga_al_camion` | — |
| 9 | 40–45 s | Camión cargado saliendo, se aleja la cámara | **IA** · prompt 4 · `A_patio_muelles.png` | **FACTORYCTYCO** · ¡Agregalo a tu lista de deseados! |

Los carteles van en español e inglés si la página va a estar en los dos idiomas
(«Reopen the factory», «Wishlist now on Steam»).

## Cómo generarlo en el editor

1. Por cada plano **IA**: *Generar un video con IA* → pegar el prompt → **Agregar captura** (la indicada) →
   16:9 · 5 s · **Alta calidad**. Generar 2 o 3 y quedarse con el mejor.
2. Recortar cada clip con **✂ Recorte manual** (`I` / `O` / *Conservar solo el tramo*) y exportarlo.
3. En la lista, marcar los clips **en el orden del guion** → **🎞 Unir clips** → exportar.
4. Carteles, música y logo: en un editor común (CapCut, DaVinci Resolve), porque Wan no escribe texto legible.
   Música sin derechos de autor: libre de uso comercial (por ejemplo, la biblioteca de YouTube Studio) o propia.

## Prompts (Wan 2.2, imagen → video, en inglés)

Todos terminan con el mismo bloque de estilo para que los planos combinen. Describen **solo lo que se mueve**: la
captura ya define el escenario.

### Prompt 1 · La barrera sube (`B_barrera_garita.png`)
```
The red and white boom barrier at the guard booth smoothly lifts up, and the white delivery truck starts rolling forward through the gate into the factory yard, wheels turning, steady slow camera tracking alongside the truck at cab height. stylized 3D video game, Unreal Engine render, clean industrial look, warm afternoon sunlight, soft long shadows, orange and yellow safety accents, smooth cinematic motion, sharp focus, high detail
```

### Prompt 2 · Despacho en marcha (`E_despacho_aereo.png`)
```
Slow aerial drone shot gliding over a factory dispatch area: the roller conveyors with yellow rails start moving, cardboard boxes roll along the lines and turn at the junctions toward the loading machine, steady rhythm, camera slowly pushing forward and tilting down. stylized 3D video game, Unreal Engine render, clean industrial look, warm afternoon sunlight, soft long shadows, orange and yellow safety accents, smooth cinematic motion, sharp focus, high detail
```

### Prompt 3 · TecJunior con la caja (`D_despacho_tecjunior.png`)
```
A young factory worker in a teal vest and orange gloves picks up a cardboard box from the roller conveyor, checks the shipping label and walks toward the camera carrying it with both hands, boxes advancing on the conveyor behind him, camera slowly lowering from a high angle to a heroic low angle. stylized 3D video game, Unreal Engine render, clean industrial look, warm afternoon sunlight, soft long shadows, orange and yellow safety accents, smooth cinematic motion, sharp focus, high detail
```

### Prompt 4 · Cierre: el camión se va (`A_patio_muelles.png`)
```
A loaded delivery truck pulls away from the loading dock and drives across the industrial yard toward the exit, the camera slowly rising and pulling back to reveal the whole yard, the brick walls and the loading bays, calm and satisfying ending shot. stylized 3D video game, Unreal Engine render, clean industrial look, warm afternoon sunlight, soft long shadows, orange and yellow safety accents, smooth cinematic motion, sharp focus, high detail
```

Si sale algo raro, ajustar de a una cosa: menos acciones por prompt, cámara más lenta («static camera»), o cambiar
la semilla. Si el cielo negro de la captura se «inventa» mal, agregar al prompt `dark night sky`, o mejor grabar con cielo.
