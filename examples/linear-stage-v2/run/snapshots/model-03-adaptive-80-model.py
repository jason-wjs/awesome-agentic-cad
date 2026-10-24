"""Parametric screw-driven stage, mm. Original nominal geometry, not catalog parts."""
from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import time

from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

from build123d import (
    Box, Circle, Color, Compound, Cylinder, Helix, Plane, Pos,
    RectangleRounded, RegularPolygon, Rot, chamfer, export_step, extrude, sweep,
)

COLORS = {
    'base': '#40536d', 'support': '#c5cbd2', 'rod': '#d4dce4',
    'screw': '#a4adb8', 'carriage': '#167f91', 'guide': '#3b6472',
    'bushing': '#a5adb7', 'nut': '#c49b46', 'motor': '#252d39',
    'coupling': '#b9c9d8', 'bolt': '#39414c', 'seal': '#30353b',
    'connector': '#1c232b',
}
MATERIALS = {
    'base': (.68, .34), 'support': (.82, .28), 'rod': (.95, .20),
    'screw': (.90, .26), 'carriage': (.68, .30), 'guide': (.65, .35),
    'bushing': (.92, .25), 'nut': (.85, .27), 'motor': (.55, .40),
    'coupling': (.88, .24), 'bolt': (.78, .32), 'seal': (.05, .52),
    'connector': (.02, .55),
}
MOVING = ('platform', 'guide_housing', 'guide_bushing', 'nut_holder', 'drive_nut',
          'platform_bolt', 'nut_bolt', 'nut_flange_bolt')


@dataclass(frozen=True)
class Stage:
    travel: float = 80
    platform_length: float = 52
    end_clearance: float = 6
    support_thickness: float = 12
    screw_lead: float = 4

    @property
    def support_x(self):
        return (self.travel + self.platform_length + 2*self.end_clearance + self.support_thickness)/2

    @property
    def rod_length(self):
        return 2*self.support_x + self.support_thickness

    @property
    def base_length(self):
        return 2*self.support_x + 100


def box(dx, dy, dz, x=0, y=0, z=0, bevel=0):
    shape = Box(dx, dy, dz)
    if bevel:
        shape = chamfer(shape.edges(), bevel)
    return Pos(x, y, z) * shape


def cyl_x(radius, length, x=0, y=0, z=0):
    return Pos(x, y, z) * Rot(0, 90, 0) * Cylinder(radius, length)


def cyl_z(radius, length, x=0, y=0, z=0):
    return Pos(x, y, z) * Cylinder(radius, length)


def plate(dx, dy, dz, radius, x=0, y=0, z=0, bevel=0):
    shape = extrude(RectangleRounded(dx, dy, radius), amount=dz)
    if bevel:
        edges = [e for e in shape.edges() if abs(e.center().Z-dz) < 1e-5]
        shape = chamfer(edges, bevel)
    return Pos(x, y, z) * shape


def motor_plate(length, x):
    return Pos(x, 0, 28) * Rot(0, 90, 0) * extrude(RectangleRounded(42, 42, 3), amount=length)


def socket(radius, depth):
    # radius is circumradius: actual polygon, not the circular recess in v1.
    return extrude(RegularPolygon(radius, 6, rotation=30), amount=depth)


def vertical_bolt(x, y, bottom, shoulder, top, radius=2, head=3.5):
    shape = cyl_z(radius, shoulder-bottom, x, y, (shoulder+bottom)/2)
    shape += cyl_z(head, top-shoulder, x, y, (top+shoulder)/2)
    shape -= Pos(x, y, top-1.6) * socket(head*.57, 2)
    return shape


def bolt_x(x_tip, x_shoulder, x_top, y, z, radius=1.5, head=2.75):
    """Socket-head screw; tip and head may point either way along X."""
    sign = 1 if x_top > x_shoulder else -1
    shape = cyl_x(radius, abs(x_tip-x_shoulder), (x_tip+x_shoulder)/2, y, z)
    shape += cyl_x(head, abs(x_top-x_shoulder), (x_top+x_shoulder)/2, y, z)
    shape -= Pos(x_top-sign*1.6, y, z) * Rot(0, 90*sign, 0) * socket(head*.57, 2)
    return shape


def is_moving(name):
    return name.startswith(MOVING)


def mechanism(name):
    if is_moving(name):
        return 'carriage'
    if name == 'lead_screw' or name.startswith('shaft_collar'):
        return 'screw'
    if name.startswith('coupling'):
        return 'coupling'
    if name == 'motor_shaft':
        return 'motor_shaft'
    return 'fixed'


