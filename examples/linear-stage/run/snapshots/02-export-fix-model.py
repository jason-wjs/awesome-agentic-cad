"""Screw-driven linear stage. Millimeters; nominal, simplified bought-in geometry."""
from dataclasses import dataclass
from pathlib import Path
import argparse
import json

from build123d import Box, Color, Compound, Cylinder, Pos, RectangleRounded, Rot, export_step, extrude

COLORS = {
    'base': '#52677e', 'support': '#a9bbc8', 'rod': '#d2dce4',
    'screw': '#8a99a8', 'carriage': '#258f99', 'guide': '#72a1ac',
    'bushing': '#b9c5cb', 'nut': '#c99c49', 'motor': '#344354',
    'coupling': '#a6bdcf', 'bolt': '#354453',
}
MOVING = ('platform', 'guide_housing', 'guide_bushing', 'nut_holder', 'drive_nut', 'platform_bolt', 'nut_bolt')


@dataclass(frozen=True)
class Stage:
    travel: float = 80
    platform_length: float = 52
    end_clearance: float = 6
    support_thickness: float = 12

    @property
    def support_x(self):
        return (self.travel + self.platform_length + 2*self.end_clearance + self.support_thickness)/2

    @property
    def rod_length(self):
        return 2*self.support_x + self.support_thickness

    @property
    def base_length(self):
        return 2*self.support_x + 100


def box(dx, dy, dz, x=0, y=0, z=0):
    """Centered box."""
    return Pos(x, y, z) * Box(dx, dy, dz)


def cyl_x(radius, length, x=0, y=0, z=0):
    return Pos(x, y, z) * Rot(0, 90, 0) * Cylinder(radius, length)


def cyl_z(radius, length, x=0, y=0, z=0):
    return Pos(x, y, z) * Cylinder(radius, length)


def plate(dx, dy, dz, radius, x=0, y=0, z=0):
    """Plate extruded upwards from z."""
    return Pos(x, y, z) * extrude(RectangleRounded(dx, dy, radius), amount=dz)


def vertical_bolt(x, y, bottom, shoulder, top, radius=2, head=3.5):
    screw = cyl_z(radius, shoulder-bottom, x, y, (shoulder+bottom)/2)
    screw += cyl_z(head, top-shoulder, x, y, (top+shoulder)/2)
    # A visible socket recess, without modeling thread geometry.
    screw -= cyl_z(head*.48, 1.5, x, y, top-.5)
    return screw


