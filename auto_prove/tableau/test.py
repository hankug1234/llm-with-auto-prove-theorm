import itertools, sys 
sys.path.append(".")
from auto_prove import unify_list, Formula, Notated, Term, Function, Var, Operation, Predicate, Constant, Atom
from auto_prove.tableau import prove_with_premises

if __name__ == "__main__":
    
    tableaus = []
    
    prem1 = Predicate("P", [Constant("a")])
    prem2 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Predicate("P", [Var("x")]),
            Predicate("Q", [Var("x")])))

    goal  = Predicate("Q", [Constant("a")])

    prove_with_premises([prem1, prem2], goal, qdepth=2)
    
    # ─────────────────────────────────────────────
    #  무한 등식-루프를 일으키는 간단한 예제
    # ─────────────────────────────────────────────
    #  전제 S
    prem1 = Predicate("P", [Constant("a")])                          # ① P(a)
    prem2 = (
        Operation.ALL, "x",                                           # ② ∀x (P(x) → P(f(x)))
        (Operation.IMPLIE,
        Predicate("P", [Var("x")]),
        Predicate("P", [Function("f", [Var("x")])]))
    )
    prem3 = (Operation.EQUAL,                                         # ③ a = f(a)
            Constant("a"),
            Function("f", [Constant("a")]))

    #  결론을 아무거나 두면 되지만, 예컨대 Q(a) 를 증명하려고 한다고 하자
    goal = Predicate("Q", [Constant("a")])

    # 증명 시도
    prove_with_premises([prem1,prem2,prem3], goal, qdepth=10)
    
    print("-------- 2 / 6 / 7 -------------- 증명 실패 여야 함")
    
    # ----------------------------------------------
    # 1. 기본 유효   P(a),  ∀x( P(x) → Q(x) ) ⊢ Q(a)
    prem1 = Predicate("P", [Constant("a")])
    prem2 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Predicate("P", [Var("x")]),
            Predicate("Q", [Var("x")])))
    goal  = Predicate("Q", [Constant("a")])
    tableaus.append(prove_with_premises([prem1,prem2], goal, qdepth=5))
    # ----------------------------------------------
    # 2. 동일 변수 반복 (무효)  ∀x P(x) ⊬ Q(a)
    prem1 = (Operation.ALL, "x", Predicate("P", [Var("x")]))
    goal  = Predicate("Q", [Constant("a")])    # entailment가 안 됨
    tableaus.append(prove_with_premises([prem1], goal, qdepth=5))
    # ----------------------------------------------
    # 3. ∧ 도입  P(a) ∧ R(a) ⊢ R(a)
    prem1 = (Operation.AND,
            Predicate("P", [Constant("a")]),
            Predicate("R", [Constant("a")]))
    goal  = Predicate("R", [Constant("a")])
    tableaus.append(prove_with_premises([prem1], goal, qdepth=5))
    # ----------------------------------------------
    # 4. ∃ 제거  ∃y (R(y) ∧ P(y)) , ∀x (R(x) → Q(x)) ⊢ ∃z Q(z)
    prem1 = (Operation.SOME, "y",
            (Operation.AND,
            Predicate("R", [Var("y")]),
            Predicate("P", [Var("y")])))
    prem2 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Predicate("R", [Var("x")]),
            Predicate("Q", [Var("x")])))
    goal  = (Operation.SOME, "z", Predicate("Q", [Var("z")]))
    tableaus.append(prove_with_premises([prem1,prem2], goal, qdepth=5))
    # ----------------------------------------------
    # 5. double-negation  ¬¬P(b) ⊢ P(b)
    prem1 = (Operation.NEG, (Operation.NEG, Predicate("P", [Constant("b")])))
    goal  = Predicate("P", [Constant("b")])
    tableaus.append(prove_with_premises([prem1], goal, qdepth=5))
    # ----------------------------------------------
    # 6. De Morgan (무효)  ¬(P(a) ∧ Q(a)) ⊢ ¬P(a) ∨ ¬Q(a)   # 타블로가 닫히지 않음
    prem1 = ("neg",
            (Operation.AND,
            Predicate("P", [Constant("a")]),
            Predicate("Q", [Constant("a")])))
    goal  = (Operation.OR,
            ("neg", Predicate("P", [Constant("a")])),
            ("neg", Predicate("Q", [Constant("a")])))
    tableaus.append(prove_with_premises([prem1], goal, qdepth=5))
    # ----------------------------------------------
    # 7. 조건부의 역 (무효)  P(a) → Q(a)  ⊬ Q(a) → P(a)
    prem1 = (Operation.IMPLIE,
            Predicate("P", [Constant("a")]),
            Predicate("Q", [Constant("a")]))
    goal  = (Operation.IMPLIE,
            Predicate("Q", [Constant("a")]),
            Predicate("P", [Constant("a")]))
    tableaus.append(prove_with_premises([prem1], goal, qdepth=5))
    
    # ----------------------------------------------
    # 8. ∀/∃ 혼합   ∀x (P(x) → ∃y R(x,y)) , P(c) ⊢ ∃y R(c,y)
    prem1 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Predicate("P", [Var("x")]),
            (Operation.SOME, "y", Predicate("R", [Var("x"), Var("y")]))))
    prem2 = Predicate("P", [Constant("c")])
    goal  = (Operation.SOME, "y", Predicate("R", [Constant("c"), Var("y")]))
    tableaus.append(prove_with_premises([prem1,prem2], goal, qdepth=5))
    # ----------------------------------------------
    
    
    
    