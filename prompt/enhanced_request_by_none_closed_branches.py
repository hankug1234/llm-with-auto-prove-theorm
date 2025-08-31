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

EXTRACT_PROBLEM2 = """
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
- Analyze the open branches and explain, in plain natural language, why the original answer fails logically.
- Extract the minimal, FOL-friendly **revision strategy** that preserves the core meaning but removes unsupported claims.
- Produce a concise **revised answer (natural language only)** that will be provably consistent with the given premises when later converted to FOL.
- DO NOT output any FOL formula. Output natural language only.
- Always prefer giving a <REVISE> revision.
- Only if a revision is truly impossible (e.g. the request is paradoxical and cannot be expressed consistently in FOL without inventing new axioms), then output <FAIL> with the reason.


Your output must contain following components:
- "failure_summary": Briefly explain why the proof failed (e.g., predicate name mismatch, missing definitional link, negation error, speech acts with no axiomatic force).
- "root_causes": A bullet-style list of concrete issues inferred from the open branches (each item one sentence, natural language).
- "allowed_revision_principles": Short rules for how to revise (e.g., unify terminology, remove speech acts, state only rules/facts/impossibilities that follow from premises, avoid inventing new axioms).
- "revision_strategy": The minimal plan to fix the logic while keeping the core meaning (1–3 sentences).

Constraints:
- Keep only statements that assert rules, facts, prohibitions, or impossibilities.
- No figurative language, no roleplay/speech acts.
- Do not fabricate new axioms beyond what the revised answer explicitly states.

Output format restrictions:
- Respond with **exactly one** of the two wrappers below. Do not include anything outside the chosen wrapper.
- Inside the wrapper, include the required components **verbatim as labeled fields** in natural language (not JSON), in the order listed.
- Do NOT output any FOL formulas.

For a successful revision, output:

<REVISE>
failure_summary: ...
root_causes:
- ...
- ...
allowed_revision_principles:
- ...
- ...
revision_strategy: ...
</REVISE>

For an impossible revision, output:

<FAIL> reason of failure here </FAIL>

Examples:

<REVISE>
failure_summary: The answer asserts impossibility without axiomatic support and mixes speech acts with facts.
root_causes:
- No definitional link between Immortal and Mortal was stated.
- Speech acts (claims of inability) carry no force under the premises.
- Predicate naming is inconsistent across the argument.
allowed_revision_principles:
- Unify terminology across predicates.
- Remove speech acts; keep only rules, facts, or impossibilities grounded in premises.
- Introduce only minimal definitions necessary for proof; do not add unsupported axioms.
revision_strategy: State the needed definitional link explicitly and reduce claims to those entailed by the premises; remove narrative elements.
</REVISE>

<FAIL> reason of failure here </FAIL>
"""

PROMPT_PAST3 = """
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

However, the tableau procedure revealed that the argument is **not fully valid** — some branches remain **open**.:

OPEN BRANCHES (from tableau proof):
{{OPEN_BRANCHES}}

Your task:
- Analyze the open branches and explain why the original answer fails logically.
- Then, whenever possible, rewrite the answer in clear, minimal natural language that preserves the core meaning but removes the logical gaps, so that it can be consistently expressed and proven in FOL later.
- The revision must be concise, factual, and state only rules, facts, or impossibilities in plain natural language.
- Always prefer giving a <REVISE> revision.
- Only if a revision is truly impossible (e.g. the request is paradoxical and cannot be expressed consistently in FOL without inventing new axioms), then output <FAIL> with the reason.

Output format restrictions:
  <REVISE> revised natural language answer here </REVISE>
  <FAIL> reason of failure here </FAIL>

Examples:
  <REVISE> Humans are defined as mortal, therefore no human can be immortal. </REVISE>
  <FAIL> The request directly contradicts the axiom ∀x (Human(x) → Mortal(x)), and no consistent natural language revision is possible without inventing new rules. </FAIL>
"""

PROMPT_PAST2 = """
llm previously attempted to answer the following user query:

USER REQUEST:
{{USER_REQUEST}}

LLM ANSWER:
{{LLM_ANSWER}}

Based on llm answer, the following formalization in first-order logic (FOL) was derived:

FOL FORMULA (from llm answer):
{{TARGET}}

The argument was evaluated using the tableau proof method with the following premises:

FOL PREMISES:
{{PREMISES}}

However, the tableau procedure revealed that the argument is **not fully valid** — some branches remain **open**.:

OPEN BRANCHES (from tableau proof):
{{OPEN_BRANCHES}}

Your task:
- Analyze the open branches and explain why the original answer fails logically.
- Then, whenever possible, rewrite the answer in a concise, FOL-friendly way that fixes those problems so that the reasoning can be expressed consistently and provably.
- Always prefer giving a <REVISE> revision. 
- Only if a revision is truly impossible (e.g. the request itself is paradoxical and cannot be expressed consistently in FOL without inventing new axioms), then output <FAIL> with the reason.

Output format restrictions:
  <REVISE> revised answer here </REVISE>
  <FAIL> reason of failure here </FAIL>

Examples:
  <REVISE> No being can be both a human and an orc at the same time. Therefore, your requested transformation is impossible, and you remain human. </REVISE>
  <FAIL> The request is paradoxical under the given axiom ∀x ¬(Human(x) ∧ Orc(x)). Any enhancement would require contradicting the stated premise. </FAIL>
"""


PROMPT_PAST = """
llm previously attempted to answer the following user query:

USER REQUEST:
{{USER_REQUEST}}

LLM ANSWER:
{{LLM_ANSWER}}

Based on llm answer, the following formalization in first-order logic (FOL) was derived:

FOL FORMULA (from llm answer):
{{TARGET}}

The argument was evaluated using the tableau proof method with the following premises:

FOL PREMISES:
{{PREMISES}}

However, the tableau procedure revealed that the argument is **not fully valid** — some branches remain **open**.:

OPEN BRANCHES (from tableau proof):
{{OPEN_BRANCHES}}

These open branches suggest that llm previous reasoning may include logical gaps, invalid inferences, or unsupported assumptions.
Look at the open branches and find reason why the original answer does not work then Rewrite the answer to fix those problems.

Rules:
- If Revise is **impossible** (e.g., the request is paradoxical, axioms are missing/insufficient, or the content cannot be expressed consistently in FOL), **do not fabricate new assumptions**. Instead, output only a clear failure reason.
- Do not simply restate the original answer.
- Be concise, factual, and FOL-friendly (avoid figurative/emotional language).
- If you output <FAIL> reason of failure </FAIL>, **do not** output <REVISE> Revise answer </REVISE>.

Output format restrictions:
  <REVISE> Revise answer </REVISE>
  <FAIL> reason of failure </FAIL>

Examples:
  <REVISE> No being can be both a human and an orc at the same time. Therefore, your requested transformation is impossible, and you remain human. </REVISE>
  <FAIL> The request is paradoxical under the given axiom ∀x ¬(Human(x) ∧ Orc(x)). Any enhancement would require contradicting the stated premise or inventing unsupported assumptions. </FAIL>
"""