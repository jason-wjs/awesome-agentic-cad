"""Compare the travel revision and an independent rebuild of the 80 mm model."""
from hashlib import sha256
from pathlib import Path
import argparse
import json

from build123d import Pos, import_step
from check import HERE, TOL, load_parts, recorded, volume

EXPECTED_CHANGED = {'base', 'guide_rod_front', 'guide_rod_rear', 'lead_screw'}


def difference(a, b):
    # Use two direct cuts. Common can return empty for coincident cylinders.
    return volume(a - b) + volume(b - a)


def inspect(baseline, revised, rebuilt):
    old_manifest, old = load_parts(baseline)
    new_manifest, new = load_parts(revised)
    rebuilt_manifest, again = load_parts(rebuilt)
    errors = []
    if old.keys() != new.keys() or old.keys() != again.keys():
        errors.append('Named part inventories differ')
    if (old_manifest['travel_mm'], new_manifest['travel_mm'], rebuilt_manifest['travel_mm']) != (80, 120, 80):
        errors.append('Expected 80 mm baseline, 120 mm revision, and 80 mm rebuild')
    rows, regression = [], []
    for name in sorted(old.keys() & new.keys() & again.keys()):
        before, after = old[name], new[name]
        shift = after.bounding_box().center() - before.bounding_box().center()
        aligned = Pos(*(-shift)) * after
        diff = difference(before, aligned)
        rebuild_diff = difference(before, again[name])
        rows.append({'part': name, 'geometry_changed': diff > TOL,
                     'translation_mm': list(shift),
                     'aligned_symmetric_difference_mm3': diff})
        regression.append({'part': name, 'symmetric_difference_mm3': rebuild_diff,
                           'valid': bool(again[name].is_valid), 'solids': len(again[name].solids())})
        print(f'{name}: local geometry changed={diff > TOL}; '
              f'rebuild difference={rebuild_diff:.9g} mm³', flush=True)
    rows.sort(key=lambda row: row['part'])
    regression.sort(key=lambda row: row['part'])
    changed = {row['part'] for row in rows if row['geometry_changed']}
    if changed != EXPECTED_CHANGED:
        errors.append(f'Unexpected changed geometry: {sorted(changed ^ EXPECTED_CHANGED)}')
    regression_good = all(row['symmetric_difference_mm3'] <= TOL and row['valid'] and row['solids'] == 1
                          for row in regression)
    rebuilt_assembly = import_step(str(rebuilt / 'assembly.step'))
    rebuilt_assembly_good = (rebuilt_assembly.is_valid and len(rebuilt_assembly.solids()) == len(again) and
                             abs(volume(rebuilt_assembly) - sum(volume(p) for p in again.values())) < TOL)
    regression_good &= rebuilt_assembly_good
    if not regression_good:
        errors.append('The 80 mm rebuild differs from the baseline')
    variants_good = all(json.loads((folder / 'checks.json').read_text())['passed']
                        for folder in (baseline, revised))
    if not variants_good:
        errors.append('One or more variant checks failed')
    freeze_path = HERE / 'run' / 'frozen-80-sha256.json'
    if freeze_path.exists():
        frozen = json.loads(freeze_path.read_text())
        mismatched = [path for path, digest in frozen.items()
                      if sha256((HERE / path).read_bytes()).hexdigest() != digest]
        if mismatched:
            errors.append(f'Frozen baseline hashes changed: {mismatched}')
    else:
        mismatched = None
        errors.append('Missing frozen baseline hash record')
    report = {'passed': not errors, 'symmetric_difference_tolerance_mm3': TOL,
              'expected_changed_parts': sorted(EXPECTED_CHANGED),
              'changed_parts': sorted(changed), 'original_80_rebuild_matches': regression_good,
              'all_variant_checks_passed': variants_good, 'frozen_80_unchanged': mismatched == [],
              'motion_checked_travel_mm': [80, 120],
              'rebuild_check': 'Part geometry equality in assembly coordinates, valid single solids, assembly round-trip',
              'rebuilt_assembly_round_trip_passed': bool(rebuilt_assembly_good),
              'frozen_80_hash_mismatches': mismatched, 'part_comparison': rows,
              'rebuild_comparison': regression, 'errors': errors}
    (HERE / 'generated' / 'revision-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('part_comparison', 'rebuild_comparison')}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=HERE / 'generated' / '80')
    parser.add_argument('--revised', type=Path, default=HERE / 'generated' / '120')
    parser.add_argument('--rebuilt', type=Path, default=HERE / 'generated' / 'rebuilt-80')
    parser.add_argument('--record')
    args = parser.parse_args()
    action = lambda: inspect(args.baseline.resolve(), args.revised.resolve(), args.rebuilt.resolve())
    report = recorded(args.record, HERE / 'generated', action) if args.record else action()
    raise SystemExit(0 if report['passed'] else 1)
