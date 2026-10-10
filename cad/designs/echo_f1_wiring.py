"""Collision-screened DISPLAY routes. Virtual surface ports are NOT real PCB pins.
Never changes CAD, firmware, or the electrical connection/net list.
"""
from pathlib import Path
import argparse
import os,json,hashlib,heapq,itertools,time
ROOT=Path(__file__).resolve().parents[2]
HANDLES=[]
if os.name=='nt' and (ROOT/'.setup/runtime-dlls').exists():
    HANDLES.append(os.add_dll_directory(str(ROOT/'.setup/runtime-dlls')))
import numpy as np
import trimesh
from scipy.ndimage import distance_transform_edt
import cadquery as cq

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build',choices=['echo-f1-v1','echo-f1-cn-v2'],default='echo-f1-v1')
OUT=ROOT/'builds'/parser.parse_args().build
M=json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
P={p['id']:p for p in M['parts']}
pitch=1.0
radius=.65
clearance=.15
points=[];boxes={};solids={}
for a in M['cadParts']:
    raw=(OUT/'assembly-parts'/f"{a['id']}.stl").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==a['sha256']['stl']
    mesh=trimesh.load_mesh(OUT/'assembly-parts'/f"{a['id']}.stl",process=True)
    assert P[a['id']]['rotation']==[0,0,0], 'Add rotation handling before routing a rotated build.'
    mesh.apply_translation(P[a['id']]['position'])
    boxes[a['id']]=mesh.bounds.copy()
    vox=mesh.voxelized(pitch).fill()
    points.append(np.rint(vox.points/pitch).astype(np.int32))
    rawstep=(OUT/'step'/f"{a['id']}.step").read_bytes()
    assert hashlib.sha256(rawstep).hexdigest()==a['sha256']['step']
    solids[a['id']]=cq.importers.importStep(str(OUT/'step'/f"{a['id']}.step")).val().translate(tuple(P[a['id']]['position']))
    print('Voxelized',a['id'],len(points[-1]),flush=True)
occupied=np.concatenate(points)
lo=occupied.min(axis=0)-12;hi=occupied.max(axis=0)+12
shape=tuple((hi-lo+1).tolist());solid_grid=np.zeros(shape,dtype=bool)
indices=occupied-lo
solid_grid[tuple(indices.T)]=True
# Includes a circumscribed half-voxel allowance, not just a centre-line test.
blocked=distance_transform_edt(~solid_grid,sampling=pitch)<radius+clearance+np.sqrt(3)*pitch/2+.05
reserved=np.zeros(shape,dtype=np.uint8)
neighbours=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
preferred={'battery_holder':(0,1),'power_switch':(0,-1),'arm_button':(0,-1),'microphone':(0,1),'esp32':(2,1),'driver':(2,1),'regulator':(2,1),'motor_L':(1,1),'motor_R':(1,-1)}
ports={}

def index(p):return tuple(np.rint(np.asarray(p)/pitch).astype(int)-lo)
def world(p):return (np.asarray(p)+lo)*pitch
def free(p):return all(0<=p[i]<shape[i] for i in range(3)) and not blocked[p]
def port_options(part,terminal,target):
    key=part+'|'+terminal
    if key in ports:return [ports[key]]
    mn,mx=boxes[part];middle=(mn+mx)/2;span=mx-mn
    choices=[];seen=set()
    for axis in range(3):
        rest=[a for a in range(3) if a!=axis]
        for sign in [-1,1]:
            for u,v in itertools.product([-.3,0,.3],repeat=2):
                for offset in [2.0,3.0,4.0]:
                    p=middle.copy();p[axis]=(mx[axis] if sign>0 else mn[axis])+sign*offset
                    p[rest[0]]+=span[rest[0]]*u;p[rest[1]]+=span[rest[1]]*v
                    q=index(p)
                    if q in seen or not free(q):continue
                    seen.add(q)
                    pref=0 if (axis,sign)==preferred.get(part) else 35
                    crowded=30 if any(np.linalg.norm(world(q)-world(x))<3 for k,x in ports.items() if k.startswith(part+'|')) else 0
                    score=pref+crowded+offset*3+np.linalg.norm(world(q)-target)*.12
                    choices.append((score,q))
    return [x[1] for x in sorted(choices)[:8]]

def route(start,goal):
    def h(p):return sum(abs(p[i]-goal[i]) for i in range(3))
    queue=[(h(start),0,start)];cost={start:0};parent={};expanded=0
    while queue and expanded<220000:
        _,g,p=heapq.heappop(queue)
        if g!=cost.get(p):continue
        if p==goal:
            path=[p]
            while p in parent:p=parent[p];path.append(p)
            return path[::-1]
        expanded+=1
        for d in neighbours:
            n=tuple(p[i]+d[i] for i in range(3))
            if not free(n):continue
            # Prefer separate lanes without making a false wire-to-wire clearance claim.
            ng=g+1+(3 if reserved[n] and h(n)>3 and sum(abs(n[i]-start[i]) for i in range(3))>3 else 0)
            if ng>=cost.get(n,10**9):continue
            cost[n]=ng;parent[n]=p;heapq.heappush(queue,(ng+h(n),ng,n))
    return None

