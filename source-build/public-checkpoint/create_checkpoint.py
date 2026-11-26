"""Read and hash the first 200 completed source-build receipts. Copy no proof or command data."""
import csv
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
BUILD=HERE.parent
COUNT=200
REV='72fead102f663d5c7a407964a13dc0cf9d977207'

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    # Split at LF so a simultaneous append can never become a checkpoint entry.
    prefix=(BUILD/'receipts/modules.jsonl').read_bytes().split(b'\n')[:-1][:COUNT]
    assert len(prefix)==COUNT
    plan=json.loads((BUILD/'source-order.json').read_bytes())
    published={r['module']:r['sha256'] for r in csv.DictReader((BUILD.parent/'cached-data/oleans.csv').open(encoding='utf8')) if r['relative_path'].endswith('.olean')}
    results=[];seen=set();privacy={}
    login_segment=Path.home().name
    identities=['local-account-component','Windows-user-root','Unix-home-root','drive-absolute-path','file-uri','workspace-component']
    patterns=[re.compile(re.escape(login_segment.encode()),re.I),re.compile(rb'(?i)(?:\\+|/)users(?:\\+|/)'),re.compile(rb'/(?:home|Users|mnt/[a-z])/'),re.compile(rb'(?i)(?<![a-z0-9])[a-z]:(?:\\+|/)[a-z0-9_.-]'),re.compile(rb'(?i)file://'),re.compile(rb'(?i)(?:documents(?:\\+|/)codex|rh-reduced(?:\\+|/)source-build)')]
    for raw in prefix:
        row=json.loads(raw);name=row['module'];assert name in plan['imports'] and name not in seen and re.fullmatch(r'[\w]+(?:\.[\w]+)*',name)
        assert row['appContainer'] is True and row['exit']==row['wrapperExit']==0 and not row['separateChallenge']
        assert (set(plan['imports'][name])&plan['imports'].keys())<=seen
        seen.add(name);rel=Path(*name.split('.'));source=(BUILD/'compact/src'/rel).with_suffix('.lean')
        assert digest(source)==row['sourceSha256']
        cmd=(BUILD/'commands'/(row['tag']+'.log'));events=[json.loads(s) for s in cmd.read_bytes().splitlines()]
        argv=events[0]['argv'];assert events[0]['caps']==0 and events[-1]['exit']==0 and any(e.get('appContainer')==1 for e in events)
        assert Path(argv[0])==BUILD/'lean-4.35.0-windows/bin/lean.exe' and Path(argv[-1])==source
        setup=Path(argv[argv.index('--setup')+1]);assert digest(setup)==row['setupSha256'] and json.loads(setup.read_bytes())['name']==name
        artifacts={}
        for suf,info in row['artifacts'].items():
            assert suf in {'.olean','.ilean','.olean.private','.olean.server','.ir'}
            f=BUILD/'verified-lib'/(rel.as_posix()+suf);data=f.read_bytes();h=hashlib.sha256(data).hexdigest()
            assert h==info['sha256'] and len(data)==info['bytes'];artifacts[suf]={'path':f.relative_to(BUILD).as_posix(),'bytes':len(data),'sha256':h}
            # Search byte strings and Windows UTF-16 LE/BE strings. Publish only match classes/counts.
            classes=set()
            for chunk in (data,data.replace(b'\0',b'')):
                if not chunk:continue
                for label,pat in zip(identities,patterns):
                    if label not in classes and pat.search(chunk):classes.add(label)
            for label in classes:
                counts=privacy.setdefault(suf,{});counts[label]=counts.get(label,0)+1
        assert '.olean' in artifacts
        results.append({'module':name,'source':source.relative_to(BUILD).as_posix(),'sourceSha256':row['sourceSha256'],'setupSha256':row['setupSha256'],
                        'artifacts':artifacts,'publicCacheOleanSha256':published[name],'publicCacheBytesMatch':artifacts['.olean']['sha256']==published[name]})
    output={'format':'compact-source-checkpoint-v1','gitRevision':REV,'edition':'grh-compact','cutoffUtc':json.loads(prefix[-1])['utc'],
            'expectedModules':len(plan['order']),'completedModules':len(seen),'sourceMainBuilt':False,'rawExportAlreadyMatched':'challenge only',
            'compilerRelease':json.loads((BUILD/'official-tool.json').read_bytes()),'dependencyPins':json.loads((BUILD/'official-pins.json').read_bytes()),
            'sourceImportPlanSha256':digest(BUILD/'source-order.json'),'publishedCacheIdenticalCount':sum(r['publicCacheBytesMatch'] for r in results),
            'pathMarkerFilesByArtifactSuffix':privacy,'binaryPayloadIncluded':False,'modules':results}
    dest=HERE/'checkpoint-manifest.json';dest.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({'modules':len(seen),'matches':output['publishedCacheIdenticalCount'],'markers':privacy,'manifest':digest(dest),'bytes':dest.stat().st_size}))

if __name__=='__main__':main()
