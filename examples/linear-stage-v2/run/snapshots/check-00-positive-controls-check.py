"""Inspect exported STEP geometry and sample the screw-driven mechanism.

Run ``python check.py generated/80 --record check-01-80``. Inspection uses the
saved B-reps and motion classifications in the manifest; it never calls build().
"""
from contextlib import redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from math import isclose
import argparse
import json
import sys
import time

from build123d import Box, GeomType, Pos, Rot, import_step

HERE = Path(__file__).parent
TOL = 1e-5  # Intersecting volume, mm³. Touching surfaces are permitted.
LINEAR_TOL = 1e-6  # STEP round-trip lengths, mm.
ROTARY = {'screw', 'coupling', 'motor_shaft'}


def volume(shape):
    return sum(s.volume for s in shape.solids()) if shape is not None else 0.0


def bb_overlap(a, b):
    aa, bb = a.bounding_box(), b.bounding_box()
    return all(min(u, v) - max(w, x) > 1e-7
               for u, v, w, x in zip(aa.max, bb.max, aa.min, bb.min))


def overlap(a, b):
    return volume(a.intersect(b)) if bb_overlap(a, b) else 0.0


def removed_volume(a, b):
    return max(0.0, a.volume - volume(a - b))


def circles(shape, radius):
    return [list(e.arc_center) for e in shape.edges()
            if e.geom_type == GeomType.CIRCLE and isclose(e.radius, radius, abs_tol=1e-6)]


def has_point(points, expected):
    return any(all(abs(a - b) < LINEAR_TOL for a, b in zip(p, expected))
               for p in points)


