from auto_prove import Formula, Constant, Var, Function, Predicate, Operation, operation, is_operation, is_atom, is_term, is_formula
from collections import deque 
from typing import Tuple,List,Union
import re,sys

sys.setrecursionlimit(10000)

_variation_pattern = re.compile(r'^[x-z][0-9]*$')

class String2FormulaConvertException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

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
            all_is_term = all((is_term(_param)) for _param in _params)
            
            if len(value) >= 1 and value[0].isupper() and all_is_term:
                sub_formula = Predicate(value,list(_params))
            elif len(value) >= 1 and all_is_term:
                sub_formula = Function(value,list(_params))
            else:
                sub_formula = _params
                primitive = _primitive(value)
                if primitive is not None:
                    params.append(primitive)
                
            params.append(sub_formula)
            formula = remain
            i = 0
            value=""
            continue
        elif ch == ")":
            
            primitive = _primitive(value)
            if primitive is not None:
                params.append(primitive)
                
            value = ""
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
    if len(params) == 1:
        return (params[0],remain)
    return (tuple(params),remain)

def _pre_modification(formula: Formula)->Formula:

    if is_atom(formula) or is_term(formula):
        return formula
    else:
        temp = None
        queue = deque(list(formula))
        while len(queue) > 0:
            f = queue.popleft()
            if isinstance(f,Operation):
                if f.is_binary_ops():
                    return (f,temp,_pre_modification((e for e in queue)))
                elif f.is_quantifiers():
                    return (f,queue.popleft(), _pre_modification((e for e in queue)))
                else:
                    negs = []
                    while len(queue) > 0 and isinstance(queue[0], Operation) and queue[0].is_unary_ops():
                        negs.append(queue.popleft())
                    if len(queue) > 0:
                        temp = queue.popleft() 
                        for neg in negs:
                            temp = (neg,temp)
                        temp = (f,_pre_modification(temp))
                    else:    
                        raise String2FormulaConvertException("convert error")
            else:
                temp = _pre_modification(f)
    if temp is None:
        raise String2FormulaConvertException("convert error")
    
    return temp

    
def _seperate_premises(premises:Formula) -> List[Formula]:
    
    def _seperate_point(e,stack):
        if isinstance(e,Operation) and not e.is_binary_ops():
            if len(stack) > 0 and is_formula(stack[-1]):
                return True 
        elif len(stack) > 0 and is_formula(stack[-1]) and is_formula(e):
            if len(stack) > 1 and isinstance(stack[-2],Operation) and not stack[-2].is_quantifiers():
                return True
            elif len(stack) == 1:
                return True 
        return False
                        
    if is_atom(premises):
        return [premises]
    
    stack = []
    seperated = []
    for e in premises:
        if _seperate_point(e,stack):
            if len(stack) == 1:
                seperated.append(stack[0])
            else:
                seperated.append(tuple(stack))
            
            stack = []    
            stack.append(e)
        else:
            stack.append(e)
                    
    if len(stack) > 0:
        seperated.append(tuple(stack))
    return seperated 

def pre_modification_fol_interpreter(fol:str) -> Tuple[List[Formula], Formula]:
    
    conclusion = "⊢"
    
    if conclusion in fol:
        premises, goal = fol.split(conclusion)
        premises,_ = _formula(premises)
        premises = _seperate_premises(premises)
        goal,_ = _formula(goal)
        print(premises,goal)
        return ([_pre_modification(premise) for premise in premises ], _pre_modification(goal)) 
    
    goal,_ = _formula(fol)
    return ([], _pre_modification(goal))


if __name__ == "__main__":
    print(pre_modification_fol_interpreter("P(a),  ∀x( P(x) → Q(x) ) ⊢ Q(a)"))