import os

# Define exact replacements for HTML files
replacements = {
    'index.html': [
        (
            'style="background: linear-gradient(135deg, white, var(--primary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"',
            'style="color: var(--primary);"'
        )
    ],
    'events.html': [
        (
            'background: linear-gradient(135deg, #064e3b 0%, #0d4d3d 50%, #10b981 100%);',
            'background: #0d4d3d;'
        ),
        (
            'background: linear-gradient(135deg, #064e3b, #10b981);',
            'background: #0d4d3d;'
        )
    ],
    'community.html': [
        (
            'linear-gradient(180deg, rgba(6, 78, 59, 0.08), rgba(238, 242, 247, 0) 330px),\n                #eef2f7;',
            '#eef2f7;'
        ),
        (
            'linear-gradient(135deg, rgba(15, 23, 42, 0.18), rgba(16, 185, 129, 0.85)),',
            'rgba(13, 77, 61, 0.85),'
        ),
        (
            'linear-gradient(120deg, rgba(15, 23, 42, 0.90), rgba(6, 78, 59, 0.72)),',
            'rgba(15, 23, 42, 0.90),'
        )
    ],
    'groups.html': [
        (
            'linear-gradient(180deg, rgba(6, 78, 59, 0.08), rgba(238, 242, 247, 0) 320px),\n                #eef2f7;',
            '#eef2f7;'
        ),
        (
            'radial-gradient(circle at top left, rgba(16, 185, 129, 0.10), transparent 280px),\n                radial-gradient(circle at bottom right, rgba(15, 23, 42, 0.08), transparent 320px),\n                #ffffff;',
            '#ffffff;'
        )
    ]
}

ui_dir = 'd:/PROGRAMS/web/random/coworkconnect/ui'

for filename, reps in replacements.items():
    filepath = os.path.join(ui_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        orig_content = content
        for target, replacement in reps:
            content = content.replace(target, replacement)
            # Try with different whitespace just in case
            content = content.replace(target.replace('\n', '\r\n'), replacement)
        
        if content != orig_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated gradients in {filename}")
        else:
            print(f"No match/change for {filename}")
