from typing import List, Tuple,  Optional
import itertools, sys 
sys.path.append(".")
from auto_prove import unify_list, Formula, Notated, Term, Fun, Constance, Var, Operation, Predicate



# --- Skolem 함수 인덱스 관리 ---------------------------------------------
_sko_counter = itertools.count(1)

def new_sko_fun(free_vars: List[Var]) -> Fun:
    """새로운 Skolem 함수 f_i(free_vars...)를 생성."""
    i = next(_sko_counter)
    return Fun(f"f_{i}",free_vars)

def reset_sko():
    """Skolem 함수 인덱스 리셋."""
    global _sko_counter
    _sko_counter = itertools.count(1)

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
    if isinstance(form, Predicate):
        return Predicate(form.name, [substitute_term(t, old, new) for t in form.args])

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
    op = form[0]
    inner = form[1]
    inner_op = inner[0]
     
    return (
        isinstance(form, tuple) 
        and op == Operation.NEG
        and (
            (isinstance(inner, tuple) and inner_op == Operation.NEG)
            or isinstance(inner, bool)
            )
    )

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
    op = form[0]
    inner = form[1]
    inner_op = inner[0]
    return (isinstance(form, tuple) and op == Operation.SOME) \
       or (isinstance(form, tuple) and op == Operation.NEG
           and isinstance(inner, tuple) and inner_op == Operation.ALL)

def is_universal(form: Formula) -> bool:
    op = form[0]
    inner = form[1]
    inner_op = inner[0]
    return (isinstance(form, tuple) and op == Operation.ALL) \
       or (isinstance(form, tuple) and op == Operation.NEG
           and isinstance(op, tuple) and inner_op == Operation.SOME)

def instance(form: Formula, term: Term) -> Term:
    op = form[0]
    inner = form[1]
    inner_op = inner[0]
    if op in {Operation.SOME,Operation.ALL}:
        _, var, body = form
        return substitute_in_formula(body, var, term)
    if op == Operation.NEG and isinstance(inner, tuple) and inner_op in {Operation.SOME,Operation.ALL}:
        return (Operation.NEG, instance(inner, term))
    raise ValueError(f"No instance for {form}")

def is_atomic(form: Formula) -> bool:
    if isinstance(form, Predicate) or isinstance(form,bool):
        return True 
    return False

