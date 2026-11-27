"""Run the two unchanged raw-NDJSON analyses in a separate directory using Python 3.11."""
import argparse
import json
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
RAW_SHA = "5a4ab2e2c6db4ca5ea3bafbe76157f8db5ab520e1eaacd5a13350eafad1e96f6"
RAW_BYTES = 5_172_278_111
REFERENCE = {
    "main-raw-lineage.json": "de01d90f947fd457fa6de976a34a992e34f504d95607c8cf3abd1fc96981e534",
    "raw-edge-certificates.json": "4245a52728f8def92fead1353dc75b18f1b13382eaac219529f48dc3acd957de",
}


def check_results(folder):
    for name, expected in REFERENCE.items():
        saved = (PACKAGE / name).read_bytes()
        if sha256(saved).hexdigest() != expected:
            raise ValueError(f"published reference file failed its SHA-256 check: {name}")
        actual = (folder / name).read_bytes()
        original, reproduction = json.loads(saved), json.loads(actual)
        if name == "main-raw-lineage.json":
            # This field is just the basename passed by the operator on this machine.
            if not isinstance(reproduction["inputFile"], str):
                raise ValueError("invalid input basename field")
            original.pop("inputFile")
            reproduction.pop("inputFile")
        if reproduction != original:
            raise ValueError(f"reproduced JSON data differs: {name}")
        raw_match = actual == saved
        print(f"{name}: JSON evidence matches; byte-for-byte match={raw_match}; "
              f"reproduced SHA-256={sha256(actual).hexdigest()}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="restored raw Main NDJSON")
    p.add_argument("--receipt", type=Path, required=True, help="published solution-pack.json")
    p.add_argument("--work", type=Path, required=True, help="a new directory for the two results")
    args = p.parse_args()
    receipt = json.loads(args.receipt.read_bytes())
    if (receipt.get("kind"), receipt.get("rawBytes"), receipt.get("rawSha256")) != ("solution", RAW_BYTES, RAW_SHA):
        raise ValueError("the receipt does not identify the published local Main")
    if args.input.stat().st_size != RAW_BYTES:
        raise ValueError("input size does not match the raw Main receipt")
    # The original scripts locate their own sibling result. Stage them together without
    # touching this published directory or copying the large input.
    args.work.mkdir(parents=True, exist_ok=False)
    run = args.work / "analysis" / "raw-lineage"
    run.mkdir(parents=True)
    for name in ("trace_ndjson.py", "verify_edges.py"):
        shutil.copyfile(PACKAGE / name, run / name)
    py = [sys.executable, "-I", "-B"]
    subprocess.run([*py, str(run / "trace_ndjson.py"), "--input", str(args.input.resolve()),
                    "--receipt", str(args.receipt.resolve())], check=True)
    subprocess.run([*py, str(run / "verify_edges.py"), "--input", str(args.input.resolve())], check=True)
    check_results(run)


if __name__ == "__main__":
    main()
