import urllib.request
import json

URL = "http://127.0.0.1:27182/mcp"
session_id = None

def send_request(payload):
    global session_id
    headers = {'Content-Type': 'application/json'}
    if session_id:
        headers['MCP-Session-Id'] = session_id
    req = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        resp_text = response.read().decode('utf-8')
        if resp_text:
            return json.loads(resp_text)
        return {}

send_request({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "ai", "version": "1.0"}}
})
send_request({"jsonrpc": "2.0", "method": "notifications/initialized"})

script = """
import adsk.core, adsk.fusion, traceback
def run(context):
    try:
        with open(r'C:\\opt_fusion_log.txt', 'a') as f:
            f.write('\\n--- API HELP ---\\n')
            f.write(str(adsk.fusion.JointGeometry.createByPoint.__doc__))
            f.write('\\n')
    except:
        pass
"""

send_request({
    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
    "params": {"name": "fusion_mcp_execute", "arguments": {"featureType": "script", "object": {"script": script}}}
})
