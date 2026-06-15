from build123d import *

print("Importing downloaded open-source CAD file...")
imported_part = import_step("downloaded_model.step")

print("Modifying the imported CAD part (Cutting it exactly in half)...")
with BuildPart() as modified_model:
    add(imported_part)
    
    # Find the exact center of the model using its bounding box
    bbox = modified_model.part.bounding_box()
    center_y = bbox.min.Y + (bbox.max.Y - bbox.min.Y) / 2
    
    # Split the model in half along the XZ plane at the center Y coordinate
    # The split operation takes a plane and a keep flag (Keep.TOP, Keep.BOTTOM, or Keep.BOTH)
    # By default, split(keep=Keep.TOP) keeps the positive side of the plane's normal.
    split_plane = Plane(origin=(0, center_y, 0), z_dir=(0, 1, 0))
    split(bisect_by=split_plane, keep=Keep.TOP)

# Export the newly modified model
export_step(modified_model.part, "half_model.step")
export_stl(modified_model.part, "half_model.stl")
print("Successfully cut the model in half and saved half_model.step!")
