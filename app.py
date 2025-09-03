# pip install gradio==4.44.0
import gradio as gr
from datetime import datetime
from agent import ATPagent 
from auto_prove.interpreter import pre_modification_fol_interpreter as interpreter
from prompt import game_master_modelfile as modelfile
from langchain_core.messages import AnyMessage, AIMessage
from agent import ResponseParser
import re
import json,os
        
class ModelParser(ResponseParser):
    
    def parse(self,response:AnyMessage):
        match = re.search(r"<GM>(.*?)</GM>", response.content, re.DOTALL)
        if match:
            content = match.group(1)
            return AIMessage(content.strip())
        
        return response
parser = ModelParser()

user_instruction = {
                    "{{CONCEPT}}" : modelfile.CONCEPT,
                    "{{USER_INSTRUCTION}}":modelfile.USER_INSTRUCTION,
                    "{{INPUT_FORMAT}}":modelfile.INPUT_FORMAT,
                    "{{OUTPUT_FORMAT}}":modelfile.OUTPUT_FORMAT,
                    "{{RULES}}":modelfile.RULES,
                    "{{EXAMPLES}}":modelfile.EXAMPLES
                    }


#chat = ChatGPT(model_name="gpt-4o",buffer_length = 3000 ,max_tokens = 15000, timeout=60, max_retries=1,debug_mode_open=False)
agent = ATPagent(user_instruction=user_instruction,premises=[],response_parser=parser)
session = agent.get_sesesion()
RULEBOOK_DIR = "./rule_books"  

# ---------- Helper functions ----------
def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def append_log(log_text: str, entry: str) -> str:
    line = f"[{timestamp()}] {entry}"
    return (log_text + "\n" + line).strip()

def get_premises(premises: list) -> list:
    return [(interpreter(fol)[1],rule) for fol,rule in premises]

def list_rulebooks(dirpath: str) -> list[str]:
    """RULEBOOK_DIR 안의 .json 파일 목록을 반환 (파일명만)."""
    if not os.path.isdir(dirpath):
        return []
    return sorted([f for f in os.listdir(dirpath) if f.lower().endswith(".json")])

def load_rulebook_file(filename: str, rules: list[str], log_text: str):
    """
    선택한 파일을 읽어 rules_state를 교체.
    파일 형식은 [{ "formula": "...", "description": "..."}, ...] JSON 배열을 기대.
    """
    if not filename:
        return gr.update(value=rules), gr.update(value=log_text), gr.update(value=log_text) ,gr.update(choices=rules, value=[])
    path = os.path.join(RULEBOOK_DIR, filename)
    if not os.path.isfile(path):
        return  gr.update(value=rules), gr.update(value=log_text), gr.update(value=log_text) ,gr.update(choices=rules, value=[])

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # JSON -> [(formula, description)] 로 변환
        new_rules = []
        premises = []
        for i, item in enumerate(data):
            formula = item.get("formula")
            desc = item.get("description")
            if isinstance(formula, str) and isinstance(desc, str):
                new_rules.append(f"{desc} : {formula}")
                premises.append((agent._fol2formula(formula)[1],desc))

        rules += new_rules
        from datetime import datetime
        log_text = (log_text + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f'Rulebook loaded: "{filename}" (rules={len(rules)})').strip()
        logs = "\n".join([f"{i}. {premise}" for i, premise in enumerate(rules)])
        log_text += f"\n{logs}"
       
        agent._set_premises(premises)
        return  gr.update(value=rules), gr.update(value=log_text), gr.update(value=log_text) ,gr.update(choices=rules, value=[])
    except Exception as e:
        return  gr.update(value=rules), gr.update(value=log_text + f"\n{e}"), gr.update(value=log_text) ,gr.update(choices=rules, value=[])

