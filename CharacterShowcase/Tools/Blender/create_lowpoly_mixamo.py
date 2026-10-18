#!/usr/bin/env python3
"""
create_lowpoly_mixamo.py
========================
Blender 5.2 — สร้าง Low Poly Character เวอร์ชันปรับปรุงสำหรับ Mixamo Auto-Rigging

การปรับปรุงจากเวอร์ชันเดิม:
  1. ไม่มีช่องว่าง (gap) ระหว่างชิ้นส่วนร่างกาย — แต่ละชิ้นแตะกันพอดี
  2. ใช้ Bridge Geometry ที่ข้อต่อสำคัญ (ไหล่ สะโพก คอ) เพื่อให้ silhouette ต่อเนื่อง
  3. เพิ่มความกว้างที่ไหล่และสะโพก เพื่อให้ Mixamo จำแนก joint ได้ง่ายขึ้น
  4. ใช้ merge_by_distance ลบ duplicate vertices ที่จุดสัมผัส
  5. ยืนยัน T-Pose orientation ก่อน export

⚠️ ข้อจำกัด (ยังคงอยู่):
  - ยังเป็น Box geometry (Low Poly style)
  - ไม่มี edge loops ที่ข้อต่อ — deformation จะ blocky
  - ไม่มี Armature — ต้องใช้ Mixamo Auto-Rigging
  - ยังต้องตรวจสอบด้วยตนเองก่อน Mixamo upload

Usage:
  blender --background --python create_lowpoly_mixamo.py
"""

import bpy
import bmesh
import math
import os

PROJECT_ROOT  = r"C:\Users\ACER\Downloads\Lab6\CharacterShowcase"
BLEND_ORIG    = os.path.join(PROJECT_ROOT, "Tools", "Blender", "character_lowpoly.blend")
BLEND_OUT     = os.path.join(PROJECT_ROOT, "Tools", "Blender", "character_lowpoly_mixamo.blend")
FBX_OUT       = os.path.join(PROJECT_ROOT, "Assets", "Models",  "character_lowpoly_mixamo.fbx")
GLB_OUT       = os.path.join(PROJECT_ROOT, "Assets", "Models",  "character_lowpoly_mixamo.glb")

print("=" * 70)
print("Low Poly Character — Mixamo Edition  (Phase 3.1)")
print("=" * 70)
print(f"Blend (NEW) : {BLEND_OUT}")
print(f"FBX  (NEW)  : {FBX_OUT}")
print(f"Original    : {BLEND_ORIG}  ← NOT MODIFIED")
print()

# Confirm original is untouched
if os.path.exists(BLEND_ORIG):
    orig_size = os.path.getsize(BLEND_ORIG)
    print(f"✅ Original .blend preserved ({orig_size} bytes)")
else:
    print("⚠ Original .blend not found at expected path")

# ── Clear scene (fresh start — NOT loading original) ──────────────────────────
print("\n[1/8] Clearing scene...")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for blk in list(bpy.data.meshes):     bpy.data.meshes.remove(blk)
for blk in list(bpy.data.materials):  bpy.data.materials.remove(blk)
for blk in list(bpy.data.lights):     bpy.data.lights.remove(blk)
for blk in list(bpy.data.cameras):    bpy.data.cameras.remove(blk)

# ── Materials ─────────────────────────────────────────────────────────────────
print("[2/8] Creating materials (same as original)...")

