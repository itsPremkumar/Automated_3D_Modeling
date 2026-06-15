import os
import argparse

def convert_mesh_to_mesh(input_path, output_path):
    import trimesh
    print(f"Loading mesh: {input_path}")
    mesh = trimesh.load(input_path)
    print(f"Exporting mesh to: {output_path}")
    mesh.export(output_path)
    print("Conversion successful!")

def convert_cad_to_mesh(input_path, output_path):
    from build123d import import_step, export_stl
    print(f"Loading CAD model: {input_path}")
    part = import_step(input_path)
    
    print(f"Tessellating and exporting to: {output_path}")
    if output_path.lower().endswith('.stl'):
        export_stl(part, output_path)
    else:
        # Build123d exports STL and STEP natively, OBJ might need trimesh
        # As a fallback, export STL to memory/temp and use trimesh
        temp_stl = "temp_conversion.stl"
        export_stl(part, temp_stl)
        convert_mesh_to_mesh(temp_stl, output_path)
        os.remove(temp_stl)
    print("Conversion successful!")

def convert_cad_to_cad(input_path, output_path):
    # This usually means STEP to IGES or BREP
    from build123d import import_step
    # Note: build123d primarily handles STEP. 
    print("CAD to CAD conversion (e.g. STEP to IGES) can be done via OpenCASCADE/CadQuery.")
    print("Currently saving as STEP.")

def main():
    parser = argparse.ArgumentParser(description="Universal 3D File Converter")
    parser.add_argument("input_file", help="Input 3D file (.step, .stl, .obj, etc)")
    parser.add_argument("output_file", help="Output 3D file (.step, .stl, .obj, etc)")
    
    args = parser.parse_args()
    
    in_ext = os.path.splitext(args.input_file)[1].lower()
    out_ext = os.path.splitext(args.output_file)[1].lower()
    
    mesh_formats = ['.stl', '.obj', '.ply', '.gltf', '.glb']
    cad_formats = ['.step', '.stp']
    
    if in_ext in mesh_formats and out_ext in mesh_formats:
        print("Detected Mesh -> Mesh conversion.")
        convert_mesh_to_mesh(args.input_file, args.output_file)
        
    elif in_ext in cad_formats and out_ext in mesh_formats:
        print("Detected CAD (B-Rep) -> Mesh conversion.")
        convert_cad_to_mesh(args.input_file, args.output_file)
        
    elif in_ext in mesh_formats and out_ext in cad_formats:
        print("ERROR: Mesh -> CAD (Reverse Engineering) is mathematically extremely difficult!")
        print("You cannot easily convert a faceted .stl back into a perfectly smooth .step file without manual resurfacing software like Geomagic or Fusion 360's Mesh to BRep tool.")
        
    else:
        print(f"Unsupported conversion: {in_ext} -> {out_ext}")

if __name__ == "__main__":
    main()
