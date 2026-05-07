class_name StoryBeat extends Resource

## A single narrative beat — the atomic unit of the story.

@export var id: StringName           ## Unique identifier, e.g. &"fall_from_building"
@export var title: String
@export var zone: String             ## Matches a label in journal_map.gd ZONE_DATA
@export var description: String
@export var completed: bool = false
