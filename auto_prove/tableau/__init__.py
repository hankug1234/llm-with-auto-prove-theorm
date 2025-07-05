from typing import List, Tuple,  Optional, Dict, Set
import itertools, sys 
sys.path.append(".")
from auto_prove import unify_list, Formula, Notated, Term, Fun, Var, Operation, Terminology, Constance, Atom


# --- Skolem 함수 인덱스 관리 ---------------------------------------------
_sko_counter = itertools.count(1)
_reflex_seen: Dict[int, Set[int]] = {}   # branch_id → {hash(term), ...}
terms_in_branch = set()

def new_sko_fun(free_vars: List[Var]) -> Fun:
    """새로운 Skolem 함수 f_i(free_vars...)를 생성."""
    i = next(_sko_counter)
    return Fun(f"f_{i}",free_vars)

def reset_sko():
    """Skolem 함수 인덱스 리셋."""
    global _sko_counter
    _sko_counter = itertools.count(1)

def reset_reflex_seen():
    global _reflex_seen
    _reflex_seen = {} 

def reset_terms_in_branch():
    global terms_in_branch
    terms_in_branch = set()
    

# --- 노테이션 처리 --------------------------------------------------------
def notation(notated: Notated) -> List[Var]:
    return notated[0]

def formula(notated: Notated) -> Formula:
    return notated[1]

def make_notated(free: List[Var], formula: Formula) -> Notated:
    return (free.copy(), formula)

# --- 항 및 공식 치환 -------------------------------------------------------
def substitute_term(term: Term, old: Term, new: Term) -> Term:
    if term == old:
        return new
    if isinstance(term, Fun):
        return Fun(term.name,[substitute_term(t, old, new) for t in term.args])
    return term

def substitute_in_formula(form: Formula, old: Term, new: Term) -> Formula:
    if isinstance(form, Terminology):
        return Terminology(form.name, [substitute_term(t, old, new) for t in form.args])

    if isinstance(form,Term):
        return substitute_term(form, old, new)

    if isinstance(form, tuple):
        if len(form) == 2:  # 단항 연산자
            op, sub = form
            return (op, substitute_in_formula(sub, old, new))
        elif len(form) == 3:  # 이항 연산자
            op, left, right = form
            return (op, substitute_in_formula(left, old, new), substitute_in_formula(right, old, new))

    return form 

# --- 공식 형태 판별 및 구성 ------------------------------------------------

def is_unary_formula(form: Formula) -> bool:
    # double negation, neg true or neg false
    if isinstance(form , tuple):
        op = form[0]
        inner = form[1]
        
        return (
            isinstance(form, tuple) 
            and op == Operation.NEG
            and (
                (isinstance(inner, tuple) and inner[0] == Operation.NEG)
                or isinstance(inner, bool)
                )
        )
    return False

def is_conjunctive(form: Formula) -> bool:
    if isinstance(form, tuple):
        op = form[0]
        
        if op == Operation.AND:
            return True
        
        if op == Operation.NEG and isinstance(form[1], tuple):
            inner = form[1]
            inner_op = inner[0]
            
            if inner_op in {
                Operation.OR,
                Operation.IMPLIE,
                Operation.REVERSED_IMPLIE,
                Operation.NOR
            }:
                return True
    return False

def is_disjunctive(form: Term) -> bool:
    if isinstance(form, tuple):
        op = form[0]

        if op == Operation.OR:
            return True

        if op == Operation.NEG and isinstance(form[1], tuple):
            inner = form[1]
            inner_op = inner[0]
            
            if inner_op in {
                Operation.AND, 
                Operation.NAND, 
                Operation.IMPLIE,
                Operation.REVERSED_IMPLIE
            }:
                return True
    return False

def component(form: Formula) -> bool:
    if form == (Operation.NEG,True):
        return False
    if form == (Operation.NEG,False):
        return True
    if is_unary_formula(form):
        inner_inner = form[1][1]
        return inner_inner
    raise ValueError(f"No unary component for {form}")

