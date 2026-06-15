from build123d import *

print("Importing downloaded open-source CAD file...")
imported_part = import_step("downloaded_model.step")

print("Modifying the imported CAD part (Drilling a single hole through the center)...")
with BuildPart() as modified_model:
    add(imported_part)
    
    # Find the exact center of the model using its bounding box
    bbox = modified_model.part.bounding_box()
    center_x = bbox.min.X + (bbox.max.X - bbox.min.X) / 2
    center_y = bbox.min.Y + (bbox.max.Y - bbox.min.Y) / 2
    
    # We will drill a hole straight down the Z-axis, directly through the center
    # Find the highest Z point so we know where to start drilling from
    top_z = bbox.max.Z + 10 # Start slightly above the model
    
    # Create the hole by sketching a circle and extruding a subtraction
    with BuildSketch(Plane(origin=(center_x, center_y, top_z), z_dir=(0, 0, 1))):
        Circle(radius=5) # 10mm diameter hole
        
    # Extrude the subtraction all the way through the bounding box height
    total_height = (bbox.max.Z - bbox.min.Z) + 20
    extrude(amount=-total_height, mode=Mode.SUBTRACT)

# Export the newly modified model
export_step(modified_model.part, "holed_model.step")
export_stl(modified_model.part, "holed_model.stl")
print("Successfully drilled a single hole through the model and saved holed_model.step!")