def simplify(path):
    result=[path[0]]
    for i in range(1,len(path)-1):
        if tuple(path[i][k]-path[i-1][k] for k in range(3))!=tuple(path[i+1][k]-path[i][k] for k in range(3)):result.append(path[i])
    result.append(path[-1]);return [world(p).tolist() for p in result]

def native_conflicts(polyline,checked_radius=radius):
    conflicts=[];minimum=1000.0
    for i,(a,b) in enumerate(zip(polyline,polyline[1:])):
        mn=np.minimum(a,b)-checked_radius-clearance;mx=np.maximum(a,b)+checked_radius+clearance
        edge=cq.Edge.makeLine(cq.Vector(*a),cq.Vector(*b))
        for pid,(pmin,pmax) in boxes.items():
            if np.any(mx<pmin) or np.any(mn>pmax):continue
            distance=solids[pid].distance(edge);minimum=min(minimum,distance)
            if distance<checked_radius+clearance-1e-6:conflicts.append({'segment':i,'partId':pid,'distanceMm':round(distance,5)})
    return conflicts,minimum


def clear_segment(a,b):
    # Shortcuts must keep the same inflated voxel and native-solid checks.
    # Never smooth with an unchecked spline that can cut back through a part.
    a=np.asarray(a);b=np.asarray(b)
    samples=np.linspace(a,b,max(2,int(np.ceil(np.linalg.norm(b-a)/.35))+1))
    if not all(free(index(p)) for p in samples):return False
    return not native_conflicts([a,b])[0]


def tidy(polyline):
    # Greedy visibility simplification removes the voxel staircase.
    simple=[polyline[0]];i=0
    while i<len(polyline)-1:
        j=len(polyline)-1
        while j>i+1 and not clear_segment(polyline[i],polyline[j]):j-=1
        simple.append(polyline[j]);i=j
    # Small, sampled round corners. Every resulting rendered segment is checked.
    rounded=[simple[0]]
    for a,b,c in zip(simple,simple[1:],simple[2:]):
        a,b,c=map(np.asarray,(a,b,c))
        before=b-a;after=c-b
        d=min(2.,np.linalg.norm(before)/3,np.linalg.norm(after)/3)
        entry=b-before/np.linalg.norm(before)*d;leave=b+after/np.linalg.norm(after)*d
        rounded.extend([((1-t)**2*entry+2*(1-t)*t*b+t*t*leave).tolist() for t in np.linspace(0,1,5)])
    rounded.append(simple[-1])
    if len(rounded)<=64 and all(clear_segment(a,b) for a,b in zip(rounded,rounded[1:])):return rounded
    return simple


result=[]
for w in M['connections']:
    a,b=w['from'],w['to']
    aa=port_options(a['partId'],a['terminal'],np.asarray(P[b['partId']]['position']))
    bb=port_options(b['partId'],b['terminal'],np.asarray(P[a['partId']]['position']))
    found=None
    for start,goal in itertools.islice(itertools.product(aa,bb),12):
        path=route(start,goal)
        if path:
            poly=tidy(simplify(path))
            if len(poly)>64:continue
            collisions,minimum=native_conflicts(poly)
            if not collisions:
                found=dict(id=w['id'],endpoints={'from':a,'to':b},status='DISPLAY_CLEAR',fromAnchorMm=poly[0],toAnchorMm=poly[-1],polylineMm=poly,wireRadiusMm=radius,clearanceMm=clearance,anchorStatus='VIRTUAL_SURFACE_PORT_NOT_REAL_PIN',segmentCount=len(poly)-1,collisions=[])
                ports[a['partId']+'|'+a['terminal']]=start;ports[b['partId']+'|'+b['terminal']]=goal
                for p in path:reserved[p]=1
                break
    result.append(found or dict(id=w['id'],status='UNRESOLVED',reason='No collision-screened display route found. Keep the 2D connection only.'))
    print(w['id'],result[-1]['status'],flush=True)

# The original centre-to-centre route is an intentional negative control.
old=next(c for c in M['connections'] if c['id']=='W12')
pa=P[old['from']['partId']]['position'];pb=P[old['to']['partId']]['position'];z=max(pa[2],pb[2])+8
bad,_=native_conflicts([pa,[pa[0],pa[1],z],[pb[0],pb[1],z],pb])
assert bad,'Negative control must detect the old through-component route.'
report={'schemaVersion':1,'purpose':'DISPLAY_ONLY_NOT_MANUFACTURING_WIRE_HARNESS','voxelPitchMm':pitch,'wireRadiusMm':radius,'partClearanceMm':clearance,'includesClosedShellInCollisionCheck':True,'modelStlHashes':{p['id']:p['sha256']['stl'] for p in M['cadParts']},'modelBindings':{p['id']:{'stl':p['sha256']['stl'],'step':p['sha256']['step'],'position':P[p['id']]['position'],'rotation':P[p['id']]['rotation']} for p in M['cadParts']},'connections':result,'negativeControl':{'wireId':'W12','oldRouteDetected':True,'collisions':bad},'limitations':['Surface ports are display proxies, not verified PCB terminals.','Clearance uses simplified component CAD, not measured supplier parts.','Connector bodies, service loops, bend radius, wire-to-wire spacing and assembly access are not validated.','The cover is removed only for viewing; its CAD remains an obstacle in the route checks.']}
(OUT/'checks/wire-display.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('READY',sum(c['status']=='DISPLAY_CLEAR' for c in result),'/',len(result),flush=True)
