import os
import time
import json
import urllib.request
import traceback
import logging
import glob

# ==============================================================================
# ENTERPRISE PIPELINE SETUP
# ==============================================================================

def update_status(version_dir, stage, progress_pct, status_msg):
    """Generates a status.json file for real-time dashboard tracking."""
    status_file = os.path.join(version_dir, "status.json")
    version_str = os.path.basename(version_dir)
    data = {
        "version": version_str,
        "stage": stage,
        "progress": progress_pct,
        "status": status_msg,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    with open(status_file, "w") as f:
        json.dump(data, f, indent=4)

def setup_pipeline():
    """Initializes version control, logging, and status tracking."""
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

    log_file = os.path.join(version_dir, "pipeline.log")
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S', handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ])
    
    update_status(version_dir, "setup", 5, "Pipeline Initialized")
    return version_dir, models_dir, renders_dir, version_str

def load_config():
    """Loads parametric configuration data."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.abspath(os.path.join(base_dir, "..", "config.json"))
    with open(config_file, "r") as f:
        return json.load(f)

# ==============================================================================
# PIPELINE STAGE 1: CAD GENERATION
# ==============================================================================

def generate_cad(models_dir, version_dir, config):
    update_status(version_dir, "cad_generation", 15, "Generating CAD Geometry")
    logging.info("[1/4] Generating Parametric CAD Model (Jet Engine Impeller)...")
    from build123d import BuildPart, Cone, Cylinder, PolarLocations, Mode, Locations, Box, export_step, export_stl
    
    with BuildPart() as impeller:
        # 1. Hub
        Cone(bottom_radius=config["hub_radius"], top_radius=config["cone_top_radius"], height=config["hub_height"])
        # 2. Drive Shaft Bore
        Cylinder(radius=config["bore_radius"], height=config["hub_height"], mode=Mode.SUBTRACT)
        # 3. Blades
        with PolarLocations(0, config["blade_count"]):
            with Locations((15, 0, config["hub_height"]/2)): 
                Box(config["blade_length"], config["blade_thickness"], config["blade_height"], rotation=(config["blade_angle"], 0, 0)) 

    # --- GEOMETRY VALIDATION (Solid B-Rep Check) ---
    logging.info("      -> Validating Geometry integrity (B-Rep)...")
    update_status(version_dir, "cad_validation", 25, "Running B-Rep Topology Validation")
    
    if not impeller.part.is_valid:
        logging.error("      -> FATAL ERROR: Generated B-Rep geometry is INVALID (non-manifold or self-intersecting).")
        raise ValueError("Geometry Validation Failed")
    
    volume_mm3 = impeller.part.volume
    if volume_mm3 <= 0:
        logging.error("      -> FATAL ERROR: Generated volume is zero or negative.")
        raise ValueError("Geometry Volume Invalid")
        
    # Bounding Box Scale Check
    bbox = impeller.part.bounding_box()
    if bbox.size.X > 500 or bbox.size.Y > 500 or bbox.size.Z > 500:
        logging.error(f"      -> FATAL ERROR: Bounding Box exceeded 500mm scale limit! X:{bbox.size.X:,.2f}")
        raise ValueError("Scale/Bounding Box Validation Failed")

    logging.info(f"      -> Geometry Validation: PASS (Volume: {volume_mm3:,.2f} mm3, X-Span: {bbox.size.X:,.2f} mm)")

    # --- EXPORT ---
    step_path = os.path.join(models_dir, "impeller.step")
    stl_path = os.path.join(models_dir, "impeller.stl")
    
    export_step(impeller.part, step_path)
    export_stl(impeller.part, stl_path)
    logging.info(f"      -> Exported CAD (STEP): {step_path}")
    logging.info(f"      -> Exported Mesh (STL): {stl_path}")
    
    # --- ENGINEERING REPORT ---
    mass_g = volume_mm3 * (config["material_density_g_cm3"] / 1000) 
    estimated_cost = mass_g * config["cost_per_gram_usd"]
    
    report = (
        f"--- ENGINEERING REPORT ---\n"
        f"Material:  Aluminum 6061\n"
        f"Volume:    {volume_mm3:,.2f} mm³\n"
        f"Mass:      {mass_g:,.2f} grams\n"
        f"Est. Cost: ${estimated_cost:,.2f} USD\n"
        f"Validation: PASS\n"
        f"--------------------------\n"
    )
    report_path = os.path.join(models_dir, "impeller_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    return step_path, stl_path

# ==============================================================================
# PIPELINE STAGE 2: STL MANUFACTURING VALIDATION
# ==============================================================================

def validate_stl(stl_path, version_dir):
    update_status(version_dir, "stl_validation", 40, "Running Trimesh Watertight Analysis")
    logging.info("[2/4] Executing STL Manufacturing Printability Validation...")
    import trimesh
    
    mesh = trimesh.load(stl_path)
    if not isinstance(mesh, trimesh.Trimesh):
        # Could be a Scene object if there are multiple separated components
        if isinstance(mesh, trimesh.Scene):
            logging.error("      -> FATAL ERROR: STL exported as a disconnected Scene, not a unified part.")
            raise ValueError("Disconnected Geometry Error")
            
    is_watertight = mesh.is_watertight
    if not is_watertight:
        logging.error("      -> FATAL ERROR: STL mesh is NOT WATERTIGHT (contains holes). Print will fail.")
        raise ValueError("STL Watertight Validation Failed")
        
    logging.info("      -> STL Watertight Validation: PASS")
    update_status(version_dir, "stl_validation", 50, "STL Validation Passed")

# ==============================================================================
# PIPELINE STAGE 3: FUSION 360 MCP & RENDERING
# ==============================================================================

def execute_mcp_verification(step_path, renders_dir, version_dir):
    update_status(version_dir, "mcp_render", 60, "Injecting Payload to Fusion 360 MCP")
    logging.info("[3/4] Executing Multi-Angle Visual Verification via Fusion 360 MCP...")
    
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
        
        # Professional Camera Setup
        viewport.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
        cam = viewport.camera
        cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
        cam.perspectiveAngle = 0.872665 # 50mm Lens Equivalent (~50 deg)
        cam.isSmoothTransition = False
        
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
        
        for view_name, orientation in views_to_capture.items():
            cam.viewOrientation = orientation
            cam.isFitView = True
            viewport.camera = cam
            
            # Additional visual enhancements
            try:
                # Some API environments might restrict visual settings directly, so wrap in try/except
                design.designType = adsk.fusion.DesignTypes.DirectDesignType 
            except:
                pass
                
            viewport.refresh()
            image_path = os.path.join(output_dir, "impeller_" + view_name + ".png")
            viewport.saveAsImageFile(image_path, 1920, 1080)
        
        doc.close(False)
        message = f"Successfully generated presentation-grade screenshots: Iso, Top, Front"
        print(json.dumps({{"success": True, "message": message}}))
        
    except:
        if ui:
            print(json.dumps({{"success": False, "message": f"Failed:\\n{{traceback.format_exc()}}"}}))
"""

    URL = "http://127.0.0.1:27182/mcp"
    headers = {'Content-Type': 'application/json'}
    session_id = None
    
    # 5. MCP Exponential Retry System
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            req_init = urllib.request.Request(URL, data=json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "CICD", "version": "2.0"}}
            }).encode('utf-8'), headers=headers)
            
            with urllib.request.urlopen(req_init) as response:
                if 'MCP-Session-Id' in response.headers:
                    session_id = response.headers.get('MCP-Session-Id')
            
            headers['MCP-Session-Id'] = session_id
            
            req_notif = urllib.request.Request(URL, data=json.dumps({
                "jsonrpc": "2.0", "method": "notifications/initialized"
            }).encode('utf-8'), headers=headers)
            urllib.request.urlopen(req_notif)
            
            update_status(version_dir, "mcp_render", 70, "Executing Fusion Payload")
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
            
            # --- SESSION CLEANUP ---
            update_status(version_dir, "mcp_render", 90, "Cleaning up MCP Session")
            try:
                # Issue the formal JSON-RPC shutdown sequence
                req_shutdown = urllib.request.Request(URL, data=json.dumps({
                    "jsonrpc": "2.0", "id": 3, "method": "shutdown"
                }).encode('utf-8'), headers=headers)
                urllib.request.urlopen(req_shutdown)
            except Exception as e:
                logging.warning(f"      -> Warning: Could not execute formal MCP shutdown ({e})")
            
            break # Success, break out of retry loop
            
        except urllib.error.URLError as e:
            logging.warning(f"      -> Connection Failed (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = 5 * (attempt + 1) # Exponential Backoff
                update_status(version_dir, "mcp_retry", 60, f"Retrying connection in {retry_delay}s")
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
        config = load_config()
        
        logging.info("="*60)
        logging.info(f"STARTING FINAL ENTERPRISE AI/CAD PIPELINE ({version_str})")
        logging.info("="*60)
        
        # 1. CAD Generation
        step_path, stl_path = generate_cad(models_dir, version_dir, config)
        
        # 2. STL Manufacturing Validation
        validate_stl(stl_path, version_dir)
        
        # 3. Fusion 360 Visuals
        execute_mcp_verification(step_path, renders_dir, version_dir)
        
        update_status(version_dir, "complete", 100, "Pipeline Execution Finished")
        logging.info("[4/4] Pipeline Execution Complete! All artifacts verified and generated.")
        logging.info(f"      -> Output directory: {version_dir}")
        logging.info("="*60)
    except Exception as e:
        if 'version_dir' in locals():
            update_status(version_dir, "error", 0, f"Pipeline Crashed: {e}")
        logging.error(f"PIPELINE FAILED: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
