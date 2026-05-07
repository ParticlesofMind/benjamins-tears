"""Helper script: print shape keys and bones in a character file."""
import bpy
import sys

bpy.ops.wm.read_factory_settings(use_empty=True)

filepath = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None
if not filepath:
    print("Usage: blender --background --python tools/list_shape_keys.py -- <file>")
    sys.exit(1)

ext = filepath.rsplit('.', 1)[-1].lower()
if ext in ('glb', 'gltf'):
    bpy.ops.import_scene.gltf(filepath=filepath)
elif ext == 'blend':
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
    for obj in data_to.objects:
        if obj is not None:
            bpy.context.scene.collection.objects.link(obj)
elif ext == 'fbx':
    bpy.ops.import_scene.fbx(filepath=filepath)

for obj in bpy.data.objects:
    print(f"\nObject: {obj.name!r}  type={obj.type}")
    if obj.type == 'MESH' and obj.data.shape_keys:
        keys = [k.name for k in obj.data.shape_keys.key_blocks]
        print(f"  Shape keys ({len(keys)}): {keys}")
    elif obj.type == 'ARMATURE':
        bones = [b.name for b in obj.data.bones]
        print(f"  Bones ({len(bones)}): {bones[:15]}{'...' if len(bones) > 15 else ''}")
