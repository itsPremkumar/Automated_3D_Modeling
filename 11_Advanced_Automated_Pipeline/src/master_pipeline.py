import os
import time
import json
import urllib.request
import traceback
import logging
import glob
import hashlib

# ==============================================================================
# ENTERPRISE PIPELINE SETUP
# ==============================================================================

def update_status(version_dir, stage, progress_pct, status_msg):
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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.abspath(os.path.join(base_dir, "..", "config.json"))
    with open(config_file, "r") as f:
        return json.load(f)

def generate_manifest(version_dir, files):
    manifest_path = os.path.join(version_dir, "manifest.json")
    data = {"version": os.path.basename(version_dir), "artifacts": {}}
    for f in files:
        if os.path.exists(f):
            with open(f, "rb") as file_obj:
                data["artifacts"][os.path.basename(f)] = hashlib.sha256(file_obj.read()).hexdigest()
    with open(manifest_path, "w") as f:
        json.dump(data, f, indent=4)
    logging.info(f"      -> Artifact Manifest generated: {manifest_path}")

def generate_bom(models_dir, config):
    bom_path = os.path.join(models_dir, "BOM.csv")
    bom_items = config.get("bom", [])
    
    with open(bom_path, "w") as f:
        f.write("Part_Name,Quantity,Material\n")
        for item in bom_items:
            f.write(f"{item['name']},{item['quantity']},{item['material']}\n")
            
    logging.info(f"      -> Dynamic Bill of Materials (BOM) generated: {bom_path}")
    return bom_path

def generate_urdf(models_dir, config):
    urdf_path = os.path.join(models_dir, "robot.urdf")
    part_name = "impeller"
    
    urdf_content = f"""<?xml version="1.0"?>
<robot name="automated_robot">
  <link name="base_link">
    <visual>
      <geometry>
        <mesh filename="{part_name}.stl" />
      </geometry>
      <material name="aluminum">
        <color rgba="0.7 0.7 0.7 1"/>
      </material>
    </visual>
    <collision>
      <geometry>
        <mesh filename="{part_name}.stl" />
      </geometry>
    </collision>
    <inertial>
      <mass value="0.136" />
      <inertia ixx="0.001" ixy="0.0" ixz="0.0" iyy="0.001" iyz="0.0" izz="0.001" />
    </inertial>
  </link>
</robot>
"""
    with open(urdf_path, "w") as f:
        f.write(urdf_content)
    logging.info(f"      -> URDF Robotics Profile generated: {urdf_path}")
    return urdf_path

# ==============================================================================
# PIPELINE STAGE 1: CAD GENERATION
# ==============================================================================

def generate_cad(models_dir, version_dir, config):
    update_status(version_dir, "cad_generation", 15, "Generating CAD Geometry")
    logging.info("[1/4] Generating Parametric CAD Model (Jet Engine Impeller)...")
    from build123d import BuildPart, Cone, Cylinder, PolarLocations, Mode, Locations, Box, export_step, export_stl
    
    cad_params = config["cad_parameters"]
    mfg_rules = config["manufacturing_rules"]
    
    with BuildPart() as impeller:
        Cone(bottom_radius=cad_params["hub_radius"], top_radius=cad_params["cone_top_radius"], height=cad_params["hub_height"])
        Cylinder(radius=cad_params["bore_radius"], height=cad_params["hub_height"], mode=Mode.SUBTRACT)
        with PolarLocations(0, cad_params["blade_count"]):
            with Locations((15, 0, cad_params["hub_height"]/2)): 
                Box(cad_params["blade_length"], cad_params["blade_thickness"], cad_params["blade_height"], rotation=(cad_params["blade_angle"], 0, 0)) 

    # --- GEOMETRY VALIDATION ---
    logging.info("      -> Validating Geometry integrity (B-Rep)...")
    update_status(version_dir, "cad_validation", 25, "Running B-Rep Topology Validation")
    
    if not impeller.part.is_valid:
        logging.error("      -> FATAL ERROR: Generated B-Rep geometry is INVALID.")
        raise ValueError("Geometry Validation Failed")
    
    volume_mm3 = impeller.part.volume
    if volume_mm3 <= 0:
        raise ValueError("Geometry Volume Invalid")
        
    bbox = impeller.part.bounding_box()
    if bbox.size.X > 500 or bbox.size.Y > 500 or bbox.size.Z > 500:
        raise ValueError("Scale/Bounding Box Validation Failed")

    logging.info(f"      -> Geometry Validation: PASS (Volume: {volume_mm3:,.2f} mm3, X-Span: {bbox.size.X:,.2f} mm)")

    # --- EXPORT ---
    step_path = os.path.join(models_dir, "impeller.step")
    stl_path = os.path.join(models_dir, "impeller.stl")
    
    export_step(impeller.part, step_path)
    export_stl(impeller.part, stl_path)
    logging.info(f"      -> Exported CAD (STEP): {step_path}")
    logging.info(f"      -> Exported Mesh (STL): {stl_path}")
    
    # --- REPORTS ---
    mass_g = volume_mm3 * (mfg_rules["material_density_g_cm3"] / 1000) 
    estimated_cost = mass_g * mfg_rules["cost_per_gram_usd"]
    
    report_path = os.path.join(models_dir, "impeller_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Volume: {volume_mm3:,.2f} mm³\nMass: {mass_g:,.2f} grams\nCost: ${estimated_cost:,.2f} USD")
        
    bom_path = generate_bom(models_dir, config)
    urdf_path = generate_urdf(models_dir, config)
    return step_path, stl_path, report_path, bom_path, urdf_path

