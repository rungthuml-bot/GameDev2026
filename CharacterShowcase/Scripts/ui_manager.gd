## ui_manager.gd
## Godot 4.7 | GDScript
## Main scene controller for 3D Character Animation Showcase.
## - Loads character_rigged.fbx from Assets/Models/
## - Restores the 4-color Low Poly material palette (Skin, Shirt, Pants, Shoes)
## - Registers all 8 Mixamo animations into an AnimationLibrary
## - Handles UI controls (Prev / Next / Play-Pause / Status)
## - Integrates with CameraOrbit for smooth showcase interaction

extends Node3D

# ── Scene node references (set via @onready) ──────────────────────────────────
@onready var anim_name_label: Label    = $UI/AnimationPanel/MarginContainer/VBoxContainer/BottomBar/AnimNameLabel
@onready var status_label:    Label    = $UI/AnimationPanel/MarginContainer/VBoxContainer/StatusLabel
@onready var btn_prev:        Button   = $UI/AnimationPanel/MarginContainer/VBoxContainer/BottomBar/BtnPrev
@onready var btn_next:        Button   = $UI/AnimationPanel/MarginContainer/VBoxContainer/BottomBar/BtnNext
@onready var btn_play_pause:  Button   = $UI/AnimationPanel/MarginContainer/VBoxContainer/BottomBar/BtnPlayPause
@onready var spawn_point:     Marker3D = $CharacterSpawnPoint
@onready var camera:          Camera3D = $CameraRig/Camera3D

# ── State ─────────────────────────────────────────────────────────────────────
var character_node:     Node3D          = null
var animation_player:   AnimationPlayer = null
var animation_list:     Array[String]   = []
var current_anim_index: int             = 0
var is_playing:         bool            = true
var is_finished:        bool            = false

# Path to rigged character model
const CHARACTER_MODEL_PATH := "res://Assets/Models/character_rigged.fbx"

# 8 Mixamo animation configurations
const MIXAMO_ANIMATIONS := [
	{"name": "Idle",      "file": "anim_idle.fbx",      "loop": true},
	{"name": "Walking",   "file": "anim_walking.fbx",   "loop": true},
	{"name": "Running",   "file": "anim_running.fbx",   "loop": true},
	{"name": "Reaction",  "file": "anim_reaction.fbx",  "loop": false},
	{"name": "Taunt",     "file": "anim_taunt.fbx",     "loop": false},
	{"name": "Capoeira",  "file": "anim_capoeira.fbx",  "loop": false},
	{"name": "Defeated",  "file": "anim_defeated.fbx",  "loop": false},
	{"name": "Boxing",    "file": "anim_boxing.fbx",    "loop": false}
]

# Material palette colors (matching original Blender design)
const COLOR_SKIN  := Color(0.882, 0.718, 0.580)
const COLOR_SHIRT := Color(0.180, 0.330, 0.820)
const COLOR_PANTS := Color(0.120, 0.120, 0.280)
const COLOR_SHOES := Color(0.082, 0.060, 0.040)


func _ready() -> void:
	_connect_buttons()
	_try_load_character()


# ── Button wiring ─────────────────────────────────────────────────────────────
func _connect_buttons() -> void:
	if not btn_prev.pressed.is_connected(_on_prev_pressed):
		btn_prev.pressed.connect(_on_prev_pressed)
	if not btn_next.pressed.is_connected(_on_next_pressed):
		btn_next.pressed.connect(_on_next_pressed)
	if not btn_play_pause.pressed.is_connected(_on_play_pause_pressed):
		btn_play_pause.pressed.connect(_on_play_pause_pressed)
	_set_buttons_enabled(false)


func _set_buttons_enabled(enabled: bool) -> void:
	btn_prev.disabled       = not enabled
	btn_next.disabled       = not enabled
	btn_play_pause.disabled = not enabled


