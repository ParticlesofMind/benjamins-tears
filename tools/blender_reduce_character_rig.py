"""
Reduce Benjamin's exported Rigify-heavy GLB to a smaller Godot game rig.

This keeps the visible character mesh and locomotion animations, remaps helper
and face weights onto nearby gameplay bones, marks only those bones as deform
bones, and re-exports with Blender's glTF deformation-bone filter.

Usage:
  blender --background --python tools/blender_reduce_character_rig.py -- \
    --input archive/character_export_attempts/real_benjamin_candidates/benjamin_candidate_animated.glb \
    --output archive/character_export_attempts/real_benjamin_candidates/benjamin_candidate_game_rig.glb
"""

import argparse
import os
import shutil
import tempfile

import bpy


KEEP_BONES = {
    "root",
    "DEF-spine",
    "DEF-spine.001",
    "DEF-spine.002",
    "DEF-spine.003",
    "DEF-spine.004",
    "DEF-spine.005",
    "DEF-spine.006",
    "DEF-shoulder.L",
    "DEF-upper_arm.L",
    "DEF-forearm.L",
    "DEF-hand.L",
    "DEF-shoulder.R",
    "DEF-upper_arm.R",
    "DEF-forearm.R",
    "DEF-hand.R",
    "DEF-thigh.L",
    "DEF-shin.L",
    "DEF-foot.L",
    "DEF-toe.L",
    "DEF-thigh.R",
    "DEF-shin.R",
    "DEF-foot.R",
    "DEF-toe.R",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Animated source GLB")
    parser.add_argument("--output", required=True, help="Reduced output GLB")
    return parser.parse_args(sys_argv_after_separator())


def sys_argv_after_separator() -> list[str]:
    import sys

    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def side_suffix(name: str) -> str:
    if name.endswith(".L") or ".L." in name:
        return ".L"
    if name.endswith(".R") or ".R." in name:
        return ".R"
    return ""


def fallback_target(keep: set[str]) -> str:
    for name in ("root", "DEF-spine", "DEF-spine.001"):
        if name in keep:
            return name
    if not keep:
        raise RuntimeError("No keep bones found on armature")
    return sorted(keep)[0]


def weight_target_for(name: str, keep: set[str], armature: bpy.types.Object) -> str:
    if name in keep:
        return name

    suffix = side_suffix(name)
    lowered = name.lower()

    body_part_targets = [
        ("toe", "DEF-toe"),
        ("foot", "DEF-foot"),
        ("shin", "DEF-shin"),
        ("thigh", "DEF-thigh"),
        ("pelvis", "DEF-thigh"),
        ("knee", "DEF-thigh"),
        ("hand", "DEF-hand"),
        ("palm", "DEF-hand"),
        ("finger", "DEF-hand"),
        ("thumb", "DEF-hand"),
        ("forearm", "DEF-forearm"),
        ("elbow", "DEF-forearm"),
        ("upper_arm", "DEF-upper_arm"),
        ("arm", "DEF-upper_arm"),
        ("shoulder", "DEF-upper_arm"),
    ]
    for needle, target_prefix in body_part_targets:
        target = target_prefix + suffix
        if needle in lowered and target in keep:
            return target

    if any(
        token in lowered
        for token in (
            "eye",
            "lid",
            "jaw",
            "chin",
            "nose",
            "teeth",
            "tongue",
            "ear",
            "brow",
            "head",
            "neck",
        )
    ):
        return "DEF-spine.006" if "DEF-spine.006" in keep else "DEF-spine.004"

    if "breast" in lowered or "spine.006" in lowered:
        return "DEF-spine.006"
    if "spine.005" in lowered:
        return "DEF-spine.005" if "DEF-spine.005" in keep else "DEF-spine.004"
    if "spine.004" in lowered:
        return "DEF-spine.004"
    if "spine.003" in lowered:
        return "DEF-spine.003"
    if "spine.002" in lowered:
        return "DEF-spine.002"
    if "spine.001" in lowered:
        return "DEF-spine.001"
    if "spine" in lowered:
        return "DEF-spine"

    bone = armature.data.bones.get(name)
    while bone and bone.parent:
        bone = bone.parent
        if bone.name in keep:
            return bone.name

    return fallback_target(keep)


def find_character_objects() -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and any(mod.type == "ARMATURE" for mod in obj.modifiers)
    ]
    if not armatures:
        raise RuntimeError("No armature found in input GLB")
    if not meshes:
        raise RuntimeError("No skinned mesh found in input GLB")
    return armatures[0], meshes


def reduce_weights(mesh: bpy.types.Object, armature: bpy.types.Object, keep: set[str]) -> None:
    for name in keep:
        if name not in mesh.vertex_groups:
            mesh.vertex_groups.new(name=name)

    group_name_by_index = {group.index: group.name for group in mesh.vertex_groups}
    reduced_weights: list[tuple[int, dict[str, float]]] = []

    for vertex in mesh.data.vertices:
        accum: dict[str, float] = {}
        for assignment in vertex.groups:
            source_name = group_name_by_index.get(assignment.group)
            if not source_name or assignment.weight <= 0.0:
                continue
            target = weight_target_for(source_name, keep, armature)
            accum[target] = accum.get(target, 0.0) + assignment.weight

        total = sum(accum.values())
        if total > 0.0:
            reduced_weights.append(
                (vertex.index, {name: min(1.0, weight / total) for name, weight in accum.items()})
            )

    vertex_indices = range(len(mesh.data.vertices))
    for group in mesh.vertex_groups:
        group.remove(vertex_indices)

    for vertex_index, weights in reduced_weights:
        for group_name, weight in weights.items():
            mesh.vertex_groups[group_name].add([vertex_index], weight, "REPLACE")


def reduce_file(input_path: str, output_path: str) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=input_path)

    armature, meshes = find_character_objects()
    keep = {name for name in KEEP_BONES if name in armature.data.bones}

    for mesh in meshes:
        reduce_weights(mesh, armature, keep)
    for bone in armature.data.bones:
        bone.use_deform = bone.name in keep

    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    armature.select_set(True)
    for mesh in meshes:
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = armature

    final_output = output_path
    same_file = os.path.abspath(input_path) == os.path.abspath(output_path)
    if same_file:
        fd, temp_output = tempfile.mkstemp(suffix=".glb")
        os.close(fd)
        final_output = temp_output

    bpy.ops.export_scene.gltf(
        filepath=final_output,
        export_format="GLB",
        use_selection=True,
        export_skins=True,
        export_animations=True,
        export_def_bones=True,
        export_morph=False,
    )

    if same_file:
        shutil.move(final_output, output_path)

    print(
        f"Reduced rig: {len(armature.data.bones)} source bones, "
        f"{len(keep)} exported deform bones, {len(meshes)} skinned meshes"
    )
    print(f"Output: {output_path}")


def main() -> None:
    args = parse_args()
    reduce_file(args.input, args.output)


if __name__ == "__main__":
    main()
