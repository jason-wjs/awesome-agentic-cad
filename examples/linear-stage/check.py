"""Check exported STEP files, interfaces, and sampled assembly positions."""
from itertools import combinations
from pathlib import Path
import argparse
import json
from math import isclose

from build123d import GeomType, Pos, import_step
from model import is_moving

TOL = 1e-5  # mm³


def bb_overlap(a,b):
    aa,bb=a.bounding_box(),b.bounding_box()
    return all(min(u,v)-max(w,x)>1e-7 for u,v,w,x in zip(aa.max,bb.max,aa.min,bb.min))


def overlap(a,b):
    if not bb_overlap(a,b): return 0.0
    common=a.intersect(b)
    return sum(s.volume for s in common.solids()) if common is not None else 0.0


def circles(shape,radius):
    return [list(e.arc_center) for e in shape.edges()
            if e.geom_type==GeomType.CIRCLE and isclose(e.radius,radius,abs_tol=1e-6)]


def has_point(points,expected):
    return any(all(abs(a-b)<1e-6 for a,b in zip(p,expected)) for p in points)


def inspect(folder):
    manifest=json.loads((folder/'manifest.json').read_text())
    parts={entry['name']:import_step(str(folder/'parts'/f"{entry['name']}.step")) for entry in manifest['parts']}
    errors=[]
    geometry=[]
    for entry in manifest['parts']:
        name=entry['name']; shape=parts[name]
        bounds=shape.bounding_box()
        checks={'name':name,'valid':shape.is_valid,'solids':len(shape.solids()),
                'volume_mm3':round(shape.volume,6)}
        good=shape.is_valid and len(shape.solids())==1 and abs(shape.volume-entry['volume_mm3'])<TOL
        good &= all(abs(a-b)<1e-6 for a,b in zip(bounds.min,entry['bbox_min_mm']))
        good &= all(abs(a-b)<1e-6 for a,b in zip(bounds.max,entry['bbox_max_mm']))
        checks['round_trip_matches']=good
        if not good: errors.append(f'Invalid or changed STEP part: {name}')
        geometry.append(checks)
    saved=import_step(str(folder/'assembly.step'))
    assembly_good=saved.is_valid and len(saved.solids())==len(parts)
    assembly_good &= abs(saved.volume-sum(p.volume for p in parts.values()))<TOL
    if not assembly_good: errors.append('Assembly STEP topology or volume mismatch')

    # Inspect the saved B-rep circular edges, not just the parameter dictionary.
    platform_expected=[[x,y,z] for x in (-18,18) for y in (-16,16) for z in (40,48)]
    platform_good=all(has_point(circles(parts['platform'],2.75),p) for p in platform_expected)
    s=manifest['support_centers_x_mm'][1]
    motor_expected=[[s+38,y,z] for y in (-15.5,15.5) for z in (12.5,43.5)]
    motor_good=all(has_point(circles(parts['motor_face'],1.7),p) for p in motor_expected)
    if not platform_good: errors.append('Platform mounting interface changed')
    if not motor_good: errors.append('Motor mounting interface changed')
    interfaces={'platform':{'pitch_mm':[36,32],'diameter_mm':5.5,'passed':platform_good},
                'motor':{'pitch_mm':[31,31],'diameter_mm':3.4,'passed':motor_good}}

    fixed={n:p for n,p in parts.items() if not is_moving(n)}
    moving={n:p for n,p in parts.items() if is_moving(n)}
    static_collisions=[]
    for group in (fixed,moving):
        for (na,a),(nb,b) in combinations(group.items(),2):
            volume=overlap(a,b)
            if volume>TOL: static_collisions.append({'a':na,'b':nb,'volume_mm3':round(volume,6)})
    if static_collisions: errors.append(f'{len(static_collisions)} collisions within fixed/moving groups')
    samples=[]
    travel=manifest['travel_mm']
    for i in range(9):
        position=-travel/2+i*travel/8
        shifted={n:Pos(position,0,0)*p for n,p in moving.items()}
        collisions=[]
        candidates=0
        for na,a in shifted.items():
            for nb,b in fixed.items():
                if bb_overlap(a,b):
                    candidates+=1
                    volume=overlap(a,b)
                    if volume>TOL: collisions.append({'a':na,'b':nb,'volume_mm3':round(volume,6)})
        clearance=min(shifted['platform'].distance_to(fixed['end_support_left']),
                      shifted['platform'].distance_to(fixed['end_support_right']))
        samples.append({'carriage_x_mm':position,'broad_phase_candidates':candidates,
                        'platform_to_end_support_mm':round(clearance,6),'collisions':collisions})
        if collisions: errors.append(f'{len(collisions)} moving/fixed collisions at x={position:g}')
        if clearance<6-1e-6: errors.append(f'End clearance below 6 mm at x={position:g}')
        print(f'x={position:g} mm: {len(collisions)} moving/fixed collisions; platform/end-support clearance={clearance:.6f} mm',flush=True)
    report={'passed':not errors,'travel_mm':travel,'overlap_tolerance_mm3':TOL,
            'part_count':len(parts),'geometry':geometry,'assembly_round_trip_passed':bool(assembly_good),
            'interfaces':interfaces,'static_collisions':static_collisions,'motion_samples':samples,'errors':errors}
    (folder/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'part_count':len(parts),'static_collisions':static_collisions,'errors':errors},indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    raise SystemExit(0 if inspect(args.folder)['passed'] else 1)
