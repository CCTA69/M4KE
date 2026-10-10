"""Deterministic, colour-separated build plates from hash-bound print meshes.

Writes unsliced Bambu-compatible 3MF projects, never sends a printer command.
Only translation and Z-axis quarter turns are allowed: no scale or CAD edits.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import math
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'builds/echo-f1-cn-v2'
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
PRODUCTION = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
TARGETS = {
    'h2c': ('Bambu Lab H2C 0.4 nozzle', '0.20mm Standard @BBL H2C', 'Generic PLA @BBL H2C 0.4 nozzle', 330, 320),
    'p1s': ('Bambu Lab P1S 0.4 nozzle', '0.20mm Standard @BBL X1C', 'Generic PLA', 256, 256),
    'x1c': ('Bambu Lab X1 Carbon 0.4 nozzle', '0.20mm Standard @BBL X1C', 'Generic PLA', 256, 256),
    'a1': ('Bambu Lab A1 0.4 nozzle', '0.20mm Standard @BBL A1', 'Generic PLA @BBL A1', 256, 256),
    'a1mini': ('Bambu Lab A1 mini 0.4 nozzle', '0.20mm Standard @BBL A1M', 'Generic PLA @BBL A1M', 180, 180),
}
MARGIN, GAP = 12.0, 12.0  # model envelopes; native support/toolpath validation is separate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def settings(pid):
    density = 35 if pid.startswith('chassis_') or pid == 'rear_wing' else 25
    if pid.startswith(('splice_', 'bearing_spacer_')) or pid == 'fit_coupon': density = 100
    if pid.startswith('motor_'): density = 50
    if pid.startswith('front_wheel_'): density = 40
    support = pid.startswith(('shell_', 'chassis_')) or pid in ('canopy', 'rear_wing')
    return {'wall_loops': '4', 'top_shell_layers': '5', 'bottom_shell_layers': '5',
            'sparse_infill_density': f'{density}%',
            # Bambu calls its Rectilinear enum "zig-zag", not "rectilinear".
            # The latter is substituted on import and changes the intended recipe.
            'sparse_infill_pattern': 'zig-zag' if density == 100 else 'gyroid',
            'enable_support': '1' if support else '0', 'support_type': 'tree(auto)',
            'support_on_build_plate_only': '1', 'support_threshold_angle': '30',
            'brim_type': 'outer_only', 'brim_width': '4', 'brim_object_gap': '0.15'}


def load_parts(manifest):
    coupon = {'id': 'fit_coupon', 'name': '00 · 先打印公差试片', 'file': 'print/00_fit_coupon.stl',
              'sha256': sha(BUILD / 'print/00_fit_coupon.stl')}
    result = []
    for part in [coupon] + manifest['printParts']:
        path = BUILD / part['file']
        if sha(path) != part['sha256']: raise ValueError('Source mesh hash changed: ' + part['id'])
        mesh = trimesh.load_mesh(path, process=True)
        if not mesh.is_watertight or mesh.volume <= 0: raise ValueError('Invalid mesh: ' + part['id'])
        mesh.apply_translation(-mesh.bounds[0])
        result.append({**part, 'mesh': mesh, 'colour': 'red' if part['id'].startswith('shell_') else 'black',
                       'settings': settings(part['id'])})
    return result


def pack(parts, width, depth):
    """First-fit decreasing shelf pack. Coupon is always its own first plate."""
    plates = []
    for group in ([parts[0]], [p for p in parts[1:] if p['colour'] == 'black'],
                  [p for p in parts[1:] if p['colour'] == 'red']):
        group_plates = []
        for part in sorted(group, key=lambda p: (-max(p['mesh'].extents[:2]), p['id'])):
            chosen = None
            for plate in group_plates:
                for angle in (0, 90):
                    w, d = part['mesh'].extents[:2][::(-1 if angle else 1)]
                    for row in plate['rows']:
                        if row['x'] + w <= width-MARGIN and d <= row['height']:
                            chosen = plate, row, float(w), float(d), angle; break
                    if chosen: break
                    y = max((r['y']+r['height']+GAP for r in plate['rows']), default=MARGIN)
                    if w <= width-2*MARGIN and y+d <= depth-MARGIN:
                        row = {'x': MARGIN, 'y': y, 'height': float(d)}
                        plate['rows'].append(row); chosen = plate, row, float(w), float(d), angle; break
                if chosen: break
            if chosen is None:
                w, d = map(float, part['mesh'].extents[:2])
                if w > width-2*MARGIN or d > depth-2*MARGIN: raise ValueError('Part exceeds bed: '+part['id'])
                row = {'x': MARGIN, 'y': MARGIN, 'height': d}
                plate = {'colour': part['colour'], 'rows': [row], 'parts': []}
                group_plates.append(plate); chosen = plate, row, w, d, 0
            plate, row, w, d, angle = chosen
            plate['parts'].append({**part, 'x': row['x'], 'y': row['y'], 'width': w, 'depth': d, 'angle': angle})
            row['x'] += w+GAP
        plates.extend(group_plates)
    for i, plate in enumerate(plates):
        plate['index'] = i+1
        plate['title'] = '00 · 公差试片 / 黑 PLA' if i == 0 else f'{i:02d} · {"红色外壳" if plate["colour"] == "red" else "黑色结构件"}'
        # Centre occupied model bounds; equal spare room for brims and supports.
        right = max(p['x']+p['width'] for p in plate['parts'])
        top = max(p['y']+p['depth'] for p in plate['parts'])
        dx, dy = (width-right-MARGIN)/2, (depth-top-MARGIN)/2
        for p in plate['parts']: p['x'] += dx; p['y'] += dy
    return plates


def xml_bytes(root):
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def meta(root, key, value):
    ET.SubElement(root, 'metadata', key=key, value=str(value))


def project(path, plates, profile, width, depth):
    ET.register_namespace('', CORE)
    model = ET.Element('model', {'unit': 'millimeter', 'xmlns': CORE,
        'xmlns:BambuStudio': 'http://schemas.bambulab.com/package/2021',
        'xmlns:p':PRODUCTION, 'requiredextensions':'p'})
    for k,v in [('Application','BambuStudio-02.08.02.61'), ('BambuStudio:3mfVersion','1'),
                ('Title','ECHO F1 CN V2 / arranged, unsliced'), ('Designer','M4KE'), ('License','MIT')]:
        ET.SubElement(model, 'metadata', name=k).text = v
    resources, build = ET.SubElement(model, 'resources'), ET.SubElement(model, 'build')
    config = ET.Element('config')
    children = {}
    subrels = ET.Element('Relationships',xmlns=RELS)
    cols = math.ceil(math.sqrt(len(plates)))
    oid = 0
    for plate in plates:
        pi = plate['index']-1
        ox, oy = pi % cols * width * 1.2, -(pi//cols) * depth * 1.2
        pc = ET.SubElement(config, 'plate')
        native_title='00 - FIT COUPON - BLACK PLA' if pi==0 else f'{pi:02d} - {plate["colour"].upper()} PLA'
        meta(pc, 'plater_id', pi+1); meta(pc, 'plater_name', native_title); meta(pc, 'locked', 'false')
        for p in plate['parts']:
            oid += 1
            mesh = p['mesh'].copy()
            if p['angle']:
                mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, [0,0,1]))
                mesh.apply_translation(-mesh.bounds[0])
            # Stable ASCII slicer IDs avoid legacy Windows codepage corruption.
            # The app and handbook provide the Chinese name beside each ID.
            # Mirror a native Bambu project: build items point to component
            # objects; actual meshes live in referenced production-extension parts.
            # This keeps component/part IDs consistent with native project exports.
            mesh_id,object_id=oid*2-1,oid*2
            child_path=f'3D/Objects/object_{oid}.model'
            object_uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'm4ke/cn-v2/r2/{p["id"]}/object'))
            component_uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'm4ke/cn-v2/r2/{p["id"]}/component'))
            obj = ET.SubElement(resources, 'object', id=str(object_id), type='model', **{'p:UUID':object_uuid})
            components=ET.SubElement(obj,'components')
            ET.SubElement(components,'component',objectid=str(mesh_id),
                transform='1 0 0 0 1 0 0 0 1 0 0 0',**{'p:path':'/'+child_path,'p:UUID':component_uuid})
            child=ET.Element('model',{'unit':'millimeter','xmlns':CORE,
                'xmlns:BambuStudio':'http://schemas.bambulab.com/package/2021','xmlns:p':PRODUCTION,'requiredextensions':'p'})
            ET.SubElement(child,'metadata',name='BambuStudio:3mfVersion').text='1'
            child_resources=ET.SubElement(child,'resources')
            mesh_object=ET.SubElement(child_resources,'object',id=str(mesh_id),type='model',name=p['id'],**{'p:UUID':str(uuid.uuid5(uuid.NAMESPACE_URL,f'm4ke/cn-v2/r2/{p["id"]}/mesh'))})
            geom = ET.SubElement(mesh_object, 'mesh'); vertices = ET.SubElement(geom, 'vertices')
            for v in mesh.vertices: ET.SubElement(vertices, 'vertex', **dict(zip(('x','y','z'),map(lambda n:format(n,'.9g'),v))))
            triangles = ET.SubElement(geom, 'triangles')
            for f in mesh.faces: ET.SubElement(triangles, 'triangle', **dict(zip(('v1','v2','v3'),map(str,f))))
            ET.SubElement(child,'build')
            children[child_path]=xml_bytes(child)
            ET.SubElement(subrels,'Relationship',Target='/'+child_path,Id=f'rel-{oid}',Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
            ET.SubElement(build, 'item', objectid=str(object_id), transform=f'1 0 0 0 1 0 0 0 1 {p["x"]+ox:.8f} {p["y"]+oy:.8f} 0', printable='1')
            oc = ET.SubElement(config, 'object', id=str(object_id))
            for k,v in {'name':p['id'], 'extruder':'1', **p['settings']}.items(): meta(oc,k,v)
            ET.SubElement(oc, 'metadata', face_count=str(len(mesh.faces)))
            volume = ET.SubElement(oc, 'part', id=str(mesh_id), subtype='normal_part',uuid=component_uuid)
            meta(volume,'name',p['id']); meta(volume,'source_file',Path(p['file']).name)
            meta(volume,'matrix','1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')
            ET.SubElement(volume,'mesh_stat',face_count=str(len(mesh.faces)),edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
            instance = ET.SubElement(pc,'model_instance')
            meta(instance,'object_id',object_id); meta(instance,'instance_id',0); meta(instance,'identify_id',oid)
    types = ET.Element('Types', xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
    for ext,ct in [('rels','application/vnd.openxmlformats-package.relationships+xml'),
                   ('model','application/vnd.ms-package.3dmanufacturing-3dmodel+xml'),('config','application/xml')]:
        ET.SubElement(types,'Default',Extension=ext,ContentType=ct)
    rels = ET.Element('Relationships',xmlns=RELS)
    ET.SubElement(rels,'Relationship',Target='/3D/3dmodel.model',Id='rel-1',Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',xml_bytes(types)); z.writestr('_rels/.rels',xml_bytes(rels))
        z.writestr('3D/3dmodel.model',xml_bytes(model)); z.writestr('Metadata/model_settings.config',xml_bytes(config))
        z.writestr('3D/_rels/3dmodel.model.rels',xml_bytes(subrels))
        for child_path,contents in children.items():z.writestr(child_path,contents)
        z.writestr('Metadata/project_settings.config',json.dumps(profile,ensure_ascii=False))
    return sha(path)


def svg_preview(path, plate, width, depth):
    items=[]
    for n,p in enumerate(plate['parts'],1):
        mesh=p['mesh'].copy()
        if p['angle']:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[0,0,1]));mesh.apply_translation(-mesh.bounds[0])
        xy=np.unique(mesh.vertices[:,:2],axis=0)
        outline=xy[ConvexHull(xy).vertices]
        points=' '.join(f'{x+p["x"]:.2f},{depth-y-p["y"]:.2f}' for x,y in outline)
        items.append(f'<polygon points="{points}" fill="{"#e75065" if plate["colour"]=="red" else "#637b9b"}" stroke="#c2d2e3" stroke-width="0.5"/>')
        items.append(f'<text x="{p["x"]+p["width"]/2:.2f}" y="{depth-p["y"]-p["depth"]/2:.2f}" text-anchor="middle" fill="white" font-family="sans-serif" font-size="8">{n:02d}</text>')
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {depth}" role="img"><title>{html.escape(plate["title"])}</title><rect width="{width}" height="{depth}" rx="6" fill="#111b29"/><rect x="12" y="12" width="{width-24}" height="{depth-24}" fill="none" stroke="#566b82" stroke-dasharray="2 2"/>{"".join(items)}</svg>',encoding='utf8')


def generate(slicer_root):
    # Import profile resolver only; no installed() lookup, no user settings modification.
    from bambu_handoff import Profiles
    profiles=Profiles(slicer_root)
    manifest=json.loads((BUILD/'manifest.json').read_text(encoding='utf8'))
    parts=load_parts(manifest); destination=BUILD/'plates';destination.mkdir(exist_ok=True)
    plans=[]
    for key,(machine,process,filament,w,d) in TARGETS.items():
        lineage={};resolved={}
        for kind,name in [('machine',machine),('process',process),('filament',filament)]:
            lineage[kind]=[];resolved[kind]=profiles.resolve(kind,name,lineage=lineage[kind])
        settings_all={**resolved['machine'],**resolved['process'],**resolved['filament']}
        settings_all.update(printer_settings_id=machine,print_settings_id=process,filament_settings_id=[filament],
            printer_model=resolved['machine']['printer_model'],printer_variant='0.4',
            curr_bed_type='Textured PEI Plate',filament_colour=['#252934'],filament_type=['PLA'],
            print_sequence='by layer',enable_prime_tower='0',layer_height='0.2',wall_loops='4',
            top_shell_layers='5',bottom_shell_layers='5',brim_width='4',brim_type='outer_only')
        # Source-record fields aren't slicer settings. Keep machine identity, not last-merged filament identity.
        for k in ['name','type','from','instantiation','setting_id','inherits','include']:settings_all.pop(k,None)
        # Preset files describe supported nozzle variants, not project filament
        # slots. All variants here belong to our ONE manually changed PLA slot.
        # Bambu's GUI PresetBundle::load_config_file_config rejects a missing or
        # mismatched self-index map; the CLI alone does not catch this failure.
        variants = settings_all.get('filament_extruder_variant', [])
        if settings_all.get('extruder_variant_list'):
            if not variants: raise ValueError('Missing filament variant map: '+machine)
            settings_all['filament_self_index'] = ['1'] * len(variants)
        else:
            settings_all['filament_self_index'] = ['1']
        settings_all.update(name='project_settings', **{'from':'project'}, version='02.08.02.61',
            print_compatible_printers=[machine], inherits_group=['','',''],
            different_settings_to_system=['brim_type;brim_width;bottom_shell_layers;enable_prime_tower;layer_height;top_shell_layers;wall_loops','',''])
        # This project-level option is a scalar even where a preset stores ["2"].
        long_retraction=settings_all.get('enable_long_retraction_when_cut')
        if isinstance(long_retraction,list):
            if len(set(long_retraction))!=1:raise ValueError('Ambiguous long-retraction setting')
            settings_all['enable_long_retraction_when_cut']=long_retraction[0]
        # Respect the shipped machine profile, including H2C's nozzle reach.
        machine_area=np.array([list(map(float,xy.split('x'))) for xy in resolved['machine']['printable_area']])
        w,d=machine_area.max(axis=0)
        usable_min,usable_max=machine_area.min(axis=0),machine_area.max(axis=0)
        for area in resolved['machine'].get('extruder_printable_area',[]):
            points=np.array([list(map(float,xy.split('x'))) for xy in area.split(',')])
            usable_min=np.maximum(usable_min,points.min(axis=0));usable_max=np.minimum(usable_max,points.max(axis=0))
        exclusion=resolved['machine'].get('bed_exclude_area',[])
        if exclusion:
            # Conservative front strip, not a hand-waved exclusion-zone collision pass.
            usable_min[1]=max(usable_min[1],max(float(xy.split('x')[1]) for xy in exclusion))
        plates=pack(parts,*(usable_max-usable_min))
        for plate in plates:
            for piece in plate['parts']:piece['x']+=float(usable_min[0]);piece['y']+=float(usable_min[1])
        file=f'plates/ECHO-F1-CN-v2-{key}-0.4-PLA-r2.3mf'
        digest=project(BUILD/file,plates,settings_all,w,d)
        rows=[]
        for p in plates:
            preview=f'plates/{key}-plate-{p["index"]:02d}.svg'
            svg_preview(BUILD/preview,p,w,d)
            rows.append({k:v for k,v in p.items() if k not in ('rows','parts')} | {
                'preview':preview,'sha256Preview':sha(BUILD/preview),
                'parts':[{k:v for k,v in piece.items() if k!='mesh'} for piece in p['parts']]})
        plans.append({'id':key,'label':machine.replace(' 0.4 nozzle',''),'machine':machine,
            'file':file,'sha256':digest,'bedMm':[float(w),float(d)],'packingAreaMm':[usable_min.tolist(),usable_max.tolist()],'nozzleMm':0.4,'bedType':'Textured PEI Plate',
            'status':'ARRANGED_UNSLICED','nativeValidation':'NOT_RUN','plates':rows,
            'profileSources':{kind:[{'name':r['name'],'sha256':r['sha256']} for r in trace] for kind,trace in lineage.items()}})
    result={'schemaVersion':1,'artifactRevision':2,'status':'ARRANGED_UNSLICED','printerConnected':False,'printSent':False,
        'sourcePrintHashes':{p['id']:p['sha256'] for p in parts},'projects':plans,
        'notes':['只有打印件和试片；不含电子元件参考模型。','按颜色分盘；使用单个料槽，每盘开打前手动装对应颜色，无需AMS。',
                 '没有G-code。打开为工程，选实际喷嘴、耗材和热床，再切片检查；不要直接发送。',
                 '12mm模型边距、12mm模型间距；避开预设禁区并取双喷头可达区域交集；支撑与裙边仍需切片检查。']}
    write_json(destination/'print-plan.json',result)
    print(json.dumps({'projects':len(plans),'plateCounts':{p['id']:len(p['plates']) for p in plans},'printSent':False}))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--slicer-root',required=True)
    args=parser.parse_args();generate(Path(args.slicer_root))