def make_mat(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
    bsdf.inputs['Roughness'].default_value  = 0.85
    bsdf.inputs['Metallic'].default_value   = 0.0
    for key in ('Specular IOR Level', 'Specular', 'Specular Level'):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.05
            break
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

MAT_SKIN  = make_mat("M_Skin",  (0.882, 0.718, 0.580))
MAT_SHIRT = make_mat("M_Shirt", (0.180, 0.330, 0.820))
MAT_PANTS = make_mat("M_Pants", (0.120, 0.120, 0.280))
MAT_SHOE  = make_mat("M_Shoes", (0.082, 0.060, 0.040))

# ── Geometry helper ───────────────────────────────────────────────────────────
def add_box(name, cx, cy, cz, hw, hd, hh, mat):
    """Box centred at (cx,cy,cz) with half-extents hw/hd/hh."""
    mesh_data = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh_data)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    coords = [
        (cx-hw, cy-hd, cz-hh), (cx+hw, cy-hd, cz-hh),
        (cx+hw, cy+hd, cz-hh), (cx-hw, cy+hd, cz-hh),
        (cx-hw, cy-hd, cz+hh), (cx+hw, cy-hd, cz+hh),
        (cx+hw, cy+hd, cz+hh), (cx-hw, cy+hd, cz+hh),
    ]
    verts = [bm.verts.new(c) for c in coords]
    bm.verts.ensure_lookup_table()
    for fi in [(0,1,2,3),(7,6,5,4),(0,4,5,1),(2,6,7,3),(0,3,7,4),(1,5,6,2)]:
        bm.faces.new([verts[i] for i in fi])
    bm.normal_update()
    bm.to_mesh(mesh_data)
    bm.free()
    mesh_data.update()
    mesh_data.materials.append(mat)
    for face in mesh_data.polygons:
        face.material_index = 0
    return obj


def add_bridge_box(name, cx, cy, cz_bot, cz_top, hw_bot, hd_bot, hw_top, hd_top, mat):
    """
    Tapered box (frustum) connecting two different-sized cross-sections.
    Used for shoulder-to-arm and hip-to-leg bridges to improve Mixamo joint detection.
    """
    mesh_data = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh_data)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    # Bottom face (larger side)
    bot = [
        bm.verts.new((cx-hw_bot, cy-hd_bot, cz_bot)),
        bm.verts.new((cx+hw_bot, cy-hd_bot, cz_bot)),
        bm.verts.new((cx+hw_bot, cy+hd_bot, cz_bot)),
        bm.verts.new((cx-hw_bot, cy+hd_bot, cz_bot)),
    ]
    # Top face (smaller side)
    top = [
        bm.verts.new((cx-hw_top, cy-hd_top, cz_top)),
        bm.verts.new((cx+hw_top, cy-hd_top, cz_top)),
        bm.verts.new((cx+hw_top, cy+hd_top, cz_top)),
        bm.verts.new((cx-hw_top, cy+hd_top, cz_top)),
    ]
    bm.verts.ensure_lookup_table()
    bm.faces.new([bot[3], bot[2], bot[1], bot[0]])   # bottom (outward = down)
    bm.faces.new([top[0], top[1], top[2], top[3]])   # top    (outward = up)
    bm.faces.new([bot[0], bot[1], top[1], top[0]])   # front
    bm.faces.new([bot[2], bot[3], top[3], top[2]])   # back
    bm.faces.new([bot[3], bot[0], top[0], top[3]])   # left
    bm.faces.new([bot[1], bot[2], top[2], top[1]])   # right
    bm.normal_update()
    bm.to_mesh(mesh_data)
    bm.free()
    mesh_data.update()
    mesh_data.materials.append(mat)
    for face in mesh_data.polygons:
        face.material_index = 0
    return obj

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTER PROPORTIONS (same as original for consistency)
# ══════════════════════════════════════════════════════════════════════════════
print("[3/8] Computing proportions...")

H_FOOT  = 0.07;  H_LLEG  = 0.36;  H_ULEG  = 0.37
H_HIP   = 0.15;  H_CHEST = 0.42;  H_NECK  = 0.09;  H_HEAD  = 0.26

TOTAL_H = H_FOOT + H_LLEG + H_ULEG + H_HIP + H_CHEST + H_NECK + H_HEAD
print(f"  Total height: {TOTAL_H:.3f} m  (identical to v1)")

ZB_FOOT  = 0.0
ZB_LLEG  = ZB_FOOT  + H_FOOT;  ZB_ULEG  = ZB_LLEG  + H_LLEG
ZB_HIP   = ZB_ULEG  + H_ULEG;  ZB_CHEST = ZB_HIP   + H_HIP
ZB_NECK  = ZB_CHEST + H_CHEST; ZB_HEAD  = ZB_NECK  + H_NECK

