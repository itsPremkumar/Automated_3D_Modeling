from build123d import *

# Pillow Block Bearing Parameters
base_length = 80.0
base_width = 30.0
base_thickness = 10.0
mount_hole_dist = 60.0
mount_hole_dia = 8.0

bearing_od = 22.0
bearing_width = 7.0
shaft_clearance = 12.0
center_height = 25.0

with BuildPart() as pillow_block:
    # 1. Base
    with BuildSketch(Plane.XY) as base_sketch:
        Rectangle(base_length, base_width)
    extrude(amount=base_thickness)
    
    # Base Mounting Holes
    with Locations(pillow_block.faces().sort_by(Axis.Z)[-1]):
        with Locations((-mount_hole_dist/2, 0), (mount_hole_dist/2, 0)):
            Hole(radius=mount_hole_dia/2)
            
    # 2. Upright Housing
    with BuildSketch(pillow_block.faces().sort_by(Axis.Z)[-1]) as upright_base:
        Rectangle(bearing_od + 14, base_width)
    extrude(amount=center_height - base_thickness + bearing_od/2 + 4)
    
    # 3. Fillets on the upright housing to make it rounded at the top
    top_edges = pillow_block.edges().filter_by(Axis.Y).sort_by(Axis.Z)[-2:]
    fillet(top_edges, radius=(bearing_od + 14) / 2 - 0.1)

    # 4. Bearing Bore
    # Create the bore on the XZ plane, so the hole runs along the Y axis
    with BuildSketch(Plane.XZ) as bore_sketch:
        with Locations((0, center_height)):
            Circle(bearing_od/2)
    # Extrude the bore using SUBTRACT
    extrude(amount=bearing_width/2, both=True, mode=Mode.SUBTRACT)
    
    # 5. Shaft clearance bore (goes all the way through)
    with BuildSketch(Plane.XZ) as shaft_sketch:
        with Locations((0, center_height)):
            Circle(shaft_clearance/2)
    extrude(amount=base_width, both=True, mode=Mode.SUBTRACT)

# Export to standard formats
export_step(pillow_block.part, "pillow_block.step")
export_stl(pillow_block.part, "pillow_block.stl")
print("Pillow block generated successfully!")
