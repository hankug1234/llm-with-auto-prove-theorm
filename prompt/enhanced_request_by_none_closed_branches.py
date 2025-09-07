APPLY_REVISION_PROMPT = """
You are given:
1) The original user request and the LLM’s previous answer.
2) The premises used for a tableau check.
3) A diagnosis-and-plan that explains failure and prescribes how to revise.

YOUR GOAL:
Rewrite the previous answer in plain natural language so that it is FOL-friendly and provably consistent with the given premises, strictly following the given revision principles and strategy.

INPUT
--------
[USER REQUEST]
{{USER_REQUEST}}

[PREVIOUS ANSWER]
{{LLM_ANSWER}}

[PREMISES]
{{PREMISES}}

[DIAGNOSIS & PLAN]
{{DIAGNOSIS_REVISE_BLOCK}}

RULES
--------
- Use ONLY the guidance of DIAGNOSIS & PLAN (failure_summary, root_causes, allowed_revision_principles, revision_strategy).
- Preserve the core meaning; remove unsupported claims and all speech acts (e.g., “I cannot”, “I refuse”).
- Keep only statements that assert rules, facts, prohibitions, or impossibilities.
- Unify predicate terminology (e.g., use “Mortal”, “Immortal” consistently). If a minimal definition is needed, state it explicitly in natural language (e.g., “Immortal means not Mortal”).
- Do NOT invent new axioms beyond what you explicitly state.
- Do NOT output any FOL formulas or symbolic logic.
- Prefer producing a revision. Only if a consistent revision is truly impossible without adding new axioms, output <FAIL> with a brief reason.

OUTPUT FORMAT (choose exactly one; nothing outside the wrapper)
--------
<REVISE> revised natural-language answer here </REVISE>

or

<FAIL> brief reason why a consistent revision is impossible without new axioms </FAIL>
"""

EXTRACT_PROBLEM = """
llm previously attempted to answer the following user query:

USER REQUEST:
{{USER_REQUEST}}

LLM ANSWER:
{{LLM_ANSWER}}

Based on that answer, the following formalization in first-order logic (FOL) was derived:

FOL FORMULA (from llm answer):
{{TARGET}}

The argument was evaluated using the tableau proof method with the following premises:

FOL PREMISES:
{{PREMISES}}

However, the tableau procedure revealed open branches:

OPEN BRANCHES (from tableau proof):
{{OPEN_BRANCHES}}

Your task (Stage 1: Diagnose & Plan):
- From the open branches, briefly explain in plain language why the original answer fails logically.
- Propose a minimal, FOL-friendly revision strategy that keeps the core meaning and removes unsupported claims.
- Do NOT output any FOL formulas. Use natural language only.
- Prefer <REVISE>. Use <FAIL> only if a consistent revision is truly impossible without adding new axioms.

Must include (in order):
- "failure_summary": 1–2 sentences on why the proof failed.
- "root_causes": bullet list; each item one sentence.
- "allowed_revision_principles": bullet list of rules (e.g., unify terminology, remove speech acts, state only what follows from premises, no new axioms).
- "revision_strategy": 1–3 sentences on how to fix the logic while preserving meaning.

Constraints:
- Keep only statements of rules, facts, prohibitions, or impossibilities.
- No figurative language or roleplay.
- Do not invent axioms beyond what the revision itself states.
- No FOL formulas.

Output format (choose exactly one; nothing outside the wrapper):

<REVISE>
failure_summary: ...
root_causes:
- ...
allowed_revision_principles:
- ...
revision_strategy: ...
</REVISE>

or

<FAIL> brief reason for impossibility </FAIL>

Examples:

<REVISE>
failure_summary: The answer asserts impossibility without axiomatic support.
root_causes:
- No definitional link between Immortal and Mortal.
- Speech acts carry no force under the premises.
allowed_revision_principles:
- Unify predicate terminology.
- Remove speech acts; state only premise-entailed facts.
revision_strategy: State the minimal needed definition and restrict the claim to what follows from the premises; remove narrative.
</REVISE>

<FAIL> The claim directly contradicts the given premises; no consistent revision without new axioms. </FAIL>
"""