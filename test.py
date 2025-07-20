from auto_prove import Formula, Constant, Var, Function, Predicate, Operation, operation, is_operation, is_atom
from collections import deque 
from typing import Tuple,List
import re

_variation_pattern = re.compile(r'^[A-Za-z]$')

class String2FormulaConvertException(Exception):
    def __init__(self,message):
        super.__init__(message)

def _formula(formula:str) -> Tuple[Formula, str]:
    value = ""
    remain = None
    params = []
    while True:
        for i,ch in enumerate(formula):
            if ch == "(":
                formula, remain = _formula(formula[i:])
                params.append(formula)
                break 
            elif ch == ")":
                if value != "":
                    if value[0].isupper():
                        return (Predicate(value,params), formula[i:])
                    else:
                        return (Function(value,params), formula[i:])
                else:
                    return (tuple(params), formula[i:])
            elif ch == ',' or is_operation(ch) or i+1 == len(formula):
                if is_operation(ch):
                    params.append(operation(ch))
                                  
                if _variation_pattern.fullmatch(value):
                    params.append(Var(value))
                elif len(value) >= 1:
                    params.append(Constant(value))
                value = ""
            else:
                if ch != ' ':
                    value+=ch
        if remain == "" or remain is None:
            break              
        formula = remain
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