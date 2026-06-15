import os
import time
import json
import urllib.request
import traceback
import logging
import glob
import hashlib

# ==============================================================================
# AI ORCHESTRATOR COMPATIBLE SETUP
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

def generate_bom(models_dir, config):
    bom_path = os.path.join(models_dir, "BOM.csv")
    bom_items = config.get("bom", [])
    with open(bom_path, "w") as f:
        f.write("Part_Name,Quantity,Material\n")
        for item in bom_items:
            f.write(f"{item['name']},{item['quantity']},{item['material']}\n")
    return bom_path

def generate_urdf(models_dir):
    urdf_path = os.path.join(models_dir, "robot.urdf")
    urdf_content = """<?xml version="1.0"?>
<robot name="servo_assembly">
  <link name="base_mount">
    <visual><geometry><mesh filename="assembly.stl" /></geometry></visual>
    <collision><geometry><mesh filename="assembly.stl" /></geometry></collision>
    <inertial><mass value="0.05" /><inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.001" /></inertial>
  </link>
  <link name="servo_arm">
    <visual><geometry><box size="0.05 0.01 0.005"/></geometry></visual>
    <collision><geometry><box size="0.05 0.01 0.005"/></geometry></collision>
    <inertial><mass value="0.01" /><inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.0001" /></inertial>
  </link>
  <joint name="main_servo_joint" type="revolute">
    <parent link="base_mount"/>
    <child link="servo_arm"/>
    <origin xyz="0 0 0.005" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-1.57" upper="1.57" effort="1.5" velocity="1.0"/>
  </joint>
</robot>
"""
    with open(urdf_path, "w") as f:
        f.write(urdf_content)
    return urdf_path

# ==============================================================================
# PIPELINE STAGE 1: ASSEMBLY CAD GENERATION & FEA PROXY
# ==============================================================================

def generate_cad(models_dir, version_dir, config):
    update_status(version_dir, "cad_generation", 15, "Generating Robotic Assembly")
    logging.info("[1/5] Generating Assembly CAD (Base Mount + Servo Arm)...")
    from build123d import Box, Location, export_step, export_stl, Compound
    
    cad_params = config["cad_parameters"]
    mfg_rules = config["manufacturing_rules"]
    
    # Generate Components
    base = Box(cad_params["base_width"], cad_params["base_length"], cad_params["base_thickness"])
    # Shift arm so it stacks on top
    arm = Box(cad_params["arm_length"], cad_params["arm_width"], cad_params["arm_thickness"])
    arm = arm.moved(Location((0, 0, (cad_params["base_thickness"] + cad_params["arm_thickness"])/2.0)))
    
    # Create Assembly
    assembly = Compound(children=[base, arm])
    
    if not assembly.is_valid:
        raise ValueError("Geometry Validation Failed")
    
    volume_mm3 = assembly.volume
    mass_g = volume_mm3 * (mfg_rules["material_density_g_cm3"] / 1000) 
    
    # --- FEA SIMULATION PROXY ---
    logging.info("[2/5] Running FEA Simulation Proxy (Bending Stress)...")
    update_status(version_dir, "simulation", 25, "Running FEA Proxy")
    
    # Proxy: Bending stress on the arm from a 5N tip load
    load_N = 5.0
    moment_Nmm = load_N * cad_params["arm_length"]
    section_modulus = (cad_params["arm_width"] * (cad_params["arm_thickness"] ** 2)) / 6.0
    stress_mpa = moment_Nmm / section_modulus
    
    fitness = {
        "mass_g": round(mass_g, 2),
        "stress_mpa": round(stress_mpa, 2),
        "target_max_stress": mfg_rules["max_allowable_stress_mpa"],
        "structurally_safe": stress_mpa < mfg_rules["max_allowable_stress_mpa"]
    }
    
    with open(os.path.join(version_dir, "fitness.json"), "w") as f:
        json.dump(fitness, f, indent=4)
        
    logging.info(f"      -> FEA Stress: {stress_mpa:.2f} MPa (Limit: {mfg_rules['max_allowable_stress_mpa']} MPa)")
    logging.info(f"      -> Mass: {mass_g:.2f} g")

    # --- EXPORT ---
    step_path = os.path.join(models_dir, "assembly.step")
    stl_path = os.path.join(models_dir, "assembly.stl")
    export_step(assembly, step_path)
    export_stl(assembly, stl_path)
    
    bom_path = generate_bom(models_dir, config)
    urdf_path = generate_urdf(models_dir)
    
    return step_path, stl_path, bom_path, urdf_path

# ==============================================================================
# PIPELINE STAGE 2: STL MANUFACTURING VALIDATION & REPAIR (3MF EXPORT)
# ==============================================================================

