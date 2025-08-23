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

Output format:
- Write the revised answer as plain declarative sentences.
- Avoid figurative language.
- Structure sentences so they can be directly mapped to FOL predicates.

Example:
    Original Answer:
    "The air crackles with chaotic energy, but the attempt fails. Your form remains distinctly human, though a flicker of green briefly tints your skin. The fundamental laws of existence prevent such a paradoxical transformation."

    Feedback:
    "The request was to become both an orc and a human simultaneously, which is paradoxical. A more accurate response should state the impossibility of being both at once."

    Output:
    No being can be both a human and an orc.
    
Original Answer:
{{ORIGINAL_ANSWER}}

Feedback:
{{FEEDBACK}}
"""