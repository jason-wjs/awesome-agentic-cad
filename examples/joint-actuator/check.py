"""Check the exported actuator STEP files, without importing the model builder.

Usage: python check.py generated/bore-20 generated/bore-30 --output run/check.json
"""
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from hashlib import sha256
from itertools import combinations
from math import cos, sin, pi, isclose
from pathlib import Path
import argparse
import json
import time

from build123d import Box, Compound, Cylinder, GeomType, Pos, Rot, import_step
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

HERE = Path(__file__).resolve().parent
VOLUME_TOL = 1e-5  # mm³; face contact has zero intersecting volume.
LENGTH_TOL = 1e-5  # mm; STEP round-trip tolerance.
MOUNTING = {
    'rear_cap': {'pitch_radius': 48, 'hole_x': [-45, -42], 'counterbore_x': [-47.75, -45],
                 'counterbore_mouth_x': -48,
                 'bore_x': [-47.55, -42.45], 'bore_extent_x': [-48, -42], 'bore_chamfer': .45,
                 'bbox': [[-48, -55, -55], [-42, 55, 55]]},
    'output_flange': {'pitch_radius': 40, 'hole_x': [41, 45], 'counterbore_x': [45, 47.75],
                      'counterbore_mouth_x': 48,
                      'bore_x': [34, 48], 'bore_extent_x': [34, 48], 'bore_chamfer': 0,
                      'bbox': [[34, -49, -49], [48, 49, 49]]},
}


def volume(shape):
    if shape is None:
        return 0.0
    total = 0.0
    for solid in shape.solids():
        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(solid.wrapped, properties, 1e-10, True)
        total += properties.Mass()
    return total


def bounds(shape):
    bb = shape.bounding_box()
    return [list(bb.min), list(bb.max)]


def broad_phase(a, b):
    """Reject disjoint bounding boxes before exact B-rep intersection."""
    return all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) > 1e-7
               for i in range(3))


def intersection_volume(a, b):
    return volume(a.intersect(b)) if broad_phase(bounds(a), bounds(b)) else 0.0


def axial_cylinder(radius, x_min, x_max):
    return Pos((x_min + x_max) / 2, 0, 0) * Rot(0, 90, 0) * Cylinder(radius, x_max - x_min)


def native_distance(a, b):
    calculation = BRepExtrema_DistShapeShape()
    calculation.LoadS1(a.wrapped)
    calculation.LoadS2(b.wrapped)
    calculation.SetMultiThread(True)
    calculation.Perform()
    if not calculation.IsDone():
        raise RuntimeError('Native minimum-distance calculation failed')
    return calculation.Value()


def circular_edges(shape, radius=None):
    found = set()
    for edge in shape.edges():
        if edge.geom_type != GeomType.CIRCLE:
            continue
        if radius is not None and not isclose(edge.radius, radius, abs_tol=LENGTH_TOL):
            continue
        found.add(tuple(round(v, 6) for v in [edge.radius, *edge.arc_center]))
    return sorted(found)


def has_point(points, expected):
    return any(all(abs(a - b) < LENGTH_TOL for a, b in zip(point, expected)) for point in points)


