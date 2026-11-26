import Mathlib.Tactic.NormNum.LegendreSymbol
import Mathlib.Tactic.NormNum.Prime

namespace Chesi.PrimeWeight

local instance : Fact (Nat.Prime 9239) := ⟨by norm_num⟩

theorem primes_and_residues :
    Nat.Prime 18481 ∧ Nat.Prime 258721 ∧
    18481 % 18480 = 1 ∧ 258721 % 18480 = 1 ∧ 9239 = 18480 / 2 - 1 := by
  norm_num

theorem two_weights :
    (1 - legendreSym 9239 18481 = (0 : ℤ)) ∧
    (1 - legendreSym 9239 258721 = (2 : ℤ)) := by
  norm_num

#print axioms primes_and_residues
#print axioms two_weights

end Chesi.PrimeWeight