def build(p, position=0):
    s = p.support_x
    parts = {}

    def add(name, shape, color):
        shape.label = name
        shape.color = Color(COLORS[color])
        parts[name] = shape

    base = plate(p.base_length, 100, 8, 5, x=30)
    for x in (-s-12, s+68):
        for y in (-41, 41):
            base -= cyl_z(2.75, 10, x, y, 4)
            base -= cyl_z(5, 3, x, y, 6.5)
    for x in (-s, s):
        for y in (-38, 38): base -= cyl_z(2.1, 10, x, y, 4)
    for y in (-22, 22): base -= cyl_z(2.1, 10, s+35, y, 4)
    add('base', base, 'base')

    for side, x in [('left', -s), ('right', s)]:
        support = box(12, 86, 44, x=x, z=30)
        for y in (-28, 28): support -= cyl_x(4.1, 14, x, y, 30)
        support -= cyl_x(8.1, 14, x, 0, 28)
        for i, y in enumerate((-38, 38)):
            support -= cyl_z(2.25, 46, x, y, 30)
            support -= cyl_z(4, 6, x, y, 50)
            add(f'support_bolt_{side}_{i}', vertical_bolt(x, y, 4, 47, 51), 'bolt')
        add(f'end_support_{side}', support, 'support')
        ring = cyl_x(8, 12, x, 0, 28) - cyl_x(4.1, 14, x, 0, 28)
        add(f'screw_bearing_{side}', ring, 'bushing')
    for side, y in [('front', -28), ('rear', 28)]:
        add(f'guide_rod_{side}', cyl_x(4, p.rod_length, 0, y, 30), 'rod')
    # Shaft reaches the left bearing and extends into the coupling on the right.
    add('lead_screw', cyl_x(4, 2*s+26, 7, 0, 28), 'screw')

    mount = box(6, 52, 45, s+35, 0, 30.5)
    mount -= cyl_x(11.2, 8, s+35, 0, 28)
    motor = box(40, 42, 42, s+60, 0, 28)
    face = box(2, 42, 42, s+39, 0, 28)
    face += cyl_x(11, 2, s+37, 0, 28)
    for i, y in enumerate((-15.5, 15.5)):
        for j, z in enumerate((12.5, 43.5)):
            mount -= cyl_x(1.7, 8, s+35, y, z)
            mount -= cyl_x(3.2, 2.2, s+33, y, z)
            motor -= cyl_x(1.7, 7, s+42.5, y, z)
            face -= cyl_x(1.7, 6, s+39, y, z)
            bolt = cyl_x(1.5, 10, s+39, y, z) + cyl_x(2.75, 2, s+33, y, z)
            bolt -= cyl_x(1.3, 1, s+32.4, y, z)
            add(f'motor_bolt_{i}_{j}', bolt, 'bolt')
    for i, y in enumerate((-22, 22)):
        mount -= cyl_z(2.25, 47, s+35, y, 30.5)
        mount -= cyl_z(4, 5, s+35, y, 51)
        add(f'mount_bolt_{i}', vertical_bolt(s+35, y, 4, 48.5, 52.5), 'bolt')
    add('motor_mount', mount, 'support')
    add('motor_body', motor, 'motor')
    add('motor_face', face, 'support')
    add('motor_shaft', cyl_x(2.5, 19, s+30.5, 0, 28), 'rod')
    coupling = cyl_x(9, 18, s+21, 0, 28)
    coupling -= cyl_x(4.1, 9.2, s+16.5, 0, 28)
    coupling -= cyl_x(2.6, 9.2, s+25.5, 0, 28)
    # Two shallow circumferential grooves make the coupling easy to identify.
    for x in (s+18, s+24):
        coupling -= cyl_x(9.1, 1, x, 0, 28) - cyl_x(8, 1.2, x, 0, 28)
    add('coupling', coupling, 'coupling')

    platform = plate(52, 82, 8, 4, z=40)
    for x in (-18, 18):
        for y in (-16, 16): platform -= cyl_z(2.75, 10, x, y, 44)
    for side, y in [('front', -28), ('rear', 28)]:
        housing = box(36, 16, 20, y=y, z=30) - cyl_x(6.1, 38, 0, y, 30)
        for i, x in enumerate((-12, 12)):
            housing -= cyl_z(1.6, 5, x, y, 38.5)
            platform -= cyl_z(1.7, 10, x, y, 44)
            platform -= cyl_z(3, 3.2, x, y, 46.5)
            add(f'platform_bolt_{side}_{i}', vertical_bolt(x, y, 37, 45, 47.5, 1.5, 2.75), 'bolt')
        add(f'guide_housing_{side}', housing, 'guide')
        add(f'guide_bushing_{side}', cyl_x(6, 32, 0, y, 30)-cyl_x(4.15, 34, 0, y, 30), 'bushing')
    nut_holder = box(20, 20, 22, z=29) - cyl_x(6.1, 22, 0, 0, 28)
    nut = cyl_x(6, 20, 0, 0, 28) + cyl_x(10, 3, -11.5, 0, 28)
    nut -= cyl_x(4.15, 25, -1.5, 0, 28)
    for i, x in enumerate((-6, 6)):
        nut_holder -= cyl_z(1.6, 6, x, 0, 38)
        platform -= cyl_z(1.7, 10, x, 0, 44)
        platform -= cyl_z(3, 3.2, x, 0, 46.5)
        add(f'nut_bolt_{i}', vertical_bolt(x, 0, 35.5, 45, 47.5, 1.5, 2.75), 'bolt')
    add('nut_holder', nut_holder, 'nut')
    add('drive_nut', nut, 'nut')
    add('platform', platform, 'carriage')
    # Keep every carriage-related part in the same moving frame.
    for name in parts:
        if is_moving(name):
            shifted = Pos(position, 0, 0) * parts[name]
            shifted.label, shifted.color = name, parts[name].color
            parts[name] = shifted
    return parts


def is_moving(name):
    return name.startswith(MOVING)


def assembly(parts, label):
    return Compound(label=label, children=list(parts.values()))


def export(p, output):
    output.mkdir(parents=True, exist_ok=True)
    parts = build(p)
    part_dir = output/'parts'
    part_dir.mkdir(exist_ok=True)
    bom=[]
    for name, shape in parts.items():
        export_step(shape, str(part_dir/f'{name}.step'))
        bb = shape.bounding_box()
        bom.append({'name':name, 'moving':is_moving(name), 'volume_mm3':round(shape.volume,6),
                    'bbox_min_mm':list(bb.min), 'bbox_max_mm':list(bb.max),
                    'color_rgba':list(shape.color)})
    export_step(assembly(parts, f'linear_stage_{p.travel:g}mm'), str(output/'assembly.step'))
    manifest={'travel_mm':p.travel,'base_length_mm':p.base_length,'rod_length_mm':p.rod_length,
              'support_centers_x_mm':[-p.support_x,p.support_x], 'parts':bom}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Exported {len(parts)} named parts; travel={p.travel:g}, base={p.base_length:g}, rods={p.rod_length:g} mm',flush=True)
    return parts


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    export(Stage(**json.loads(args.config.read_text())),args.output)
