from typing import Any, List, Tuple,  Optional
import itertools, sys 
sys.path.append(".")
from auto_prove import unify_list, Formula, Notated, Term, Fun, Constance, Var, Operation



# --- Skolem 함수 인덱스 관리 ---------------------------------------------
_sko_counter = itertools.count(1)

def new_sko_fun(free_vars: List[Constance]) -> Fun:
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

def fmla(notated: Notated) -> Formula:
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

def substitute_in_formula(form: Formula, old: Term, new: Term) -> Term:
    if isinstance(form, Formula):
        head, *args = form
        new_args = []
        for arg in args:
            if isinstance(arg, tuple):
                new_args.append(substitute_in_formula(arg, old, new))
            else:
                new_args.append(substitute_term(arg, old, new))
        return (head, *new_args)
    return form

# --- 공식 형태 판별 및 구성 ------------------------------------------------
binary_ops = {"and", "or", "imp", "revimp", "uparrow", "downarrow", "notimp", "notrevimp"}
quantifiers = {"some", "all"}

def is_unary(form: Term) -> bool:
    # double negation, neg true or neg false
    return (
        isinstance(form, tuple) and form[0] == "neg"
        and (isinstance(form[1], tuple) and form[1][0] == "neg"
             or form[1] in ("true","false"))
    )

def component(form: Term) -> Term:
    if form == ("neg","true"):
        return "false"
    if form == ("neg","false"):
        return "true"
    if isinstance(form, tuple) and form[0] == "neg" \
       and isinstance(form[1], tuple) and form[1][0] == "neg":
        return form[1][1]
    raise ValueError(f"No unary component for {form}")

def is_conjunctive(form: Term) -> bool:
    if isinstance(form, tuple) and form[0] == "and":
        return True
    if isinstance(form, tuple) and form[0] == "neg" \
       and isinstance(form[1], tuple) and form[1][0] in {"or","imp","revimp","uparrow"}:
        return True
    return False

def is_disjunctive(form: Term) -> bool:
    if isinstance(form, tuple) and form[0] == "or":
        return True
    if isinstance(form, tuple) and form[0] in {"imp","revimp","uparrow"}:
        return True
    if isinstance(form, tuple) and form[0] == "neg" \
       and isinstance(form[1], tuple) and form[1][0] in {"and","downarrow","notimp","notrevimp"}:
        return True
    return False

def components(form: Term) -> Tuple[Term, Term]:
    op = form[0]
    if op == "and":
        return (form[1], form[2])
    if op == "or":
        return (form[1], form[2])
    if op == "imp":
        return (("neg", form[1]), form[2])
    if op == "revimp":
        return (form[1], ("neg", form[2]))
    if op == "uparrow":
        return (("neg", form[1]), ("neg", form[2]))
    if op == "downarrow":
        return (("neg", form[1]), ("neg", form[2]))
    if op == "notimp":
        return (form[1], ("neg", form[2]))
    if op == "notrevimp":
        return (("neg", form[1]), form[2])
    if op == "neg" and isinstance(form[1], tuple):
        return components(form[1])
    raise ValueError(f"No components for {form}")

def is_existential(form: Term) -> bool:
    return (isinstance(form, tuple) and form[0] == "some") \
       or (isinstance(form, tuple) and form[0] == "neg"
           and isinstance(form[1], tuple) and form[1][0] == "all")

def is_universal(form: Term) -> bool:
    return (isinstance(form, tuple) and form[0] == "all") \
       or (isinstance(form, tuple) and form[0] == "neg"
           and isinstance(form[1], tuple) and form[1][0] == "some")

def instance(form: Term, term_or_var: Any) -> Term:
    if form[0] in {"some","all"}:
        _, var, body = form
        return substitute_in_formula(body, var, term_or_var)
    if form[0] == "neg" and isinstance(form[1], tuple) and form[1][0] in {"some","all"}:
        return ("neg", instance(form[1], term_or_var))
    raise ValueError(f"No instance for {form}")

def is_atomic(form: Term) -> bool:
    if isinstance(form, str):
        return False
    if isinstance(form, tuple):
        head = form[0]
        if head in {"neg","and","or","imp","revimp","uparrow","downarrow","notimp","notrevimp","some","all"}:
            return False
        return True
    return False

