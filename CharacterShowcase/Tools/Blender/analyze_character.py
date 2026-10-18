#!/usr/bin/env python3
"""
analyze_character.py
=====================
Blender 5.2 — ตรวจสอบ character_lowpoly.blend สำหรับ Mixamo Auto-Rigging

Usage:
  blender --background --python analyze_character.py
"""

import bpy
import bmesh
import os
import math
from collections import deque

BLEND_PATH   = r"C:\Users\ACER\Downloads\Lab6\CharacterShowcase\Tools\Blender\character_lowpoly.blend"
REPORT_PATH  = r"C:\Users\ACER\Downloads\Lab6\CharacterShowcase\Tools\Blender\analysis_report.txt"

print("=" * 70)
print("Character Analysis Script — Phase 3.1")
print("=" * 70)

# ── Load .blend ───────────────────────────────────────────────────────────────
if not os.path.exists(BLEND_PATH):
    print(f"ERROR: .blend not found: {BLEND_PATH}")
    raise SystemExit(1)

bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
print(f"Loaded: {BLEND_PATH}")

# ── Find character mesh ───────────────────────────────────────────────────────
char = None
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # Prefer LowPolyCharacter
        if 'LowPoly' in obj.name or 'Character' in obj.name:
            char = obj
            break

if char is None:
    # Fall back to largest mesh
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if meshes:
        char = max(meshes, key=lambda o: len(o.data.vertices))

if char is None:
    print("ERROR: No mesh object found in scene!")
    raise SystemExit(1)

print(f"\nAnalysing object: '{char.name}'")
print()

report_lines = []

def log(msg=""):
    print(msg)
    report_lines.append(msg)

# ══════════════════════════════════════════════════════════════════════════════
#  1. TRANSFORM CHECK
# ══════════════════════════════════════════════════════════════════════════════
log("─" * 70)
log("1. TRANSFORM (Object Mode)")
log("─" * 70)

loc = char.location
rot = char.rotation_euler
sca = char.scale

scale_ok    = all(abs(s - 1.0) < 0.0001 for s in sca)
rotation_ok = all(abs(r)       < 0.0001 for r in rot)
location_ok = abs(loc.x) < 0.001 and abs(loc.y) < 0.001

log(f"  Location  : X={loc.x:.4f}  Y={loc.y:.4f}  Z={loc.z:.4f}")
log(f"  Rotation  : X={math.degrees(rot.x):.2f}°  Y={math.degrees(rot.y):.2f}°  Z={math.degrees(rot.z):.2f}°")
log(f"  Scale     : X={sca.x:.4f}  Y={sca.y:.4f}  Z={sca.z:.4f}")
log()
log(f"  Scale applied (all = 1.0)     : {'✅ YES' if scale_ok else '❌ NO — must Apply Scale'}")
log(f"  Rotation applied (all = 0.0°) : {'✅ YES' if rotation_ok else '❌ NO — must Apply Rotation'}")
log(f"  Centred X/Y at origin         : {'✅ YES' if location_ok else '⚠ OFFSET — check centering'}")

# ══════════════════════════════════════════════════════════════════════════════
#  2. MESH STATISTICS
# ══════════════════════════════════════════════════════════════════════════════
log()
log("─" * 70)
log("2. MESH STATISTICS")
log("─" * 70)

mesh = char.data
v_count = len(mesh.vertices)
e_count = len(mesh.edges)
f_count = len(mesh.polygons)
mat_count = len(mesh.materials)

log(f"  Vertices  : {v_count}")
log(f"  Edges     : {e_count}")
log(f"  Faces     : {f_count}")
log(f"  Materials : {mat_count}  → {[m.name for m in mesh.materials]}")

# ══════════════════════════════════════════════════════════════════════════════
#  3. BOUNDING BOX & DIMENSIONS
# ══════════════════════════════════════════════════════════════════════════════
log()
log("─" * 70)
log("3. WORLD-SPACE BOUNDING BOX")
log("─" * 70)

