import sys 
sys.path.append(".")
from auto_prove import Function, Var, Operation, Predicate, Constant
from auto_prove.tableau import Tableau

def test_prove_with_premises():
    tableau_prover = Tableau()
    prove_with_premises = tableau_prover.prove
    
    # -------- 2 / 6 / 7 -------------- 증명 실패 여야 함
    
    # ----------------------------------------------
    # 1. 기본 유효   P(a),  ∀x( P(x) → Q(x) ) ⊢ Q(a)
    prem1 = Predicate("P", [Constant("a")])
    prem2 = (Operation.ALL, Var("x"),
            (Operation.IMPLIE,
            Predicate("P", [Var("x")]),
            Predicate("Q", [Var("x")])))
    goal  = Predicate("Q", [Constant("a")])
    assert True == prove_with_premises([prem1,prem2], goal, qdepth=5)[0]
    # ----------------------------------------------
    # 2. 동일 변수 반복 (무효)  ∀x P(x) ⊬ Q(a)
    prem1 = (Operation.ALL, Var("x"), Predicate("P", [Var("x")]))
    goal  = Predicate("Q", [Constant("a")])    # entailment가 안 됨
    assert False == prove_with_premises([prem1], goal, qdepth=5)[0]
    # ----------------------------------------------
    # 3. ∧ 도입  P(a) ∧ R(a) ⊢ R(a)
    prem1 = (Operation.AND,
            Predicate("P", [Constant("a")]),
            Predicate("R", [Constant("a")]))
    goal  = Predicate("R", [Constant("a")])
    assert True == prove_with_premises([prem1], goal, qdepth=5)[0]
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
    assert True == prove_with_premises([prem1,prem2], goal, qdepth=5)[0]
    # ----------------------------------------------
    # 5. double-negation  ¬¬P(b) ⊢ P(b)
    prem1 = (Operation.NEG, (Operation.NEG, Predicate("P", [Constant("b")])))
    goal  = Predicate("P", [Constant("b")])
    assert True == prove_with_premises([prem1], goal, qdepth=5)[0]
    # ----------------------------------------------
    # 6. De Morgan (무효)  ¬(P(a) ∧ Q(a)) ⊢ ¬P(a) ∨ ¬Q(a)   # 타블로가 닫히지 않음
    prem1 = (Operation.NEG,
            (Operation.AND,
            Predicate("P", [Constant("a")]),
            Predicate("Q", [Constant("a")])))
    goal  = (Operation.OR,
            (Operation.NEG, Predicate("P", [Constant("a")])),
            (Operation.NEG, Predicate("Q", [Constant("a")])))
    assert True == prove_with_premises([prem1], goal, qdepth=5)[0]
    # ----------------------------------------------
    # 7. 조건부의 역 (무효)  P(a) → Q(a)  ⊬ Q(a) → P(a)
    prem1 = (Operation.IMPLIE,
            Predicate("P", [Constant("a")]),
            Predicate("Q", [Constant("a")]))
    goal  = (Operation.IMPLIE,
            Predicate("Q", [Constant("a")]),
            Predicate("P", [Constant("a")]))
    assert False == prove_with_premises([prem1], goal, qdepth=5)[0]
    
    # ----------------------------------------------
    # 8. ∀/∃ 혼합   ∀x (P(x) → ∃y R(x,y)) , P(c) ⊢ ∃y R(c,y)
    prem1 = (Operation.ALL, Var("x"),
            (Operation.IMPLIE,
            Predicate("P", [Var("x")]),
            (Operation.SOME, Var("y"), Predicate("R", [Var("x"), Var("y")]))))
    prem2 = Predicate("P", [Constant("c")])
    goal  = (Operation.SOME, Var("y"), Predicate("R", [Constant("c"), Var("y")]))
    assert True == prove_with_premises([prem1,prem2], goal, qdepth=5)[0]
    # ----------------------------------------------
    
        
if __name__ == "__main__":
        from auto_prove.interpreter import pre_modification_fol_interpreter as interpreter  
        world_rules = [
        ("∀x (Human(x) → Mortal(x))","Humans are mortal."),
        ("¬(Dead(x) ∧ Alive(x))","Death and life cannot exist simultaneously."),
        ("∀x (Wizard(x) → CanUseMagic(x))","Wizards can use magic."),
        ("¬(Orc(x) ∧ Human(x))","Orcs and humans are distinct races."),
        ("∀x (EnemyOf(x, y) → ¬FriendOf(x, y))","One cannot be both an enemy and a friend at the same time.")
        ] 
        tableau_prover = Tableau()
        prove_with_premises = tableau_prover.prove
        premises, goal = interpreter("Laughs([Wizard]) ∧ Says([Wizard], [Mortality is the bedrock of existence, little one.]) ∧ Says([Wizard], [To defy it is to invite oblivion.]) ∧ ∃x (Defies(x, [Mortality]) ∧ Grants([Wizard], x))".strip())
        premises = [(interpreter(fol)[1],rule) for fol,rule in world_rules]
        print("premises: ")
        for premise in premises:
                print(premise)
        print("goal: ")
        print(goal)
        print()
        print()
        result, branches = prove_with_premises(premises, goal, qdepth=5)
        
        print("none cloesed branches: ")        
        for branch in branches:
                print(branch)
        print("result: ")
        print(result)