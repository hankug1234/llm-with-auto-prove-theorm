from auto_prove import Formula, Constant, Var, Function, Predicate, Operation, operation, is_operation, is_atom
from collections import deque 
from typing import Tuple,List
import re,sys

sys.setrecursionlimit(10000)

_variation_pattern = re.compile(r'^[a-z]$')

class String2FormulaConvertException(Exception):
    def __init__(self,message):
        super.__init__(message)

def _formula(formula:str) -> Tuple[Formula, str]:
    value = ""
    remain = None
    params = []
    i = 0
    while i < len(formula):
        ch = formula[i]
        if ch == "(":
            formula, remain = _formula(formula[i+1:])
            params.append(formula)
            formula = remain
            i = 0
            continue
        elif ch == ")":
            if value:
                if value[0].isupper():
                    return (Predicate(value,params), formula[i+1:])
                else:
                    return (Function(value,params), formula[i+1:])
            else:
                return (tuple(params), formula[i+1:])
        elif ch == ',' or is_operation(ch) or i+1 == len(formula):
                                
            if _variation_pattern.fullmatch(value):
                params.append(Var(value))
            elif len(value) >= 1:
                if value == "false":
                    params.append(False)
                elif value == "true":
                    params.append(True)
                else:
                    params.append(Constant(value))
                value = ""
            if is_operation(ch):
                params.append(operation(ch))
        else:
            if ch != ' ':
                value+=ch
        i+=1           

    return (tuple(params),remain)

def _pre_modification(formula: Formula)->Formula:

    if is_atom(formula):
        return formula
    else:
        temp = []
        queue = deque(list(formula))
        while len(queue) > 0:
            f = queue.popleft()
            if isinstance(f,Operation):
                if f.is_binary_ops():
                    temp.append((f,temp.pop(),_pre_modification(queue.appendleft())))
                else:
                    temp.append((f,_pre_modification(queue.appendleft())))
            else:
                temp.append(_pre_modification(f))
        return temp[0]

def str2formula(fol:str) -> Tuple[List[Formula], Formula]:
    
    conclusion = "⊢"
    
    if conclusion in fol:
        premises, goal = fol.split(conclusion)
        premises = _formula(premises)
        goal = _formula(goal)
        return ([_pre_modification(premise) for premise in premises ], _pre_modification(goal)) 
    goal = _formula(fol)
    return ([], _pre_modification(goal))


if __name__ == "__main__":
    print(str2formula("∀x (P(x) → P(f(x)))")[1])