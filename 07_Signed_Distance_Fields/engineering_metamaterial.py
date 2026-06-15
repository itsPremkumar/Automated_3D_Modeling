import numpy as np
from skimage import measure
import trimesh

print("Generating SDF Grid for Engineering Metamaterial (Gyroid Lattice)...")

# Define grid size and resolution
resolution = 100
x, y, z = np.mgrid[-np.pi*2:np.pi*2:complex(0, resolution), 
                   -np.pi*2:np.pi*2:complex(0, resolution), 
                   -np.pi*2:np.pi*2:complex(0, resolution)]

# SDF Equation for a Gyroid surface (structural metamaterial)
# Used in aerospace engineering and heat exchangers for high strength-to-weight ratio
gyroid_sdf = np.sin(x)*np.cos(y) + np.sin(y)*np.cos(z) + np.sin(z)*np.cos(x)

# We want a thick lattice, not just a thin surface. 
# So we extract the volume where the SDF is between -0.5 and 0.5.
# By thresholding the absolute value, we get a solid network.
vol = np.abs(gyroid_sdf) - 0.5

print("Running Marching Cubes algorithm to extract B-Rep mesh from SDF...")
# Extract mesh using marching cubes at the zero-isolevel of our thickness volume
verts, faces, normals, values = measure.marching_cubes(vol, level=0.0)

print("Exporting mesh to STL...")
# Create a Trimesh object
mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)

# Scale it to a reasonable engineering dimension (e.g., 50x50x50 mm)
bounds = mesh.bounds
size = bounds[1] - bounds[0]
scale_factor = 50.0 / max(size)
mesh.apply_scale(scale_factor)

# Center it
mesh.apply_translation(-mesh.center_mass)

# Export to STL
output_filename = "gyroid_metamaterial.stl"
mesh.export(output_filename)

print(f"Success! Engineering Metamaterial saved to {output_filename}")
print(f"Mesh details: {len(verts)} vertices, {len(faces)} faces.")
