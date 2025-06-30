import itertools
from enum import Enum
from typing import List, Union, Tuple, Any

# Represent variables and compound terms
class Var:
    def __init__(self, name: str):
        self.name = name
    def __repr__(self):
        return self.name
    def __eq__(self, other):
        return isinstance(other, Var) and self.name == other.name
    def __hash__(self):
        return hash(self.name)

class Fun:
    def __init__(self, name: str, args: List['Term']):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"{self.name}({', '.join(map(str, self.args))})"
    def __eq__(self, other):
        return (
            isinstance(other, Fun)
            and self.name == other.name
            and len(self.args) == len(other.args)
            and all(a == b for a, b in zip(self.args, other.args))
        )
    def __hash__(self):
        return hash("@".join( [self.name] + [str(arg) for arg in self.args]))
        
class Predicate:
    def __init__(self, name: str, args: List['Term']):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"{self.name}({', '.join(map(str, self.args))})"
    def __eq__(self, other):
        return (
            isinstance(other, Predicate)
            and self.name == other.name
            and len(self.args) == len(other.args)
            and all(a == b for a, b in zip(self.args, other.args))
        )
    def __hash__(self):
        return hash("@".join( [self.name] + [str(arg) for arg in self.args]))
        
class Constance:
    def __init__(self, const: str):
        self.const = const 
    def __repr__(self):
        return f"{self.const}"
    def __eq__(self, other):
        return isinstance(other, Constance) and self.const == other.const
    def __hash__(self):
        return hash(self.const)


class Operation(Enum):
    NEG = "neg"
    AND = "and"
    OR = "or"
    IMPLIE = "imp"
    REVERSED_IMPLIE = "revimp"
    NOR = "uparrow"
    NAND = "downarrow"
    NOT_IMPLIE = "notimp"
    NOT_REVERSED_IMPLIE = "notrevimp"
    SOME = "some"
    ALL = "all"
    EQUAL = "equal"
    
    def is_unary_ops(self) -> bool:
        return self == Operation.NEG

    def is_binary_ops(self) -> bool:
        return self in {
            Operation.AND, Operation.OR, Operation.IMPLIE, Operation.REVERSED_IMPLIE,
            Operation.NOR, Operation.NAND, Operation.NOT_IMPLIE, Operation.NOT_REVERSED_IMPLIE
        }

    def is_quantifiers(self) -> bool:
        return self in {Operation.SOME, Operation.ALL}
        
# --- 용어 정의 ------------------------------------------------------------
# Term: 원자 기호나 함수 응용, 혹은 문자열(변수/상수)
Term = Union[Var, Fun, Constance]
Atom = Union[bool,Predicate]
Env = List[Tuple[Var, Term]]
Formula = Union[
    Atom,
    Term,
    Tuple[Operation, 'Formula'],                # 단항
    Tuple[Operation, 'Formula', 'Formula']      # 이항
]
Notated = Tuple[List[Var], Formula]

def partial_value(term: Term, env: Env) -> Term:
    if isinstance(term, Var):
        for (x, t) in env:
            if term == x:
                return partial_value(t, env)
    return term

def occurs_check(x: Var, term: Term, env: Env) -> bool:
    u = partial_value(term, env)
    if x == u:
        return True
    if isinstance(u, Fun):
        return any(occurs_check(x, arg, env) for arg in u.args)
    return False

def unify(t1: Term, t2: Term, env: Env) -> Env:
    u1 = partial_value(t1, env)
    u2 = partial_value(t2, env)

    if u1 == u2:
        return env

    if isinstance(u1, Var) and not occurs_check(u1, u2, env):
        return [(u1, u2)] + env

    if isinstance(u2, Var) and not occurs_check(u2, u1, env):
        return [(u2, u1)] + env

    if isinstance(u1, Fun) and isinstance(u2, Fun) and u1.name == u2.name and len(u1.args) == len(u2.args):
        return unify_list(u1.args, u2.args, env)

    raise ValueError(f"Cannot unify {u1} and {u2}")

def unify_list(args1: List[Term], args2: List[Term], env: Env) -> Env:
    for a, b in zip(args1, args2):
        env = unify(a, b, env)
    return env

#---------------------------------------------------------------------------------------------------------------

