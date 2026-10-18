## camera_orbit.gd
## Godot 4.7 | GDScript
## Orbit camera around the character spawn point.
## Controls:
##   - Left Mouse Button drag: orbit (yaw/pitch)
##   - Mouse Scroll:           zoom in/out
##   - A/D keys:               orbit left/right
##   - W/S keys:               zoom in/out

extends Camera3D

# ── Orbit parameters ──────────────────────────────────────────────────────────
@export var orbit_target: Vector3 = Vector3(0.0, 1.0, 0.0)
@export var orbit_distance: float = 4.5
@export var orbit_yaw: float     = 0.0      # horizontal angle (degrees)
@export var orbit_pitch: float   = -15.0    # vertical angle (degrees)

@export var orbit_speed_mouse: float = 0.3  # degrees per pixel
@export var orbit_speed_key:   float = 60.0 # degrees per second (A/D)
@export var zoom_speed:        float = 0.5
@export var zoom_min:          float = 1.0
@export var zoom_max:          float = 12.0
@export var pitch_min:         float = -70.0
@export var pitch_max:         float = 20.0

# ── Internal state ─────────────────────────────────────────────────────────────
var _is_dragging: bool = false
var _last_mouse_pos: Vector2 = Vector2.ZERO


func _ready() -> void:
	_apply_orbit()


func _input(event: InputEvent) -> void:
	# ── Mouse button drag ──────────────────────────────────────────────────────
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			_is_dragging = event.pressed
			if _is_dragging:
				_last_mouse_pos = event.position

		# Scroll zoom
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			orbit_distance = clampf(orbit_distance - zoom_speed, zoom_min, zoom_max)
			_apply_orbit()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			orbit_distance = clampf(orbit_distance + zoom_speed, zoom_min, zoom_max)
			_apply_orbit()

	# ── Mouse motion drag ──────────────────────────────────────────────────────
	elif event is InputEventMouseMotion and _is_dragging:
		var delta: Vector2 = event.position - _last_mouse_pos
		_last_mouse_pos = event.position

		orbit_yaw   -= delta.x * orbit_speed_mouse
		orbit_pitch -= delta.y * orbit_speed_mouse
		orbit_pitch  = clampf(orbit_pitch, pitch_min, pitch_max)
		_apply_orbit()


func _process(delta: float) -> void:
	# ── Keyboard orbit ─────────────────────────────────────────────────────────
	var key_input := 0.0
	if Input.is_action_pressed("camera_orbit_left"):
		key_input -= 1.0
	if Input.is_action_pressed("camera_orbit_right"):
		key_input += 1.0

	if key_input != 0.0:
		orbit_yaw += key_input * orbit_speed_key * delta
		_apply_orbit()

	# Keyboard zoom
	if Input.is_action_pressed("camera_zoom_in"):
		orbit_distance = clampf(orbit_distance - zoom_speed * delta * 5.0, zoom_min, zoom_max)
		_apply_orbit()
	if Input.is_action_pressed("camera_zoom_out"):
		orbit_distance = clampf(orbit_distance + zoom_speed * delta * 5.0, zoom_min, zoom_max)
		_apply_orbit()


## Recomputes camera position and orientation from orbit angles + distance.
func _apply_orbit() -> void:
	var yaw_rad:   float = deg_to_rad(orbit_yaw)
	var pitch_rad: float = deg_to_rad(orbit_pitch)

	var offset := Vector3(
		orbit_distance * cos(pitch_rad) * sin(yaw_rad),
		orbit_distance * sin(pitch_rad),
		orbit_distance * cos(pitch_rad) * cos(yaw_rad)
	)

	global_position = orbit_target + offset
	look_at(orbit_target, Vector3.UP)


## Called by ui_manager when a character is loaded — updates orbit target height.
func set_orbit_target(pos: Vector3) -> void:
	orbit_target = pos
	_apply_orbit()
