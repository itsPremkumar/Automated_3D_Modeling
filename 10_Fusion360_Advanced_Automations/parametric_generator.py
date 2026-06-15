import adsk.core
import adsk.fusion
import traceback
import os
import json

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Create a new document
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        
        # Get the root component of the active design
        rootComp = design.rootComponent
        
        # 1. Create a new sketch on the xy plane
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        sketch = sketches.add(xyPlane)
        
        # 2. Draw a rectangle (points are in cm)
        lines = sketch.sketchCurves.sketchLines
        point1 = adsk.core.Point3D.create(0, 0, 0)
        point2 = adsk.core.Point3D.create(10, 5, 0) # 100mm x 50mm
        lines.addTwoPointRectangle(point1, point2)
        
        # 3. Extrude the sketch into a 3D body
        extrudes = rootComp.features.extrudeFeatures
        prof = sketch.profiles.item(0)
        
        # Define distance (5cm = 50mm)
        distance = adsk.core.ValueInput.createByReal(5)
        extrudeInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrudeInput.setDistanceExtent(False, distance)
        
        extrude = extrudes.add(extrudeInput)
        
        # Setup visual style
        design.designType = adsk.fusion.DesignTypes.DirectDesignType # Disable timeline for speed
        viewport = app.activeViewport
        viewport.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
        viewport.fit()
        
        # Save Screenshot
        output_dir = r"c:\one\Automated_3D_Modeling\10_Fusion360_Advanced_Automations"
        screenshot_path = os.path.join(output_dir, "parametric_box.png")
        viewport.saveAsImageFile(screenshot_path, 1920, 1080)
        
        print(json.dumps({"success": True, "message": f"Successfully created parametric box and saved screenshot to {screenshot_path}"}))
        
    except:
        if ui:
            print(json.dumps({"success": False, "message": f"Failed:\n{traceback.format_exc()}"}))
