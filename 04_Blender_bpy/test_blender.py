import bpy

# Clear existing mesh objects
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.select_by_type(type='MESH')
bpy.ops.object.delete()

# Create a 20x20x20 cube
bpy.ops.mesh.primitive_cube_add(size=20, location=(0, 0, 0))
cube = bpy.context.active_object

# Create a cylinder for the hole
bpy.ops.mesh.primitive_cylinder_add(radius=5, depth=30, location=(0, 0, 0))
cylinder = bpy.context.active_object

# Add Boolean modifier to cut the hole
bpy.context.view_layer.objects.active = cube
bool_mod = cube.modifiers.new(name="CutHole", type='BOOLEAN')
bool_mod.operation = 'DIFFERENCE'
bool_mod.object = cylinder
bpy.ops.object.modifier_apply(modifier="CutHole")

# Delete the cylinder
bpy.ops.object.select_all(action='DESELECT')
cylinder.select_set(True)
bpy.ops.object.delete()

# Export
bpy.ops.export_mesh.stl(filepath="blender_cube.stl")
print("Blender: Successfully generated blender_cube.stl")