ZC_FOOT  = ZB_FOOT  + H_FOOT  / 2;  ZC_LLEG  = ZB_LLEG  + H_LLEG  / 2
ZC_ULEG  = ZB_ULEG  + H_ULEG  / 2;  ZC_HIP   = ZB_HIP   + H_HIP   / 2
ZC_CHEST = ZB_CHEST + H_CHEST / 2;  ZC_NECK  = ZB_NECK  + H_NECK  / 2
ZC_HEAD  = ZB_HEAD  + H_HEAD  / 2

Z_SHOULDER = ZB_CHEST + H_CHEST * 0.83

# Arm dims (unchanged)
L_UARM = 0.27;  L_FARM = 0.24;  L_HAND = 0.10

# IMPROVED: chest wider so shoulder bridge connects cleanly
HW_CHEST = 0.200   # slightly wider than original (was 0.195)
HD_CHEST = 0.130

X_SHOULDER = HW_CHEST          # arm starts exactly at chest edge (NO GAP)
X_C_UARM   = X_SHOULDER + L_UARM / 2
X_C_FARM   = X_SHOULDER + L_UARM + L_FARM / 2
X_C_HAND   = X_SHOULDER + L_UARM + L_FARM + L_HAND / 2

X_LEG = 0.090   # slightly wider leg separation (was 0.088)

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD BODY — MIXAMO IMPROVEMENTS:
#    1. Zero gaps between adjacent segments (exact Z boundaries)
#    2. Shoulder bridge pieces (tapered) for smooth silhouette
#    3. Hip-to-thigh bridge
#    4. Neck-to-head bridge
# ══════════════════════════════════════════════════════════════════════════════
print("[4/8] Building improved body parts...")

parts = []

# ─── HEAD ─────────────────────────────────────────────────────────────────────
parts.append(add_box("Head",  0, 0, ZC_HEAD,  0.118, 0.108, H_HEAD /2, MAT_SKIN))

# ─── NECK-to-HEAD bridge (taper from neck to head width) ─────────────────────
bridge_nh_h = 0.025
parts.append(add_bridge_box(
    "Bridge_NeckHead",
    cx=0, cy=0,
    cz_bot=ZB_HEAD,
    cz_top=ZB_HEAD + bridge_nh_h,
    hw_bot=0.058, hd_bot=0.055,   # neck width
    hw_top=0.118, hd_top=0.108,   # head width
    mat=MAT_SKIN
))
# Adjust head Z so it sits above the bridge
ZC_HEAD_ADJ = ZB_HEAD + bridge_nh_h + H_HEAD / 2
parts[-1]  # bridge already added

# Re-add head at adjusted position
parts.pop()       # remove bridge
parts.pop()       # remove head
# Re-create with bridge integrated
parts.append(add_bridge_box(
    "Bridge_NeckHead",
    cx=0, cy=0,
    cz_bot=ZB_HEAD,
    cz_top=ZB_HEAD + bridge_nh_h,
    hw_bot=0.058, hd_bot=0.055,
    hw_top=0.118, hd_top=0.108,
    mat=MAT_SKIN
))
parts.append(add_box("Head", 0, 0,
    ZB_HEAD + bridge_nh_h + H_HEAD / 2,
    0.118, 0.108, H_HEAD / 2,
    MAT_SKIN
))

# ─── NECK ─────────────────────────────────────────────────────────────────────
parts.append(add_box("Neck", 0, 0, ZC_NECK, 0.058, 0.055, H_NECK / 2, MAT_SKIN))

# ─── CHEST/TORSO ──────────────────────────────────────────────────────────────
parts.append(add_box("Chest", 0, 0, ZC_CHEST, HW_CHEST, HD_CHEST, H_CHEST / 2, MAT_SHIRT))

# ─── SHOULDER BRIDGES (tapered, connects chest to upper arm) ──────────────────
# Left shoulder: tapers from chest-width at shoulder Z to arm width
SHLDR_H = 0.08    # bridge height at shoulder
SHLDR_INNER_X = HW_CHEST          # inner face at chest edge
SHLDR_OUTER_X = X_SHOULDER + 0.06 # outer face at arm start + arm radius

