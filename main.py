from agent import ATPagent 
from custom_chat import ChatGPT
from auto_prove.interpreter import pre_modification_fol_interpreter as interpreter

if __name__ == "__main__":
    user_instruction = {
                    "{{CONCEPT}}" : "",
                    "{{USER_INSTRUCTION}}":"",
                    "{{INPUT_FORMAT}}":"",
                    "{{OUTPUT_FORMAT}}":"",
                    "{{RULES}}":"",
                    "{{EXAMPLES}}":""
                 }
    
    
    world_rules = [
        "∀x (Human(x) → Mortal(x))",
        "¬(Dead(x) ∧ Alive(x))",
        "∀x (Wizard(x) → CanUseMagic(x))",
        "¬(Orc(x) ∧ Human(x))",
        "∀x (EnemyOf(x, y) → ¬FriendOf(x, y))"
    ] 
    
    premises = [interpreter(rule)[1] for rule in world_rules]
    
    #chat = ChatGPT(model_name="gpt-4o",buffer_length = 3000 ,max_tokens = 15000, timeout=60, max_retries=1,debug_mode_open=False)
    agent = ATPagent(user_instruction=None,premises=premises)
    session = agent.get_sesesion()
    
    while True:
        user_input = input("사용자 입력 : ")
        response = session.send(user_input)
        if response is None:
            break 
        else:
            print(response)
        
    print("agent stoped ...")
    
    #<FOL> ∀x (Guard(x) → (¬FeelsSad(x) ↔ ¬Lies(x))) </FOL>