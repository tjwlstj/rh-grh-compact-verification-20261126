"""Recompute dependency paths from a Lean lineage graph using two BFS directions."""
import argparse
import gzip
import hashlib
import json
from array import array
from collections import Counter, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOTS = ("riemannHypothesis", "riemannZeta_eq_zero_re", "LFunction_ne_zero_of_half_lt_re",
         "LFunction_eq_zero_re", "LFunction_eq_zero_re_of_isPrimitive")
PARENT = "HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight"
FOCUS = PARENT + "._proof_1_4"
CONTROLS = ("Nat.add_comm", "RiemannHypothesis", "RiemannZetaZerosOnLine",
            "DirichletLNonvanishingRightOfHalf", "DirichletLZerosOnLine",
            "PrimitiveDirichletLZerosOnLine")
FIELDS = ("type", "value", "inductiveConstructors", "mutualInductives",
          "constructorInductive", "recursorInductives", "recursorRuleConstructors",
          "recursorRuleRhs", "mutualValues")
KINDS = {"axiom", "definition", "theorem", "opaque", "quotientPrimitive",
         "inductive", "constructor", "recursor"}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(path):
    with path.open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()

def check_files():
    manifest = HERE / "SHA256SUMS"
    entries = set()
    for line in manifest.read_text(encoding="utf8").splitlines():
        checksum, name = line.split("  ", 1)
        require(Path(name).name == name and name not in entries and name != "SHA256SUMS", "Invalid manifest entry")
        require(digest(HERE / name) == checksum, f"Checksum mismatch for {name}")
        entries.add(name)
    require({"replay.py", "Lineage.lean", "result.json", "graph.ndjson.gz", "portable-receipt.json"} <= entries,
            "Manifest omits required inputs")
    print(json.dumps({"verifiedFiles": len(entries)}))

def read_graph(path):
    names, kinds, groups = [], [], []
    raw_hash = hashlib.sha256()
    raw_bytes = 0
    with path.open("rb") as file:
        is_gzip = file.read(2) == b"\x1f\x8b"
    opener = gzip.open if is_gzip else open
    with opener(path, "rb") as stream:
        first = next(stream)
        header = json.loads(first)
        raw_hash.update(first)
        raw_bytes += len(first)
        require(header["header"] == 1 and tuple(header["edges"]) == FIELDS, "Unexpected graph schema")
        for line in stream:
            raw_hash.update(line)
            raw_bytes += len(line)
            row = json.loads(line)
            if isinstance(row,dict):
                require(row == {"done":len(names), "missing":0} and not stream.read(1), "Incomplete graph or unresolved constants")
                break
            i, name, kind, refs = row
            require(type(i) is int and i == len(names) and isinstance(name,str)
                    and kind in KINDS and len(refs) == len(FIELDS), "Invalid declaration row")
            require(all(isinstance(xs,list) and all(type(j) is int and j >= 0 for j in xs) for xs in refs),
                    "Invalid dependency ID")
            names.append(name)
            kinds.append(kind)
            groups.append(tuple(tuple(xs) for xs in refs))
        else:
            raise ValueError("Missing graph completion marker")
    require(all(j < len(names) for g in groups for xs in g for j in xs), "Dangling edge")
    seeds = header["seeds"]
    require(seeds == names[:len(seeds)] and tuple(seeds[:13]) == (*ROOTS,PARENT,FOCUS,*CONTROLS),
            "Unexpected or ambiguous root IDs")
    require(all(names.count(s) == 1 for s in seeds[:13]), "A queried name identifies multiple nodes")
    return seeds, names, kinds, groups, raw_hash.hexdigest(), raw_bytes

def reversed_distances(groups, fields, focus):
    parents = [[] for _ in groups]
    for i, rows in enumerate(groups):
        for field in fields:
            for j in rows[field]:
                parents[j].append(i)
    distances = array("i", [-1]) * len(groups)
    distances[focus] = 0
    queue = deque([focus])
    while queue:
        j = queue.popleft()
        for i in parents[j]:
            if distances[i] < 0:
                distances[i] = 1 + distances[j]
                queue.append(i)
    return distances

def shortest(start, first, fields, dist, focus, names, kinds, groups):
    i = start
    path = [names[i]]
    steps = []
    if i == focus and first is None:
        return {"length":0, "names":path, "steps":steps}
    while True:
        allowed = first if not steps and first is not None else fields
        options = ((dist[j], names[j], j) for k in allowed for j in groups[i][k] if dist[j] >= 0)
        best = min(options, default=None)
        if best is None:
            require(not steps, "Inconsistent reverse distance")
            return None
        distance, _, j = best
        if steps or first is None:
            require(dist[i] == 1 + distance, "Selected path is not shortest")
        labels = [FIELDS[k] for k in allowed if j in groups[i][k]]
        steps.append({"from":names[i], "fromId":i, "kind":kinds[i], "fields":labels,
                      "to":names[j], "toId":j})
        path.append(names[j])
        if j == focus:
            return {"length":len(steps), "names":path, "steps":steps}
        i = j

