"""Trace literal expression references to one helper in a fixed Lean 4.35 raw export.

No Lean environment is loaded. One process, one sequential pass if no forward lookup
changes its answer; otherwise rerun from proved positive seeds until the answer stabilises.
"""
import argparse
import array
import ctypes
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = "HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4"
PARENT = TARGET.rsplit(".", 1)[0]
ROOTS = ["riemannHypothesis", "riemannZeta_eq_zero_re", "LFunction_ne_zero_of_half_lt_re",
         "LFunction_eq_zero_re", "LFunction_eq_zero_re_of_isPrimitive"]
WATCH = [TARGET, PARENT, *ROOTS, "New.grh", "Nat", "Classical.choice"]
FULL, TYPE, VALUE, SEALED, LEAN, DIRECT, CONTROL = 1, 2, 4, 8, 16, 32, 64
TRANS = FULL | TYPE | VALUE | SEALED | LEAN
POLICY = {"exprTypeValueRules": FULL, "onlyTypes": TYPE, "onlyBodies": VALUE,
          "theoremAndOpaqueBodiesSealed": SEALED, "leanConstantInfoGetUsedConstantsAsSet": LEAN}
APP = re.compile(rb'\{"app":\{"arg":([0-9]+),"fn":([0-9]+)\},"ie":([0-9]+)\}\r?\n')
FORMAT = {"exporter": {"name": "lean4export", "version": "3.1.0"}, "format": {"version": "3.1.0"},
          "lean": {"githash": "eb6cafb7290e8bd5f2937522d8d804f58f02bafc", "version": "4.35.0"}}


def low_priority():
    if os.name == "nt":
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x40):
            raise OSError("could not set idle priority")
    else:
        os.nice(10)


class Names:
    def __init__(self):
        self.parents = array.array("I", [0])
        self.parts = [None]
        self.prefixes = {0: ""}
        self.wanted = {".".join(name.split(".")[:i]) for name in WATCH
                       for i in range(1, 1 + len(name.split(".")))}
        self.ids = {}

    def add(self, row):
        n = row["in"]
        if n != len(self.parts):
            raise ValueError("unexpected name index")
        if "str" in row:
            v = row["str"]
            part = v["str"]
        else:
            v = row["num"]
            part = v["i"]
        pre = v["pre"]
        if not 0 <= pre < n:
            raise ValueError("invalid name prefix")
        self.parts.append(part)
        self.parents.append(pre)
        if pre in self.prefixes and isinstance(part, str) and "." not in part:
            text = (self.prefixes[pre] + "." if pre else "") + part
            if text in self.wanted:
                self.prefixes[n] = text
                if text in WATCH:
                    self.ids[text] = n
                    return text
        return None

    def text(self, idx):
        parts = []
        while idx:
            c = self.parts[idx]
            parts.append(("«"+c+"»" if isinstance(c, str) and ("." in c or c.isdecimal()) else str(c)))
            idx = self.parents[idx]
        return ".".join(reversed(parts))