# ── Character loading & setup ─────────────────────────────────────────────────
func _try_load_character() -> void:
	if not ResourceLoader.exists(CHARACTER_MODEL_PATH):
		_set_status_waiting("Character model not found at: " + CHARACTER_MODEL_PATH)
		return

	var scene: PackedScene = load(CHARACTER_MODEL_PATH)
	if scene == null:
		_set_status_error("Failed to load PackedScene from: " + CHARACTER_MODEL_PATH)
		return

	character_node = scene.instantiate() as Node3D
	if character_node == null:
		_set_status_error("Failed to instantiate character as Node3D")
		return

	add_child(character_node)
	character_node.global_position = spawn_point.global_position

	# Move camera target to character torso height and set optimal framing
	if camera:
		if "orbit_distance" in camera:
			camera.orbit_distance = 3.4
		if "orbit_pitch" in camera:
			camera.orbit_pitch = -8.0
		if camera.has_method("set_orbit_target"):
			camera.set_orbit_target(spawn_point.global_position + Vector3(0, 0.9, 0))

	# Restore character material palette
	_restore_character_materials()

	# Find and configure AnimationPlayer
	_setup_animations()


# ── Material palette restoration ──────────────────────────────────────────────
func _restore_character_materials() -> void:
	if character_node == null:
		return

	# Material for skin parts (Head & Bridge_NeckHead)
	var mat_skin := StandardMaterial3D.new()
	mat_skin.resource_name = "M_Skin"
	mat_skin.albedo_color = COLOR_SKIN
	mat_skin.roughness = 0.85
	mat_skin.metallic = 0.0

	var head_mesh: MeshInstance3D = character_node.find_child("Head", true, false)
	if head_mesh:
		head_mesh.material_override = mat_skin

	var neck_mesh: MeshInstance3D = character_node.find_child("Bridge_NeckHead", true, false)
	if neck_mesh:
		neck_mesh.material_override = mat_skin

	# Main body mesh: bake vertex colors based on bind-pose geometric heights
	var body_mesh: MeshInstance3D = character_node.find_child("LowPolyCharacter_Mixamo", true, false)
	if body_mesh and body_mesh.mesh is ArrayMesh:
		var orig_mesh: ArrayMesh = body_mesh.mesh
		if orig_mesh.get_surface_count() > 0:
			var arrs := orig_mesh.surface_get_arrays(0)
			var verts: PackedVector3Array = arrs[Mesh.ARRAY_VERTEX]
			var colors := PackedColorArray()
			colors.resize(verts.size())

			for i in range(verts.size()):
				var p: Vector3 = verts[i]
				var c := COLOR_SHIRT # Torso default
				if p.y < 0.075:
					c = COLOR_SHOES   # Feet / Shoes
				elif p.y < 0.95:
					c = COLOR_PANTS   # Hips & Legs
				elif abs(p.x) > 0.32 and p.y > 1.15:
					c = COLOR_SKIN    # Forearms & Hands
				elif p.y > 1.365 and abs(p.x) < 0.12:
					c = COLOR_SKIN    # Neck
				colors[i] = c

			arrs[Mesh.ARRAY_COLOR] = colors

			var colored_mesh := ArrayMesh.new()
			colored_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrs)

			var mat_body := StandardMaterial3D.new()
			mat_body.resource_name = "M_Body_Palette"
			mat_body.vertex_color_use_as_albedo = true
			mat_body.roughness = 0.85
			mat_body.metallic = 0.0
			colored_mesh.surface_set_material(0, mat_body)

			body_mesh.mesh = colored_mesh
			print("[ShowcaseUI] Restored 4-color palette onto character model")


# ── Animation setup ───────────────────────────────────────────────────────────
func _setup_animations() -> void:
	animation_player = _find_child_of_type(character_node, "AnimationPlayer") as AnimationPlayer
	if animation_player == null:
		_set_status_error("Character loaded, but no AnimationPlayer found")
		return

	# Connect animation finished signal safely
	if not animation_player.animation_finished.is_connected(_on_animation_finished):
		animation_player.animation_finished.connect(_on_animation_finished)

	# Register the 8 Mixamo animations
	var mixamo_lib := AnimationLibrary.new()
	var loaded_count := 0

	for cfg in MIXAMO_ANIMATIONS:
		var file_path := "res://Assets/Animations/Mixamo/" + str(cfg["file"])
		if ResourceLoader.exists(file_path):
			var a_scene: PackedScene = load(file_path)
			if a_scene:
				var a_inst: Node = a_scene.instantiate()
				var src_ap: AnimationPlayer = _find_child_of_type(a_inst, "AnimationPlayer") as AnimationPlayer
				if src_ap and src_ap.has_animation("mixamo_com"):
					var clip: Animation = src_ap.get_animation("mixamo_com").duplicate()
					clip.loop_mode = Animation.LOOP_LINEAR if cfg["loop"] else Animation.LOOP_NONE
					mixamo_lib.add_animation(str(cfg["name"]), clip)
					loaded_count += 1
				a_inst.free()

	if animation_player.has_animation_library("Mixamo"):
		animation_player.remove_animation_library("Mixamo")
	animation_player.add_animation_library("Mixamo", mixamo_lib)
	print("[ShowcaseUI] Registered %d Mixamo animations" % loaded_count)

	_build_animation_list()

	if animation_list.is_empty():
		_set_status_error("No animations loaded")
		return

	status_label.text = "Character loaded successfully."
	status_label.modulate = Color(0.4, 1.0, 0.5)
	_set_buttons_enabled(true)
	_play_animation(0)


