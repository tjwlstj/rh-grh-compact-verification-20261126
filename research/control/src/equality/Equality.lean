import Init

theorem pointwise_proofs_equal (P : Prop) (a b : P) : a = b := rfl

theorem witness_bodies_equal :
    (fun (P : Prop) (a b : P) => a) = (fun (P : Prop) (a b : P) => b) := rfl

#print axioms pointwise_proofs_equal
#print axioms witness_bodies_equal
