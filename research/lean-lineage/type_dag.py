"""Read the verified local module as an inert byte stream and check the focus type DAG."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
U = struct.Struct("<Q")

class Region:
    def __init__(self, path):
        self.data = path.read_bytes()
        if self.data[:7] != b'olean\x02\x01':
            raise ValueError('expected OLean format 2, GMP')
        self.base = self.u(80)
        self.root = self.u(88)
        self.size = len(self.data)
    def u(self,o): return U.unpack_from(self.data,o)[0]
    def offset(self,v):
        o = v-self.base
        if v&7 or not 96<=o<self.size: raise ValueError(('bad position',o))
        return o
    def tag(self,v): return self.data[self.offset(v)+7]
    def field(self,v,n): return self.u(self.offset(v)+8+8*n)
    def string(self,v):
        o=self.offset(v)
        if self.tag(v)!=249:raise ValueError('not a string')
        n=self.u(o+8)
        if n<1 or self.data[o+32+n-1]!=0:raise ValueError('bad string')
        return self.data[o+32:o+32+n-1].decode()
    def name(self,v):
        if v==1:return ''
        t=self.tag(v)
        if t not in (1,2):raise ValueError('not a name')
        prefix=self.name(self.field(v,0));last=self.field(v,1)
        component=self.string(last) if t==1 else str(last>>1)
        return prefix+'.'+component if prefix else component
    def array(self,v):
        o=self.offset(v)
        if self.tag(v)!=246:raise ValueError('not a ref array')
        n=self.u(o+8)
        return [self.u(o+24+8*i) for i in range(n)]
    def decl(self,v):
        info=self.field(v,0)
        cv=self.field(info,0)
        return self.name(self.field(cv,0)), [self.field(cv,i) for i in (0,1,2)], self.kind_members(info), self.tag(v)
    def expr(self,v):
        """Kind, non-expression fields, expression children, following con-leche's Expr reader."""
        tag=self.tag(v)
        if tag==10:return self.expr(self.field(v,1))
        layouts={0:('bvar',(0,),()),3:('sort',(0,),()),4:('const',(0,1),()),
                 5:('app',(),(0,1)),6:('lam',(),(1,2)),7:('forall',(),(1,2)),
                 8:('let',(),(1,2,3)),9:('lit',(0,),()),11:('proj',(0,1),(2,))}
        kind,atoms,children=layouts[tag]
        return kind,tuple(self.field(v,i) for i in atoms),tuple(self.field(v,i) for i in children)
    def head(self,v):
        k,atoms,kids=self.expr(v)
        nargs=0
        while k=='app':
            nargs+=1
            k,atoms,kids=self.expr(kids[0])
        if k=='const':name=self.name(atoms[0])
        elif k=='bvar':name=f'bound variable {atoms[0]>>1}'
        else:name=k
        return {'head':name,'applicationArity':nargs}
    def kind_members(self,v):
        o=self.offset(v); n=self.data[o+6]
        return [self.field(v,i) for i in range(n)]
    def node(self,v):
        o=self.offset(v); t=self.tag(v); b=self.data
        if t<=243:
            n=b[o+6];size=int.from_bytes(b[o+4:o+6],'little')
            if size<8+8*n or o+size>len(b):raise ValueError(('ctor layout',o))
            return b[o:o+8]+b[o+8+8*n:o+size],self.kind_members(v)
        if t==246:
            n=self.u(o+8)
            return b[o:o+24],self.array(v)
        if t==249:
            return b[o:o+32+self.u(o+8)],[]
        if t==250:
            n=abs(int.from_bytes(b[o+12:o+16],'little',signed=True))
            if self.u(o+16)!=v+24:raise ValueError(('mpz',o))
            return b[o:o+16]+b[o+24:o+24+8*n],[]
        raise ValueError(('unknown object shape',t,o))

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_PAIRS = 700_000
MAX_ARRAY_ITEMS = 150_000
PRODUCER = b"4.35.0".ljust(33, b"\0") + b"eb6cafb7290e8bd5f2937522d8d804f58f02bafc"
KINDS = ("axiom", "definition", "theorem", "opaque", "quot", "inductive", "constructor", "recursor")
EXTRA_FIELDS = (
    (), ("value", "hints", "all"), ("value", "all"), ("value", "all"), (),
    ("numParams", "numIndices", "all", "ctors", "numNested"),
    ("induct", "cidx", "numParams", "numFields"),
    ("all", "numParams", "numIndices", "numMotives", "numMinors", "rules"),
)


class Unsupported(ValueError):
    pass