def validate_stl(stl_path, models_dir, version_dir):
    update_status(version_dir, "stl_validation", 40, "Running Trimesh Validation")
    logging.info("[3/5] Executing Advanced STL Validation & 3MF Export...")
    import trimesh
    
    mesh = trimesh.load(stl_path)
    if isinstance(mesh, trimesh.Scene):
        # We now expect a scene because it's an assembly! Convert to single mesh for simple printing check
        mesh = mesh.dump(concatenate=True)
            
    if not mesh.is_watertight:
        logging.warning("      -> WARNING: STL mesh is NOT WATERTIGHT. Attempting advanced Mesh Healing...")
        try:
            mesh.fix_normals()
            mesh.remove_degenerate_faces()
            trimesh.repair.fill_holes(mesh)
            mesh.export(stl_path)
        except Exception as e:
            pass

    mf3_path = os.path.join(models_dir, "assembly.3mf")
    mesh.export(mf3_path)
    return mf3_path

# ==============================================================================
# PIPELINE STAGE 3: FUSION 360 MCP (COLLISION, EXPORT & RENDERING)
# ==============================================================================

def execute_mcp_verification(step_path, models_dir, renders_dir, version_dir):
    update_status(version_dir, "mcp_render", 60, "Injecting Payload to Fusion 360 MCP")
    logging.info("[4/5] Executing Assembly Collision Checks, F3D Export & Exploded Views via Fusion 360...")
    
    f3d_path = os.path.join(models_dir, "assembly.f3d")
    
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
        cam.perspectiveAngle = 0.872665
        
        output_dir = r"{renders_dir}"
        
        # Render original
        cam.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
        cam.isFitView = True
        viewport.camera = cam
        viewport.refresh()
        viewport.saveAsImageFile(os.path.join(output_dir, "assembly_iso.png"), 1920, 1080)
            
        # --- 4. TRUE EXPLODED VIEW GENERATION ---
        if target.occurrences.count > 0:
            for i in range(target.occurrences.count):
                occ = target.occurrences.item(i)
                bbox = occ.boundingBox
                cx = (bbox.maxPoint.x + bbox.minPoint.x) / 2.0
                cy = (bbox.maxPoint.y + bbox.minPoint.y) / 2.0
                cz = (bbox.maxPoint.z + bbox.minPoint.z) / 2.0
                
                dist = math.sqrt(cx**2 + cy**2 + cz**2)
                if dist > 0.1:
                    vec = adsk.core.Vector3D.create(cx/dist, cy/dist, cz/dist)
                    vec.scaleBy(10.0)
                    mat = occ.transform
                    mat.translation = vec
                    occ.transform = mat
            
            cam.viewOrientation = adsk.core.ViewOrientations.IsoBottomLeftViewOrientation
            cam.isFitView = True
            viewport.camera = cam
            viewport.refresh()
            viewport.saveAsImageFile(os.path.join(output_dir, "assembly_exploded.png"), 1920, 1080)
        
        doc.close(False)
        print(json.dumps({{"success": True, "message": "Verified assembly collisions, exported F3D, and generated Exploded Views."}}))
        
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
            req_init = urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "CICD", "version": "4.0"}}}).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req_init) as response:
                session_id = response.headers.get('MCP-Session-Id')
            headers['MCP-Session-Id'] = session_id
            
            urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode('utf-8'), headers=headers))
            
            payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "fusion_mcp_execute", "arguments": {"featureType": "script", "object": {"script": fusion_script}}}}
            req_exec = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req_exec) as response:
                res = json.loads(response.read().decode('utf-8'))
                text_result = res["result"]["content"][0]["text"]
                try:
                    result_json = json.loads(text_result)
                    if result_json.get("success"):
                        logging.info(f"      -> SUCCESS: {result_json.get('message')}")
                    else:
                        logging.error(f"      -> FAILED: {result_json.get('message')}")
                except: pass
            
            try:
                urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "id": 3, "method": "shutdown"}).encode('utf-8'), headers=headers))
                urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "method": "notifications/exit"}).encode('utf-8'), headers=headers))
            except: pass
            break
            
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise e
    return f3d_path

def main():
    try:
        version_dir, models_dir, renders_dir, version_str = setup_pipeline()
        config = load_config()
        
        logging.info("="*60)
        logging.info(f"STARTING AI ORCHESTRATOR COMPATIBLE PIPELINE ({version_str})")
        logging.info("="*60)
        
        step_path, stl_path, bom_path, urdf_path = generate_cad(models_dir, version_dir, config)
        mf3_path = validate_stl(stl_path, models_dir, version_dir)
        f3d_path = execute_mcp_verification(step_path, models_dir, renders_dir, version_dir)
        
        all_outputs = [step_path, stl_path, bom_path, urdf_path, mf3_path, f3d_path]
        for render in glob.glob(os.path.join(renders_dir, "*.png")):
            all_outputs.append(render)
        generate_manifest(version_dir, all_outputs)
        
        update_status(version_dir, "complete", 100, "Pipeline Execution Finished")
        logging.info("[5/5] Pipeline Execution Complete! Ready for AI Optimization Feedback.")
        logging.info("="*60)
    except Exception as e:
        if 'version_dir' in locals():
            update_status(version_dir, "error", 0, f"Pipeline Crashed: {e}")
        logging.error(f"PIPELINE FAILED: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
