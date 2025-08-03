from agent import ATPagent 
from custom_chat import ChatGPT

if __name__ == "__main__":
    user_instruction = {
                    "{{CONCEPT}}" : "",
                    "{{USER_INSTRUCTION}}":"",
                    "{{INPUT_FORMAT}}":"",
                    "{{OUTPUT_FORMAT}}":"",
                    "{{RULES}}":"",
                    "{{EXAMPLES}}":""
                 }
    chat = ChatGPT(model_name="gpt-4o",buffer_length = 3000 ,max_tokens = 15000, timeout=60, max_retries=1,debug_mode_open=False)
    agent = ATPagent(user_instruction=None,fol_translate_model=chat ,chat_model=chat)
    session = agent.get_sesesion()
    
    while True:
        user_input = input("사용자 입력 : ")
        response = session.send(user_input)
        if response is None:
            break 
        else:
            print(response)
        
    print("agent stoped ...")