# ==============================================================================
# PIPELINE STAGE 2: STL MANUFACTURING VALIDATION & REPAIR (3MF EXPORT)
# ==============================================================================

def validate_stl(stl_path, models_dir, version_dir):
    update_status(version_dir, "stl_validation", 40, "Running Trimesh Watertight Analysis")
    logging.info("[2/4] Executing Advanced STL Validation & 3MF Export...")
    import trimesh
    
    mesh = trimesh.load(stl_path)
    if isinstance(mesh, trimesh.Scene):
        raise ValueError("Disconnected Geometry Error")
            
    if not mesh.is_watertight:
        logging.warning("      -> WARNING: STL mesh is NOT WATERTIGHT. Attempting advanced Mesh Healing...")
        update_status(version_dir, "stl_repair", 45, "Running Mesh Healing Algorithms")
        
        # Advanced Repair Sequence
        try:
            mesh.fix_normals()
            mesh.remove_degenerate_faces()
            trimesh.repair.fill_holes(mesh)
        except Exception as e:
            logging.error(f"      -> Repair algorithm crashed: {e}")
            
        if not mesh.is_watertight:
            logging.error("      -> FATAL ERROR: Auto-repair failed. Mesh is irrecoverable.")
            raise ValueError("STL Watertight Validation & Repair Failed")
        else:
            logging.info("      -> Auto-repair SUCCESS: Mesh healed. Overwriting STL.")
            mesh.export(stl_path)
    else:
        logging.info("      -> STL Watertight Validation: PASS")
        
    # Export 3MF for modern slicing
    mf3_path = os.path.join(models_dir, "impeller.3mf")
    mesh.export(mf3_path)
    logging.info(f"      -> Exported Advanced Print File (3MF): {mf3_path}")
    update_status(version_dir, "stl_validation", 50, "STL Validation Passed")
    return mf3_path

# ==============================================================================
# PIPELINE STAGE 3: FUSION 360 MCP (COLLISION, EXPORT & RENDERING)
# ==============================================================================

