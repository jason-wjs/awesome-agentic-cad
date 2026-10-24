"""Cross-check the collision results with volume removed by a Boolean cut."""
from itertools import combinations
from pathlib import Path
import json
from build123d import Pos
from compare import load_parts
from check import bb_overlap, overlap, TOL
from model import is_moving

HERE=Path(__file__).parent


def inspect(variant):
    folder=HERE/'generated'/variant
    parts=load_parts(folder)
    travel=json.loads((folder/'manifest.json').read_text())['travel_mm']
    fixed={n:p for n,p in parts.items() if not is_moving(n)}
    moving={n:p for n,p in parts.items() if is_moving(n)}
    checked=0
    collisions=[]
    disagreements=[]

    def check_pair(na,a,nb,b,position):
        nonlocal checked
        if not bb_overlap(a,b): return
        checked+=1
        remaining=sum(s.volume for s in (a-b).solids())
        removed=max(0,a.volume-remaining)
        common=overlap(a,b)
        entry={'a':na,'b':nb,'position_mm':position,'cut_overlap_mm3':round(removed,6),'common_overlap_mm3':round(common,6)}
        if removed>TOL: collisions.append(entry)
        if abs(removed-common)>TOL: disagreements.append(entry)
    for group in (fixed,moving):
        for (na,a),(nb,b) in combinations(group.items(),2):check_pair(na,a,nb,b,None)
    for i in range(9):
        position=-travel/2+i*travel/8
        for na,a in moving.items():
            shifted=Pos(position,0,0)*a
            for nb,b in fixed.items():check_pair(na,shifted,nb,b,position)
    return {'travel_mm':travel,'candidate_pairs_checked':checked,'passed':not collisions and not disagreements,
            'collisions':collisions,'kernel_method_disagreements':disagreements}


if __name__=='__main__':
    reports=[inspect(v) for v in ('80','120')]
    result={'passed':all(r['passed'] for r in reports),'variants':reports}
    (HERE/'generated/collision-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