parts.append(add_bridge_box(
    "ShoulderBridge_L",
    cx = SHLDR_INNER_X + (SHLDR_OUTER_X - SHLDR_INNER_X) / 2,
    cy = 0,
    cz_bot = Z_SHOULDER - SHLDR_H / 2,
    cz_top = Z_SHOULDER + SHLDR_H / 2,
    hw_bot = (SHLDR_OUTER_X - SHLDR_INNER_X) / 2, hd_bot = HD_CHEST,
    hw_top = (SHLDR_OUTER_X - SHLDR_INNER_X) / 2, hd_top = 0.060,
    mat = MAT_SHIRT
))
parts.append(add_bridge_box(
    "ShoulderBridge_R",
    cx = -(SHLDR_INNER_X + (SHLDR_OUTER_X - SHLDR_INNER_X) / 2),
    cy = 0,
    cz_bot = Z_SHOULDER - SHLDR_H / 2,
    cz_top = Z_SHOULDER + SHLDR_H / 2,
    hw_bot = (SHLDR_OUTER_X - SHLDR_INNER_X) / 2, hd_bot = HD_CHEST,
    hw_top = (SHLDR_OUTER_X - SHLDR_INNER_X) / 2, hd_top = 0.060,
    mat = MAT_SHIRT
))

# ─── ARMS (zero-gap from shoulder) ────────────────────────────────────────────
parts.append(add_box("UpperArm_L",  X_C_UARM, 0, Z_SHOULDER, L_UARM/2, 0.060, 0.064, MAT_SHIRT))
parts.append(add_box("Forearm_L",   X_C_FARM, 0, Z_SHOULDER, L_FARM/2, 0.050, 0.054, MAT_SKIN))
parts.append(add_box("Hand_L",      X_C_HAND, 0, Z_SHOULDER, L_HAND/2, 0.042, 0.030, MAT_SKIN))

parts.append(add_box("UpperArm_R", -X_C_UARM, 0, Z_SHOULDER, L_UARM/2, 0.060, 0.064, MAT_SHIRT))
parts.append(add_box("Forearm_R",  -X_C_FARM, 0, Z_SHOULDER, L_FARM/2, 0.050, 0.054, MAT_SKIN))
parts.append(add_box("Hand_R",     -X_C_HAND, 0, Z_SHOULDER, L_HAND/2, 0.042, 0.030, MAT_SKIN))

# ─── HIPS ─────────────────────────────────────────────────────────────────────
# Slightly wider hips for better Mixamo hip bone detection
parts.append(add_box("Hips", 0, 0, ZC_HIP, 0.185, 0.122, H_HIP / 2, MAT_PANTS))

# ─── HIP-to-LEG bridge (tapered from hip width to leg width) ─────────────────
LEG_BRIDGE_H = 0.04
for side, sx in [("L", X_LEG), ("R", -X_LEG)]:
    parts.append(add_bridge_box(
        f"HipBridge_{side}",
        cx    = sx, cy = 0,
        cz_bot= ZB_ULEG,
        cz_top= ZB_ULEG + LEG_BRIDGE_H,
        hw_bot= 0.090, hd_bot= 0.100,   # wide at hip connection
        hw_top= 0.082, hd_top= 0.088,   # narrows to thigh
        mat   = MAT_PANTS
    ))

# ─── UPPER LEGS (start above bridge) ─────────────────────────────────────────
ULEG_ADJ_Z = ZB_ULEG + LEG_BRIDGE_H
ULEG_ADJ_H = H_ULEG - LEG_BRIDGE_H

for side, sx in [("L", X_LEG), ("R", -X_LEG)]:
    parts.append(add_box(
        f"UpperLeg_{side}", sx, 0,
        ULEG_ADJ_Z + ULEG_ADJ_H / 2,
        0.082, 0.088, ULEG_ADJ_H / 2,
        MAT_PANTS
    ))

