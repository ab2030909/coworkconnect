import os
import re

ui_dir = 'd:/PROGRAMS/web/random/coworkconnect/ui'
icon_link = '<link rel="icon" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.11.3/icons/briefcase-fill.svg">'
simple_footer = '''    <footer class="footer" style="padding: 2rem 0; background-color: var(--color-surface); border-top: 1px solid var(--color-border); text-align: center; color: var(--color-muted); font-size: 0.85rem; font-weight: 600;">
        <div class="container">
            <p>&copy; 2026 CoWorkConnect. All rights reserved.</p>
        </div>
    </footer>'''

for filename in os.listdir(ui_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(ui_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add icon
        if 'rel="icon"' not in content:
            content = content.replace('</head>', f'    {icon_link}\n</head>')

        # Replace footer
        content = re.sub(r'<footer.*?</footer\s*>', simple_footer, content, flags=re.DOTALL)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
print("Updated all HTML files.")
