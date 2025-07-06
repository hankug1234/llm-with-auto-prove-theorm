from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import OllamaEmbeddings
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AnyMessage, RemoveMessage
from pydantic import BaseModel, Field
from typing import Annotated, TypedDict, Union
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages




class ToolCallResponse(BaseModel):
    """이것은 llm model이 tools를 호출 할떄 사용 하는 양식 입니다 . <function>[{“function”: {“name”: “some name”, “arguments”: { “some arguments”: “some content” }}},...]</function> 이런 형식의 문장이 답변에 포함 되어 있을시 이 도구를 사용 하세요 """
    tools: str = Field(description="[{“function”: {“name”: “some name”, “arguments”: { “some arguments”: “some content” }}},...]" )

class MessageResponse(BaseModel):
    """이것은 llm model 의 일반적인 반환 양식 입니다. tools 호출 이외에는 이 양식을 사용 합니다.  """
    response : str = Field(description="response of llm model")

class Response(BaseModel):
    result: Union[ToolCallResponse,MessageResponse]      
    
class State(TypedDict):
    history: Annotated[list[AnyMessage], add_messages]
  

class ATPagent:
    def __init__(self,
                 data_path = "",
                 user_id = "admin",
                 information = "",
                 system_prompt="""
                 when you use tool you must use this format [{"function": {"name": "function_name", "arguments": { "arg1": "value1", "arg2": "value2" }}},...]
                 you must have check that your answer is collect or not
                 think step by step 
                 """,tools=[] ,chat_model = None, embeddings=None):
        
        self.tools = tools 
        self.system_prompt = system_prompt
        self.tools_manager = None
        self.information = information
        self.data_path = data_path
        self.user_id = user_id
        
        if embeddings is None:
            embeddings = OllamaEmbeddings(model="llama3")
        
        if chat_model is None:
            chat_model = ChatOllama(model="gemma3:12b")
            
        self.chat_model = chat_model.with_structured_output(Response,method="json_schema")
        self.embeddings = embeddings 
        
        self.memory = InMemoryStore(index={
        "embed": self.embeddings,
        "dims": 4096,
        "fields":["keyword"]
        })
        
        self.checkpointer = MemorySaver()
        self.graph_builder = StateGraph(state_schema=State)
        self.graph = self._build()
        
    def __call__(self,config):
        self.agent_mode_updates(config)
        
    def _build(self):
        self.graph_builder.add_node("init",self.init)
        self.graph_builder.add_node("persona_manager",self.persona_manager)
        self.graph_builder.add_node("persona",self.persona)
        self.graph_builder.add_node("user",self.wait_user_answer)
        self.graph_builder.add_node("tools",self.tool_calling)
        self.graph_builder.add_node("audio",self.play_voice)
        self.graph_builder.add_node("summarize",self.summarize_conversation)
        
        self.graph_builder.add_edge(START,"init")
        self.graph_builder.add_edge("init","persona_manager")
        self.graph_builder.add_edge("persona_manager","summarize")
        self.graph_builder.add_conditional_edges("summarize",self.router,["persona","persona_manager","user","tools","audio",END])
        self.graph_builder.add_edge("user","persona_manager")
        self.graph_builder.add_edge("tools","persona_manager")
        self.graph_builder.add_edge("audio","user")
        self.graph_builder.add_edge("persona","audio")
        
        return self.graph_builder.compile(checkpointer=self.checkpointer,store=self.memory)