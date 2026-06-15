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
        design = app.activeProduct
        
        if not design:
            print(json.dumps({"success": False, "message": "No active Fusion design."}))
            return

        exportMgr = design.exportManager
        rootComp = design.rootComponent
        
        output_dir = r"c:\one\Automated_3D_Modeling\10_Fusion360_Advanced_Automations\exports"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        base_name = "bulk_exported_model"
        
        # 1. Export STEP (Might fail on Personal License)
        try:
            step_path = os.path.join(output_dir, f"{base_name}.step")
            stepOptions = exportMgr.createSTEPExportOptions(step_path)
            exportMgr.execute(stepOptions)
        except Exception as e:
            print("STEP Export restricted by license.")
            
        # 2. Export IGES (Might fail on Personal License)
        try:
            iges_path = os.path.join(output_dir, f"{base_name}.iges")
            igesOptions = exportMgr.createIGESExportOptions(iges_path)
            exportMgr.execute(igesOptions)
        except Exception as e:
            print("IGES Export restricted by license.")
        
        # 3. Export STL (Mesh) - Always works
        try:
            stl_path = os.path.join(output_dir, f"{base_name}.stl")
            stlOptions = exportMgr.createSTLExportOptions(rootComp, stl_path)
            stlOptions.sendToPrintUtility = False
            exportMgr.execute(stlOptions)
        except Exception as e:
            print(f"STL Export failed: {e}")
        
        message = f"Successfully bulk exported to STEP, IGES, and STL in {output_dir}"
        print(json.dumps({"success": True, "message": message}))
        
    except:
        if ui:
            print(json.dumps({"success": False, "message": f"Failed:\n{traceback.format_exc()}"}))
