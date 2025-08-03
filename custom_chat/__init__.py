from gpt_web import ChatGPTWeb 
from typing import Any, Dict, Iterator, List, Optional
from langchain_core.callbacks import (
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage
)
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field
from selenium.common import TimeoutException
import time 

class OverMaxTokenException(Exception):
    def __init__(self,message):
        super().__init__(message)

class OverMaxRetryException(Exception):
    def __init__(self,message):
        super().__init__(message)

class ChatGPT(BaseChatModel):
    """A custom chat model that echoes the first `parrot_buffer_length` characters
    of the input.

    When contributing an implementation to LangChain, carefully document
    the model including the initialization parameters, include
    an example of how to initialize the model and include any relevant
    links to the underlying models documentation or API.

    Example:

        .. code-block:: python

            model = ChatParrotLink(parrot_buffer_length=2, model="bird-brain-001")
            result = model.invoke([HumanMessage(content="hello")])
            result = model.batch([[HumanMessage(content="hello")],
                                 [HumanMessage(content="world")]])
    """
    
    model_name: str = None
    buffer_length: int
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    stop: Optional[List[str]] = None
    max_retries: int = 2
    debug_mode_open: bool = True
    llm: ChatGPTWeb = None

    def __init__(self, **data):
        super().__init__(**data)
        self.llm = ChatGPTWeb(
            model=self.model_name,
            timeout=self.timeout,
            debug_mode_open=self.debug_mode_open,
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Override the _generate method to implement the chat model logic.

        This can be a call to an API, a call to a local model, or any other
        implementation that generates a response to the input prompt.

        Args:
            messages: the prompt composed of a list of messages.
            stop: a list of strings on which the model should stop generating.
                  If generation stops due to a stop token, the stop token itself
                  SHOULD BE INCLUDED as part of the output. This is not enforced
                  across models right now, but it's a good practice to follow since
                  it makes it much easier to parse the output of the model
                  downstream and understand why generation stopped.
            run_manager: A run manager with callbacks for the LLM.
        """
        # Replace this with actual logic to generate a response from a list
        # of messages.
        request = "\n".join([message.content  for message in messages ])
        end_length = self.buffer_length
        start_length = 0
        retry_count = 0
        ct_input_tokens = len(request)
        tokens = ""       
        
        if ct_input_tokens > self.max_tokens:
            raise OverMaxTokenException(f"over max token error token size must small then {self.max_tokens}")
        
        start = time.time()
        while retry_count <= self.max_retries:
            try:
                while start_length < ct_input_tokens:
                    tokens = self.llm.invoke(request[start_length: end_length])
                    start_length += self.buffer_length
                    end_length += self.buffer_length
                break
            except TimeoutException:
                retry_count += 1
        
        if retry_count > self.max_retries:
            raise OverMaxRetryException("over max retries")
        
        end = time.time()
        total_time = end - start 
        
        ct_output_tokens = len(tokens)
        
        message = AIMessage(
            content=tokens,
            additional_kwargs={},  # Used to add additional payload to the message
            response_metadata={  # Use for response metadata
                "time_in_seconds": total_time,
                "model_name": self.model_name,
            },
            usage_metadata={
                "input_tokens": ct_input_tokens,
                "output_tokens": ct_output_tokens,
                "total_tokens": ct_input_tokens + ct_output_tokens,
            },
        )

        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream the output of the model.

        This method should be implemented if the model can generate output
        in a streaming fashion. If the model does not support streaming,
        do not implement it. In that case streaming requests will be automatically
        handled by the _generate method.

        Args:
            messages: the prompt composed of a list of messages.
            stop: a list of strings on which the model should stop generating.
                  If generation stops due to a stop token, the stop token itself
                  SHOULD BE INCLUDED as part of the output. This is not enforced
                  across models right now, but it's a good practice to follow since
                  it makes it much easier to parse the output of the model
                  downstream and understand why generation stopped.
            run_manager: A run manager with callbacks for the LLM.
        """
        last_message = messages[-1]
        tokens = str(last_message.content[: self.parrot_buffer_length])
        ct_input_tokens = sum(len(message.content) for message in messages)

        for token in tokens:
            usage_metadata = UsageMetadata(
                {
                    "input_tokens": ct_input_tokens,
                    "output_tokens": 1,
                    "total_tokens": ct_input_tokens + 1,
                }
            )
            ct_input_tokens = 0
            chunk = ChatGenerationChunk(
                message=AIMessageChunk(content=token, usage_metadata=usage_metadata)
            )

            if run_manager:
                # This is optional in newer versions of LangChain
                # The on_llm_new_token will be called automatically
                run_manager.on_llm_new_token(token, chunk=chunk)

            yield chunk

        # Let's add some other information (e.g., response metadata)
        chunk = ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                response_metadata={"time_in_sec": 3, "model_name": self.model_name},
            )
        )
        if run_manager:
            # This is optional in newer versions of LangChain
            # The on_llm_new_token will be called automatically
            run_manager.on_llm_new_token(token, chunk=chunk)
        yield chunk

    @property
    def _llm_type(self) -> str:
        """Get the type of language model used by this chat model."""
        return "echoing-chat-model-advanced"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return a dictionary of identifying parameters.

        This information is used by the LangChain callback system, which
        is used for tracing purposes make it possible to monitor LLMs.
        """
        return {
            # The model name allows users to specify custom token counting
            # rules in LLM monitoring applications (e.g., in LangSmith users
            # can provide per token pricing for their model and monitor
            # costs for the given LLM.)
            "model_name": self.model_name,
        }
    
    def params(self):
        return {
            "model_name": self.model_name,
            "buffer_length": self.buffer_length,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "stop": self.stop,
            "max_retries": self.max_retries,
            "debug_mode_open": self.debug_mode_open
        }
        
if __name__ == "__main__":
    import sys 
    sys.path.append(".")
    from agent import Response
    chat = ChatGPT(model_name="gpt-4o",buffer_length = 1500 ,max_tokens = 15000, timeout=60, max_retries=1,debug_mode_open=False).with_structured_output(Response,method="json_schema")
    print(chat.params())
    messages = [HumanMessage("how are you doing")]
    result = chat.invoke(messages)
    print(result.content)