from auto_prove import Formula, Constant, Var, Function, Predicate, Operation, operation, is_operation, is_atom, is_term, is_formula
from collections import deque 
from typing import Tuple,List,Union
import re,sys

sys.setrecursionlimit(10000)

_variation_pattern = re.compile(r'^[a-z]$')

class String2FormulaConvertException(Exception):
    def __init__(self,message):
        super.__init__(message)

def _primitive(value:str)->Union[bool,Var,Constant]:
    if _variation_pattern.fullmatch(value):
        return Var(value)
    elif len(value) >= 1:
        if value == "false":
            return False
        elif value == "true":
            return True
        else:
            return Constant(value)
    else:
        return None

def _formula(formula:str) -> Tuple[Formula, str]:
    params = []
    value, remain = "", ""
    i = 0
    while i < len(formula):
        ch = formula[i]
        if ch == "(":
            _params, remain = _formula(formula[i+1:])
            if re.fullmatch(_variation_pattern,value):
                sub_formula = Predicate(value,list(_params))
            elif len(value) >= 1:
                sub_formula = Function(value,list(_params))
            else:
                sub_formula = _params
            params.append(sub_formula)
            formula = remain
            i = 0
            value=""
            continue
        elif ch == ")":
            
            primitive = _primitive(value)
            if primitive is not None:
                params.append(primitive)
            
            return (tuple(params), formula[i+1:])
        elif ch == ',' or ch.isspace() or is_operation(ch) or i+1 == len(formula):
                                
            primitive = _primitive(value)
            if primitive is not None:
                params.append(primitive)
                
            if is_operation(ch):
                params.append(operation(ch))
            value = ""
            
        else:
            value+=ch
        i+=1           

    return (tuple(params),remain)

def _pre_modification(formula: Formula)->Formula:

    if is_atom(formula) or is_term(formula):
        return formula
    else:
        temp = []
        queue = deque(list(formula))
        while len(queue) > 0:
            f = queue.popleft()
            if isinstance(f,Operation):
                if f.is_binary_ops():
                    return (f,temp.pop(),_pre_modification(tuple(queue)))
                elif f.is_quantifiers():
                    return (f,queue.popleft(), _pre_modification(tuple(queue)))
                else:
                    return (f,_pre_modification(tuple(queue)))
            else:
                temp.append(_pre_modification(f))
        return temp[0]
    
def _seperate_premises(premises:List[Formula]) -> List[Tuple]:
    stack = []
    seperated = []
    for formula in premises:
        if len(stack) != 0 and is_formula(stack[-1]) and not is_formula(formula) :
            seperated.append(tuple(stack))
            stack = []    
            stack.append(formula)
        else:
            stack.append(formula)
                    
    if len(stack) > 0:
        seperated.append(tuple(stack))
    return seperated 

def str2formula(fol:str) -> Tuple[List[Formula], Formula]:
    
    conclusion = "⊢"
    
    if conclusion in fol:
        premises, goal = fol.split(conclusion)
        premises,_ = _formula(premises)
        premises = _seperate_premises(premises)
        goal,_ = _formula(goal)
        return ([_pre_modification(premise) for premise in premises ], _pre_modification(goal)) 
    goal,_ = _formula(fol)
    print(goal)
    return ([], _pre_modification(goal))


if __name__ == "__main__":
    print(str2formula("∀x (P(x) → P(f(x)))")[1])