# --- 단일 확장 단계 singlestep -------------------------------------------
def singlestep(
    tableau: List[List[Notated]],
    qdepth: int
) -> Optional[Tuple[List[List[Notated]], int]]:
    for b_idx, branch in enumerate(tableau):
        # 1) Unary
        for f_idx, (free, form) in enumerate(branch):
            if is_unary(form):
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
        # 4) Delta (existential)
        for f_idx, (free, form) in enumerate(branch):
            if is_existential(form):
                term = new_sko_fun(free)
                inst = instance(form, term)
                new_branch = branch[:f_idx] + [make_notated(free, inst)] + branch[f_idx+1:]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth)
        # 5) Gamma (universal)
        for f_idx, (free, form) in enumerate(branch):
            if is_universal(form) and qdepth > 0:
                v = f"V{qdepth}"
                inst = instance(form, v)
                new_branch = [make_notated([v] + free, inst)] + branch[:f_idx] + branch[f_idx+1:] + [(free, form)]
                return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth-1)
        # 6) Equality reflexivity closure
        for free, form in branch:
            if isinstance(form, tuple) and form[0] == "neg":
                inner = form[1]
                if isinstance(inner, tuple) and inner[0] == "=" and inner[1] == inner[2]:
                    new_branch = branch + [([], "false")]
                    return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth)
        # 7) Equality replacement in atomic formulas
        eqs = [(fmla_eq[1], fmla_eq[2]) for free_eq, fmla_eq in branch
               if isinstance(fmla_eq, tuple) and fmla_eq[0] == "=" and len(fmla_eq) == 3]
        for t1, t2 in eqs:
            for free, form in branch:
                if is_atomic(form):
                    newf1 = substitute_in_formula(form, t1, t2)
                    if newf1 != form:
                        nb = branch + [make_notated(free, newf1)]
                        return (tableau[:b_idx] + [nb] + tableau[b_idx+1:], qdepth)
                    newf2 = substitute_in_formula(form, t2, t1)
                    if newf2 != form:
                        nb = branch + [make_notated(free, newf2)]
                        return (tableau[:b_idx] + [nb] + tableau[b_idx+1:], qdepth)
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



