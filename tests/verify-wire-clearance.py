"""Replay display-wire clearance against native STEP solids, not cached pass flags.

This is not a harness/PCB/pin-position certification. No geometry is changed.
"""
from pathlib import Path
import hashlib,json,math,os,argparse

ROOT=Path(__file__).resolve().parents[1]
handles=[]
if os.name=='nt' and (ROOT/'.setup/runtime-dlls').exists():
    handles.append(os.add_dll_directory(str(ROOT/'.setup/runtime-dlls')))
import cadquery as cq

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build',choices=['echo-f1-v1','echo-f1-cn-v2'],default='echo-f1-v1')
build_id=parser.parse_args().build
out=ROOT/'builds'/build_id
part_count,wire_count=(38,14) if build_id=='echo-f1-cn-v2' else (40,22)
m=json.loads((out/'manifest.json').read_text(encoding='utf8'))
r=json.loads((out/'checks/wire-display.json').read_text(encoding='utf8'))
assert m['wireDisplay']==r
assert r['purpose']=='DISPLAY_ONLY_NOT_MANUFACTURING_WIRE_HARNESS'
assert r['includesClosedShellInCollisionCheck'] is True
assert r['wireRadiusMm']==.65 and r['partClearanceMm']==.15
parts={p['id']:p for p in m['parts']}
solids={};boxes={}
for c in m['cadParts']:
    p=parts[c['id']]
    assert p['rotation']==[0,0,0]
    for kind,folder in [('stl','assembly-parts'),('step','step')]:
        assert hashlib.sha256((out/folder/f'{c["id"]}.{kind}').read_bytes()).hexdigest()==c['sha256'][kind]
    assert r['modelBindings'][c['id']]==dict(stl=c['sha256']['stl'],step=c['sha256']['step'],position=p['position'],rotation=p['rotation'])
    solid=cq.importers.importStep(str(out/'step'/f'{c["id"]}.step')).val().translate(tuple(p['position']))
    bb=solid.BoundingBox()
    solids[c['id']]=solid
    boxes[c['id']]=([bb.xmin,bb.ymin,bb.zmin],[bb.xmax,bb.ymax,bb.zmax])
assert len(solids)==len(parts)==part_count
assert set(m.get('coverPartIds',['body_shell','canopy']))<=solids.keys()
tests=0


def conflicts(polyline,radius,clearance):
    global tests
    hits=[];margin=radius+clearance
    for i,(a,b) in enumerate(zip(polyline,polyline[1:])):
        assert len(a)==len(b)==3 and all(math.isfinite(v) for v in a+b)
        assert math.dist(a,b)>1e-6
        edge=cq.Edge.makeLine(cq.Vector(*a),cq.Vector(*b))
        for pid,(lo,hi) in boxes.items():
            if any(max(a[k],b[k])+margin<lo[k] or min(a[k],b[k])-margin>hi[k] for k in range(3)):continue
            tests+=1
            # Distance to a segment includes its endpoints. A radius-sized
            # capsule bounds the viewport cylinder and its round joint spheres.
            d=solids[pid].distance(edge)
            if d<margin-1e-6:hits.append(dict(segment=i,partId=pid,distanceMm=d))
    return hits


logical={c['id']:c for c in m['connections']}
assert len(r['connections'])==len(logical)==wire_count
assert len({c['id'] for c in r['connections']})==wire_count
segments=0
for c in r['connections']:
    net=logical[c['id']]
    assert 'polylineMm' not in net, 'Electrical netlist must not contain centre-to-centre placeholder paths.'
    assert c['endpoints']=={'from':net['from'],'to':net['to']}
    assert c['status']=='DISPLAY_CLEAR' and c['anchorStatus']=='VIRTUAL_SURFACE_PORT_NOT_REAL_PIN'
    assert c['wireRadiusMm']==r['wireRadiusMm'] and c['clearanceMm']==r['partClearanceMm']
    assert 2<=len(c['polylineMm'])<=64
    assert c['polylineMm'][0]==c['fromAnchorMm'] and c['polylineMm'][-1]==c['toAnchorMm']
    hits=conflicts(c['polylineMm'],c['wireRadiusMm'],c['clearanceMm'])
    assert not hits,(c['id'],hits)
    segments+=len(c['polylineMm'])-1
old=logical['W12'];a=parts[old['from']['partId']]['position'];b=parts[old['to']['partId']]['position']
z=max(a[2],b[2])+8
negative=conflicts([a,[a[0],a[1],z],[b[0],b[1],z],b],.65,.15)
expected={'esp32','motor_R'} if build_id=='echo-f1-cn-v2' else {'microphone','esp32','body_shell'}
assert expected<={h['partId'] for h in negative}
assert m['checks']['physicalTest']=='NOT_RUN'
print(f'PASS: {wire_count} display routes / {segments} rendered capsule segments / {part_count} native obstacles; {tests} narrow-phase checks; closed-shell included; old W12 rejected. Real pins, connectors, bend radius and wire-to-wire clearance NOT VERIFIED.')
