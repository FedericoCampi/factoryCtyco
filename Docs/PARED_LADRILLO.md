# Pared de ladrillos suelta — 27 de septiembre de 2026

`Pared_Ladrillo` (carpeta Environment) en el estacionamiento, para moverla, girarla y escalarla a mano.
Malla `/Game/FactoryCtyco/Environments/ParedLadrillo/SM_ParedLadrillo`: 2 m × 0,40 m × 2,5 m, origen al centro
de la base, colisión de caja. Material `M_LadrilloMundo`: la textura del ladrillo del estacionamiento
proyectada desde la posición en el mundo (1 repetición por metro a lo largo y a lo alto), así al escalar
o girar la pared los ladrillos no se estiran. Para más paredes: duplicar el actor.

Regenerar: `blender -b --factory-startup -P Scripts/author_sign_and_wall.py` y
`UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/apply_brick_wall.py -unattended -nosound`
(conserva la posición de los `Pared_Ladrillo*` que ya existan).
