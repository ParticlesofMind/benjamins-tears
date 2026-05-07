extends CanvasLayer

# Zone data parsed from story/world_sketch.tldr
# Format: [label, tldraw_x, tldraw_y]
const ZONE_DATA := [
	["Forest of Beasts", 689, -1098],
	["Abandoned Settlement", 1865, -1000],
	["The Watchtower I", 2656, -958],
	["Maze I", 4232, -844],
	["Old Guard Posts", 1230, -778],
	["The Crossing", 2702, -678],
	["Maze II", 4225, -615],
	["Town", 817, -610],
	["The Arena", 3282, -556],
	["The Heavens", 4596, -524],
	["Drylands", 470, -512],
	["Church", 1217, -495],
	["The Wall", 2787, -418],
	["Maze III", 4198, -366],
	["Drylands (North)", 270, -360],
	["The Coast", 1131, -273],
	["Wetlands", 726, -255],
	["Culture of Fire", 1836, -182],
	["Ruins", 248, -147],
	["The Watchtower II", 2565, -145],
	["Maze IV", 4218, -139],
	["Ruins (South)", 625, -99],
	["Dropoff", 625, 42],
	["Graveyard of Angels", 248, 63],
	["The Lighthouse", 1424, 91],
	["Crater", 469, 157],
]

# Connections between zones (index pairs)
const CONNECTIONS := [
	[0, 4],
	[0, 7],  # Forest of Beasts — Old Guard Posts, Town
	[4, 7],
	[4, 11],  # Old Guard Posts — Town, Church
	[7, 10],
	[7, 16],
	[7, 11],  # Town — Drylands, Wetlands, Church
	[10, 14],
	[10, 18],  # Drylands — Drylands North, Ruins
	[11, 1],  # Church — Abandoned Settlement
	[1, 5],
	[1, 2],  # Abandoned Settlement — The Crossing, Watchtower I
	[5, 12],
	[5, 8],  # The Crossing — The Wall, The Arena
	[12, 9],  # The Wall — The Heavens (via maze)
	[15, 24],  # The Coast — The Lighthouse
	[17, 5],  # Culture of Fire — The Crossing
	[18, 23],
	[23, 25],  # Ruins — Graveyard — Crater
	[22, 25],
	[22, 23],  # Dropoff — Crater, Graveyard
]

# Source coordinate bounds
const SRC_X_MIN := 248.0
const SRC_X_MAX := 4596.0
const SRC_Y_MIN := -1098.0
const SRC_Y_MAX := 157.0

# Display area within 1920x1080
const MAP_RECT := Rect2(120, 90, 1680, 560)

var _zone_nodes: Array = []
var _zone_dots: Dictionary = {}
var _visible := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	_build_zones()
	var story_manager := get_node_or_null("/root/StoryManager")
	if story_manager and story_manager.has_signal("beat_completed"):
		story_manager.beat_completed.connect(_on_story_beat_completed)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_M:
			_toggle()
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_ESCAPE and _visible:
			_close()
			get_viewport().set_input_as_handled()


func _toggle() -> void:
	if _visible:
		_close()
	else:
		_open()


func _open() -> void:
	_visible = true
	visible = true
	refresh_zone_colors()
	get_tree().paused = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)


func refresh_zone_colors() -> void:
	for zone_label in _zone_dots:
		var dot: ColorRect = _zone_dots[zone_label]
		if is_instance_valid(dot):
			dot.color = _zone_color(zone_label)


func _close() -> void:
	_visible = false
	visible = false
	get_tree().paused = false
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _src_to_screen(tx: float, ty: float) -> Vector2:
	var nx := (tx - SRC_X_MIN) / (SRC_X_MAX - SRC_X_MIN)
	var ny := (ty - SRC_Y_MIN) / (SRC_Y_MAX - SRC_Y_MIN)
	return Vector2(
		MAP_RECT.position.x + nx * MAP_RECT.size.x, MAP_RECT.position.y + ny * MAP_RECT.size.y
	)


func _build_zones() -> void:
	var map_area: Control = $Background/MapPanel/MapArea
	var line_layer: Node2D = $Background/MapPanel/Lines

	# Draw connection lines first (behind dots)
	for conn in CONNECTIONS:
		var a := _src_to_screen(ZONE_DATA[conn[0]][1], ZONE_DATA[conn[0]][2])
		var b := _src_to_screen(ZONE_DATA[conn[1]][1], ZONE_DATA[conn[1]][2])
		var line := Line2D.new()
		line.add_point(a - MAP_RECT.position)
		line.add_point(b - MAP_RECT.position)
		line.width = 1.0
		line.default_color = Color(0.55, 0.45, 0.3, 0.35)
		line_layer.add_child(line)

	# Draw zone nodes
	for zone in ZONE_DATA:
		var label: String = zone[0]
		var screen_pos := _src_to_screen(zone[1], zone[2])
		var local_pos := screen_pos - MAP_RECT.position

		var btn := Button.new()
		btn.flat = true
		btn.text = ""
		btn.custom_minimum_size = Vector2(14, 14)
		btn.position = local_pos - Vector2(7, 7)
		btn.tooltip_text = label
		map_area.add_child(btn)

		# Dot — colour reflects story beat status for this zone
		var dot := ColorRect.new()
		dot.size = Vector2(8, 8)
		dot.position = Vector2(3, 3)
		dot.color = _zone_color(label)
		btn.add_child(dot)
		_zone_dots[label] = dot

		# Label
		var lbl := Label.new()
		lbl.text = label
		lbl.position = Vector2(12, -6)
		lbl.add_theme_font_size_override("font_size", 10)
		lbl.add_theme_color_override("font_color", Color(0.8, 0.72, 0.55, 0.85))
		btn.add_child(lbl)

		_zone_nodes.append(btn)


## Returns a dot colour based on story beat completion for a given zone label.
## - All beats done   → green
## - Some beats done  → amber
## - No beats / zone not in story → default parchment
func _zone_color(zone_label: String) -> Color:
	var story_manager := get_node_or_null("/root/StoryManager")
	if not story_manager or not story_manager.has_method("beats_for_zone"):
		return Color(0.85, 0.75, 0.55, 0.9)
	var beats: Array = story_manager.beats_for_zone(zone_label)
	if beats.is_empty():
		return Color(0.85, 0.75, 0.55, 0.9)
	var done := beats.filter(func(b): return b.completed).size()
	if done == beats.size():
		return Color(0.4, 0.85, 0.45, 0.9)  # all complete — green
	if done > 0:
		return Color(0.95, 0.75, 0.2, 0.9)  # partial — amber
	return Color(0.85, 0.75, 0.55, 0.9)  # untouched — parchment


func _on_story_beat_completed(_beat: StoryBeat) -> void:
	refresh_zone_colors()