# --- 단일 확장 단계 singlestep -------------------------------------------
def singlestep(
    tableau: List[List[Notated]],
    qdepth: int
) -> Optional[Tuple[List[List[Notated]], int]]:
    
    terms_in_branch = set()

    def _collect_terms(form: Formula):
        """Atomic / equality 식에서 term 모으기 (도우미)"""
        if isinstance(form, Predicate):
            for a in form.args: terms_in_branch.add(a)
        elif isinstance(form, tuple) and form[0] == "=" and len(form) == 3:
            terms_in_branch.add(form[1]); terms_in_branch.add(form[2])

    for b_idx, branch in enumerate(tableau):
        
        # 1) Unary
        for f_idx, (free, form) in enumerate(branch):
            if is_unary_formula(form):
                comp = component(form)
                new_branch = branch[:f_idx] + [make_notated(free, comp)] + branch[f_idx+1:]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth)
            
        # 2) Alpha
        for f_idx, (free, form) in enumerate(branch):
            if is_conjunctive(form):
                a1, a2 = components(form)
                new_branch = branch[:f_idx] + [make_notated(free, a1), make_notated(free, a2)] + branch[f_idx+1:]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth)
            
        # 3) Beta
        for f_idx, (free, form) in enumerate(branch):
            if is_disjunctive(form):
                b1, b2 = components(form)
                br1 = branch[:f_idx] + [make_notated(free, b1)] + branch[f_idx+1:]
                br2 = branch[:f_idx] + [make_notated(free, b2)] + branch[f_idx+1:]
                new_tb = tableau[:b_idx] + [br1, br2] + tableau[b_idx+1:]
                return (new_tb, qdepth)
            
        # 4) Gamma (universal)
        for f_idx, (free, form) in enumerate(branch):
            if is_universal(form) and qdepth > 0:
                v = Var(f"V{qdepth}") 
                inst = instance(form, v) 
                inst_notated = make_notated(free, inst)
                original_notated = make_notated([v] + free, form)
                new_branch = [inst_notated] + branch[:f_idx] + branch[f_idx+1:] + [original_notated]
                new_tableau = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                return (new_tableau, qdepth - 1)
            
        # 5) Equality reflexivity EXPANSION  (t = t 삽입)
        for _, formula in branch:
            _collect_terms(formula)

        existing_eqs = {frm for _, frm in branch if isinstance(frm, tuple) and frm[0] == Operation.EQUAL and len(frm) == 3}

        for t in terms_in_branch:
            reflex = ("=", t, t)
            if reflex not in existing_eqs:                   # 아직 없다면 추가
                new_branch = branch + [make_notated([], reflex)]
                new_tableau = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                return (new_tableau, qdepth)

        # ──────────────────────────────────────────────────────────────
        # 6) Equality reflexivity CLOSURE   ( ¬(t = t) → false )
        # ----------------------------------------------------------------
        for free, frm in branch:
            if isinstance(frm, tuple) and frm[0] == Operation.NEG:
                inner = frm[1]
                if isinstance(inner, tuple) and inner[0] == "=" and inner[1] == inner[2]:
                    new_branch = branch + [([], "false")]
                    new_tableau = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                    return (new_tableau, qdepth)

        # ──────────────────────────────────────────────────────────────
        # 7) Equality SUBSTITUTIVITY (원자식 치환)  <— 기존 규칙 보강
        # ----------------------------------------------------------------
        eqs = [
            (eqf[1], eqf[2])
            for _, eqf in branch
            if isinstance(eqf, tuple) and eqf[0] == "=" and len(eqf) == 3
        ]
        if eqs:
            existing_forms = {frm for _, frm in branch}            # 중복 방지
            for t1, t2 in eqs:
                for free, frm in branch:
                    if not is_atomic(frm):                         # (부정)원자식만 대상
                        continue

                    # --- t1 ↦ t2 치환 ---
                    new_f = substitute_in_formula(frm, t1, t2)
                    if new_f != frm and new_f not in existing_forms:
                        new_branch = branch + [make_notated(free, new_f)]
                        new_tableau = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                        return (new_tableau, qdepth)

                    # --- t2 ↦ t1 치환 (대칭) ---
                    new_f = substitute_in_formula(frm, t2, t1)
                    if new_f != frm and new_f not in existing_forms:
                        new_branch = branch + [make_notated(free, new_f)]
                        new_tableau = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                        return (new_tableau, qdepth)
        # 7) Delta (existential)
        for f_idx, (free, form) in enumerate(branch):
            if is_existential(form):
                term = new_sko_fun(free)
                inst = instance(form, term)
                new_branch = branch[:f_idx] + [make_notated(free, inst)] + branch[f_idx+1:]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth)
    return None

# --- 전체 확장 expand -----------------------------------------------------
def expand(tableau: List[List[Notated]], qdepth: int) -> List[List[Notated]]:
    while True:
        step = singlestep(tableau, qdepth)
        if not step:
            return tableau
        tableau, qdepth = step

# --- 분기 닫힘 검사 closed -----------------------------------------------
def closed(tableau):
    for branch in tableau:
        # 이미 false 가 있으면 패스
        if any(fmla(nf) == 'false' for nf in branch):
            continue

        # 모든 리터럴 쌍을 골라내서…
        atoms = [fmla(nf) for nf in branch if is_atomic(fmla(nf))]
        # 예: atoms = [P(x), Q(y), R(z)]
        # 이들 중에 P,Q,R 을 동시에 유일화해서 모순이 있는지 테스트
        try:
            env = []  # 빈 환경에서 출발
            # 만약 종단 조건이 'X' 와 'neg X' 가 동시에 있는지를
            # 다중 유일화로 검사한다면, 아래처럼:
            for X, Y in itertools.product(atoms, repeat=2):
                if isinstance(Y, tuple) and Y[0]=='neg':
                    env = unify_list([X], [Y[1]], env)
                    # 혹은 여러 쌍을 한 번에 넘겨도 되고…
            # 여기까지 에러 없이 왔으면 모순이므로 닫힌(branch closed)
            continue
        except ValueError:
            # 유일화 실패 → 이 브랜치는 안 닫혔음
            return False
    return True

# --- 테스트 인터페이스 -----------------------------------------------------
def test(formula: Term, qdepth: int = 3):
    reset_sko()
    root = make_notated([], ("neg", formula))
    tree = expand([[root]], qdepth)
    if closed(tree):
        print(f"Proof found at Q-depth {qdepth}")
    else:
        print(f"No proof at Q-depth {qdepth}")

# --- 사용 예제 ------------------------------------------------------------
if __name__ == "__main__":
    # 예제: x = y, P(x) ⊢ P(y) 증명
    conj = ("and", ("=", "x", "y"), ("P", "x"))
    entail = ("imp", conj, ("P", "y"))
    test(entail, qdepth=2)