world_verts = [(char.matrix_world @ v.co) for v in mesh.vertices]
min_x = min(v.x for v in world_verts);  max_x = max(v.x for v in world_verts)
min_y = min(v.y for v in world_verts);  max_y = max(v.y for v in world_verts)
min_z = min(v.z for v in world_verts);  max_z = max(v.z for v in world_verts)

width  = max_x - min_x
depth  = max_y - min_y
height = max_z - min_z

log(f"  X (width)  : {min_x:.4f} → {max_x:.4f}  =  {width:.4f} m")
log(f"  Y (depth)  : {min_y:.4f} → {max_y:.4f}  =  {depth:.4f} m")
log(f"  Z (height) : {min_z:.4f} → {max_z:.4f}  =  {height:.4f} m")
log()
log(f"  Foot Z (min): {min_z:.6f}  {'✅ on ground (< 0.001)' if abs(min_z) < 0.001 else '❌ not at ground!'}")
log(f"  Total height: {height:.4f} m")
log(f"  Total width : {width:.4f} m  (arm-span including hands)")

# Mixamo expects roughly human proportions
aspect = height / width if width > 0 else 0
log(f"  H/W ratio   : {aspect:.2f}  (typical human: 1.3–2.0)")
if 1.2 <= aspect <= 2.2:
    log(f"  Proportion  : ✅ Within acceptable range for Mixamo")
else:
    log(f"  Proportion  : ⚠ Unusual — may cause Mixamo auto-rig issues")

# ══════════════════════════════════════════════════════════════════════════════
#  4. GEOMETRY ISLANDS (Disconnected Components)
# ══════════════════════════════════════════════════════════════════════════════
log()
log("─" * 70)
log("4. GEOMETRY ISLANDS (Disconnected Mesh Regions)")
log("─" * 70)

# Build vertex adjacency from edges
adj = {i: [] for i in range(v_count)}
for edge in mesh.edges:
    v0, v1 = edge.vertices
    adj[v0].append(v1)
    adj[v1].append(v0)

visited = [False] * v_count
islands = []
for start in range(v_count):
    if visited[start]:
        continue
    island_verts = []
    queue = deque([start])
    while queue:
        v_idx = queue.popleft()
        if visited[v_idx]:
            continue
        visited[v_idx] = True
        island_verts.append(v_idx)
        for nb in adj[v_idx]:
            if not visited[nb]:
                queue.append(nb)
    islands.append(island_verts)

log(f"  Total mesh islands : {len(islands)}")
log()

# Classify islands by Z range
def classify_island(verts_idx, mesh_obj):
    verts = [mesh_obj.data.vertices[i].co for i in verts_idx]
    zmin = min(v.z for v in verts)
    zmax = max(v.z for v in verts)
    xmin = min(v.x for v in verts)
    xmax = max(v.x for v in verts)
    ymin = min(v.y for v in verts)
    ymax = max(v.y for v in verts)
    return {
        'count': len(verts_idx),
        'zmin': zmin, 'zmax': zmax,
        'xmin': xmin, 'xmax': xmax,
        'ymin': ymin, 'ymax': ymax,
        'width': xmax - xmin,
        'height': zmax - zmin,
        'cx': (xmin + xmax) / 2,
        'cz': (zmin + zmax) / 2,
    }

islands_info = [classify_island(isl, char) for isl in islands]
# Sort by Z centre descending (top = head, bottom = feet)
islands_info.sort(key=lambda i: i['cz'], reverse=True)

# Map Z ranges to body parts
total_h = height
body_labels = {
    (0.85, 1.00): "Head",
    (0.75, 0.90): "Neck",
    (0.45, 0.80): "Chest/Torso",
    (0.40, 0.55): "Hips",
    (0.00, 0.10): "Feet",
    (0.05, 0.25): "Lower Legs",
    (0.20, 0.50): "Upper Legs",
}

