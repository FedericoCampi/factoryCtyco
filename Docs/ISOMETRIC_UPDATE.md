# Cámara, animación e iluminación

Actualización del 13 de septiembre de 2026.

- Cámara fija oblicua: inclinación de 55°, diagonal de 45°, brazo de 2450 cm
  y campo de visión de 35°. Conserva el ángulo mientras el personaje gira.
- WASD continúa moviendo el personaje en relación con la cámara. Espacio salta.
- `Robot1` mide 1,80 m, tiene un rig mecánico de 22 huesos más el nodo raíz
  del contenedor FBX, con pesos revisados en Blender.
- Animaciones propias: reposo de 2 s, caminata de 0,8 s y pose aérea de 1 s.
  Un Blend Space mezcla reposo y caminata según la velocidad real.
- Velocidad de desplazamiento: 190 cm/s. El ciclo se ajusta a la longitud
  del paso para reducir el deslizamiento de los pies.
- La malla animada usa 181.353 triángulos y conserva la textura del original.
  Los archivos originales no se sustituyen.
- Sol más claro, cielo de día, luz de relleno sin sombras duras y un fondo
  neutro alrededor de la arena. Las 82 colisiones de la arena se conservan.

El archivo Blender editable y los FBX están en `SourceAssets/Robot1/Rigged`.
`Scripts/author_robot_rig.py` reproduce el rig y los ciclos. El componente
`RobotLocomotion` del Blueprint contiene las referencias editables a las
animaciones y el ajuste de velocidad.

`isometric_playtest.json` registra la prueba automática de movimiento,
deformación del esqueleto, cámara fija, reposo, salto y aterrizaje.
Las capturas `isometric_idle.png`, `isometric_walk.png` e `isometric_final.png`
permiten revisar la iluminación y la vista del juego.
