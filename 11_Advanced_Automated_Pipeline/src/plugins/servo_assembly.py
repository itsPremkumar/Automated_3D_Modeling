def build(config):
    """
    Standard CAD Plugin Interface.
    Returns:
        assembly: The generated build123d Compound or Part.
        part_name: A string identifier for the model.
    """
    from build123d import Box, Location, Compound
    
    cad_params = config["cad_parameters"]
    
    # Generate Components
    base = Box(cad_params["base_width"], cad_params["base_length"], cad_params["base_thickness"])
    # Shift arm so it stacks on top
    arm = Box(cad_params["arm_length"], cad_params["arm_width"], cad_params["arm_thickness"])
    arm = arm.moved(Location((0, 0, (cad_params["base_thickness"] + cad_params["arm_thickness"])/2.0)))
    
    # Create Assembly
    assembly = Compound(children=[base, arm])
    
    return assembly, "servo_assembly"
