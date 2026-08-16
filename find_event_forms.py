import os

ui_dir = 'd:/PROGRAMS/web/random/coworkconnect/ui'
for filename in os.listdir(ui_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(ui_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'event' in filename or 'event' in content.lower():
            for line_no, line in enumerate(content.splitlines(), 1):
                if 'date' in line.lower() or 'time' in line.lower() or 'form' in line.lower():
                    if any(keyword in line.lower() for keyword in ['event', 'create', 'add', 'submit', 'start', 'end']):
                        print(f"{filename}:{line_no}: {line.strip()}")
