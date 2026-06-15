import urllib.request
import json
import os

print("Searching GitHub for open-source '.step' files...")

# Search GitHub API for files named "bracket.step"
search_url = "https://api.github.com/search/code?q=filename:bracket.step+extension:step"

try:
    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        if data['total_count'] > 0:
            item = data['items'][0]
            repo_name = item['repository']['full_name']
            file_path = item['path']
            print(f"Found file: {file_path} in repository: {repo_name}")
            
            # Construct raw URL
            raw_url = f"https://raw.githubusercontent.com/{repo_name}/master/{file_path}"
            
            print(f"Downloading from: {raw_url}")
            # Try to download. Sometimes master branch is main, so if master fails, try main.
            try:
                urllib.request.urlretrieve(raw_url, "downloaded_bracket.step")
                print("Successfully downloaded downloaded_bracket.step")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/{file_path}"
                    urllib.request.urlretrieve(raw_url, "downloaded_bracket.step")
                    print("Successfully downloaded downloaded_bracket.step (from main branch)")
                else:
                    raise e
        else:
            print("No files found.")
except Exception as e:
    print(f"Error: {e}")
