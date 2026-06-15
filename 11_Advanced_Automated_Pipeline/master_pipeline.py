import os
import time
import json
import urllib.request
import traceback

def generate_cad():
    print("[1/3] Generating Parametric CAD Model (Spur Gear)...")
    from build123d import BuildPart, Cylinder, PolarLocations, Box, extrude, export_step, export_stl, Mode
    
    # Parametric definitions
    teeth = 20
    module = 2
    pitch_radius = (teeth * module) / 2
    thickness = 10
    hole_radius = 5
    
    with BuildPart() as gear:
        # Base cylinder
        Cylinder(radius=pitch_radius, height=thickness)
        # Cut center hole
        Cylinder(radius=hole_radius, height=thickness, mode=Mode.SUBTRACT)
        # Add teeth
        with PolarLocations(pitch_radius, teeth):
            Box(module*2.5, module*2.5, thickness)

    # Export
    step_path = os.path.abspath("gear.step")
    stl_path = os.path.abspath("gear.stl")
    export_step(gear.part, step_path)
    export_stl(gear.part, stl_path)
    print(f"      -> Exported CAD (STEP): {step_path}")
    print(f"      -> Exported Mesh (STL): {stl_path}")
    return step_path

def execute_mcp_verification(step_path):
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
        
        output_dir = r"{os.path.dirname(step_path)}"
        
        # 1. Isometric View
        cam = viewport.camera
        cam.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
        cam.isFitView = True
        viewport.camera = cam
        viewport.refresh()
        iso_path = os.path.join(output_dir, "gear_iso.png")
        viewport.saveAsImageFile(iso_path, 1920, 1080)
        
        # 2. Top View
        cam.viewOrientation = adsk.core.ViewOrientations.TopViewOrientation
        cam.isFitView = True
        viewport.camera = cam
        viewport.refresh()
        top_path = os.path.join(output_dir, "gear_top.png")
        viewport.saveAsImageFile(top_path, 1920, 1080)
        
        # 3. Front View
        cam.viewOrientation = adsk.core.ViewOrientations.FrontViewOrientation
        cam.isFitView = True
        viewport.camera = cam
        viewport.refresh()
        front_path = os.path.join(output_dir, "gear_front.png")
        viewport.saveAsImageFile(front_path, 1920, 1080)
        
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
        step_path = generate_cad()
        
        # Step 2: Multi-Angle Visual Verification via MCP
        execute_mcp_verification(step_path)
        
        print("[3/3] Pipeline Execution Complete! All artifacts generated.")
        print("="*60)
    except Exception as e:
        print(f"PIPELINE FAILED: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