'''from typing import Any, List, Tuple, Union
from auto_prove import unify
import itertools

# Formula representation using nested tuples
Term = Union[str, Tuple[Any, ...]]

def member(item: Any, lst: List[Any]) -> bool:
    return item in lst

def remove(item: Any, lst: List[Any]) -> List[Any]:
    return [x for x in lst if x == item]

def append(list_a: List[Any], list_b: List[Any]) -> List[Any]:
    return list_a + list_b

# Propositional operators
PROP_OPS = {'neg', 'and', 'or', 'imp', 'revimp', 'uparrow', 'downarrow', 'notimp', 'notrevimp'}

def is_conjunctive(f: Term) -> bool:
    if isinstance(f, tuple) and f[0] in {'and', 'downarrow', 'notimp', 'notrevimp'}:
        return True
    if isinstance(f, tuple) and f[0] == 'neg' and isinstance(f[1], tuple) and f[1][0] in {'or', 'imp', 'revimp', 'uparrow'}:
        return True
    return False

def is_disjunctive(f: Term) -> bool:
    if isinstance(f, tuple) and f[0] in {'or', 'imp', 'revimp', 'uparrow'}:
        return True
    if isinstance(f, tuple) and f[0] == 'neg' and isinstance(f[1], tuple) and f[1][0] in {'and', 'downarrow', 'notimp', 'notrevimp'}:
        return True
    return False

def is_unary(f: Term) -> bool:
    return isinstance(f, tuple) and f[0] == 'neg' and (isinstance(f[1], tuple) and f[1][0] == 'neg' or f[1] in {'true', 'false'})

def is_binary_operator(op: str) -> bool:
    return op in PROP_OPS

def components(f: Term) -> Tuple[Term, Term]:
    op, *args = f
    if is_conjunctive(f) or is_disjunctive(f):
        if op == 'and': return args[0], args[1]
        if op == 'neg' and args[0][0] == 'and': return ('neg', args[0][1]), ('neg', args[0][2])
        if op == 'or': return args[0], args[1]
        if op == 'neg' and args[0][0] == 'or': return ('neg', args[0][1]), ('neg', args[0][2])
        if op == 'imp': return ('neg', args[0]), args[1]
        if op == 'neg' and args[0][0] == 'imp': return args[0][1], ('neg', args[0][2])
        # Add other operators analogously
    raise ValueError("Not a conjunctive/disjunctive formula")

def component(f: Term) -> Term:
    if isinstance(f, tuple) and f[0] == 'neg':
        subf = f[1]
        if isinstance(subf, tuple) and subf[0] == 'neg':
            return subf[1]
        if subf == 'true': return 'false'
        if subf == 'false': return 'true'
    raise ValueError("Not a unary formula")

def is_universal(f: Term) -> bool:
    return isinstance(f, tuple) and (f[0] == 'all' or (f[0] == 'neg' and isinstance(f[1], tuple) and f[1][0] == 'some'))

def is_existential(f: Term) -> bool:
    return isinstance(f, tuple) and (f[0] == 'some' or (f[0] == 'neg' and isinstance(f[1], tuple) and f[1][0] == 'all'))

def is_literal(f: Term) -> bool:
    return not (is_conjunctive(f) or is_disjunctive(f) or is_unary(f) or is_universal(f) or is_existential(f))

def is_atomic(f: Term) -> bool:
    return is_literal(f) and not (isinstance(f, tuple) and f[0] == 'neg')
#치환
def sub(term: Term, var: str, formula: Term) -> Term:
    if formula == var:
        return term
    if not isinstance(formula, tuple):
        return formula
    op, *args = formula
    if op == 'neg':
        return ('neg', sub(term, var, args[0]))
    if op in PROP_OPS:
        return (op, sub(term, var, args[0]), sub(term, var, args[1]))
    if op in {'all', 'some'} and args[0] == var:
        return (op, args[0], args[1])  # no substitution under bound var
    if op in {'all', 'some'}:
        return (op, args[0], sub(term, var, args[1]))
    # Functions/terms
    return (op, *[sub(term, var, a) for a in args])

def instance(formula: Term, term: Term) -> Term:
    op, *args = formula
    if op == 'all':
        return sub(term, args[0], args[1])
    if op == 'neg' and isinstance(args[0], tuple) and args[0][0] == 'some':
        var, body = args[0][1], args[0][2]
        return ('neg', sub(term, var, body))
    if op == 'some':
        return sub(term, args[0], args[1])
    if op == 'neg' and isinstance(args[0], tuple) and args[0][0] == 'all':
        var, body = args[0][1], args[0][2]
        return ('neg', sub(term, var, body))
    raise ValueError("Not a quantified formula")

# --- 용어 정의 ------------------------------------------------------------
Term = Union[str, Tuple[Any, ...]]
Notated = Tuple[List[str], Term]  # (free_vars, formula)

# --- Skolem 함수 인덱스 관리 ---------------------------------------------
_sko_counter = itertools.count(1)

def new_sko_fun(free_vars: List[str]) -> Term:
    """새로운 Skolem 함수 f_i(free_vars...)를 생성."""
    i = next(_sko_counter)
    return ("f" + str(i), *free_vars)

def reset_sko():
    """Skolem 함수 인덱스 리셋."""
    global _sko_counter
    _sko_counter = itertools.count(1)

# --- 노테이션 처리 -------------------------------------------------------
def notation(notated: Notated) -> List[str]:
    return notated[0]

def fmla(notated: Notated) -> Term:
    return notated[1]

def make_notated(free: List[str], formula: Term) -> Notated:
    return (free.copy(), formula)

# --- 단일 확장 단계 singlestep -------------------------------------------
def singlestep(
    tableau: List[List[Notated]],
    qdepth: int
) -> Union[Tuple[List[List[Notated]], int], None]:
    """
    tableau: branches 의 리스트
    qdepth: 남은 γ-규칙(∀) 적용 횟수
    반환: (new_tableau, new_qdepth) 또는 더 이상 확장 불가능하면 None
    """
    # branches 우선순위: [0]부터 순서대로
    for b_idx, branch in enumerate(tableau):
        # branch 에서 적용할 수 있는 첫 번째 규칙 찾기
        # 1) 단항규칙(neg neg, neg true/false)
        for f_idx, (free, form) in enumerate(branch):
            # ... (is_unary, component 판별) ...
            if is_unary(form):
                comp = component(form)
                new_not = make_notated(free, comp)
                new_branch = branch[:f_idx] + [new_not] + branch[f_idx+1:]
                new_tb = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                return (new_tb, qdepth)
        # 2) α-규칙 (conjunctive)
        for f_idx, (free, form) in enumerate(branch):
            if is_conjunctive(form):
                a1, a2 = components(form)
                n1 = make_notated(free, a1)
                n2 = make_notated(free, a2)
                new_branch = branch[:f_idx] + [n1, n2] + branch[f_idx+1:]
                new_tb = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                return (new_tb, qdepth)
        # 3) β-규칙 (disjunctive)
        for f_idx, (free, form) in enumerate(branch):
            if is_disjunctive(form):
                b1, b2 = components(form)
                n1 = make_notated(free, b1)
                n2 = make_notated(free, b2)
                br1 = branch[:f_idx] + [n1] + branch[f_idx+1:]
                br2 = branch[:f_idx] + [n2] + branch[f_idx+1:]
                new_tb = tableau[:b_idx] + [br1, br2] + tableau[b_idx+1:]
                return (new_tb, qdepth)
        # 4) δ-규칙 (existential)
        for f_idx, (free, form) in enumerate(branch):
            if is_existential(form):
                term = new_sko_fun(free)
                inst = instance(form, term)
                new_not = make_notated(free, inst)
                new_branch = branch[:f_idx] + [new_not] + branch[f_idx+1:]
                new_tb = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                return (new_tb, qdepth)
        # 5) γ-규칙 (universal), Q-depth 차감
        for f_idx, (free, form) in enumerate(branch):
            if is_universal(form) and qdepth > 0:
                v = f"V{qdepth}"  # 새 자유변수
                inst = instance(form, v)
                new_not = make_notated([v] + free, inst)
                # 새 인스턴스는 branch 맨 앞, 원본 공식은 맨 뒤로
                new_branch = [new_not] + branch[:f_idx] + branch[f_idx+1:] + [(free, form)]
                new_tb = tableau[:b_idx] + [new_branch] + tableau[b_idx+1:]
                return (new_tb, qdepth - 1)
    # 더 이상 확장할 규칙이 없으면 None
    return None

# --- 전체 확장 expand --------------------------------------------------
def expand(tableau: List[List[Notated]], qdepth: int) -> List[List[Notated]]:
    while True:
        step = singlestep(tableau, qdepth)
        if step is None:
            return tableau
        tableau, qdepth = step

# --- 닫힘 검사 closed ---------------------------------------------------
def closed(tableau: List[List[Notated]]) -> bool:
    for branch in tableau:
        # 분기가 false 리터럴 포함 시 닫힘
        if any(fmla(nf) == 'false' for nf in branch):
            continue
        # 리터럴 X, ¬Y 쌍이 유일화 가능하면 닫힘
        atoms = [(nf, fmla(nf)) for nf in branch if is_atomic(fmla(nf))]
        for (_, x) in atoms:
            for (_, y) in atoms:
                if isinstance(y, tuple) and y[0] == 'neg' and unify(x, y[1]):
                    break
            else:
                continue
            break
        else:
            return False
    return True

# --- 테스트 인터페이스 --------------------------------------------------
def test(formula: Term, qdepth: int):
    
    # Example: usage of sub
    F = ('imp', 'p', ('all', 'x', ('neg', 'q(x)')))
    print("sub('a', 'x', F) =", sub('a', 'x', F))
    # Example: instance
    G = ('all', 'x', ('imp', 'p(x)', ('some', 'y', 'q(x,y)')))
    print("instance(G, 'a') =", instance(G, 'a'))

    
    
    reset_sko()
    root = make_notated([], ('neg', formula))
    tree = expand([[root]], qdepth)
    if closed(tree):
        print(f"First-order tableau theorem at Q-depth {qdepth}.")
    else:
        print(f"Not a first-order tableau theorem at Q-depth {qdepth}.")'''