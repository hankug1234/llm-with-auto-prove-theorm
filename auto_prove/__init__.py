from enum import Enum
from typing import List, Union, Tuple, Set


_logic_operator_mapping = {
    '¬': 'neg',
    '∧': 'and',
    '∨': 'or',
    '→': 'imp',
    '←': 'revimp',
    '↑': 'uparrow',
    '↓': 'downarrow',
    '¬→': 'notimp',        
    '¬←': 'notrevimp',     
    '↔': 'and_imp_bi',     
    '=': 'equal',
    '∀': 'all',
    '∃': 'some'
}

class Terminology:
    def __init__(self, name: str, args: List['Term']):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"terminology {self.name}({', '.join(map(str, self.args))})"
    def __str__(self):
        return f"terminology {self.name}({', '.join(map(str, self.args))})"
    def __eq__(self, other):
        return (
            isinstance(other, Terminology)
            and self.name == other.name
            and len(self.args) == len(other.args)
            and all(a == b for a, b in zip(self.args, other.args))
        )
    def __hash__(self):
        return hash(("terminology",self.name, tuple(self.args)))

# Represent variables and compound terms
class Var:
    def __init__(self, name: str):
        self.name = name
    def __repr__(self):
        return "var " + self.name
    def __str__(self):
        return "var " + self.name
    def __eq__(self, other):
        return isinstance(other, Var) and self.name == other.name
    def __hash__(self):
        return hash(("var", self.name))

class Fun:
    def __init__(self, name: str, args: List['Term']):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"function {self.name}({', '.join(map(str, self.args))})"
    def __str__(self):
        return f"function {self.name}({', '.join(map(str, self.args))})"
    def __eq__(self, other):
        return (
            isinstance(other, Fun)
            and self.name == other.name
            and len(self.args) == len(other.args)
            and all(a == b for a, b in zip(self.args, other.args))
        )
    def __hash__(self):
        return hash(("function",self.name, tuple(self.args)))
        
class Constance:
    def __init__(self, const: str):
        self.const = const 
    def __repr__(self):
        return f"constance {self.const}"
    def __str__(self):
        return f"constance {self.const}"
    def __eq__(self, other):
        return isinstance(other, Constance) and self.const == other.const
    def __hash__(self):
        return hash(("constance", self.const))
    

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
Atom = Union[bool,Terminology]
Env = List[Tuple[Var, Term]]
Formula = Union[
    Atom,
    Term,
    Tuple[Operation, 'Formula'],                # 단항
    Tuple[Operation, 'Formula', 'Formula']      # 이항
]
Notated = Tuple[List[Var], Formula]

def operation(logic_operation: str) -> Operation:
    try:
        return Operation(_logic_operator_mapping[logic_operation])
    except Exception as e:
        print(e)
        return None

def is_operation(logic_operation:str)->bool:
    return logic_operation in _logic_operator_mapping.keys()

def partial_value(term: Term, env: Env, visited: Set[Var] = None) -> Term:
    if visited is None:
        visited = set()
    if isinstance(term, Var):
        if term in visited:
            return term  # 순환 방지
        visited.add(term)
        for (x, t) in env:
            if term == x:
                return partial_value(t, env, visited)
    return term

def occurs_check(x: Var, term: Term, env: Env) -> bool:
    u = partial_value(term, env)
    if x == u:
        return True
    if isinstance(u, Fun):
        return any(occurs_check(x, arg, env) for arg in u.args)
    return False

def add_binding(env: Env, var: Var, term: Term) -> Env:
    # 기존 치환 제거 후 새로 추가
    return [(v, t) for (v, t) in env if v != var] + [(var, term)]

def unify(t1: Term, t2: Term, env: Env) -> Env:
    u1 = partial_value(t1, env)
    u2 = partial_value(t2, env)

    if u1 == u2:
        return env

    if isinstance(u1, Var) and not occurs_check(u1, u2, env):
        return add_binding(env, u1, u2)

    if isinstance(u2, Var) and not occurs_check(u2, u1, env):
        return add_binding(env, u2, u1)

    if isinstance(u1, Fun) and isinstance(u2, Fun) and u1.name == u2.name and len(u1.args) == len(u2.args):
        return unify_list(u1.args, u2.args, env)

    raise ValueError(f"Cannot unify {u1} and {u2}")

def unify_list(args1: List[Term], args2: List[Term], env: Env) -> Env:
    for a, b in zip(args1, args2):
        env = unify(a, b, env)
    return env