# ---------- Rule management ----------
def add_rule(rule_text: str, rules: list[str], log_text: str):
    rule_text = (rule_text or "").strip()
    if not rule_text:
        # No-op UI update
        return gr.update(value=''), \
               gr.update(value=rules), \
               gr.update(value=log_text),\
               gr.update(value=log_text), gr.update(choices=rules, value=[])
               
    # Deduplicate while preserving order
    if rule_text not in rules:
        fol = agent._natural2fol(rule_text)
        rules = rules + [f"{rule_text} : {fol}"]
        agent._set_premises([(agent._fol2formula(fol)[1],rule_text)])
        log_text = append_log(log_text, f'Rule added: "{rule_text} : {fol}"')
    # 입력칸 비우기 + 룰 목록/드롭다운 갱신
    return (
        gr.update(value=''),
        gr.update(value=rules),
        gr.update(value=log_text),
        gr.update(value=log_text),
        gr.update(choices=rules, value=[])
    )

def clear_rules(rules: list[str], log_text: str):
    if rules:
        log_text = append_log(log_text, f"All rules cleared. (count={len(rules)})")
    deleted = [(agent._fol2formula(rule.split(":")[1].strip())[1],rule.split(":")[0].strip()) for rule in rules]
    agent._remove_premises(deleted)
    # 드롭다운도 비우기
    return gr.update(value=[]), gr.update(value=log_text), gr.update(value=log_text), gr.update(choices=[], value=[])

# 🔸 신규: 개별 삭제
def delete_selected_rule(selected: list[str] | None, rules: list[str], log_text: str):
    if selected is None or len(selected) == 0:
        return rules, log_text, gr.update(value=log_text), gr.update(choices=rules, value=[])
    deleted = set(selected)
    rules = [rule for rule in rules if rule not in deleted]
    new_premises = [(agent._fol2formula(rule.split(":")[1].strip())[1] ,rule.split(":")[0].strip()) for rule in rules]
    agent._set_premises(new_premises)
    for d in selected:
        log_text = append_log(log_text, f'Removed rule #: "{d}"')
    rules_txt = "\n".join(rules)
    log_text = append_log(log_text, f'rules : \n{rules_txt}')
    return gr.update(value=rules), gr.update(value=log_text), gr.update(value=log_text), gr.update(choices=rules, value=[])

# ---------- Chat handling ----------
def handle_chat(user_msg: str, chat_history: list, rules: list[str], log_text: str):
    global agent, session
    
    user = (user_msg or "").strip()
    user_message = {"role": "user", "content": user}
    
    if not user:
        return gr.update(value=chat_history), gr.update(value=log_text)

    response = None

    response = session.send(user)
    
    ok = response["ok"]
    error = str(response["error"]) 
    value = response['value']
    
    if ok: 
        message = {"role": "assistant", "content": value}
        log = f"증명 성공 \n  답변 : {value} "
    else: 
        message = {"role": "assistant", "content": "답변 할 수 없다."}
        log = f"증명 실패 \n 오류 : {error} \n 답변 : {value}"
    
    if response is None:
        agent = ATPagent(user_instruction=user_instruction,premises=[],response_parser=parser)
        session = agent.get_sesesion()
        return gr.update(value=[]), gr.update(value=log_text)

    chat_history = chat_history + [user_message, message]
    log_text = append_log(log_text, f'User: "{user}"')
    log_text = append_log(log_text, f'GM : "{log}"')
    return gr.update(value=chat_history), gr.update(value=log_text)

def show_items():
    return [[rule] for rule in rules_state]