def components(form: Formula) -> Tuple[Formula, Formula]:
    if isinstance(form, tuple):
        op = form[0]
        if op == Operation.AND:
            return (form[1], form[2])
        if op == Operation.OR:
            return (form[1], form[2])
        if op == Operation.IMPLIE:
            return ((Operation.NEG, form[1]), form[2])
        if op == Operation.REVERSED_IMPLIE:
            return (form[1], (Operation.NEG, form[2]))
        if op == Operation.NOR:
            return ((Operation.NEG, form[1]), (Operation.NEG, form[2]))
        if op == Operation.NAND:
            return ((Operation.NEG, form[1]), (Operation.NEG, form[2]))
        if op == Operation.NOT_IMPLIE:
            return (form[1], (Operation.NEG, form[2]))
        if op == Operation.NOT_REVERSED_IMPLIE:
            return ((Operation.NEG, form[1]), form[2])
        if op == Operation.NEG and isinstance(form[1], tuple):
            return components(form[1])
    raise ValueError(f"No components for {form}")

def is_existential(form: Formula) -> bool:
    if isinstance(form,tuple):
        op = form[0]
        inner = form[1]
        return (isinstance(form, tuple) and op == Operation.SOME) \
        or (isinstance(form, tuple) and op == Operation.NEG
            and isinstance(inner, tuple) and inner[0] == Operation.ALL)
    return False 

def is_universal(form: Formula) -> bool:
    if isinstance(form,tuple):
        op = form[0]
        inner = form[1]
        return (isinstance(form, tuple) and op == Operation.ALL) \
        or (isinstance(form, tuple) and op == Operation.NEG
            and isinstance(op, tuple) and inner[0] == Operation.SOME)
    return False

def instance(form: Formula, term: Term) -> Formula:
    op = form[0]
    inner = form[1]
    if op in {Operation.SOME,Operation.ALL}:
        _, var, body = form
        return substitute_in_formula(body, var, term)
    if op == Operation.NEG and isinstance(inner, tuple) and inner[0] in {Operation.SOME,Operation.ALL}:
        return (Operation.NEG, instance(inner, term))
    raise ValueError(f"No instance for {form}")

def is_atomic(form: Formula) -> bool:
    if isinstance(form, Terminology) or isinstance(form,bool):
        return True 
    return False

def _already_reflex(branch, term) -> bool:
    """branch 에 대해 term 의 reflex 가 이미 삽입되었나?"""
    bid = id(branch)
    bucket = _reflex_seen.setdefault(bid, set())
    h = hash(term)
    if h in bucket:
        return True          # 이미 있었음 → 삽입 스킵
    bucket.add(h)            # 최초 발견 → 기록하고 False 반환
    return False

def _collect_terms(form: Formula):
    """등식(=)에 등장한 term만 모은다."""
    if (isinstance(form, tuple)
        and form[0] == Operation.EQUAL
        and len(form) == 3):
        terms_in_branch.add(form[1])
        terms_in_branch.add(form[2])