# AST 노드 정의
class Node:
    pass

class ForAll(Node):
    def __init__(self, var, body):
        self.var = var
        self.body = body

class Exists(Node):
    def __init__(self, var, body):
        self.var = var
        self.body = body

class Predicate(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args

class Not(Node):
    def __init__(self, body):
        self.body = body

class And(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Or(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Implies(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

# Skolem 함수 이름 생성기
_skolem_counter = itertools.count(1)

def new_skolem_function(free_vars):
    f_id = next(_skolem_counter)
    return f"f{f_id}({', '.join(free_vars)})" if free_vars else f"c{f_id}"

# 자유 변수 추출
def free_vars(node, bound=None):
    if bound is None:
        bound = set()
    if isinstance(node, Predicate):
        return set(arg for arg in node.args if arg not in bound)
    elif isinstance(node, (And, Or, Implies)):
        return free_vars(node.left, bound) | free_vars(node.right, bound)
    elif isinstance(node, Not):
        return free_vars(node.body, bound)
    elif isinstance(node, ForAll):
        return free_vars(node.body, bound | {node.var})
    elif isinstance(node, Exists):
        return free_vars(node.body, bound | {node.var})
    return set()

# Skolemization
def skolemize(node, bound_vars=None):
    if bound_vars is None:
        bound_vars = set()

    if isinstance(node, Exists):
        fvs = list(free_vars(node.body, bound_vars))
        skolem_term = new_skolem_function(fvs)
        replaced = replace_var(node.body, node.var, skolem_term)
        return skolemize(replaced, bound_vars)
    elif isinstance(node, ForAll):
        return ForAll(node.var, skolemize(node.body, bound_vars | {node.var}))
    elif isinstance(node, And):
        return And(skolemize(node.left, bound_vars), skolemize(node.right, bound_vars))
    elif isinstance(node, Or):
        return Or(skolemize(node.left, bound_vars), skolemize(node.right, bound_vars))
    elif isinstance(node, Implies):
        return Implies(skolemize(node.left, bound_vars), skolemize(node.right, bound_vars))
    elif isinstance(node, Not):
        return Not(skolemize(node.body, bound_vars))
    else:
        return node

# 변수 치환
def replace_var(node, var, term):
    if isinstance(node, Predicate):
        return Predicate(node.name, [term if arg == var else arg for arg in node.args])
    elif isinstance(node, ForAll):
        if node.var == var:
            return node
        return ForAll(node.var, replace_var(node.body, var, term))
    elif isinstance(node, Exists):
        if node.var == var:
            return node
        return Exists(node.var, replace_var(node.body, var, term))
    elif isinstance(node, And):
        return And(replace_var(node.left, var, term), replace_var(node.right, var, term))
    elif isinstance(node, Or):
        return Or(replace_var(node.left, var, term), replace_var(node.right, var, term))
    elif isinstance(node, Implies):
        return Implies(replace_var(node.left, var, term), replace_var(node.right, var, term))
    elif isinstance(node, Not):
        return Not(replace_var(node.body, var, term))
    else:
        return node

# AST 출력
def pretty_print(node):
    if isinstance(node, Predicate):
        return f"{node.name}({', '.join(node.args)})"
    elif isinstance(node, ForAll):
        return f"∀{node.var}.({pretty_print(node.body)})"
    elif isinstance(node, Exists):
        return f"∃{node.var}.({pretty_print(node.body)})"
    elif isinstance(node, Not):
        return f"¬({pretty_print(node.body)})"
    elif isinstance(node, And):
        return f"({pretty_print(node.left)} ∧ {pretty_print(node.right)})"
    elif isinstance(node, Or):
        return f"({pretty_print(node.left)} ∨ {pretty_print(node.right)})"
    elif isinstance(node, Implies):
        return f"({pretty_print(node.left)} → {pretty_print(node.right)})"
    return str(node)

# 테스트 예시
if __name__ == "__main__":
    # 예: ∃x ∀y P(x, y)  →  ∀y P(f1, y)
    formula = Exists("x", ForAll("y", Predicate("P", ["x", "y"])))
    print("원래 공식:")
    print(pretty_print(formula))
    skolemized = skolemize(formula)
    print("\nSkolemized 공식:")
    print(pretty_print(skolemized))