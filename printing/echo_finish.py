"""Apply an appearance-only finish and split existing H2C plates by PLA recipe.

No new geometry, scale changes, G-code, printer connections or print commands.
The generic R2 projects remain untouched. Re-run after regenerating R2 plates.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile

from bambu_handoff import Profiles

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'builds/echo-f1-cn-v2'
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS = {'m': CORE}
WHITE, EMBER = '#F1EFE9', '#983C40'
SHELLS = {'shell_front', 'shell_rear'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')


def metadata(element, key):
    return element.find(f'metadata[@key="{key}"]')


def split_project(source, destination, selected_plates, filament, colour, profiles):
    """Copy native mesh bytes, change only plate placement and material recipe."""
    ET.register_namespace('', CORE)
    ET.register_namespace('p', PROD)
    with zipfile.ZipFile(source) as z:
        data = {name: z.read(name) for name in z.namelist()}
    model = ET.fromstring(data['3D/3dmodel.model'])
    model.set('xmlns:BambuStudio', 'http://schemas.bambulab.com/package/2021')
    # Preserve extension prefixes used as strings in requiredextensions.
    model.set('xmlns:p', PROD) if not any(k.startswith('{'+PROD+'}') for e in model.iter() for k in e.attrib) else None
    config = ET.fromstring(data['Metadata/model_settings.config'])
    profile = json.loads(data['Metadata/project_settings.config'])
    selected = set(selected_plates)
    kept_ids, original_indices = set(), []
    for plate in list(config.findall('plate')):
        original_index = int(metadata(plate, 'plater_id').attrib['value'])
        if original_index not in selected:
            config.remove(plate)
            continue
        original_indices.append(original_index)
        for instance in plate.findall('model_instance'):
            kept_ids.add(metadata(instance, 'object_id').attrib['value'])
        metadata(plate, 'plater_id').set('value', str(len(original_indices)))
        metadata(plate, 'plater_name').set('value', f'{original_index:02d} - '+('EMBER SILK BODY - AMS A1' if filament.find('Silk') >= 0 else 'WHITE BASIC - AMS A4'))
    for obj in list(config.findall('object')):
        if obj.attrib['id'] not in kept_ids:
            config.remove(obj)
    resources = model.find('m:resources', NS)
    kept_paths = set()
    for obj in list(resources):
        if obj.attrib.get('id') not in kept_ids:
            resources.remove(obj)
        else:
            for c in obj.findall('m:components/m:component', NS):
                kept_paths.add(c.attrib['{'+PROD+'}path'].lstrip('/'))
    items = model.find('m:build', NS)
    for item in list(items):
        if item.attrib['objectid'] not in kept_ids:
            items.remove(item)
        elif selected == {4}:
            # Original R2 four-plate layout uses two columns (330 x 320 mm).
            transform = list(map(float, item.attrib['transform'].split()))
            transform[9] -= 396
            transform[10] += 384
            item.set('transform', ' '.join(format(v, '.8g') for v in transform))
    for title in model.findall('m:metadata', NS):
        if title.attrib.get('name') == 'Title':
            title.text = 'ECHO F1 / EMBER x WHITE / ' + ('BODY' if selected == {4} else 'STRUCTURE')
    rels = ET.fromstring(data['3D/_rels/3dmodel.model.rels'])
    for rel in list(rels):
        if rel.attrib['Target'].lstrip('/') not in kept_paths:
            rels.remove(rel)
    lineage = []
    resolved = profiles.resolve('filament', filament, lineage=lineage)
    profile.update({k: v for k, v in resolved.items() if k not in {'name', 'type', 'from', 'instantiation', 'setting_id', 'inherits', 'include'}})
    profile.update(filament_settings_id=[filament], filament_colour=[colour],
                   name='project_settings', **{'from': 'project'})
    variants = profile.get('filament_extruder_variant', [])
    profile['filament_self_index'] = ['1'] * max(1, len(variants))
    retract = profile.get('enable_long_retraction_when_cut')
    if isinstance(retract, list):
        assert len(set(retract)) == 1
        profile['enable_long_retraction_when_cut'] = retract[0]
    xml = lambda e: ET.tostring(e, encoding='utf-8', xml_declaration=True)
    # Bambu's relationship reader expects an unprefixed Relationships root.
    ET.register_namespace('', REL)
    relationships_xml = xml(rels)
    ET.register_namespace('', CORE)
    data.update({'3D/3dmodel.model': xml(model), 'Metadata/model_settings.config': xml(config),
                 '3D/_rels/3dmodel.model.rels': relationships_xml,
                 'Metadata/project_settings.config': json.dumps(profile, ensure_ascii=False).encode('utf8')})
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, raw in data.items():
            if name.startswith('3D/Objects/') and name not in kept_paths:
                continue
            assert not name.endswith('.gcode')
            z.writestr(name, raw)
    with zipfile.ZipFile(destination) as z, zipfile.ZipFile(source) as original:
        assert z.testzip() is None
        assert all(z.read(name) == original.read(name) for name in kept_paths)
    ids = [metadata(obj, 'name').attrib['value'] for obj in config.findall('object')]
    return dict(file=destination.relative_to(OUT).as_posix(), sha256=digest(destination.read_bytes()),
                partIds=ids, originalPlates=original_indices, filament=filament,
                status='GEOMETRY_CHECKED_UNSLICED', profileSources=[{'name': p['name'], 'sha256': p['sha256']} for p in lineage])


def apply(manifest, profiles):
    plan = manifest['printPlan']
    h2c = next(p for p in plan['projects'] if p['id'] == 'h2c')
    source = OUT / h2c['file']
    assert digest(source.read_bytes()) == h2c['sha256']
    assert h2c['bedMm'] == [330.0, 320.0] and len(h2c['plates']) == 4
    assert {p['id'] for p in h2c['plates'][3]['parts']} == SHELLS
    original_meshes = {p['id']: p['sha256'] for p in manifest['printParts']}
    for part in manifest['parts']:
        if part['kind'] != 'printed':
            continue
        part['color'] = EMBER if part['id'] in SHELLS else WHITE
        part['displayFinish'] = 'silk' if part['id'] in SHELLS else 'standard'
    white = split_project(source, OUT/'plates/ECHO-F1-CN-v2-h2c-WHITE-STRUCTURE-r2.3mf',
                          [1, 2, 3], 'Bambu PLA Basic @BBL H2C', WHITE, profiles)
    ember = split_project(source, OUT/'plates/ECHO-F1-CN-v2-h2c-EMBER-BODY-r2.3mf',
                          [4], 'Bambu PLA Silk @BBL H2C 0.4 nozzle', EMBER, profiles)
    white.update(label='第 1–3 盘 · 冰白结构', slot='A4', colour='白色', printerId='h2c',
                 note='试片已打过时不要重复打印。底盘、电机座、轮圈、前后翼均用 PLA Basic。')
    ember.update(label='第 4 盘 · 灰烬红车壳', slot='A1', colour='灰烬红双色', printerId='h2c',
                 note='此文件内只有一盘，对应原工程第 4 盘。使用 PLA Silk，不用 Basic 预设。')
    assert set(white['partIds']).isdisjoint(ember['partIds'])
    assert set(white['partIds'] + ember['partIds']) == set(plan['sourcePrintHashes'])
    assert len(white['partIds'] + ember['partIds']) == 19
    manifest['appearance'] = {
        'id': 'ember-white-v1', 'title': '灰烬红 × 冰白',
        'summary': '红黑双色车壳，冰白前后翼与轮圈，黑色橡胶轮胎。',
        'previewNote': '外壳用灰烬红代表色预览；丝绸双色会随观察方向和打印方向变化，不是精确色样。',
        'palette': [{'name': '灰烬红 · A1 / PLA Silk', 'color': EMBER},
                    {'name': '冰白 · A4 / PLA Basic', 'color': WHITE},
                    {'name': '黑色 · 采购橡胶轮胎', 'color': '#1B1C20'}],
        'rules': ['白色用于所有承力打印件；丝绸料只用于前后车壳。',
                  '支撑专用料不拿来打印车身；槽位编号不能代替料卷标签确认，无需购买黑色耗材。',
                  '不缩放、不改孔位；19 个打印对象的几何与 R2 完全相同。',
                  '两份工程按材料分开，避免新手把整车误打成同一种颜色。',
                  'A4 白色、A1 车壳仅为历史示例；同步实际打印机后，按实装材料映射槽位并重新切片。'],
        'artifacts': [white, ember], 'geometryUnchanged': True,
        'sourcePrintHashes': deepcopy(plan['sourcePrintHashes']), 'printSent': False,
    }
    assert {p['id']: p['sha256'] for p in manifest['printParts']} == original_meshes
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slicer-root', default='C:/Program Files/Bambu Studio')
    args = parser.parse_args()
    manifest = json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
    manifest = apply(manifest, Profiles(args.slicer_root))
    json_write(OUT/'manifest.json', manifest)
    json_write(OUT/'checks/appearance.json', manifest['appearance'])
    print(json.dumps({'appearance': manifest['appearance']['title'], 'artifacts': manifest['appearance']['artifacts'], 'printSent': False}, ensure_ascii=False))