log(f"  {'#':>3}  {'Verts':>5}  {'Z min':>7}  {'Z max':>7}  {'Height':>7}  {'Width':>7}  {'Cx':>7}  Region")
log("  " + "-" * 65)
for i, info in enumerate(islands_info):
    # Guess body region from Z
    z_frac_min = info['zmin'] / total_h if total_h > 0 else 0
    z_frac_max = info['zmax'] / total_h if total_h > 0 else 0
    z_frac_c   = info['cz']  / total_h if total_h > 0 else 0
    cx_abs = abs(info['cx'])

    if z_frac_c > 0.82:                        region = "Head"
    elif z_frac_c > 0.78:                      region = "Neck"
    elif z_frac_c > 0.52 and cx_abs < 0.05:   region = "Chest"
    elif z_frac_c > 0.52 and cx_abs > 0.35:   region = "Hand L/R"
    elif z_frac_c > 0.52 and cx_abs > 0.25:   region = "Forearm L/R"
    elif z_frac_c > 0.52 and cx_abs > 0.12:   region = "Upper Arm L/R"
    elif z_frac_c > 0.44 and cx_abs < 0.05:   region = "Hips"
    elif z_frac_c > 0.28:                      region = "Upper Leg L/R"
    elif z_frac_c > 0.08:                      region = "Lower Leg L/R"
    else:                                       region = "Foot L/R"

    log(f"  {i+1:>3}  {info['count']:>5}  {info['zmin']:>7.3f}  {info['zmax']:>7.3f}  "
        f"{info['height']:>7.3f}  {info['width']:>7.3f}  {info['cx']:>7.3f}  {region}")

# ══════════════════════════════════════════════════════════════════════════════
#  5. GAP ANALYSIS AT JOINTS
# ══════════════════════════════════════════════════════════════════════════════
log()
log("─" * 70)
log("5. GAP ANALYSIS AT CRITICAL JOINTS")
log("─" * 70)

# Find gaps between adjacent islands by checking min distance between islands
# We check the vertical gaps (Z-axis) between torso islands

# Sort islands by Z centre
sorted_by_z = sorted(islands_info, key=lambda i: i['cz'])

log("  Vertical gaps between adjacent body segments (Z-axis):")
log()
for i in range(len(sorted_by_z) - 1):
    lower = sorted_by_z[i]
    upper = sorted_by_z[i + 1]
    gap_z = upper['zmin'] - lower['zmax']
    
    if abs(lower['cx']) > 0.15 and abs(upper['cx']) > 0.15:
        continue  # Skip arm-to-arm comparisons (different X)
    if abs(lower['cx'] - upper['cx']) > 0.1:
        continue  # Different X sides

    status = ""
    if gap_z < -0.001:
        status = "✅ OVERLAP"
    elif gap_z < 0.002:
        status = "✅ TOUCHING (~0)"
    elif gap_z < 0.015:
        status = "⚠ SMALL GAP"
    else:
        status = "❌ GAP — Mixamo may misidentify joint"

    log(f"    Z {lower['zmax']:.3f} → {upper['zmin']:.3f}  gap={gap_z:+.4f} m  {status}")

# ══════════════════════════════════════════════════════════════════════════════
#  6. FACE ORIENTATION / NORMALS CHECK
# ══════════════════════════════════════════════════════════════════════════════
log()
log("─" * 70)
log("6. FACE NORMALS CHECK")
log("─" * 70)

# Use bmesh for normal analysis
bm = bmesh.new()
bm.from_mesh(mesh)
bm.normal_update()

outward_count  = 0
inward_count   = 0
zero_area_count = 0

for face in bm.faces:
    if face.calc_area() < 1e-8:
        zero_area_count += 1
        continue
    # Check if normal points roughly away from mesh centre
    face_centre = face.calc_center_median()
    dot = face.normal.dot(face_centre.normalized())
    if dot >= 0:
        outward_count += 1
    else:
        inward_count += 1

bm.free()

total_valid = outward_count + inward_count
log(f"  Total faces       : {f_count}")
log(f"  Zero-area faces   : {zero_area_count}")
log(f"  Outward normals   : {outward_count}  ({100*outward_count/max(total_valid,1):.1f}%)")
log(f"  Inward normals    : {inward_count}   ({100*inward_count/max(total_valid,1):.1f}%)")

