import inspect, re, json5, json
from typing import List, Callable, Any
from prompt.toolkit import PROMPT

class Tools:
    def __init__(self,tools: List[Callable[...,Any]]):
        
        self.tools :List[Callable[...,Any]]  = tools
        self.system_prompt_template : str = PROMPT
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