import os
import re

TEMPLATES_TO_UPDATE = [
    r"templates\account\list.html",
    r"templates\class\list.html",
    r"templates\schoolyear\list.html",
    r"templates\subject\list.html",
    r"templates\teacher\list.html",
    r"templates\schedule\list.html",
]

base_dir = r"d:\HT Khao Thi"

for rel_path in TEMPLATES_TO_UPDATE:
    file_path = os.path.join(base_dir, rel_path)
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "pagination.html" in content:
        print(f"Already updated {file_path}")
        continue

    pattern = r"(</table>\s*</div>)"
    def repl(m):
        return m.group(1) + "\n        <div class=\"card-footer bg-white\">\n            {% include 'pagination.html' %}\n        </div>"
        
    new_content = re.sub(pattern, repl, content)
    
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"Failed {file_path}")