# ---------- Build UI ----------
with gr.Blocks(title="TRPG Game Master Agent", fill_height=True) as demo:
    rules_state = gr.State([])        # list[str]
    premises = gr.State([])
    log_state = gr.State("")          # str
    chat_state = gr.State([])         # list[[user, assistant], ...]
    gr.Markdown("## 🎲 TRPG Game Master Chat\n"
                "Left: system logs and rules • Right: chat session.\n"
                "_(Outputs stay natural language; your pipeline can then translate to FOL and verify with tableau.)_")

    with gr.Row():
        # ---------- LEFT PANEL ----------
        with gr.Column(scale=5, min_width=420):
            with gr.Group():
                gr.Markdown("### 🧭 System Log")
                log_box = gr.Textbox(label="Log", value="", lines=18, interactive=False)
                
            with gr.Group():
                gr.Markdown("### 📚 Rulebook Loader")
                # 디렉토리의 JSON 파일 목록으로 드롭다운 구성
                rulebook_select = gr.Dropdown(
                    label="Select a rulebook (.json)",
                    choices=list_rulebooks(RULEBOOK_DIR),
                    value=None,
                    interactive=True
                )
                with gr.Row():
                    refresh_rb = gr.Button("Refresh list")
                    load_rb = gr.Button("Load selected", variant="primary")

            with gr.Group():
                gr.Markdown("### ⚙️ TRPG Rule Manager")
                rule_input = gr.Textbox(label="Add a rule (natural language)", placeholder="e.g., ‘Wizards can use magic.’")
                with gr.Row():
                    add_btn = gr.Button("Add Rule", variant="primary")
                    clr_btn = gr.Button("Clear All Rules", variant="secondary")
                    del_btn = gr.Button("Delete Selected", variant="stop")
                
                with gr.Row():
                    dataset = gr.CheckboxGroup(
                                label="rules"
                            )

        # ---------- RIGHT PANEL ----------
        with gr.Column(scale=7, min_width=520):
            chat = gr.Chatbot(label="Game Master", height=480, type="messages")
            user_box = gr.Textbox(label="Your action / dialogue", placeholder="Describe what you do or say...", lines=3)
            send_btn = gr.Button("Send", variant="primary")

    # ---- Bind events ----
    add_btn.click(
        add_rule,
        inputs=[rule_input, rules_state, log_state],
        outputs=[rule_input, rules_state, log_state, log_box, dataset],  # 🔸 드롭다운도 갱신
    )

    clr_btn.click(
        clear_rules,
        inputs=[rules_state, log_state],
        outputs=[rules_state, log_state, log_box, dataset],  # 🔸 드롭다운 비우기
    )

    # 🔸 개별 삭제 이벤트
    del_btn.click(
        delete_selected_rule,
        inputs=[dataset, rules_state, log_state],
        outputs=[rules_state, log_state, log_box, dataset],
    )

    def sync_log(log_text):  # Reflect log_state into readonly textbox
        return gr.update(value=log_text)

    send_btn.click(
        handle_chat,
        inputs=[user_box, chat_state, rules_state, log_state],
        outputs=[chat_state, log_state],
    ).then(
        fn=lambda: gr.update(value=""),
        inputs=None,
        outputs=user_box,
    ).then(
        sync_log,
        inputs=[log_state],
        outputs=[log_box],
    ).then(
        lambda hist: gr.update(value=hist),
        inputs=[chat_state],
        outputs=[chat],
    )

    user_box.submit(
        handle_chat,
        inputs=[user_box, chat_state, rules_state, log_state],
        outputs=[chat_state, log_state],
    ).then(
        fn=lambda: gr.update(value=""),
        inputs=None,
        outputs=user_box,
    ).then(
        sync_log,
        inputs=[log_state],
        outputs=[log_box],
    ).then(
        lambda hist: gr.update(value=hist),
        inputs=[chat_state],
        outputs=[chat],
    )
    
     # 앱 로드시 드롭다운 초기화
    demo.load(
        fn=lambda: gr.update(choices=list_rulebooks(RULEBOOK_DIR), value=None),
        inputs=None,
        outputs=rulebook_select
    )

    # 새로고침 버튼
    refresh_rb.click(
        fn=lambda: gr.update(choices=list_rulebooks(RULEBOOK_DIR), value=None),
        inputs=None,
        outputs=rulebook_select
    )

    # 로드 버튼: 파일 읽고 rules_state 교체 -> 슬롯 렌더 -> 프리뷰 업데이트 -> (선택) 로그 박스 반영
    load_rb.click(
        load_rulebook_file,
        inputs=[rulebook_select, rules_state, log_state],
        outputs=[rules_state, log_state, log_box, dataset],
    )
    

if __name__ == "__main__":
    demo.launch()


