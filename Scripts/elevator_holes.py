"""Centros de los pozos del ascensor2, compartidos por floor_holes.py (Blender) y apply_elevator2.py (Unreal).

Coordenadas en m de Blender de la malla del padre: Unreal local (x, y, z) cm = (x, -y, z) * 100.
Si se mueve un ascensor, cambiar aca y regenerar esa malla (author_arena_edit.py / author_parking_scene.py).
"""
HOLES = {
    # Ascensor_Fabrica: local (1190, 80, 0) en SceneRobot_Fabrica, en el vano este (movido por el usuario el 30/09).
    # Sobresale 1,7 m del borde de la losa: afuera el pozo se abre en Piso_Exterior (apply_elevator_move.py).
    "arena": [(11.9, -0.8, 0.0)],
    "parking": [(9.0, 10.0, 1.35)],  # Ascensor_Estacionamiento: local (900, -1000, 135), en la terraza
    # Ascensor_Empleados va detras de la puerta de la plataforma de SM_EmpleadosEscena, sin pozo en el piso (29/09)
    "empleados": [],
}