def explode(name):
    """Editorial exploded layout. Offsets are not a collision-free assembly path."""
    if name.startswith(('platform_bolt', 'nut_bolt')):
        return [0, 0, 76], 1
    if name == 'platform':
        return [0, 0, 55], 2
    if name.startswith('nut_flange_bolt'):
        return [-32, 0, 25], 1
    if name == 'drive_nut':
        return [-21, 0, 25], 3
    if name == 'nut_holder':
        return [0, 0, 25], 3
    if name.startswith(('guide_housing', 'guide_bushing')):
        sign = -1 if 'front' in name else 1
        return [(-42 if 'bushing' in name else 0), sign*19, 25], 3
    if name.startswith(('support_bolt', 'guide_set_screw', 'mount_bolt')):
        return [0, 0, 52], 1
    if name.startswith('motor_bolt'):
        return [-30, 0, 14], 1
    if name.startswith('coupling_clamp_bolt'):
        return [34, 0, 44], 1
    if name.startswith('shaft_collar_set'):
        sign = -1 if 'left' in name else 1
        return [sign*32, 0, 38], 1
    if name.startswith('shaft_collar'):
        sign = -1 if 'left' in name else 1
        return [sign*32, 0, 14], 4
    if name.startswith('screw_bearing'):
        sign = -1 if 'left' in name else 1
        return [sign*(22 if 'outer' in name else 32), 0, 14], 4
    if name.startswith('end_support'):
        sign = -1 if 'left' in name else 1
        return [sign*10, 0, 14], 4
    if name.startswith('guide_rod') or name == 'lead_screw':
        return [0, 0, 14], 4
    if name == 'coupling':
        return [34, 0, 14], 4
    if name == 'motor_mount':
        return [48, 0, 14], 4
    if name.startswith('motor'):
        return [68+(12 if name == 'motor_rearcap' else 0), 0, 14], 5
    return [0, 0, 0], 5


