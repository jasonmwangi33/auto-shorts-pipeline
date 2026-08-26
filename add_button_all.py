import glob, re

files = glob.glob('.github/workflows/*.yml')

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'workflow_dispatch:' not in content and 'on:' in content:
        content = re.sub(r'^(on:.*?\n)', r'\1  workflow_dispatch:\n', content, flags=re.MULTILINE)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Added button to {file_path}")
