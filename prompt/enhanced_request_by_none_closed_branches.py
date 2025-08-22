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
1. **Review** the open branches and analyze whether your answer failed to account for them.
2. **Revise** llm original answer if needed, addressing the logical gaps or false assumptions.
3. **Justify** your revised conclusion with a clear logical explanation or example that is consistent with first-order logic.

OUTPUT FORMAT:
- Output only the final line, no extra text:
  <FOL> your_expression </FOL>
  <NOT_FOL> reason </NOT_FOL>
  
EXAMPLES:
<FOL> ∀x (Cat(x) → Animal(x)) </FOL>
<FOL> ∃x (Person(x) ∧ Believes(x, Love)) </FOL>
<NOT_FOL> Nonsensical input </NOT_FOL>

IMPORTANT:  
Do not simply restate llm previous answer. You must explicitly address the open branches and correct any reasoning errors or oversights they reveal.


"""