func _build_animation_list() -> void:
	animation_list.clear()
	if animation_player.has_animation_library("Mixamo"):
		var lib: AnimationLibrary = animation_player.get_animation_library("Mixamo")
		for cfg in MIXAMO_ANIMATIONS:
			var anim_name: String = str(cfg["name"])
			if lib.has_animation(anim_name):
				animation_list.append("Mixamo/" + anim_name)
		for anim_name in lib.get_animation_list():
			var full_name := "Mixamo/" + anim_name
			if not full_name in animation_list:
				animation_list.append(full_name)


# ── Animation playback ────────────────────────────────────────────────────────
func _play_animation(index: int) -> void:
	if animation_player == null or animation_list.is_empty():
		return

	current_anim_index = index
	var full_name: String = animation_list[current_anim_index]
	var display_name: String = full_name.get_slice("/", 1) if "/" in full_name else full_name

	# Reset character spawn position so locomotion cycles don't carry off the platform
	if character_node:
		character_node.global_position = spawn_point.global_position

	animation_player.play(full_name)
	is_playing = true
	is_finished = false
	btn_play_pause.text = "Pause"

	# Get loop mode and duration info
	var anim: Animation = animation_player.get_animation(full_name)
	var dur_text := "%.2fs" % anim.length if anim else "0.00s"

	anim_name_label.text = "Animation: %s" % display_name
	status_label.text = "Playing: %s | Duration: %s" % [display_name, dur_text]
	status_label.modulate = Color(0.4, 0.9, 1.0)


func _on_animation_finished(_anim_name: StringName) -> void:
	is_finished = true
	is_playing = false
	btn_play_pause.text = "Replay"
	status_label.text = "Animation finished. Select Replay to play again."
	status_label.modulate = Color(0.8, 0.8, 0.8)


func _on_prev_pressed() -> void:
	if animation_list.is_empty():
		return
	var idx := (current_anim_index - 1 + animation_list.size()) % animation_list.size()
	_play_animation(idx)


func _on_next_pressed() -> void:
	if animation_list.is_empty():
		return
	var idx := (current_anim_index + 1) % animation_list.size()
	_play_animation(idx)


func _on_play_pause_pressed() -> void:
	if animation_player == null:
		return
	var full_name: String = animation_list[current_anim_index]
	var display_name: String = full_name.get_slice("/", 1) if "/" in full_name else full_name
	var anim: Animation = animation_player.get_animation(full_name)
	var dur_text := "%.2fs" % anim.length if anim else "0.00s"

	if is_finished:
		# Replay finished one-shot animation
		_play_animation(current_anim_index)
	elif is_playing:
		animation_player.pause()
		btn_play_pause.text = "Play"
		is_playing = false
		status_label.text = "Paused: %s | Duration: %s" % [display_name, dur_text]
	else:
		animation_player.play()
		btn_play_pause.text = "Pause"
		is_playing = true
		status_label.text = "Playing: %s | Duration: %s" % [display_name, dur_text]


# ── Utility ───────────────────────────────────────────────────────────────────
func _find_child_of_type(node: Node, type_name: String) -> Node:
	if node.get_class() == type_name:
		return node
	for child in node.get_children():
		var result := _find_child_of_type(child, type_name)
		if result != null:
			return result
	return null


func _set_status_waiting(msg: String) -> void:
	status_label.text = "Waiting: " + msg
	status_label.modulate = Color(1, 0.8, 0.2)
	anim_name_label.text = "No Character Loaded"
	_set_buttons_enabled(false)


func _set_status_error(msg: String) -> void:
	status_label.text = "Error: " + msg
	status_label.modulate = Color(1, 0.3, 0.3)
	anim_name_label.text = "Error"
	_set_buttons_enabled(false)
