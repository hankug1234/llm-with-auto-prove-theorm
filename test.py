from auto_prove import Formula, Atom, Term, Constant, Var, Fun, Terminology, Operation, operation, is_operation
from collections import deque 
import re

class OperationException(Exception):
    def __init__(self,message):
        super.__init__(message)

def is_atom(e)->bool:
    if isinstance(e,bool) or isinstance(e,Terminology):
        return True
    return False 

def is_term(e)->bool:
    if isinstance(e,Constant) or isinstance(e,Var) or isinstance(e,Fun):
        return True
    return False 

def is_formula(e)->bool:
    if is_atom(e) or is_term(e) or isinstance(e,tuple):
        return True
    return False 

def _make_atom_or_term(stack):
    _stack = deque([e for e in stack])
    args = deque([])
    _name = ""
    while len(_stack) > 0:
        e = _stack[-1]
        if isinstance(e,Term):
            args.appendleft(_stack.pop())
        elif is_formula(e) or isinstance(e,Operation) or e == ' ' or e == ',' or (e == '(' and _name != "") :
                if e == ' ' or e == ',':
                    _stack.pop()
                    
                if '(' in _name: 
                    _name.replace('(',"")
                    if len(_name) > 0 and _name[0].isupper():
                        _stack.append(Terminology(_name,list(args)))
                        return _stack
                    elif len(_name) > 0:
                        _stack.append(Fun(_name,list(args)))
                        return _stack
                elif '(' not in _name and len(args) == 0 :
                    if _name in ['⊤','true','True']:
                        _stack.append(True) 
                        return _stack
                    elif _name in ['⊥','false','False']:
                        _stack.append(False) 
                        return _stack 
                elif '(' not in _name and len(args) == 0 :
                    if re.fullmatch(r'[a-z]', _name):
                        _stack.append(Var(_name)) 
                        return _stack
                    elif _name:
                        _stack.append(Constant(_name)) 
                        return _stack 
        else:
            _name += _stack.pop()
    return None

def _make_formula(stack):
        new_formula = deque([])
        while len(stack) > 0:
            e = stack.pop()
            
            if e == '(':
                stack.append(tuple(new_formula))
                return 
            
            new_formula.appendleft(e)
            if isinstance(e,Operation):
                sub_formula = tuple(new_formula)
                new_formula.clear()
                new_formula.appendleft(sub_formula)
                        
def _pre_modifing(stack,ch):
    op = operation(ch)
    if op is None:
        raise OperationException("wrong operation")
    
    if op.is_binary_ops() or op.is_quantifiers():
        stack.append(op)
    else:
        e = stack.pop()
        stack.append(op)
        stack.append(e)       

def convert(formal_sentance: str) -> Formula:     
    _formal_sentance = f"({formal_sentance})"
    _tokens = _formal_sentance.split(" ")
    _stack = deque([])
    
    for _token in _tokens:
            
        for ch in _token:
            
            if ch == ')':
                _tmp = _make_atom_or_term(_stack)
                if _tmp:
                    _stack = _tmp
                _make_formula(_stack)
            elif ch == ',':
                _tmp = _make_atom_or_term(_stack)
                if _tmp:
                    _stack = _tmp
            elif is_operation(ch):
                _tmp = _make_atom_or_term(_stack)
                if _tmp:
                    _stack = _tmp
                _pre_modifing(_stack,ch)
            else:
                _stack.append(ch) 
        _stack.append(" ")
    return _stack[0]

if __name__ == "__main__":
    print(convert("∀x (P(x) → P(f(x)))"))