class InputRegion(Region):
    def __init__(self, path):
        if path.stat().st_size > MAX_FILE_BYTES:
            raise Unsupported("file exceeds the per-input size budget")
        super().__init__(path)
        if self.size < 96 or self.size % 8 or self.base % 8 or self.base + self.size >= 2**64:
            raise Unsupported("invalid or unsupported region header")
        if self.data[7:80] != PRODUCER:
            raise Unsupported("unsupported Lean version or build")

    def bounds(self, address, size):
        offset = self.offset(address)
        if size < 0 or offset + size > self.size:
            raise Unsupported("object extends beyond the public .olean region")

    def array(self, address):
        self.bounds(address, 24)
        count = self.u(self.offset(address) + 8)
        if count > MAX_ARRAY_ITEMS:
            raise Unsupported("reference array exceeds the item budget")
        self.bounds(address, 24 + 8 * count)
        return super().array(address)

    def node(self, address):
        self.bounds(address, 8)
        pos = self.offset(address)
        tag = self.tag(address)
        if tag == 249:
            self.bounds(address, 32)
            size = self.u(pos + 8)
            self.bounds(address, 32 + size)
            if not size or self.data[pos + 32 + size - 1] != 0:
                raise Unsupported("invalid string terminator")
        elif tag == 250:
            self.bounds(address, 24)
            limbs = abs(int.from_bytes(self.data[pos + 12:pos + 16], "little", signed=True))
            self.bounds(address, 24 + 8 * limbs)
        payload, children = super().node(address)
        for child in children:
            if not child & 1 and self.offset(child) >= pos:
                raise Unsupported("unsupported cross-region or non-backward reference")
        return payload, children

    def ctor(self, address, tag, count):
        if self.tag(address) != tag:
            raise Unsupported("unexpected constructor tag")
        payload, fields = self.node(address)
        if len(fields) != count:
            raise Unsupported("unexpected constructor field count")
        return payload, fields

    def name_key(self, address):
        parts = []
        while address != 1:
            tag = self.tag(address)
            if tag not in (1, 2):
                raise Unsupported("unsupported declaration name")
            _, (prefix, last) = self.ctor(address, tag, 2)
            if tag == 1:
                self.node(last)
                component = self.string(last)
            elif last & 1:
                component = last >> 1
            else:
                raise Unsupported("unsupported large numeric name component")
            parts.append(component)
            address = prefix
        return tuple(reversed(parts))

    def declarations(self, root_fields):
        _, names = self.node(root_fields[1])
        _, records = self.node(root_fields[2])
        if any(self.tag(root_fields[i]) != 246 for i in (1, 2)) or len(names) != len(records):
            raise Unsupported("unsupported declaration/name array shape")
        result = {}
        for published_name, record in zip(names, records):
            tag = self.tag(record)
            if tag >= len(KINDS):
                raise Unsupported("unsupported declaration kind")
            _, (body,) = self.ctor(record, tag, 1)
            _, fields = self.ctor(body, 0, 1 + len(EXTRA_FIELDS[tag]))
            _, (name, levels, decl_type) = self.ctor(fields[0], 0, 3)
            key = self.name_key(name)
            if key in result or self.name_key(published_name) != key:
                raise Unsupported("ambiguous or inconsistent declaration name index")
            result[key] = (record, tag, body, fields, (name, levels, decl_type))
        return result



def check(olean, expected_dir):
    region=InputRegion(olean.resolve(strict=True))
    name="HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4"
    if hashlib.sha256(region.data).hexdigest()!="5bed4c44eda5e7e797137cae4a9943deb4d3f559bbcadc15b42b69df3d5f57b4":
        raise ValueError("Unexpected locally built module")
    records=region.declarations(region.node(region.root)[1])
    _,kind,_,_,(_,_,root)=records[tuple(name.split("."))]
    if kind!=2: raise ValueError("Expected a theorem")
    ids={root:0}
    order=[root]
    nodes=[]
    for addr in order:
        scalar,children=region.node(addr)
        refs=[]
        for child in children:
            if child & 1:
                refs.append(["immediate",child])
            else:
                if child not in ids:
                    ids[child]=len(order)
                    order.append(child)
                refs.append(["id",ids[child]])
        nodes.append([scalar.hex(),refs])
    target=root
    binders=[]
    while region.expr(target)[0]=="forall":
        t=region.field(target,1)
        binders.append({"binder":region.name(region.field(target,0)),"typeHead":region.head(t)})
        target=region.field(target,2)
    data={"format":"olean-v2-local-type-object-dag-1","root":0,"nodes":nodes}
    raw=(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n").encode()
    if raw != (expected_dir/"focus-type-dag.json").read_bytes():
        raise ValueError("Type DAG bytes differ from published reference")
    summary={"constant":name,"kind":"theorem","moduleSha256":hashlib.sha256(region.data).hexdigest(),
             "kernelTypeGraphFile":"focus-type-dag.json","kernelTypeGraphSha256":hashlib.sha256(raw).hexdigest(),
             "kernelTypeGraphBytes":len(raw),"serializedReachableObjects":len(nodes),
             "forallBinders":binders,"bodyHeadAfterForalls":region.head(target)}
    def direct_expr_focus(address):
        stack=[address]
        visited=set()
        while stack:
            cur=stack.pop()
            if cur in visited: continue
            visited.add(cur)
            kind,atoms,children=region.expr(cur)
            if kind in ("const","proj") and region.name_key(atoms[0])==tuple(name.split(".")):
                return True
            stack.extend(children)
        return False

    direct=[]
    for key,(_,tag,_,fields,(_,_,decl_type)) in records.items():
        references=[]
        if direct_expr_focus(decl_type):
            references.append("type")
        if tag in (1,2,3) and direct_expr_focus(fields[1]):
            references.append("value")
        if references:
            direct.append({"name":".".join(str(part) for part in key),"fields":references})
    summary["directFocusCallersWithinSourceModule"]=direct
    summary["sourceModuleDeclarationsChecked"]=len(records)
    if summary != json.loads((expected_dir/"focus-type-structure.json").read_bytes()):
        raise ValueError("Type structure or module-wide direct callers differ")
    print(json.dumps({"moduleBytes":region.size, "verifiedTypeDagSha256":summary["kernelTypeGraphSha256"], "directCallers":direct}))

if __name__ == "__main__":
    cmd=argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("--olean",required=True,type=Path,help="directly built JointHarmonicUnique.olean")
    cmd.add_argument("--expected-dir",default=HERE,type=Path)
    args=cmd.parse_args()
    check(args.olean,args.expected_dir)
