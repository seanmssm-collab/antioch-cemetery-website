"""
Regenerates map_fragment.txt: the static SVG geometry (fence, road,
landmarks, plot markers) embedded in templates/index.html. Plot names/
dates are NOT baked in here -- those come live from /api/plots -- only
positions, which rarely change.
"""
import csv
import json
import sqlite3

GEOJSON = "/Users/Shared/CemeteryCAD/Antioch/dxf_entities.geojson"
DB_PATH = "/Users/Shared/CemeteryCAD/Antioch/app/cemetery.db"
EXPANSION_FENCE_CSV = "/Users/Shared/CemeteryCAD/Antioch/expansion_fence.csv"
EXPANSION_ROAD_CSV = "/Users/Shared/CemeteryCAD/Antioch/expansion_road.csv"
OUT = "/Users/Shared/CemeteryCAD/Antioch/public_site/map_fragment.txt"

# where the driveway starts (entrance fork) -- anchor for the "ROAD" label,
# nudged down from the road's own coordinate so it sits between the two
# edge lines rather than overlapping the top one
ROAD_LABEL_POS = (3273730.0, 6745736.0)

# name, X, Y, box size in ft (Pavilion is a real building -- full grid box;
# Gazebo is small -- kept at its original size, just relocated)
LANDMARKS = [
    ("Gazebo", 3273980.0, 6745729.80, 8.0),
    ("Pavilion", 3273864.94, 6746057.38, 20.0),
]

# The original 2015 survey's north fence edge is being physically removed --
# the cemetery's real boundary is now 70ft further north (the expansion).
# Drop this exact segment from the original FENCE polyline; the new
# boundary line (read from expansion_fence.csv below) replaces it.
# Compared with a tolerance, not exact equality -- the literal floats here
# don't match the GeoJSON's full precision, so a straight == silently
# failed to match and left the old line on the map.
OLD_NORTH_EDGE = [(3273986.072, 6745922.554), (3273614.205, 6745925.146)]

def is_old_north_edge(a, b):
    def close(p, q):
        return abs(p[0] - q[0]) < 0.01 and abs(p[1] - q[1]) < 0.01
    return (close(a, OLD_NORTH_EDGE[0]) and close(b, OLD_NORTH_EDGE[1])) or \
           (close(a, OLD_NORTH_EDGE[1]) and close(b, OLD_NORTH_EDGE[0]))

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
        if layer == "ROAD":
            road_lines.append(pts)
            continue
        # split the fence polyline into individual segments so the old
        # north edge can be dropped without losing the rest of the fence
        for a, b in zip(pts, pts[1:]):
            if is_old_north_edge(a, b):
                continue
            fence_lines.append([a, b])

# the new north boundary (70ft expansion), replacing the old edge above
with open(EXPANSION_FENCE_CSV) as ef:
    new_boundary = [(float(r["X"]), float(r["Y"])) for r in csv.DictReader(ef)]
fence_lines.append(new_boundary)

# the driveway extension north through the expansion, up past the pavilion
# (two parallel edges, matching the rest of the road)
road_ext_a, road_ext_b = [], []
with open(EXPANSION_ROAD_CSV) as rf:
    for r in csv.DictReader(rf):
        pt = (float(r["X"]), float(r["Y"]))
        (road_ext_a if r["line"] == "A" else road_ext_b).append(pt)
road_lines.append(road_ext_a)
road_lines.append(road_ext_b)

conn = sqlite3.connect(DB_PATH)
plots = conn.execute("SELECT plot_number, survey_x, survey_y FROM plots WHERE survey_x IS NOT NULL").fetchall()
conn.close()

all_lines = fence_lines + road_lines
xs = [x for seg in all_lines for x, y in seg] + [p[1] for p in plots] + [lx for _, lx, ly, lb in LANDMARKS]
ys = [y for seg in all_lines for x, y in seg] + [p[2] for p in plots] + [ly for _, lx, ly, lb in LANDMARKS]
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

def smooth_path_for(lines):
    """Catmull-Rom spline through each line's points, as SVG cubic beziers --
    turns sharp angular corners into smooth rounded arcs. Used for the road,
    which should read as a real curved driveway, not a surveyor's polyline."""
    parts = []
    for seg in lines:
        pts = [to_svg(x, y) for x, y in seg]
        if len(pts) < 3:
            dattr = "M " + " L ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
            parts.append(dattr)
            continue
        padded = [pts[0]] + pts + [pts[-1]]
        d = [f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"]
        for i in range(1, len(padded) - 2):
            p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
            b1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            b2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d.append(f"C {b1[0]:.2f},{b1[1]:.2f} {b2[0]:.2f},{b2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}")
        parts.append(" ".join(d))
    return parts

fence_paths = "\n".join(f'<path d="{p}" class="fenceline" />' for p in path_for(fence_lines))
road_paths = "\n".join(f'<path d="{p}" class="roadline" />' for p in smooth_path_for(road_lines))

markers = []
for num, x, y in plots:
    px, py = to_svg(x, y)
    markers.append(f'<circle class="plot-marker" id="plot-{num}" cx="{px:.2f}" cy="{py:.2f}" r="1.4" />')
markers_svg = "\n".join(markers)

landmark_svg = []
for name, x, y, box in LANDMARKS:
    px, py = to_svg(x, y)
    half = box / 2
    landmark_svg.append(
        f'<g class="landmark" transform="translate({px:.2f},{py:.2f})">'
        f'<rect x="{-half:.1f}" y="{-half:.1f}" width="{box:.1f}" height="{box:.1f}" />'
        f'<text x="0" y="{-half - 3:.1f}" class="landmark-label">{name}</text>'
        f'</g>'
    )
landmarks_svg = "\n".join(landmark_svg)

rlx, rly = to_svg(*ROAD_LABEL_POS)
road_label_svg = f'<text x="{rlx:.2f}" y="{rly:.2f}" class="road-label">ROAD</text>'

with open(OUT, "w") as f:
    f.write(f"VIEWBOX=0 0 {W:.2f} {H:.2f}\n")
    f.write("FENCE\n")
    f.write(fence_paths)
    f.write("\nROAD\n")
    f.write(road_paths)
    f.write("\nLANDMARKS\n")
    f.write(landmarks_svg)
    f.write("\nROADLABEL\n")
    f.write(road_label_svg)
    f.write("\nMARKERS\n")
    f.write(markers_svg)

print(f"wrote {OUT}: {len(fence_lines)} fence segs, {len(road_lines)} road segs, {len(LANDMARKS)} landmarks, {len(plots)} plots")
print(f"viewBox: 0 0 {W:.2f} {H:.2f}")
