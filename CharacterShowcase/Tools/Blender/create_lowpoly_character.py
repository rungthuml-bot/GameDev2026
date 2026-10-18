#!/usr/bin/env python3
"""
create_lowpoly_character.py
============================
Blender 5.2 Python Script — Low Poly Humanoid Character Generator

สร้างตัวละครมนุษย์ Low Poly ท่า T-Pose สำหรับ:
  - Mixamo Auto-Rigging (FBX export)
  - Godot 4.7 (GLB export via Blender)

Usage (headless):
  blender --background --python create_lowpoly_character.py

⚠️  ข้อจำกัดที่ต้องทราบ (Procedural Geometry):
  - ตัวละครประกอบจาก Box primitives (Cube meshes)
  - ไม่มี Armature / Rig — ต้องใช้ Mixamo Auto-Rigging
  - บริเวณข้อต่อ (ไหล่, ศอก, เข่า, สะโพก) ไม่มี topology loop
  - ต้องตรวจสอบ T-Pose direction และ scale ใน Blender Editor
    ก่อนนำไป Mixamo
  - ไม่ถือว่า "พร้อมใช้งาน" จนกว่าจะผ่านการตรวจสอบด้วยตนเอง
"""

import bpy
import bmesh
import math
import os
import sys

# ══════════════════════════════════════════════════════════════════════════════
#  OUTPUT PATHS
# ══════════════════════════════════════════════════════════════════════════════
PROJECT_ROOT = r"C:\Users\ACER\Downloads\Lab6\CharacterShowcase"
BLEND_OUTPUT = os.path.join(PROJECT_ROOT, "Tools", "Blender", "character_lowpoly.blend")
FBX_OUTPUT   = os.path.join(PROJECT_ROOT, "Assets", "Models", "character_lowpoly.fbx")
GLB_OUTPUT   = os.path.join(PROJECT_ROOT, "Assets", "Models", "character_lowpoly.glb")

print("=" * 60)
print("Low Poly Character Generator — Blender 5.2")
print("=" * 60)
print(f"Blend : {BLEND_OUTPUT}")
print(f"FBX   : {FBX_OUTPUT}")
print(f"GLB   : {GLB_OUTPUT}")
print()

# ══════════════════════════════════════════════════════════════════════════════
#  CLEAR DEFAULT SCENE
# ══════════════════════════════════════════════════════════════════════════════
print("[1/7] Clearing scene...")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for blk in list(bpy.data.meshes):      bpy.data.meshes.remove(blk)
for blk in list(bpy.data.materials):   bpy.data.materials.remove(blk)
for blk in list(bpy.data.lights):      bpy.data.lights.remove(blk)
for blk in list(bpy.data.cameras):     bpy.data.cameras.remove(blk)

# ══════════════════════════════════════════════════════════════════════════════
#  MATERIALS (Flat-shaded colours)
# ══════════════════════════════════════════════════════════════════════════════
print("[2/7] Creating materials...")

def make_material(name, rgb, roughness=0.85):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
    bsdf.inputs['Roughness'].default_value  = roughness
    bsdf.inputs['Metallic'].default_value   = 0.0
    # 'Specular IOR Level' name varies by Blender version — set safely
    for spec_name in ('Specular IOR Level', 'Specular', 'Specular Level'):
        if spec_name in bsdf.inputs:
            bsdf.inputs[spec_name].default_value = 0.05
            break
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

MAT_SKIN  = make_material("M_Skin",  (0.882, 0.718, 0.580))   # warm peach
MAT_SHIRT = make_material("M_Shirt", (0.180, 0.330, 0.820))   # cobalt blue
MAT_PANTS = make_material("M_Pants", (0.120, 0.120, 0.280))   # dark navy
MAT_SHOE  = make_material("M_Shoes", (0.082, 0.060, 0.040))   # dark brown

# ══════════════════════════════════════════════════════════════════════════════
#  GEOMETRY HELPER
# ══════════════════════════════════════════════════════════════════════════════

