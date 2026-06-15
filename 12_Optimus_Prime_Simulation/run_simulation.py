import urllib.request
import json
import os
import sys

URL = "http://127.0.0.1:27182/mcp"
PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), "optimus_prime_simulation_v6.py")
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
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Connection refused. Ensure Autodesk Fusion 360 is running on {URL}\nError: {e}")
        return None

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimus Prime G1 Simulation Controller")
    parser.add_argument("--module", type=str, default="ALL", 
                        choices=["ALL", "rom", "head", "wave", "breathing", "walk", "run", "combat", "transform", "stability", "servo"],
                        help="Select a specific simulation module to run in isolation.")
    args = parser.parse_args()

    if not os.path.exists(PAYLOAD_FILE):
        print(f"Payload file not found: {PAYLOAD_FILE}")
        sys.exit(1)

    print(f"Loading Optimus Prime payload (> 50KB)... [Target: {args.module}]")
    with open(PAYLOAD_FILE, "r", encoding="utf-8") as f:
        script_content = f"TARGET_MODULE = '{args.module}'\n" + f.read()

    print("Initializing connection to Fusion 360 MCP...")
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
    
    send_request({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })

    print("Transmitting Optimus Prime G1 Engine to Fusion 360...")
    execute_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "fusion_mcp_execute",
            "arguments": {
                "featureType": "script",
                "object": {
                    "script": script_content
                }
            }
        }
    }
    
    print("====================================================================")
    print("Fusion 360 is now building and simulating the robot.")
    print("CRITICAL: Do NOT click inside Fusion 360 until the simulation completes!")
    print("====================================================================")
    
    res = send_request(execute_payload)
    if res:
        print("\nSimulation Complete!")
        print(json.dumps(res, indent=2))
