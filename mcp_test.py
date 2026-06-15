import urllib.request
import json
import os

def run_fusion_script(code):
    url = "http://127.0.0.1:27182/mcp"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "fusion_mcp_execute",
            "arguments": {
                "featureType": "script",
                "object": {
                    "script": code
                }
            }
        }
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

fusion_code = """
import adsk.core, adsk.fusion, traceback
import os

def run(_context: str):
    app = adsk.core.Application.get()
    
    files_to_open = [
        r"C:/one/Automated_3D_Modeling/06_Engineering_Models/pillow_block.step",
        r"C:/one/Automated_3D_Modeling/06_Engineering_Models/flange_coupling.step"
    ]
    
    for step_file in files_to_open:
        if not os.path.exists(step_file):
            print(f"File not found: {step_file}")
            continue
            
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent
        
        importManager = app.importManager
        stepOptions = importManager.createSTEPImportOptions(step_file)
        importManager.importToTarget(stepOptions, rootComp)
        
        cam = app.activeViewport.camera
        cam.isFitView = True
        app.activeViewport.camera = cam
        app.activeViewport.refresh()
        
        screenshot_path = step_file.replace('.step', '.png')
        app.activeViewport.saveAsImageFile(screenshot_path, 1920, 1080)
        print("Screenshot saved to: " + screenshot_path)
        
        doc.close(False)
"""

print(run_fusion_script(fusion_code))
