#!/usr/bin/env python3
"""Inspect native STEP exports and sample declared rigid assembly paths."""
from __future__ import annotations
import hashlib, itertools, json, sys
from pathlib import Path
from build123d import Axis, import_step

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
TOL=1e-5  # mm^3; ignores numerical sliver volumes, not visible interferences.
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def volume(shape):
    if shape is None:return 0.0
    if isinstance(shape,(list,tuple)):return sum(volume(s) for s in shape)
    return sum(abs(s.volume) for s in shape.solids())
def overlap(a,b):return volume(a.intersect(b))
def check_path(name, moving, fixed, positions, transform):
    samples=[{'position':p,'overlap_mm3':sum(overlap(transform(moving,p),b) for b in fixed)} for p in positions]
    return {'name':name,'samples':samples,'maximum_overlap_mm3':max(s['overlap_mm3'] for s in samples),'passed':all(s['overlap_mm3']<TOL for s in samples)}

def main():
    report={'method':'OpenCascade solid validity, pairwise common volume, sampled rigid paths. Sampling is not continuous collision certification.','volume_tolerance_mm3':TOL,'script_sha256':sha(Path(__file__)),'cases':[],'physical_print':'not performed','physical_fit':'not measured','strength':'not tested'}
    for k in map(int,sys.argv[1:] or range(1,9)):
        file=HERE/'exports'/f'J0{k}-assembled.step';assembly=import_step(file)
        parts=list(assembly.children);a=next(p for p in parts if '_A_' in p.label);b=next(p for p in parts if '_B_' in p.label)
        static=[{'a':x.label,'b':y.label,'overlap_mm3':overlap(x,y)} for x,y in itertools.combinations(parts,2)]
        case={'id':f'J0{k}','step_sha256':sha(file),'solid_count':len(assembly.solids()),'parts':[{'name':p.label,'valid':p.is_valid,'volume_mm3':p.volume,'bounds_mm':list(p.bounding_box().min)+list(p.bounding_box().max)} for p in parts],'assembled_pairs':static,'paths':[]}
        if k in [4,5]:
            radius=20 if k==5 else 18;axis=Axis((-radius,0,0),(0,0,1))
            case['paths'].append(check_path('A at -77 degrees: approach along X from -50 to 0 mm',a,[b],list(range(-50,1)),lambda p,t:p.rotate(axis,-77).translate((t,0,0))))
            case['paths'].append(check_path('A: rotate -77 to 0 degrees about Z at X=-radius',a,[b],list(range(-77,1)),lambda p,t:p.rotate(axis,t)))
        elif k==8:
            keys=sorted((p for p in parts if '_/_Key_' in p.label),key=lambda p:p.label)
            for i,key in enumerate(keys):case['paths'].append(check_path(f'Key {i+1}: withdraw along '+('+Y' if i==0 else '-Y'),key,[a,b,keys[1-i]],list(range(0,36)),lambda p,t:p.translate((0,t*(1 if i==0 else -1),0))))
            case['paths'].append(check_path('After removing keys: A slides +Y',a,[b],list(range(0,31)),lambda p,t:p.translate((0,t,0))))
        else:case['paths'].append(check_path('A: translate from Z=-25 to 0'+(' with X=1.5 Z' if k==3 else ''),a,[b],list(range(-25,1)),lambda p,t:p.translate((1.5*t if k==3 else 0,0,t))))
        case['blocked_direction_control']={'movement':'A translated -1 mm along X; geometric restraint expected','overlap_mm3':overlap(a.translate((-1,0,0)),b)}
        case['passed']=len(assembly.solids())==(4 if k==8 else 2) and all(p['valid'] for p in case['parts']) and all(p['overlap_mm3']<TOL for p in static) and all(p['passed'] for p in case['paths']) and case['blocked_direction_control']['overlap_mm3']>TOL
        report['cases'].append(case);print(case['id'],'PASS' if case['passed'] else 'FAIL',[(p['name'],round(p['maximum_overlap_mm3'],4)) for p in case['paths']],flush=True)
    report['status']='passed' if all(c['passed'] for c in report['cases']) else 'findings'
    (HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if report['status']=='passed' else 1)
if __name__=='__main__':main()