# --- 단일 확장 단계 singlestep -------------------------------------------
def singlestep(
    tableau: List[List[Notated]],
    qdepth: int,
    equality: int
) -> Optional[Tuple[List[List[Notated]], int, int]]:

    for b_idx, branch in enumerate(tableau):
        
        # 1) Unary
        for f_idx, (free, form) in enumerate(branch):
            if is_unary_formula(form):
                comp = component(form)
                new_branch = branch[:f_idx] + [make_notated(free, comp)] + branch[f_idx+1:]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth, equality)
            
        # 2) Alpha
        for f_idx, (free, form) in enumerate(branch):
            if is_conjunctive(form):
                a1, a2 = components(form)
                new_branch = branch[:f_idx] + [make_notated(free, a1), make_notated(free, a2)] + branch[f_idx+1:]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth, equality)
            
        # 3) Beta
        for f_idx, (free, form) in enumerate(branch):
            if is_disjunctive(form):
                b1, b2 = components(form)
                br1 = branch[:f_idx] + [make_notated(free, b1)] + branch[f_idx+1:]
                br2 = branch[:f_idx] + [make_notated(free, b2)] + branch[f_idx+1:]
                new_tb = tableau[:b_idx] + [br1, br2] + tableau[b_idx+1:]
                return (new_tb, qdepth, equality)
            
        # 4) Gamma (universal)
        for f_idx, (free, form) in enumerate(branch):
            if is_universal(form) and qdepth > 0:
                v = Var(f"V{qdepth}") 
                inst = instance(form, v) 
                inst_notated = make_notated(free, inst)
                original_notated = make_notated([v] + free, form)
                new_branch = [inst_notated] + branch[:f_idx] + branch[f_idx+1:] + [original_notated]
                new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                return (new_tableau, qdepth - 1, equality)
            
        # 5) Equality reflexivity EXPANSION  (t = t 삽입)
        for _, formula in branch:
            _collect_terms(formula)

        existing_eqs = {frm for _, frm in branch if isinstance(frm, tuple) and frm[0] == Operation.EQUAL and len(frm) == 3}

        for t in terms_in_branch:
            reflex = (Operation.EQUAL, t, t)
            
            if reflex in existing_eqs or _already_reflex(branch, t):
                continue  
            
            if reflex not in existing_eqs:                   # 아직 없다면 추가
                new_branch = branch + [make_notated([], reflex)]
                new_tableau = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                return (new_tableau, qdepth, equality)
            
        # 6) Equality SUBSTITUTIVITY (원자식 치환)  <— 기존 규칙 보강
        eqs = [
            (eqf[1], eqf[2])
            for _, eqf in branch
            if isinstance(eqf, tuple) and eqf[0] == Operation.EQUAL and len(eqf) == 3
        ]
        if eqs:
            existing_forms = {frm for _, frm in branch}            # 중복 방지
            for t1, t2 in eqs:
                for free, frm in branch:
                    if not is_atomic(frm):                         # (부정)원자식만 대상
                        continue

                    # --- t1 ↦ t2 치환 ---
                    new_f = substitute_in_formula(frm, t1, t2)
                    if equality > 0 and new_f != frm and new_f not in existing_forms:
                        new_branch = branch + [make_notated(free, new_f)]
                        new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                        return (new_tableau, qdepth, equality - 1)

                    # --- t2 ↦ t1 치환 (대칭) ---
                    new_f = substitute_in_formula(frm, t2, t1)
                    if equality > 0 and new_f != frm and new_f not in existing_forms:
                        new_branch = branch + [make_notated(free, new_f)]
                        new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                        return (new_tableau, qdepth, equality - 1)

        # 7) Equality reflexivity CLOSURE   ( ¬(t = t) → false )
        for free, frm in branch:
            if isinstance(frm, tuple) and frm[0] == Operation.NEG:
                inner = frm[1]
                if isinstance(inner, tuple) and inner[0] == Operation.EQUAL and inner[1] == inner[2]:
                    new_branch = branch + [([], False)]
                    new_tableau = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                    return (new_tableau, qdepth, equality)

                    
        # 8) Delta (existential)
        for f_idx, (free, form) in enumerate(branch):
            if is_existential(form):
                term = new_sko_fun(free)
                inst = instance(form, term)
                new_branch = branch[:f_idx] + [make_notated(free, inst)] + branch[f_idx+1:]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth, equality)
    return None

# --- 전체 확장 expand -----------------------------------------------------
def expand(tableau: List[List[Notated]], qdepth: int, equality: int) -> List[List[Notated]]:
    while True:
        step = singlestep(tableau, qdepth, equality)
        if not step:
            return tableau
        tableau, qdepth, equality = step
        

# --- 분기 닫힘 검사 closed -----------------------------------------------
def is_literal(form: Formula) -> bool:
    """원자식 또는 그 부정인지 판별."""
    if isinstance(form, Terminology):
        return True                 # P(t)
    if (isinstance(form, tuple) and
        form[0] == Operation.NEG and
        isinstance(form[1], Terminology)):
        return True                 # ¬P(t)
    return False


def negate_literal(lit: Formula) -> Formula:
    """리터럴 lit의 논리적 부정을 돌려준다."""
    if isinstance(lit, Terminology):                 # P(t) → ¬P(t)
        return (Operation.NEG, lit)
    if (isinstance(lit, tuple) and lit[0] == Operation.NEG):
        return lit[1]                              # ¬P(t) → P(t)
    raise ValueError("not a literal")


