from typing import Tuple, Dict, Any

def build(config: Dict[str, Any]) -> Tuple[Any, str]:
    """
    6-DOF Robotic Arm Generator Plugin.
    
    Constructs a fully parametric 6-axis robotic arm by sequentially stacking 
    boxes and cylinders based on link lengths provided in the JSON configuration.
    
    Args:
        config (Dict[str, Any]): The configuration dictionary containing kinematic dimensions.
        
    Returns:
        Tuple[Any, str]: A tuple containing the build123d Compound (6 distinct solid bodies) 
                         and the string identifier '6dof_robotic_arm'.
    """
    from build123d import Cylinder, Box, Location, Compound
    
    p = config["cad_parameters"]
    
    # 1. Base (Fixed)
    base = Cylinder(radius=p["base_radius"], height=p["base_height"])
    
    # 2. Waist (Yaw)
    waist = Box(40, 40, 40)
    waist = waist.moved(Location((0, 0, p["base_height"] + 20)))
    
    # 3. Shoulder/Bicep (Pitch)
    bicep = Box(p["link_thickness"], p["link_thickness"], p["bicep_length"])
    bicep = bicep.moved(Location((0, 0, p["base_height"] + 40 + p["bicep_length"]/2.0)))
    
    # 4. Elbow/Forearm (Pitch)
    forearm = Box(p["link_thickness"]*0.8, p["link_thickness"]*0.8, p["forearm_length"])
    forearm = forearm.moved(Location((0, 0, p["base_height"] + 40 + p["bicep_length"] + p["forearm_length"]/2.0)))
    
    # 5. Wrist Pitch 
    wrist_p = Box(20, 20, 20)
    wrist_p = wrist_p.moved(Location((0, 0, p["base_height"] + 40 + p["bicep_length"] + p["forearm_length"] + 10)))
    
    # 6. Wrist Roll / End Effector
    wrist_r = Cylinder(radius=15, height=5)
    wrist_r = wrist_r.moved(Location((0, 0, p["base_height"] + 40 + p["bicep_length"] + p["forearm_length"] + 20 + 2.5)))
    
    # Create the full 6-axis Assembly
    assembly = Compound(children=[base, waist, bicep, forearm, wrist_p, wrist_r])
    
    return assembly, "6dof_robotic_arm"
