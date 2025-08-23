PROMPT = """
Instruction:
You are given two texts:
1. An original answer (may contain narrative, emotion, or unnecessary description).
2. Feedback highlighting logical gaps or paradoxes.

Your task:
- Revise the original answer using the feedback.
- Remove all narrative, emotional, or descriptive elements.
- Keep only the essential logical facts and constraints that can be easily expressed in first-order logic (FOL).
- The result must be short, unambiguous, and focused on the logical core.

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
    
Original Answer:
{{ORIGINAL_ANSWER}}

Feedback:
{{FEEDBACK}}
"""