def add_box(name, cx, cy, cz, hw, hd, hh, mat):
    """
    Create a box mesh centred at (cx,cy,cz) with half-extents (hw, hd, hh).
    hw = half-width  (X)
    hd = half-depth  (Y)
    hh = half-height (Z)
    Returns the Blender Object.
    """
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()

    # 8 corners
    coords = [
        (cx - hw, cy - hd, cz - hh),
        (cx + hw, cy - hd, cz - hh),
        (cx + hw, cy + hd, cz - hh),
        (cx - hw, cy + hd, cz - hh),
        (cx - hw, cy - hd, cz + hh),
        (cx + hw, cy - hd, cz + hh),
        (cx + hw, cy + hd, cz + hh),
        (cx - hw, cy + hd, cz + hh),
    ]
    verts = [bm.verts.new(c) for c in coords]
    bm.verts.ensure_lookup_table()

    # 6 faces  (quads, outward normals)
    face_indices = [
        (0, 1, 2, 3),   # bottom  -Z
        (7, 6, 5, 4),   # top     +Z
        (0, 4, 5, 1),   # front   -Y
        (2, 6, 7, 3),   # back    +Y
        (0, 3, 7, 4),   # left    -X
        (1, 5, 6, 2),   # right   +X
    ]
    for fi in face_indices:
        bm.faces.new([verts[i] for i in fi])

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    mesh.materials.append(mat)
    for face in mesh.polygons:
        face.material_index = 0

    return obj


# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTER PROPORTIONS  (Blender units = metres)
#
#  Design goals:
#    - Total height ≈ 1.72 m  (stylized, slightly shorter than realistic)
#    - Feet rest on Z = 0.0  (ground plane)
#    - Character faces -Y  (Blender "front view")
#    - Arms extended horizontally along +X / -X  (T-Pose)
#    - Clear separation of body segments — avoids overlapping geometry
#      at joints so Mixamo auto-rigger can identify each region
# ══════════════════════════════════════════════════════════════════════════════
print("[3/7] Computing proportions...")

# Segment heights
H_FOOT    = 0.07    # ankle block / shoe
H_LLEG    = 0.36    # lower leg (shin)
H_ULEG    = 0.37    # upper leg (thigh)
H_HIP     = 0.15    # pelvis block
H_CHEST   = 0.42    # torso / chest
H_NECK    = 0.09    # neck column
H_HEAD    = 0.26    # head block

TOTAL_H = H_FOOT + H_LLEG + H_ULEG + H_HIP + H_CHEST + H_NECK + H_HEAD
print(f"  Total height: {TOTAL_H:.3f} m")

# Cumulative Z base positions (bottom edge of each segment)
ZB_FOOT  = 0.0
ZB_LLEG  = ZB_FOOT  + H_FOOT
ZB_ULEG  = ZB_LLEG  + H_LLEG
ZB_HIP   = ZB_ULEG  + H_ULEG
ZB_CHEST = ZB_HIP   + H_HIP
ZB_NECK  = ZB_CHEST + H_CHEST
ZB_HEAD  = ZB_NECK  + H_NECK

# Centre Z of each segment
ZC_FOOT  = ZB_FOOT  + H_FOOT  / 2
ZC_LLEG  = ZB_LLEG  + H_LLEG  / 2
ZC_ULEG  = ZB_ULEG  + H_ULEG  / 2
ZC_HIP   = ZB_HIP   + H_HIP   / 2
ZC_CHEST = ZB_CHEST + H_CHEST / 2
ZC_NECK  = ZB_NECK  + H_NECK  / 2
ZC_HEAD  = ZB_HEAD  + H_HEAD  / 2

# Shoulder height = 85% up the chest segment
Z_SHOULDER = ZB_CHEST + H_CHEST * 0.83

# Arm segment lengths  (along X)
L_UARM = 0.27    # upper arm
L_FARM = 0.24    # forearm
L_HAND = 0.10    # hand block

# Chest / shoulder half-width
HW_CHEST = 0.195
# Upper arm starts at chest edge → shoulder X
X_SHOULDER = HW_CHEST + 0.005   # tiny gap

# Arm centres X
X_C_UARM = X_SHOULDER + L_UARM / 2
X_C_FARM = X_SHOULDER + L_UARM + L_FARM / 2
X_C_HAND = X_SHOULDER + L_UARM + L_FARM + L_HAND / 2

