import uuid
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import OllamaEmbeddings
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AnyMessage, RemoveMessage
from pydantic import BaseModel, Field
from typing import Annotated, TypedDict, Union, Any, Callable, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.store.base import BaseStore, SearchItem




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
                 user_id : str = "admin",
                 system_prompt : str ="""
                 when you use tool you must use this format [{"function": {"name": "function_name", "arguments": { "arg1": "value1", "arg2": "value2" }}},...]
                 you must have check that your answer is collect or not
                 think step by step 
                 """
                 ,tools : List[Callable] =[] 
                 ,chat_model: str = None
                 ,embeddings=None
                 ,fields: List[str] = []):
        
        self.tools = tools 
        self.system_prompt = system_prompt
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
        "fields":fields
        })
        
        self.checkpointer = MemorySaver()
        self.graph_builder = StateGraph(state_schema=State)
        self.graph = self._build()
        
    def __call__(self,config):
        self.agent_mode_updates(config)
        
    
    def retrive(self, namespace: str ,query: str , limit: int, store:BaseStore)-> list[SearchItem]: 
        return store.search((self.user_id, namespace), query=query, limit=limit)
    
    def save(self, namespace: str, value: dict[str, Any], store:BaseStore):
        store.put((self.user_id,namespace),str(uuid.uuid4()),value)
        
    def agent_mode_updates(self,config):

        for event in self.graph.stream({"manager_messages" : [
                                                        SystemMessage("사용자가 입장 하였습니다. 방문 인사를 해주세요")] , "mode" : MODE.MANAGER},stream_mode="updates",config=config):
            if "persona_manager" in event.keys():
                print(self.ai_message_parse(event['persona_manager']['manager_messages'][-1]))
                print("\n")
        
        is_runnig = True
        while is_runnig:
            user_answer = input("답변을 입력해 주세요 : ")
            print("\n")
            for event in self.graph.stream(Command(resume=user_answer), stream_mode="updates",config=config):
                if "persona_manager" in event.keys():
                    print(self.ai_message_parse(event['persona_manager']['manager_messages'][-1]))
                    print("\n")
                elif "persona" in event.keys():
                    print(self.ai_message_parse(event['persona']['persona_messages'][-1]))
                    print("\n")
                elif "user" in event.keys():
                    if event['user'] is None:
                        is_runnig = False 
                        break 
                    
        print("chatting end")
        
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