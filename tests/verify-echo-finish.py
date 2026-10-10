"""Verify colour artifacts retain exact R2 meshes; optionally native-import them."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET, zipfile

root=Path(__file__).resolve().parents[1]
out=root/'builds/echo-f1-cn-v2'
m=json.loads((out/'manifest.json').read_text(encoding='utf8'))
p=argparse.ArgumentParser();p.add_argument('--native', action='store_true');args=p.parse_args()
a=m['appearance'];assert a['geometryUnchanged'] and not a['printSent']
assert a['sourcePrintHashes']==m['printPlan']['sourcePrintHashes']
assert {x['id'] for x in m['parts'] if x.get('displayFinish')=='silk'}=={'shell_front','shell_rear'}
assert {x['color'] for x in m['parts'] if x['kind']=='printed'}=={'#F1EFE9','#983C40'}
source=next(x for x in m['printPlan']['projects'] if x['id']=='h2c')
assert hashlib.sha256((out/source['file']).read_bytes()).hexdigest()==source['sha256']
seen=set();results=[]
ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
with zipfile.ZipFile(out/source['file']) as original:
    for artifact in a['artifacts']:
        file=out/artifact['file'];assert hashlib.sha256(file.read_bytes()).hexdigest()==artifact['sha256']
        with zipfile.ZipFile(file) as z:
            assert z.testzip() is None and not any(n.endswith('.gcode') for n in z.namelist())
            model=ET.fromstring(z.read('3D/3dmodel.model'))
            config=ET.fromstring(z.read('Metadata/model_settings.config'))
            profile=json.loads(z.read('Metadata/project_settings.config'))
            ids=[obj.find('metadata[@key="name"]').attrib['value'] for obj in config.findall('object')]
            assert set(ids)==set(artifact['partIds']) and len(ids)==len(set(ids))
            assert not seen.intersection(ids);seen.update(ids)
            assert model.attrib['unit']=='millimeter'
            for item in model.findall('m:build/m:item',ns):
                transform=list(map(float,item.attrib['transform'].split()))
                assert transform[:9]==[1,0,0,0,1,0,0,0,1] and transform[11]==0
            children=[n for n in z.namelist() if n.startswith('3D/Objects/')]
            assert len(children)==len(ids)
            for n in children:assert z.read(n)==original.read(n),n
            assert len(profile['filament_self_index'])==len(profile['filament_extruder_variant'])
            assert set(profile['filament_self_index'])=={'1'}
            assert profile['filament_settings_id']==[artifact['filament']]
            assert len(config.findall('plate'))==len(artifact['originalPlates'])
        result={'file':artifact['file'],'sha256':artifact['sha256'],'geometry':'EXACT_R2_MESH_BYTES','objects':len(ids),'nativeImport':'NOT_RUN'}
        if args.native:
            work=root/'.setup/plate-validation/ember-white'/artifact['slot'];work.mkdir(parents=True,exist_ok=True)
            command=[sys.executable,str(root/'.setup/bambu-entry.py'),'--datadir',str(work/'profile'),
                     '--debug','2','--orient','0','--arrange','0','--outputdir',str(work),
                     '--info','--export-3mf','roundtrip.3mf',str(file)]
            run=subprocess.run(command,cwd=root,capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (work/'import.log').write_bytes(run.stdout+run.stderr)
            assert run.returncode==0 and (work/'roundtrip.3mf').is_file(),str(work/'import.log')
            with zipfile.ZipFile(work/'roundtrip.3mf') as z:
                native=ET.fromstring(z.read('Metadata/model_settings.config'))
                names={o.find('metadata[@key="name"]').attrib['value'] for o in native.findall('object')}
                assert names==set(ids)
                triangle_count=sum(len(ET.fromstring(z.read(n)).findall('.//m:triangle',ns)) for n in z.namelist() if n.endswith('.model'))
                assert triangle_count>0, 'Object labels alone do not prove imported geometry'
                for o in native.findall('object'):
                    v={x.attrib.get('key'):x.attrib.get('value') for x in o.findall('metadata')}
                    assert v['wall_loops']=='4' and v['sparse_infill_pattern'] in ('gyroid','zig-zag')
            result['nativeImport']='PASSED'
        results.append(result)
assert seen==set(a['sourcePrintHashes']) and len(seen)==19
record={'checks':results,'printSent':False,'physicalTesting':'NOT_CLAIMED'}
(out/'checks/appearance-validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(record,ensure_ascii=False))