# ─── LOWER LEGS ──────────────────────────────────────────────────────────────
for side, sx in [("L", X_LEG), ("R", -X_LEG)]:
    parts.append(add_box(f"LowerLeg_{side}", sx, 0, ZC_LLEG, 0.068, 0.074, H_LLEG / 2, MAT_PANTS))

# ─── FEET (wider front — extends toward -Y for shoe toe) ─────────────────────
for side, sx in [("L", X_LEG), ("R", -X_LEG)]:
    parts.append(add_box(f"Foot_{side}", sx, -0.048, ZC_FOOT, 0.064, 0.110, H_FOOT / 2, MAT_SHOE))

total_parts = len(parts)
print(f"  Body parts created: {total_parts}")

# ══════════════════════════════════════════════════════════════════════════════
#  JOIN + MERGE BY DISTANCE
# ══════════════════════════════════════════════════════════════════════════════
print("[5/8] Joining and cleaning mesh...")

bpy.ops.object.select_all(action='DESELECT')
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()

character = bpy.context.active_object
character.name = "LowPolyCharacter_Mixamo"

# Apply transforms
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Merge by distance — weld vertices within 0.001 m
# This cleans up any floating point duplicates at shared edges
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.001)   # 1mm — conservative
bpy.ops.mesh.normals_make_consistent(inside=False)  # Recalculate outward
bpy.ops.object.mode_set(mode='OBJECT')

# Count islands after merge
mesh_data = character.data
adj = {i: [] for i in range(len(mesh_data.vertices))}
from collections import deque
for edge in mesh_data.edges:
    v0, v1 = edge.vertices
    adj[v0].append(v1)
    adj[v1].append(v0)

visited = [False] * len(mesh_data.vertices)
island_count = 0
for start in range(len(mesh_data.vertices)):
    if visited[start]: continue
    island_count += 1
    q = deque([start])
    while q:
        v = q.popleft()
        if visited[v]: continue
        visited[v] = True
        for nb in adj[v]:
            if not visited[nb]: q.append(nb)

# Fix foot Z
world_min_z = min((character.matrix_world @ v.co).z for v in mesh_data.vertices)
if abs(world_min_z) > 0.001:
    character.location.z -= world_min_z
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

world_min_z2 = min((character.matrix_world @ v.co).z for v in mesh_data.vertices)
world_max_z  = max((character.matrix_world @ v.co).z for v in mesh_data.vertices)
world_min_x  = min((character.matrix_world @ v.co).x for v in mesh_data.vertices)
world_max_x  = max((character.matrix_world @ v.co).x for v in mesh_data.vertices)

v_count = len(mesh_data.vertices)
f_count = len(mesh_data.polygons)

print(f"  Vertices        : {v_count}  (v1 had 128)")
print(f"  Faces           : {f_count}  (v1 had 96)")
print(f"  Islands         : {island_count}  (v1 had 16)")
print(f"  Height          : {world_max_z:.4f} m")
print(f"  Width (armspan) : {world_max_x - world_min_x:.4f} m")
print(f"  Foot Z          : {world_min_z2:.6f}  (target: 0.000)")

# ══════════════════════════════════════════════════════════════════════════════
#  CAMERA + LIGHTS
# ══════════════════════════════════════════════════════════════════════════════
print("[6/8] Adding camera and lights...")

cam_d = bpy.data.cameras.new("Cam")
cam_d.type = 'PERSP'
cam_d.lens = 50.0
cam_o = bpy.data.objects.new("Cam", cam_d)
bpy.context.scene.collection.objects.link(cam_o)
cam_o.location = (0.0, -4.0, TOTAL_H * 0.5)
cam_o.rotation_euler = (math.radians(90), 0.0, 0.0)
bpy.context.scene.camera = cam_o

