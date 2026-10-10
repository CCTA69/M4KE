"""Independent deposited-toolpath envelope checks. Never connects to a printer.

Reads local validation G-code, not a user-downloadable executable print file.
Checks include extruding arcs, brims and supports. Vendor startup/shutdown
motions are excluded: this is not a firmware simulator or a hardware approval.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import math
import re

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'builds/echo-f1-cn-v2'
WORD=re.compile(r'([A-Z])(-?(?:\d+(?:\.\d*)?|\.\d+))')


def bounds_of_arc(start,end,words,clockwise):
    assert 'R' not in words, 'Radius-format arcs need an explicit verifier'
    assert 'I' in words or 'J' in words, 'Missing arc centre'
    cx,cy=start[0]+words.get('I',0),start[1]+words.get('J',0)
    radius=math.hypot(start[0]-cx,start[1]-cy)
    end_radius=math.hypot(end[0]-cx,end[1]-cy)
    assert abs(radius-end_radius)<0.08, 'Arc centre inconsistent with endpoints'
    # Use the larger radius to be conservative about coordinate rounding.
    radius=max(radius,end_radius)
    a=math.atan2(start[1]-cy,start[0]-cx)
    b=math.atan2(end[1]-cy,end[0]-cx)
    sign=-1 if clockwise else 1
    sweep=(sign*(b-a))%(2*math.pi)
    if math.hypot(end[0]-start[0],end[1]-start[1])<1e-7 or words.get('P',0)>=1:
        sweep=2*math.pi
    points=[start,end]
    for angle in [0,math.pi/2,math.pi,3*math.pi/2]:
        if (sign*(angle-a))%(2*math.pi)<=sweep+1e-8:
            points.extend([[cx+radius*math.cos(angle),cy+radius*math.sin(angle),z] for z in [start[2],end[2]]])
    return points


def inspect(lines,lo,hi):
    xyz=[0.,0.,0.]; e=0.; absolute=True; relative_e=False
    feature='Custom'; width=0.6; plane='G17'
    low=[math.inf]*3; high=[-math.inf]*3
    features=Counter(); layers=Counter(); violations=[]; segments=0
    for number,raw in enumerate(lines,1):
        line=raw.strip()
        if line.startswith('; FEATURE:'):
            feature=line.split(':',1)[1].strip(); continue
        if line.startswith('; LINE_WIDTH:'):
            width=float(line.split(':',1)[1]); continue
        command=line.split(';',1)[0].strip()
        if not command: continue
        op=command.split()[0]
        values={k:float(v) for k,v in WORD.findall(command)[1:]}
        if op=='G90':absolute=True
        elif op=='G91':absolute=False
        elif op=='M82':relative_e=False
        elif op=='M83':relative_e=True
        elif op in ('G17','G18','G19'):plane=op
        elif op=='G92':
            for i,k in enumerate('XYZ'):
                if k in values:xyz[i]=values[k]
            if 'E' in values:e=values['E']
        elif op in ('G0','G1','G2','G3'):
            end=[values.get(k,xyz[i]) if absolute else xyz[i]+values.get(k,0) for i,k in enumerate('XYZ')]
            de=values.get('E',0) if relative_e else values.get('E',e)-e
            e=e+de if relative_e else values.get('E',e)
            moving=any(abs(x-y)>1e-8 for x,y in zip(xyz,end)) or op in ('G2','G3')
            if de>1e-8 and moving and feature!='Custom':
                assert plane=='G17', 'Non-XY extruding arc is outside this verifier'
                points=bounds_of_arc(xyz,end,values,op=='G2') if op in ('G2','G3') else [xyz,end]
                # Half-bead + 0.1 mm rounding margin; no unsupported zero-width assumption.
                pad=max(0.2,width/2)+0.1
                for point in points:
                    for i in range(3):
                        low[i]=min(low[i],point[i]-(pad if i<2 else 0))
                        high[i]=max(high[i],point[i]+(pad if i<2 else 0))
                if any(p[i]-pad<lo[i]-1e-4 or p[i]+pad>hi[i]+1e-4 for p in points for i in (0,1)):
                    if len(violations)<5:violations.append({'line':number,'feature':feature,'command':command})
                features[feature]+=1;layers[round(end[2],3)]+=1;segments+=1
            xyz=end
    assert segments>0, 'No deposited model/support paths'
    assert not violations, f'Deposited paths outside printable area: {violations}'
    assert low[2]>0 and abs(min(layers)-0.2)<0.01, 'Missing expected 0.2 mm first layer'
    zs=sorted(layers)
    assert all(b-a<0.221 for a,b in zip(zs,zs[1:])), 'Unexpected empty printed layer / Z gap'
    return {'depositionEnvelopeMm':[[round(x,3) for x in low],[round(x,3) for x in high]],
            'layerCount':len(layers),'depositedSegments':segments,'features':dict(features)}


def controls():
    fixture=['G90','M83','G1 X10 Y10 Z.2','; FEATURE: Outer wall','G1 X20 E1','G3 X10 Y10 I-5 J0 E1']
    assert inspect(fixture,[0,0],[30,30])['depositedSegments']==2
    try:inspect(fixture,[15,0],[30,30])
    except AssertionError:pass
    else:raise AssertionError('Negative bed-boundary control was not rejected')
    absolute=['G90','M82','G92 E20','G1 X10 Y10 Z.2','; FEATURE: Outer wall','G1 X20 E21','G1 E20']
    assert inspect(absolute,[0,0],[30,30])['depositedSegments']==1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',default='recheck-2026-10-09')
    parser.add_argument('--printer',default='h2c')
    args=parser.parse_args(); controls()
    plan=json.loads((BUILD/'plates/print-plan.json').read_text(encoding='utf8'))
    evidence=json.loads((BUILD/'checks/print-plates-native.json').read_text(encoding='utf8'))
    project=next(p for p in plan['projects'] if p['id']==args.printer)
    record=next(p for p in evidence['records'] if p['id']==args.printer)
    assert record['inputSha256']==hashlib.sha256((BUILD/project['file']).read_bytes()).hexdigest()
    folder=ROOT/'.setup/plate-validation'/args.run/args.printer
    native=json.loads((folder/'result.json').read_text(encoding='utf8'))
    assert native['return_code']==0
    reports=[]
    for plate in native['sliced_plates']:
        assert not plate.get('warning_message'), 'Native model/plate warning requires review'
        p=folder/f'plate_{plate["id"]}.gcode'
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        source=next(s for s in record['plateEstimates'] if s['plate']==plate['id'])
        assert source['gcodeSha256']==digest, 'Stale or different native slice output'
        with p.open(encoding='utf8') as file:
            result=inspect(file,*project['packingAreaMm'])
        maximum=max(o['bbox']['height'] for o in plate['objects'])
        assert abs(result['depositionEnvelopeMm'][1][2]-maximum)<=0.21, 'Sliced top does not match model height'
        result.update(plate=plate['id'],gcodeSha256=digest,status='PASS',nativePlateWarnings=plate.get('warning_message',''))
        reports.append(result)
        print(f'PASS plate {plate["id"]}: {result["layerCount"]} layers, {result["depositedSegments"]} deposited segments, supports/brims within printable area',flush=True)
    assert len(reports)==len(project['plates'])
    output={'printer':project['machine'],'projectSha256':record['inputSha256'],'status':'PASS',
            'checks':['Hash-bound native slice','No native plate warnings','Extruding lines and XY arcs including support/brim within nozzle-accessible area','0.2 mm first layer; no Z gaps > 0.22 mm','Sliced model heights match'],
            'controls':'PASS: boundary rejection, relative and absolute extrusion',
            'plates':reports,'vendorCommandWarnings':record.get('warnings',[]),'printSent':False,'physicalTest':'NOT_RUN',
            'limitations':['Not a collision, adhesion, strength or support-removal simulation.','Vendor startup/shutdown and actual printer firmware are not simulated.','Actual filament/nozzle/plate settings, coupon fit and first layer still require operator review.']}
    (BUILD/'checks/print-toolpaths.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8')
