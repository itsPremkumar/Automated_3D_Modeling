import urllib.request
import json
import random

print("Fetching FreeCAD test step files...")
url = "https://api.github.com/repos/FreeCAD/FreeCAD/git/trees/main?recursive=1"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req)
    tree = json.loads(res.read().decode())['tree']
    
    step_files = [item['path'] for item in tree if item['path'].lower().endswith('.step') or item['path'].lower().endswith('.stp')]
    
    if step_files:
        chosen = step_files[0]
        for f in step_files:
            if "bracket" in f.lower() or "block" in f.lower():
                chosen = f
                break
                
        print(f"Chosen file: {chosen}")
        raw_url = f"https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/{chosen}"
        print(f"Downloading from: {raw_url}")
        
        urllib.request.urlretrieve(raw_url, "downloaded_model.step")
        print("Successfully downloaded 'downloaded_model.step'")
    else:
        print("No step files found.")
except Exception as e:
    print(f"Error: {e}")
