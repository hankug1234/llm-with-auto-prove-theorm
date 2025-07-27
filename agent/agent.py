import uuid,sys 
sys.path.append(".")
from auto_prove.interpreter import pre_modification_fol_interpreter, pre_modification_fol2sentance
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import OllamaEmbeddings
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AnyMessage, RemoveMessage
from pydantic import BaseModel, Field
from typing import Annotated, TypedDict, Union, Any, Callable, List, Dict, Tuple
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.store.base import BaseStore, SearchItem
from langgraph.types import Command, interrupt
from agent.toolkits import Tools
from auto_prove.tableau import Tableau
from auto_prove import Formula, Notated, Operation, operation2string
from prompt.enhanced_request_by_none_closed_branches import PROMPT as enhanced_request
from prompt.fol_convertor_strict import PROMPT as fol_convertor_strict 
from prompt.fol_convertor_none_strict import PROMPT as fol_convertor_none_strict
from prompt.agent_modelfile import PROMPT as agent_modelfile



def add(a: List[Any], b: List[Any]):
    return a + b
    
class ChatModelNoneException(Exception):
    def __init__(self,message="chat model is None"):
        super().__init__(message)
        
class FolConvertFailException(Exception):
    def __init__(self,message="fol convert fail"):
        super().__init__(message)

class ToolCallResponse(BaseModel):
    """이것은 llm model이 tools를 호출 할떄 사용 하는 양식 입니다 . <function>[{“function”: {“name”: “some name”, “arguments”: { “some arguments”: “some content” }}},...]</function> 이런 형식의 문장이 답변에 포함 되어 있을시 이 도구를 사용 하세요 """
    tools: str = Field(description="[{“function”: {“name”: “some name”, “arguments”: { “some arguments”: “some content” }}},...]" )

class MessageResponse(BaseModel):
    """이것은 llm model 의 일반적인 반환 양식 입니다. tools 호출 이외에는 이 양식을 사용 합니다.  """
    answer: str = Field(description="response of llm model") 

class Response(BaseModel):
    result: Union[ToolCallResponse,MessageResponse]
    
class FOLMessageResponse(BaseModel):
    """
    if llm output like FOL: <First-Order Logic expression> format use this response type   
    """    
    answer: str = Field(description="<First-Order Logic expression>") 

class NoneFOLMessageResponse(BaseModel):
    """
    if llm output like NOT_FOL: <reason> format use this response type   
    """    
    answer: str = Field(description="<reason>") 

class TranslateResponse(BaseModel):
    result: Union[FOLMessageResponse,NoneFOLMessageResponse]
    
