"""Data-only regression tests for resolving names, universe IDs, expression IDs and declaration fields."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import tempfile


HERE = Path(__file__).resolve().parent
core = runpy.run_path(str(HERE / "compare_exports.py"))
source = HERE.parent / "control/exports/a.ndjson"


def remap_fixture(rows):
    """Use the real A fixture. Emit names, levels and expressions in a different
    valid dependency order; preserve each named declaration and its declaration order."""
    pools = {k:{} for k in ("in","il","ie")}
    decls = []
    for r in rows[1:]:
        kind = next((k for k in pools if k in r),None)
        if kind is None: decls.append(r)
        else: pools[kind][r[kind]] = r
    idmap = {"in":{0:0}, "il":{0:0}, "ie":{}}
    result = [rows[0]]
    def convert(row, ref):
        tag = next(k for k in row if k not in pools)
        d = row[tag]
        if "in" in row:
            d["pre"] = ref("in",d["pre"])
        elif "il" in row:
            if tag=="param": row[tag] = ref("in",d)
            elif tag=="succ": row[tag] = ref("il",d)
            elif tag in ("max","imax"): row[tag] = [ref("il",n) for n in d]
            else: raise ValueError(tag)
        elif "ie" in row:
            if tag=="app":
                for k in ("fn","arg"): d[k] = ref("ie",d[k])
            elif tag in ("forallE","lam","letE"):
                d["name"] = ref("in",d["name"])
                for k in ("type","body") + (("value",) if tag=="letE" else ()): d[k]=ref("ie",d[k])
            elif tag=="const":
                d["name"] = ref("in",d["name"]);d["us"]=[ref("il",u) for u in d["us"]]
            elif tag=="sort": row[tag] = ref("il",d)
            elif tag=="proj":
                d["typeName"]=ref("in",d["typeName"]);d["struct"]=ref("ie",d["struct"])
            elif tag=="mdata": d["expr"]=ref("ie",d["expr"])
            elif tag not in ("bvar","natVal","strVal"): raise ValueError(tag)
        else:
            def declaration(d):
                for k in ("name","induct"):
                    if k in d: d[k]=ref("in",d[k])
                for k in ("levelParams","all","ctors"):
                    if k in d: d[k]=[ref("in",i) for i in d[k]]
                for k in ("type","value"):
                    if k in d: d[k]=ref("ie",d[k])
                for rule in d.get("rules",[]):
                    rule["ctor"]=ref("in",rule["ctor"]);rule["rhs"]=ref("ie",rule["rhs"])
            if tag=="inductive":
                for members in d.values():
                    for item in members: declaration(item)
            else: declaration(d)
    for kind,pool in pools.items():
        depth={k:0 for k in idmap[kind]}
        for i,row in pool.items():
            deps=[]
            def levels(space, old):
                if space==kind: deps.append(depth[old])
                return old
            convert(deepcopy(row),levels)
            depth[i]=max(deps,default=0)+1
        for old in sorted(pool,key=lambda i:(depth[i],-i)):
            new=len(idmap[kind]); item=deepcopy(pool[old])
            convert(item,lambda space,old:idmap[space][old])
            item[kind]=new; idmap[kind][old]=new; result.append(item)
    for row in decls:
        clean=deepcopy(row)
        convert(clean,lambda space,old:idmap[space][old])
        result.append(clean)
    return result,{k:sum(old!=new for old,new in m.items()) for k,m in idmap.items()}


def main():
    rows=[json.loads(line) for line in source.read_bytes().splitlines()]
    permuted,moved=remap_fixture(rows)
    assert all(count>20 for count in moved.values())
    with tempfile.TemporaryDirectory() as dirname:
        work=Path(dirname)
        def save(label,rows):
            f=work/(label+".ndjson")
            f.write_bytes(b"".join((json.dumps(r,separators=(",",":"))+"\n").encode() for r in rows))
            db=work/(label+".sqlite")
            record=core["ingest"](f,db,hashlib.sha256(f.read_bytes()).hexdigest(),0)
            return db,record
        db_a,a=save("original",rows);db_p,p=save("permuted",permuted)
        report=core["compare"](db_a,db_p)
        assert report=={"left_only":[],"right_only":[],"different":[],"common":592,"common_identical":592}
        assert a["name_sequence_digest"]==p["name_sequence_digest"]
        # Keep the dependency graph and declarations fixed. Toggle a boolean
        # on a constructor and change one RHS in a recursor rule by expression ID.
        mutated=deepcopy(rows)
        group=next(row["inductive"] for row in mutated if "inductive" in row)
        ctr,rec=group["ctors"][0],group["recs"][0]
        ctr["isUnsafe"]=not ctr["isUnsafe"]
        assert rec["rules"][0]["rhs"]!=0
        rec["rules"][0]["rhs"]=0
        db_m,_=save("mutated",mutated)
        negatives=core["compare"](db_a,db_m)
        changed=sorted(field["field"] for d in negatives["different"] for field in d["fields"])
        assert changed==["isUnsafe","rules[0].rhs"]
        rejected=[]
        for label,append in [("unknown_record",{"unexpected":{}}),("forward_expr",{"ie":0,"app":{"arg":0,"fn":0}}),("unknown_declaration_field",{"axiom":{"type":0,"name":0,"levelParams":[],"isUnsafe":False,"extra":True}})]:
            try: save(label,[rows[0],append])
            except ValueError: rejected.append(label)
            else: raise AssertionError(label+" was accepted")
        print(json.dumps({"unmodified_declarations":a["declarations"],"renumbered_ids":moved,
                          "renumbered_common_identical":report["common_identical"],
                          "inductive_negative_changed_fields":changed,
                          "rejected_malformed":rejected},indent=2))


if __name__=="__main__": main()