def run_pass(path, seeds, old_witness):
    names = Names()
    masks, witnesses = bytearray(), array.array("I")
    decl = dict(seeds)
    seen = set()
    used_early = {}
    leaf_data = {}
    links = dict(old_witness)
    watched = {}
    exprs = Counter()
    kinds = Counter()
    input_hash = hashlib.sha256()
    rows = total = 0
    level_count = 1
    target_id = control_id = None

    def name_mask(n):
        if not 0 < n < len(names.parts):
            raise ValueError("undefined name index")
        flags = decl.get(n, 0)
        if n not in seen:
            used_early[n] = used_early.get(n, 0) | (TRANS & ~flags)
        return flags

    def ref_leaf(n, index, kind):
        flags = name_mask(n)
        if n == target_id:
            flags |= DIRECT
        if n == control_id:
            flags |= CONTROL
        witness = 0
        if flags & FULL:
            witness = index + 1
            leaf_data[witness] = (n, rows, kind)
        return flags, witness

    def expr(row):
        i = row["ie"]
        if i != len(masks):
            raise ValueError("out-of-order expression")
        tag = next(k for k in row if k != "ie")
        e = row[tag]
        flags = next_ref = 0
        if tag == "const":
            flags, next_ref = ref_leaf(e["name"], i, tag)
            children = ()
        elif tag == "proj":
            flags, next_ref = ref_leaf(e["typeName"], i, tag)
            children = (e["struct"],)
        elif tag == "app":
            children = (e["fn"], e["arg"])
        elif tag in ("lam", "forallE"):
            children = (e["type"], e["body"])
        elif tag == "letE":
            children = (e["type"], e["value"], e["body"])
        elif tag == "mdata":
            children = (e["expr"],)
        elif tag in ("natVal", "strVal", "bvar", "sort"):
            children = ()
        else:
            raise ValueError("unknown expression: " + tag)
        for child in children:
            if not 0 <= child < i:
                raise ValueError("forward expression index")
            flags |= masks[child]
            next_ref = next_ref or witnesses[child]
        masks.append(flags)
        witnesses.append(next_ref)
        exprs[tag] += 1

    def record(kind, info, aux=()):
        n = info["name"]
        if n in seen or not 0 < n < len(names.parts):
            raise ValueError("duplicate or invalid declaration")
        fields = [("type", info["type"])]
        if kind in ("def", "thm", "opaque"):
            fields.append(("value", info["value"]))
        if kind == "recursor":
            fields.extend(("ruleRhs"+str(i), rule["rhs"]) for i, rule in enumerate(info["rules"]))
        flags = 0
        fields_masks = {}
        # Proof/value first when recording one explicit witness.
        for field, index in reversed(fields):
            if not 0 <= index < len(masks):
                raise ValueError("invalid declaration expression")
            mask = masks[index]
            fields_masks[field] = mask
            flags |= mask & FULL
            if field == "type":
                flags |= mask & (TYPE | SEALED | LEAN)
            elif field == "value":
                flags |= mask & (VALUE | LEAN)
                if kind == "def":
                    flags |= mask & SEALED
            else:
                flags |= mask & SEALED
            if n not in links and n != target_id and mask & FULL:
                leaf = witnesses[index]
                near, line, shape = leaf_data[leaf]
                links[n] = (kind, rows, field, index, leaf - 1, line, shape, near)
        for other in aux:
            flags |= name_mask(other) & LEAN
        if n == target_id:
            flags |= TRANS
        decl[n] = decl.get(n, 0) | flags
        seen.add(n)
        kinds[kind] += 1
        if n in names.ids.values():
            watched[n] = {"line": rows, "kind": kind, "fields": {f: {"ie": i, "mask": fields_masks[f]} for f,i in fields},
                          "recordSha256": hashlib.sha256(line_bytes).hexdigest()}

    with path.open("rb", buffering=2 ** 20) as f:
        for line_bytes in f:
            rows += 1
            total += len(line_bytes)
            input_hash.update(line_bytes)
            if line_bytes.startswith(b'{"app":'):
                m = APP.fullmatch(line_bytes)
                if m:
                    arg, fn, i = map(int, m.groups())
                    if i != len(masks) or arg >= i or fn >= i:
                        raise ValueError("unexpected application reference")
                    masks.append(masks[fn] | masks[arg])
                    witnesses.append(witnesses[fn] or witnesses[arg])
                    exprs["app"] += 1
                    continue
            row = json.loads(line_bytes)
            if "ie" in row:
                expr(row)
            elif "in" in row:
                new = names.add(row)
                if new == TARGET:
                    target_id = row["in"]
                    decl[target_id] = TRANS
                elif new == ROOTS[0]:
                    control_id = row["in"]
            elif "il" in row:
                if row["il"] != level_count or set(row)-{"il"} not in ({"succ"},{"max"},{"imax"},{"param"}):
                    raise ValueError("unexpected universe level")
                level_count += 1
            elif rows == 1 and row == {"meta": FORMAT}:
                pass
            elif len(row) == 1:
                kind, info = next(iter(row.items()))
                if kind == "inductive":
                    for x in info["types"]:
                        record("inductive", x, x["ctors"])
                    for x in info["ctors"]:
                        record("constructor", x, [x["name"]])
                    for x in info["recs"]:
                        record("recursor", x, x["all"])
                elif kind in {"axiom","quot","thm","opaque","def"}:
                    record(kind, info)
                else:
                    raise ValueError("unknown declaration: "+kind)
            else:
                raise ValueError("unknown record")
    if set(names.ids) != set(WATCH) or not set(names.ids.values()) <= seen:
        raise ValueError("missing watched declaration")
    if set(used_early) - seen:
        raise ValueError("some expression/structural references have no declaration in this export")
    conflicts = {n: assumed & decl[n] for n, assumed in used_early.items() if assumed & decl[n]}
    def edge(start):
        kind, line, field, ie, leaf, leaf_line, shape, next_n = links[start]
        return {"from": names.text(start), "kind":kind, "declarationLine":line, "field":field,
                "rootExpr":ie, "referenceExpr":leaf, "referenceLine":leaf_line, "referenceForm":shape,
                "to":names.text(next_n)}, next_n
    def chain(start):
        path = []
        visited = set()
        while start != target_id:
            if start in visited or start not in links:
                raise ValueError("unsubstantiated positive or cycle")
            visited.add(start)
            e, start = edge(start)
            path.append(e)
        return path
    report = {}
    for name in WATCH:
        n = names.ids[name]
        w = watched[n].copy()
        w["policies"] = {key:bool(decl[n]&bit) for key,bit in POLICY.items()}
        for item in w["fields"].values():
            mask = item.pop("mask")
            item.update({key:bool(mask&bit) for key,bit in POLICY.items()})
            item.update(directHelper=bool(mask&DIRECT), directRiemannHypothesis=bool(mask&CONTROL))
        w["witness"] = chain(n) if decl[n]&FULL else None
        report[name] = w
    return {"rawBytes":total, "rawSha256":input_hash.hexdigest(), "lines":rows,
            "nameRecords":len(names.parts)-1, "expressionRecords":len(masks), "levelRecords":level_count-1,
            "declarationKinds":dict(kinds), "expressionKinds":dict(exprs),
            "earlyNames":len(used_early), "unresolvedNamesAtEOF":0, "changedAssumptions":len(conflicts),
            "watched":report}, {n:v for n,v in decl.items() if v}, links


