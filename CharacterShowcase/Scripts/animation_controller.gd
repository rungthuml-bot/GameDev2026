## animation_controller.gd
## Godot 4.7 | GDScript
## Standalone animation controller — attach to a character node that has
## an AnimationPlayer child. Provides API for external callers (ui_manager).
##
## NOTE: This script is INACTIVE in Phase 2 (no character model yet).
##       It will be wired up in Phase 6 when character.glb is imported.

extends Node

@export var animation_player_path: NodePath = NodePath("AnimationPlayer")

var _player: AnimationPlayer = null


func _ready() -> void:
	_player = get_node_or_null(animation_player_path) as AnimationPlayer
	if _player == null:
		push_warning("[AnimController] AnimationPlayer not found at: " + str(animation_player_path))


## Play animation by full name (library/animation_name format)
func play(anim_name: String) -> void:
	if _player == null:
		return
	if _player.has_animation(anim_name):
		_player.play(anim_name)
	else:
		push_warning("[AnimController] Animation not found: " + anim_name)


## Pause current animation
func pause() -> void:
	if _player:
		_player.pause()


## Resume paused animation
func resume() -> void:
	if _player:
		_player.play()


## Returns list of all available animation names across all libraries
func get_animation_names() -> Array[String]:
	if _player == null:
		return []
	var names: Array[String] = []
	for lib_name in _player.get_animation_library_list():
		var lib: AnimationLibrary = _player.get_animation_library(lib_name)
		for anim_name in lib.get_animation_list():
			names.append((lib_name + "/" + anim_name) if lib_name != "" else anim_name)
	return names


## Returns name of currently playing animation
func get_current_animation() -> String:
	if _player == null:
		return ""
	return _player.current_animation


## Set playback speed (1.0 = normal, 0.5 = half, 2.0 = double)
func set_speed(speed: float) -> void:
	if _player:
		_player.speed_scale = speed
