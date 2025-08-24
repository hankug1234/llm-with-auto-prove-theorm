PROMPT = """
Instruction:
    You are given a natural language question and answer.
    Your task is to extract only the core logical content that can be formalized in First-Order Logic (FOL).
        Ignore narrative elements (e.g., laughter, tone, emotions, metaphors).
        Keep only rules, facts, prohibitions, or impossibilities relevant to reasoning.
        If the core logic can be expressed as a single sentence, output it as one concise statement.
        If multiple logical steps are required, divide the output into two sections:
            [Premises]: list the essential assumptions/rules as short simple sentences.
            [Conclusion]: state the final claim that follows.
        
Format:
    [Question Reformulated] <logical restatement of the question>  
    [Answer Core Logic]  
    <one sentence if possible>  
    -- OR --  
    [Premises]  
    1. ...  
    2. ...  
    [Conclusion]  
    ...  

Input:
    Question : {{QUESTION}}
    Answer : {{ANSWER}}
"""