# Leg X offset from centre
X_LEG = 0.088

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD BODY PARTS
# ══════════════════════════════════════════════════════════════════════════════
print("[4/7] Building body parts...")

parts = []

# ─── Head ─────────────────────────────────────────────────────────────────────
parts.append(add_box(
    "Head",
    cx=0, cy=0, cz=ZC_HEAD,
    hw=0.115, hd=0.105, hh=H_HEAD / 2,
    mat=MAT_SKIN
))

# ─── Neck ─────────────────────────────────────────────────────────────────────
parts.append(add_box(
    "Neck",
    cx=0, cy=0, cz=ZC_NECK,
    hw=0.055, hd=0.052, hh=H_NECK / 2,
    mat=MAT_SKIN
))

# ─── Chest / Torso ────────────────────────────────────────────────────────────
#   Slight taper: use one box (low poly doesn't need sub-segments)
parts.append(add_box(
    "Chest",
    cx=0, cy=0, cz=ZC_CHEST,
    hw=HW_CHEST, hd=0.128, hh=H_CHEST / 2,
    mat=MAT_SHIRT
))

# ─── Hips / Pelvis ────────────────────────────────────────────────────────────
parts.append(add_box(
    "Hips",
    cx=0, cy=0, cz=ZC_HIP,
    hw=0.178, hd=0.118, hh=H_HIP / 2,
    mat=MAT_PANTS
))

# ─── Arms — Left side (positive X) ───────────────────────────────────────────
parts.append(add_box(
    "UpperArm_L",
    cx= X_C_UARM, cy=0, cz=Z_SHOULDER,
    hw=L_UARM / 2, hd=0.060, hh=0.064,
    mat=MAT_SHIRT
))
parts.append(add_box(
    "Forearm_L",
    cx= X_C_FARM, cy=0, cz=Z_SHOULDER,
    hw=L_FARM / 2, hd=0.050, hh=0.054,
    mat=MAT_SKIN
))
parts.append(add_box(
    "Hand_L",
    cx= X_C_HAND, cy=0, cz=Z_SHOULDER,
    hw=L_HAND / 2, hd=0.042, hh=0.030,
    mat=MAT_SKIN
))

# ─── Arms — Right side (negative X, mirror) ──────────────────────────────────
parts.append(add_box(
    "UpperArm_R",
    cx=-X_C_UARM, cy=0, cz=Z_SHOULDER,
    hw=L_UARM / 2, hd=0.060, hh=0.064,
    mat=MAT_SHIRT
))
parts.append(add_box(
    "Forearm_R",
    cx=-X_C_FARM, cy=0, cz=Z_SHOULDER,
    hw=L_FARM / 2, hd=0.050, hh=0.054,
    mat=MAT_SKIN
))
parts.append(add_box(
    "Hand_R",
    cx=-X_C_HAND, cy=0, cz=Z_SHOULDER,
    hw=L_HAND / 2, hd=0.042, hh=0.030,
    mat=MAT_SKIN
))

# ─── Legs — Left side (positive X) ───────────────────────────────────────────
parts.append(add_box(
    "UpperLeg_L",
    cx= X_LEG, cy=0, cz=ZC_ULEG,
    hw=0.082, hd=0.088, hh=H_ULEG / 2,
    mat=MAT_PANTS
))
parts.append(add_box(
    "LowerLeg_L",
    cx= X_LEG, cy=0, cz=ZC_LLEG,
    hw=0.068, hd=0.074, hh=H_LLEG / 2,
    mat=MAT_PANTS
))
parts.append(add_box(
    "Foot_L",
    cx= X_LEG, cy=-0.048, cz=ZC_FOOT,
    hw=0.062, hd=0.108, hh=H_FOOT / 2,
    mat=MAT_SHOE
))

