PROMPT = """

You previously attempted to answer the following user query:

USER REQUEST:
{{USER_REQUEST}}

YOUR PREVIOUS ANSWER:
{{LLM_ANSWER}}

Based on your answer, the following formalization in first-order logic (FOL) was derived:

FOL FORMULA (from your answer):
{{TARGET}}

The argument was evaluated using the tableau proof method with the following premises:

FOL PREMISES:
{{PREMISES}}

However, the tableau procedure revealed that the argument is **not fully valid** — some branches remain **open**. These open branches represent possible interpretations under which your conclusion does not logically follow from the premises:

OPEN BRANCHES (from tableau proof):
{{OPEN_BRANCHES}}

These open branches suggest that your previous reasoning may include logical gaps, invalid inferences, or unsupported assumptions.

---

### 🔧 Your Tasks:

1. **Review** the open branches and analyze whether your answer failed to account for them.
2. **Revise** your original answer if needed, addressing the logical gaps or false assumptions.
3. **Justify** your revised conclusion with a clear logical explanation or example that is consistent with first-order logic.

**⚠️ Important:**  
Do not simply restate your previous answer. You must explicitly address the open branches and correct any reasoning errors or oversights they reveal.


"""