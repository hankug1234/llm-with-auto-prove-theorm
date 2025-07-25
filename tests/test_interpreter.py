import sys 
sys.path.append(".")
from auto_prove import Function, Var, Operation, Predicate, Constant

def test_interpreter():
    from auto_prove.interpreter import pre_modification_fol_interpreter as interpreter  
     # 1. 기본 유효   P(a),  ∀x( P(x) → Q(x) ) ⊢ Q(a)
    prem1 = Predicate("P", [Constant("a")])
    prem2 = (Operation.ALL, Var("x"),
            (Operation.IMPLIE,
            Predicate("P", [Var("x")]),
            Predicate("Q", [Var("x")])))
    goal  = Predicate("Q", [Constant("a")])
    premises, target = interpreter("P(a), ∀x( P(x) → Q(x) ) ⊢ Q(a)")
    assert premises == [prem1, prem2]
    assert target == goal
    # ----------------------------------------------
    # 2. 동일 변수 반복 (무효)  ∀x P(x) ⊢ Q(a)
    prem1 = (Operation.ALL, Var("x"), Predicate("P", [Var("x")]))
    goal  = Predicate("Q", [Constant("a")])    # entailment가 안 됨
    premises, target = interpreter("∀x P(x) ⊢ Q(a)")
    assert premises == [prem1]
    assert target == goal
    
    # ----------------------------------------------
    # 3. ∧ 도입  P(a) ∧ R(a) ⊢ R(a)
    prem1 = (Operation.AND,
            Predicate("P", [Constant("a")]),
            Predicate("R", [Constant("a")]))
    goal  = Predicate("R", [Constant("a")])
    premises, target = interpreter("P(a) ∧ R(a) ⊢ R(a)")
    assert premises == [prem1]  
    assert target == goal
    
    # ----------------------------------------------
    # 4. ∃ 제거  ∃y (R(y) ∧ P(y)) , ∀x (R(x) → Q(x)) ⊢ ∃z Q(z)
    prem1 = (Operation.SOME, Var("y"),
            (Operation.AND,
            Predicate("R", [Var("y")]),
            Predicate("P", [Var("y")])))
    prem2 = (Operation.ALL, Var("x"),
            (Operation.IMPLIE,
            Predicate("R", [Var("x")]),
            Predicate("Q", [Var("x")])))
    goal  = (Operation.SOME, Var("z"), Predicate("Q", [Var("z")]))
    premises, target = interpreter("∃y (R(y) ∧ P(y)) , ∀x (R(x) → Q(x)) ⊢ ∃z Q(z)")
    assert premises == [prem1, prem2]
    assert target == goal
    
    # ----------------------------------------------
    # 5. double-negation  ¬¬P(b) ⊢ P(b)
    prem1 = (Operation.NEG, (Operation.NEG, Predicate("P", [Constant("b")])))
    goal  = Predicate("P", [Constant("b")])
    premises, target = interpreter("¬¬P(b) ⊢ P(b)")
    assert premises == [prem1]
    assert target == goal
    
    # ----------------------------------------------
    # 6. De Morgan (무효)  ¬(P(a) ∧ Q(a)) ⊢ ¬P(a) ∨ ¬Q(a)   # 타블로가 닫히지 않음
    prem1 = (Operation.NEG,
            (Operation.AND,
            Predicate("P", [Constant("a")]),
            Predicate("Q", [Constant("a")])))
    goal  = (Operation.OR,
            (Operation.NEG, Predicate("P", [Constant("a")])),
            (Operation.NEG, Predicate("Q", [Constant("a")])))
    premises, target = interpreter("¬(P(a) ∧ Q(a)) ⊢ ¬P(a) ∨ ¬Q(a)")
    assert premises == [prem1]
    assert target == goal
    
    # ----------------------------------------------
    # 7. 조건부의 역 (무효)  P(a) → Q(a)  ⊢ Q(a) → P(a)
    prem1 = (Operation.IMPLIE,
            Predicate("P", [Constant("a")]),
            Predicate("Q", [Constant("a")]))
    goal  = (Operation.IMPLIE,
            Predicate("Q", [Constant("a")]),
            Predicate("P", [Constant("a")]))
    premises, target = interpreter("P(a) → Q(a) ⊢ Q(a) → P(a)")
    assert premises == [prem1]
    
    
    # ----------------------------------------------
    # 8. ∀/∃ 혼합   ∀x (P(x) → ∃y R(x,y)) , P(c) ⊢ ∃y R(c,y)
    prem1 = (Operation.ALL, Var("x"),
            (Operation.IMPLIE,
            Predicate("P", [Var("x")]),
            (Operation.SOME, Var("y"), Predicate("R", [Var("x"), Var("y")]))))
    prem2 = Predicate("P", [Constant("c")])
    goal  = (Operation.SOME, Var("y"), Predicate("R", [Constant("c"), Var("y")]))
    premises, target = interpreter("∀x (P(x) → ∃y R(x,y)) , P(c) ⊢ ∃y R(c,y)")
    assert premises == [prem1, prem2]
    assert target == goal
    
if __name__ == "__main__":
    from auto_prove.interpreter import pre_modification_fol_interpreter as interpreter  
    print(interpreter("∀x (P(x) → ∃y R(x,y)) , P(c) ⊢ ∃y R(c,y)"))