# ─── Legs — Right side (negative X, mirror) ──────────────────────────────────
parts.append(add_box(
    "UpperLeg_R",
    cx=-X_LEG, cy=0, cz=ZC_ULEG,
    hw=0.082, hd=0.088, hh=H_ULEG / 2,
    mat=MAT_PANTS
))
parts.append(add_box(
    "LowerLeg_R",
    cx=-X_LEG, cy=0, cz=ZC_LLEG,
    hw=0.068, hd=0.074, hh=H_LLEG / 2,
    mat=MAT_PANTS
))
parts.append(add_box(
    "Foot_R",
    cx=-X_LEG, cy=-0.048, cz=ZC_FOOT,
    hw=0.062, hd=0.108, hh=H_FOOT / 2,
    mat=MAT_SHOE
))

print(f"  Body parts created: {len(parts)}")

# ══════════════════════════════════════════════════════════════════════════════
#  JOIN INTO SINGLE MESH  (required for Mixamo auto-rigging)
# ══════════════════════════════════════════════════════════════════════════════
print("[5/7] Joining parts into single mesh...")

bpy.ops.object.select_all(action='DESELECT')
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()

character = bpy.context.active_object
character.name = "LowPolyCharacter"

# Ensure feet are exactly at Z=0
bpy.context.view_layer.objects.active = character
bpy.ops.object.select_all(action='DESELECT')
character.select_set(True)

# Apply any residual transforms
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Check actual bounding box
world_min_z = min(
    (character.matrix_world @ v.co).z
    for v in character.data.vertices
)
if abs(world_min_z) > 0.001:
    character.location.z -= world_min_z
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Recheck
world_min_z2 = min(
    (character.matrix_world @ v.co).z
    for v in character.data.vertices
)
world_max_z  = max(
    (character.matrix_world @ v.co).z
    for v in character.data.vertices
)

v_count = len(character.data.vertices)
f_count = len(character.data.polygons)
mat_names = [m.name for m in character.data.materials]

print(f"  Vertices : {v_count}")
print(f"  Faces    : {f_count}")
print(f"  Materials: {mat_names}")
print(f"  Foot Z   : {world_min_z2:.4f}  (should be ~0.0)")
print(f"  Top  Z   : {world_max_z:.4f}  (should be ≈ {TOTAL_H:.3f})")

# ══════════════════════════════════════════════════════════════════════════════
#  CAMERA + LIGHTING  (for Blender preview, not game scene)
# ══════════════════════════════════════════════════════════════════════════════
print("[6/7] Setting up camera and lights...")

