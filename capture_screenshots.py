import urllib.request
import json
import time

URL = "http://127.0.0.1:27182/mcp"
session_id = None

def send_request(payload):
    global session_id
    headers = {'Content-Type': 'application/json'}
    if session_id:
        headers['MCP-Session-Id'] = session_id
        
    req = urllib.request.Request(
        URL, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers
    )
    try:
        with urllib.request.urlopen(req) as response:
            # Capture session ID if provided
            if 'MCP-Session-Id' in response.headers:
                session_id = response.headers.get('MCP-Session-Id')
                
            if response.status == 200:
                resp_text = response.read().decode('utf-8')
                if resp_text:
                    return json.loads(resp_text)
                return {}
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# 1. Initialize
init_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "ai_agent", "version": "1.0"}
    }
}
print("Initializing...")
res = send_request(init_payload)
print("Init Response:", res)
print("Session ID:", session_id)

# 2. Initialized Notification
send_request({
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
})

# 3. Fusion Script
fusion_script = r"""
import adsk.core, adsk.fusion, traceback
import os

def run(_context: str):
    try:
        app = adsk.core.Application.get()
        
        files_to_open = [
            r"c:\one\Automated_3D_Modeling\01_CadQuery\cadquery_cube.step",
            r"c:\one\Automated_3D_Modeling\02_Build123d\build123d_cube.step",
            r"c:\one\Automated_3D_Modeling\06_Engineering_Models\pillow_block.step",
            r"c:\one\Automated_3D_Modeling\06_Engineering_Models\flange_coupling.step"
        ]
        
        blender_file = r"c:\one\Automated_3D_Modeling\04_Blender_bpy\blender_cube.stl"
        if os.path.exists(blender_file):
            files_to_open.append(blender_file)
            
        for model_file in files_to_open:
            if not os.path.exists(model_file):
                print(f"File not found: {model_file}")
                continue
                
            if not model_file.lower().endswith('.step'):
                continue

            doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            design = adsk.fusion.Design.cast(app.activeProduct)
            rootComp = design.rootComponent
            
            importManager = app.importManager
            options = importManager.createSTEPImportOptions(model_file)
            importManager.importToTarget(options, rootComp)
            
            viewport = app.activeViewport
            cam = viewport.camera
            cam.isFitView = True
            viewport.camera = cam
            viewport.refresh()
            
            viewport.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
            
            screenshot_path = os.path.splitext(model_file)[0] + ".png"
            viewport.saveAsImageFile(screenshot_path, 1920, 1080)
            print("Screenshot saved to: " + screenshot_path)
            
            doc.close(False)
    except Exception as e:
        print(f"Fusion Script Failed: {traceback.format_exc()}")
"""

# 4. Execute tool
execute_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "fusion_mcp_execute",
        "arguments": {
            "featureType": "script",
            "object": {
                "script": fusion_script
            }
        }
    }
}
print("Executing script...")
res2 = send_request(execute_payload)
print("Execute Response:", res2)
