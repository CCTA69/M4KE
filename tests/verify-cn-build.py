"""Independent, read-only package/mesh checks. Does not imply physical testing."""
from pathlib import Path
import hashlib, json, zipfile
import trimesh
root=Path(__file__).resolve().parents[1]/'builds/echo-f1-cn-v2'
m=json.loads((root/'manifest.json').read_text(encoding='utf8'))
assert m['packageStatus']=='READY_FOR_FIT_CHECK'
assert m['checks']['physicalTest']=='NOT_RUN' and not m['checks']['interferenceConflicts']
assert m['procurementStatus']=='CONFIRM_LISTED_VARIANTS_BEFORE_FULL_PRINT'
assert len(m['parts'])==38 and len(m['printParts'])==18 and len(m['assembly'])==11
ids={p['id'] for p in m['parts']};assert len(ids)==38
assert {'shell_front','shell_rear','esp32','microphone','motor_L','motor_R'}<=ids
assert 'driver' not in ids and 'hub_L' not in ids  # obsolete separate parts must not survive
seen=set()
for step in m['assembly']:
    assert set(step['partIds'])<=ids and set(step['requires'])<=seen
    seen.add(step['id'])
assert len(m['connections'])==14
assert all(w['from']['partId'] in ids and w['to']['partId'] in ids for w in m['connections'])
assert any(w['to']['terminal']=='GPIO3 / A3' for w in m['connections'])
assert not any('GPIO34' in str(w) for w in m['connections'])
assert sum(x['qty']*x['budgetCny'] for x in m['bom'])==566
assert 250<=m['dimensionsMm'][0]<=300
for p in m['printParts']:
    raw=(root/p['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==p['sha256']
    mesh=trimesh.load_mesh(root/p['file'],process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
    assert len(mesh.split())==1,p['id']
    assert abs(mesh.volume-p['volumeMm3'])/p['volumeMm3']<.01
    assert max(mesh.extents[:2])<=170,p['id']  # leave some room on 180 mm bed, not a slicing proof
    assert abs(mesh.bounds[0,2])<.001,p['id']
hashes=json.loads((root/'SHA256SUMS.json').read_text())
with zipfile.ZipFile(root/'ECHO-F1-build-package.zip') as z:
    assert z.testzip() is None
    current={p['file'] for p in m['printPlan']['projects']}
    current.update(p['file'] for p in m.get('appearance',{}).get('artifacts',[]))
    assert {n.removeprefix('ECHO-F1-CN-v2/') for n in z.namelist() if n.endswith('.3mf')}==current, 'No obsolete broken 3MFs in the package'
    for file,want in hashes.items():
        assert '..' not in Path(file).parts and not Path(file).is_absolute()
        raw=(root/file).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==want,file
        assert raw==z.read('ECHO-F1-CN-v2/'+file),file
assert (root/'print/00_fit_coupon.stl').is_file()
assert all(x=='NOT_RUN' for x in m['engineering']['physicalTests'].values())
print(f'PASS: {len(hashes)} files match ZIP/hash; 18 single-solid watertight print meshes + coupon; references, budget and 14 nets checked. Procurement fit and physical testing remain pending.')
