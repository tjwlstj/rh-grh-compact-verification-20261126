import Statements

/-- The four author predicates are checked at their original names. -/
theorem auditRH : RiemannZetaZerosOnLine = _root_.RiemannHypothesis := rfl

theorem auditHalfPlane : DirichletLNonvanishingRightOfHalf =
  (∀ (q : ℕ) [NeZero q] (χ : DirichletCharacter ℂ q) (z : ℂ),
    (1 / 2 : ℝ) < z.re → (χ ≠ 1 ∨ z ≠ 1) → DirichletCharacter.LFunction χ z ≠ 0) := rfl

theorem auditStrip : DirichletLZerosOnLine =
  (∀ (q : ℕ) [NeZero q] (χ : DirichletCharacter ℂ q) (z : ℂ),
    (0 : ℝ) < z.re → z.re < 1 → DirichletCharacter.LFunction χ z = 0 →
    z.re = (1 / 2 : ℝ)) := rfl

theorem auditPrimitive : PrimitiveDirichletLZerosOnLine =
  (∀ (q : ℕ) [NeZero q] (χ : DirichletCharacter ℂ q), χ.IsPrimitive →
    ∀ z : ℂ, (0 : ℝ) < z.re → z.re < 1 → DirichletCharacter.LFunction χ z = 0 →
      z.re = (1 / 2 : ℝ)) := rfl

#print axioms auditRH
#print axioms auditHalfPlane
#print axioms auditStrip
#print axioms auditPrimitive