def branch_closed(branch: List[Notated]) -> bool:
    # 1) false 리터럴
    if any(formula(n) == False for n in branch):
        return True
    literals = [n for n in branch if is_literal(formula(n))]
    if len(literals) == 0:
        return False

    # 3) 각 리터럴에 대해 부정형 존재 + 유일화 검사
    for free1, lit1 in literals:
        neg_lit1 = negate_literal(lit1)

        # neg_lit1 이 branch 에 존재하는지 확인
        for free2, lit2 in literals:
            if lit2 == neg_lit1:
                return True

            # (a) 술어 이름, 인자 수가 일치하는지 (이미 lit2 == ¬lit1)
            # (b) 두 리터럴의 대응 term 들이 유일화(resolve) 되는지 확인
            if isinstance(lit1, Terminology) and isinstance(lit2, tuple):
                # lit2 = (NEG, Terminology(...))
                lit2_inner = lit2[1]
                try:
                    _ = unify_list(lit1.args, lit2_inner.args, [])
                    return True
                except ValueError:
                    pass  # 이 리터럴 쌍은 충돌 못 함

            elif (isinstance(lit1, tuple) and lit1[0] == Operation.NEG
                    and isinstance(lit2, Terminology)):
                # lit1 = (NEG, Terminology(...)), lit2 = Terminology(...)
                lit1_inner = lit1[1]
                try:
                    _ = unify_list(lit1_inner.args, lit2.args, [])
                    return True
                except ValueError:
                    pass

    # 여기까지 왔으면 모순 쌍 없음 → 열린 브랜치
    return False


def closed(tableau: List[List[Notated]]) -> bool:
    """tableau 의 모든 branch 가 닫혔으면 True"""
    return all(branch_closed(branch) for branch in tableau)


# --- 테스트 인터페이스 -----------------------------------------------------
def prove(formula: Term, qdepth: int = 3, equality : int = 6):
    reset_sko()
    reset_reflex_seen()
    reset_terms_in_branch()
    root = make_notated([], (Operation.NEG, formula))
    tree = expand([[root]], qdepth, equality)
    if closed(tree):
        print(f"Proof found at Q-depth {qdepth}")
    else:
        print(f"No proof at Q-depth {qdepth}")
        
# ─────────────────────────────────────────────────────────────
# 전제(assumptions)를 포함한 초기 branch 생성
# ─────────────────────────────────────────────────────────────
def _build_initial_branch(premises: List[Formula],
                          conclusion: Formula) -> List[Notated]:
    """
    S ⊢ X 를 tableau 로 증명하기 위한 branch:
      - 모든 전제 S 를 '참'으로,    (positive node)
      - 결론 X  는 '부정'으로 삽입. (¬X)
    """
    branch: List[Notated] = []

    # 1) 전제들을 먼저 positive 로 추가
    for prem in premises:
        branch.append(make_notated([], prem))

    # 2) 부정 결론 ¬X 추가
    branch.append(make_notated([], (Operation.NEG, conclusion)))

    return branch


# ─────────────────────────────────────────────────────────────
#  S ⊢ X  판단 함수 (premises + conclusion)
# ─────────────────────────────────────────────────────────────
        
def prove_with_premises(premises: List[Formula], 
                        conclusion: Formula,
                        qdepth: int = 3,
                        equality: int = 6) -> bool:
    """
    premises  (S) 가 주어졌을 때,
    결론 conclusion (X)이  Tableau 상에서 따르는지(S ⊢ X) 확인.
    반환값: True  → 증명 성공 (Theorem under premises)
            False → 깊이 qdepth 까지는 실패 (불완전할 수 있음)
    """
    reset_sko()                             # Skolem 인덱스 초기화
    reset_reflex_seen()
    reset_terms_in_branch()
    root_branch = _build_initial_branch(premises, conclusion)
    tableau = expand([root_branch], qdepth, equality) # 기존 expand 사용

    if closed(tableau):
        print(f"⊢  증명 성공   (Q-depth={qdepth})")
        return True
    else:
        print(f"⊢  증명 실패   (Q-depth={qdepth} 까지)")
        return False

