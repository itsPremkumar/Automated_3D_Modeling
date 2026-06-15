import cadquery as cq

# Create a 20x20x20 box with a 10mm hole through the center
result = cq.Workplane("XY").box(20, 20, 20).faces(">Z").workplane().hole(10)

# Export to STL and STEP
cq.exporters.export(result, "cadquery_cube.stl")
cq.exporters.export(result, "cadquery_cube.step")
print("CadQuery: Successfully generated cadquery_cube.stl and cadquery_cube.step")
