from typing import Tuple, Dict, Any

def build(config: Dict[str, Any]) -> Tuple[Any, str]:
    """
    STEP Modifier Plugin.
    
    Demonstrates importing a raw, external STEP file (e.g., from GrabCAD), applying 
    a parametric Boolean cut (hollowing out the center) based on JSON parameters, 
    and returning the modified B-Rep geometry for manufacturing validation.
    
    Args:
        config (Dict[str, Any]): The JSON configuration containing 'cutout_radius'.
        
    Returns:
        Tuple[Any, str]: A tuple containing the modified build123d Part and its name.
        
    Raises:
        FileNotFoundError: If the external 'raw_input.step' file is missing.
    """
    import os
    from build123d import import_step, Cylinder
    
    # 1. Read config
    cut_radius = config["cad_parameters"]["cutout_radius"]
    
    # 2. Import external STEP file
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    step_path = os.path.join(base_dir, "inputs", "raw_input.step")
    
    if not os.path.exists(step_path):
        raise FileNotFoundError(f"Missing external CAD file: {step_path}")
        
    raw_part = import_step(step_path)
    
    # 3. Modify geometry: Drill a massive hole straight through the center
    hole_cutter = Cylinder(radius=cut_radius, height=200) # Ensure it goes all the way through
    
    # Perform Boolean Subtraction
    modified_part = raw_part - hole_cutter
    
    return modified_part, "modified_external_bracket"
