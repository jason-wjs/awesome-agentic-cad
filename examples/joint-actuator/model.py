"""Nominal hollow-shaft joint actuator, millimetres. build123d 0.11.

The rigid 80/82-tooth reducer represents an undeformed flexspline with a
0.6 mm radial tooth gap. The geometry is a cutaway study, not a flexure solver.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import time

from build123d import (
    Box, Circle, Color, Compound, Cylinder, Ellipse, Plane, Polygon, Pos,
    RectangleRounded, RegularPolygon, Rot, Sphere, chamfer, export_step,
    extrude, sweep,
)

MATERIALS = {
    "aluminium": ("#bac3cc", .88, .28),
    "steel": ("#8c99a7", .93, .24),
    "polished": ("#cbd4dd", .97, .18),
    "dark_steel": ("#353e49", .82, .30),
    "magnet": ("#535a63", .72, .31),
    "copper": ("#c67d42", .88, .25),
    "brass": ("#af9251", .82, .29),
    "pcb": ("#105e4b", .10, .45),
    "chip": ("#19262c", .15, .44),
    "polymer": ("#333a43", .05, .48),
}


def cyl(radius, a, b, y=0, z=0):
    return Pos((a+b)/2, y, z) * Rot(0, 90, 0) * Cylinder(radius, b-a)


def ring(outer, inner, a, b):
    return cyl(outer, a, b) - cyl(inner, a-1, b+1)


def axial(profile, a, b):
    return Pos(a, 0, 0) * Rot(0, 90, 0) * extrude(profile, amount=b-a, dir=(0, 0, 1))


def box(dx, dy, dz, x, y, z):
    return Pos(x, y, z) * Box(dx, dy, dz)


def bolt(a, shoulder, b, y, z, radius=1.2, head=3.2):
    """Rear-facing socket-head screw, with unthreaded nominal shank."""
    shape = cyl(head, a, shoulder, y, z) + cyl(radius, shoulder, b, y, z)
    recess = axial(RegularPolygon(head*.52, 6, rotation=30), a-.1, a+1.4)
    return shape - Pos(0, y, z)*recess


def gear_profile(count, root, tip):
    points = []
    for i in range(count):
        for fraction, radius in ((0, root), (.22, tip), (.60, tip), (.82, root)):
            angle = 2*math.pi*(i+fraction)/count
            points.append((radius*math.cos(angle), radius*math.sin(angle)))
    return Polygon(*points, align=None)


def mounting_holes(shape, specification, front=False):
    a, b = specification["x_min_mm"], specification["x_max_mm"]
    for i in range(specification["count"]):
        angle = math.radians(specification["phase_deg"] + i*360/specification["count"])
        y = specification["pitch_radius_mm"]*math.cos(angle)
        z = specification["pitch_radius_mm"]*math.sin(angle)
        shape -= cyl(specification["hole_radius_mm"], a-.1, b+.1, y, z)
        lo, hi = ((b-specification["counterbore_depth_mm"], b+.1) if front
                  else (a-.1, a+specification["counterbore_depth_mm"]))
        shape -= cyl(specification["counterbore_radius_mm"], lo, hi, y, z)
    return shape


def build(config):
    bore = config["bore_mm"]/2
    parts = {}
    records = {}

    def add(name, shape, material, group, offset, section=False, stage=2):
        # Freeze locations into a flat compound before adding the named STEP node.
        # Nested reused assembly children otherwise duplicate occurrences on export.
        shape = Compound(shape.solids())
        shape.label = name
        shape.color = Color(MATERIALS[material][0])
        parts[name] = shape
        records[name] = {"name": name, "group": group, "material_key": material,
                         "section": section, "explode": {"offset_mm": offset, "stage": stage}}

    # Rear cover and cooling jacket. External flange holes are left open for mounting.
    cap = ring(55, bore, -48, -42)
    cap = chamfer(cap.edges(), .45)
    cap = mounting_holes(cap, config["rear_mount"])
    jacket = ring(50, 49, -42, 0)
    for a in (-41, -34, -27, -20, -13, -6):
        fin = ring(55, 49.8, a, a+3)
        fin = chamfer(fin.edges(), .25)
        jacket += fin
    # A machined flat supports the encoder PCB without cutting into the stator.
    jacket += box(28, 2.1, 19, -20, -50.55, -7)
    jacket -= box(30, 12, 21, -20, -57.6, -7)
    for i in range(4):
        t = i*math.pi/2
        y, z = 51*math.cos(t), 51*math.sin(t)
        cap -= cyl(1.5, -48.1, -41.9, y, z)
        cap -= cyl(3.5, -48.1, -45, y, z)
        jacket -= cyl(1.5, -42.1, -38.5, y, z)
        add(f"case_screw_{i+1:02d}", bolt(-47.7, -45.3, -39, y, z),
            "dark_steel", "fasteners", [-115, 0, 0], stage=1)
    add("rear_cap", cap, "aluminium", "rear_cap", [-92, 0, 0])
    add("motor_housing", jacket, "aluminium", "motor_housing", [-64, 0, 0], True)

    stator = ring(48.7, 46.6, -36, -14)
    for i in range(12):
        stator += Rot(i*30, 0, 0)*box(16, 8.8, 5.4, -25.5, 42.4, 0)
    add("stator", stator, "dark_steel", "stator", [-36, 0, 0], True)
    wire_path = RectangleRounded(24, 9, 2.8).wire()
    wire = sweep(Plane(origin=wire_path@0, z_dir=wire_path%0)*Circle(.42), wire_path)
    one_coil = Compound(children=[Pos(-25.5, 38.7+.9*i, 0)*Rot(90, 0, 0)*wire for i in range(9)])
    for i in range(12):
        add(f"winding_{i+1:02d}", Rot(i*30, 0, 0)*one_coil,
            "copper", "windings", [-36, 0, 0])

    drum = ring(33.8, 31, -34, -1) + ring(33.8, bore+3, -34, -31)
    add("rotor_drum", drum, "dark_steel", "rotor", [-12, 0, 0])
    # Separate magnet segments expose the rotor's circumferential structure.
    magnet_points = []
    for radius, angles in ((34, range(0, 21, 2)), (36.6, range(20, -1, -2))):
        for degree in angles:
            theta = math.radians(degree+1.25)
            magnet_points.append((radius*math.cos(theta), radius*math.sin(theta)))
    magnet = axial(Polygon(*magnet_points, align=None), -30, -4)
    for i in range(16):
        add(f"magnet_{i+1:02d}", Rot(i*22.5, 0, 0)*magnet,
            "magnet", "magnets", [-12, 0, 0])
    add("rotor_shaft", ring(bore+3, bore, -40, 15), "steel", "shaft", [-12, 0, 0])

    housing = ring(49, 45.2, 0, 40)
    # Circumferential reliefs and a mounting shoulder provide readable machined edges.
    for a in (4, 10, 16, 22, 28, 34):
        housing -= ring(50, 48.15, a, a+1.5)
    housing += ring(52, 45.2, 0, 3)
    add("gear_housing", housing, "aluminium", "gear_housing", [25, 0, 0], True)

    circular = cyl(44, 3, 14) - axial(gear_profile(config["circular_spline_teeth"],
                          config["circular_spline_root_radius_mm"],
                          config["circular_spline_tip_radius_mm"]), 2.9, 14.1)
    add("circular_spline", circular, "steel", "circular_spline", [18, 0, 0], True)
    lip = axial(gear_profile(config["flexspline_teeth"],
                            config["flexspline_root_radius_mm"],
                            config["flexspline_tip_radius_mm"]), 3, 12) - cyl(31, 2.9, 12.1)
    cup = ring(32.4, 31, 3, 33) + lip + ring(32.4, bore+4, 30, 33)
    # Six small lightening holes in the cup base; the thin wall remains intact.
    for i in range(6):
        theta = (i+.5)*math.pi/3
        cup -= cyl(2.1, 29.9, 33.1, 25*math.cos(theta), 25*math.sin(theta))
    add("flexspline", cup, "polished", "flexspline", [46, 0, 0], True)

    wave = axial(Ellipse(28, 25.8)-Circle(bore+3.2), 4, 13)
    add("wave_generator", wave, "dark_steel", "wave_generator", [4, 0, 0])
    outer_race = axial(Ellipse(30.7, 28.5)-Ellipse(30.2, 28.0), 4.4, 12.6)
    add("wave_bearing_outer", outer_race, "polished", "wave_bearing", [4, 0, 0], True)
    balls = []
    for i in range(36):
        theta = 2*math.pi*i/36
        balls.append(Pos(8.5, 27.1*math.sin(theta), -29.3*math.cos(theta))*Sphere(.85))
    # axial(Ellipse) maps its major axis to Z, consistent with the ball centreline.
    add("wave_bearing_balls", Compound(children=balls), "polished", "wave_bearing", [4, 0, 0])

    add("output_bearing_inner", ring(36, 34, 22, 38), "polished", "output_bearing", [70, 0, 0])
    add("output_bearing_outer", ring(45, 43, 22, 38), "polished", "output_bearing", [70, 0, 0], True)
    rollers, spacers = [], []
    for i in range(28):
        theta = 2*math.pi*i/28
        y, z = 39.5*math.cos(theta), 39.5*math.sin(theta)
        sign = 1 if i%2 == 0 else -1
        direction = (math.sqrt(.5), sign*math.sqrt(.5)*math.cos(theta), sign*math.sqrt(.5)*math.sin(theta))
        rollers.append(Plane(origin=(30, y, z), z_dir=direction)*Cylinder(2.3, 4.8))
        spacers.append(Rot(math.degrees(theta)+180/28, 0, 0)*box(3.2, 4.8, 1.1, 30, 39.5, 0))
    add("output_bearing_rollers", Compound(children=rollers), "polished", "output_bearing", [70, 0, 0])
    add("output_bearing_separators", Compound(children=spacers), "brass", "output_bearing", [70, 0, 0])

    flange = ring(49, bore, 41, 48) + ring(34, bore, 34, 41)
    # Front register and recesses distinguish the flange from a flat washer.
    flange -= ring(31, 23, 47.1, 48.1)
    flange = mounting_holes(flange, config["front_mount"], front=True)
    for i in range(6):
        theta = 2*math.pi*i/6
        flange -= cyl(1.65, 40.9, 48.1, 19.5*math.cos(theta), 19.5*math.sin(theta))
    add("output_flange", flange, "aluminium", "output_flange", [104, 0, 0])

    # Encoder electronics on the flat: board, IC, connector and discrete contacts.
    board = box(25, 1.2, 16, -20, -52.8, -7)
    for x in (-30, -10):
        for z in (-13, -1):
            hole = Pos(x, -52.8, z)*Rot(90, 0, 0)*Cylinder(.85, 3)
            board -= hole
            post = Pos(x, -52, z)*Rot(90, 0, 0)*Cylinder(1.4, .4)
            post -= Pos(x, -52, z)*Rot(90, 0, 0)*Cylinder(.85, .6)
            add(f"encoder_post_{x}_{z}", post, "brass", "encoder", [-64, -10, 0])
    add("encoder_pcb", board, "pcb", "encoder", [-64, -10, 0])
    add("encoder_ic", box(7, 1, 6, -20, -53.9, -7), "chip", "encoder", [-64, -10, 0])
    add("encoder_connector", box(7, 2, 3, -20, -54.4, -1), "polymer", "encoder", [-64, -10, 0])
    contacts = [box(.5, .3, 1.1, -23+i, -53.55, -11) for i in range(7)]
    contacts += [box(.5, .3, 1.1, -23+i, -53.55, -3.15) for i in range(7)]
    add("encoder_contacts", Compound(children=contacts), "brass", "encoder", [-64, -10, 0])

    return parts, records


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate(config_path, output):
    started = time.perf_counter()
    config = json.loads(config_path.read_text())
    # Leave at least 1 mm between the bore and the inner flange bolt holes.
    max_bore = 2*(19.5-1.65-1)
    if not math.isfinite(config["bore_mm"]) or not 0 < config["bore_mm"] <= max_bore:
        raise ValueError(f"bore_mm must be positive and no more than {max_bore:g} mm (1 mm bolt-hole wall).")
    output.mkdir(parents=True, exist_ok=True)
    (output/"parts").mkdir(exist_ok=True)
    (output/"presentation-parts").mkdir(exist_ok=True)
    parts, records = build(config)
    print(f"Built {len(parts)} named parts in {time.perf_counter()-started:.1f}s", flush=True)
    cut_box = box(220, 110, 110, 0, -55, 55)
    presentation = []
    manifest_parts = []
    for index, (name, shape) in enumerate(parts.items()):
        if not shape.is_valid or any(s.volume <= 0 for s in shape.solids()):
            raise ValueError(f"Invalid native geometry: {name}")
        record = records[name]
        material_name = record["material_key"]
        color, metalness, roughness = MATERIALS[material_name]
        bounds = shape.bounding_box()
        export_step(shape, output/"parts"/f"{name}.step")
        if name == "stator":
            # Expose the windings while retaining their pole cores and rear bridge.
            yoke_window = cut_box - cyl(46.6, -110, 110) - box(154, 220, 220, -110, 0, 0)
            display = shape-yoke_window
        else:
            display = shape-cut_box if record["section"] else copy.deepcopy(shape)
        omitted = not display.solids()
        changed = record["section"] and abs(shape.volume-display.volume) > 1e-7
        relative = f"presentation-parts/{name}.step" if changed else f"parts/{name}.step"
        if omitted:
            relative = None
        else:
            display.label = name
            display.color = Color(color)
            if not display.is_valid:
                raise ValueError(f"Invalid cutaway geometry: {name}")
            if changed:
                export_step(display, output/relative)
            presentation.append(display)
        entry = {"name": name, "group": record["group"], "canonical_step": f"parts/{name}.step",
                 "presentation_step": relative, "cutaway": changed,
                 "omitted_from_cutaway": omitted, "solid_count": len(shape.solids()),
                 "volume_mm3": shape.volume, "bbox_min_mm": list(bounds.min),
                 "bbox_max_mm": list(bounds.max), "color_rgba": list(Color(color)),
                 "material": {"name": material_name, "metalness": metalness, "roughness": roughness},
                 "explode": record["explode"]}
        manifest_parts.append(entry)
        print(f"[{index+1:02d}/{len(parts)}] {name}: {len(shape.solids())} solids", flush=True)
    assembly = Compound(label="joint_actuator", children=list(parts.values()))
    export_step(assembly, output/"assembly.step")
    export_step(Compound(label="joint_actuator_cutaway", children=presentation), output/"cutaway.step")
    manifest = {"name": "Hollow-shaft joint actuator", "units": "mm", "axis": "X",
                "bore_mm": config["bore_mm"], "parameters": config,
                "nominal_envelope_mm": {"body_diameter": 110, "length": 96, "x_min": -48, "x_max": 48},
                "interfaces": {"rear_mount": config["rear_mount"], "front_mount": config["front_mount"]},
                "simplifications": ["Rigid undeformed flexspline; simplified trapezoidal teeth with 0.6 mm radial clearance.",
                                    "Nominal unthreaded fasteners and simplified bearing contacts."],
                "part_count": len(manifest_parts), "solid_count": len(assembly.solids()),
                "parts": manifest_parts}
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    elapsed = round(time.perf_counter()-started, 3)
    record = {"config": config_path.name, "model_sha256": digest(__file__),
              "config_sha256": digest(config_path), "bore_mm": config["bore_mm"],
              "part_count": len(manifest_parts), "solid_count": len(assembly.solids()),
              "elapsed_seconds": elapsed, "assembly_sha256": digest(output/"assembly.step"),
              "cutaway_sha256": digest(output/"cutaway.step"), "native_valid": True}
    run = Path(__file__).parent/"run"/f"model-{config['bore_mm']}.json"
    run.parent.mkdir(exist_ok=True)
    run.write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.config.resolve(), args.output.resolve())
