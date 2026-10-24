"""Compare saved travel variants and verify a fresh 80 mm rebuild."""
from hashlib import sha256
from pathlib import Path
import json
from build123d import Pos, import_step
from check import overlap, TOL

HERE=Path(__file__).parent


def load_parts(folder):
    data=json.loads((folder/'manifest.json').read_text())
    return {e['name']:import_step(str(folder/'parts'/f"{e['name']}.step")) for e in data['parts']}


def difference(a,b):
    common=overlap(a,b)
    return max(0,a.volume+b.volume-2*common)


def main():
    frozen=json.loads((HERE/'run/frozen-80-sha256.json').read_text())
    hashes_match=all(sha256((HERE/path).read_bytes()).hexdigest()==digest for path,digest in frozen.items())
    a=load_parts(HERE/'generated/80')
    b=load_parts(HERE/'generated/120')
    rebuilt=load_parts(HERE/'generated/rebuilt-80')
    assert a.keys()==b.keys()==rebuilt.keys()
    rows=[]
    regression=[]
    for name,old in a.items():
        new=b[name]
        shift=new.bounding_box().center()-old.bounding_box().center()
        aligned=Pos(*(-shift))*new
        diff=difference(old,aligned)
        changed=diff>TOL
        rows.append({'part':name,'geometry_changed':changed,'translation_mm':list(shift),
                     'aligned_symmetric_difference_mm3':round(diff,6)})
        regression.append({'part':name,'symmetric_difference_mm3':round(difference(old,rebuilt[name]),6)})
    changed=[r['part'] for r in rows if r['geometry_changed']]
    expected=['base','guide_rod_front','guide_rod_rear','lead_screw']
    regression_passed=all(r['symmetric_difference_mm3']<=TOL for r in regression)
    variants_passed=all(json.loads((HERE/'generated'/variant/'checks.json').read_text())['passed'] for variant in ('80','120','rebuilt-80'))
    report={'passed':hashes_match and regression_passed and changed==expected and variants_passed,
            'frozen_80_unchanged':hashes_match,'expected_changed_parts':expected,'changed_parts':changed,
            'original_80_rebuild_matches':regression_passed,'all_variant_checks_passed':variants_passed,
            'part_comparison':rows,'rebuild_comparison':regression}
    (HERE/'generated/revision-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('part_comparison','rebuild_comparison')},indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
