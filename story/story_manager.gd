extends Node

## StoryManager — autoload singleton.
## Holds the full act/beat structure and tracks completion state.
##
## Add to AutoLoad as "StoryManager" (res://story/story_manager.gd).

signal beat_completed(beat: StoryBeat)

const SAVE_PATH := "user://story_progress.cfg"

const _ACT_PATHS := [
	"res://story/act_01_the_fall.tres",
	"res://story/act_02_homecoming.tres",
	"res://story/act_03_renovations.tres",
	"res://story/act_04_uberfall.tres",
	"res://story/act_05_boy_meets_girl.tres",
	"res://story/act_06_cult_of_fire.tres",
	"res://story/act_07_edge_of_town.tres",
	"res://story/act_08_the_keyhole.tres",
]

var acts: Array[StoryAct] = []


func _ready() -> void:
	for path in _ACT_PATHS:
		var act := load(path) as StoryAct
		if act:
			acts.append(act)
	_load_progress()


# ── Public API ────────────────────────────────────────────────────────────────

func complete_beat(id: StringName) -> void:
	var beat := find_beat(id)
	if beat and not beat.completed:
		beat.completed = true
		beat_completed.emit(beat)
		_save_progress()


func is_beat_done(id: StringName) -> bool:
	var beat := find_beat(id)
	return beat.completed if beat else false


func find_beat(id: StringName) -> StoryBeat:
	for act in acts:
		for beat in act.beats:
			if beat.id == id:
				return beat
	return null


## Returns all beats whose .zone matches the given zone label.
func beats_for_zone(zone_label: String) -> Array[StoryBeat]:
	var result: Array[StoryBeat] = []
	for act in acts:
		for beat in act.beats:
			if beat.zone == zone_label:
				result.append(beat)
	return result


## Returns true if every beat in every act is completed.
func is_story_complete() -> bool:
	for act in acts:
		for beat in act.beats:
			if not beat.completed:
				return false
	return true


# ── Persistence ───────────────────────────────────────────────────────────────

func _save_progress() -> void:
	var cfg := ConfigFile.new()
	for act in acts:
		for beat in act.beats:
			cfg.set_value("beats", str(beat.id), beat.completed)
	cfg.save(SAVE_PATH)


func _load_progress() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) != OK:
		return
	for act in acts:
		for beat in act.beats:
			beat.completed = cfg.get_value("beats", str(beat.id), false)
