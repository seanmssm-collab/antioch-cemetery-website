"""
Assembles templates/index.html from map_fragment.txt (produced by
build_map_fragment.py). Run build_map_fragment.py first.
"""

FRAGMENT = "/Users/Shared/CemeteryCAD/Antioch/public_site/map_fragment.txt"
OUT = "/Users/Shared/CemeteryCAD/Antioch/public_site/templates/index.html"

with open(FRAGMENT) as f:
    content = f.read()

viewbox_line, rest = content.split("\n", 1)
viewbox = viewbox_line.split("=", 1)[1]  # already "0 0 W H", no extra prefix needed
w, h = viewbox.split()[2], viewbox.split()[3]

fence_part, rest = rest.split("ROAD\n", 1)
road_part, rest = rest.split("LANDMARKS\n", 1)
landmarks_part, rest = rest.split("ROADLABEL\n", 1)
roadlabel_part, rest = rest.split("COMPASS\n", 1)
compass_part, markers_part = rest.split("MARKERS\n", 1)

fence_svg = fence_part.replace("FENCE\n", "").strip()
road_svg = road_part.strip()
landmarks_svg = landmarks_part.strip()
roadlabel_svg = roadlabel_part.strip()
compass_svg = compass_part.strip()
markers_svg = markers_part.strip()

template = (
    '{% extends "base.html" %}\n'
    "{% block content %}\n"
    '  <div class="panel-row">\n'
    '    <div class="search-panel">\n'
    '      <div class="search-bar">\n'
    '        <input type="text" id="q" placeholder="Search by name">\n'
    '        <button onclick="doSearch()">Search</button>\n'
    "      </div>\n"
    "    </div>\n"
    '    <div class="info-panel">\n'
    '      <div id="info-card"></div>\n'
    '      <div id="results"></div>\n'
    "    </div>\n"
    "  </div>\n"
    '  <div id="map-wrap">\n'
    f'    <svg viewBox="{viewbox}" width="{w}" height="{h}" id="map">\n'
    f"      <g>{fence_svg}</g>\n"
    f"      <g>{road_svg}</g>\n"
    f"      <g>{markers_svg}</g>\n"
    f"      <g>{landmarks_svg}</g>\n"
    f"      <g>{roadlabel_svg}</g>\n"
    f"      <g>{compass_svg}</g>\n"
    '      <g id="found-pin" class="found-pin" visibility="hidden">\n'
    '        <path d="M0,-11 C4,-11 7,-8 7,-4 C7,1 0,9 0,9 C0,9 -7,1 -7,-4 C-7,-8 -4,-11 0,-11 Z" />\n'
    '        <circle cx="0" cy="-4" r="2.2" class="found-pin-dot" />\n'
    "      </g>\n"
    "    </svg>\n"
    "  </div>\n"
    "{% endblock %}\n"
)

with open(OUT, "w") as f:
    f.write(template)
print(f"wrote {OUT}, {len(template)} bytes, viewBox={viewbox}")