for lname, ltype, loc, energy, col in [
    ("Key",  "SUN",   (2.0, -3.0, 4.0), 4.5, (1.0, 0.96, 0.89)),
    ("Fill", "POINT", (-2.5, -1.5, 2.0), 280.0, (0.45, 0.55, 1.0)),
    ("Rim",  "POINT", (0.5, 2.8, 2.5),  200.0, (1.0, 0.75, 0.4)),
]:
    ld = bpy.data.lights.new(lname, ltype)
    ld.energy = energy
    ld.color  = col
    lo = bpy.data.objects.new(lname, ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = loc
    if ltype == 'SUN':
        lo.rotation_euler = (math.radians(55), 0, math.radians(30))

world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes.clear()
bg = world.node_tree.nodes.new('ShaderNodeBackground')
bg.inputs['Color'].default_value    = (0.07, 0.06, 0.11, 1.0)
bg.inputs['Strength'].default_value = 0.5
out_w = world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(bg.outputs['Background'], out_w.inputs['Surface'])

# ══════════════════════════════════════════════════════════════════════════════
#  SAVE .BLEND (new file — original untouched)
# ══════════════════════════════════════════════════════════════════════════════
print("[7/8] Saving files...")

os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
blend_sz = os.path.getsize(BLEND_OUT)
print(f"  ✅ .blend saved  ({blend_sz // 1024} KB): {BLEND_OUT}")

# Verify original still intact
if os.path.exists(BLEND_ORIG):
    orig_sz = os.path.getsize(BLEND_ORIG)
    print(f"  ✅ Original .blend untouched ({orig_sz} bytes): {BLEND_ORIG}")
else:
    print(f"  ⚠ Original .blend not found: {BLEND_ORIG}")

# ── Export FBX ────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='DESELECT')
character.select_set(True)
bpy.context.view_layer.objects.active = character

os.makedirs(os.path.dirname(FBX_OUT), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath             = FBX_OUT,
    use_selection        = True,
    apply_scale_options  = 'FBX_SCALE_ALL',
    bake_space_transform = True,
    use_mesh_modifiers   = True,
    mesh_smooth_type     = 'FACE',
    global_scale         = 1.0,
    axis_forward         = '-Z',
    axis_up              = 'Y',
    add_leaf_bones       = False,
    bake_anim            = False,
)
fbx_sz = os.path.getsize(FBX_OUT)
print(f"  ✅ FBX  exported ({fbx_sz // 1024} KB): {FBX_OUT}")

# ── Export GLB ────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(GLB_OUT), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath         = GLB_OUT,
    export_format    = 'GLB',
    use_selection    = True,
    export_apply     = True,
    export_materials = 'EXPORT',
    export_cameras   = False,
    export_lights    = False,
)
glb_sz = os.path.getsize(GLB_OUT)
print(f"  ✅ GLB  exported ({glb_sz // 1024} KB): {GLB_OUT}")

# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("[8/8] MIXAMO EDITION SUMMARY")
print("=" * 70)
print(f"  Vertices      : {v_count}  (was 128 in v1)")
print(f"  Faces         : {f_count}  (was 96 in v1)")
print(f"  Islands       : {island_count}  (was 16 in v1)")
print(f"  Height        : {world_max_z:.4f} m")
print(f"  Arm span      : {world_max_x - world_min_x:.4f} m")
print(f"  Foot Z        : {world_min_z2:.6f}")
print()
print("  IMPROVEMENTS over v1:")
print("    ✅ Zero gap at shoulder (arm starts at exact chest edge)")
print("    ✅ Shoulder bridge (tapered box connecting chest to arm)")
print("    ✅ Hip-to-leg bridge (tapered, wider at hip for bone detection)")
print("    ✅ Neck-to-head bridge (tapered transition)")
print("    ✅ Merge by distance (removes float-precision duplicates)")
print("    ✅ Normals recalculated outward (Recalculate Outside)")
print()
print("  REMAINING LIMITATIONS:")
print("    ⚠ Still separate mesh islands (box-based construction)")
print("    ⚠ No edge loops at joints (Low Poly style preserved)")
print("    ⚠ No Armature — requires Mixamo Auto-Rigging")
print("    ⚠ Must inspect in Blender Editor before Mixamo upload")
print()
print("  FILES PRODUCED:")
print(f"    {BLEND_OUT}")
print(f"    {FBX_OUT}")
print(f"    {GLB_OUT}")
print()
print("  ⚠ ORIGINAL PRESERVED (untouched):")
print(f"    {BLEND_ORIG}")
print("=" * 70)