def forward_distance(groups, start, first, fields, focus):
    if start == focus and first is None:
        return 0
    seen = bytearray(len(groups))
    queue = deque()
    for field in fields if first is None else first:
        for j in groups[start][field]:
            if j == focus:
                return 1
            if not seen[j]:
                seen[j] = 1
                queue.append((j, 1))
    while queue:
        i, n = queue.popleft()
        for field in fields:
            for j in groups[i][field]:
                if j == focus:
                    return n+1
                if not seen[j]:
                    seen[j] = 1
                    queue.append((j,n+1))
    return None

def forward_coverage(groups, kinds, names, start):
    seen = bytearray(len(groups))
    seen[start] = 1
    stack = [start]
    axioms = []
    while stack:
        i = stack.pop()
        if kinds[i] == "axiom":
            axioms.append(names[i])
        for field in (0,1):
            for j in groups[i][field]:
                if not seen[j]:
                    seen[j] = 1
                    stack.append(j)
    return {"vertices":sum(seen), "axiomDeclarations":sorted(axioms)}

def measure(path):
    seeds,names,kinds,groups,sha,size = read_graph(path)
    focus = seeds.index(FOCUS)
    result = {
        "graphSha256":sha, "graphBytes":size, "graphVertices":len(names), "seedCount":len(seeds),
        "kinds":dict(Counter(kinds)), "displayNameCollisionsBeyondFirst":len(names)-len(set(names)),
        "fields":list(FIELDS), "focusName":FOCUS, "focusKind":kinds[focus],
        "fieldOccurrences":{label:sum(len(g[k]) for g in groups) for k,label in enumerate(FIELDS)},
        "literalForwardCoverage":{n:forward_coverage(groups,kinds,names,seeds.index(n)) for n in (*ROOTS,PARENT,*CONTROLS)},
        "directLiteralCallers":[{"name":names[i], "id":i, "kind":kinds[i],
                                 "fields":[FIELDS[k] for k in (0,1) if focus in row[k]]}
                                for i,row in enumerate(groups) if focus in row[0] or focus in row[1]],
        "independentKnownDirectControl":{"from":ROOTS[1], "field":"value", "to":ROOTS[0],
                                        "observed":seeds.index(ROOTS[0]) in groups[seeds.index(ROOTS[1])][1]},
    }
    queries = 0
    for mode,fields in (("literal",(0,1)), ("typesOnly",(0,)), ("structural",tuple(range(len(FIELDS))))):
        distances = reversed_distances(groups,fields,focus)
        section = {}
        constraints = [("shortest",None),("firstType",(0,))]
        if mode != "typesOnly":
            constraints.append(("firstValue",(1,)))
        for name in (*ROOTS,PARENT,*CONTROLS,FOCUS):
            start = seeds.index(name)
            section[name] = {}
            for key,first in constraints:
                witness = shortest(start,first,fields,distances,focus,names,kinds,groups)
                direct_distance = forward_distance(groups,start,first,fields,focus)
                require((None if witness is None else witness["length"]) == direct_distance,
                        f"BFS directions disagree for {mode}/{name}/{key}")
                section[name][key] = witness
                queries += 1
        result[mode] = section
    require(queries == 104, "Incomplete query set")
    return result, queries

def main():
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("--graph",type=Path,default=HERE/"graph.ndjson.gz",help="raw NDJSON or gzip")
    cmd.add_argument("--expected",type=Path,default=HERE/"result.json",help="reference result for exact graph comparison")
    cmd.add_argument("--measure-only",action="store_true",help="measure independent input without comparing it to the recorded run")
    cmd.add_argument("--output",type=Path,help="write newly measured full results to this non-existing file")
    cmd.add_argument("--check-files",action="store_true",help="check the package manifest and exit")
    options = cmd.parse_args()
    if options.check_files:
        check_files()
        return
    data, queries = measure(options.graph)
    if not options.measure_only:
        expected = json.loads(options.expected.read_bytes())
        for field,value in data.items():
            require(field in expected and expected[field] == value, f"Reference mismatch: {field}")
    if options.output:
        with options.output.open("x",encoding="utf8",newline="\n") as output:
            json.dump(data,output,ensure_ascii=False,indent=2)
            output.write("\n")
    summary = {"graphSha256":data["graphSha256"],"graphVertices":data["graphVertices"],
               "bidirectionalQueries":queries,"referenceMatched":not options.measure_only,
               "shortest":{n:(w["length"] if (w:=data["literal"][n]["shortest"]) is not None else None) for n in ROOTS}}
    print(json.dumps(summary,ensure_ascii=False))

if __name__ == "__main__":
    main()
