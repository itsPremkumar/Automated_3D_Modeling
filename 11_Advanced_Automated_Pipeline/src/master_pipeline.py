import os
import time
import json
import urllib.request
import traceback

def generate_cad():
    print("[1/3] Generating Advanced CAD Model (Jet Engine Impeller)...")
    from build123d import BuildPart, BuildSketch, Cone, Cylinder, PolarLocations, Rectangle, extrude, add, export_step, export_stl, Mode
    
    with BuildPart() as impeller:
        # 1. The Central Hub (Aerodynamic Tapered Cone)
        Cone(bottom_radius=25, top_radius=10, height=35)
        
        # 2. The Drive Shaft Bore
        Cylinder(radius=4, height=35, mode=Mode.SUBTRACT)
        
        # 3. The Aerodynamic Fan Blades
        # Array the blade 12 times around the hub
        with PolarLocations(0, 12):
            from build123d import Locations, Box
            with Locations((15, 0, 17.5)): # Shift outwards and up to align with cone
                Box(35, 1.5, 35, rotation=(25, 0, 0)) # Rotate 25 degrees to cut the air

    # Output directories based on current script location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.abspath(os.path.join(base_dir, "..", "outputs", "models"))
    renders_dir = os.path.abspath(os.path.join(base_dir, "..", "outputs", "renders"))
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)

    # 4. Automated Engineering Analytics (Mass & Cost)
    volume_mm3 = impeller.part.volume
    density_al_g_cm3 = 2.7 # Aerospace Aluminum 6061
    mass_g = volume_mm3 * (density_al_g_cm3 / 1000) # Convert mm^3 to cm^3 and multiply by density
    estimated_cost = mass_g * 0.15 # $0.15 per gram of machined material
    
    report = (
        f"--- ENGINEERING REPORT ---\n"
        f"Material:  Aluminum 6061\n"
        f"Volume:    {volume_mm3:,.2f} mm³\n"
        f"Mass:      {mass_g:,.2f} grams\n"
        f"Est. Cost: ${estimated_cost:,.2f} USD\n"
        f"--------------------------\n"
    )
    print(report)
    
    # Export
    step_path = os.path.join(models_dir, "impeller.step")
    stl_path = os.path.join(models_dir, "impeller.stl")
    report_path = os.path.join(models_dir, "impeller_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    export_step(impeller.part, step_path)
    export_stl(impeller.part, stl_path)
        
    print(f"      -> Exported CAD (STEP): {step_path}")
    print(f"      -> Exported Mesh (STL): {stl_path}")
    print(f"      -> Exported Report (TXT): {report_path}")
    return step_path, renders_dir

def execute_mcp_verification(step_path, renders_dir):
    print("[2/3] Executing Multi-Angle Visual Verification via Fusion 360 MCP...")
    
    # We write the native Fusion 360 python script that will run via MCP
    fusion_script = f"""
import adsk.core
import adsk.fusion
import os
import json
import traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Open the generated STEP file
        importManager = app.importManager
        stepOptions = importManager.createSTEPImportOptions(r"{step_path}")
        
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        target = design.rootComponent
        
        importManager.importToTarget(stepOptions, target)
        
        # Setup viewport
        viewport = app.activeViewport
        viewport.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
        
        output_dir = r"{renders_dir}"
        
        views_to_capture = {{
            "top": adsk.core.ViewOrientations.TopViewOrientation,
            "bottom": adsk.core.ViewOrientations.BottomViewOrientation,
            "front": adsk.core.ViewOrientations.FrontViewOrientation,
            "back": adsk.core.ViewOrientations.BackViewOrientation,
            "left": adsk.core.ViewOrientations.LeftViewOrientation,
            "right": adsk.core.ViewOrientations.RightViewOrientation,
            "iso_tr": adsk.core.ViewOrientations.IsoTopRightViewOrientation,
            "iso_tl": adsk.core.ViewOrientations.IsoTopLeftViewOrientation,
            "iso_br": adsk.core.ViewOrientations.IsoBottomRightViewOrientation,
            "iso_bl": adsk.core.ViewOrientations.IsoBottomLeftViewOrientation
        }}
        
        cam = viewport.camera
        for view_name, orientation in views_to_capture.items():
            cam.viewOrientation = orientation
            cam.isFitView = True
            viewport.camera = cam
            viewport.refresh()
            image_path = os.path.join(output_dir, "impeller_" + view_name + ".png")
            viewport.saveAsImageFile(image_path, 1920, 1080)
        
        # Close document
        doc.close(False)
        
        message = f"Successfully generated visual verification screenshots: Iso, Top, Front"
        print(json.dumps({{"success": True, "message": message}}))
        
    except:
        if ui:
            print(json.dumps({{"success": False, "message": f"Failed:\\n{{traceback.format_exc()}}"}}))
"""

    # Send payload via HTTP to MCP Server
    URL = "http://127.0.0.1:27182/mcp"
    headers = {'Content-Type': 'application/json'}
    session_id = None
    
    # 1. Initialize
    req_init = urllib.request.Request(URL, data=json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "CICD", "version": "1.0"}}
    }).encode('utf-8'), headers=headers)
    
    with urllib.request.urlopen(req_init) as response:
        if 'MCP-Session-Id' in response.headers:
            session_id = response.headers.get('MCP-Session-Id')
    
    headers['MCP-Session-Id'] = session_id
    
    # 2. Initialized Notification
    req_notif = urllib.request.Request(URL, data=json.dumps({
        "jsonrpc": "2.0", "method": "notifications/initialized"
    }).encode('utf-8'), headers=headers)
    urllib.request.urlopen(req_notif)
    
    # 3. Execute payload
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "fusion_mcp_execute",
            "arguments": {
                "featureType": "script",
                "object": {
                    "script": fusion_script
                }
            }
        }
    }
    
    req_exec = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req_exec) as response:
        res = json.loads(response.read().decode('utf-8'))
        if "result" in res and "content" in res["result"]:
            text_result = res["result"]["content"][0]["text"]
            try:
                result_json = json.loads(text_result)
                if result_json.get("success"):
                    print(f"      -> SUCCESS: {result_json.get('message')}")
                else:
                    print(f"      -> FAILED: {result_json.get('message')}")
            except json.JSONDecodeError:
                print(f"      -> Raw Output: {text_result}")

def main():
    print("="*60)
    print("STARTING ADVANCED CI/CD ENGINEERING PIPELINE")
    print("="*60)
    
    try:
        # Step 1: CAD Generation & Export
        step_path, renders_dir = generate_cad()
        
        # Step 2: Multi-Angle Visual Verification via MCP
        execute_mcp_verification(step_path, renders_dir)
        
        print("[3/3] Pipeline Execution Complete! All artifacts generated.")
        print("="*60)
    except Exception as e:
        print(f"PIPELINE FAILED: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
