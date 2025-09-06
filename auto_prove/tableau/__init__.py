from typing import List, Tuple,  Optional, Dict, Set
import itertools, sys 
sys.path.append(".")
from auto_prove import unify_list, is_atom, Formula, Notated, Term, Function, Var, Operation, Predicate, Constant, Atom
import logging

class Tableau:
# --- Skolem 함수 인덱스 관리 ---------------------------------------------
    def __init__(self):
        self._sko_counter = itertools.count(1)
        self._reflex_seen: Dict[int, Set[int]] = {}   # branch_id → {hash(term), ...}
        self._terms_in_branch = set()

    def _new_sko_fun(self, free_vars: List[Var]) -> Function:
        """새로운 Skolem 함수 f_i(free_vars...)를 생성."""
        i = next(self._sko_counter)
        return Function(f"f_{i}",free_vars)

    def _reset_sko(self):
        """Skolem 함수 인덱스 리셋."""
        self._sko_counter = itertools.count(1)

    def _reset_reflex_seen(self):
        self._reflex_seen = {} 

    def _reset_terms_in_branch(self):
        self._terms_in_branch = set()
        

    # --- 노테이션 처리 --------------------------------------------------------
    def _formula(self, notated: Notated) -> Formula:
        return notated[1]

    def _make_notated(self, free: List[Var], formula: Formula) -> Notated:
        return (free.copy(), formula)

    # --- 항 및 공식 치환 -------------------------------------------------------
    def _substitute_term(self, term: Term, old: Term, new: Term) -> Term:
        if term == old:
            return new
        if isinstance(term, Function):
            return Function(term.name,[self._substitute_term(t, old, new) for t in term.args])
        return term

    def _substitute_in_formula(self, form: Formula, old: Term, new: Term) -> Formula:
        if isinstance(form, Predicate):
            return Predicate(form.name, [self._substitute_term(t, old, new) for t in form.args])

        if isinstance(form,Term):
            return self._substitute_term(form, old, new)

        if isinstance(form, tuple):
            if len(form) == 2:  # 단항 연산자
                op, sub = form
                return (op, self._substitute_in_formula(sub, old, new))
            elif len(form) == 3:  # 이항 연산자
                op, left, right = form
                return (op, self._substitute_in_formula(left, old, new), self._substitute_in_formula(right, old, new))

        return form 

    # --- 공식 형태 판별 및 구성 ------------------------------------------------

    def _is_unary_formula(self, form: Formula) -> bool:
        # double negation, neg true or neg false
        if isinstance(form , tuple):
            op = form[0]
            inner = form[1]
            
            return (
                op == Operation.NEG
                and (
                    (isinstance(inner, tuple) and inner[0] == Operation.NEG)
                    or isinstance(inner, bool)
                    )
            )
        return False

    def _is_conjunctive(self, form: Formula) -> bool:
        if not isinstance(form, tuple):
            return False

        op = form[0]

        # 직접 α
        if op in {Operation.AND,
                  Operation.NOR,
                  Operation.AND_IMPLIE_BI,
                  Operation.NOT_IMPLIE,
                  Operation.NOT_REVERSED_IMPLIE}:
            return True

        # 부정 α :  ¬(β형)
        if op == Operation.NEG and isinstance(form[1], tuple):
            inner_op = form[1][0]
            if inner_op in {Operation.OR,
                            Operation.IMPLIE,
                            Operation.REVERSED_IMPLIE,
                            Operation.NAND}:
                return True
        return False


    # β-공식 : 두 개의 브랜치를 만들어 분기
    def _is_disjunctive(self, form: Formula) -> bool:
        if not isinstance(form, tuple):
            return False

        op = form[0]

        # 직접 β
        if op in {Operation.OR, 
                  Operation.NAND,
                  Operation.IMPLIE, 
                  Operation.REVERSED_IMPLIE}:
            return True

        # 부정 β :  ¬(α형)
        if op == Operation.NEG and isinstance(form[1], tuple):
            inner_op = form[1][0]
            if inner_op in {Operation.AND,
                            Operation.NOR,
                            Operation.AND_IMPLIE_BI,
                            Operation.NOT_IMPLIE,
                            Operation.NOT_REVERSED_IMPLIE}:
                return True
        return False

    def _component(self, form: Formula) -> Formula:
        # 1) 단순 부정인 경우
        if isinstance(form, tuple) and form[0] == Operation.NEG \
        and isinstance(form[1], tuple) and form[1][0] == Operation.NEG:
            return form[1][1]                 # 바로 안쪽 식 하나만 꺼내 줌

        # 2) 논리 상수에 대한 부정은 별도 처리 (True/False를 상수 기호로 가정)
        if form == (Operation.NEG, True):
            return False
        if form == (Operation.NEG, False):
            return True

        raise ValueError(f"No unary component for {form}")

    def _components(self, form: Formula) -> Tuple[Formula, Formula]:
        if isinstance(form, tuple):
            op = form[0]
            if op == Operation.AND:
                return (form[1], form[2])
            if op == Operation.OR:
                return (form[1], form[2])
            if op == Operation.IMPLIE:
                return ((Operation.NEG, form[1]), form[2])
            if op == Operation.REVERSED_IMPLIE:
                return ((Operation.NEG, form[2]), form[1])
            if op == Operation.NOR:
                return ((Operation.NEG, form[1]), (Operation.NEG, form[2]))
            if op == Operation.NAND:
                return ((Operation.NEG, form[1]), (Operation.NEG, form[2]))
            if op == Operation.NOT_IMPLIE:
                return (form[1], (Operation.NEG, form[2]))
            if op == Operation.NOT_REVERSED_IMPLIE:
                return (form[2],(Operation.NEG, form[1]))
            if op == Operation.AND_IMPLIE_BI:
                return (Operation.IMPLIE,form[1], form[2]), (Operation.IMPLIE, form[2], form[1])
            if op == Operation.NEG and isinstance(form[1], tuple):
                inner = form[1]
                in_op, a, b = inner[0], inner[1], inner[2]

                match in_op:
                    case Operation.AND   : return (Operation.NEG, a), (Operation.NEG, b)
                    case Operation.OR    : return (Operation.NEG, a), (Operation.NEG, b)
                    case Operation.IMPLIE: return a,                (Operation.NEG, b)
                    case Operation.REVERSED_IMPLIE: return b,       (Operation.NEG, a)
                    case Operation.NOR   : return a, b
                    case Operation.NAND  : return a, b
                    case Operation.NOT_IMPLIE:
                        # ¬¬(A→B)  →  A→B  →  (¬A , B)
                        return (Operation.NEG, a), b
                    case Operation.NOT_REVERSED_IMPLIE:
                        # ¬¬(A←B)  →  A←B  →  (¬B , A)
                        return (Operation.NEG, b), a
                    case Operation.AND_IMPLIE_BI:
                        return (Operation.AND, a, (Operation.NEG, b)), (Operation.AND, b, (Operation.NEG, a))
                    
        raise ValueError(f"No components for {form}")

    def _is_existential(self, form: Formula) -> bool:
        if isinstance(form,tuple):
            op = form[0]
            inner = form[1]
            return (isinstance(form, tuple) and op == Operation.SOME) \
            or (isinstance(form, tuple) and op == Operation.NEG
                and isinstance(inner, tuple) and inner[0] == Operation.ALL)
        return False 

    def _is_universal(self, form: Formula) -> bool:
        if isinstance(form, tuple):
            op = form[0]
            inner = form[1]
            return (
                op == Operation.ALL
                or (op == Operation.NEG and isinstance(inner, tuple) and inner[0] == Operation.SOME)
            )
        return False

    def _instance(self, form: Formula, term: Term) -> Formula:
        op = form[0]
        inner = form[1]
        if op in {Operation.SOME,Operation.ALL}:
            _, var, body = form
            return self._substitute_in_formula(body, var, term)
        if op == Operation.NEG and isinstance(inner, tuple) and inner[0] in {Operation.SOME,Operation.ALL}:
            return (Operation.NEG, self._instance(inner, term))
        raise ValueError(f"No instance for {form}")

    def _already_reflex(self,branch, term) -> bool:
        """branch 에 대해 term 의 reflex 가 이미 삽입되었나?"""
        bid = id(branch)
        bucket = self._reflex_seen.setdefault(bid, set())
        h = hash(term)
        if h in bucket:
            return True          # 이미 있었음 → 삽입 스킵
        bucket.add(h)            # 최초 발견 → 기록하고 False 반환
        return False

    def _collect_terms(self, form: Formula):
        """등식(=)에 등장한 term만 모은다."""
        if (isinstance(form, tuple)
            and form[0] == Operation.EQUAL
            and len(form) == 3):
            self._terms_in_branch.add(form[1])

            self._terms_in_branch.add(form[2])

    # --- 단일 확장 단계 singlestep -------------------------------------------
    def _singlestep(
        self,
        tableau: List[List[Notated]],
        qdepth: int,
        equality: int
    ) -> Optional[Tuple[List[List[Notated]], int, int]]:

        for b_idx, branch in enumerate(tableau):
            self._terms_in_branch = set()
            # 1) Unary
            for f_idx, (free, form) in enumerate(branch):
                if self._is_unary_formula(form):
                    comp = self._component(form)
                    new_branch = branch[:f_idx] + [self._make_notated(free, comp)] + branch[f_idx+1:]
                    return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth, equality)
                
            # 2) Alpha
            for f_idx, (free, form) in enumerate(branch):
                if self._is_conjunctive(form):
                    a1, a2 = self._components(form)
                    new_branch = branch[:f_idx] + [self._make_notated(free, a1), self._make_notated(free, a2)] + branch[f_idx+1:]
                    return (tableau[:b_idx] + [new_branch] + tableau[b_idx+1:], qdepth, equality)
                
            # 3) Beta
            for f_idx, (free, form) in enumerate(branch):
                if self._is_disjunctive(form):
                    b1, b2 = self._components(form)
                    br1 = branch[:f_idx] + [self._make_notated(free, b1)] + branch[f_idx+1:]
                    br2 = branch[:f_idx] + [self._make_notated(free, b2)] + branch[f_idx+1:]
                    new_tb = tableau[:b_idx] + [br1, br2] + tableau[b_idx+1:]
                    return (new_tb, qdepth, equality)
            
            inst_notateds = []
            original_notateds = []
            removed_notateds = set()
            new_branch = []
            # 4) Gamma (universal)
            for f_idx, (free, form) in enumerate(branch):
                if self._is_universal(form) and qdepth > 0:
                    v = Var(f"V{qdepth}") 
                    inst = self._instance(form, v) 
                    inst_notated = self._make_notated(free, inst)
                    original_notated = self._make_notated([v] + free, form)
                    inst_notateds.append(inst_notated)
                    original_notateds.append(original_notated)
                    removed_notateds.add(f_idx)
            
            if len(removed_notateds) > 0:
                new_branch = [notated for i , notated in enumerate(branch) if i not in removed_notateds]
                        
            if len(inst_notateds) > 0:
                new_branch = inst_notateds + new_branch + original_notateds
                new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                return (new_tableau, qdepth - 1, equality)
                
            # 5) Equality reflexivity EXPANSION  (t = t 삽입)
            for _, formula in branch:
                self._collect_terms(formula)

            existing_eqs = {frm for _, frm in branch if isinstance(frm, tuple) and frm[0] == Operation.EQUAL and len(frm) == 3}

            for t in self._terms_in_branch:
                reflex = (Operation.EQUAL, t, t)
                
                if reflex in existing_eqs or self._already_reflex(branch, t):
                    continue  
                
                if reflex not in existing_eqs:                   # 아직 없다면 추가
                    new_branch = branch + [self._make_notated([], reflex)]
                    new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                    return (new_tableau, qdepth, equality)
                
            # 6) Equality SUBSTITUTIVITY (원자식 치환)  <— 기존 규칙 보강
            eqs = [
                (eqf[1], eqf[2])
                for _, eqf in branch
                if isinstance(eqf, tuple) and eqf[0] == Operation.EQUAL and len(eqf) == 3
            ]
            if eqs:
                existing_forms = {frm for _, frm in branch}            # 중복 방지
                for t1, t2 in eqs:
                    for free, frm in branch:
                        if not is_atom(frm):                         # (부정)원자식만 대상
                            continue

                        # --- t1 ↦ t2 치환 ---
                        new_f = self._substitute_in_formula(frm, t1, t2)
                        if equality > 0 and new_f != frm and new_f not in existing_forms:
                            new_branch = branch + [self._make_notated(free, new_f)]
                            new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                            return (new_tableau, qdepth, equality - 1)

                        # --- t2 ↦ t1 치환 (대칭) ---
                        new_f = self._substitute_in_formula(frm, t2, t1)
                        if equality > 0 and new_f != frm and new_f not in existing_forms:
                            new_branch = branch + [self._make_notated(free, new_f)]
                            new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                            return (new_tableau, qdepth, equality - 1)

            # 7) Equality reflexivity CLOSURE   ( ¬(t = t) → false )
            for free, frm in branch:
                if isinstance(frm, tuple) and frm[0] == Operation.NEG:
                    inner = frm[1]
                    if isinstance(inner, tuple) and inner[0] == Operation.EQUAL and inner[1] == inner[2]:
                        new_branch = branch + [([], False)]
                        new_tableau = tableau[:b_idx] + tableau[b_idx+1:] + [new_branch]
                        return (new_tableau, qdepth, equality)

                        
            # 8) Delta (existential)
            for f_idx, (free, form) in enumerate(branch):
                if self._is_existential(form):
                    term = self._new_sko_fun(free)
                    inst = self._instance(form, term)
                    new_branch = branch[:f_idx] + [self._make_notated(free, inst)] + branch[f_idx+1:]
                    return (tableau[:b_idx] + tableau[b_idx+1:] + [new_branch] , qdepth, equality)
        return None

    # --- 전체 확장 expand -----------------------------------------------------
    def _expand(self,tableau: List[List[Notated]], qdepth: int, equality: int) -> List[List[Notated]]:
        while True:
            step = self._singlestep(tableau, qdepth, equality)
            if not step:
                return tableau
            tableau, qdepth, equality = step
            

    # --- 분기 닫힘 검사 closed -----------------------------------------------
    def _is_literal(self,form: Formula) -> bool:
        """원자식 또는 그 부정인지 판별."""
        if isinstance(form, Predicate):
            return True                 # P(t)
        if (isinstance(form, tuple) and
            form[0] == Operation.NEG and
            isinstance(form[1], Predicate)):
            return True                 # ¬P(t)
        return False


    def _negate_literal(self,lit: Formula) -> Formula:
        """리터럴 lit의 논리적 부정을 돌려준다."""
        if isinstance(lit, Predicate):                 # P(t) → ¬P(t)
            return (Operation.NEG, lit)
        if (isinstance(lit, tuple) and lit[0] == Operation.NEG):
            return lit[1]                              # ¬P(t) → P(t)
        raise ValueError("not a literal")


    def _branch_closed(self, branch: List[Notated]) -> bool:
        # 1) false 리터럴
        if any(self._formula(n) == False for n in branch):
            return True
        
        literals = [n for n in branch if self._is_literal(self._formula(n))]
        if len(literals) == 0:
            return False

        # 3) 각 리터럴에 대해 부정형 존재 + 유일화 검사
        for free1, lit1 in literals:
            neg_lit1 = self._negate_literal(lit1)

            # neg_lit1 이 branch 에 존재하는지 확인
            for free2, lit2 in literals:
                if lit2 == neg_lit1:
                    return True

                # (a) 술어 이름, 인자 수가 일치하는지 (이미 lit2 == ¬lit1)
                # (b) 두 리터럴의 대응 term 들이 유일화(resolve) 되는지 확인
                try:
                    
                    if (isinstance(lit2, tuple) and lit2[0] == Operation.NEG
                            and isinstance(lit1, Predicate)):
                        lit2_inner = lit2[1]
                        if lit1.name == lit2_inner.name:
                            _ = unify_list(lit1.args, lit2_inner.args, [])
                            return True
                        
                    elif (isinstance(lit1, tuple) and lit1[0] == Operation.NEG
                            and isinstance(lit2, Predicate)):
                        lit1_inner = lit1[1]
                        if lit2.name == lit1_inner.name:
                            _ = unify_list(lit1_inner.args, lit2.args, [])
                            return True
                        
                except ValueError:
                    pass

        # 여기까지 왔으면 모순 쌍 없음 → 열린 브랜치
        return False


    def _closed(self,tableau: List[List[Notated]]) -> List[bool]:
        """tableau 의 모든 branch 가 닫혔으면 True"""
        return [self._branch_closed(branch) for branch in tableau]
            
    # ─────────────────────────────────────────────────────────────
    # 전제(assumptions)를 포함한 초기 branch 생성
    # ─────────────────────────────────────────────────────────────
    def _build_initial_branch(self, premises: List[Formula],
                            conclusion: Formula) -> List[Notated]:
        """
        S ⊢ X 를 tableau 로 증명하기 위한 branch:
        - 모든 전제 S 를 '참'으로,    (positive node)
        - 결론 X  는 '부정'으로 삽입. (¬X)
        """
        branch: List[Notated] = []

        # 1) 전제들을 먼저 positive 로 추가
        for prem in premises:
            branch.append(self._make_notated([], prem))

        # 2) 부정 결론 ¬X 추가
        branch.append(self._make_notated([], (Operation.NEG, conclusion)))

        return branch


    # ─────────────────────────────────────────────────────────────
    #  S ⊢ X  판단 함수 (premises + conclusion)
    # ─────────────────────────────────────────────────────────────
            
    def prove(self,
                premises: List[Formula], 
                conclusion: Formula,
                qdepth: int = 6,
                equality: int = 6) -> Tuple[bool, List[List[Notated]]]:
        """
        premises  (S) 가 주어졌을 때,
        결론 conclusion (X)이  Tableau 상에서 따르는지(S ⊢ X) 확인.
        반환값: True  → 증명 성공 (Theorem under premises)
                False → 깊이 qdepth 까지는 실패 (불완전할 수 있음)
        """
        self._reset_sko()                             # Skolem 인덱스 초기화
        self._reset_reflex_seen()
        self._reset_terms_in_branch()
        root_branch = self._build_initial_branch(premises, conclusion)
        tableau = self._expand([root_branch], qdepth, equality) # 기존 expand 사용
        branch_state = self._closed(tableau)
        none_closed_branches = [branch for is_closed, branch in zip(branch_state, tableau) if is_closed is False]
        return (all(branch_state), none_closed_branches)