if inward_count == 0:
    log(f"  Result            : ✅ All normals outward — good for Mixamo")
elif inward_count < f_count * 0.05:
    log(f"  Result            : ⚠ Minor inward normals — may need Recalculate Outside")
else:
    log(f"  Result            : ❌ Many inverted normals — MUST fix before Mixamo upload")

# ══════════════════════════════════════════════════════════════════════════════
#  7. MIXAMO READINESS ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════
log()
log("─" * 70)
log("7. MIXAMO AUTO-RIGGING READINESS ASSESSMENT")
log("─" * 70)

issues  = []
notes   = []
passed  = []

# Island count
if len(islands) == 1:
    passed.append(f"Fully connected mesh (1 island)")
elif len(islands) <= 8:
    notes.append(f"{len(islands)} mesh islands — Mixamo can handle this (disconnected acceptable)")
else:
    notes.append(f"{len(islands)} mesh islands — Mixamo usually handles multi-piece meshes BUT joint detection may be less precise")

# Scale
if not scale_ok:
    issues.append("Scale not applied (not 1,1,1) — MUST apply before FBX export")
else:
    passed.append("Scale applied (1,1,1)")

# Foot Z
if abs(min_z) < 0.001:
    passed.append(f"Feet at ground Z≈0 ({min_z:.5f})")
else:
    issues.append(f"Feet not at Z=0 (min_z={min_z:.4f}) — Mixamo expects ground at 0")

# Height
if 1.2 <= height <= 2.5:
    passed.append(f"Height {height:.3f}m in normal range")
else:
    issues.append(f"Height {height:.3f}m unusual — may confuse Mixamo")

# Normals
if inward_count == 0:
    passed.append("No inverted normals detected")
else:
    issues.append(f"{inward_count} inverted normals — fix with Recalculate Outside")

# Materials
if mat_count > 0:
    passed.append(f"{mat_count} materials assigned")
else:
    notes.append("No materials — acceptable but grey in Mixamo preview")

log()
log("  ✅ PASSED:")
for p in passed:
    log(f"    • {p}")

if notes:
    log()
    log("  ⚠ NOTES (acceptable for Mixamo):")
    for n in notes:
        log(f"    • {n}")

if issues:
    log()
    log("  ❌ ISSUES TO FIX:")
    for iss in issues:
        log(f"    • {iss}")

log()
if not issues:
    log("  VERDICT: ✅ MESH APPEARS SUITABLE FOR MIXAMO AUTO-RIGGING")
    log("           (Still requires manual visual inspection in Blender)")
else:
    log("  VERDICT: ⚠ FIX THE ISSUES ABOVE BEFORE MIXAMO UPLOAD")

# ══════════════════════════════════════════════════════════════════════════════
#  8. MANUAL INSPECTION CHECKLIST
# ══════════════════════════════════════════════════════════════════════════════
log()
log("─" * 70)
log("8. MANUAL INSPECTION CHECKLIST (must do in Blender Editor)")
log("─" * 70)
checklist = [
    "Open character_lowpoly.blend in Blender 5.2",
    "Numpad 1 (Front View) — character faces TOWARD you (-Y direction)",
    "Numpad 3 (Right Side View) — character stands upright, no lean",
    "Numpad 7 (Top View) — left/right arms are symmetric",
    "Overlay > Face Orientation — all faces BLUE (outward)",
    "Select character → N panel → Dimensions match analysis report",
    "Arms clearly separate from torso with visible elbow midpoints",
    "Head clearly distinct from neck (significant size difference)",
    "Feet clearly wider/longer than ankles",
    "No missing body parts (check all 16 expected islands visible)",
]
for i, item in enumerate(checklist, 1):
    log(f"  [{i:2d}] ☐  {item}")

# ══════════════════════════════════════════════════════════════════════════════
#  SAVE REPORT
# ══════════════════════════════════════════════════════════════════════════════
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print()
print(f"Report saved: {REPORT_PATH}")
print("=" * 70)