# Camera — front view, framing full body
cam_data = bpy.data.cameras.new("Preview_Cam")
cam_data.type = 'PERSP'   # Blender 5.x enum value
cam_data.lens = 50.0
cam_obj = bpy.data.objects.new("Preview_Cam", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
cam_obj.location = (0.0, -3.6, TOTAL_H * 0.5)
cam_obj.rotation_euler = (math.radians(90), 0.0, 0.0)
bpy.context.scene.camera = cam_obj

# Key light — sun from upper-left-front
sun_data = bpy.data.lights.new("Key_Light", 'SUN')
sun_data.energy = 4.5
sun_data.color  = (1.0, 0.96, 0.89)
sun_obj = bpy.data.objects.new("Key_Light", sun_data)
bpy.context.scene.collection.objects.link(sun_obj)
sun_obj.location = (2.0, -3.0, 4.0)
sun_obj.rotation_euler = (math.radians(55), math.radians(0), math.radians(30))

# Fill light — point from left
fill_data = bpy.data.lights.new("Fill_Light", 'POINT')
fill_data.energy = 280.0
fill_data.color  = (0.45, 0.55, 1.0)
fill_obj = bpy.data.objects.new("Fill_Light", fill_data)
bpy.context.scene.collection.objects.link(fill_obj)
fill_obj.location = (-2.5, -1.5, 2.0)

# Rim light — back
rim_data = bpy.data.lights.new("Rim_Light", 'POINT')
rim_data.energy = 200.0
rim_data.color  = (1.0, 0.75, 0.4)
rim_obj = bpy.data.objects.new("Rim_Light", rim_data)
bpy.context.scene.collection.objects.link(rim_obj)
rim_obj.location = (0.5, 2.8, 2.5)

# World background (dark studio)
world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes.clear()
bg_node  = world.node_tree.nodes.new('ShaderNodeBackground')
bg_node.inputs['Color'].default_value    = (0.07, 0.06, 0.11, 1.0)
bg_node.inputs['Strength'].default_value = 0.5
out_node = world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(bg_node.outputs['Background'], out_node.inputs['Surface'])

# Render settings (Cycles for preview quality)
scene = bpy.context.scene
scene.render.engine              = 'CYCLES'
scene.render.resolution_x       = 1280
scene.render.resolution_y       = 720
scene.cycles.samples             = 64
scene.render.film_transparent    = False

# ══════════════════════════════════════════════════════════════════════════════
#  SAVE .BLEND
# ══════════════════════════════════════════════════════════════════════════════
print("[7/7] Saving files...")

os.makedirs(os.path.dirname(BLEND_OUTPUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUTPUT)
blend_size = os.path.getsize(BLEND_OUTPUT)
print(f"  ✅ .blend saved  ({blend_size // 1024} KB): {BLEND_OUTPUT}")

# ──────────────────────────────────────────────────────────────────────────────
#  EXPORT FBX  (for Mixamo upload)
# ──────────────────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='DESELECT')
character.select_set(True)
bpy.context.view_layer.objects.active = character

os.makedirs(os.path.dirname(FBX_OUTPUT), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath             = FBX_OUTPUT,
    use_selection        = True,
    apply_scale_options  = 'FBX_SCALE_ALL',
    bake_space_transform = True,
    use_mesh_modifiers   = True,
    mesh_smooth_type     = 'FACE',
    use_tspace           = True,
    global_scale         = 1.0,
    axis_forward         = '-Z',      # Blender -Y → FBX +Z (Mixamo standard)
    axis_up              = 'Y',       # Blender +Z → FBX +Y
    add_leaf_bones       = False,
    bake_anim            = False,     # No animation yet
)
fbx_size = os.path.getsize(FBX_OUTPUT)
print(f"  ✅ FBX  exported ({fbx_size // 1024} KB): {FBX_OUTPUT}")

# ──────────────────────────────────────────────────────────────────────────────
#  EXPORT GLB  (direct Godot import, backup)
# ──────────────────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(GLB_OUTPUT), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath             = GLB_OUTPUT,
    export_format        = 'GLB',
    use_selection        = True,
    export_apply         = True,
    export_materials     = 'EXPORT',
    export_cameras       = False,
    export_lights        = False,
    # export_yup / export_normals / export_colors vary by version — use defaults
)
glb_size = os.path.getsize(GLB_OUTPUT)
print(f"  ✅ GLB  exported ({glb_size // 1024} KB): {GLB_OUTPUT}")

# ══════════════════════════════════════════════════════════════════════════════
#  FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("CHARACTER GENERATION COMPLETE")
print("=" * 60)
print(f"  Geometry type   : Procedural Box Mesh (Low Poly)")
print(f"  Total height    : {world_max_z:.3f} m")
print(f"  Foot Z (ground) : {world_min_z2:.4f} m  (target: 0.000)")
print(f"  Vertex count    : {v_count}")
print(f"  Face count      : {f_count}")
print(f"  Materials       : {mat_names}")
print(f"  Pose            : T-Pose (arms horizontal along ±X)")
print(f"  Facing          : -Y  (Blender front view)")
print()
print("⚠️  LIMITATIONS (must inspect before Mixamo upload):")
print("  1. No topology edge loops at joints")
print("  2. Body parts are solid boxes — no internal connectivity")
print("  3. Gap geometry between segments (shoulder, elbow, knee)")
print("  4. No armature / rig — requires Mixamo Auto-Rigging")
print("  5. Scale and orientation must be verified in Blender Editor")
print()
print("✅ NEXT STEPS (manual inspection required):")
print("  1. Open character_lowpoly.blend in Blender 5.2")
print("  2. Check front/side/top views for T-Pose correctness")
print("  3. Confirm no inverted normals (Overlay > Face Orientation)")
print("  4. Verify character faces -Y in front view")
print("  5. Check feet are at Z=0.000 exactly")
print("  6. Upload character_lowpoly.fbx to mixamo.com")
print("  7. After Mixamo rigging: download GLB and place in Assets/Models/")
print("=" * 60)
