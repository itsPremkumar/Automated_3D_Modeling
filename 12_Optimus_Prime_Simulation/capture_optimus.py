import urllib.request
import json
import os
import sys

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
            resp_text = response.read().decode('utf-8')
            if resp_text:
                return json.loads(resp_text)
            return {}
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("Initializing connection to Fusion 360 MCP...")
    send_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "ai", "version": "1.0"}}
    })
    send_request({"jsonrpc": "2.0", "method": "notifications/initialized"})

    output_dir = r"C:\one\Automated_3D_Modeling\12_Optimus_Prime_Simulation\images"
    os.makedirs(output_dir, exist_ok=True)

    script_content = f"""
import adsk.core, adsk.fusion, traceback, time, os

def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    viewport = app.activeViewport
    camera = viewport.camera

    out_dir = r"{output_dir}"
    
    views = [
        ("Front", adsk.core.ViewOrientations.FrontViewOrientation),
        ("Back", adsk.core.ViewOrientations.BackViewOrientation),
        ("Left", adsk.core.ViewOrientations.LeftViewOrientation),
        ("Right", adsk.core.ViewOrientations.RightViewOrientation),
        ("Top", adsk.core.ViewOrientations.TopViewOrientation),
        ("Iso", adsk.core.ViewOrientations.IsoTopRightViewOrientation)
    ]

    for name, orientation in views:
        camera.viewOrientation = orientation
        camera.isFitView = True
        viewport.camera = camera
        adsk.doEvents()
        time.sleep(1.0)
        
        path = os.path.join(out_dir, f"optimus_{{name}}.png")
        viewport.saveAsImageFile(path, 1920, 1080)
"""

    execute_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "fusion_mcp_execute",
            "arguments": {
                "featureType": "script",
                "object": {"script": script_content}
            }
        }
    }
    
    print("Taking screenshots of Optimus Prime...")
    res = send_request(execute_payload)
    if res:
        print("Screenshots captured successfully.")

if __name__ == "__main__":
    main()
