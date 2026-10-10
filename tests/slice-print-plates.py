"""Local native-import checks plus an optional all-plate slice; never print.

Use --slicer for an ordinary Bambu CLI. A separately provisioned Windows DLL
host may be supplied with --entry (the upstream wchar_t main entry point).
All G-code stays in .setup, not in the beginner's downloadable build package.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,xml.etree.ElementTree as E,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'builds/echo-f1-cn-v2'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--slicer',required=True);parser.add_argument('--entry')
parser.add_argument('--slice',default='h2c',dest='slice_id');parser.add_argument('--run',default='native-final')
args=parser.parse_args()
plan=json.loads((OUT/'plates/print-plan.json').read_text(encoding='utf8'))
records=[]
for project in plan['projects']:
    job=ROOT/'.setup/plate-validation'/args.run/project['id'];job.mkdir(parents=True,exist_ok=True)
    source=OUT/project['file'];source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash==project['sha256']
    command=[str(Path(args.slicer).resolve())]
    if args.entry:command.append(str(Path(args.entry).resolve()))
    command += ['--datadir',str(ROOT/'.setup/bambu-print-profile'),'--debug','2','--orient','0','--arrange','0',
                '--outputdir',str(job),'--info','--export-3mf','roundtrip.3mf',str(source)]
    run=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (job/'import.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode==0 and (job/'roundtrip.3mf').is_file(),f'{project["id"]}: native import failed'
    with zipfile.ZipFile(job/'roundtrip.3mf') as z:
        meta=E.fromstring(z.read('Metadata/model_settings.config'))
        objects=meta.findall('object');plates=meta.findall('plate')
        assert len(objects)==19 and len(plates)==len(project['plates'])
        names={o.find('metadata[@key="name"]').attrib['value'] for o in objects}
        assert names==set(plan['sourcePrintHashes']), (project['id'],names)
        # Verify native per-object settings survived, not merely object counts.
        for obj in objects:
            values={m.attrib.get('key'):m.attrib.get('value') for m in obj.findall('metadata')}
            assert values['wall_loops']=='4'
            assert values['sparse_infill_pattern'] in ('zig-zag','gyroid'),'Native import must not substitute the authored infill pattern'
            if values['sparse_infill_density']=='100%':assert values['sparse_infill_pattern']=='zig-zag'
            if values['name'].startswith('shell_'):assert values['enable_support']=='1'
    record={'id':project['id'],'inputSha256':source_hash,'nativeImport':'PASSED',
            'objects':19,'plates':len(plates),'sliceStatus':'NOT_RUN','printSent':False}
    project['nativeValidation']='IMPORTED'
    if project['id']==args.slice_id:
        slicing=[*command[:-4],'--slice','0','--mstpp','180',str(source)]
        # command's last four are --info, --export-3mf, filename, input.
        run=subprocess.run(slicing,cwd=ROOT,capture_output=True,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        log=run.stdout+run.stderr;(job/'slice.log').write_bytes(log)
        native=json.loads((job/'result.json').read_text(encoding='utf8'))
        assert run.returncode==0 and native['return_code']==0 and len(native.get('sliced_plates',[]))==len(plates)
        assert sum(len(p['objects']) for p in native['sliced_plates'])==19
        assert all(p.get('filament_change_times',0)==0 for p in native['sliced_plates'])
        warnings=sorted(set(re.findall(r'Invalid T command \(T\d+\)',log.decode('utf8',errors='replace'))))
        stats=[]
        for p in native['sliced_plates']:
            gcode=job/f'plate_{p["id"]}.gcode';assert gcode.is_file() and gcode.stat().st_size>1000
            stats.append({'plate':p['id'],'objects':len(p['objects']),
                          'estimatedGrams':sum(f['total_used_g'] for f in p['filaments']),
                          'estimatedSeconds':p.get('total_predication'),'gcodeSha256':hashlib.sha256(gcode.read_bytes()).hexdigest()})
        record.update(sliceStatus='COMPLETED_WITH_WARNINGS' if warnings else 'COMPLETED',warnings=warnings,plateEstimates=stats)
        project['nativeValidation']='SLICED_WITH_WARNINGS' if warnings else 'PASSED'
        project['sliceSummary']={'estimatedGrams':round(sum(s['estimatedGrams'] for s in stats),1),
                                 'estimatedHours':round(sum(s['estimatedSeconds'] for s in stats)/3600,1),
                                 'warnings':warnings,'estimatesNotMeasurements':True}
    records.append(record)
    print(json.dumps(record,ensure_ascii=False),flush=True)
Path(OUT/'checks/print-plates-native.json').write_text(json.dumps({'engine':'BambuStudio 02.08.02.61','printSent':False,'records':records},ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'plates/print-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