def build(p, position=0):
    s = p.support_x
    parts = {}

    def add(name, shape, color):
        shape.label = name
        shape.color = Color(COLORS[color])
        shape.material_key = color
        parts[name] = shape

    base = plate(p.base_length, 100, 8, 5, x=30, bevel=.6)
    base -= box(43, 44, 3, s+59, 0, 6.5)
    # Shallow machining pockets expose a rim while retaining a full-thickness spine.
    for y in (-43, 43):
        base -= plate(2*s-30, 8, 2.2, 3, y=y, z=6)
    for x in (-s-12, s+68):
        for y in (-41, 41):
            base -= cyl_z(2.75, 10, x, y, 4)
            base -= cyl_z(5, 3, x, y, 6.5)
    for x in (-s, s):
        for y in (-38, 38):
            base -= cyl_z(2.1, 10, x, y, 4)
    for y in (-22, 22):
        base -= cyl_z(2.1, 10, s+34.2, y, 4)
    add('base', base, 'base')

    for side, x in [('left', -s), ('right', s)]:
        support = box(12, 86, 44, x=x, z=30, bevel=.65)
        for y in (-28, 28):
            support -= cyl_x(4.1, 14, x, y, 30)
            support -= cyl_z(1.6, 20, x, y, 44)
            set_screw = cyl_z(1.5, 6, x, y, 37.1)
            set_screw -= Pos(x, y, 38.6) * socket(.9, 2)
            add(f'guide_set_screw_{side}_{"front" if y < 0 else "rear"}', set_screw, 'bolt')
        support -= cyl_x(8.1, 14, x, 0, 28)
        for i, y in enumerate((-38, 38)):
            support -= cyl_z(2.25, 46, x, y, 30)
            support -= cyl_z(4, 6, x, y, 50)
            add(f'support_bolt_{side}_{i}', vertical_bolt(x, y, 4, 47, 51), 'bolt')
        add(f'end_support_{side}', support, 'support')
        outer = cyl_x(8, 12, x, 0, 28) - cyl_x(5.7, 14, x, 0, 28)
        inner = cyl_x(5.6, 12, x, 0, 28) - cyl_x(4.1, 14, x, 0, 28)
        add(f'screw_bearing_outer_{side}', outer, 'bushing')
        add(f'screw_bearing_inner_{side}', inner, 'rod')
        # Seal is a separately visible annulus with radial clearance to both rings.
        for face, off in [('front', -5.8), ('rear', 5.8)]:
            seal = cyl_x(5.68, .35, x+off, 0, 28) - cyl_x(5.62, .6, x+off, 0, 28)
            add(f'screw_bearing_seal_{side}_{face}', seal, 'seal')
    for side, y in [('front', -28), ('rear', 28)]:
        add(f'guide_rod_{side}', cyl_x(4, p.rod_length, 0, y, 30), 'rod')

    # A single-start rounded ridge makes lead and handedness visible. It is not a T8 specification.
    print('Building helical screw...', flush=True)
    thread_length = 2*s-20
    helix = Helix(p.screw_lead, thread_length, 3.35)
    profile = Plane.XZ * Pos(3.35, 0) * Circle(.65)
    ridge = sweep(profile, path=helix, is_frenet=True)
    core = Cylinder(3.2, thread_length+2)
    # sweep starts at local z=0; the core overlaps both terminal turns.
    core = Pos(0, 0, thread_length/2) * core
    threaded = core + ridge
    screw = Pos(-thread_length/2, 0, 28) * Rot(0, 90, 0) * threaded
    screw += cyl_x(4, 24, -s-2, 0, 28)
    screw += cyl_x(4, 30, s+5, 0, 28)
    for x in (-s+7, s-7):
        screw += cyl_x(5, 2, x, 0, 28)
    add('lead_screw', screw, 'screw')

    for side, x in [('left', -s-9), ('right', s+9)]:
        collar = cyl_x(7, 6, x, 0, 28) - cyl_x(4.05, 8, x, 0, 28)
        collar -= cyl_z(1.4, 8, x, 0, 34)
        bolt = cyl_z(1.3, 2.8, x, 0, 33.5)
        bolt -= Pos(x, 0, 33.4) * socket(.8, 2)
        add(f'shaft_collar_{side}', collar, 'bushing')
        add(f'shaft_collar_set_{side}', bolt, 'bolt')

    mount = box(6, 52, 45, s+35, 0, 30.5, bevel=.5)
    mount -= cyl_x(11.2, 8, s+35, 0, 28)
    motor = motor_plate(30, s+43)
    frontcap = motor_plate(3, s+40)
    rearcap = motor_plate(7, s+73)
    face = motor_plate(2, s+38)
    face += cyl_x(11, 2, s+37, 0, 28)
    face -= cyl_x(2.6, 6, s+38, 0, 28)
    for i, y in enumerate((-15.5, 15.5)):
        for j, z in enumerate((12.5, 43.5)):
            mount -= cyl_x(1.7, 8, s+35, y, z)
            mount -= cyl_x(3.2, 2.2, s+33, y, z)
            motor -= cyl_x(1.7, 7, s+42.5, y, z)
            frontcap -= cyl_x(1.7, 5, s+41.5, y, z)
            face -= cyl_x(1.7, 6, s+39, y, z)
            add(f'motor_bolt_{i}_{j}', bolt_x(s+44, s+34, s+32, y, z), 'bolt')
    for i, y in enumerate((-22, 22)):
        mount -= cyl_z(2.25, 47, s+34.2, y, 30.5)
        mount -= cyl_z(4, 5, s+34.2, y, 51)
        add(f'mount_bolt_{i}', vertical_bolt(s+34.2, y, 4, 48.5, 52.5), 'bolt')
    add('motor_mount', mount, 'support')
    add('motor_body', motor, 'motor')
    add('motor_frontcap', frontcap, 'support')
    add('motor_rearcap', rearcap, 'support')
    add('motor_face', face, 'support')
    # A keyed plastic plug on the rear face, above the base clearance pocket.
    connector = box(6, 13, 9, s+83, 0, 34, bevel=.6)
    connector -= box(3.1, 9, 5, s+84.5, 0, 34)
    add('motor_connector', connector, 'connector')
    add('motor_shaft', cyl_x(2.5, 19, s+30.5, 0, 28), 'rod')
    coupling = cyl_x(9, 18, s+21, 0, 28)
    coupling -= cyl_x(4.1, 9.2, s+16.5, 0, 28)
    coupling -= cyl_x(2.6, 9.2, s+25.5, 0, 28)
    for x in (s+18, s+24):
        coupling -= cyl_x(9.1, .8, x, 0, 28) - cyl_x(8.4, 1, x, 0, 28)
    coupling -= box(20, 10, .7, s+21, 5, 28)
    for i, x in enumerate((s+15, s+27)):
        coupling -= cyl_z(1.6, 22, x, 6.2, 28)
        coupling -= cyl_z(2.9, 5, x, 6.2, 35.2)
        add(f'coupling_clamp_bolt_{i}', vertical_bolt(x, 6.2, 22, 32.7, 35.2, 1.5, 2.75), 'bolt')
    add('coupling', coupling, 'coupling')

    platform = plate(52, 82, 8, 4, z=40, bevel=.6)
    for x in (-18, 18):
        for y in (-16, 16):
            platform -= cyl_z(2.75, 10, x, y, 44)
            platform -= cyl_z(4.6, 2.4, x, y, 47)
    for side, y in [('front', -28), ('rear', 28)]:
        housing = box(36, 16, 20, y=y, z=30, bevel=.6) - cyl_x(6.1, 38, 0, y, 30)
        for i, x in enumerate((-12, 12)):
            housing -= cyl_z(1.6, 5, x, y, 38.5)
            platform -= cyl_z(1.7, 10, x, y, 44)
            platform -= cyl_z(3, 3.2, x, y, 46.5)
            add(f'platform_bolt_{side}_{i}', vertical_bolt(x, y, 37, 45, 47.5, 1.5, 2.75), 'bolt')
        add(f'guide_housing_{side}', housing, 'guide')
        bushing = cyl_x(6, 32, 0, y, 30)-cyl_x(4.15, 34, 0, y, 30)
        for x in (-12, 12):
            bushing -= cyl_x(6.1, 1, x, y, 30)-cyl_x(5.65, 1.2, x, y, 30)
        add(f'guide_bushing_{side}', bushing, 'bushing')
    nut_holder = box(20, 20, 22, z=29, bevel=.5) - cyl_x(6.1, 22, 0, 0, 28)
    nut = cyl_x(6, 20, 0, 0, 28) + cyl_x(10, 3, -11.5, 0, 28)
    nut -= cyl_x(4.15, 25, -1.5, 0, 28)
    for i, (y, z) in enumerate([(5.6, 22.4), (-5.6, 22.4), (5.6, 33.6), (-5.6, 33.6)]):
        nut -= cyl_x(1.35, 5, -11.5, y, z)
        nut_holder -= cyl_x(1.35, 6, -8, y, z)
        add(f'nut_flange_bolt_{i}', bolt_x(-5.5, -13, -15.5, y, z, 1.25, 2.1), 'bolt')
    for i, x in enumerate((-6, 6)):
        nut_holder -= cyl_z(1.6, 6, x, 0, 38)
        platform -= cyl_z(1.7, 10, x, 0, 44)
        platform -= cyl_z(3, 3.2, x, 0, 46.5)
        add(f'nut_bolt_{i}', vertical_bolt(x, 0, 35.5, 45, 47.5, 1.5, 2.75), 'bolt')
    add('nut_holder', nut_holder, 'nut')
    add('drive_nut', nut, 'nut')
    add('platform', platform, 'carriage')
    for name in parts:
        if is_moving(name):
            shifted = Pos(position, 0, 0) * parts[name]
            shifted.label, shifted.color = name, parts[name].color
            shifted.material_key = parts[name].material_key
            parts[name] = shifted
    return parts


