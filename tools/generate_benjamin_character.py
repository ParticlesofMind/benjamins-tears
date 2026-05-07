"""
Deprecated procedural Benjamin placeholder generator.

Benjamin's active player model must come from the Character Creator/Blender
source and the accepted Mesh2Motion game rig export. This script is kept only
as an archived prototype/reference path, and it refuses to run unless explicitly
allowed so it cannot overwrite the real runtime asset by accident.
"""

from __future__ import annotations

import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


PROJECT_ROOT = "/Users/benjaminjacklaubacher/benjamin's-tears"
ACTIVE_BLEND = os.path.join(
    PROJECT_ROOT, "assets/models/characters/benjamin/source/BenjaminCharacter.blend"
)
ACTIVE_RUNTIME_OUTPUT = os.path.join(
    PROJECT_ROOT, "assets/models/characters/benjamin/runtime/benjamin_male_animated.glb"
)
PLACEHOLDER_ARCHIVE_DIR = os.path.join(
    PROJECT_ROOT, "archive/character_export_attempts/procedural_placeholder_workbench"
)
DEFAULT_BLEND = os.path.join(PLACEHOLDER_ARCHIVE_DIR, "BenjaminCharacter_generated_placeholder.blend")
DEFAULT_RUNTIME_OUTPUT = os.path.join(
    PLACEHOLDER_ARCHIVE_DIR, "benjamin_male_generated_placeholder.glb"
)
SOURCE_NOTE_PATH = os.path.join(PLACEHOLDER_ARCHIVE_DIR, "GENERATED_CHARACTER.md")
ALLOW_ENV_VAR = "BT_ALLOW_PLACEHOLDER_BENJAMIN"

COLLECTION_NAME = "BT_Generated_Benjamin"
ARMATURE_NAME = "Benjamin_Rig"

LOOP_ACTIONS = {
    "idle",
    "walk",
    "walk_backward",
    "walk_strafe_left",
    "walk_strafe_right",
    "sprint",
}

REQUIRED_ACTIONS = [
    "idle",
    "walk",
    "walk_backward",
    "walk_strafe_left",
    "walk_strafe_right",
    "sprint",
    "jump",
    "fall",
    "land",
]

MAJOR_BONES = [
    "root",
    "hips",
    "spine",
    "chest",
    "neck",
    "head",
    "upper_arm.L",
    "forearm.L",
    "hand.L",
    "upper_arm.R",
    "forearm.R",
    "hand.R",
    "thigh.L",
    "shin.L",
    "foot.L",
    "thigh.R",
    "shin.R",
    "foot.R",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default=DEFAULT_BLEND)
    parser.add_argument("--runtime-output", default=DEFAULT_RUNTIME_OUTPUT)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument(
        "--allow-active-output",
        action="store_true",
        help="Allow this deprecated placeholder generator to write over active Benjamin assets.",
    )
    return parser.parse_args(sys_argv_after_separator())


def sys_argv_after_separator() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def assert_generation_allowed(args: argparse.Namespace) -> None:
    if os.environ.get(ALLOW_ENV_VAR) != "1":
        raise RuntimeError(
            "Refusing to generate procedural Benjamin placeholder assets. "
            "The active character must come from the Character Creator/Mesh2Motion pipeline. "
            f"Set {ALLOW_ENV_VAR}=1 only for archived prototype output."
        )

    blend_path = os.path.abspath(args.blend)
    runtime_output = os.path.abspath(args.runtime_output)
    active_paths = {os.path.abspath(ACTIVE_BLEND), os.path.abspath(ACTIVE_RUNTIME_OUTPUT)}
    if not args.allow_active_output and {blend_path, runtime_output} & active_paths:
        raise RuntimeError(
            "Refusing to overwrite active Benjamin source/runtime with the deprecated "
            "procedural placeholder. Write to archive output paths instead."
        )


def clear_scene() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for datablock_collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.images,
    ):
        for datablock in list(datablock_collection):
            if datablock.users == 0:
                datablock_collection.remove(datablock)


def make_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    return collection


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.75):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def link_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    for existing in list(obj.users_collection):
        if existing != collection:
            existing.objects.unlink(obj)


