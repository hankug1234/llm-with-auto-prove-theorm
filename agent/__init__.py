from enum import Enum
import uuid,sys 
sys.path.append(".")
from auto_prove.interpreter import pre_modification_fol_interpreter, fol2sentance
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import OllamaEmbeddings
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AnyMessage, RemoveMessage, ToolMessage
from pydantic import BaseModel, Field
from typing import Annotated, TypedDict, Union, Any, Callable, List, Tuple
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.store.base import BaseStore, SearchItem
from langgraph.types import Command, interrupt
from agent.toolkits import Tools
from langgraph.prebuilt import ToolNode
from auto_prove.tableau import Tableau
from auto_prove import Formula, Notated, Operation, operation2string
from prompt.enhanced_request_by_none_closed_branches import PROMPT as enhanced_request
from prompt.fol_convertor_mini import PROMPT as fol_convertor_mini 
from prompt.agent_modelfile import PROMPT as agent_modelfile
from prompt.revise import PROMPT as revise_prompt
from prompt.extract_core_logic import PROMPT as extract_core_logic
from langchain_core.runnables.config import RunnableConfig
import threading, re
import logging
from html import unescape

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
FOL_RESULT_PATTERN = r"<\s*FOL\s*>([\s\S]*?)<\s*/\s*FOL\s*>"
TOOL_RESULT_PATTERN = r"<\s*function_call\s*>([\s\S]*?)<\s*/\s*function_call\s*>"
REVISE = r"<\s*REVISE\s*>([\s\S]*?)<\s*/\s*REVISE\s*>"
FAIL = r"<\s*FAIL\s*>([\s\S]*?)<\s*/\s*FAIL\s*>"

def add(a: List[Any], b: List[Any]):
    return a + b

class Mode(Enum):
    CORE = "core"
    ENHANCED = "enhanced"
    TOOL = "tool"
    END = "end"
    DECISION = "decision"
    PROVE = "prove"


class EnhancedRequestMessage(SystemMessage):
    def __init__(self, content: str,origin_answer: str, core_logic: str ,**kwargs):
        super().__init__(content=content, **kwargs)
        self.origin_answer = origin_answer
        self.core_logic = core_logic
        
    def __repr__(self):
        return f"EnhancedMessage(content={self.content!r})"
    
class EnhanceFailMessage(AIMessage):
    def __init__(self, content: str,origin_answer:str, core_logic:str ,**kwargs):
        super().__init__(content=content, **kwargs)
        self.origin_answer = origin_answer
        self.core_logic = core_logic
        
    def __repr__(self):
        return f"EnhancedMessage(content={self.content!r})"
    
class ChatModelNoneException(Exception):
    def __init__(self,message="chat model is None"):
        super().__init__(message)
        
class FolConvertFailException(Exception):
    def __init__(self,message="fol convert fail"):
        super().__init__(message)
        
class OverMaxAttemptionException(Exception):
    def __init__(self,message="over max attemption"):
        super().__init__(message)
    
class State(TypedDict):
    history: Annotated[list[AnyMessage], add_messages]
    user_instruction: SystemMessage
    mode: Mode
    is_proved: bool 
    error: Exception
    tool_count: int = 0
    enhance_count: int = 0

class Return(TypedDict):
    ok: bool 
    value: str
    error: Exception 
    
class Session:
    def __init__(self, thread_id: str, sessions: dict[str, Any], lock: threading.Lock):
        self.thread_id = thread_id
        self.lock = lock
        self.__sessions = sessions
    
    def __repr__(self):
        return f"Session(thread_id={self.thread_id})"
    
    def __str__(self):
        return f"Session(thread_id={self.thread_id})"
    
    def send(self, query: str):
        try:
            return self.__sessions[self.thread_id].send(query)
        except StopIteration:
            with self.lock:
                del self.__sessions[self.thread_id]
            return None

class ResponseParser:
    def parse(response:AnyMessage) -> AnyMessage:
        return response