def load_parts(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    parts = {e['name']: import_step(str(folder / 'parts' / f"{e['name']}.step"))
             for e in manifest['parts']}
    return manifest, parts


def mechanism(entry):
    return entry.get('mechanism', 'carriage' if entry.get('moving') else 'fixed')


def posed(parts, entries, position, lead):
    angle = 360 * position / lead
    rotation = Pos(0, 0, 28) * Rot(angle, 0, 0) * Pos(0, 0, -28)
    return {name: (Pos(position, 0, 0) * shape if mechanism(entries[name]) == 'carriage'
                   else rotation * shape if mechanism(entries[name]) in ROTARY else shape)
            for name, shape in parts.items()}


def critical_pair(na, nb):
    # Independently cross-check the narrow clearances around the drivetrain.
    names = {na, nb}
    return ('lead_screw' in names or 'motor_shaft' in names or
            ('platform' in names and any(n.startswith('end_support_') for n in names)))


def self_test():
    """Positive controls: a known overlap and a collision caused by rotation."""
    cube = Box(2, 2, 2)
    half_overlap = Pos(1, 0, 0) * cube
    arm = Pos(0, 2, 28) * Box(2, 1, 1)
    probe = Pos(0, 0, 30) * Box(1, 1, 1)
    carriage = Pos(0, 0, 40) * Box(1, 1, 1)
    shapes = {'arm': arm, 'probe': probe, 'carriage': carriage}
    entries = {'arm': {'mechanism': 'coupling'}, 'probe': {'mechanism': 'fixed'},
               'carriage': {'mechanism': 'carriage'}}
    quarter_turn = posed(shapes, entries, position=1, lead=4)
    checks = {
        'known_overlap_common_mm3': overlap(cube, half_overlap),
        'known_overlap_cut_mm3': removed_volume(cube, half_overlap),
        'touching_cubes_overlap_mm3': overlap(cube, Pos(2, 0, 0) * cube),
        'separated_cubes_overlap_mm3': overlap(cube, Pos(3, 0, 0) * cube),
        'initial_arm_probe_overlap_mm3': overlap(arm, probe),
        'quarter_turn_arm_probe_overlap_mm3': overlap(quarter_turn['arm'], probe),
        'translated_carriage_center_x_mm': quarter_turn['carriage'].bounding_box().center().X,
        'fixed_probe_center_z_mm': quarter_turn['probe'].bounding_box().center().Z,
    }
    expected = [4, 4, 0, 0, 0, 1, 1, 30]
    result = {'passed': all(abs(actual - wanted) < TOL
                            for actual, wanted in zip(checks.values(), expected)),
              'measured': checks, 'expected': dict(zip(checks, expected))}
    print(json.dumps(result, indent=2))
    return result


def inspect(folder):
    manifest, parts = load_parts(folder)
    entries = {e['name']: e for e in manifest['parts']}
    errors = []
    geometry = []
    if len(entries) != len(manifest['parts']):
        errors.append('Duplicate part names in manifest')
    for name, shape in parts.items():
        entry = entries[name]
        bb = shape.bounding_box()
        delta_v = abs(shape.volume - entry['volume_mm3'])
        delta_bbox = max(abs(a - b) for actual, expected in
                         ((bb.min, entry['bbox_min_mm']), (bb.max, entry['bbox_max_mm']))
                         for a, b in zip(actual, expected))
        good = bool(shape.is_valid and len(shape.solids()) == 1 and
                    delta_v < TOL and delta_bbox < LINEAR_TOL)
        geometry.append({'name': name, 'valid': bool(shape.is_valid),
                         'solids': len(shape.solids()), 'volume_mm3': shape.volume,
                         'volume_round_trip_error_mm3': delta_v,
                         'bbox_round_trip_error_mm': delta_bbox,
                         'round_trip_matches': good})
        if not good:
            errors.append(f'Invalid or changed STEP part: {name}')
        print(f'part {name}: {len(shape.solids())} solid(s), valid={shape.is_valid}, '
              f'round-trip={good}', flush=True)
    saved = import_step(str(folder / 'assembly.step'))
    assembly_good = bool(saved.is_valid and len(saved.solids()) == len(parts) and
                         abs(saved.volume - sum(p.volume for p in parts.values())) < TOL)
    if not assembly_good:
        errors.append('Assembly STEP topology or volume mismatch')

    # Probe the actual circular edges of the exported solids at both plate faces.
    platform_expected = [[x, y, z] for x in (-18, 18) for y in (-16, 16) for z in (40, 48)]
    platform_found = circles(parts['platform'], 2.75)
    platform_good = all(has_point(platform_found, p) for p in platform_expected)
    support_right = manifest['support_centers_x_mm'][1]
    motor_expected = [[support_right + x, y, z] for x in (38, 40)
                      for y in (-15.5, 15.5) for z in (12.5, 43.5)]
    motor_found = circles(parts['motor_face'], 1.7)
    motor_good = all(has_point(motor_found, p) for p in motor_expected)
    for good, label in ((platform_good, 'Platform'), (motor_good, 'Motor')):
        if not good:
            errors.append(f'{label} mounting interface changed')
    interfaces = {
        'platform': {'pitch_mm': [36, 32], 'diameter_mm': 5.5, 'passed': platform_good,
                     'expected_circle_centers_mm': platform_expected,
                     'measured_circle_centers_mm': platform_found},
        'motor': {'pitch_mm': [31, 31], 'diameter_mm': 3.4, 'passed': motor_good,
                  'expected_circle_centers_mm': motor_expected,
                  'measured_circle_centers_mm': motor_found},
    }

    rigid_groups = {}
    for name, entry in entries.items():
        group = mechanism(entry)
        if group not in {'fixed', 'carriage'} | ROTARY:
            errors.append(f'Unknown mechanism group: {name}: {group}')
        # All drivetrain parts share the same rotation, hence one rigid group.
        rigid_groups[name] = 'rotary' if group in ROTARY else group
    candidates = 0
    crosschecks = []
    disagreements = []

    def inspect_pair(na, a, nb, b, position):
        nonlocal candidates
        if not bb_overlap(a, b):
            return None
        candidates += 1
        common = overlap(a, b)
        if critical_pair(na, nb):
            cut = removed_volume(a, b)
            entry = {'a': na, 'b': nb, 'carriage_x_mm': position,
                     'common_mm3': common, 'cut_mm3': cut}
            crosschecks.append(entry)
            if abs(common - cut) > TOL:
                disagreements.append(entry)
        if common > TOL:
            return {'a': na, 'b': nb, 'volume_mm3': common}
        return None

    static_collisions = []
    for (na, a), (nb, b) in combinations(parts.items(), 2):
        if rigid_groups[na] == rigid_groups[nb]:
            collision = inspect_pair(na, a, nb, b, None)
            if collision:
                static_collisions.append(collision)
                print(f'static collision: {collision}', flush=True)
    if static_collisions:
        errors.append(f'{len(static_collisions)} collisions within rigid groups')
    print(f'Static geometry: {len(static_collisions)} collisions', flush=True)

    travel = manifest['travel_mm']
    lead = manifest.get('lead_mm', manifest.get('screw_lead_mm', 4.0))
    if lead <= 0:
        raise ValueError('Screw lead must be positive')
    # Nine full-travel samples plus quarter-turn offsets around the center.
    # The extra poses prevent integer turns from hiding asymmetric collisions.
    positions = sorted({-travel / 2 + i * travel / 8 for i in range(9)} |
                       {lead * i / 4 for i in (-3, -2, -1, 0, 1, 2, 3)
                        if abs(lead * i / 4) <= travel / 2})
    samples = []
    for position in positions:
        at = posed(parts, entries, position, lead)
        collisions = []
        before = candidates
        for (na, a), (nb, b) in combinations(at.items(), 2):
            if rigid_groups[na] != rigid_groups[nb]:
                collision = inspect_pair(na, a, nb, b, position)
                if collision:
                    collisions.append(collision)
        clearance = min(at['platform'].distance_to(at['end_support_left']),
                        at['platform'].distance_to(at['end_support_right']))
        samples.append({'carriage_x_mm': position, 'shaft_angle_deg': 360 * position / lead,
                        'shaft_phase_deg': (360 * position / lead) % 360,
                        'broad_phase_candidates': candidates - before,
                        'platform_to_end_support_mm': clearance, 'collisions': collisions})
        if collisions:
            errors.append(f'{len(collisions)} collisions at carriage x={position:g} mm')
        if clearance < 6 - LINEAR_TOL:
            errors.append(f'End clearance below 6 mm at x={position:g}')
        print(f'x={position:g} mm / shaft={360 * position / lead:g}°: '
              f'{len(collisions)} collisions; end clearance={clearance:.6f} mm', flush=True)
        for row in collisions:
            print(f'  {row}', flush=True)
    if disagreements:
        errors.append(f'{len(disagreements)} Common/cut volume disagreements')
    report = {'passed': not errors, 'travel_mm': travel, 'lead_mm': lead,
              'rotation_axis': {'origin_mm': [0, 0, 28], 'direction': [1, 0, 0]},
              'part_count': len(parts), 'overlap_tolerance_mm3': TOL,
              'length_tolerance_mm': LINEAR_TOL, 'geometry': geometry,
              'assembly_round_trip_passed': assembly_good, 'interfaces': interfaces,
              'static_collisions': static_collisions, 'motion_samples': samples,
              'broad_phase_candidates_total': candidates, 'cut_volume_crosschecks': crosschecks,
              'kernel_method_disagreements': disagreements, 'errors': errors}
    (folder / 'checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('passed', 'part_count', 'travel_mm', 'errors')}, indent=2))
    return report


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def recorded(label, folder, action):
    run = HERE / 'run'
    run.mkdir(exist_ok=True)
    snapshots = run / 'snapshots'
    snapshots.mkdir(exist_ok=True)
    if (run / f'{label}.json').exists():
        raise FileExistsError(f'Run record already exists: {label}')
    sources = {}
    for name in ('check.py', 'compare.py', 'model.py'):
        path = HERE / name
        if path.exists():
            data = path.read_bytes()
            sources[name] = sha256(data).hexdigest()
            (snapshots / f'{label}-{name}').write_bytes(data)
    inputs = {str(p.relative_to(HERE)): sha256(p.read_bytes()).hexdigest()
              for p in sorted(folder.rglob('*')) if p.is_file() and p != folder / 'checks.json'}
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    with (run / f'{label}.log').open('w') as log:
        with redirect_stdout(Tee(sys.stdout, log)):
            report = action()
    metadata = {'started_at_utc': started, 'duration_seconds': time.monotonic() - timer,
                'python': sys.version.split()[0], 'source_sha256': sources,
                'input_sha256': inputs, 'exit_code': 0 if report['passed'] else 1}
    (run / f'{label}.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (run / f'{label}-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, nargs='?')
    parser.add_argument('--self-test', action='store_true', help='Run synthetic positive controls.')
    parser.add_argument('--record', help='Preserve stdout, source snapshots, and input hashes in run/.')
    args = parser.parse_args()
    if not args.self_test and args.folder is None:
        parser.error('folder is required unless --self-test is given')
    folder = args.folder.resolve() if args.folder else HERE / 'generated' / '80'
    action = self_test if args.self_test else lambda: inspect(folder)
    result = recorded(args.record, folder, action) if args.record else action()
    raise SystemExit(0 if result['passed'] else 1)
