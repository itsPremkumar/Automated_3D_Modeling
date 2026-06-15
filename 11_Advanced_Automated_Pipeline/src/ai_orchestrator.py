import os
import json
import subprocess
import time
import glob
import logging

def get_latest_version_dir(outputs_base):
    existing_versions = glob.glob(os.path.join(outputs_base, "v*"))
    if not existing_versions:
        return None
    latest = max(existing_versions, key=lambda x: int(os.path.basename(x).replace("v", "")))
    return latest

def run_orchestrator():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.abspath(os.path.join(base_dir, "..", "config.json"))
    outputs_base = os.path.abspath(os.path.join(base_dir, "..", "outputs"))
    pipeline_script = os.path.join(base_dir, "master_pipeline.py")
    plugin_script = os.path.join(base_dir, "plugins", "servo_assembly.py")
    
    logging.basicConfig(level=logging.INFO, format='[AI ORCHESTRATOR] %(message)s')
    
    logging.info("Starting Autonomous AI Optimization Loop (Modular Framework)...")
    logging.info("Goal: Maximize Arm Length (Target: 70mm) while ensuring Structural Safety (Stress < 45 MPa).")
    
    max_iterations = 5
    for iteration in range(max_iterations):
        logging.info(f"\n--- Optimization Iteration {iteration + 1} ---")
        
        with open(config_file, "r") as f:
            config = json.load(f)
            
        if iteration == 0:
            logging.info("AI Action: Increasing target arm length to 70mm.")
            config["cad_parameters"]["arm_length"] = 70.0
            config["cad_parameters"]["arm_thickness"] = 5.0 
        
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
            
        logging.info("Triggering Universal CAD Pipeline...")
        subprocess.run([
            "uv", "run", "--with", "build123d", "--with", "trimesh", "--python", "3.12", 
            pipeline_script, 
            "--plugin", plugin_script, 
            "--config", config_file
        ], check=True)
        
        latest_dir = get_latest_version_dir(outputs_base)
        fitness_file = os.path.join(latest_dir, "fitness.json")
        
        if os.path.exists(fitness_file):
            with open(fitness_file, "r") as f:
                fitness = json.load(f)
                
            stress = fitness["stress_mpa"]
            safe = fitness["structurally_safe"]
            mass = fitness["mass_g"]
            
            logging.info(f"Feedback Received -> Stress: {stress} MPa (Limit: 45) | Safe: {safe} | Mass: {mass}g")
            
            if safe:
                logging.info(f"SUCCESS! Optimized design achieved in {iteration + 1} iterations.")
                break
            else:
                logging.warning("Design FAILED structural proxy. AI Action: Reinforcing arm thickness +2mm.")
                config["cad_parameters"]["arm_thickness"] += 2.0
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=4)
        else:
            logging.error("No fitness.json found. Pipeline crashed.")
            break

if __name__ == "__main__":
    run_orchestrator()
