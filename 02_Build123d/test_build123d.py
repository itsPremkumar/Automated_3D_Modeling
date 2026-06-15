from build123d import *

# Create a 20x20x20 box with a 10mm hole through the center
with BuildPart() as p:
    Box(20, 20, 20)
    with BuildSketch(p.faces().sort_by(Axis.Z)[-1]):
        Circle(radius=5)
    extrude(amount=-20, mode=Mode.SUBTRACT)

# Export to STL and STEP
export_stl(p.part, "build123d_cube.stl")
export_step(p.part, "build123d_cube.step")
print("Build123d: Successfully generated build123d_cube.stl and build123d_cube.step")