def create_uv_sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    segments: int = 24,
    rings: int = 12,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_to_collection(obj, collection)
    return obj


def create_cube(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_to_collection(obj, collection)
    return obj


def create_cylinder_between(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    vertices: int = 18,
) -> bpy.types.Object:
    start_v = Vector(start)
    end_v = Vector(end)
    midpoint = (start_v + end_v) * 0.5
    direction = end_v - start_v
    length = direction.length
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=length,
        location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    link_to_collection(obj, collection)
    return obj


def create_armature(collection: bpy.types.Collection) -> bpy.types.Object:
    bpy.ops.object.armature_add(location=(0, 0, 0))
    armature = bpy.context.object
    armature.name = ARMATURE_NAME
    armature.data.name = f"{ARMATURE_NAME}_Data"
    link_to_collection(armature, collection)

    bpy.ops.object.mode_set(mode="EDIT")
    armature.data.edit_bones.remove(armature.data.edit_bones[0])

    def bone(
        name: str,
        head: tuple[float, float, float],
        tail: tuple[float, float, float],
        parent: str | None = None,
    ) -> None:
        edit_bone = armature.data.edit_bones.new(name)
        edit_bone.head = head
        edit_bone.tail = tail
        edit_bone.use_deform = True
        if parent:
            edit_bone.parent = armature.data.edit_bones[parent]

    bone("root", (0, 0, 0.02), (0, 0, 0.18))
    bone("hips", (0, 0, 0.84), (0, 0, 1.02), "root")
    bone("spine", (0, 0, 1.02), (0, 0, 1.28), "hips")
    bone("chest", (0, 0, 1.28), (0, 0, 1.48), "spine")
    bone("neck", (0, 0, 1.48), (0, 0, 1.58), "chest")
    bone("head", (0, 0, 1.58), (0, 0, 1.84), "neck")

    bone("upper_arm.L", (-0.30, 0, 1.42), (-0.60, 0, 1.22), "chest")
    bone("forearm.L", (-0.60, 0, 1.22), (-0.82, 0, 1.02), "upper_arm.L")
    bone("hand.L", (-0.82, 0, 1.02), (-0.94, -0.02, 0.96), "forearm.L")
    bone("upper_arm.R", (0.30, 0, 1.42), (0.60, 0, 1.22), "chest")
    bone("forearm.R", (0.60, 0, 1.22), (0.82, 0, 1.02), "upper_arm.R")
    bone("hand.R", (0.82, 0, 1.02), (0.94, -0.02, 0.96), "forearm.R")

    bone("thigh.L", (-0.16, 0, 0.84), (-0.18, 0, 0.46), "hips")
    bone("shin.L", (-0.18, 0, 0.46), (-0.18, 0, 0.12), "thigh.L")
    bone("foot.L", (-0.18, 0, 0.12), (-0.18, -0.22, 0.06), "shin.L")
    bone("thigh.R", (0.16, 0, 0.84), (0.18, 0, 0.46), "hips")
    bone("shin.R", (0.18, 0, 0.46), (0.18, 0, 0.12), "thigh.R")
    bone("foot.R", (0.18, 0, 0.12), (0.18, -0.22, 0.06), "shin.R")

    bpy.ops.object.mode_set(mode="OBJECT")
    armature.show_in_front = True
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    return armature


def bind_object_to_bone(obj: bpy.types.Object, armature: bpy.types.Object, bone_name: str) -> None:
    group = obj.vertex_groups.new(name=bone_name)
    group.add([vertex.index for vertex in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("Benjamin_Rig_Deform", "ARMATURE")
    modifier.object = armature
    obj.parent = armature
    obj["bt_deform_bone"] = bone_name


def build_character_meshes(collection: bpy.types.Collection, armature: bpy.types.Object) -> None:
    mats = {
        "skin": material("BT_Benjamin_Skin", (0.72, 0.54, 0.43, 1.0)),
        "skin_shadow": material("BT_Benjamin_Skin_Shadow", (0.58, 0.40, 0.32, 1.0)),
        "suit": material("BT_Benjamin_Inky_Suit", (0.035, 0.04, 0.045, 1.0)),
        "shirt": material("BT_Benjamin_Worn_Shirt", (0.80, 0.76, 0.66, 1.0)),
        "tie": material("BT_Benjamin_Quiet_Blue_Tie", (0.08, 0.16, 0.26, 1.0)),
        "shoes": material("BT_Benjamin_Shoes", (0.045, 0.035, 0.025, 1.0)),
        "hair": material("BT_Benjamin_Dark_Hair", (0.025, 0.018, 0.012, 1.0)),
        "eye": material("BT_Benjamin_Eyes", (0.82, 0.88, 0.94, 1.0)),
        "pupil": material("BT_Benjamin_Pupils", (0.015, 0.015, 0.018, 1.0)),
    }

    specs: list[tuple[bpy.types.Object, str]] = []

    specs.append((create_uv_sphere("Benjamin_Hips", (0, 0, 0.88), (0.25, 0.17, 0.17), mats["suit"], collection), "hips"))
    specs.append((create_uv_sphere("Benjamin_Torso", (0, -0.01, 1.18), (0.31, 0.18, 0.34), mats["suit"], collection), "spine"))
    specs.append((create_uv_sphere("Benjamin_Chest", (0, -0.015, 1.38), (0.34, 0.18, 0.25), mats["suit"], collection), "chest"))
    specs.append((create_cube("Benjamin_Shirt_Front", (0, -0.18, 1.29), (0.115, 0.018, 0.27), mats["shirt"], collection), "chest"))
    specs.append((create_cube("Benjamin_Tie", (0, -0.205, 1.23), (0.036, 0.016, 0.25), mats["tie"], collection), "chest"))

    specs.append((create_uv_sphere("Benjamin_Neck", (0, -0.005, 1.52), (0.09, 0.08, 0.10), mats["skin"], collection), "neck"))
    specs.append((create_uv_sphere("Benjamin_Head", (0, -0.015, 1.70), (0.17, 0.135, 0.205), mats["skin"], collection), "head"))
    specs.append((create_uv_sphere("Benjamin_Nose", (0, -0.145, 1.70), (0.035, 0.030, 0.050), mats["skin_shadow"], collection, 12, 8), "head"))
    specs.append((create_uv_sphere("Benjamin_Hair_Cap", (0, 0.005, 1.84), (0.18, 0.14, 0.08), mats["hair"], collection), "head"))
    specs.append((create_uv_sphere("Benjamin_Left_Eye", (-0.055, -0.137, 1.735), (0.023, 0.010, 0.018), mats["eye"], collection, 12, 8), "head"))
    specs.append((create_uv_sphere("Benjamin_Right_Eye", (0.055, -0.137, 1.735), (0.023, 0.010, 0.018), mats["eye"], collection, 12, 8), "head"))
    specs.append((create_uv_sphere("Benjamin_Left_Pupil", (-0.055, -0.145, 1.735), (0.010, 0.004, 0.010), mats["pupil"], collection, 8, 6), "head"))
    specs.append((create_uv_sphere("Benjamin_Right_Pupil", (0.055, -0.145, 1.735), (0.010, 0.004, 0.010), mats["pupil"], collection, 8, 6), "head"))

    for side, sign in (("L", -1.0), ("R", 1.0)):
        specs.append((
            create_cylinder_between(
                f"Benjamin_Upper_Arm_{side}",
                (0.33 * sign, 0, 1.39),
                (0.60 * sign, 0, 1.21),
                0.060,
                mats["suit"],
                collection,
            ),
            f"upper_arm.{side}",
        ))
        specs.append((
            create_cylinder_between(
                f"Benjamin_Forearm_{side}",
                (0.60 * sign, 0, 1.21),
                (0.81 * sign, 0, 1.02),
                0.050,
                mats["suit"],
                collection,
            ),
            f"forearm.{side}",
        ))
        specs.append((create_uv_sphere(f"Benjamin_Hand_{side}", (0.88 * sign, -0.02, 0.97), (0.055, 0.040, 0.065), mats["skin"], collection, 12, 8), f"hand.{side}"))
        specs.append((
            create_cylinder_between(
                f"Benjamin_Thigh_{side}",
                (0.15 * sign, 0, 0.82),
                (0.18 * sign, 0, 0.46),
                0.075,
                mats["suit"],
                collection,
            ),
            f"thigh.{side}",
        ))
        specs.append((
            create_cylinder_between(
                f"Benjamin_Shin_{side}",
                (0.18 * sign, 0, 0.46),
                (0.18 * sign, 0, 0.14),
                0.065,
                mats["suit"],
                collection,
            ),
            f"shin.{side}",
        ))
        specs.append((create_uv_sphere(f"Benjamin_Shoe_{side}", (0.18 * sign, -0.08, 0.075), (0.085, 0.155, 0.055), mats["shoes"], collection, 14, 8), f"foot.{side}"))

    for obj, bone_name in specs:
        bind_object_to_bone(obj, armature, bone_name)


def clear_pose(armature: bpy.types.Object) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0, 0, 0)
        pose_bone.location = (0, 0, 0)
        pose_bone.scale = (1, 1, 1)


def key_pose(
    armature: bpy.types.Object,
    frame: int,
    rotations: dict[str, tuple[float, float, float]] | None = None,
    locations: dict[str, tuple[float, float, float]] | None = None,
) -> None:
    clear_pose(armature)
    rotations = rotations or {}
    locations = locations or {}
    for bone_name, value in rotations.items():
        armature.pose.bones[bone_name].rotation_euler = tuple(math.radians(v) for v in value)
    for bone_name, value in locations.items():
        armature.pose.bones[bone_name].location = value
    bpy.context.scene.frame_set(frame)
    for bone_name in MAJOR_BONES:
        pose_bone = armature.pose.bones[bone_name]
        pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        pose_bone.keyframe_insert(data_path="location", frame=frame)


def make_action(
    armature: bpy.types.Object,
    name: str,
    frames: list[tuple[int, dict[str, tuple[float, float, float]], dict[str, tuple[float, float, float]]]],
) -> bpy.types.Action:
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    armature.animation_data_create()
    armature.animation_data.action = action
    for frame, rotations, locations in frames:
        key_pose(armature, frame, rotations, locations)
    return action


def add_nla_track(armature: bpy.types.Object, action: bpy.types.Action) -> None:
    animation_data = armature.animation_data_create()
    track = animation_data.nla_tracks.new()
    track.name = action.name
    strip = track.strips.new(action.name, 1, action)
    strip.name = action.name


def build_actions(armature: bpy.types.Object) -> None:
    action_specs = {
        "idle": [
            (1, {"chest": (1, 0, 0), "head": (-1, 0, 0)}, {"hips": (0, 0, 0.00)}),
            (30, {"chest": (-1, 0, 0), "head": (1, 0, 0)}, {"hips": (0, 0, 0.015)}),
            (60, {"chest": (1, 0, 0), "head": (-1, 0, 0)}, {"hips": (0, 0, 0.00)}),
        ],
        "walk": [
            (1, {"upper_arm.L": (18, 0, 0), "upper_arm.R": (-18, 0, 0), "thigh.L": (-22, 0, 0), "thigh.R": (22, 0, 0), "shin.L": (12, 0, 0), "shin.R": (0, 0, 0)}, {"hips": (0, 0, 0.00)}),
            (16, {"upper_arm.L": (-18, 0, 0), "upper_arm.R": (18, 0, 0), "thigh.L": (22, 0, 0), "thigh.R": (-22, 0, 0), "shin.L": (0, 0, 0), "shin.R": (12, 0, 0)}, {"hips": (0, 0, 0.025)}),
            (32, {"upper_arm.L": (18, 0, 0), "upper_arm.R": (-18, 0, 0), "thigh.L": (-22, 0, 0), "thigh.R": (22, 0, 0), "shin.L": (12, 0, 0), "shin.R": (0, 0, 0)}, {"hips": (0, 0, 0.00)}),
        ],
        "walk_backward": [
            (1, {"upper_arm.L": (-14, 0, 0), "upper_arm.R": (14, 0, 0), "thigh.L": (18, 0, 0), "thigh.R": (-18, 0, 0)}, {"hips": (0, 0, 0.00)}),
            (16, {"upper_arm.L": (14, 0, 0), "upper_arm.R": (-14, 0, 0), "thigh.L": (-18, 0, 0), "thigh.R": (18, 0, 0)}, {"hips": (0, 0, 0.018)}),
            (32, {"upper_arm.L": (-14, 0, 0), "upper_arm.R": (14, 0, 0), "thigh.L": (18, 0, 0), "thigh.R": (-18, 0, 0)}, {"hips": (0, 0, 0.00)}),
        ],
        "walk_strafe_left": [
            (1, {"chest": (0, 0, -5), "thigh.L": (0, 0, 12), "thigh.R": (0, 0, -10)}, {"hips": (0, 0, 0.00)}),
            (14, {"chest": (0, 0, 5), "thigh.L": (0, 0, -10), "thigh.R": (0, 0, 12)}, {"hips": (0, 0, 0.018)}),
            (28, {"chest": (0, 0, -5), "thigh.L": (0, 0, 12), "thigh.R": (0, 0, -10)}, {"hips": (0, 0, 0.00)}),
        ],
        "walk_strafe_right": [
            (1, {"chest": (0, 0, 5), "thigh.L": (0, 0, -10), "thigh.R": (0, 0, 12)}, {"hips": (0, 0, 0.00)}),
            (14, {"chest": (0, 0, -5), "thigh.L": (0, 0, 12), "thigh.R": (0, 0, -10)}, {"hips": (0, 0, 0.018)}),
            (28, {"chest": (0, 0, 5), "thigh.L": (0, 0, -10), "thigh.R": (0, 0, 12)}, {"hips": (0, 0, 0.00)}),
        ],
        "sprint": [
            (1, {"chest": (8, 0, 0), "upper_arm.L": (35, 0, 0), "upper_arm.R": (-35, 0, 0), "thigh.L": (-34, 0, 0), "thigh.R": (34, 0, 0), "shin.L": (22, 0, 0)}, {"hips": (0, 0, 0.02)}),
            (10, {"chest": (8, 0, 0), "upper_arm.L": (-35, 0, 0), "upper_arm.R": (35, 0, 0), "thigh.L": (34, 0, 0), "thigh.R": (-34, 0, 0), "shin.R": (22, 0, 0)}, {"hips": (0, 0, 0.055)}),
            (20, {"chest": (8, 0, 0), "upper_arm.L": (35, 0, 0), "upper_arm.R": (-35, 0, 0), "thigh.L": (-34, 0, 0), "thigh.R": (34, 0, 0), "shin.L": (22, 0, 0)}, {"hips": (0, 0, 0.02)}),
        ],
        "jump": [
            (1, {"chest": (10, 0, 0), "thigh.L": (18, 0, 0), "thigh.R": (18, 0, 0), "shin.L": (-18, 0, 0), "shin.R": (-18, 0, 0), "upper_arm.L": (25, 0, 0), "upper_arm.R": (25, 0, 0)}, {"hips": (0, 0, -0.05)}),
            (10, {"chest": (-8, 0, 0), "thigh.L": (-10, 0, 0), "thigh.R": (-10, 0, 0), "upper_arm.L": (-35, 0, 0), "upper_arm.R": (-35, 0, 0)}, {"hips": (0, 0, 0.12)}),
            (22, {"chest": (-2, 0, 0), "upper_arm.L": (-18, 0, 0), "upper_arm.R": (-18, 0, 0)}, {"hips": (0, 0, 0.08)}),
        ],
        "fall": [
            (1, {"chest": (-4, 0, 0), "upper_arm.L": (-22, 0, -12), "upper_arm.R": (-22, 0, 12), "thigh.L": (8, 0, 0), "thigh.R": (-8, 0, 0)}, {"hips": (0, 0, 0.05)}),
            (18, {"chest": (4, 0, 0), "upper_arm.L": (-34, 0, -18), "upper_arm.R": (-34, 0, 18), "thigh.L": (-8, 0, 0), "thigh.R": (8, 0, 0)}, {"hips": (0, 0, 0.02)}),
        ],
        "land": [
            (1, {"chest": (15, 0, 0), "thigh.L": (28, 0, 0), "thigh.R": (28, 0, 0), "shin.L": (-24, 0, 0), "shin.R": (-24, 0, 0)}, {"hips": (0, 0, -0.10)}),
            (12, {"chest": (6, 0, 0), "thigh.L": (12, 0, 0), "thigh.R": (12, 0, 0)}, {"hips": (0, 0, -0.03)}),
            (28, {}, {"hips": (0, 0, 0.00)}),
        ],
    }

    for name, frames in action_specs.items():
        action = make_action(armature, name, frames)
        add_nla_track(armature, action)
    armature.animation_data.action = bpy.data.actions["idle"]
    clear_pose(armature)


def add_camera_and_light(collection: bpy.types.Collection) -> None:
    bpy.ops.object.light_add(type="AREA", location=(0, -3, 3.4))
    light = bpy.context.object
    light.name = "Benjamin_Key_Light"
    light.data.energy = 420
    light.data.size = 4
    link_to_collection(light, collection)

    bpy.ops.object.camera_add(location=(0, -4.2, 1.45), rotation=(math.radians(74), 0, 0))
    camera = bpy.context.object
    camera.name = "Benjamin_Preview_Camera"
    camera.data.lens = 48
    bpy.context.scene.camera = camera
    link_to_collection(camera, collection)


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 60
    scene["bt_character_generator"] = "tools/generate_benjamin_character.py"
    scene["bt_character_style"] = "stylized_rigid_game_rig"
    scene["bt_runtime_output"] = DEFAULT_RUNTIME_OUTPUT


def select_export_objects(collection: bpy.types.Collection) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in collection.objects:
        if obj.type in {"ARMATURE", "MESH"}:
            obj.select_set(True)
    armature = bpy.data.objects[ARMATURE_NAME]
    bpy.context.view_layer.objects.active = armature


def export_runtime(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_texcoords=True,
        export_normals=True,
        export_skins=True,
        export_morph=False,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_nla_strips=True,
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )


def write_source_note() -> None:
    os.makedirs(os.path.dirname(SOURCE_NOTE_PATH), exist_ok=True)
    with open(SOURCE_NOTE_PATH, "w", encoding="utf-8") as handle:
        handle.write(
            "# Procedural Benjamin Placeholder\n\n"
            "Generated by deprecated `tools/generate_benjamin_character.py`.\n\n"
            "This output is archived reference material only. Do not install it as the active "
            "Benjamin player model; the active source/runtime must come from the Character "
            "Creator/Mesh2Motion pipeline.\n"
        )


def remove_blender_backup(blend_path: str) -> None:
    backup_path = f"{blend_path}1"
    if os.path.exists(backup_path):
        os.remove(backup_path)


def validate_actions() -> None:
    missing = [name for name in REQUIRED_ACTIONS if name not in bpy.data.actions]
    if missing:
        raise RuntimeError(f"Missing generated actions: {', '.join(missing)}")


def main() -> None:
    args = parse_args()
    assert_generation_allowed(args)

    blend_path = os.path.abspath(args.blend)
    runtime_output = os.path.abspath(args.runtime_output)

    clear_scene()
    collection = make_collection()
    materials_note = bpy.data.texts.new("BT_Generator_Notes")
    materials_note.write("Generated by tools/generate_benjamin_character.py\n")

    armature = create_armature(collection)
    build_character_meshes(collection, armature)
    build_actions(armature)
    validate_actions()
    add_camera_and_light(collection)
    configure_scene()
    select_export_objects(collection)
    write_source_note()

    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    if not args.no_save:
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        remove_blender_backup(blend_path)
    if not args.no_export:
        export_runtime(runtime_output)

    print("[Benjamin Generator] Blend:", blend_path)
    print("[Benjamin Generator] Runtime:", runtime_output)
    print("[Benjamin Generator] Actions:", ", ".join(REQUIRED_ACTIONS))
    print("[Benjamin Generator] Rig:", ARMATURE_NAME, len(armature.data.bones), "bones")


if __name__ == "__main__":
    main()
