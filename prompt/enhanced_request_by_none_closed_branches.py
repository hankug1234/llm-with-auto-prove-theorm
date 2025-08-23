PROMPT = """
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