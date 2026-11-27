import Init

theorem witness (P : Prop) (a b : P) : P := b

theorem result (P : Prop) (a b : P) : P := witness P a b

#print axioms witness
#print axioms result
