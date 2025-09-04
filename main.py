from agent import ATPagent 
from custom_chat import ChatGPT
from auto_prove.interpreter import pre_modification_fol_interpreter as interpreter
from prompt import game_master_modelfile as modelfile
from langchain_core.messages import AnyMessage, AIMessage
from agent import ResponseParser
import re


'''
todo list 

1. fol 변환 llm이 자연어를 술어 논리 언어로 번역 할때 전제에 사용된 것과 동일한 의미의 술어를 사용한다면 같은 술어로 번역 해야함 
    a. 전제에서 술어를 추출 해서 술어표현과 그 의미를 기제하고 동일한 의미에 해당 할시 해당 표현을 사용 하라고 해야함 -> 사전에 정의한 술어 추가 프롬프트 삽입 하여 해결

2. 현재 trpg 상황에 맞는 인격를 작성 해야함 / 게임 마스터 llm에 사용자의 응답에 맞는 행동을 하도록 프롬프트 작성
결
3. 게임 마스터 llm의 답변 형식에 맞는 파서 작성

4. 백터 디비로 과거 플레이 내용을 요약 저장     
    성
'''

if __name__ == "__main__":
    user_instruction = {
                    "{{CONCEPT}}" : modelfile.CONCEPT,
                    "{{USER_INSTRUCTION}}":modelfile.USER_INSTRUCTION,
                    "{{INPUT_FORMAT}}":modelfile.INPUT_FORMAT,
                    "{{OUTPUT_FORMAT}}":modelfile.OUTPUT_FORMAT,
                    "{{RULES}}":modelfile.RULES,
                    "{{EXAMPLES}}":modelfile.EXAMPLES
                 }
    class ModelParser(ResponseParser):
        
        def parse(self,response:AnyMessage):
            match = re.search(r"<GM>(.*?)</GM>", response.content, re.DOTALL)
            if match:
                content = match.group(1)
                return AIMessage(content.strip())
            
            return response
    parser = ModelParser()
    
    world_rules = [
        ("∀x (Human(x) → Mortal(x))","Humans are mortal."),
        ("¬(Dead(x) ∧ Alive(x))","Death and life cannot exist simultaneously."),
        ("∀x (Wizard(x) → CanUseMagic(x))","Wizards can use magic."),
        ("¬(Orc(x) ∧ Human(x))","Orcs and humans are distinct races."),
        ("∀x (EnemyOf(x, y) → ¬FriendOf(x, y))","One cannot be both an enemy and a friend at the same time."),
        ("∀x (Immortal(x) ↔ ¬Mortal(x))","Immortality is the negation of mortality.")
    ] 
    
    premises = [(interpreter(fol)[1],rule) for fol,rule in world_rules]
    
    #chat = ChatGPT(model_name="gpt-4o",buffer_length = 3000 ,max_tokens = 15000, timeout=60, max_retries=1,debug_mode_open=False)
    agent = ATPagent(manager_prompt=user_instruction,premises=premises,response_parser=parser)
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