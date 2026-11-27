"""Run the unchanged Lean reader inside an already prepared isolated environment."""
import argparse
import json
import os
from pathlib import Path
import subprocess

PIN = "eb6cafb7290e8bd5f2937522d8d804f58f02bafc"
HERE = Path(__file__).resolve().parent

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--lean",required=True,type=Path,help="verified official v4.35.0 Lean executable")
    cli.add_argument("--library",required=True,type=Path,help="direct-build library directory containing Main.olean")
    cli.add_argument("--dep",action="append",default=[],type=Path,help="one pinned official dependency library; repeat in search order")
    cli.add_argument("--work",required=True,type=Path,help="new or empty directory for the two outputs")
    cli.add_argument("--show",action="store_true",help="validate paths and print command without executing Lean")
    args = cli.parse_args()
    tool = args.lean.resolve(strict=True)
    project = args.library.resolve(strict=True)
    deps = [path.resolve(strict=True) for path in args.dep]
    work = args.work.resolve()
    for file in ("Main.olean","Lib/DiscreteSeries/Theta/JointHarmonicUnique.olean"):
        if not (project/file).is_file():
            raise FileNotFoundError(file)
    if not tool.is_file() or not all(path.is_dir() for path in deps):
        raise ValueError("Unexpected executable or library path")
    if work.exists() and (not work.is_dir() or any(work.iterdir())):
        raise ValueError("Use an empty output directory")
    search = os.pathsep.join(str(p) for p in [project,*deps])
    argv = [str(tool), "-j1", "--tstack=400000", str(HERE / "Lineage.lean")]
    if args.show:
        print(json.dumps({"cwd":str(work),"argv":argv,"LEAN_PATH":search},indent=2))
        return
    work.mkdir(parents=True,exist_ok=True)
    env = dict(os.environ)
    env.update(LEAN_PATH=search,LEAN_NUM_THREADS="1",LEAN_ABORT_ON_PANIC="1")
    version = subprocess.run([str(tool),"--version"],cwd=work,env=env,check=True,
                             stdout=subprocess.PIPE,text=True).stdout
    if "version 4.35.0," not in version or PIN not in version:
        raise ValueError(f"Unexpected Lean version: {version.strip()}")
    subprocess.run(argv,cwd=work,env=env,check=True)
    for file in ("lineage-graph-v1.ndjson","lineage-needle-type.txt"):
        if not (work/file).is_file():
            raise ValueError("Expected Lean output missing: " + file)

if __name__ == "__main__":
    main()
