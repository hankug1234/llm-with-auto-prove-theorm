PROMPT = """
Instruction:
You are given a natural language question and answer.
Your task is to extract only the core logical content that can be formalized in First-Order Logic (FOL).
Ignore narrative elements (e.g., laughter, tone, emotions, metaphors).
Keep only statements that assert rules, facts, prohibitions, or impossibilities.
Rephrase figurative language into strict logical propositions.
If the answer contains multiple claims, break them down into separate simple statements.
Output the result in clear, minimal natural-language sentences suitable for FOL translation.

Input:
Question : {{QUESTION}}
Answer : {{ANSWER}}
"""