import json
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
import unittest

HERE = Path(__file__).resolve().parent
core = runpy.run_path(str(HERE / "replay.py"))

class TestLineage(unittest.TestCase):
    def test_primary_structural_and_first_field(self):
        names = ["root","bridge","focus","mate","unrelated"]
        kinds = ["theorem"] * len(names)
        def group(t=(),v=(),m=()):
            return (t,v,(),(),(),(),(),(),m)
        groups = [group((3,),(1,)),group(v=(2,)),group(),group(v=(1,)),group(m=(2,))]
        for fields,start,first,wanted in (
            ((0,1),0,None,2), ((0,1),0,(0,),3), ((0,1),4,None,None),
            ((0,1),2,(0,),None), (tuple(range(9)),4,None,1)
        ):
            d = core["reversed_distances"](groups,fields,2)
            w = core["shortest"](start,first,fields,d,2,names,kinds,groups)
            self.assertEqual(w["length"] if w is not None else None, wanted)
            self.assertEqual(core["forward_distance"](groups,start,first,fields,2),wanted)

    def test_truncated_graph_and_missing_vertices_rejected(self):
        header = {"header":1,"edges":core["FIELDS"],"seeds":[]}
        row = [0,"n","theorem",[[] for _ in core["FIELDS"]]]
        with TemporaryDirectory() as temp:
            file = Path(temp)/"data"
            for rows in ((header,row),(header,row,{"done":1,"missing":1})):
                file.write_bytes(("\n".join(json.dumps(r) for r in rows)+"\n").encode())
                with self.assertRaises(ValueError):
                    core["read_graph"](file)

if __name__=="__main__":
    unittest.main()