def self_test():
    """Known overlap, surface contact, and a blocked through-bore."""
    cube = Box(2, 2, 2)
    tube = axial_cylinder(3, -5, 5) - axial_cylinder(1, -6, 6)
    bore = axial_cylinder(0.9, -6, 6)
    plug = axial_cylinder(0.9, -1, 1)
    seated_head = axial_cylinder(3.05, 44, 46.8)
    head_path = axial_cylinder(3.05, 44, 49)
    obstructing_lip = axial_cylinder(3.4, 47.3, 47.5) - axial_cylinder(2.8, 47.2, 47.6)
    observed = {
        'overlapping_cubes_mm3': intersection_volume(cube, Pos(1, 0, 0) * cube),
        'touching_cubes_mm3': intersection_volume(cube, Pos(2, 0, 0) * cube),
        'separated_cubes_mm3': intersection_volume(cube, Pos(3, 0, 0) * cube),
        'clear_bore_mm3': intersection_volume(tube, bore),
        'blocked_bore_mm3': intersection_volume(tube + plug, bore),
        'separated_cubes_distance_mm': native_distance(cube, Pos(3, 0, 0) * cube),
        'seated_head_lip_intersection_mm3': intersection_volume(seated_head, obstructing_lip),
        'head_insertion_lip_intersection_mm3': intersection_volume(head_path, obstructing_lip),
    }
    expected = dict(zip(observed, [4.0, 0.0, 0.0, 0.0, pi * 0.9**2 * 2, 1.0, 0.0,
                                   pi * (3.05**2 - 2.8**2) * .2]))
    return {'passed': all(abs(observed[k] - expected[k]) < VOLUME_TOL for k in observed),
            'measured': observed, 'expected': expected}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def mounting_interfaces(parts, bore_mm):
    """Probe the drawing dimensions independently of manifest measurements."""
    records = {}
    for name, spec in MOUNTING.items():
        shape = parts[name]
        measured = circular_edges(shape)
        expected = []
        for radius, xs in ((2.2, spec['hole_x']), (3.8, spec['counterbore_x'])):
            for x in xs:
                for i in range(8):
                    angle = (22.5 + 45 * i) * pi / 180
                    expected.append([radius, x, spec['pitch_radius'] * cos(angle), spec['pitch_radius'] * sin(angle)])
        for i in range(8):
            angle = (22.5 + 45 * i) * pi / 180
            expected.append([4.05, spec['counterbore_mouth_x'],
                             spec['pitch_radius'] * cos(angle), spec['pitch_radius'] * sin(angle)])
        expected_bore = [[bore_mm / 2, x, 0, 0] for x in spec['bore_x']]
        if spec['bore_chamfer']:
            expected_bore += [[bore_mm / 2 + spec['bore_chamfer'], x, 0, 0] for x in spec['bore_extent_x']]
        missing = [row for row in expected + expected_bore if not has_point(measured, row)]
        measured_bbox = bounds(shape)
        bbox_error = max(abs(a - b) for aa, bb in zip(measured_bbox, spec['bbox']) for a, b in zip(aa, bb))
        records[name] = {'passed': not missing and bbox_error < LENGTH_TOL,
                         'bolt_count': 8, 'pitch_diameter_mm': spec['pitch_radius'] * 2,
                         'hole_diameter_mm': 4.4, 'counterbore_diameter_mm': 7.6,
                         'counterbore_depth_mm': 3.0, 'counterbore_mouth_chamfer_mm': .25,
                         'bore_diameter_mm': bore_mm,
                         'bbox_mm': measured_bbox, 'bbox_error_mm': bbox_error,
                         'expected_edges_radius_xyz_mm': expected + expected_bore,
                         'missing_edges_radius_xyz_mm': missing}
    return records


def clearances(parts):
    magnets = Compound([parts[f'magnet_{i:02d}'] for i in range(1, 17)])
    # The polygonal internal-tooth tip is a chord, so its minimum radius is
    # slightly less than its 34.4 mm vertex radius. Use that analytic lower bound.
    tooth_gap = 34.4 * cos(pi * .38 / 82) - 33.8
    specifications = {
        'motor_air_gap': (parts['stator'], magnets, 1.4),
        'shaft_to_wave_generator': (parts['rotor_shaft'], parts['wave_generator'], .2),
        'undeformed_tooth_gap': (parts['flexspline'], parts['circular_spline'], tooth_gap),
    }
    records = {}
    for name, (a, b, minimum) in specifications.items():
        print(f'Native clearance: {name}', flush=True)
        measured = native_distance(a, b)
        records[name] = {'passed': measured >= minimum - LENGTH_TOL,
                         'measured_minimum_mm': measured, 'required_minimum_mm': minimum}
    return records


