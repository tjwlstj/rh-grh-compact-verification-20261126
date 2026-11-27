"""Check the final declaration comparison with independent read-only SQL queries."""
import json
from pathlib import Path
import sqlite3
import sys

index_dir, result_file = map(Path, sys.argv[1:])
result = json.loads(result_file.read_bytes())
open_uri = lambda name: (index_dir / (name + ".sqlite")).resolve().as_uri() + "?mode=ro"
with sqlite3.connect(open_uri("left"), uri=True) as conn:
    conn.execute("attach database ? as loc", (open_uri("right"),))
    for schema in ("main", "loc"):
        assert conn.execute(f"pragma {schema}.integrity_check").fetchall() == [("ok",)]
    counts = conn.execute("""
        select count(*), sum(a.kind = b.kind), sum(json_extract(a.fields,'$.type') = json_extract(b.fields,'$.type')),
               sum(a.kind = b.kind and a.fields = b.fields)
        from main.decl as a join loc.decl as b on a.name=b.name
    """).fetchone()
    only_mit, only_local = [conn.execute(f"select count(*) from (select name from {a}.decl except select name from {b}.decl)").fetchone()[0] for a,b in (("main","loc"),("loc","main"))]
    assert (counts[0],counts[3],only_mit,only_local)==(result["common"],result["common_identical"],len(result["left_only"]),len(result["right_only"]))
    changed = []
    for name, kind_a, kind_b, fields_a, fields_b in conn.execute("select m.name,m.kind,l.kind,m.fields,l.fields from main.decl m join loc.decl l using(name) where m.kind!=l.kind or m.fields!=l.fields order by m.name"):
        a,b=json.loads(fields_a),json.loads(fields_b)
        unequal_top_level = [k for k in sorted(set(a)|set(b)) if k not in a or k not in b or a[k]!=b[k]]
        changed.append({"name":json.loads(name),"kinds":[kind_a,kind_b],"unequalTopLevelFields":unequal_top_level})
    assert [r["name"] for r in changed] == [r["components"] for r in result["different"]]
    print(json.dumps({"commonNames":counts[0],"equalKinds":counts[1],"equalTypes":counts[2],"equalDeclarations":counts[3],"onlyMIT":only_mit,"onlyLocal":only_local,"changed":changed},ensure_ascii=True))
