# 3D Modeling Automation — Source Code Reference

This document centralizes all the working Python code used to generate our engineering parts and the script that automated Autodesk Fusion 360 to capture the screenshots via MCP. 

---

## 1. Parametric Pillow Block Bearing
**Framework:** `Build123d`
**File:** `06_Engineering_Models/pillow_block.py`

This script programmatically generates a standard pillow block housing, utilizing boolean operations and parametric variables.

```python
from build123d import *

# Pillow Block Bearing Parameters
base_length = 80.0
base_width = 30.0
base_thickness = 10.0
mount_hole_dist = 60.0
mount_hole_dia = 8.0

bearing_od = 22.0
bearing_width = 7.0
shaft_clearance = 12.0
center_height = 25.0

with BuildPart() as pillow_block:
    # 1. Base
    with BuildSketch(Plane.XY) as base_sketch:
        Rectangle(base_length, base_width)
    extrude(amount=base_thickness)
    
    # Base Mounting Holes
    with Locations(pillow_block.faces().sort_by(Axis.Z)[-1]):
        with Locations((-mount_hole_dist/2, 0), (mount_hole_dist/2, 0)):
            Hole(radius=mount_hole_dia/2)
            
    # 2. Upright Housing
    with BuildSketch(pillow_block.faces().sort_by(Axis.Z)[-1]) as upright_base:
        Rectangle(bearing_od + 14, base_width)
    extrude(amount=center_height - base_thickness + bearing_od/2 + 4)
    
    # 3. Fillets on the upright housing to make it rounded at the top
    top_edges = pillow_block.edges().filter_by(Axis.Y).sort_by(Axis.Z)[-2:]
    fillet(top_edges, radius=(bearing_od + 14) / 2 - 0.1)

    # 4. Bearing Bore
    with BuildSketch(Plane.XZ) as bore_sketch:
        with Locations((0, center_height)):
            Circle(bearing_od/2)
    extrude(amount=bearing_width/2, both=True, mode=Mode.SUBTRACT)
    
    # 5. Shaft clearance bore (goes all the way through)
    with BuildSketch(Plane.XZ) as shaft_sketch:
        with Locations((0, center_height)):
            Circle(shaft_clearance/2)
    extrude(amount=base_width, both=True, mode=Mode.SUBTRACT)

# Export to standard formats
export_step(pillow_block.part, "pillow_block.step")
export_stl(pillow_block.part, "pillow_block.stl")
print("Pillow block generated successfully!")
```

---

## 2. Parametric Flange Coupling
**Framework:** `Build123d`
**File:** `06_Engineering_Models/flange_coupling.py`

This script generates a flange coupling complete with a keyway slot and bolt holes on a polar array.

```python
from build123d import *

# Flange Coupling Parameters
shaft_dia = 12.0
flange_od = 60.0
flange_thickness = 10.0
hub_od = 25.0
hub_length = 20.0
bolt_circle_dia = 45.0
bolt_hole_dia = 5.0
num_bolts = 4
keyway_width = 4.0
keyway_depth = 2.0

with BuildPart() as flange:
    # 1. Flange body
    with BuildSketch(Plane.XY) as sketch:
        Circle(flange_od/2)
    extrude(amount=flange_thickness)
    
    # 2. Hub
    with BuildSketch(flange.faces().sort_by(Axis.Z)[-1]):
        Circle(hub_od/2)
    extrude(amount=hub_length)
    
    # 3. Central Bore & Keyway
    with BuildSketch(flange.faces().sort_by(Axis.Z)[0]): 
        Circle(shaft_dia/2)
        with Locations((0, shaft_dia/2 + keyway_depth/2)):
            Rectangle(keyway_width, keyway_depth + 0.1, align=(Align.CENTER, Align.CENTER))
    extrude(amount=flange_thickness + hub_length, mode=Mode.SUBTRACT)
    
    # 4. Bolt holes
    with BuildSketch(flange.faces().sort_by(Axis.Z)[0]):
        with PolarLocations(radius=bolt_circle_dia/2, count=num_bolts):
            Circle(bolt_hole_dia/2)
    extrude(amount=flange_thickness, mode=Mode.SUBTRACT)
    
    # 5. Fillet between flange and hub for strength
    hub_base_edges = [e for e in flange.edges().filter_by(GeomType.CIRCLE) 
                      if abs(e.radius - hub_od/2) < 0.1 and abs(e.center().Z - flange_thickness) < 0.1]
    if hub_base_edges:
        fillet(hub_base_edges, radius=2.0)

export_step(flange.part, "flange_coupling.step")
export_stl(flange.part, "flange_coupling.stl")
print("Flange coupling generated successfully!")
```

---

## 3. Fusion 360 MCP Automation Script
**Framework:** `urllib` / JSON-RPC / Fusion 360 Python API
**File:** `capture_screenshots.py`

This script connects to the local Autodesk Fusion 360 MCP Server via HTTP POST requests, properly extracts the `MCP-Session-Id`, and pushes a Python payload into Fusion 360 that automatically imports all `.step` files and captures high-res screenshots.

```python
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
            if 'MCP-Session-Id' in response.headers:
                session_id = response.headers.get('MCP-Session-Id')
                
            if response.status == 200:
                resp_text = response.read().decode('utf-8')
                if resp_text:
                    return json.loads(resp_text)
                return {}
    except Exception as e:
        print(f"Error: {e}")
        return None

# 1. Initialize Connection
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
send_request(init_payload)

# 2. Initialized Notification
send_request({
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
})

# 3. Fusion 360 Internal Python Script Payload
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
            
        for model_file in files_to_open:
            if not os.path.exists(model_file):
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

# 4. Execute the Script inside Fusion 360
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
print("Executing script inside Fusion 360...")
send_request(execute_payload)
print("Finished!")
```