class State(TypedDict):
    history: Annotated[list[AnyMessage], add_messages]
    premises: Annotated[list[Formula], add]
    user_instruction: SystemMessage
  

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
                 ,max_attemption : int = 5
                 ,tools : List[Callable] =[] 
                 ,chat_model = None
                 ,fol_translate_model = None
                 ,embeddings=None
                 ,fields: List[str] = []
                 ,prove_system = Tableau()
                 ,fol_strict_mode: bool = False):
        
        if len(tools) > 0:
            self.tools = Tools(tools)
        else:
            self.tools = None 
        self.end_signal = end_signal
        self.user_id = user_id
        self.max_attemption = max_attemption
        self.user_instruction = user_instruction
        
        if embeddings is None:
            embeddings = OllamaEmbeddings(model="llama3")
        
        if chat_model is None:
            chat_model = ChatOllama(model="gemma3:12b").with_structured_output(Response,method="json_schema")
            
        if fol_translate_model is None:
            fol_translate_model = ChatOllama(model="gemma3:12b").with_structured_output(TranslateResponse,method="json_schema")
        
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
        
        self.set_fol_translater_mode(fol_strict_mode)
        
        self.checkpointer = MemorySaver()
        self.graph_builder = StateGraph(state_schema=State)
        self.graph = self._build()
        self.prove_system = prove_system
    
    def _make_agent_model(self):
        return agent_modelfile\
               .replace("{{CONCEPT}}",self.user_instruction["{{CONCEPT}}"])\
               .replace("{{USER_INSTRUCTION}}",self.user_instruction["{{USER_INSTRUCTION}}"])\
               .replace("{{INPUT_FORMAT}}",self.user_instruction["{{INPUT_FORMAT}}"])\
               .replace("{{OUTPUT_FORMAT}}",self.user_instruction["{{OUTPUT_FORMAT}}"])\
               .replace("{{RULES}}",self.user_instruction["{{RULES}}"])\
               .replace("{{EXAMPLES}}",self.user_instruction["{{EXAMPLES}}"])\
    
    def _init_context(self, state : State):
        if self.tools:
            user_instruction = SystemMessage(self.tools.get_template(self._make_agent_model()))
        else:
            user_instruction = SystemMessage(self._make_agent_model())
        return {"history" : [], "user_instruction" : user_instruction}
    
    def _retrive_long_term_memory(self, namespace: str ,query: str , limit: int, store:BaseStore)-> list[SearchItem]: 
        return store.search((self.user_id, namespace), query=query, limit=limit)
    
    def _save_long_term_memory(self, namespace: str, value: dict[str, Any], store:BaseStore):
        store.put((self.user_id,namespace),str(uuid.uuid4()),value)
        
        
    def _formal_language_converter(self,fol_sentance : str) -> Tuple[List[Formula], Formula]:
        _converter = pre_modification_fol_interpreter
        result = self.fol_translate_model.invoke([SystemMessage(self.fol_translater_prompt),HumanMessage(fol_sentance)]).result 
        if isinstance(result,NoneFOLMessageResponse):
            raise FolConvertFailException()
        
        return _converter(result.answer)
    
    def _current_user_request(history:list[AnyMessage]) -> HumanMessage: 
        for message in history[::-1]:
            if isinstance(message,HumanMessage):
                return message 
        return None
            
    def _enhaned_request(self, branches: List[List[Notated]], request:str,\
        answer:str, premises:List[Formula], goal:Formula) -> str:
        
        branches = [[pre_modification_fol2sentance(formula) for formula in branch[1]] for branch in branches]
        branches = [ f"{i}. {operation2string(Operation.AND)} ".join(branch) for i,branch in enumerate(branches) ]
        branches = '\n'.join(branches)
        
        target = pre_modification_fol2sentance(goal)
        premises = [f" {i}. {pre_modification_fol2sentance(premise)}" for i,premise in enumerate(premises)]
        premises = "\n".join(premises)
        
        return enhanced_request\
        .replace("{{USER_REQUEST}}",f"- {request}")\
        .replace("{{LLM_ANSWER}}",f"- {answer}")\
        .replace("{{TARGET}}",f"- {target}")\
        .replace("{{PREMISES}}",premises)\
        .replace("{{OPEN_BRANCHES}}",branches)
        
        
    def _core_model(self,state:State):
        if isinstance(state["history"][-1],HumanMessage) and state["history"][-1].content == self.end_signal:
            return Command(goto=END)
        
        if len(state["history"]) >=self.max_attemption\
            and not any([isinstance(message,HumanMessage) for message in state["history"][-self.max_attemption:]]):
            user_message = interrupt("fail")
            response = self.chat_model.invoke([state["user_instruction"],HumanMessage(user_message)]).result
        else:
            response = self.chat_model.invoke([state["user_instruction"],state["history"][-1]]).result
            
        if isinstance(response,ToolCallResponse):
            tool_call_results = "\n".join([f"{k} = {v}" for k,v in self.tools.tools_calling(response.tools)])
            return Command(goto="core_model", update = {"history": [SystemMessage(tool_call_results)]})
            
        return {"history": [AIMessage(response.answer)]}
    
    def _auto_prove(self,state:State):
        try:
            fol_formula = self._formal_language_converter(state["history"][-1].content)
            origin_answer = state["history"][-1].content
            origin_request = self._current_user_request(state["history"])
            
            premises,goal = fol_formula
            premises = premises + state["premises"]
            is_proved, none_closed_branches = self.prove_system.prove(premises=premises, conclusion=goal)
            
            if not is_proved:
                request = self._enhaned_request(none_closed_branches,origin_request,origin_answer,premises,goal)
                return {"history" : [SystemMessage("\n".join(request[1]))]}        
                
            user_question = interrupt(state["history"][-1].content)
            return {"history" : [HumanMessage(user_question)]}
            
        except FolConvertFailException:
            pass 
        except Exception:
            pass 


    def _build(self):
        self.graph_builder.add_node("init",self._init_context)
        self.graph_builder.add_node("core_model",self._core_model)
        self.graph_builder.add_node("auto_prove",self._auto_prove)
        self.graph_builder.add_edge(START,"init")
        self.graph_builder.add_edge("init","core_model")
        self.graph_builder.add_edge("core_model","auto_prove")
        self.graph_builder.add_edge("core_model","auto_prove")
        self.graph_builder.add_edge("persona_manager","summarize")
       
        
        return self.graph_builder.compile(checkpointer=self.checkpointer,store=self.memory)

    def set_fol_translater_mode(self,strict:bool):
        self.fol_strict_mode = strict
        if self.fol_strict_mode:
            self.fol_translater_prompt = fol_convertor_strict
        else: 
            self.fol_translater_prompt = fol_convertor_none_strict
    
    async def async_excute(self, query :Dict[str,Any], thread_id: str = "1"):
        config = {
            "configurable" : {
                "thread_id": thread_id
            }
        }

        async for event in self.graph.astream(query, stream_mode="updates", config=config):
            yield event
    
    def excute(self, query :Dict[str,Any], thread_id: str = "1"):
        config = {
            "configurable" : {
                "thread_id": thread_id
            }
        }

        for event in self.graph.stream(query, stream_mode="updates", config=config):
            #interrupt_message = event['__interrupt__']
            yield event