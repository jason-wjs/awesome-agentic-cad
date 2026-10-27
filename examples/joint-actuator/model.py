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

from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

from build123d import (
    Axis, Box, Circle, Color, Compound, Cylinder, Ellipse, Plane, Polygon, Pos,
    Rectangle, RectangleRounded, RegularPolygon, Rot, Sphere, Torus, chamfer, export_step,
    extrude, fillet, revolve, sweep,
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
    "insulation": ("#8b704a", .08, .40),
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
    cap = cyl(head, a, shoulder, y, z)
    cap = chamfer(cap.edges(), min(.25, (shoulder-a)*.18))
    shape = cap + cyl(radius, shoulder-.1, b, y, z)
    recess = axial(RegularPolygon(head*.52, 6, rotation=30), a-.1, a+1.4)
    return shape - Pos(0, y, z)*recess


def front_bolt(tip, shoulder, face, y, z, radius=1.8, head=3.05):
    return Rot(0, 180, 0)*bolt(-face, -shoulder, -tip, y, -z, radius, head)


def turned(points):
    """Revolve an axial/radial profile about the shaft axis."""
    return revolve(Polygon(*points, align=None), axis=Axis.X)


def torus_x(major, minor, x):
    return Pos(x, 0, 0)*Rot(0, 90, 0)*Torus(major, minor)


def face_edges(shape, x):
    return [edge for edge in shape.edges()
            if abs(edge.bounding_box().min.X-x) < 1e-5 and abs(edge.bounding_box().max.X-x) < 1e-5]


def gear_profile(count, root, tip):
    points = []
    for i in range(count):
        for fraction, radius in ((0, root), (.22, tip), (.60, tip), (.82, root)):
            angle = 2*math.pi*(i+fraction)/count
            points.append((radius*math.cos(angle), radius*math.sin(angle)))
    profile = Polygon(*points, align=None)
    return fillet(profile.vertices(), .10)


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
    mouth = b if front else a
    circular_length = 2*math.pi*specification["counterbore_radius_mm"]
    mouths = [edge for edge in face_edges(shape, mouth) if abs(edge.length-circular_length) < 1e-4]
    return chamfer(mouths, .25)


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

    stator = ring(48.7, 46.6, -36, -16)
    tooth = box(12, 8.8, 6.2, -27, 42.4, 0)
    tooth = fillet(tooth.edges().filter_by(Axis.Y), .35)
    for i in range(18):
        stator += Rot(i*20, 0, 0)*tooth
    add("stator", stator, "dark_steel", "stator", [-36, 0, 0], True)
    # Two close-packed layers, with rounded end turns around insulated pole cores.
    loops = []
    for length, width in ((20, 9.6), (22, 11.6)):
        wire_path = RectangleRounded(length, width, width/2-.01).wire()
        wire = sweep(Plane(origin=wire_path@0, z_dir=wire_path%0)*Circle(.44), wire_path)
        loops += [Pos(-27, 38.65+i, 0)*Rot(90, 0, 0)*wire for i in range(8)]
    one_coil = Compound(loops)
    liner_profile = RectangleRounded(14.2, 7.4, 1.1)-RectangleRounded(12.2, 6.4, .45)
    liner = Pos(-27, 46.1, 0)*Rot(90, 0, 0)*extrude(liner_profile, amount=7.9)
    for i in range(18):
        add(f"winding_{i+1:02d}", Rot(i*20, 0, 0)*one_coil,
            "copper", "windings", [-36, 0, 0])
        add(f"bobbin_{i+1:02d}", Rot(i*20, 0, 0)*liner,
            "insulation", "windings", [-36, 0, 0])

    drum = ring(33.8, 31, -34, -1) + ring(33.8, bore+3, -34, -31)
    add("rotor_drum", drum, "dark_steel", "rotor", [-12, 0, 0])
    # Separate magnet segments expose the rotor's circumferential structure.
    theta_a, theta_b = math.radians(1.25), math.radians(21.25)
    wedge = axial(Polygon((0, 0), (44*math.cos(theta_a), 44*math.sin(theta_a)),
                          (44*math.cos(theta_b), 44*math.sin(theta_b)), align=None), -30.1, -3.9)
    magnet = ring(36.6, 34, -30, -4) & wedge
    magnet = chamfer(face_edges(magnet, -30)+face_edges(magnet, -4), .18)
    for i in range(16):
        add(f"magnet_{i+1:02d}", Rot(i*22.5, 0, 0)*magnet,
            "magnet", "magnets", [-12, 0, 0])
    add("rotor_shaft", ring(bore+3, bore, -40, 15), "steel", "shaft", [-12, 0, 0])

    # A separate carrier supports the rotor at the rear cover.
    carrier = ring(28, 24.15, -42, -35) + ring(28, 22.1, -42, -40)
    carrier = chamfer(carrier.edges(), .25)
    add("rear_bearing_carrier", carrier, "aluminium", "rear_cap", [-80, 0, 0], True)
    add("rear_bearing_retainer", chamfer(ring(28, 22.1, -35, -34.5).edges(), .12),
        "dark_steel", "rear_cap", [-72, 0, 0], True)
    rear_groove = torus_x(21, 1, -37.5)
    rear_inner = chamfer(ring(20.7, bore+3.1, -40, -35).edges(), .15)-rear_groove
    rear_outer = chamfer(ring(24, 21.3, -40, -35).edges(), .2)-rear_groove
    add("rear_bearing_inner", rear_inner, "polished", "shaft", [-52, 0, 0])
    add("rear_bearing_outer", rear_outer, "polished", "shaft", [-52, 0, 0], True)
    rear_balls = [Pos(-37.5, 21*math.cos(i*math.pi/18), 21*math.sin(i*math.pi/18))*Sphere(.9) for i in range(36)]
    add("rear_bearing_balls", Compound(rear_balls), "polished", "shaft", [-52, 0, 0])

    housing = ring(49, 45.2, 0, 40)
    # Circumferential reliefs and a mounting shoulder provide readable machined edges.
    for a in (4, 10, 16, 22, 28, 34):
        housing -= ring(50, 48.15, a, a+1.5)
    housing += ring(52, 45.2, 0, 3)
    housing += ring(49, 37, 0, 3)
    for i in range(8):
        theta = math.radians(22.5+i*45)
        housing -= cyl(1.45, -.1, 3.1, 39*math.cos(theta), 39*math.sin(theta))
    add("gear_housing", housing, "aluminium", "gear_housing", [25, 0, 0], True)

    circular = cyl(44, 3, 14) - axial(gear_profile(config["circular_spline_teeth"],
                          config["circular_spline_root_radius_mm"],
                          config["circular_spline_tip_radius_mm"]), 2.9, 14.1)
    circular = chamfer([e for e in circular.edges() if e.length > 250], .35)
    circular_bolts = []
    for i in range(8):
        theta = math.radians(22.5+i*45)
        y, z = 39*math.cos(theta), 39*math.sin(theta)
        circular -= cyl(1.6, 2.9, 14.1, y, z)
        circular -= cyl(2.5, 11.5, 14.1, y, z)
        circular_bolts.append(front_bolt(.5, 11.8, 13.8, y, z, 1.3, 2.15))
    add("circular_spline", circular, "steel", "circular_spline", [18, 0, 0], True)
    add("circular_spline_pilot", chamfer(ring(45.1, 44.05, 3, 14).edges(), .18),
        "steel", "circular_spline", [18, 0, 0], True)
    add("circular_spline_screws", Compound(circular_bolts), "dark_steel", "circular_spline", [30, 0, 0], True, stage=1)
    lip = axial(gear_profile(config["flexspline_teeth"],
                            config["flexspline_root_radius_mm"],
                            config["flexspline_tip_radius_mm"]), 3, 12) - cyl(31, 2.9, 12.1)
    cup = ring(32.4, 31, 3, 33) + lip + ring(32.4, bore+4, 30, 33)
    cup += chamfer(ring(33, 31.5, 26, 30).edges(), .25)
    for a in (15, 22):
        cup -= ring(33, 32.15, a, a+.7)
    # Six small lightening holes in the cup base; the thin wall remains intact.
    for i in range(6):
        theta = (i+.5)*math.pi/3
        cup -= cyl(2.1, 29.9, 33.1, 25*math.cos(theta), 25*math.sin(theta))
    add("flexspline", cup, "polished", "flexspline", [46, 0, 0], True)

    wave_path = Pos(8.5, 0, 0)*Rot(0, 90, 0)*Ellipse(29.2, 27.0).wire()
    wave_groove = sweep(Plane(origin=wave_path@0, z_dir=wave_path%0)*Circle(1.5), wave_path)
    wave = axial(Ellipse(28.55, 26.35)-Circle(bore+3.2), 4, 13)
    wave = chamfer(face_edges(wave, 4)+face_edges(wave, 13), .25)-wave_groove
    add("wave_generator", wave, "dark_steel", "wave_generator", [4, 0, 0])
    outer_race = axial(Ellipse(30.95, 28.75)-Ellipse(30.0, 27.8), 4.4, 12.6)
    outer_race = chamfer(face_edges(outer_race, 4.4)+face_edges(outer_race, 12.6), .15)-wave_groove
    add("wave_bearing_outer", outer_race, "polished", "wave_bearing", [4, 0, 0], True)
    balls = []
    for i in range(36):
        theta = 2*math.pi*i/36
        balls.append(Pos(8.5, 27.0*math.sin(theta), -29.2*math.cos(theta))*Sphere(1.4))
    # axial(Ellipse) maps its major axis to Z, consistent with the ball centreline.
    add("wave_bearing_balls", Compound(children=balls), "polished", "wave_bearing", [4, 0, 0])

    inner_race = turned([(22, 34), (22, 39), (27, 39), (30, 36), (33, 39), (38, 39), (38, 34)])
    outer_race = turned([(22, 40), (27, 40), (30, 43), (33, 40), (38, 40), (38, 45), (22, 45)])
    inner_race = chamfer(face_edges(inner_race, 22)+face_edges(inner_race, 38), .3)
    outer_race = chamfer(face_edges(outer_race, 22)+face_edges(outer_race, 38), .3)
    for x in (23.5, 36):
        outer_race -= ring(40.3, 39.9, x, x+.6)
        retainer = ring(40.2, 39.1, x+.05, x+.55)
        add(f"output_bearing_seal_{x:g}", retainer, "polymer", "output_bearing", [70, 0, 0], True)
    add("output_bearing_inner", inner_race, "polished", "output_bearing", [70, 0, 0])
    add("output_bearing_outer", outer_race, "polished", "output_bearing", [70, 0, 0], True)
    rollers, spacers = [], []
    for i in range(28):
        theta = 2*math.pi*i/28
        y, z = 39.5*math.cos(theta), 39.5*math.sin(theta)
        sign = 1 if i%2 == 0 else -1
        direction = (math.sqrt(.5), sign*math.sqrt(.5)*math.cos(theta), sign*math.sqrt(.5)*math.sin(theta))
        roller = chamfer(Cylinder(2.3, 4.8).edges(), .18)
        rollers.append(Plane(origin=(30, y, z), z_dir=direction)*roller)
        spacers.append(Rot(math.degrees(theta)+180/28, 0, 0)*box(2, 4, 1.1, 30, 39.5, 0))
    add("output_bearing_rollers", Compound(children=rollers), "polished", "output_bearing", [70, 0, 0])
    add("output_bearing_separators", Compound(children=spacers), "brass", "output_bearing", [70, 0, 0])

    flange = ring(49, bore, 41, 48) + ring(34, bore, 34, 41)
    flange = chamfer([e for e in flange.edges() if e.length > 300], .6)
    # Front register and recesses distinguish the flange from a flat washer.
    flange -= ring(31, 23, 47.1, 48.1)
    flange = mounting_holes(flange, config["front_mount"], front=True)
    spacer = ring(32, bore+4, 33, 34)
    output_bolts = []
    for i in range(6):
        theta = 2*math.pi*(i+.5)/6
        y, z = 25*math.cos(theta), 25*math.sin(theta)
        flange -= cyl(2.1, 33.9, 48.1, y, z)
        flange -= cyl(3.4, 43.5, 48.1, y, z)
        spacer -= cyl(2.1, 32.9, 34.1, y, z)
        output_bolts.append(front_bolt(30.2, 44, 46.8, y, z))
    add("output_spacer", spacer, "steel", "output_flange", [92, 0, 0])
    add("output_flange_screws", Compound(output_bolts), "dark_steel", "output_flange", [118, 0, 0], stage=1)
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


def volume(shape):
    """Integrate curved B-rep faces adaptively, including the elliptical raceways."""
    total = 0.0
    for solid in shape.solids():
        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(solid.wrapped, properties, 1e-10, True)
        total += properties.Mass()
    return total


def generate(config_path, output):
    started = time.perf_counter()
    config = json.loads(config_path.read_text())
    # Leave at least 1 mm below the rear bearing's raceway root.
    max_bore = 2*(21-1-1-3.1)
    if not math.isfinite(config["bore_mm"]) or not 0 < config["bore_mm"] <= max_bore:
        raise ValueError(f"bore_mm must be positive and no more than {max_bore:g} mm (1 mm bearing wall).")
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
                 "volume_mm3": volume(shape), "bbox_min_mm": list(bounds.min),
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
