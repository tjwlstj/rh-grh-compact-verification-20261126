import New.Endgame.PrimeError

namespace Chesi.ProjectWeights

local instance : Fact (Nat.Prime 9239) := ⟨by norm_num⟩

theorem zero_weight : lambdaClass 9239 18480 18481 = 0 := by
  unfold lambdaClass
  rw [chiK_eq_legendreSym]
  norm_num

theorem doubled_weight : lambdaClass 9239 18480 258721 = 2 * Real.log 258721 := by
  have hp : Nat.Prime 258721 := by norm_num
  have hm : 258721 ∈ {n : ℕ | (n : ZMod 18480) = 1} := by
    change ((258721 : ℕ) : ZMod 18480) = 1
    calc
      ((258721 : ℕ) : ZMod 18480) = ((1 : ℕ) : ZMod 18480) :=
        (ZMod.natCast_eq_natCast_iff 258721 1 18480).2 (by rfl)
      _ = 1 := Nat.cast_one
  have hr : ArithmeticFunction.vonMangoldt.residueClass (1 : ZMod 18480) 258721 =
      Real.log (258721 : ℝ) := by
    change {n : ℕ | (n : ZMod 18480) = 1}.indicator (ArithmeticFunction.vonMangoldt ·) 258721 = _
    rw [Set.indicator_of_mem hm, ArithmeticFunction.vonMangoldt_apply_prime hp] <;> norm_num
  unfold lambdaClass
  rw [hr, chiK_eq_legendreSym]
  norm_num <;> ring

#print axioms zero_weight
#print axioms doubled_weight

end Chesi.ProjectWeights
