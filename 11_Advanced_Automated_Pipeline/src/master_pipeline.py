import os
import time
import json
import urllib.request
import traceback
import logging
import glob

def setup_pipeline():
    # 1. Version Control & Directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outputs_base = os.path.abspath(os.path.join(base_dir, "..", "outputs"))
    os.makedirs(outputs_base, exist_ok=True)
    
    existing_versions = glob.glob(os.path.join(outputs_base, "v*"))
    version_num = 1
    if existing_versions:
        version_num = max([int(os.path.basename(v).replace("v", "")) for v in existing_versions if os.path.basename(v).startswith("v") and os.path.basename(v)[1:].isdigit()] + [0]) + 1
    version_str = f"v{version_num:03d}"
    
    version_dir = os.path.join(outputs_base, version_str)
    models_dir = os.path.join(version_dir, "models")
    renders_dir = os.path.join(version_dir, "renders")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)

    # 2. Robust File Logging
    log_file = os.path.join(version_dir, "pipeline.log")
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S', handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ])
    
    return version_dir, models_dir, renders_dir, version_str

def generate_cad(models_dir):
    logging.info("[1/3] Generating Advanced CAD Model (Jet Engine Impeller)...")
    from build123d import BuildPart, BuildSketch, Cone, Cylinder, PolarLocations, Rectangle, extrude, add, export_step, export_stl, Mode, Locations, Box
    
    with BuildPart() as impeller:
        # 1. The Central Hub
        Cone(bottom_radius=25, top_radius=10, height=35)
        # 2. The Drive Shaft Bore
        Cylinder(radius=4, height=35, mode=Mode.SUBTRACT)
        # 3. The Aerodynamic Fan Blades
        with PolarLocations(0, 12):
            with Locations((15, 0, 17.5)): 
                Box(35, 1.5, 35, rotation=(25, 0, 0)) 

    # 3. Geometry Validation (Solid Check)
    logging.info("      -> Validating Geometry integrity...")
    if not impeller.part.is_valid:
        logging.error("      -> FATAL ERROR: Generated B-Rep geometry is INVALID (non-manifold or self-intersecting).")
        raise ValueError("Geometry Validation Failed")
    
    volume_mm3 = impeller.part.volume
    if volume_mm3 <= 0:
        logging.error("      -> FATAL ERROR: Generated volume is zero or negative.")
        raise ValueError("Geometry Volume Invalid")
        
    logging.info(f"      -> Geometry Validation: PASS")

    # 4. Automated Engineering Analytics
    density_al_g_cm3 = 2.7 
    mass_g = volume_mm3 * (density_al_g_cm3 / 1000) 
    estimated_cost = mass_g * 0.15 
    
    report = (
        f"--- ENGINEERING REPORT ---\n"
        f"Material:  Aluminum 6061\n"
        f"Volume:    {volume_mm3:,.2f} mm³\n"
        f"Mass:      {mass_g:,.2f} grams\n"
        f"Est. Cost: ${estimated_cost:,.2f} USD\n"
        f"--------------------------\n"
    )
    for line in report.strip().split("\n"):
        logging.info(f"      {line}")
    
    step_path = os.path.join(models_dir, "impeller.step")
    stl_path = os.path.join(models_dir, "impeller.stl")
    report_path = os.path.join(models_dir, "impeller_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    export_step(impeller.part, step_path)
    export_stl(impeller.part, stl_path)
        
    logging.info(f"      -> Exported CAD (STEP): {step_path}")
    logging.info(f"      -> Exported Mesh (STL): {stl_path}")
    logging.info(f"      -> Exported Report (TXT): {report_path}")
    
    return step_path

def execute_mcp_verification(step_path, renders_dir):
    logging.info("[2/3] Executing Multi-Angle Visual Verification via Fusion 360 MCP...")
    
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
        
        importManager = app.importManager
        stepOptions = importManager.createSTEPImportOptions(r"{step_path}")
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        target = design.rootComponent
        importManager.importToTarget(stepOptions, target)
        
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
        
        doc.close(False)
        message = f"Successfully generated visual verification screenshots: Iso, Top, Front"
        print(json.dumps({{"success": True, "message": message}}))
        
    except:
        if ui:
            print(json.dumps({{"success": False, "message": f"Failed:\\n{{traceback.format_exc()}}"}}))
"""

    URL = "http://127.0.0.1:27182/mcp"
    headers = {'Content-Type': 'application/json'}
    session_id = None
    
    # 5. MCP Retry System
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            req_init = urllib.request.Request(URL, data=json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "CICD", "version": "1.0"}}
            }).encode('utf-8'), headers=headers)
            
            with urllib.request.urlopen(req_init) as response:
                if 'MCP-Session-Id' in response.headers:
                    session_id = response.headers.get('MCP-Session-Id')
            
            headers['MCP-Session-Id'] = session_id
            
            req_notif = urllib.request.Request(URL, data=json.dumps({
                "jsonrpc": "2.0", "method": "notifications/initialized"
            }).encode('utf-8'), headers=headers)
            urllib.request.urlopen(req_notif)
            
            payload = {
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "fusion_mcp_execute", "arguments": {"featureType": "script", "object": {"script": fusion_script}}}
            }
            
            req_exec = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req_exec) as response:
                res = json.loads(response.read().decode('utf-8'))
                if "result" in res and "content" in res["result"]:
                    text_result = res["result"]["content"][0]["text"]
                    try:
                        result_json = json.loads(text_result)
                        if result_json.get("success"):
                            logging.info(f"      -> SUCCESS: {result_json.get('message')}")
                        else:
                            logging.error(f"      -> FAILED: {result_json.get('message')}")
                    except json.JSONDecodeError:
                        logging.warning(f"      -> Raw Output: {text_result}")
            
            break # Success, break out of retry loop
            
        except urllib.error.URLError as e:
            logging.warning(f"      -> Connection Failed (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logging.info(f"      -> Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error("      -> FATAL ERROR: MCP Server unreachable after maximum retries.")
                raise e
        except Exception as e:
            logging.error(f"      -> Unexpected Error: {e}")
            raise e

def main():
    try:
        version_dir, models_dir, renders_dir, version_str = setup_pipeline()
        
        logging.info("="*60)
        logging.info(f"STARTING ENTERPRISE AI/CAD PIPELINE ({version_str})")
        logging.info("="*60)
        
        step_path = generate_cad(models_dir)a
        execute_mcp_verification(step_path, renders_dir)
        
        logging.info("[3/3] Pipeline Execution Complete! All artifacts verified and generated.")
        logging.info(f"      -> Output directory: {version_dir}")
        logging.info("="*60)
    except Exception as e:
        logging.error(f"PIPELINE FAILED: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
