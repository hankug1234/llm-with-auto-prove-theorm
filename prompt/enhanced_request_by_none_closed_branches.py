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

Your Tasks:
1. Review the open branches and analyze why the original answer failed.
2. Revise the original answer to close the logical gaps and correct false assumptions.
3. If Revise is **impossible** (e.g., the request is paradoxical, axioms are missing/insufficient, or the content cannot be expressed consistently in FOL), **do not fabricate new assumptions**. Instead, output only a clear failure reason.

IMPORTANT:
- Do not simply restate the original answer.
- Be concise, factual, and FOL-friendly (avoid figurative/emotional language).
- If you output <FAIL> reason of failure </FAIL>, **do not** output <REVISE> Revise answer </REVISE>.

OUTPUT FORMAT (one of the following):
  <REVISE> Revise answer </REVISE>
  <FAIL> reason of failure </FAIL>

Examples:
  <REVISE> No being can be both a human and an orc at the same time. Therefore, your requested transformation is impossible, and you remain human. </REVISE>
  <FAIL> The request is paradoxical under the given axiom ∀x ¬(Human(x) ∧ Orc(x)). Any enhancement would require contradicting the stated premise or inventing unsupported assumptions. </FAIL>
"""