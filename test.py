from auto_prove import Formula, Atom, Term, Constance, Var, Fun, Terminology, Operation, operation, is_operation
from collections import deque 
import re

class OperationException(Exception):
    def __init__(self,message):
        super.__init__(message)

            
def _make_atom_or_term(stack):
    _stack = deque([e for e in stack])
    args = deque([])
    _name = ""
    while len(_stack) > 0:
        e = _stack[-1]
        if isinstance(e,Term):
            args.appendleft(_stack.pop())
        elif isinstance(e,Atom) or isinstance(e,Formula) or isinstance(e,Operation) or e == ' ' or e == ',' or (e == '(' and _name != "") :
                if '(' in _name: 
                    _name.replace('(',"")
                    if len(_name) > 0 and isinstance(e,Operation):
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
                        _stack.append(Constance(_name)) 
                        return _stack 
                return None 
        else:
            _past += _stack.pop()
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
    _formal_sentance = f"( {formal_sentance} )"
    _tokens = _formal_sentance.split(" ")
    _stack = deque([])
    
    for _token in _tokens:
            
        for ch in _token:
            
            if ch is ')':
                _stack = _make_atom_or_term(_stack)
                _make_formula(_stack)
            elif ch is ',':
                _stack = _make_atom_or_term(_stack)
            elif is_operation(ch):
                _stack = _make_atom_or_term(_stack)
                _pre_modifing(_stack,ch)
            else:
                _stack.append(ch) 
        _stack.append(" ")
    return _stack[0]
    