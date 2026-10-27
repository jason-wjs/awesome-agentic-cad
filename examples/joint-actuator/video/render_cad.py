"""Render exported STEP meshes with Blender Cycles.

Run through Blender: blender --background --factory-startup --python render_cad.py
-- --assets assets --output out/cad --mode stills
"""
import argparse
import gzip
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--assets', type=Path, default=Path('assets'))
parser.add_argument('--output', type=Path, default=Path('out/cad'))
parser.add_argument('--mode', choices=['hero', 'exploded', 'stills', 'animation', 'all'], default='stills')
parser.add_argument('--samples', type=int, default=64)
parser.add_argument('--width', type=int, default=1280)
parser.add_argument('--height', type=int, default=720)
parser.add_argument('--fps', type=int, default=12)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
args.assets = args.assets.resolve()
args.output = args.output.resolve()
args.output.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
preferences = bpy.context.preferences.addons['cycles'].preferences
for device_type in ['METAL', 'OPTIX', 'CUDA', 'HIP', 'ONEAPI']:
    try:
        preferences.compute_device_type = device_type
        preferences.get_devices()
        accelerators = [device for device in preferences.devices if device.type == device_type]
        if accelerators:
            for device in preferences.devices:
                device.use = device in accelerators
            scene.cycles.device = 'GPU'
            break
    except TypeError:
        continue
else:
    scene.cycles.device = 'CPU'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.015
scene.cycles.max_bounces = 8
scene.cycles.diffuse_bounces = 4
scene.cycles.glossy_bounces = 6
scene.cycles.transmission_bounces = 6
scene.cycles.seed = 7
scene.cycles.use_animated_seed = False
scene.render.use_persistent_data = True
scene.render.resolution_x = args.width
scene.render.resolution_y = args.height
scene.render.resolution_percentage = 100
scene.render.fps = args.fps
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.28, 0.32, 0.38, 1)
background.inputs['Strength'].default_value = 0.35


