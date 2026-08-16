import re

filepath = 'd:/PROGRAMS/web/random/coworkconnect/ui/groups.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update grid layout for .groups-shell
content = re.sub(
    r'grid-template-columns:\s*76px 340px minmax\(420px, 1fr\) 330px;',
    r'grid-template-columns: 350px 1fr;',
    content
)

# Update responsive CSS rules
content = re.sub(
    r'grid-template-columns:\s*70px 320px minmax\(420px, 1fr\);',
    r'grid-template-columns: 300px 1fr;',
    content
)

# 2. Remove workspace-rail
content = re.sub(
    r'<aside class="workspace-rail".*?</aside>',
    '',
    content,
    flags=re.DOTALL
)

# 3. Remove details-panel
content = re.sub(
    r'<aside class="details-panel".*?</aside>',
    '',
    content,
    flags=re.DOTALL
)

# 4. Remove filter-tabs and pinned-grid safely
# Let's just find exactly what to remove
filter_regex = r'<div class="filter-tabs" role="tablist">.*?</div>\s*<div class="sidebar-section-label">\s*<span>Pinned</span>.*?</svg>\s*</div>\s*<div class="pinned-grid" id="pinned-groups">.*?</div>\s*'
content = re.sub(
    r'<div class="filter-tabs" role="tablist">.*?<div class="sidebar-section-label">\s*<span>Live Rooms</span>',
    r'<div class="sidebar-section-label">\n                    <span>Live Rooms</span>',
    content,
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("groups.html simplified!")
