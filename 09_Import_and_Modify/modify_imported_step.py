from build123d import *

print("Importing downloaded CAD file...")
# 1. Import the existing STEP file
imported_part = import_step("blank_bracket.step")

print("Modifying the imported CAD part...")
with BuildPart() as modified_bracket:
    # Add the imported part into our active build context
    add(imported_part)
    
    # 2. Select the top face of the base
    # Sort faces by Z-axis to find the horizontal ones. 
    # The absolute highest face is the top of the upright. The base top face is lower.
    # We can filter faces by normal direction (0,0,1) which means pointing straight up.
    up_faces = modified_bracket.faces().filter_by(Axis.Z)
    
    # The base top face has a lower Z coordinate than the upright top face.
    # Let's sort them by Z coordinate and grab the lower one.
    top_base_face = up_faces.sort_by(Axis.Z)[0]
    
    # 3. Drill 4 mounting holes into it
    with BuildSketch(top_base_face):
        # Create a rectangular pattern of 4 holes
        with GridLocations(x_spacing=30, y_spacing=30, x_count=2, y_count=2):
            Circle(radius=3)  # 6mm diameter holes
    
    # Cut the holes all the way through the base
    extrude(amount=-20, mode=Mode.SUBTRACT)

# 4. Export the newly modified model
export_step(modified_bracket.part, "modified_bracket.step")
export_stl(modified_bracket.part, "modified_bracket.stl")
print("Successfully drilled 4 holes into the imported model and saved modified_bracket.step!")
