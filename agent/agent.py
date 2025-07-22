import uuid
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
from auto_prove.tableau import prove_with_premises
from auto_prove import Formula, Notated


def add(a: List[Any], b: List[Any]):
    return a + b
    

class ChatModelNoneException(Exception):
    def __init__(self,message="chat model is None"):
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
  

class ATPagent:
    def __init__(self,
                 user_id : str = "admin",
                 end_signal : str = "kill_9",
                 system_prompt : str =""
                 ,tools : List[Callable] =[] 
                 ,chat_model = None
                 ,fol_translate_model = None
                 ,embeddings=None
                 ,fields: List[str] = []
                 ,fol_strict_mode: bool = False):
        
        if len(tools) > 0:
            self.tools = Tools(tools)
        else:
            self.tools = None 
        self.end_signal = end_signal
        self.system_prompt = system_prompt + """
                 you must have check that your answer is collect or not
                 think step by step 
                 """
        self.user_id = user_id
        
        if embeddings is None:
            embeddings = OllamaEmbeddings(model="llama3")
        
        if chat_model is None:
            chat_model = ChatOllama(model="gemma3:12b").with_structured_output(Response,method="json_schema")
            
        if fol_translate_model is None:
            fol_translate_model = ChatOllama(model="gemma3:12b").with_structured_output(TranslateResponse,method="json_schema")
            
        self.chat_model = chat_model
        self.embeddings = embeddings 
        self.fol_translate_model = fol_translate_model
        
        self.memory = InMemoryStore(index={
        "embed": self.embeddings,
        "dims": 4096,
        "fields":fields
        })
        
        self.set_fol_strict_mode(fol_strict_mode)
        
        self.checkpointer = MemorySaver()
        self.graph_builder = StateGraph(state_schema=State)
        self.graph = self._build()
        
    def _init_context(self, state : State):
        new_history = []
        if self.tools:
            new_history.append(self.tools.get_template(self.system_prompt))
        else:
            new_history.append(self.system_prompt)
            
        return {"history" : new_history}
    
    def _retrive_long_term_memory(self, namespace: str ,query: str , limit: int, store:BaseStore)-> list[SearchItem]: 
        return store.search((self.user_id, namespace), query=query, limit=limit)
    
    def _save_long_term_memory(self, namespace: str, value: dict[str, Any], store:BaseStore):
        store.put((self.user_id,namespace),str(uuid.uuid4()),value)
        
        
    def _formal_language_converter(self,sentance : str) -> Union[Formula,str]:
        
        def _converter(formal_sentance:str) -> Formula:
            pass
        
        result = self.fol_translate_model.invoke([HumanMessage(sentance)]).result 
        if isinstance(result,NoneFOLMessageResponse):
            return result.answer 
        
        return _converter(result.answer)
                    
    
    def _analisys_terminologys(self, branches: List[List[Notated]]) -> Tuple[bool,List[str]]:
        pass
    
    def set_fol_strict_mode(self,mode:bool):
        self.fol_strict_mode = mode
        if self.fol_strict_mode:
            from prompt.fol_convertor_strict import PROMPT
            self.fol_translate_prompt = PROMPT 
        else: 
            from prompt.fol_convertor_none_strict import PROMPT 
            self.fol_translate_prompt = PROMPT 
    
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
            
    def _core_model(self,state:State):
        
        if isinstance(state["history"][-1],HumanMessage) and state["history"][-1].content == self.end_signal:
            return Command(goto=END)
        
        if self.chat_model is None:
            raise ChatModelNoneException
        
        if len(state["history"]) >= 6 and any([isinstance(message,HumanMessage) for message in state["history"][-5:]]):
            user_message = interrupt("hard_to_solve")
            response = self.chat_model.invoke([HumanMessage(user_message)]).result
        else:
            response = self.chat_model.invoke([state["history"][-1]]).result
            
        if isinstance(response,ToolCallResponse):
            tool_call_results = "\n".join([f"{k} = {v}" for k,v in self.tools.tools_calling(response.tools)])
            return Command(goto="core_model", update = {"history": [SystemMessage(tool_call_results)]})
            
        return {"history": [AIMessage(response.answer)]}
    
    def _auto_prove(self,state:State):
        conclusion = self._formal_language_converter(state["history"][-1].content)
        result = prove_with_premises(premises=state["premises"], conclusion= conclusion)
        
        none_closed_branches = [branch for is_closed, branch in zip(result[2], result[1]) if is_closed is False]
        analisys_result = self._analisys_terminologys(none_closed_branches)
        
        if result[0] or analisys_result[0]:
            user_question = interrupt(state["history"][-1].content)
            return {"history" : [HumanMessage(user_question)]}
        
        return {"history" : [SystemMessage("\n".join(analisys_result[1]))]}
        
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