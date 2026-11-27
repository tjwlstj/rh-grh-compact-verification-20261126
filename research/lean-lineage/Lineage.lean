import Main

/- Local read-only dependency audit. Imported constants are identified by kernel Name,
   never by a substring of their pretty-printed names. No declaration is unfolded. -/
open Lean Elab Command

namespace LocalLineage

def targets : Array Name := #[
  `riemannHypothesis, `riemannZeta_eq_zero_re, `LFunction_ne_zero_of_half_lt_re,
  `LFunction_eq_zero_re, `LFunction_eq_zero_re_of_isPrimitive]

def parentName := `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight
def needle := parentName.str "_proof_1_4"
def otherSeeds : Array Name := #[
  parentName, needle, `Nat.add_comm, `RiemannHypothesis, `RiemannZetaZerosOnLine,
  `DirichletLNonvanishingRightOfHalf, `DirichletLZerosOnLine,
  `PrimitiveDirichletLZerosOnLine]

def edgeNames := #["type","value","inductiveConstructors","mutualInductives",
  "constructorInductive","recursorInductives","recursorRuleConstructors",
  "recursorRuleRhs","mutualValues"]

def classify : ConstantInfo → String
  | .axiomInfo _ => "axiom"
  | .defnInfo _ => "definition"
  | .thmInfo _ => "theorem"
  | .opaqueInfo _ => "opaque"
  | .quotInfo _ => "quotientPrimitive"
  | .inductInfo _ => "inductive"
  | .ctorInfo _ => "constructor"
  | .recInfo _ => "recursor"

def edges (c : ConstantInfo) : Array (Array Name) := Id.run do
  let t := c.type.getUsedConstants
  let v := ((c.value? (allowOpaque := true)).map Expr.getUsedConstants).getD #[]
  let mut g : Array (Array Name) := #[t, v, #[], #[], #[], #[], #[], #[], #[]]
  match c with
  | .inductInfo i => g := (g.set! 2 i.ctors.toArray).set! 3 i.all.toArray
  | .ctorInfo i => g := g.set! 4 #[i.induct]
  | .recInfo i =>
    g := g.set! 5 i.all.toArray
    g := g.set! 6 (i.rules.map (·.ctor)).toArray
    g := g.set! 7 (i.rules.toArray.flatMap fun rule => rule.rhs.getUsedConstants)
  | .defnInfo i => g := g.set! 8 i.all.toArray
  | .thmInfo i => g := g.set! 8 i.all.toArray
  | .opaqueInfo i => g := g.set! 8 i.all.toArray
  | _ => pure ()
  return g

def emitGraph (ke : Kernel.Environment) (seeds : Array Name) (file : System.FilePath) : IO Unit := do
  let f ← IO.FS.Handle.mk file .write
  let mut table : Std.HashMap Name Nat := {}
  let mut queue : Array Name := #[]
  for seed in seeds do
    if !table.contains seed then
      table := table.insert seed queue.size
      queue := queue.push seed
  f.putStrLn (Json.mkObj [("header", toJson 1), ("edges", toJson edgeNames),
    ("seeds", toJson (queue.map Name.toString))]).compress
  let mut idx := 0
  let mut absent := 0
  while idx < queue.size do
    let name := queue[idx]!
    let opt := ke.find? name
    let kind := (opt.map classify).getD "missing"
    let groups := (opt.map edges).getD #[]
    if opt.isNone then absent := absent + 1
    let mut result : Array (Array Nat) := #[]
    for refs in groups do
      let mut dest : Array Nat := #[]
      for dep in refs do
        if let some id := table[dep]? then
          dest := dest.push id
        else
          let id := queue.size
          table := table.insert dep id
          queue := queue.push dep
          dest := dest.push id
      result := result.push dest
    let record := Json.arr #[toJson idx, toJson name.toString, toJson kind, toJson result]
    f.putStrLn record.compress
    idx := idx + 1
    if idx % 4096 == 0 then f.flush
  f.putStrLn (Json.mkObj [("done", toJson idx), ("missing", toJson absent)]).compress
  f.flush
  IO.println s!"LINEAGE_FINISHED vertices={idx} unresolved={absent}"
  if absent != 0 then throw (IO.userError s!"Unresolved declarations: {absent}")

run_cmd do
  let env ← getEnv
  let ke := (env.setExporting false).checked.get
  let mut seeds := targets ++ otherSeeds
  let candidates := #[parentName.str "_proof_1"] ++ ((Array.range 96).map fun i =>
    parentName.str s!"_proof_1_{i}")
  for name in candidates do
    if (ke.find? name).isSome then seeds := seeds.push name
  for n in seeds do
    unless (ke.find? n).isSome do throwError "Required kernel declaration missing: {n}"
  let some focus := ke.find? needle | throwError "Focus declaration missing"
  let prettyType ← liftTermElabM <| Meta.ppExpr focus.type
  liftIO (IO.FS.writeFile "lineage-needle-type.txt" (prettyType.pretty 120 ++ "\n"))
  liftIO (emitGraph ke seeds "lineage-graph-v1.ndjson")

end LocalLineage