def material(name, color, metalness, roughness, coat=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    surface = mat.node_tree.nodes.get('Principled BSDF')
    surface.inputs['Base Color'].default_value = (*color, 1)
    surface.inputs['Metallic'].default_value = metalness
    surface.inputs['Roughness'].default_value = roughness
    surface.inputs['Coat Weight'].default_value = coat
    surface.inputs['Coat Roughness'].default_value = 0.18
    return mat


# Linear reflectance values; fallback manifest colours are converted from sRGB.
materials = {
    'aluminium': material('Satin machined aluminium', (0.70, 0.72, 0.75), 1, 0.30),
    'steel': material('Bearing steel', (0.57, 0.61, 0.66), 1, 0.18),
    'polished': material('Polished steel', (0.60, 0.64, 0.69), 1, 0.12),
    'dark_steel': material('Blackened steel', (0.035, 0.04, 0.05), 0.9, 0.27),
    'magnet': material('Magnet segments', (0.04, 0.05, 0.063), 0.72, 0.31),
    'copper': material('Enamelled copper', (0.78, 0.32, 0.12), 1, 0.23, 0.22),
    'brass': material('Brass', (0.65, 0.47, 0.15), 1, 0.23),
    'pcb': material('Green solder mask', (0.012, 0.055, 0.031), 0.05, 0.35, 0.2),
    'polymer': material('Polymer', (0.018, 0.022, 0.028), 0, 0.4),
}


def load_model(bore, include_cutaway=True):
    data = json.loads((args.assets/f'joint-{bore}.json').read_text())
    buffer = gzip.decompress((args.assets/f'joint-{bore}.bin.gz').read_bytes())
    parts = []

    def mesh_object(entry, spec, suffix=''):
        count, index_count = spec['vertex_count'], spec['index_count']
        positions = np.frombuffer(buffer, dtype='<f4', count=count*3,
                                  offset=spec['position_offset'])*0.001
        indices = np.frombuffer(buffer, dtype='<u4', count=index_count,
                                offset=spec['index_offset'])
        mesh = bpy.data.meshes.new(entry['name']+suffix)
        mesh.vertices.add(count)
        mesh.vertices.foreach_set('co', positions)
        mesh.loops.add(index_count)
        mesh.loops.foreach_set('vertex_index', indices)
        mesh.polygons.add(index_count//3)
        mesh.polygons.foreach_set('loop_start', np.arange(0, index_count, 3, dtype=np.int32))
        mesh.polygons.foreach_set('loop_total', np.full(index_count//3, 3, dtype=np.int32))
        mesh.polygons.foreach_set('use_smooth', np.ones(index_count//3, dtype=bool))
        mesh.update()
        normals = np.frombuffer(buffer, dtype='<f4', count=count*3,
                                offset=spec['normal_offset']).reshape(-1, 3)
        mesh.normals_split_custom_set_from_vertices(normals.tolist())
        obj = bpy.data.objects.new(entry['name']+suffix, mesh)
        bpy.context.collection.objects.link(obj)
        name = entry['material']['name']
        if name not in materials:
            linear = tuple(c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
                           for c in entry['color_rgba'][:3])
            materials[name] = material(name, linear, entry['material']['metalness'],
                                       entry['material']['roughness'])
        obj.data.materials.append(materials[name])
        return obj

    for entry in data['parts']:
        full = mesh_object(entry, entry['mesh'])
        cut = mesh_object(entry, entry['cut_mesh'], '-section') if include_cutaway and entry.get('cut_mesh') else None
        if cut:
            cut.hide_render = True
        parts.append((entry, full, cut))
    return parts


def clear_model(parts):
    for _, full, cut in parts:
        for obj in (full, cut):
            if obj:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.meshes.remove(mesh)


def area(name, position, width, height, watts, color=(1, 1, 1)):
    lamp = bpy.data.lights.new(name, 'AREA')
    lamp.energy, lamp.color, lamp.shape = watts, color, 'RECTANGLE'
    lamp.size, lamp.size_y = width, height
    obj = bpy.data.objects.new(name, lamp)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (-obj.location).to_track_quat('-Z', 'Y').to_euler()


area('Warm key', (-0.09, -0.15, 0.22), 0.20, 0.12, 0.9, (1, 0.93, 0.83))
area('Camera fill', (0.05, -0.28, 0.10), 0.28, 0.20, 0.7)
area('Cool strip', (0.18, 0.07, 0.14), 0.06, 0.22, 1.1, (0.84, 0.92, 1))
area('Rear edge', (-0.17, 0.10, 0.06), 0.12, 0.18, 0.8)
area('Flange reflection', (0.25, -0.08, 0.03), 0.04, 0.18, 0.24)
floor_material = material('Studio floor', (0.78, 0.79, 0.80), 0, 0.6)
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, -0.05535))
floor = bpy.context.object
floor.name = 'Shadow catcher'
floor.data.materials.append(floor_material)
floor.is_shadow_catcher = True
scene.render.film_transparent = True
scene.use_nodes = True
nodes = scene.node_tree.nodes
nodes.clear()
layers = nodes.new('CompositorNodeRLayers')
over = nodes.new('CompositorNodeAlphaOver')
over.inputs[1].default_value = (8, 8, 8, 1)
composite = nodes.new('CompositorNodeComposite')
scene.node_tree.links.new(layers.outputs['Image'], over.inputs[2])
scene.node_tree.links.new(over.outputs[0], composite.inputs[0])
camera_data = bpy.data.cameras.new('Camera')
camera = bpy.data.objects.new('Camera', camera_data)
bpy.context.collection.objects.link(camera)
camera_data.type = 'ORTHO'
camera_data.clip_start, camera_data.clip_end = 0.001, 10
scene.camera = camera


def smooth(value):
    p = min(1, max(0, value))
    return p*p*(3-2*p)


def pose(parts, section, explosion=0):
    for entry, full, cut in parts:
        full.hide_render = section and (entry.get('cutaway') or entry.get('omitted_from_cutaway'))
        if cut:
            cut.hide_render = not section
        stage = entry.get('explode', {}).get('stage', 1)
        fraction = smooth((explosion-(stage-1)*0.045)/0.75)
        offset = Vector(entry.get('explode', {}).get('offset_mm', [0, 0, 0]))
        # Lift the sectioned cover clear of the transmission stack.
        shifts = {'gear_housing': (-15, 0, 70), 'wave_generator': (16, 0, 0),
                  'wave_bearing': (16, 0, 0), 'circular_spline': (22, 0, 0),
                  'flexspline': (29, 0, 0), 'output_bearing': (35, 0, 0),
                  'output_flange': (26, 0, 0)}
        offset += Vector(shifts.get(entry['group'], (0, 0, 0)))
        offset *= 0.001*fraction
        full.location = offset
        if cut:
            cut.location = offset


def camera_pose(time, explosion):
    azimuth = math.radians(-58-10*smooth(time/8.5))
    elevation = math.radians(27-5*explosion)
    target = Vector((0, 0, 0.006))
    camera.location = target+Vector((0.56*math.cos(azimuth)*math.cos(elevation),
                                    0.56*math.sin(azimuth)*math.cos(elevation),
                                    0.56*math.sin(elevation)))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = (0.157+0.085*explosion)*scene.render.resolution_x/scene.render.resolution_y


def at_time(parts, time):
    explosion = 0
    if 4.2 <= time < 7.7:
        explosion = smooth((time-4.2)/1.5)
    elif 7.7 <= time < 9:
        explosion = 1-smooth((time-7.7)/1.3)
    pose(parts, time < 3 or time >= 4.2, explosion)
    camera_pose(time, explosion)


def render(path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


parts = load_model(20)
if args.mode in ['hero', 'exploded', 'stills', 'all']:
    scene.cycles.samples = max(128, args.samples)
    views = [('cutaway', 0)] if args.mode == 'hero' else [('exploded', 6.5)] if args.mode == 'exploded' else [('cutaway', 0), ('assembly', 3.5), ('exploded', 6.5)]
    for name, time in views:
        at_time(parts, time)
        render(args.output/f'{name}.png')
if args.mode in ['animation', 'all']:
    frames = args.output/'frames'
    frames.mkdir(exist_ok=True)
    scene.cycles.samples = args.samples
    for index in range(9*args.fps):
        at_time(parts, index/args.fps)
        render(frames/f'frame-{index+1:04}.png')
if args.mode in ['stills', 'all']:
    scene.render.resolution_x = args.width//2
    scene.render.resolution_y = round(args.height*548/720)
    scene.cycles.samples = max(128, args.samples)
    camera.location = (0.65, -0.16, 0.115)
    camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = 0.156*scene.render.resolution_x/scene.render.resolution_y
    for bore in (20, 30):
        if bore == 30:
            clear_model(parts)
            parts = load_model(30, include_cutaway=False)
        pose(parts, False)
        render(args.output/f'comparison-{bore}.png')
