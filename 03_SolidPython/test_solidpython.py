from solid2 import *

# Create a 20x20x20 box with a 10mm hole through the center
cube_shape = cube([20, 20, 20], center=True)
hole_shape = cylinder(r=5, h=30, center=True)

result = cube_shape - hole_shape

# Export to SCAD
result.save_as_scad("solidpython_cube.scad")
print("SolidPython: Successfully generated solidpython_cube.scad")
