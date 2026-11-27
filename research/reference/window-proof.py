"""Reproduce the first changed NDJSON declaration without importing Lean or another comparator.

python window-proof.py --reference compact-solution.ndjson --local solution-comparator.ndjson --output window-proof.json
Byte offsets are zero-based. Lines are one-based. All ends are exclusive.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

PINS = {
    "reference": "ab7b4223b9bd748a1aa68bdb63afb6d6264121fc834aadba7ba3d3796c32115b",
    "local": "5a4ab2e2c6db4ca5ea3bafbe76157f8db5ab520e1eaacd5a13350eafad1e96f6",
}
CHUNK = 1 << 20


def hash_file(f):
    f.seek(0)
    h, size, lines = hashlib.sha256(), 0, 0
    for data in iter(lambda: f.read(CHUNK), b""):
        h.update(data)
        size += len(data)
        lines += data.count(b"\n")
    return {"sha256": h.hexdigest(), "bytes": size, "records": lines}


def common_prefix(a, b):
    a.seek(0)
    b.seek(0)
    offset = count = line_start = 0
    digest = hashlib.sha256()
    while True:
        x, y = a.read(CHUNK), b.read(CHUNK)
        if x == y and x:
            same = x
            done = False
        else:
            i = next((i for i, (m, n) in enumerate(zip(x, y)) if m != n), min(len(x), len(y)))
            if i == min(len(x),len(y)):
                raise ValueError("no differing byte before an end of file")
            same = x[:i]
            done = True
        digest.update(same)
        count += same.count(b"\n")
        nl = same.rfind(b"\n")
        if nl >= 0:
            line_start = offset + nl + 1
        offset += len(same)
        if done:
            return {"bytes": offset, "sha256": digest.hexdigest(), "completeRecords": count,
                    "firstDifferingRecordStart": line_start, "firstDifferingRecordLine": count + 1,
                    "firstDifferingByteWithinRecord": offset - line_start,
                    "firstDifferingByteHex": {"reference": f"{x[i]:02x}", "local": f"{y[i]:02x}"}}


def read_window(f, prefix):
    start = prefix["firstDifferingRecordStart"]
    f.seek(start)
    kinds = Counter()
    digest = hashlib.sha256()
    rows = 0
    children = {}
    while f.tell() - start < 8 * CHUNK:
        offset = f.tell()
        raw = f.readline(CHUNK)
        if not raw.endswith(b"\n"):
            raise ValueError("unknown or truncated NDJSON line")
        row = json.loads(raw)
        rows += 1
        line = prefix["completeRecords"] + rows
        digest.update(raw)
        if rows == 1:
            first = row
        if "ie" in row:
            tag, = (k for k in row if k != "ie")
            kinds["expr." + tag] += 1
            layout = {"app": ("fn", "arg"), "lam": ("type", "body"), "letE": ("type", "value", "body")}
            child_ids = tuple(row[tag][k] for k in layout[tag])
            if row["ie"] in children or any(c >= row["ie"] for c in child_ids):
                raise ValueError("invalid or unsupported expression order in the window")
            children[row["ie"]] = child_ids
        elif "in" in row or "il" in row:
            kinds["name" if "in" in row else "level"] += 1
        else:
            tag, = row
            if tag != "thm":
                raise ValueError(f"unexpected first declaration kind: {tag}")
            kinds[tag] += 1
            # A node before the window cannot point to a more recent expression in it.
            # Explore just the bounded window and keep one exact child route.
            proof_root = row[tag]["value"]
            if proof_root not in children:
                raise ValueError("proof root outside inspected expression window")
            parents = {proof_root: None}
            pending = [proof_root]
            while pending:
                parent = pending.pop()
                for child in children[parent]:
                    if child in children and child not in parents:
                        parents[child] = parent
                        pending.append(child)
            path = []
            current = first["ie"]
            if current in parents:
                while current is not None:
                    path.append(current)
                    current = parents[current]
                path.reverse()
            return {"firstChangedRecord": first, "firstNamedDeclaration": row, "declarationStart": offset,
                    "declarationLine": line, "declarationEnd": f.tell(),
                    "declarationRowSha256": hashlib.sha256(raw).hexdigest(),
                    "recordsFromChangedRowThroughDeclaration": rows,
                    "bytesFromChangedRowThroughDeclaration": f.tell() - start,
                    "bytesFromFirstDifferingByteThroughDeclaration": f.tell() - prefix["bytes"],
                    "windowSha256FromRowStart": digest.hexdigest(), "recordKinds": dict(sorted(kinds.items())),
                    "windowExprsReachableFromProofValue": len(parents), "windowExprsTotal": len(children),
                    "proofValueChildPathToFirstChangedExpr": path}
    raise ValueError("no declaration in supported local window")


class PrefixTables:
    """Binary-search the increasing name/expression IDs in the byte-identical prefix."""
    def __init__(self, f, limit):
        self.f = f
        self.limit = limit
        self.cache = {}

    def first(self, begin, hi, key):
        f = self.f
        f.seek(max(0, begin-1))
        if begin and f.read(1) != b"\n":
            f.readline()
        needle = b'"' + key.encode("ascii") + b'":'
        while f.tell() < hi:
            pos = f.tell()
            raw = f.readline()
            if not raw or f.tell() > self.limit:
                break
            if needle in raw:
                obj = json.loads(raw)
                if key in obj:
                    return {"offset": pos, "end": f.tell(), "row": obj}
        return None

    def get(self, key, idx):
        cache_key = key, idx
        if cache_key not in self.cache:
            self.cache[cache_key] = self.search(key, idx)
        return self.cache[cache_key]

    def search(self, key, idx):
        lo, hi = 0, self.limit
        while hi - lo > 65536:
            mid = (lo + hi) // 2
            hit = self.first(mid, hi, key)
            if hit is None or hit["row"][key] > idx:
                hi = mid
            elif hit["row"][key] < idx:
                lo = hit["end"]
            else:
                return hit
        while lo < hi:
            hit = self.first(lo, hi, key)
            if hit is None or hit["row"][key] > idx:
                break
            if hit["row"][key] == idx:
                return hit
            lo = hit["end"]
        raise ValueError(f"{key} {idx} not found in common prefix")

    def name(self, idx):
        records = []
        while idx:
            r = self.get("in", idx)
            row = r["row"]
            t = row.get("str", row.get("num"))
            if not t or not 0 <= t["pre"] < idx:
                raise ValueError("invalid name constructor")
            component = t.get("str", t.get("i"))
            records.append({"id": idx, "parent": t["pre"], "component": component, "offset": r["offset"]})
            idx = t["pre"]
        records.reverse()
        return {"text": ".".join(str(x["component"]) for x in records), "components": records}

    def equality(self, idx):
        root = self.get("ie",idx)
        current = root
        binders, apps = [], []
        while "forallE" in current["row"]:
            r = current["row"]
            data = r["forallE"]
            if data["body"] >= r["ie"]:
                raise ValueError("invalid forall ordering")
            binders.append({"ie": r["ie"], "domain": data["type"], "body": data["body"]})
            current = self.get("ie", data["body"])
        while "app" in current["row"]:
            r = current["row"]
            d = r["app"]
            if d["fn"] >= r["ie"]:
                raise ValueError("invalid app ordering")
            apps.append({"ie": r["ie"], "fn": d["fn"], "arg": d["arg"]})
            current = self.get("ie", d["fn"])
        head = self.name(current["row"]["const"]["name"])
        if head["text"] != "Eq" or len(apps) != 3:
            raise ValueError("expected fully applied equality under quantifiers")
        return {"root": root, "foralls": binders, "conclusionApps": apps,
                "head": {"expression": current, "name": head},
                "equalityArguments": list(reversed([app["arg"] for app in apps]))}


def offsets_to_lines(f, offsets):
    f.seek(0)
    line = 1
    found = {}
    for pos in sorted(set(offsets)):
        remaining = pos - f.tell()
        while remaining:
            data = f.read(min(remaining, CHUNK))
            if not data:
                raise ValueError("source offset out of range")
            line += data.count(b"\n")
            remaining -= len(data)
        found[pos] = line
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", required=True, type=Path, help="MIT raw compact-solution export")
    p.add_argument("--local", required=True, type=Path, help="local direct-build raw Main export")
    p.add_argument("--output", type=Path, help="write the receipt as JSON; stdout if omitted")
    args = p.parse_args()
    if args.output and args.output.resolve() in (args.local.resolve(), args.reference.resolve()):
        raise ValueError("output would overwrite an input")
    with args.reference.open("rb") as ref, args.local.open("rb") as local:
        streams = {"reference": ref, "local": local}
        inputs = {side: hash_file(f) for side,f in streams.items()}
        if {side:r["sha256"] for side,r in inputs.items()} != PINS:
            raise ValueError("an input differs from the pinned pair")
        prefix = common_prefix(ref, local)
        windows = {side:read_window(f,prefix) for side,f in streams.items()}
        for side, w in windows.items():
            w["followingBytes"] = inputs[side]["bytes"] - w["declarationEnd"]
            w["followingRecords"] = inputs[side]["records"] - w["declarationLine"]
        a = windows["reference"]["firstNamedDeclaration"]["thm"]
        b = windows["local"]["firstNamedDeclaration"]["thm"]
        fields = sorted(k for k in set(a)|set(b) if a.get(k) != b.get(k))
        if fields != ["value"]:
            raise ValueError("first theorem records differ outside the proof root or have equal roots")
        tables = PrefixTables(ref, prefix["firstDifferingRecordStart"])
        name = tables.name(a["name"])
        eq = tables.equality(a["type"])
        locations = [*name["components"],eq["root"],eq["head"]["expression"],*eq["head"]["name"]["components"]]
        lines = offsets_to_lines(ref, [r["offset"] for r in locations])
        for r in locations:
            r["line"] = lines[r["offset"]]
        delta = {k:windows["local"][k]-windows["reference"][k] for k in
                 ("recordsFromChangedRowThroughDeclaration","bytesFromChangedRowThroughDeclaration",
                  "followingBytes","followingRecords")}
        delta["totalBytes"] = inputs["local"]["bytes"] - inputs["reference"]["bytes"]
        delta["totalRecords"] = inputs["local"]["records"] - inputs["reference"]["records"]
        if (delta["totalBytes"] != delta["bytesFromChangedRowThroughDeclaration"]+delta["followingBytes"]
                or delta["totalRecords"] != delta["recordsFromChangedRowThroughDeclaration"]+delta["followingRecords"]):
            raise ValueError("byte or row accounting failed")
    report = {"scope":"Raw export prefix, first differing record through first following named theorem, and tail sizes only.",
              "coordinates":"Zero-based byte offsets/end-exclusive; one-based NDJSON lines.",
              "inputs": inputs, "commonPrefix": prefix, "windows": windows, "differentThmFields": fields,
              "theoremNameFromPrefix": name, "theoremTypeFromPrefix": eq, "deltaLocalMinusReference": delta}
    out = (json.dumps(report, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
    if args.output:
        args.output.write_bytes(out)
    else:
        print(out.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
