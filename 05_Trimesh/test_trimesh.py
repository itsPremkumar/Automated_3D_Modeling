import trimesh

# Create a 20x20x20 box
box = trimesh.creation.box(extents=[20, 20, 20])

# Export to STL
box.export("trimesh_cube.stl")
print("Trimesh: Successfully generated trimesh_cube.stl")