class ATPagent:
    def __init__(self
                 ,user_id : str = "admin"
                 ,end_signal : str = "kill"
                 ,user_instruction : dict = {
                    "{{CONCEPT}}" : "",
                    "{{USER_INSTRUCTION}}":"",
                    "{{INPUT_FORMAT}}":"",
                    "{{OUTPUT_FORMAT}}":"",
                    "{{RULES}}":"",
                    "{{EXAMPLES}}":""
                 }
                 ,premises : List[Tuple[Formula,str]] = []
                 ,response_parser = ResponseParser
                 ,max_attemption : int = 3
                 ,tools : List[Callable] =[]
                 ,custom_tool_mode: bool = True
                 ,chat_model = None
                 ,fol_translate_model = None
                 ,embeddings=None
                 ,fields: List[str] = []
                 ,prove_system = Tableau()):
        
        self.custom_tool_mode = custom_tool_mode
        if len(tools) > 0:
            if custom_tool_mode:
                self.tools = Tools(tools)
            else:
                self.tools = ToolNode(tools=tools)
        else:
            self.tools = None 
            
        self.end_signal = end_signal
        self.user_id = user_id
        self.max_attemption = max_attemption
        self.user_instruction = user_instruction
        
        if embeddings is None:
            embeddings = OllamaEmbeddings(model="llama3")
        
        if chat_model is None:
            chat_model = ChatOllama(model="gemma3:12b")
            
        if fol_translate_model is None:
            fol_translate_model = ChatOllama(model="gemma3:12b")
        
        if chat_model is None:
            raise ChatModelNoneException
        
        self.chat_model = chat_model
        self.embeddings = embeddings 
        self.fol_translate_model = fol_translate_model
        
        self.memory = InMemoryStore(index={
        "embed": self.embeddings,
        "dims": 4096,
        "fields":fields
        })
        
        self.checkpointer = MemorySaver()
        self.graph_builder = StateGraph(state_schema=State)
        self.prove_system = prove_system
        self.sessions = {}
        self.lock = threading.Lock()
        self.premises = []
        self.nl_premises = []
        for premise, nl_premise in premises:
            self.premises.append(premise)
            self.nl_premises.append(nl_premise)
        self.response_parser = response_parser
        self.set_fol_translater_mode()
        self.graph = self._build()
    
    def _set_premises(self,premises: List[Tuple[Formula,str]]):
        for premise, nl_premise in premises:
            self.premises.append(premise)
            self.nl_premises.append(nl_premise)
        self.set_fol_translater_mode()
    
    def _remove_premises(self, premises):
        for premise, nl_premise in premises: 
            self.premises.remove(premise)
            self.nl_premises.remove(nl_premise)
        self.set_fol_translater_mode()
    
    def _make_agent_model(self):
        if self.user_instruction is None:
            return ""
        return agent_modelfile\
               .replace("{{CONCEPT}}",self.user_instruction["{{CONCEPT}}"])\
               .replace("{{USER_INSTRUCTION}}",self.user_instruction["{{USER_INSTRUCTION}}"])\
               .replace("{{INPUT_FORMAT}}",self.user_instruction["{{INPUT_FORMAT}}"])\
               .replace("{{OUTPUT_FORMAT}}",self.user_instruction["{{OUTPUT_FORMAT}}"])\
               .replace("{{RULES}}",self.user_instruction["{{RULES}}"])\
               .replace("{{EXAMPLES}}",self.user_instruction["{{EXAMPLES}}"])\
    
    def _retrive_long_term_memory(self, namespace: str ,query: str , limit: int, store:BaseStore)-> list[SearchItem]: 
        return store.search((self.user_id, namespace), query=query, limit=limit)
    
    def _save_long_term_memory(self, namespace: str, value: dict[str, Any], store:BaseStore):
        store.put((self.user_id,namespace),str(uuid.uuid4()),value)
        
    def _natural2fol(self,natural : str) -> str:
        result = self.fol_translate_model.invoke([SystemMessage(self.fol_translater_prompt),HumanMessage(natural)]).content
        fol = self._get_result(result, FOL_RESULT_PATTERN)
        logging.info(f"fol : {fol}")
        if fol is None:
            raise FolConvertFailException(f"reason : {result}")
        return fol
    
    def _fol2formula(self, fol) -> Tuple[List[Formula], Formula]:
        _converter = pre_modification_fol_interpreter
        formula = _converter(fol.strip())
        return formula
        
    def _formal_language_converter(self,natural_sentance : str) -> Tuple[List[Formula], Formula]:
        fol = self._natural2fol(natural_sentance)
        formula = self._fol2formula(fol)
        return  formula
    
    def _current_user_request(self,history:list[AnyMessage]) -> HumanMessage: 
        for message in history[::-1]:
            if isinstance(message,HumanMessage):
                return message 
        return None
            
    def _enhaned_request(self, branches: List[List[Notated]], request:str,\
        answer:str, premises:List[Formula], goal:Formula) -> str:
        
        branches = [[fol2sentance(notate[1]) for notate in branch] for branch in branches]
        branches = [[f"({f})" for f in branch if f is not None] for branch in branches ]
        rows = []
        for i, branch in enumerate(branches):
            if len(branch) >= 2:
                row = f" {operation2string(Operation.AND)} ".join(branch)
                row = f"{i}. {row}"
            else:
                row = f"{i}. {row}"
            rows.append(row)
        branches = '\n'.join(rows)
        
        target = fol2sentance(goal)
        premises = [f" {i}. {fol2sentance(premise)}" for i,premise in enumerate(premises)]
        premises = "\n".join(premises)
        
        return enhanced_request\
        .replace("{{USER_REQUEST}}",f"- {request}")\
        .replace("{{LLM_ANSWER}}",f"- {answer}")\
        .replace("{{TARGET}}",f"- {target}")\
        .replace("{{PREMISES}}",premises)\
        .replace("{{OPEN_BRANCHES}}",branches)
    
    def _get_result(self,script: str, pattern : str):
        if script is None:
            return None

        pat = re.compile(pattern, re.IGNORECASE)
        m = pat.search(script)
        if m:
            return m.group(1).strip()

        s2 = unescape(script)
        if s2 != script:
            m = pat.search(s2)
            if m:
                return m.group(1).strip()

        s3 = re.sub(r"\x1b\[[0-9;]*m", "", s2)
        if s3 != s2:
            m = pat.search(s3)
            if m:
                return m.group(1).strip()

        return None
    
    def _core_model(self,state:State, config: RunnableConfig):
        thread_id = config.get("configurable", {}).get("thread_id")
        error, is_proved = state["error"], state["is_proved"]
        response,message = None, None 
        tool_call_results = None
        
        try:
            message = state["history"][-1]
            if isinstance(message,EnhancedRequestMessage):
                response = self.chat_model.invoke([SystemMessage(message.content)])
                fail = self._get_result(response.content, FAIL)
                revise = self._get_result(response.content, REVISE)
                if fail is not None: 
                    response = EnhanceFailMessage(fail,origin_answer=message.origin_answer, core_logic=message.core_logic)
                elif revise is not None:
                    response = AIMessage(revise)
                else:
                    raise Exception(f"enhanced request fail : {response.content}")
            elif isinstance(message,SystemMessage):
                logging.info(f"thread{thread_id}:core_model:system_request={message}")
                response = self.chat_model.invoke([message])
            else:
                logging.info(f"thread{thread_id}:core_model:user_request={message}")
                response = self.chat_model.invoke([state["user_instruction"],message])
            logging.info(f"thread{thread_id}:core_model:llm_response={response}")
            
            if self.custom_tool_mode:
                tools = self._get_result(response.content, TOOL_RESULT_PATTERN)
                if tools:
                    tool_call_results = SystemMessage("\n".join([f"{k} = {v}" for k,v in self.tools.tools_calling(tools)]))
                    
            if response.tool_calls:
                tool_call_results = self.tools.invoke({"messages": [response]})['messages'] 
            
            if tool_call_results is not None: 
                logging.info(f"thread{thread_id}:core_model:tool_call_results={tool_call_results}")
                return {"history": [response,tool_call_results]
                        ,"mode":Mode.TOOL
                        ,"tool_count" : state["tool_count"] + 1
                        ,"enhance_count" : state["enhance_count"]
                        ,"is_proved" : is_proved
                        ,"error" : error}
                    
            if self.response_parser:
                response = self.response_parser.parse(response)    
            
            return {"history": [response]
                ,"mode": Mode.PROVE
                ,"tool_count" : state["tool_count"]
                ,"enhance_count" : state["enhance_count"]
                ,"is_proved" : is_proved
                ,"error" : error}         
                
        except Exception as e:
            logging.error(f"thread{thread_id}:core_model:error={e}")
            return {"mode" : Mode.END, "error" :e, "is_proved": False, "tool_count":0, "enhance_count":0}
        
    
    def _auto_prove(self,state:State, config:RunnableConfig):
        thread_id = config.get("configurable", {}).get("thread_id")
        is_proved,error = False,None
        answer = state["history"][-1].content
        
        try:
            if isinstance(state["history"][-1], EnhanceFailMessage):
                return {
                "mode": Mode.DECISION
                ,"tool_count" : state["tool_count"]
                ,"enhance_count" : state["enhance_count"]
                ,"is_proved" : is_proved
                ,"error" : Exception("enhance request fail for current reason")} 
            
            origin_request = self._current_user_request(state["history"])
            
            extract_core_logic_prompt = extract_core_logic\
                .replace("{{QUESTION}}",origin_request.content)\
                .replace("{{ANSWER}}",answer)
                
            logging.info(f"thread{thread_id}:auto_prove:extract_core_logic_prompt={extract_core_logic_prompt}")
            core_logic = self.chat_model.invoke([SystemMessage(extract_core_logic_prompt)]).content
            logging.info(f"thread{thread_id}:auto_prove:core_logic={core_logic}")
            
            fol_formula = self._formal_language_converter(core_logic)
            premises,goal = fol_formula
            premises = premises + self.premises
            is_proved, none_closed_branches = self.prove_system.prove(premises=premises, conclusion=goal)
            
            logging.info(f"thread{thread_id}:auto_prove:is_proved={is_proved}")
            logging.info(f"thread{thread_id}:auto_prove:formula={fol_formula}")
            
            if not is_proved:
                request = self._enhaned_request(none_closed_branches,origin_request.content,answer,premises,goal)
                logging.info(f"thread{thread_id}:auto_prove:enhanced_request={request}")
                
                return {"history" : [EnhancedRequestMessage(request,origin_answer=answer, core_logic=core_logic)]
                        ,"mode": Mode.ENHANCED
                        ,"tool_count" : state["tool_count"]
                        ,"enhance_count" : state["enhance_count"] + 1
                        ,"is_proved" : is_proved
                        ,"error" : error}        
            
        except FolConvertFailException as e:
            error = e
            logging.error(f"thread{thread_id}:auto_prove:error={e}")
            
        except Exception as e:
            error = Exception("internal error")
            logging.error(f"thread{thread_id}:auto_prove:error={e}")
        
        return {
                "mode": Mode.DECISION
                ,"tool_count" : state["tool_count"]
                ,"enhance_count" : state["enhance_count"]
                ,"is_proved" : is_proved
                ,"error" : error} 

    def _decision(self,state:State, config:RunnableConfig):
        thread_id = config.get("configurable", {}).get("thread_id")
        error, is_proved = state["error"], state["is_proved"]
        tool_count, enhance_count = state["tool_count"], state["enhance_count"]
        mode, max = state["mode"], self.max_attemption
        
        logging.info(f"thread{thread_id}:end_or_loop_decision:error={error}")

        if(error is None):
            if (mode == Mode.ENHANCED  and  enhance_count  > max) or  (mode == Mode.TOOL  and tool_count  > max) :
                is_proved, error = False, OverMaxAttemptionException()
                logging.info(f"thread{thread_id}:end_or_loop_decision:error={error}")
            elif (mode == Mode.ENHANCED and enhance_count <= max) or (mode ==  Mode.TOOL and not tool_count <= max):
                logging.info(f"thread{thread_id}:end_or_loop_decision:mode={mode}")
                return { "mode": Mode.CORE
                        ,"tool_count" : state["tool_count"]
                        ,"enhance_count" : state["enhance_count"]
                        ,"is_proved" : False
                        ,"error" : None}
        logging.info(f"thread{thread_id}:end_or_loop_decision:decision=end")
        return {
                "mode": Mode.END
                ,"tool_count" : 0
                ,"enhance_count" : 0
                ,"is_proved" : is_proved
                ,"error" : error
                }
    
    def _route(self,state:State):
        if state["mode"] == Mode.END:
            return END
        elif state["mode"] == Mode.CORE:
            return "core_model"
        elif state["mode"] == Mode.DECISION or state["mode"] == Mode.ENHANCED or state["mode"] == Mode.TOOL :
            return "end_or_loop_decision" 
        else:
            return "auto_prove"
    
    def _build(self):
        self.graph_builder.add_node("core_model",self._core_model)
        self.graph_builder.add_node("auto_prove",self._auto_prove)
        self.graph_builder.add_node("end_or_loop_decision",self._decision)
        self.graph_builder.add_edge(START,"core_model")
        self.graph_builder.add_conditional_edges("core_model", self._route,["auto_prove","end_or_loop_decision",END])
        self.graph_builder.add_edge("auto_prove","end_or_loop_decision")
        self.graph_builder.add_conditional_edges("end_or_loop_decision", self._route, ["core_model",END])
        
        return self.graph_builder.compile(checkpointer=self.checkpointer,store=self.memory)

    def set_fol_translater_mode(self):
        if len(self.nl_premises) > 0:
            pre_defined = "\n".join([ f"- {premise}: {nl_premise}"  for premise, nl_premise in zip(self.premises,self.nl_premises)])
        else:
            pre_defined = "Predefined predicates dont exist"
        self.fol_translater_prompt = fol_convertor_mini.replace("{{PREDICATE_LIST}}",pre_defined)
        
    
    async def async_excute(self, query :str, thread_id: str = "1"):
        config = {
            "configurable" : {
                "thread_id": thread_id
            }
        }
        query = {"history":[HumanMessage(query)]}
        async for event in self.graph.astream(query, stream_mode="updates", config=config):
            yield event
            
    def get_sesesion(self):
        thread_id = None 
        if len(self.sessions.keys()) == 0:
            thread_id = str(0)
        else:
            thread_id = str(max([int(key) for key in self.sessions.keys()]) + 1)
        
        config = {
            "configurable" : {
                "thread_id": thread_id
            }
        }
        graph = self.graph 
        
        if self.tools:
            user_instruction = SystemMessage(self.tools.get_template(self._make_agent_model()))
        else:
            user_instruction = SystemMessage(self._make_agent_model())
                    
        def make_session():
            query = yield
            state = {
                    "history" : [HumanMessage(query)], 
                    "user_instruction" : user_instruction,
                    "tool_count" : 0,
                    "enhance_count" : 0,
                    "mode" : Mode.CORE,
                    "is_proved" : False,
                    "error" : None
                    }
            
            while True: 
                state = graph.invoke(state,config=config)
                response = Return(ok=state["is_proved"], value=state["history"][-1].content, error=state["error"])
                query = yield response
                
                if query == self.end_signal:
                    logging.info(f"thread{thread_id}:end")
                    return
                 
                state["mode"] = Mode.CORE
                state["history"] = [HumanMessage(query)]
                state["is_proved"] = False,
                state["error"] = None
                 
        session = make_session()
        next(session)
        self.sessions[thread_id] = session
            
        return Session(thread_id, self.sessions, self.lock)