# --- 사용 예제 ------------------------------------------------------------
if __name__ == "__main__":
    prem1 = Terminology("P", [Constance("a")])
    prem2 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Terminology("P", [Var("x")]),
            Terminology("Q", [Var("x")])))

    goal  = Terminology("Q", [Constance("a")])

    prove_with_premises([prem1, prem2], goal, qdepth=2)
    
    # ─────────────────────────────────────────────
    #  무한 등식-루프를 일으키는 간단한 예제
    # ─────────────────────────────────────────────
    #  전제 S
    prem1 = Terminology("P", [Constance("a")])                          # ① P(a)
    prem2 = (
        Operation.ALL, "x",                                           # ② ∀x (P(x) → P(f(x)))
        (Operation.IMPLIE,
        Terminology("P", [Var("x")]),
        Terminology("P", [Fun("f", [Var("x")])]))
    )
    prem3 = (Operation.EQUAL,                                         # ③ a = f(a)
            Constance("a"),
            Fun("f", [Constance("a")]))

    S = [prem1, prem2, prem3]

    #  결론을 아무거나 두면 되지만, 예컨대 Q(a) 를 증명하려고 한다고 하자
    goal = Terminology("Q", [Constance("a")])

    # 증명 시도
    prove_with_premises(S, goal, qdepth=5)
    
    print("-------- 2 / 6 / 7 -------------- 증명 실패 여야 함")
    
    # ----------------------------------------------
    # 1. 기본 유효   P(a),  ∀x( P(x) → Q(x) ) ⊢ Q(a)
    prem1 = Terminology("P", [Constance("a")])
    prem2 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Terminology("P", [Var("x")]),
            Terminology("Q", [Var("x")])))
    goal  = Terminology("Q", [Constance("a")])
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    # 2. 동일 변수 반복 (무효)  ∀x P(x) ⊬ Q(a)
    prem1 = (Operation.ALL, "x", Terminology("P", [Var("x")]))
    goal  = Terminology("Q", [Constance("a")])    # entailment가 안 됨
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    # 3. ∧ 도입  P(a) ∧ R(a) ⊢ R(a)
    prem1 = (Operation.AND,
            Terminology("P", [Constance("a")]),
            Terminology("R", [Constance("a")]))
    goal  = Terminology("R", [Constance("a")])
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    # 4. ∃ 제거  ∃y (R(y) ∧ P(y)) , ∀x (R(x) → Q(x)) ⊢ ∃z Q(z)
    prem1 = (Operation.SOME, "y",
            (Operation.AND,
            Terminology("R", [Var("y")]),
            Terminology("P", [Var("y")])))
    prem2 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Terminology("R", [Var("x")]),
            Terminology("Q", [Var("x")])))
    goal  = (Operation.SOME, "z", Terminology("Q", [Var("z")]))
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    # 5. double-negation  ¬¬P(b) ⊢ P(b)
    prem1 = ("neg", ("neg", Terminology("P", [Constance("b")])))
    goal  = Terminology("P", [Constance("b")])
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    # 6. De Morgan (무효)  ¬(P(a) ∧ Q(a)) ⊢ ¬P(a) ∨ ¬Q(a)   # 타블로가 닫히지 않음
    prem1 = ("neg",
            (Operation.AND,
            Terminology("P", [Constance("a")]),
            Terminology("Q", [Constance("a")])))
    goal  = (Operation.OR,
            ("neg", Terminology("P", [Constance("a")])),
            ("neg", Terminology("Q", [Constance("a")])))
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    # 7. 조건부의 역 (무효)  P(a) → Q(a)  ⊬ Q(a) → P(a)
    prem1 = (Operation.IMPLIE,
            Terminology("P", [Constance("a")]),
            Terminology("Q", [Constance("a")]))
    goal  = (Operation.IMPLIE,
            Terminology("Q", [Constance("a")]),
            Terminology("P", [Constance("a")]))
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    # 8. ∀/∃ 혼합   ∀x (P(x) → ∃y R(x,y)) , P(c) ⊢ ∃y R(c,y)
    prem1 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Terminology("P", [Var("x")]),
            (Operation.SOME, "y", Terminology("R", [Var("x"), Var("y")]))))
    prem2 = Terminology("P", [Constance("c")])
    goal  = (Operation.SOME, "y", Terminology("R", [Constance("c"), Var("y")]))
    prove_with_premises(S, goal, qdepth=5)
    # ----------------------------------------------
    prem1 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Terminology("P", [Var("x")]),
            (Operation.SOME, "y", Terminology("R", [Var("x"), Var("y")]))))
    prem2 = (Operation.ALL, "x",
            (Operation.IMPLIE,
            Terminology("P", [Var("x")]),
            (Operation.SOME, "y", Terminology("R", [Var("x"), Var("y")]))))
    print(Terminology("P", [Var("x")]) ==  Terminology("P", [Var("x")]))
    print(Var("x") == Var("x"))               # True ?
    print(Constance("a") == Constance("a"))   # True ?
    print(Fun("f", [Var("x")]) == Fun("f", [Var("x")]))
    
    print("__________________________________________")
    
    t1 = Terminology("P", [Var("x")])
    t2 = Terminology("P", [Var("x")])

    print("t1:", t1)
    print("t2:", t2)
    print("args equal?:", [a == b for a, b in zip(t1.args, t2.args)])
    print("Terminology equal?:", t1 == t2)