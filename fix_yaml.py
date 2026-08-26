import glob, re

files = glob.glob('.github/workflows/*.yml')
if not files: exit()

with open(files[0], 'r', encoding='utf-8') as f:
    content = f.read()

# Pass files out of Stage 1
content = re.sub(
    r'(\n\s+)(run: \|\s+pip install --upgrade pip\s+pip install -r requirements\.txt\s+python pipeline/batch_router\.py 1)',
    r'\1\2\1- name: Upload Workspace\1  uses: actions/upload-artifact@v4\1  with:\1    name: shared-workspace\1    path: workspace/\1    overwrite: true',
    content
)

# Catch files for Stage 2, build video, pass video to Stage 3
content = re.sub(
    r'(\n\s+)(run: \|\s+pip install --upgrade pip\s+pip install -r requirements\.txt\s+python pipeline/batch_router\.py 2)',
    r'\1- name: Download Workspace\1  uses: actions/download-artifact@v4\1  with:\1    name: shared-workspace\1    path: workspace/\1\2\1- name: Upload Workspace\1  uses: actions/upload-artifact@v4\1  with:\1    name: shared-workspace\1    path: workspace/\1    overwrite: true',
    content
)

# Catch final video for Stage 3 publishing
content = re.sub(
    r'(\n\s+)(run: \|\s+pip install --upgrade pip\s+pip install -r requirements\.txt\s+python pipeline/batch_router\.py 3)',
    r'\1- name: Download Workspace\1  uses: actions/download-artifact@v4\1  with:\1    name: shared-workspace\1    path: workspace/\1\2',
    content
)

with open(files[0], 'w', encoding='utf-8') as f:
    f.write(content)