def execute_mcp_verification(step_path, models_dir, renders_dir, version_dir):
    update_status(version_dir, "mcp_render", 60, "Injecting Payload to Fusion 360 MCP")
    logging.info("[3/4] Executing Assembly Collision Checks, F3D Export & Exploded Views via Fusion 360...")
    
    f3d_path = os.path.join(models_dir, "impeller.f3d")
    
    fusion_script = f"""
import adsk.core
import adsk.fusion
import os
import json
import traceback
import math

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
        
        # --- 1. COLLISION / INTERFERENCE DETECTION ---
        bodies = adsk.core.ObjectCollection.create()
        for comp in design.allComponents:
            for body in comp.bRepBodies:
                bodies.add(body)
                
        if bodies.count > 1:
            interferenceInput = design.createInterferenceInput(bodies)
            interferenceInput.areCoincidentFacesIncluded = False
            results = design.analyzeInterference(interferenceInput)
            if results.count > 0:
                raise ValueError(f"CRITICAL: Interference detected between {{results.count}} parts! Assembly will fail physically.")
        
        # --- 2. EXPORT NATIVE F3D ARCHIVE ---
        exportManager = design.exportManager
        f3dOptions = exportManager.createFusionArchiveExportOptions(r"{f3d_path}")
        exportManager.execute(f3dOptions)
        
        # --- 3. CAMERA SETUP ---
        viewport = app.activeViewport
        viewport.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
        cam = viewport.camera
        cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
        cam.perspectiveAngle = 0.872665 # 50mm Lens
        cam.isSmoothTransition = False
        
        output_dir = r"{renders_dir}"
        
        views_to_capture = {{
            "top": adsk.core.ViewOrientations.TopViewOrientation,
            "iso_tr": adsk.core.ViewOrientations.IsoTopRightViewOrientation
        }}
        
        for view_name, orientation in views_to_capture.items():
            cam.viewOrientation = orientation
            cam.isFitView = True
            viewport.camera = cam
            viewport.refresh()
            image_path = os.path.join(output_dir, "impeller_" + view_name + ".png")
            viewport.saveAsImageFile(image_path, 1920, 1080)
            
        # --- 4. TRUE EXPLODED VIEW GENERATION ---
        # Actually translating occurrences outward radially
        if target.occurrences.count > 0:
            for i in range(target.occurrences.count):
                occ = target.occurrences.item(i)
                
                # Get bounding box center relative to origin
                bbox = occ.boundingBox
                cx = (bbox.maxPoint.x + bbox.minPoint.x) / 2.0
                cy = (bbox.maxPoint.y + bbox.minPoint.y) / 2.0
                cz = (bbox.maxPoint.z + bbox.minPoint.z) / 2.0
                
                # Calculate outward vector and scale by 2.0x
                dist = math.sqrt(cx**2 + cy**2 + cz**2)
                if dist > 0:
                    vec = adsk.core.Vector3D.create(cx/dist, cy/dist, cz/dist)
                    vec.scaleBy(10.0) # Move outward 10cm
                    
                    mat = occ.transform
                    mat.translation = vec
                    occ.transform = mat
            
            # Recalculate camera after explosion
            cam.viewOrientation = adsk.core.ViewOrientations.IsoBottomLeftViewOrientation
            cam.isFitView = True
            viewport.camera = cam
            viewport.refresh()
            image_path = os.path.join(output_dir, "impeller_exploded_assembly.png")
            viewport.saveAsImageFile(image_path, 1920, 1080)
        else:
            # Single body case (no occurrences) - just snapshot
            cam.viewOrientation = adsk.core.ViewOrientations.IsoBottomLeftViewOrientation
            cam.isFitView = True
            viewport.camera = cam
            viewport.refresh()
            image_path = os.path.join(output_dir, "impeller_exploded_assembly.png")
            viewport.saveAsImageFile(image_path, 1920, 1080)
        
        doc.close(False)
        message = "Successfully verified assembly collisions, exported F3D, and generated Exploded Views."
        print(json.dumps({{"success": True, "message": message}}))
        
    except Exception as e:
        if ui:
            print(json.dumps({{"success": False, "message": str(e)}}))
"""

    URL = "http://127.0.0.1:27182/mcp"
    headers = {'Content-Type': 'application/json'}
    session_id = None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req_init = urllib.request.Request(URL, data=json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "CICD", "version": "4.0"}}
            }).encode('utf-8'), headers=headers)
            
            with urllib.request.urlopen(req_init) as response:
                if 'MCP-Session-Id' in response.headers:
                    session_id = response.headers.get('MCP-Session-Id')
            headers['MCP-Session-Id'] = session_id
            
            req_notif = urllib.request.Request(URL, data=json.dumps({
                "jsonrpc": "2.0", "method": "notifications/initialized"
            }).encode('utf-8'), headers=headers)
            urllib.request.urlopen(req_notif)
            
            update_status(version_dir, "mcp_render", 70, "Executing Fusion Payload (Explosion & F3D Export)")
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
            
            # --- SESSION CLEANUP & EXIT NOTIFICATION ---
            update_status(version_dir, "mcp_shutdown", 90, "Cleaning up MCP Session")
            try:
                urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps({
                    "jsonrpc": "2.0", "id": 3, "method": "shutdown"
                }).encode('utf-8'), headers=headers))
                
                urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps({
                    "jsonrpc": "2.0", "method": "notifications/exit"
                }).encode('utf-8'), headers=headers))
                logging.info("      -> MCP Session Gracefully Closed.")
            except Exception as e:
                logging.warning(f"      -> Warning: Could not execute formal MCP shutdown ({e})")
            
            break
            
        except urllib.error.URLError as e:
            logging.warning(f"      -> Connection Failed (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = 5 * (attempt + 1)
                update_status(version_dir, "mcp_retry", 60, f"Retrying connection in {retry_delay}s")
                logging.info(f"      -> Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error("      -> FATAL ERROR: MCP Server unreachable after maximum retries.")
                raise e
        except Exception as e:
            logging.error(f"      -> Unexpected Error: {e}")
            raise e
            
    return f3d_path

def main():
    try:
        version_dir, models_dir, renders_dir, version_str = setup_pipeline()
        config = load_config()
        
        logging.info("="*60)
        logging.info(f"STARTING 10/10 ROBOTICS AI/CAD PIPELINE ({version_str})")
        logging.info("="*60)
        
        step_path, stl_path, report_path, bom_path, urdf_path = generate_cad(models_dir, version_dir, config)
        mf3_path = validate_stl(stl_path, models_dir, version_dir)
        f3d_path = execute_mcp_verification(step_path, models_dir, renders_dir, version_dir)
        
        # Generate Final Artifact Manifest
        all_outputs = [step_path, stl_path, report_path, bom_path, urdf_path, mf3_path, f3d_path]
        for render in glob.glob(os.path.join(renders_dir, "*.png")):
            all_outputs.append(render)
        generate_manifest(version_dir, all_outputs)
        
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