def bearing_proximity(parts):
    """Measure every rolling element against both raceways in the nominal pose."""
    specifications = {
        'rear': ('rear_bearing_balls', 'rear_bearing_inner', 'rear_bearing_outer', .09, .11),
        'wave': ('wave_bearing_balls', 'wave_generator', 'wave_bearing_outer', .09, .11),
        'output': ('output_bearing_rollers', 'output_bearing_inner', 'output_bearing_outer', 0, .25),
    }
    records = {}
    for name, (elements, inner, outer, lower, upper) in specifications.items():
        measurements = [{'index': i, 'inner_gap_mm': solid.distance_to(parts[inner]),
                         'outer_gap_mm': solid.distance_to(parts[outer])}
                        for i, solid in enumerate(parts[elements].solids())]
        gaps = [row[key] for row in measurements for key in ('inner_gap_mm', 'outer_gap_mm')]
        records[name] = {'passed': bool(gaps) and all(lower - LENGTH_TOL <= gap <= upper + LENGTH_TOL for gap in gaps),
                         'rolling_element_count': len(measurements), 'nominal_gap_limits_mm': [lower, upper],
                         'minimum_gap_mm': min(gaps), 'maximum_gap_mm': max(gaps),
                         'measurements': measurements}
    return records


def front_screw_insertion(parts):
    """Sweep the head and shank envelopes into each front fixing along -X."""
    screws = list(parts['output_flange_screws'].solids())
    records = []
    fixed_parts = {name: shape for name, shape in parts.items() if name != 'output_flange_screws'}
    for i in range(6):
        angle = 2 * pi * (i + .5) / 6
        y, z = 25 * cos(angle), 25 * sin(angle)
        head_path = Pos(0, y, z) * axial_cylinder(3.05, 44, 49)
        shank_path = Pos(0, y, z) * axial_cylinder(1.8, 30.2, 49)
        matching = [s for s in screws if abs(s.bounding_box().center().Y - y) < LENGTH_TOL
                    and abs(s.bounding_box().center().Z - z) < LENGTH_TOL]
        cylindrical_radii = [face.radius for screw in matching for face in screw.faces()
                             if face.geom_type == GeomType.CYLINDER]
        head_matches = (len(matching) == 1 and any(abs(r - 3.05) < LENGTH_TOL for r in cylindrical_radii)
                        and any(abs(r - 1.8) < LENGTH_TOL for r in cylindrical_radii))
        obstructions = []
        for name, shape in fixed_parts.items():
            head_hit, shank_hit = intersection_volume(shape, head_path), intersection_volume(shape, shank_path)
            if head_hit > VOLUME_TOL or shank_hit > VOLUME_TOL:
                obstructions.append({'part': name, 'head_sweep_intersection_mm3': head_hit,
                                     'shank_sweep_intersection_mm3': shank_hit})
        records.append({'index': i, 'axis_yz_mm': [y, z], 'head_radius_mm': 3.05,
                        'shank_radius_mm': 1.8, 'entry_x_mm': 49, 'head_seating_x_mm': 44,
                        'shank_tip_x_mm': 30.2, 'native_screw_matches': head_matches,
                        'obstructions': obstructions, 'passed': head_matches and not obstructions})
    return {'passed': len(screws) == 6 and all(r['passed'] for r in records),
            'insertion_direction': '-X from the front face', 'screw_count': len(screws), 'screws': records}


def focused_collisions(folder, patterns):
    """Inspect only pairs involving matching parts while a design is being edited."""
    manifest = json.loads((folder / 'manifest.json').read_text())
    parts = {entry['name']: import_step(str(folder / entry['canonical_step'])) for entry in manifest['parts']}
    selected = {name for name in parts if any(fnmatchcase(name, pattern) for pattern in patterns)}
    if not selected:
        raise ValueError(f'No parts match {patterns}')
    boxes = {name: bounds(shape) for name, shape in parts.items()}
    overlaps, internal_overlaps, invalid = [], [], []
    exact_tests = 0
    for name in sorted(selected):
        shape = parts[name]
        solids = list(shape.solids())
        if not shape.is_valid or not solids or any(not s.is_valid or volume(s) <= VOLUME_TOL for s in solids):
            invalid.append(name)
        for i, j in combinations(range(len(solids)), 2):
            if not broad_phase(bounds(solids[i]), bounds(solids[j])):
                continue
            exact_tests += 1
            hit = volume(solids[i].intersect(solids[j]))
            if hit > VOLUME_TOL:
                internal_overlaps.append({'part': name, 'solid_indices': [i, j], 'intersection_mm3': hit})
    for a, b in combinations(parts, 2):
        if not ({a, b} & selected) or not broad_phase(boxes[a], boxes[b]):
            continue
        exact_tests += 1
        hit = volume(parts[a].intersect(parts[b]))
        if hit > VOLUME_TOL:
            overlaps.append({'parts': [a, b], 'intersection_mm3': hit})
    return {'scope': 'selected parts only', 'complete_assembly_check': False,
            'selected_parts': sorted(selected), 'invalid_parts': invalid,
            'passed': not (invalid or overlaps or internal_overlaps), 'exact_tests': exact_tests,
            'overlaps': overlaps, 'within_part_overlaps': internal_overlaps}


