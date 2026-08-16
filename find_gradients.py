import os

ui_dir = 'd:/PROGRAMS/web/random/coworkconnect/ui'
for filename in os.listdir(ui_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(ui_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'gradient' in content.lower():
            print(f"Gradient found in {filename}!")
            # Find and print context
            for line_no, line in enumerate(content.splitlines(), 1):
                if 'gradient' in line.lower():
                    print(f"  Line {line_no}: {line.strip()}")