def assembly(parts, label):
    return Compound(label=label, children=list(parts.values()))


def volume(shape):
    """Adaptive integration also resolves the helical B-spline faces after STEP export."""
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, props, 1e-11, True)
    return props.Mass()


def export(p, output):
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    parts = build(p)
    part_dir = output/'parts'
    part_dir.mkdir(exist_ok=True)
    bom = []
    for name, shape in parts.items():
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(f'{name}: valid={shape.is_valid}, solids={len(shape.solids())}')
        export_step(shape, str(part_dir/f'{name}.step'))
        bb = shape.bounding_box()
        metallic, roughness = MATERIALS[shape.material_key]
        offset, stage = explode(name)
        bom.append({'name': name, 'moving': is_moving(name), 'mechanism': mechanism(name),
                    'volume_mm3': round(volume(shape), 6), 'bbox_min_mm': list(bb.min),
                    'bbox_max_mm': list(bb.max), 'color_rgba': list(shape.color),
                    'material': {'name': shape.material_key, 'metalness': metallic, 'roughness': roughness},
                    'explode': {'offset_mm': offset, 'stage': stage}})
    export_step(assembly(parts, f'linear_stage_v2_{p.travel:g}mm'), str(output/'assembly.step'))
    manifest = {'travel_mm': p.travel, 'base_length_mm': p.base_length, 'rod_length_mm': p.rod_length,
                'support_centers_x_mm': [-p.support_x, p.support_x], 'screw_lead_mm': p.screw_lead,
                'rotation_axis': {'origin_mm': [0, 0, 28], 'direction': [1, 0, 0]},
                'motion': {'rotation_deg_per_mm': -360/p.screw_lead},
                'volume_method': 'BRepGProp adaptive integration, relative epsilon 1e-11',
                'thread': {'handedness': 'right', 'starts': 1, 'crest_diameter_mm': 8,
                           'profile': 'rounded ridge; nominal original design, not a catalog T8 thread',
                           'nut_bore': 'smooth clearance bore, diameter 8.3 mm'}, 'parts': bom}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Exported {len(parts)} valid single-solid parts; travel={p.travel:g}, base={p.base_length:g}, rods={p.rod_length:g} mm; elapsed={time.perf_counter()-start:.2f}s', flush=True)
    return parts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(Stage(**json.loads(args.config.read_text())), args.output)
