"""
Regenerates map_fragment.txt: the static SVG geometry (fence, road,
landmarks, plot markers) embedded in templates/index.html. Plot names/
dates are NOT baked in here -- those come live from /api/plots -- only
positions, which rarely change.
"""
import json
import sqlite3

GEOJSON = "/Users/Shared/CemeteryCAD/Antioch/dxf_entities.geojson"
DB_PATH = "/Users/Shared/CemeteryCAD/Antioch/app/cemetery.db"
OUT = "/Users/Shared/CemeteryCAD/Antioch/public_site/map_fragment.txt"

LANDMARKS = [
    ("Gazebo", 3273993.60, 6745749.80),
    ("Pavilion", 3273864.94, 6746057.38),
]

d = json.load(open(GEOJSON))
fence_lines = []
road_lines = []
for f in d["features"]:
    layer = f["properties"].get("Layer")
    if layer not in ("FENCE", "ROAD"):
        continue
    geom = f["geometry"]
    parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
    for part in parts:
        pts = [(x, y) for x, y, *_ in part]
        (fence_lines if layer == "FENCE" else road_lines).append(pts)

conn = sqlite3.connect(DB_PATH)
plots = conn.execute("SELECT plot_number, survey_x, survey_y FROM plots WHERE survey_x IS NOT NULL").fetchall()
conn.close()

all_lines = fence_lines + road_lines
xs = [x for seg in all_lines for x, y in seg] + [p[1] for p in plots] + [lx for _, lx, ly in LANDMARKS]
ys = [y for seg in all_lines for x, y in seg] + [p[2] for p in plots] + [ly for _, lx, ly in LANDMARKS]
pad = 35
minx, maxx = min(xs) - pad, max(xs) + pad
miny, maxy = min(ys) - pad, max(ys) + pad
W = maxx - minx
H = maxy - miny

def to_svg(x, y):
    return x - minx, maxy - y

def path_for(lines):
    parts = []
    for seg in lines:
        pts = [to_svg(x, y) for x, y in seg]
        dattr = "M " + " L ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
        parts.append(dattr)
    return parts

fence_paths = "\n".join(f'<path d="{p}" class="fenceline" />' for p in path_for(fence_lines))
road_paths = "\n".join(f'<path d="{p}" class="roadline" />' for p in path_for(road_lines))

markers = []
for num, x, y in plots:
    px, py = to_svg(x, y)
    markers.append(f'<circle class="plot-marker" id="plot-{num}" cx="{px:.2f}" cy="{py:.2f}" r="1.4" />')
markers_svg = "\n".join(markers)

landmark_svg = []
for name, x, y in LANDMARKS:
    px, py = to_svg(x, y)
    landmark_svg.append(
        f'<g class="landmark" transform="translate({px:.2f},{py:.2f})">'
        f'<rect x="-4" y="-4" width="8" height="8" />'
        f'<text x="0" y="-6" class="landmark-label">{name}</text>'
        f'</g>'
    )
landmarks_svg = "\n".join(landmark_svg)

with open(OUT, "w") as f:
    f.write(f"VIEWBOX=0 0 {W:.2f} {H:.2f}\n")
    f.write("FENCE\n")
    f.write(fence_paths)
    f.write("\nROAD\n")
    f.write(road_paths)
    f.write("\nLANDMARKS\n")
    f.write(landmarks_svg)
    f.write("\nMARKERS\n")
    f.write(markers_svg)

print(f"wrote {OUT}: {len(fence_lines)} fence segs, {len(road_lines)} road segs, {len(LANDMARKS)} landmarks, {len(plots)} plots")
print(f"viewBox: 0 0 {W:.2f} {H:.2f}")
