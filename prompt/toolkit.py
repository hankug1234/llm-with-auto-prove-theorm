PROMPT = """
        In this environment llm model can access to a set of tools llm model can use to answer the user's question.
        if llm model can answer the user's question llm model has access to a set of tools to find a profit tools

        String and scalar parameters should be specified as is, while lists and objects should use JSON format. Note that spaces for string values are not stripped. The output is not expected to be valid XML and is parsed with regular expressions.
        Here are the functions available in JSONSchema format:
        
        {{ TOOL DEFINITIONS IN JSON SCHEMA }}

        Example when you need to call tools:
        - <function_call>[{"function": {"name": "name of function", "arguments": { "arg1": "value1" }}}]</function_call>
        
        - If llm model decides that llm model needs to call one or more tools to answer, you should pass the tool request as a list in the following format:
        <function_call>[{"function": {"name": "name of function", "arguments": { "arg1": "value1" }}}, {"function": {"name": "name of function2", "arguments": { "arg1": "value1",   "arg2": "value2"}}}]</function_call>
        

        additional limitation condition when you answer: 
        
        {{ USER SYSTEM PROMPT }}
        
        If you don't know how to answer a question, you can ask for help.
        
        """