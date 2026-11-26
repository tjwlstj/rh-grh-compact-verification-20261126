"""Resume an intact local Windows source build, preserving its receipts and AppContainer."""
from datetime import datetime,timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
RECEIPTS=ROOT/'receipts'
MANIFEST_SHA='3057c5f652feecd0b9474a7c75b7cfa01b7011d85276af67417b87e55edbfb29'

def checksum(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()

def running():
    with (RECEIPTS/'worker.lock').open('r+b') as lock:
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return True
        msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
        return False

def recover_tail(path,tag):
    raw=path.read_bytes()
    if not raw or raw.endswith(b'\n'):return
    head,delimiter,tail=raw.rpartition(b'\n')
    if not delimiter:raise ValueError('No complete local receipt precedes the interrupted write')
    for line in head.splitlines():json.loads(line)
    try:record=json.loads(tail)
    except (ValueError,UnicodeError):record=None
    complete=raw+b'\n' if isinstance(record,dict) and 'utc' in record else head+b'\n'
    # Keep all original bytes, even if the final receipt was cut in the middle.
    backup=path.with_name(path.name+'.interrupted-'+tag)
    with backup.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    temp=path.with_name(path.name+'.repair-'+tag)
    with temp.open('xb') as f:f.write(complete);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
    print('Interrupted final receipt preserved as',backup.name)

def launch(script,args,tag):
    with (RECEIPTS/(tag+'.out')).open('xb') as out,(RECEIPTS/(tag+'.err')).open('xb') as err:
        return subprocess.Popen([sys.executable,'-I','-B','-X','utf8',str(ROOT/script),*args],cwd=ROOT,
                                stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)

def main():
    if not (RECEIPTS/'worker.lock').exists():raise SystemExit('This command needs the original local build directory and receipt files.')
    if running():print('Existing source worker holds its lock. No new process was started.');return
    if (RECEIPTS/'restart-at-boundary.request').exists():raise SystemExit('A prior controller handoff request is still present. Check its local history before resuming.')
    if (RECEIPTS/'source-terminal.json').exists():
        result=json.loads((RECEIPTS/'source-terminal.json').read_bytes())
        if result.get('sourceMainBuilt') and result.get('solution',{}).get('receiptMatchesFile'):
            print('Full compiled source and its export are already recorded. See the terminal receipt.');return
    manifest=HERE/'checkpoint-manifest.json'
    if checksum(manifest)!=MANIFEST_SHA:raise ValueError('Public checkpoint manifest digest differs')
    checkpoint=json.loads(manifest.read_bytes())
    for row in checkpoint['modules']:
        if checksum(ROOT/row['source'])!=row['sourceSha256']:raise ValueError(('source differs',row['module']))
        for item in row['artifacts'].values():
            file=ROOT/item['path']
            if file.stat().st_size!=item['bytes'] or checksum(file)!=item['sha256']:raise ValueError(('checkpoint artifact differs',row['module']))
    tag='resume-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    with (RECEIPTS/'worker.lock').open('r+b') as lock:
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:print('Another source worker acquired the lock. No new process was started.');return
        for name in ['modules.jsonl','worker.jsonl']:recover_tail(RECEIPTS/name,tag)
    worker=launch('compile_compact.py',[],tag+'-compile')
    for _ in range(120):
        if worker.poll() is not None:raise SystemExit('The new worker exited before starting. Read its local stderr.')
        log=(RECEIPTS/'worker.jsonl').read_bytes().split(b'\n')[:-1]
        if any(r.get('state')=='worker started' and r.get('pid')==worker.pid for r in map(json.loads,log[-24:])):break
        time.sleep(.25)
    else:raise SystemExit('The worker has no confirmed startup receipt. No terminal watcher was attached.')
    finishing=launch('finish_source.py',['--pid',str(worker.pid)],tag+'-finish')
    print(f'Source PID {worker.pid}, terminal observer PID {finishing.pid}. Source and export verdicts require actual terminal receipts.')

if __name__=='__main__':main()
