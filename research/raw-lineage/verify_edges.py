"""Check every published declaration-to-declaration witness against its literal raw rows.

This reader does not propagate theorem reachability. Each edge is tested in isolation:
is the stated const/proj leaf a syntactic descendant of this particular owner expression?
"""
import argparse
import array
import ctypes
import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP = re.compile(rb'\{"app":\{"arg":(\d+),"fn":(\d+)\},"ie":(\d+)\}\r?\n')


def low_priority():
    if os.name == "nt":
        lib = ctypes.windll.kernel32
        lib.GetCurrentProcess.restype = ctypes.c_void_p
        lib.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        if not lib.SetPriorityClass(lib.GetCurrentProcess(), 0x40):
            raise OSError("could not set idle priority")
    else:
        os.nice(10)


def index_source(path, names, wanted_lines):
    prefixes = {".".join(name.split(".")[:i]) for name in names for i in range(1, len(name.split(".")) + 1)}
    prefix_index = {0: ""}
    ids, offsets = {}, {}
    digest = hashlib.sha256()
    size = 0
    with path.open("rb", buffering=2**20) as f:
        for lineno, raw in enumerate(f, start=1):
            if lineno in wanted_lines:
                offsets[lineno] = size
            if raw.startswith(b'{"in":') and b'"str":{' in raw:
                row = json.loads(raw)
                component = row["str"]["str"]
                parent = row["str"]["pre"]
                if parent in prefix_index and "." not in component:
                    prefix = prefix_index[parent]
                    qualified = (prefix+"." if prefix else "") + component
                    if qualified in prefixes:
                        i = row["in"]
                        prefix_index[i] = qualified
                        if qualified in names:
                            if qualified in ids:
                                raise ValueError("ambiguous segment-qualified constant name")
                            ids[qualified] = i
            size += len(raw)
            digest.update(raw)
    if set(ids) != names or set(offsets) != wanted_lines:
        raise ValueError("an expected name or source line is absent")
    return ids, offsets, size, digest.hexdigest()


def children(raw):
    app = APP.fullmatch(raw)
    if app:
        arg, fn, index = map(int, app.groups())
        return index, (fn, arg)
    obj = json.loads(raw)
    i = obj["ie"]
    kind = next(k for k in obj if k != "ie")
    e = obj[kind]
    if kind in {"natVal", "strVal", "sort", "bvar", "const"}:
        return i, ()
    layouts = {"app": ("fn","arg"), "proj": ("struct",), "mdata": ("expr",),
               "letE": ("type","value","body"), "lam": ("type","body"), "forallE": ("type","body")}
    return i, tuple(e[k] for k in layouts[kind])


def declaration_field(obj, edge, ids):
    kind = edge["kind"]
    if kind in ("inductive", "constructor", "recursor"):
        key = {"inductive": "types", "constructor": "ctors", "recursor": "recs"}[kind]
        candidates = [v for v in obj["inductive"][key] if v["name"] == ids[edge["from"]]]
        if len(candidates) != 1:
            raise ValueError("missing or ambiguous grouped declaration")
        declaration = candidates[0]
    else:
        declaration = obj[kind]
        if declaration["name"] != ids[edge["from"]]:
            raise ValueError("wrong owner declaration")
    field = edge["field"]
    if field.startswith("ruleRhs"):
        return declaration["rules"][int(field.removeprefix("ruleRhs"))]["rhs"]
    return declaration[field]


def verify_one(f, ids, offsets, e):
    seed, root = e["referenceExpr"], e["rootExpr"]
    f.seek(offsets[e["declarationLine"]])
    owner_raw = f.readline()
    if declaration_field(json.loads(owner_raw), e, ids) != root:
        raise ValueError("claimed declaration field is not that root expression")
    f.seek(offsets[e["referenceLine"]])
    leaf_raw = f.readline()
    leaf = json.loads(leaf_raw)
    shape = e["referenceForm"]
    name = leaf[shape]["name" if shape == "const" else "typeName"]
    if shape not in ("const", "proj") or name != ids[e["to"]] or leaf["ie"] != seed:
        raise ValueError("wrong syntactic reference")
    if root < seed:
        raise ValueError("child index follows parent")
    # Store one child pointer toward this one leaf for each in-range expression.
    # All children with an index below that leaf are necessarily irrelevant.
    pred = array.array("I", [seed + 1])
    while len(pred) < root - seed + 1:
        raw = f.readline()
        if not raw:
            raise ValueError("incomplete expression interval")
        if b'"ie":' not in raw:
            continue
        i, ch = children(raw)
        if seed + len(pred) != i or any(c >= i for c in ch):
            raise ValueError("invalid expression order")
        pred.append(next((c+1 for c in ch if c >= seed and pred[c-seed]), 0))
    route = [root]
    while route[-1] != seed:
        child = pred[route[-1] - seed]
        if not child:
            raise ValueError("the claimed leaf is outside this exact field")
        route.append(child - 1)
    return {**e, "fromNameIndex":ids[e["from"]], "toNameIndex":name,
            "declarationRowSha256":hashlib.sha256(owner_raw).hexdigest(),
            "referenceRowSha256":hashlib.sha256(leaf_raw).hexdigest(),
            "expressionChildPath":route}


def main():
    low_priority()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT/"source-build"/"exports"/"solution-comparator.ndjson")
    args=parser.parse_args()
    report=json.loads((HERE/"main-raw-lineage.json").read_bytes())
    unique = {}
    for w in report["watched"].values():
        for edge in w["witness"] or []:
            name = edge["from"]
            if name in unique and unique[name] != edge:
                raise ValueError("inconsistent duplicate witness")
            unique[name] = edge
    endpoints = {n for e in unique.values() for n in (e["from"],e["to"])}
    line_numbers = {i for e in unique.values() for i in (e["referenceLine"],e["declarationLine"])}
    ids, offsets, size, digest = index_source(args.input, endpoints, line_numbers)
    if (size,digest) != (report["rawBytes"], report["rawSha256"]):
        raise ValueError("input digest mismatch")
    with args.input.open("rb", buffering=2**20) as raw:
        checks = [verify_one(raw,ids,offsets,e) for e in unique.values()]
    result={"rawSha256":digest,"rawBytes":size,"uniqueCheckedEdges":len(checks),"edges":checks}
    (HERE/"raw-edge-certificates.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(len(checks),"unique edges with explicit expression child paths")


if __name__=="__main__":
    main()
