import urllib.request
import json
import os

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

def execute_mcp_script(script_path):
    print(f"Executing {script_path} via MCP...")
    with open(script_path, 'r') as f:
        script_code = f.read()
        
    # Execute tool
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "fusion_mcp_execute",
            "arguments": {
                "featureType": "script",
                "object": {
                    "script": script_code
                }
            }
        }
    }
    
    res = send_request(payload)
    if res and "result" in res and "content" in res["result"]:
        text_result = res["result"]["content"][0]["text"]
        try:
            result_json = json.loads(text_result)
            if result_json.get("success"):
                print(f"SUCCESS: {result_json.get('message')}")
            else:
                print(f"FAILED: {text_result}")
        except json.JSONDecodeError:
            print(f"Raw Output: {text_result}")
    else:
        print(f"Failed to get a valid response. Raw response: {res}")

def main():
    print("Initializing MCP Session...")
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "TestClient", "version": "1.0.0"}
        }
    }
    res = send_request(init_payload)
    print(f"Init Response: {res}")
    
    # Send initialized notification
    send_request({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })

    base_dir = r"c:\one\Automated_3D_Modeling\10_Fusion360_Advanced_Automations"
    
    # Run Parametric Generator
    execute_mcp_script(os.path.join(base_dir, "parametric_generator.py"))
    
    # Run Bulk Exporter
    execute_mcp_script(os.path.join(base_dir, "bulk_exporter.py"))

if __name__ == "__main__":
    main()
