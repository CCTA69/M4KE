"""Read-only release consistency check. Does not certify physical performance."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[1]/'builds/echo-f1-v1'
m=json.loads((root/'manifest.json').read_text(encoding='utf8'))
assert m['packageStatus']=='READY_FOR_FIT_CHECK'
assert not m['checks']['interferenceConflicts']
assert m['checks']['physicalTest']=='NOT_RUN'
assert len({p['id'] for p in m['parts']})==len(m['parts'])==40
assert len(m['printParts'])==17 and len(m['assembly'])==11
assert len(m['connections'])==22
ids={p['id'] for p in m['parts']}
for w in m['connections']:
    assert w['from']['partId'] in ids and w['to']['partId'] in ids
seen=set()
for step in m['assembly']:
    assert set(step['partIds'])<=ids
    assert set(step['requires'])<=seen
    seen.add(step['id'])
hashes=json.loads((root/'SHA256SUMS.json').read_text())
with zipfile.ZipFile(root/'ECHO-F1-build-package.zip') as z:
    assert z.testzip() is None
    for f,expected in hashes.items():
        assert '..' not in Path(f).parts and not Path(f).is_absolute()
        raw=(root/f).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==expected,f
        assert z.read('ECHO-F1-v1/'+f)==raw,f
for p in m['printParts']:
    raw=(root/p['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==p['sha256']
    assert len(raw)==84+50*int.from_bytes(raw[80:84],'little')
    assert p['meshChecks']['watertight'] and p['meshChecks']['volumeRelativeError']<.01
assert (root/'print/00_fit_coupon.stl').stat().st_size>84
assert sum(p['qty']*p['budgetCny'] for p in m['bom'])==488
print(f'PASS: {len(hashes)} files match ZIP and SHA256; 17 print parts + coupon; references and assembly dependencies valid. Physical testing NOT_RUN.')
