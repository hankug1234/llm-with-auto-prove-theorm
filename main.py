from agent import ATPagent 


if __name__ == "__main__":
    user_instruction = {
                    "{{CONCEPT}}" : "",
                    "{{USER_INSTRUCTION}}":"",
                    "{{INPUT_FORMAT}}":"",
                    "{{OUTPUT_FORMAT}}":"",
                    "{{RULES}}":"",
                    "{{EXAMPLES}}":""
                 }
    agent = ATPagent(user_instruction=user_instruction)
    session = agent.get_sesesion()
    
    while True:
        user_input = input("사용자 입력")
        response = session.send(user_input)
        if response is None:
            break 
        else:
            print(response)
        
        