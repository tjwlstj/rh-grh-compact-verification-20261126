"""Compare complete Lean 4.35.0 NDJSON declarations after resolving file-local IDs.

Python standard library only. Numbered expression nodes are streamed to a chunked
32-byte digest table. SQLite stores named declarations, not the expression graph.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import struct
import sys
import time


HEADER = {"exporter": {"name": "lean4export", "version": "3.1.0"},
          "format": {"version": "3.1.0"},
          "lean": {"githash": "eb6cafb7290e8bd5f2937522d8d804f58f02bafc", "version": "4.35.0"}}
SCHEMA_SHA = "2e839d4ac1ef1992cfe09c489a97928ad8f8eaea3925bc76b511c6bf85e1b8aa"
APP_LINE = re.compile(rb'\{"app":\{"arg":(0|[1-9][0-9]*),"fn":(0|[1-9][0-9]*)\},"ie":(0|[1-9][0-9]*)\}\r?\n')
U64 = struct.Struct(">Q")
TAGS = ("N0 Ns Nn L0 Ls Lmax Limax Lp Ebvar Esort Econst Eapp Elam EforallE "
        "EletE Eproj EnatVal EstrVal Emdata").split()
# Domain prefix and unique one-byte tag. References are always 32 raw bytes.
PREFIX = {s: b"LeanExport-v3.1.0-sha256\x00" + bytes([i]) for i, s in enumerate(TAGS)}
BINDERS = ("default", "implicit", "strictImplicit", "instImplicit")
ORD = {k:bytes([i]) for i,k in enumerate(BINDERS)}
BASE = {"name":"name", "levelParams":"names", "type":"expr"}
DECL = {
    "axiom": {"isUnsafe":"bool"}, "thm":{"all":"names", "value":"expr"},
    "def":{"all":"names", "value":"expr", "hints":"hints", "safety":"safety"},
    "opaque":{"all":"names", "value":"expr", "isUnsafe":"bool"}, "quot":{"kind":"quotKind"},
    "inductive":{"all":"names", "ctors":"names", "numParams":"nat", "numIndices":"nat",
                 "numNested":"nat", "isRec":"bool", "isReflexive":"bool", "isUnsafe":"bool"},
    "constructor":{"induct":"name", "cidx":"nat", "numParams":"nat", "numFields":"nat", "isUnsafe":"bool"},
    "recursor":{"all":"names", "numParams":"nat", "numIndices":"nat", "numMotives":"nat",
                "numMinors":"nat", "rules":"rules", "k":"bool", "isUnsafe":"bool"},
}
DECL = {k:BASE | v for k,v in DECL.items()}
RULE = {"ctor":"name", "nfields":"nat", "rhs":"expr"}
GROUPS = {"types":"inductive", "ctors":"constructor", "recs":"recursor"}


def check(ok, error):
    if not ok:
        raise ValueError(error)


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def fields(obj, expected):
    check(type(obj) is dict and set(obj)==set(expected), f"field set on {list(obj) if type(obj) is dict else type(obj)}; expected {list(expected)}")


def no_duplicates(pairs):
    out = {}
    for k,v in pairs:
        if k in out: raise ValueError("duplicate JSON key: " + k)
        out[k] = v
    return out


def nat(value):
    check(type(value) is int and value>=0, "expected Nat")
    return value


def seq(value):
    check(type(value) is list, "expected Array")
    return value


def string(value):
    check(type(value) is str, "expected String")
    return value


def boolean(value):
    check(type(value) is bool, "expected Bool")
    return value


def span(b):
    return U64.pack(len(b))+b


def txt(s):
    return span(string(s).encode("utf-8"))


def number(i):
    i = nat(i)
    return span(i.to_bytes((i.bit_length()+7)//8, "big"))


def merkle(tag, body=b""):
    return hashlib.sha256(PREFIX[tag]+body).digest()


class Digests:
    """No resizing of a multiple-GB contiguous buffer or retention of raw expressions."""
    BLOCK = 1 << 16

    def __init__(self):
        self.blocks = []
        self.count = 0

    def put(self, index, digest):
        if type(index) is not int or index != self.count: raise ValueError("non-dense node ID")
        if index % self.BLOCK == 0: self.blocks.append(bytearray())
        self.blocks[-1].extend(digest)
        self.count += 1

    def ref(self, index):
        if type(index) is not int or not 0 <= index < self.count: raise ValueError("unknown/forward node reference")
        start = (index % self.BLOCK)*32
        return bytes(self.blocks[index // self.BLOCK][start:start+32])


class Index:
    def __init__(self, db):
        self.db = db
        self.names = Digests()
        self.levels = Digests()
        self.exprs = Digests()
        self.names.put(0, merkle("N0"))
        self.levels.put(0, merkle("L0"))
        self.parent = [None]
        self.part = [None]
        self.kinds = Counter()
        self.order = hashlib.sha256(b"LeanExport-declaration-order-v1\x00")

    def name_path(self, index):
        parts = []
        while index:
            parts.append(self.part[index])
            index = self.parent[index]
        return list(reversed(parts))

    def name(self, index, op, val):
        if op == "str":
            fields(val, ("pre","str"))
            part = string(val["str"])
            tag, data = "Ns", txt(part)
        elif op == "num":
            fields(val, ("pre","i"))
            part = nat(val["i"])
            tag, data = "Nn", number(part)
        else:
            raise ValueError("unknown name tag: " + op)
        p = val["pre"]
        self.names.put(index, merkle(tag, self.names.ref(p)+data))
        self.parent.append(p)
        self.part.append(part)

    def level(self, index, op, val):
        if op in ("max","imax"):
            check(len(seq(val))==2, "level pair arity")
            h = merkle("L"+op, self.levels.ref(val[0])+self.levels.ref(val[1]))
        elif op == "succ":
            h = merkle("Ls", self.levels.ref(val))
        elif op == "param":
            h = merkle("Lp", self.names.ref(val))
        else:
            raise ValueError("unknown level tag: " + op)
        self.levels.put(index,h)

    def app(self, index, fn, arg):
        self.exprs.put(index,merkle("Eapp", self.exprs.ref(fn)+self.exprs.ref(arg)))

    def expr(self, index, op, val):
        E,N,L = self.exprs.ref, self.names.ref, self.levels.ref
        if op == "app":
            fields(val,("arg","fn")); self.app(index, val["fn"], val["arg"]); return
        if op == "sort": data=L(val)
        elif op == "bvar": data=number(val)
        elif op == "strVal": data=txt(val)
        elif op == "natVal":
            check(re.fullmatch(r"0|[1-9][0-9]*",string(val)) is not None,"invalid natural literal")
            data=txt(val)
        elif op == "const":
            fields(val,("name","us")); us=seq(val["us"])
            data=N(val["name"])+U64.pack(len(us))+b"".join(L(i) for i in us)
        elif op in ("forallE","lam"):
            fields(val,("name","type","body","binderInfo"))
            data=N(val["name"])+E(val["type"])+E(val["body"])+ORD[val["binderInfo"]]
        elif op == "letE":
            fields(val,("name","type","value","body","nondep"))
            data=N(val["name"])+E(val["type"])+E(val["value"])+E(val["body"])+bytes([boolean(val["nondep"])])
        elif op == "proj":
            fields(val,("typeName","idx","struct"))
            data=N(val["typeName"])+number(val["idx"])+E(val["struct"])
        elif op == "mdata":
            fields(val,("data","expr"))
            check(type(val["data"]) is dict, "invalid metadata object")
            data=E(val["expr"])+U64.pack(len(val["data"]))+b"".join(txt(k)+txt(v) for k,v in sorted(val["data"].items()))
        else: raise ValueError("unknown expression tag: "+op)
        self.exprs.put(index,merkle("E"+op,data))

    def normalize(self, kind, v):
        if kind == "name": return self.names.ref(v).hex()
        if kind == "names": return [self.names.ref(i).hex() for i in seq(v)]
        if kind == "expr": return self.exprs.ref(v).hex()
        if kind == "bool": return boolean(v)
        if kind == "nat": return nat(v)
        if kind == "quotKind": check(v in ("type","ctor","lift","ind"),"quot kind")
        elif kind == "safety": check(v in ("safe","unsafe","partial"),"safety")
        elif kind == "hints":
            if type(v) is dict:
                fields(v, ("regular",)); nat(v["regular"])
            else: check(v in ("abbrev","opaque"), "reducibility hints")
        elif kind == "rules":
            return [self.normalize_fields(rule,RULE) for rule in seq(v)]
        else: raise ValueError("unknown field schema: "+kind)
        return v

    def normalize_fields(self, row, schema):
        fields(row,schema)
        return {k:self.normalize(t,row[k]) for k,t in schema.items()}

    def declaration(self, kind, val, block=None):
        out=self.normalize_fields(val,DECL[kind])
        name_hash=out.pop("name")
        if block is not None: out["inductiveBlock"] = block
        key=compact(self.name_path(val["name"]))  # typed components, not a dotted display string
        self.db.execute("INSERT INTO decl VALUES (?,?,?)",(key,kind,compact(out)))
        self.kinds[kind]+=1
        self.order.update(bytes.fromhex(name_hash))

    def record(self, row):
        check(type(row) is dict, "not an object")
        if len(row)==2:
            for tag,fn in (("in",self.name),("il",self.level),("ie",self.expr)):
                if tag in row:
                    op=next(k for k in row if k!=tag)
                    fn(row[tag],op,row[op]); return
        check(len(row)==1,"unknown record keys")
        op,val=next(iter(row.items()))
        if op=="inductive":
            fields(val,GROUPS)
            block={k:[self.names.ref(v["name"]).hex() for v in seq(members)] for k,members in val.items()}
            check(len(block["types"])>0,"empty mutual block")
            for k,kind in GROUPS.items():
                for member in val[k]: self.declaration(kind,member,block)
        elif op in ("thm","def","opaque","axiom","quot"):
            self.declaration(op,val)
        else: raise ValueError("unknown declaration tag: "+op)


def ingest(path, dbpath, expected, progress_step=5000000):
    started=time.monotonic()
    check(not dbpath.exists(),"existing index: "+str(dbpath))
    db=sqlite3.connect(dbpath)
    db.execute("PRAGMA cache_size=-12000")
    db.execute("CREATE TABLE decl(name TEXT PRIMARY KEY, kind TEXT NOT NULL, fields TEXT NOT NULL) WITHOUT ROWID")
    idx=Index(db)
    file_hash=hashlib.sha256()
    size=0
    lineno=0
    try:
        with path.open("rb", buffering=4*1024*1024) as stream:
            for lineno,raw in enumerate(stream,1):
                size+=len(raw);file_hash.update(raw)
                if lineno==1:
                    check(json.loads(raw,object_pairs_hook=no_duplicates)=={"meta":HEADER},"wrong or missing header");continue
                m=APP_LINE.fullmatch(raw)
                if m: idx.app(int(m[3]),int(m[2]),int(m[1]))
                else: idx.record(json.loads(raw,object_pairs_hook=no_duplicates))
                if progress_step and lineno%progress_step==0:
                    print(path.name,lineno,size,f"{time.monotonic()-started:.1f}s",flush=True)
        check(lineno>1,"empty file")
        hexdigest=file_hash.hexdigest()
        check(hexdigest==expected,"raw SHA mismatch: "+hexdigest)
        db.commit()
    except Exception as e:
        raise ValueError(f"{path.name} at line {lineno}: {e}") from e
    finally: db.close()
    return {"filename":path.name,"bytes":size,"sha256":hexdigest,"records":lineno,
            "names_including_anonymous":idx.names.count,"levels_including_zero":idx.levels.count,
            "expressions":idx.exprs.count,"declarations_by_kind":dict(sorted(idx.kinds.items())),
            "declarations":sum(idx.kinds.values()),"name_sequence_digest":idx.order.hexdigest(),
            "elapsed_seconds":round(time.monotonic()-started,3)}


def differences(a,b,path=""):
    if type(a) is not type(b): return [{"field":path,"left":a,"right":b}]
    if a==b: return []
    if type(a) is dict:
        out=[]
        for k in sorted(set(a)|set(b)):
            sub=(path+"." if path else "")+k
            if k not in a or k not in b: out.append({"field":sub,"missing_in":"left" if k not in a else "right"})
            else: out.extend(differences(a[k],b[k],sub))
        return out
    if type(a) is list and len(a)==len(b):
        return [row for i,(x,y) in enumerate(zip(a,b)) for row in differences(x,y,f"{path}[{i}]")]
    return [{"field":path,"left":a,"right":b}]


def compare(left,right):
    db=sqlite3.connect(left.as_uri()+"?mode=ro",uri=True)
    db.execute("ATTACH DATABASE ? AS other",(right.as_uri()+"?mode=ro",))
    names=lambda keys:[{"components":json.loads(name),"kind":kind} for name,kind in keys]
    def unique(t,u):
        return names(db.execute(f"SELECT a.name,a.kind FROM {t}.decl a LEFT JOIN {u}.decl b USING(name) WHERE b.name IS NULL ORDER BY a.name"))
    report={"left_only":unique("main","other"),"right_only":unique("other","main"),"different":[]}
    report["common"]=db.execute("SELECT count(*) FROM main.decl JOIN other.decl USING(name)").fetchone()[0]
    for name,ak,af,bk,bf in db.execute("SELECT a.name,a.kind,a.fields,b.kind,b.fields FROM main.decl a JOIN other.decl b USING(name) WHERE a.kind!=b.kind OR a.fields!=b.fields ORDER BY a.name"):
        ac,bc=json.loads(af),json.loads(bf)
        ac["declarationKind"]=ak;bc["declarationKind"]=bk
        report["different"].append({"components":json.loads(name),"kinds":[ak,bk],"fields":differences(ac,bc)})
    report["common_identical"]=report["common"]-len(report["different"])
    db.close()
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("left",type=Path);ap.add_argument("right",type=Path)
    ap.add_argument("--left-sha",required=True);ap.add_argument("--right-sha",required=True)
    ap.add_argument("--work",required=True,type=Path);ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args()
    check(not args.out.exists(),"output exists")
    args.work.mkdir(parents=True,exist_ok=False)
    a,b=(args.work.resolve()/f"{key}.sqlite" for key in ("left","right"))
    ra=ingest(args.left,a,args.left_sha)
    rb=ingest(args.right,b,args.right_sha)
    diff=compare(a,b)
    self_checks=[]
    for side,db,rec in (("left",a,ra),("right",b,rb)):
        d=compare(db,db)
        check(not d["different"] and not d["left_only"] and not d["right_only"] and
              d["common_identical"]==rec["declarations"],"self comparison failure")
        self_checks.append({"side":side,"common_identical":d["common_identical"]})
    check(ra["declarations"]==diff["common"]+len(diff["left_only"]),"left join count")
    check(rb["declarations"]==diff["common"]+len(diff["right_only"]),"right join count")
    output={"schema_lean":"4.35.0","schema_source_sha256":SCHEMA_SHA,
            "method":"Domain-separated SHA-256 structural Merkle hashes; ID-independent, includes binder names, flags and ordered fields. Declaration fields are compared using canonical JSON; references to other constants keep their names.",
            "checker_script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "utc":datetime.now(timezone.utc).isoformat(),"left":ra,"right":rb,"self_comparisons":self_checks,**diff}
    tmp=args.out.with_name(args.out.name+".partial")
    with tmp.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(output,stream,ensure_ascii=False,indent=2);stream.write("\n")
    tmp.rename(args.out)
    print(compact({"common":diff["common"],"left_only":len(diff["left_only"]),
                   "right_only":len(diff["right_only"]),"different":len(diff["different"])}),flush=True)


if __name__=="__main__":
    main()

