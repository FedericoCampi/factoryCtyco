# Robots: reciclaje y automatización

Documento vivo · actualizado el 19 de septiembre de 2026 · nombre por definir.
Estado de cierre: [checkpoint actual](ESTADO_PARA_RETOMAR_2026-09-19.md).

## Dirección confirmada

Mejorar de a poco la fábrica original con el robot: recolectar, construir,
procesar materiales, conectar cintas y ver cómo la producción transforma el
escenario. Mantener interacciones legibles, animaciones y mejoras con una breve
demora visible. Continuar usando Unreal y Blender MCP para juego y arte.

La inspiración GROW sirve para explorar relaciones y evolución del escenario.
Su diorama independiente no sustituye L_FactoryDemo. En la fábrica actual,
los tres hitos son lineales; no existe todavía un árbol de decisiones ni un
puzle de orden correcto como el del experimento.

El usuario pidió continuar después. Las siguientes iteraciones son ideas para
elegir al retomar, no tareas en ejecución ni decisiones de diseño ya aprobadas.

## Base implementada

- Robot controlable, recolección, mochila, cámara isométrica y construcción.
- Trituradora, fundición, depósitos con filtro, cintas rectas y desmontaje.
- Producción automática después de cargar material; el robot aún se maneja a mano.
- Objetivo de 20 placas almacenadas y 20 entregadas por cinta.
- Modelos, materiales, HUD e indicadores animados de actividad mejorados.
- Taller a las 5 placas producidas; estación a las 10 entregas por cinta;
  ampliación a las 20. Cada aparición tarda dos segundos.
- Anexo con 36 celdas y tres celdas de conexión por el portón frontal.
- Guardado manual de inventarios, construcciones, procesamiento e hitos.

Taller y estación todavía son decorativos. La ampliación sí permite construir.
La [guía jugable](DEMO_FABRICA.md) registra los controles y reglas reales.

## Próximas iteraciones propuestas

### 1. Primera tarea del taller — recomendación para retomar

Dar una función al taller: ordenar al robot un único viaje para llevar una
cantidad de chatarra desde un depósito hasta otro. El jugador elige origen y
destino. Mostrar la carga, el objetivo del viaje y una forma clara de cancelar.

Empezar con una ruta corta y comprobar navegación entre las colisiones reales
del mapa y las máquinas construidas. Si no hay camino, detener la tarea e
indicar el motivo. Mantener disponible el control manual.

Terminado cuando: realiza una entrega usando inventarios reales, conserva los
materiales y devuelve el control al jugador. Todavía no hace falta buscar
recursos por todo el mapa, repetir indefinidamente ni introducir energía.

### 2. Convertir el viaje en una rutina de abastecimiento

Repetir el trabajo mientras haya suministro y espacio. Mostrar estados claros:
buscando carga, transportando, destino lleno, origen vacío o camino bloqueado.
Permitir detener y reanudar; guardar la tarea y su carga sin duplicarlas.

Terminado cuando: el robot mantiene alimentada la línea durante varios ciclos
sin intervención. Después se puede ampliar a recoger montones de chatarra,
elegir prioridades o trabajar con más de un robot.

### 3. Hacer útil la estación como base de espera

Al terminar una tarea, el robot vuelve a la estación y queda disponible. Luces
y animaciones muestran si está trabajando, esperando o necesita una nueva orden.

Terminado cuando: su estado y ubicación se entienden mirando la escena.
Propuesta inicial sin batería ni penalizaciones; decidir más adelante si una
mecánica de energía mejora realmente el juego.

### 4. Preparar el segundo escenario como arquitectura independiente

La instalación botánica es una propuesta temática, aún pendiente de imagen
definitiva. El requisito confirmado es que la imagen se pueda pasar a 3D y
mantenga la presentación de la escena actual: maqueta aislada, vista elevada,
suelo continuo, estructura fija y accesos claros.

No incluir en la imagen los objetos que se crearán por separado: robots,
criaturas, máquinas, utilería, vegetación ni agua. El [prompt corregido](PROMPT_INVERNADERO.md)
conserva estas restricciones. Al recibir el 3D, revisar escala con el robot de
1,80 m, dimensiones del acceso, colisiones, encuadre y espacio construible.

Terminado cuando: se puede recorrer esa base limpia y sus accesos son
compatibles con la fábrica. El anexo actual no equivale a este segundo mapa.

### 5. Conectar los dos escenarios

Primero permitir entrar y volver por un portón o puente conservando inventario,
construcciones y progreso de ambas áreas. Elegir entre ampliación del mismo
nivel y mapas separados después de conocer las dimensiones del nuevo 3D.

Terminado cuando: el recorrido de ida y vuelta no reinicia ni pierde estado.
Luego evaluar transporte automático entre zonas y un recurso propio de la
instalación botánica que tenga un uso claro en la fábrica.

## Ideas posteriores, sin orden comprometido

- Mejoras visibles del robot compradas en el taller: capacidad, transporte o
  herramientas. Probar una sola antes de crear un árbol grande de mejoras.
- Criaturas con una función concreta: cuidar cultivos, recuperar recursos o
  ayudar con logística. Introducir una especie después de probar su trabajo.
- Pequeñas dependencias entre producción, recuperación del entorno y nuevos
  trabajos, manteniendo las animaciones sucesivas de unos segundos.
- Cintas curvas y divisores cuando las rutas rectas limiten una necesidad real.
- Sonidos de maquinaria, pequeños efectos y más animaciones de carga/descarga.
- Confirmar los modelos pendientes de triturado y placa antes de sustituirlos.

No se ha comprometido un sistema de combate, defensa, energía o economía mayor.
La siguiente elección recomendada es **un encargo concreto desde el taller**,
después de revisar la devolución del usuario sobre la versión actual.