def main():
    low_priority()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT/"source-build"/"exports"/"solution-comparator.ndjson")
    parser.add_argument("--receipt", type=Path, default=ROOT/"notes"/"export-release"/"solution-pack.json")
    args = parser.parse_args()
    expected = json.loads(args.receipt.read_bytes())
    seeds, witnesses = {}, {}
    passes = []
    while True:
        result, next_seeds, witnesses = run_pass(args.input, seeds, witnesses)
        if (result["rawSha256"],result["rawBytes"]) != (expected["rawSha256"],expected["rawBytes"]):
            raise ValueError("raw input failed receipt comparison")
        passes.append({"changedAssumptions":result["changedAssumptions"],"positiveNamesAnyPolicy":len(next_seeds)})
        if not result["changedAssumptions"]:
            break
        if next_seeds == seeds:
            raise ValueError("forward-reference fixpoint stalled")
        seeds = next_seeds
    result["passes"] = passes
    result["target"] = TARGET
    result["roots"] = ROOTS
    result["inputFile"] = args.input.name
    result["controls"] = {
        "actualTheoremWithProof": result["watched"][TARGET]["kind"] == "thm" and "value" in result["watched"][TARGET]["fields"],
        "root2ValueExplicitlyReferencesRoot1":result["watched"][ROOTS[1]]["fields"]["value"]["directRiemannHypothesis"],
        "natAndChoiceHaveNoHelperLineage":all(not result["watched"][n]["policies"]["exprTypeValueRules"] for n in ["Nat","Classical.choice"]),
    }
    if not all(result["controls"].values()):
        raise ValueError("a positive or negative control failed")
    dest=HERE/"main-raw-lineage.json"
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for name in ROOTS:
        w=result["watched"][name]
        print(name,w["policies"],len(w["witness"] or []))


if __name__ == "__main__":
    main()
