from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import OllamaEmbeddings
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AnyMessage, RemoveMessage
from pydantic import BaseModel, Field
import inspect, re, json5, json
from typing import Annotated, List, Callable, Any, TypedDict, Union
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class Tools:
    def __init__(self,tools: List[Callable[...,Any]]):
        
        self.tools :List[Callable[...,Any]]  = tools
        self.system_prompt_template : str = """
        In this environment llm model can access to a set of tools llm model can use to answer the user's question.
        if llm model can answer the user's question llm model has access to a set of tools to find a profit tools

        String and scalar parameters should be specified as is, while lists and objects should use JSON format. Note that spaces for string values are not stripped. The output is not expected to be valid XML and is parsed with regular expressions.
        Here are the functions available in JSONSchema format:
        
        {{ TOOL DEFINITIONS IN JSON SCHEMA }}

        Example when you need to call tools:
        <function_call>[{"function": {"name": "name of function", "arguments": { "arg1": "value1" }}}]</function_call>
        
        If llm model decides that llm model needs to call one or more tools to answer, you should pass the tool request as a list in the following format:
        <function_call>[{"function": {"name": "name of function", "arguments": { "arg1": "value1" }}}, {"function": {"name": "name of function2", "arguments": { "arg1": "value1",   "arg2": "value2"}}}]</function_call>
        

        additional limitation condition when you answer: 
        {{ USER SYSTEM PROMPT }}
        
        If you don't know how to answer a question, you can ask for help.
        
        """
        
        self.tool_scripts : List[dict] = [self._generate_function_description(tool) for tool in self.tools]
        self.functions : dict = {function["function"]["name"]: tool for function,tool in zip(self.json_tool_scripts,self.tools) }
        
    def _generate_function_description(self,func: Callable[...,Any]) -> dict:
        """
        분석할 함수의 정보를 JSON 형태의 딕셔너리로 반환합니다.
        func: 분석할 파이썬 함수
        출력: 함수에 대한 정보를 JSON 형식의 딕셔너리로 반환
        """
        # 함수 이름과 서명을 추출
        func_name = func.__name__
        sig = inspect.signature(func)
        annotations = func.__annotations__
        
        # docstring 추출 및 라인별로 분리
        doc = inspect.getdoc(func) or ""
        lines = [line.strip() for line in doc.splitlines() if line.strip()]
        
        # 첫번째 줄은 함수 전체에 대한 설명으로 사용 (예: 사용 상황 설명)
        func_description = lines[0] if lines else ""
        
        # 이후 라인들은 각 파라미터에 대한 설명으로 기대합니다.
        # 각 라인은 "이름(어떤 부가정보): 설명" 형태여야 합니다.
        param_desc = {}
        param_pattern = re.compile(r'^(\w+)\s*\(.*?\):\s*(.+)$')
        for line in lines[1:]:
            match = param_pattern.match(line)
            if match:
                param_name, description = match.groups()
                # 저장된 설명을 파라미터 이름별로 저장
                param_desc[param_name] = description.strip()
        
        # properties 객체 구성: 각 파라미터에 대해, 타입과 설명을 구성합니다.
        properties = {}
        required_params = []
        for param in sig.parameters.values():
            pname = param.name
            required_params.append(pname)
            # 파라미터 타입 처리: annotation에서 파이썬 타입을 문자열로 변환
            param_type = "unknown"
            if pname in annotations:
                anno = annotations[pname]
                # 만약 anno가 type 객체, 사용 __name__
                if hasattr(anno, '__name__'):
                    param_type = anno.__name__
                else:
                    param_type = str(anno)
            # 파라미터 설명: docstring에서 추출된 설명이 있으면 사용, 없으면 빈 문자열
            desc = param_desc.get(pname, "")
            properties[pname] = {
                "type": param_type,
                "description": desc
            }
        
        # 최종 JSON 딕셔너리 구성
        func_dict = {
            "type": "function",
            "function": {
                "name": func_name,
                "description": func_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_params
                }
            }
        }
        return func_dict

    def get_template(self, user_system_prompt):
        tool_definitions_str = json.dumps(self.tool_scripts, indent=4)
        return self.system_prompt_template\
        .replace("{{ TOOL DEFINITIONS IN JSON SCHEMA }}", tool_definitions_str)\
        .replace("{{ USER SYSTEM PROMPT }}", user_system_prompt)\

    def tools_calling(self, tool_messages : str):
            tool_jsons = json5.loads(tool_messages)
            return {tool_json["function"]["name"] 
                    : self.functions[tool_json["function"]["name"]](**tool_json["function"]["arguments"]) 
                    for tool_json in tool_jsons}


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