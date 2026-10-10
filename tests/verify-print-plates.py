"""Read back every delivered 3MF; reject missing parts, scaling and stale sources."""
from pathlib import Path
import hashlib,json,math,sys,zipfile,xml.etree.ElementTree as ET
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'builds/echo-f1-cn-v2'
plan=json.loads((OUT/'plates/print-plan.json').read_text(encoding='utf8'))
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
PRODUCTION='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
expected={p['id']:p['sha256'] for p in manifest['printParts']}
expected['fit_coupon']=hashlib.sha256((OUT/'print/00_fit_coupon.stl').read_bytes()).hexdigest()
assert plan['sourcePrintHashes']==expected and not plan['printSent']
for project in plan['projects']:
    raw=(OUT/project['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==project['sha256']
    with zipfile.ZipFile(OUT/project['file']) as z:
        assert z.testzip() is None and not any(n.endswith('.gcode') for n in z.namelist())
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        meta=ET.fromstring(z.read('Metadata/model_settings.config'))
        settings=json.loads(z.read('Metadata/project_settings.config'))
        assert model.attrib['unit']=='millimeter'
        assert settings['printer_settings_id']==project['machine']
        assert settings['filament_settings_id'] and settings['filament_type']==['PLA']
        assert settings['curr_bed_type']=='Textured PEI Plate'
        assert settings['nozzle_diameter'][0]=='0.4'
        assert settings['name']=='project_settings' and settings['from']=='project'
        assert settings['print_compatible_printers']==[project['machine']]
        if settings.get('extruder_variant_list'):
            assert len(settings['filament_extruder_variant'])==len(settings['filament_self_index'])
            assert settings['filament_self_index']==['1']*len(settings['filament_extruder_variant']), 'All nozzle variants belong to the single PLA slot'
        assert len(settings['filament_colour'])==1
        assert 'wall_loops' in settings['different_settings_to_system'][0].split(';')
        objects=model.findall('m:resources/m:object',NS);items=model.findall('m:build/m:item',NS)
        assert len(objects)==len(items)==19
        assert len(meta.findall('plate'))==len(project['plates'])
        assert len(meta.findall('object'))==19
        relationships=ET.fromstring(z.read('3D/_rels/3dmodel.model.rels'))
        targets={r.attrib['Target'] for r in relationships}
        assert len(targets)==19
        parts=[p for plate in project['plates'] for p in plate['parts']]
        assert {p['id'] for p in parts}==set(expected) and len(parts)==len(expected)
        assert project['plates'][0]['parts'][0]['id']=='fit_coupon'
        assert len(project['plates'][0]['parts'])==1
        for p,obj,item in zip(parts,objects,items):
            assert item.attrib['objectid']==obj.attrib['id']
            components=obj.findall('m:components/m:component',NS)
            assert len(components)==1
            component=components[0]
            target=component.attrib['{'+PRODUCTION+'}path']
            assert target in targets and '..' not in target
            child=ET.fromstring(z.read(target.lstrip('/')))
            obj=child.find('m:resources/m:object',NS)
            assert obj is not None and obj.attrib['id']==component.attrib['objectid']
            assert component.attrib['transform']=='1 0 0 0 1 0 0 0 1 0 0 0'
            vertices=np.array([[float(v.attrib[k]) for k in ('x','y','z')] for v in obj.findall('m:mesh/m:vertices/m:vertex',NS)])
            faces=np.array([[int(v.attrib[k]) for k in ('v1','v2','v3')] for v in obj.findall('m:mesh/m:triangles/m:triangle',NS)])
            mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
            source=trimesh.load_mesh(OUT/p['file'],process=True)
            assert mesh.is_watertight and mesh.is_winding_consistent
            np.testing.assert_allclose(np.sort(mesh.extents),np.sort(source.extents),atol=1e-4)
            assert abs(mesh.volume-source.volume)/source.volume<1e-5
            assert abs(mesh.bounds[0,2])<1e-5
            t=list(map(float,item.attrib['transform'].split()))
            assert t[:9]==[1,0,0,0,1,0,0,0,1] and t[11]==0,'No scaling, tilting or floating above the bed'
            config=meta.find(f'object[@id="{item.attrib["objectid"]}"]')
            assert config.find('part').attrib['id']==obj.attrib['id']
            values={v.attrib.get('key'):v.attrib.get('value') for v in config.findall('metadata')}
            assert values['sparse_infill_pattern'] in ('zig-zag','gyroid')
            if values['sparse_infill_density']=='100%':assert values['sparse_infill_pattern']=='zig-zag'
        lo,hi=np.array(project['packingAreaMm'])
        for plate in project['plates']:
            assert hashlib.sha256((OUT/plate['preview']).read_bytes()).hexdigest()==plate['sha256Preview']
            assert len({p['colour'] for p in plate['parts']})==1,'No multi-colour plate'
            for i,p in enumerate(plate['parts']):
                assert p['x']>=lo[0]+11.99 and p['y']>=lo[1]+11.99
                assert p['x']+p['width']<=hi[0]-11.99 and p['y']+p['depth']<=hi[1]-11.99
                for other in plate['parts'][i+1:]:
                    dx=max(p['x'],other['x'])-min(p['x']+p['width'],other['x']+other['width'])
                    dy=max(p['y'],other['y'])-min(p['y']+p['depth'],other['y']+other['depth'])
                    assert max(dx,dy)>=11.99,'Model envelopes overlap / insufficient spacing'
                if p['id'].startswith('shell_') or p['id']=='canopy':assert p['settings']['enable_support']=='1'
                if p['id'].startswith('bearing_spacer_'):assert p['settings']['sparse_infill_density']=='100%'
    print(f'PASS {project["id"]}: {len(project["plates"])} plates; 19 parts; source hashes, unit scale, orientation, profile, spacing and colour split')
print('Geometry/layout checks only. Real slicing and physical print results are independent.')