def inspect(folder):
    manifest_path = folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    entries = {entry['name']: entry for entry in manifest['parts']}
    errors = []
    if len(entries) != len(manifest['parts']):
        errors.append('Duplicate part names in manifest')
    parts, geometry, boxes, source_hashes = {}, [], {}, {}
    internal_overlaps = []
    internal_exact_tests = 0
    source_hashes['manifest.json'] = digest(manifest_path)
    for name, entry in entries.items():
        source = folder / 'parts' / f'{name}.step'
        shape = import_step(str(source))
        parts[name] = shape
        boxes[name] = bounds(shape)
        source_hashes[f'parts/{name}.step'] = digest(source)
        measured_volume = volume(shape)
        solids = list(shape.solids())
        valid = bool(shape.is_valid and solids and all(s.is_valid and volume(s) > VOLUME_TOL for s in solids))
        delta_volume = abs(measured_volume - entry['volume_mm3'])
        delta_bbox = max(abs(actual - expected)
                         for box, expected_box in zip(boxes[name], [entry['bbox_min_mm'], entry['bbox_max_mm']])
                         for actual, expected in zip(box, expected_box))
        round_trip = delta_volume < max(VOLUME_TOL, measured_volume * 1e-7) and delta_bbox < LENGTH_TOL
        solid_boxes = [bounds(solid) for solid in solids]
        for i, j in combinations(range(len(solids)), 2):
            if not broad_phase(solid_boxes[i], solid_boxes[j]):
                continue
            internal_exact_tests += 1
            hit = volume(solids[i].intersect(solids[j]))
            if hit > VOLUME_TOL:
                internal_overlaps.append({'part': name, 'solid_indices': [i, j], 'intersection_mm3': hit})
        geometry.append({'name': name, 'valid': valid, 'solid_count': len(solids),
                         'volume_mm3': measured_volume, 'volume_round_trip_error_mm3': delta_volume,
                         'bbox_round_trip_error_mm': delta_bbox, 'round_trip_matches': round_trip})
        if not valid or not round_trip:
            errors.append(f'Invalid or changed STEP part: {name}')
        print(f'{folder.name}: {name}: valid={valid}, solids={len(solids)}, round_trip={round_trip}', flush=True)
    if internal_overlaps:
        errors.append(f'{len(internal_overlaps)} solid pairs overlap within compound parts')

    assembly_path = folder / 'assembly.step'
    assembly = import_step(str(assembly_path))
    source_hashes['assembly.step'] = digest(assembly_path)
    part_volume = sum(row['volume_mm3'] for row in geometry)
    assembly_volume = volume(assembly)
    expected_solids = sum(row['solid_count'] for row in geometry)
    assembly_good = bool(assembly.is_valid and len(assembly.solids()) == expected_solids and
                         abs(assembly_volume - part_volume) < max(VOLUME_TOL, part_volume * 1e-7))
    if not assembly_good:
        errors.append('Assembly STEP topology or volume mismatch')

    bore_mm = manifest.get('bore_mm', manifest.get('parameters', {}).get('bore_mm'))
    if bore_mm is None or bore_mm <= 0:
        raise ValueError('Manifest must give a positive bore_mm')
    assembly_bbox = bounds(assembly)
    bore_probe = axial_cylinder(bore_mm / 2 - LENGTH_TOL, assembly_bbox[0][0] - 1, assembly_bbox[1][0] + 1)
    bore_hits = []
    for name, shape in parts.items():
        hit = intersection_volume(shape, bore_probe)
        if hit > VOLUME_TOL:
            bore_hits.append({'part': name, 'intersection_mm3': hit})
    if bore_hits:
        errors.append('The central through-bore is obstructed')

    interfaces = mounting_interfaces(parts, bore_mm)
    for name, record in interfaces.items():
        if not record['passed']:
            errors.append(f'Mounting interface or bore differs from the drawing: {name}')
    gap_records = clearances(parts)
    for name, record in gap_records.items():
        if not record['passed']:
            errors.append(f'Insufficient geometric clearance: {name}')
    bearing_records = bearing_proximity(parts)
    for name, record in bearing_records.items():
        if not record['passed']:
            errors.append(f'Rolling elements outside nominal raceway gap: {name}')
    insertion = front_screw_insertion(parts)
    if not insertion['passed']:
        errors.append('A front fixing screw cannot enter along its axis')

    presentation = []
    for name, entry in entries.items():
        if not entry.get('cutaway') or entry.get('omitted_from_cutaway'):
            continue
        source = folder / entry['presentation_step']
        section = import_step(str(source))
        source_hashes[entry['presentation_step']] = digest(source)
        section_volume = volume(section)
        outside_source = volume(section - parts[name])
        good = bool(section.is_valid and section.solids() and section_volume > VOLUME_TOL
                    and section_volume < volume(parts[name]) - VOLUME_TOL and outside_source < VOLUME_TOL)
        presentation.append({'name': name, 'valid': bool(section.is_valid), 'volume_mm3': section_volume,
                             'material_outside_canonical_part_mm3': outside_source, 'passed': good})
        if not good:
            errors.append(f'Invalid cutaway or material added to presentation part: {name}')

    collisions, exact_tests = [], 0
    for a_name, b_name in combinations(parts, 2):
        if not broad_phase(boxes[a_name], boxes[b_name]):
            continue
        exact_tests += 1
        hit = volume(parts[a_name].intersect(parts[b_name]))
        if hit > VOLUME_TOL:
            collisions.append({'parts': [a_name, b_name], 'intersection_mm3': hit})
            print(f'COLLISION {a_name} / {b_name}: {hit:.6g} mm³', flush=True)
        if exact_tests % 100 == 0:
            print(f'{folder.name}: {exact_tests} exact pair intersections', flush=True)
    if collisions:
        errors.append(f'{len(collisions)} part pairs overlap')

    report = {
        'variant': folder.name, 'bore_mm': bore_mm, 'passed': not errors, 'errors': errors,
        'part_count': len(parts), 'solid_count': expected_solids, 'geometry': geometry,
        'assembly': {'valid': bool(assembly.is_valid), 'solid_count': len(assembly.solids()),
                     'volume_mm3': assembly_volume, 'part_volume_sum_mm3': part_volume,
                     'bbox_mm': assembly_bbox, 'matches_parts': assembly_good},
        'through_bore': {'diameter_mm': bore_mm, 'probe_radius_mm': bore_mm / 2 - LENGTH_TOL,
                         'passed': not bore_hits, 'obstructions': bore_hits},
        'mounting_interfaces': interfaces, 'clearances': gap_records,
        'bearing_proximity': bearing_records, 'cutaway_parts': presentation,
        'front_screw_insertion': insertion,
        'collisions': {'pairs': len(parts) * (len(parts) - 1) // 2, 'exact_tests': exact_tests,
                       'intersection_tolerance_mm3': VOLUME_TOL, 'overlaps': collisions,
                       'within_part_exact_tests': internal_exact_tests, 'within_part_overlaps': internal_overlaps},
        'input_sha256': source_hashes,
    }
    return report, parts


def compare(before, after, before_parts, after_parts):
    """Compare external size and mating features from native geometry."""
    same_names = set(before_parts) == set(after_parts)
    delta_bbox = max(abs(a - b) for aa, bb in zip(before['assembly']['bbox_mm'], after['assembly']['bbox_mm'])
                     for a, b in zip(aa, bb))
    changed_parts, interfaces = [], {}
    for name in set(before_parts) & set(after_parts):
        delta = volume(after_parts[name]) - volume(before_parts[name])
        if abs(delta) > VOLUME_TOL:
            changed_parts.append({'name': name, 'volume_change_mm3': delta})
    bore_before, bore_after = before['bore_mm'], after['bore_mm']
    for name, spec in MOUNTING.items():
        a, b = before_parts[name], after_parts[name]
        # Enlarging the central hole must leave all material beyond that hole unchanged.
        core = axial_cylinder(max(bore_before, bore_after) / 2 + spec['bore_chamfer'] + LENGTH_TOL, -60, 60)
        a_outside, b_outside = a - core, b - core
        outside_delta = volume(a_outside - b_outside) + volume(b_outside - a_outside)
        thickness = spec['bore_extent_x'][1] - spec['bore_extent_x'][0]
        expected_removed = pi * ((bore_after / 2)**2 - (bore_before / 2)**2) * thickness
        expected_removed += 2 * pi * ((bore_after - bore_before) / 2) * spec['bore_chamfer']**2
        measured_removed = volume(a) - volume(b)
        interfaces[name] = {'passed': outside_delta < VOLUME_TOL and abs(measured_removed - expected_removed) < VOLUME_TOL,
                            'material_changed_outside_revised_bore_mm3': outside_delta,
                            'expected_material_removed_mm3': expected_removed, 'measured_material_removed_mm3': measured_removed}
    passed = (same_names and delta_bbox < LENGTH_TOL and bool(changed_parts) and
              bore_before != bore_after and all(v['passed'] for v in interfaces.values()))
    return {'passed': passed,
            'same_part_names': same_names, 'assembly_bbox_change_mm': delta_bbox,
            'bore_change_mm': [bore_before, bore_after], 'changed_parts': sorted(changed_parts, key=lambda r: r['name']),
            'mounting_interfaces': interfaces}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders', type=Path, nargs='*')
    parser.add_argument('--output', type=Path, default=HERE / 'run' / 'check.json')
    parser.add_argument('--self-test', action='store_true', help='Run known overlap and bore-obstruction controls')
    parser.add_argument('--focus', action='append', metavar='PART_GLOB',
                        help='Print a partial collision check for matching parts; may be repeated; no reports are overwritten')
    args = parser.parse_args()
    if args.self_test:
        controls = self_test()
        print(json.dumps(controls, indent=2))
        return 0 if controls['passed'] else 1
    if len(args.folders) not in (1, 2):
        parser.error('Give one assembly, or two variants to compare')
    if args.focus:
        if len(args.folders) != 1:
            parser.error('--focus takes one assembly')
        result = focused_collisions(args.folders[0], args.focus)
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    start = time.perf_counter()
    controls = self_test()
    records, shapes = [], []
    for folder in args.folders:
        record, parts = inspect(folder)
        records.append(record)
        shapes.append(parts)
    revision = compare(*records, *shapes) if len(records) == 2 else None
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'checker_sha256': digest(Path(__file__)), 'duration_seconds': time.perf_counter() - start,
              'passed': controls['passed'] and all(r['passed'] for r in records) and (revision is None or revision['passed']),
              'positive_controls': controls,
              'variants': [{'variant': r['variant'], 'passed': r['passed'],
                            'report': f"check-{r['variant']}.json"} for r in records],
              'revision': {'passed': revision['passed'], 'report': 'revision.json'} if revision is not None else None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    for record in records:
        individual = {'checked_at_utc': result['checked_at_utc'], 'checker_sha256': result['checker_sha256'],
                      'positive_controls': controls, **record}
        (args.output.parent / f"check-{record['variant']}.json").write_text(json.dumps(individual, indent=2) + '\n')
    if revision is not None:
        revision_record = {'checked_at_utc': result['checked_at_utc'], 'checker_sha256': result['checker_sha256'],
                           'input_sha256': [r['input_sha256']['assembly.step'] for r in records], **revision}
        (args.output.parent / 'revision.json').write_text(json.dumps(revision_record, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'output': str(args.output),
                      'errors': [error for r in records for error in r['errors']]}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
